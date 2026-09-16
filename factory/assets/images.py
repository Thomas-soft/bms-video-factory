"""Images de plan : génération locale par mflux, **cache de bibliothèque**, licence par fichier.

Ce qui coûte ici, c'est le modèle : **137 s par image en 1280×720** à l'étape 5.2, soit 84 % du
temps d'une vidéo. Ce module n'accélère pas le modèle — il l'appelle moins. Deux leviers, tous
deux mesurés au manifeste (`library_reuse`) :

1. **La clé de cache est le prompt, pas le plan.** Deux plans d'un même segment demandent la même
   intention visuelle ; ils partagent donc une seule image. Sur le run FR : 127 plans,
   **56 prompts distincts**.
2. **La bibliothèque survit au run.** `workspace/library/images/<clé>.png` et son `<clé>.json`
   frère (même contrat que `assets/<shot>/licence.json`) sont indexés dans `library_assets` ;
   la vidéo n° 50 réutilise ce que la n° 1 a produit.

**Trois pièges hérités de l'étape 5.2, et ce qu'ils imposent ici.**

- `hash()` de Python est **randomisé par processus** : la graine vient de `sha256`, comme
  `shotlist.graine_de_plan`. Sans cela, « même plan, même image » est faux d'un run à l'autre.
- **FLUX.2 n'a pas de prompt négatif** (`--negative-prompt` sort en erreur sur cette famille) et
  « no text » ne retire aucun texte : ce qui marche est de **décrire positivement** la surface
  propre. `charte.style_suffix` est écrit dans ce sens ; `charte.negative_prompt` n'est pas envoyé
  au modèle et le journal le dit, plutôt que de laisser croire qu'il agit.
- **La graine ne fait pas le style.** Une graine fixe ne fige que le bruit initial : dès que le
  prompt change, le style change. La cohérence vient donc du **texte** — préfixe de charte
  identique mot pour mot, cadrage et fond fixés par `charte.framing`.

Un sous-processus par image, qui se termine : `--low-ram` ne garde le transformer résident que
pour un lot de plusieurs graines d'un même prompt, ce qui n'est jamais notre cas. La règle « un
seul modèle résident » (`ARCHITECTURE` § 1.3) prime sur le temps de chargement.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from factory.core.models import Asset, Channel, Generateur, Shot
from factory.core.paths import RunPaths, racine_projet

#: Binaire de génération. mflux est installé en `uv tool` (hors `.venv`), donc jamais importable.
BINAIRE = "mflux-generate-flux2"
#: Poids par défaut — surchargés par `config/styles/<id>.yaml` → `params.image.model`.
MODELE_DEFAUT = "mlx-community/FLUX.2-Klein-4B-4bit"
#: FLUX.2 [klein] est un modèle distillé « turbo » : 4 étapes est son réglage nominal.
ETAPES_DEFAUT = 4
#: Les deux seuls formats 16:9 retenus. mflux exige des multiples de 16 (arrondi au-dessous sinon).
RESOLUTION_DEFAUT = "1280x720"
#: Essais de génération par image. Au-delà, le plan est servi par le repli de charte.
ESSAIS = 2
#: En deçà, le PNG rendu est un fichier vide ou tronqué : régénérer, ne pas le promouvoir.
TAILLE_MINIMALE_OCTETS = 8192
#: Licence des poids, donc de ce qu'ils produisent. Vérifiée à l'étape 4.
LICENCE = "Apache-2.0"
LICENCE_URL = "https://www.apache.org/licenses/LICENSE-2.0"
#: Caches à rediriger sous `models/` (`CLAUDE.md` § 3). mflux tourne en `uv tool`, hors du
#: `.venv` et donc **hors du `.env` du projet** : sans ces variables il re-télécharge 4,3 Go
#: dans `~/.cache/huggingface`. Mesuré le 16/09/2026 : 2 Gi de disque partis en 13 minutes.
CACHES = {"HF_HOME": "models/hf", "MFLUX_CACHE_DIR": "models/mflux"}


def environnement(racine: Path) -> dict[str, str]:
    """Environnement d'un sous-processus de modèle : caches sous `models/`, jamais sous `~`."""
    env = dict(os.environ)
    for variable, relatif in CACHES.items():
        env[variable] = str((racine / relatif).resolve())
    return env


class ImageIndisponible(RuntimeError):
    """Le modèle n'a pas rendu d'image exploitable après `ESSAIS` tentatives."""


class CharteIncomplete(RuntimeError):
    """La charte ne porte pas de style d'image : un moteur générateur refuse de l'inventer."""


# --------------------------------------------------------------------------------------
# Prompt et clés
# --------------------------------------------------------------------------------------

def normaliser(texte: str) -> str:
    """Forme canonique d'un prompt pour le cache : accents, casse et ponctuation retirés.

    « Un cristal de sucre… » et « un cristal de sucre - plan large » ne doivent se confondre que
    si elles décrivent la même image : la normalisation retire le bruit de saisie, **pas** les
    mots. Les tirets cadratins de `shotlist._intention` deviennent des espaces.
    """
    sans_accent = unicodedata.normalize("NFKD", texte)
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sans_accent.lower()).strip()


def construire_prompt(channel: Channel, intention: str, rupture: bool = False) -> str:
    """`style_prefix` + intention + cadrage de charte + `style_suffix`.

    L'ordre n'est pas décoratif : le préfixe porte le style (identique **mot pour mot** sur toute
    la chaîne), l'intention porte le sujet, le suffixe referme sur la palette et le cadrage. Le
    fond et l'échelle du sujet viennent de `charte.framing` — c'est le manque que l'étape 5.2 a
    payé d'un plan encadré sur huit.
    """
    charte = channel.charte
    if not charte.style_prefix.strip():
        raise CharteIncomplete(
            f"{channel.id} : charte.style_prefix est vide — un moteur qui génère des images ne "
            "peut pas choisir le style à la place de la charte "
            f"(config/channels/{channel.id}.yaml, charte.version {charte.version})"
        )
    morceaux = [charte.style_prefix.strip().rstrip(","), intention.strip().rstrip(".")]
    if rupture:
        # La rupture change de cadre et de fond sans changer de style : c'est ce que le découpage
        # demande (`shotlist._intention`) et ce que `cartes` n'a pas pu tenir faute d'un second
        # type d'asset. Ici, un mot de plus suffit — et il entre dans la clé de cache.
        morceaux.append("wide establishing framing, different background")
    if charte.framing.background.strip():
        morceaux.append(charte.framing.background.strip())
    if charte.framing.subject_scale.strip():
        morceaux.append(charte.framing.subject_scale.strip())
    if charte.style_suffix.strip():
        morceaux.append(charte.style_suffix.strip().lstrip(","))
    return ", ".join(m for m in morceaux if m)


# --------------------------------------------------------------------------------------
# Traduction des intentions visuelles
# --------------------------------------------------------------------------------------

#: Taille d'un lot de traduction. Chaque appel LLM est un sous-processus `llama-cli` qui charge
#: 6,6 Go de poids : grouper divise le nombre de chargements, pas le nombre de mots.
LOT_TRADUCTION = 8

#: Ce que le traducteur doit produire, et surtout ce qu'il ne doit jamais produire.
#:
#: **Mesuré le 16/09/2026, et c'est ce qui a fait écrire ce module.** Sur les cinq premières
#: images du run FR, deux portaient du faux texte en gros caractères et **l'une avait recopié le
#: prompt français lui-même** (« un cristal de sucre », écrit dans l'image). Deux causes, toutes
#: deux corrigées ici : FLUX.2 [klein] est légendé en anglais et rend littéralement ce qu'il ne
#: comprend pas ; et **une intention qui nomme du texte en fait apparaître** — « séquence
#: binaire » produit des chiffres, comme « no text » produit des lettres.
SYSTEME_TRADUCTION = (
    "You turn short video shot descriptions into English prompts for an image model.\n"
    "Rules, all mandatory:\n"
    "1. Output ONE line per input, numbered exactly as the input: `1. ...`\n"
    "2. English only, 6 to 18 words, a visual noun phrase — no verb tense, no sentence.\n"
    "3. Describe only what is SEEN: objects, materials, shapes, light, arrangement.\n"
    "4. Never mention writing, text, letters, numbers, digits, labels, signs, screens, "
    "titles, captions or symbols. If the source mentions any of them, replace it with an "
    "abstract visual equivalent (glowing squares, a lattice, coloured dots, a ribbon).\n"
    "5. No style words (no 'flat', 'vector', 'illustration', 'palette') — the style is added "
    "elsewhere.\n"
    "6. No people's names, no real identifiable person.\n"
    "Answer with the numbered lines and nothing else."
)


def traduire_intentions(
    intentions: list[str], lang: str, racine: Path | None = None,
    journal: IO[str] | None = None,
) -> dict[str, str]:
    """Intention de plan → description visuelle anglaise, par lots, avec le cache LLM du projet.

    Une chaîne anglophone n'y passe pas : elle n'a rien à traduire, et le passage y coûterait le
    chargement d'un 9B pour rien. Une intention non traduite retombe sur elle-même — un plan
    servi par un sujet français vaut mieux qu'un plan non servi, et le journal le dit.
    """
    from factory import llm

    base = racine or racine_projet()
    uniques = sorted({i.strip() for i in intentions if i.strip()})
    if not uniques:
        return {}
    if lang == "en":
        return {i: i for i in uniques}

    traductions: dict[str, str] = {}
    for depart in range(0, len(uniques), LOT_TRADUCTION):
        lot = uniques[depart : depart + LOT_TRADUCTION]
        demande = "\n".join(f"{n}. {texte}" for n, texte in enumerate(lot, start=1))
        try:
            reponse = llm.generate(
                demande, system=SYSTEME_TRADUCTION, max_tokens=60 * len(lot),
                temperature=0.2, seed=17, etiquette="image_prompt_fr_en", racine=base,
            )
        except Exception as erreur:  # un lot perdu ne fait pas tomber le run
            if journal is not None:
                journal.write(f"traduction : lot {depart // LOT_TRADUCTION} échoué — {erreur}\n")
            continue
        for ligne in reponse.texte.splitlines():
            trouve = re.match(r"\s*(\d+)[.)]\s*(.+)", ligne.strip())
            if not trouve:
                continue
            rang = int(trouve.group(1)) - 1
            if 0 <= rang < len(lot):
                traductions[lot[rang]] = trouve.group(2).strip().strip('"')

    manquantes = [i for i in uniques if i not in traductions]
    for intention in manquantes:
        traductions[intention] = intention
    if journal is not None:
        journal.write(
            f"traduction : {len(uniques) - len(manquantes)}/{len(uniques)} intention(s) "
            f"{lang}→en" + (f", {len(manquantes)} laissée(s) telles quelles" if manquantes else "")
            + "\n"
        )
        journal.flush()
    return traductions


def cle_bibliotheque(prompt: str, style_id: str, charte_version: str, resolution: str) -> str:
    """Clé de cache d'une image : `sha256(prompt normalisé + style + charte + format)[:16]`.

    La **version de charte** entre dans la clé : changer la palette d'une chaîne doit produire de
    nouvelles images, pas ressortir les anciennes. Le format aussi : une image 1024×576 promue en
    1280×720 serait un agrandissement, donc une image différente.
    """
    brut = f"{normaliser(prompt)}|{style_id}|{charte_version}|{resolution}"
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()[:16]


def graine_de(video_id: str, shot_id: str, essai: int = 0) -> int:
    """`sha256(video_id + shot_id)` — jamais `hash()`, randomisé par processus.

    `essai` décale la graine sans changer le plan : une image inexploitable est régénérée avec un
    bruit initial différent, et le même plan rejoué retombe sur la même graine.
    """
    brut = f"{video_id}{shot_id}" if essai == 0 else f"{video_id}{shot_id}#{essai}"
    return int(hashlib.sha256(brut.encode("utf-8")).hexdigest()[:16], 16)


def graine_mflux(graine: int) -> int:
    """Graine ramenée au domaine accepté par mflux (entier 32 bits non signé)."""
    return graine % (2**32)


# --------------------------------------------------------------------------------------
# Bibliothèque
# --------------------------------------------------------------------------------------

def dossier_bibliotheque(racine: Path | None = None) -> Path:
    """`workspace/library/images/` — créé à la demande."""
    dossier = (racine or racine_projet()) / "workspace" / "library" / "images"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def maintenant() -> str:
    """Horodatage ISO-8601 UTC, comme tous les fichiers du run."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reutilisable(
    conn: sqlite3.Connection, asset_id: str, channel: Channel, video_id: str
) -> tuple[bool, str]:
    """La bibliothèque peut-elle servir cet asset à cette chaîne, pour ce run ?

    Deux plafonds de `channel.library` : `cooldown_videos` (combien de vidéos doivent séparer
    deux emplois) et `max_uses_per_channel`. **Le rejeu du même run ne compte pas** : sans cette
    exception, une reprise après incident régénérerait des heures d'images déjà payées, et le
    critère « deuxième exécution, 0 génération » de l'étape 12.2 serait intenable
    (`INTERFACES.md` § 3, objection 18).
    """
    if conn.execute(
        "SELECT 1 FROM library_uses WHERE asset_id = ? AND video_id = ?", (asset_id, video_id)
    ).fetchone():
        return True, "déjà employé par ce run"

    usages = [
        ligne["video_id"]
        for ligne in conn.execute(
            "SELECT video_id FROM library_uses WHERE asset_id = ? AND channel_id = ? "
            "ORDER BY used_at DESC",
            (asset_id, channel.id),
        )
    ]
    if len(usages) >= channel.library.max_uses_per_channel:
        return False, f"max_uses_per_channel atteint ({len(usages)})"

    if usages and channel.library.cooldown_videos:
        recents = [
            ligne["video_id"]
            for ligne in conn.execute(
                "SELECT DISTINCT video_id FROM library_uses WHERE channel_id = ? "
                "ORDER BY used_at DESC LIMIT ?",
                (channel.id, channel.library.cooldown_videos),
            )
        ]
        if set(usages) & set(recents):
            return False, f"employé dans les {channel.library.cooldown_videos} derniers runs"
    return True, "libre"


def _inscrire(
    conn: sqlite3.Connection, asset: Asset, chemin: Path, prompt_key: str,
    channel: Channel, video_id: str, racine: Path,
) -> None:
    """Index `library_assets` + trace d'emploi `library_uses`, toutes deux idempotentes."""
    conn.execute(
        "INSERT INTO library_assets (asset_id, kind, layer, path, provider, licence, licence_url,"
        " attribution_line, person_release, has_text, lang, keywords, phash, prompt_key, uses,"
        " created_at, last_used_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)"
        " ON CONFLICT(asset_id) DO UPDATE SET last_used_at = excluded.last_used_at",
        (
            asset.asset_id, "images", "background", str(chemin.relative_to(racine)),
            asset.provider, asset.licence, asset.licence_url, asset.attribution_line,
            asset.person_release, int(asset.has_text),
            # `lang` reste NULL tant que l'image ne porte pas de texte : une image sans lettrage
            # franchit la frontière de langue, une image lettrée non (`INTERFACES.md` § 3).
            channel.lang if asset.has_text else None,
            prompt_key, None, prompt_key, maintenant(), maintenant(),
        ),
    )
    conn.execute(
        "INSERT INTO library_uses (asset_id, video_id, channel_id, used_at) VALUES (?,?,?,?)"
        " ON CONFLICT(asset_id, video_id) DO UPDATE SET used_at = excluded.used_at",
        (asset.asset_id, video_id, channel.id, maintenant()),
    )
    conn.execute(
        "UPDATE library_assets SET uses = (SELECT COUNT(*) FROM library_uses WHERE asset_id = ?),"
        " last_used_at = ? WHERE asset_id = ?",
        (asset.asset_id, maintenant(), asset.asset_id),
    )


# --------------------------------------------------------------------------------------
# Générateur
# --------------------------------------------------------------------------------------

@dataclass
class ResultatImage:
    """Une image servie à un plan, et ce qu'elle a coûté."""

    chemin: Path
    asset: Asset
    cle: str
    genere: bool
    secondes: float
    essais: int = 1
    pic_mlx_go: float | None = None


@dataclass
class GenerateurImages:
    """Sert une image par plan, de la bibliothèque ou du modèle. Un sous-processus par image."""

    conn: sqlite3.Connection
    style_id: str
    racine: Path = field(default_factory=racine_projet)
    journal: IO[str] | None = None
    modele: str = MODELE_DEFAUT
    resolution: str = RESOLUTION_DEFAUT
    etapes: int = ETAPES_DEFAUT
    #: Rempli par la première génération : `« Peak MLX memory: 11.15 GB »` annoncé par mflux.
    pics_mlx: list[float] = field(default_factory=list)
    #: Temps de chaque génération réelle, en secondes ; les réemplois n'y figurent pas.
    temps_generation: list[float] = field(default_factory=list)
    #: Intention de plan → description visuelle anglaise (`traduire_intentions`). Vide pour
    #: une chaîne anglophone : le sujet y est déjà dans la langue du modèle.
    traductions: dict[str, str] = field(default_factory=dict)

    @property
    def largeur_hauteur(self) -> tuple[int, int]:
        largeur, hauteur = self.resolution.lower().split("x")
        return int(largeur), int(hauteur)

    def tracer(self, message: str) -> None:
        if self.journal is not None:
            self.journal.write(message.rstrip() + "\n")
            self.journal.flush()

    # -- appel du modèle -----------------------------------------------------------------

    def _binaire(self) -> str:
        chemin = shutil.which(BINAIRE) or str(Path.home() / ".local" / "bin" / BINAIRE)
        if not Path(chemin).exists():
            raise ImageIndisponible(
                f"{BINAIRE} introuvable : mflux est installé en `uv tool` "
                "(`uv tool install mflux`), voir outils/MODELES.md"
            )
        return chemin

    def _generer(self, prompt: str, graine: int, sortie: Path) -> tuple[bool, float, str]:
        """Un appel mflux, dans un sous-processus qui se termine. Rend (succès, secondes, sortie)."""
        largeur, hauteur = self.largeur_hauteur
        commande = [
            self._binaire(), "--model", self.modele, "--prompt", prompt,
            "--width", str(largeur), "--height", str(hauteur),
            "--steps", str(self.etapes), "--seed", str(graine_mflux(graine)),
            # `--low-ram` décharge le transformer entre deux images et `--vae-tiling` découpe le
            # décodage VAE : 11,15 Go de pic au lieu de 14 (mesuré étape 5.2 et mflux #407).
            "--low-ram", "--vae-tiling",
            "--output", str(sortie),
        ]
        depart = time.perf_counter()
        processus = subprocess.run(
            commande, capture_output=True, text=True, env=environnement(self.racine)
        )
        secondes = time.perf_counter() - depart
        sortie_texte = (processus.stdout or "") + (processus.stderr or "")
        pic = re.findall(r"Peak MLX memory:\s*([\d.]+)\s*GB", sortie_texte)
        if pic:
            self.pics_mlx.append(max(float(x) for x in pic))
        exploitable = (
            processus.returncode == 0
            and sortie.exists()
            and sortie.stat().st_size >= TAILLE_MINIMALE_OCTETS
        )
        return exploitable, secondes, sortie_texte

    # -- service d'un plan ---------------------------------------------------------------

    def image_pour(
        self, shot: Shot, channel: Channel, video_id: str, rupture: bool = False
    ) -> ResultatImage:
        """L'image d'un plan : celle de la bibliothèque si elle est libre, sinon une génération."""
        demande = shot.asset_request.prompt_or_keywords.strip()
        # La traduction est faite en amont, en lots, par `traduire_intentions` : ici on ne
        # fait que la lire. Absente, l'intention passe telle quelle — et le prompt reste
        # servi plutôt qu'abandonné.
        sujet = self.traductions.get(demande, demande)
        prompt = construire_prompt(channel, sujet, rupture)
        cle = cle_bibliotheque(prompt, self.style_id, channel.charte.version, self.resolution)
        dossier = dossier_bibliotheque(self.racine)
        fichier, licence = dossier / f"{cle}.png", dossier / f"{cle}.json"

        if fichier.exists() and fichier.stat().st_size >= TAILLE_MINIMALE_OCTETS and licence.exists():
            asset = Asset.model_validate_json(licence.read_text(encoding="utf-8"))
            libre, motif = _reutilisable(self.conn, asset.asset_id, channel, video_id)
            if libre:
                self.tracer(f"{shot.id} : bibliothèque {cle} ({motif})")
                _inscrire(self.conn, asset, fichier, cle, channel, video_id, self.racine)
                return ResultatImage(fichier, asset, cle, genere=False, secondes=0.0, essais=0)
            # Le cooldown ne dit pas « régénère » mais « ne ressers pas celle-ci » : une nouvelle
            # graine produit une image différente, qui prend sa propre clé.
            self.tracer(f"{shot.id} : {cle} écartée ({motif}) — nouvelle image")
            cle = cle_bibliotheque(
                prompt + f" #{shot.id}", self.style_id, channel.charte.version, self.resolution
            )
            fichier, licence = dossier / f"{cle}.png", dossier / f"{cle}.json"

        dernier = ""
        for essai in range(ESSAIS):
            graine = graine_de(video_id, shot.id, essai)
            exploitable, secondes, sortie_texte = self._generer(prompt, graine, fichier)
            if exploitable:
                self.temps_generation.append(secondes)
                asset = self._licence(fichier, licence, prompt, graine, shot, channel)
                _inscrire(self.conn, asset, fichier, cle, channel, video_id, self.racine)
                self.tracer(
                    f"{shot.id} : générée {cle} en {secondes:.1f} s "
                    f"(graine {graine_mflux(graine)}, essai {essai + 1})"
                )
                return ResultatImage(
                    fichier, asset, cle, genere=True, secondes=secondes, essais=essai + 1,
                    pic_mlx_go=self.pics_mlx[-1] if self.pics_mlx else None,
                )
            # Un PNG vide ou tronqué est pire qu'une absence : il passerait les contrôles de
            # présence et casserait le rendu. Il est retiré avant de rejouer.
            if fichier.exists():
                fichier.unlink()
            dernier = sortie_texte.strip()[-400:]
            self.tracer(f"{shot.id} : essai {essai + 1}/{ESSAIS} échoué — {dernier[-200:]}")

        raise ImageIndisponible(f"{shot.id} : {ESSAIS} essais échoués — {dernier}")

    def _licence(
        self, fichier: Path, licence: Path, prompt: str, graine: int, shot: Shot, channel: Channel
    ) -> Asset:
        """Écrit `<clé>.json` à côté du PNG : même contrat que `assets/<shot>/licence.json`."""
        asset = Asset(
            asset_id=hashlib.sha256(fichier.read_bytes()).hexdigest()[:16],
            path=str(fichier.relative_to(self.racine)),
            provider="flux",
            source_url=None,
            author="BMS (généré)",
            licence=LICENCE,
            licence_url=LICENCE_URL,
            attribution_line=None,
            downloaded_at=maintenant(),
            person_release=None,
            generator=Generateur(
                model=self.modele,
                model_revision=None,
                prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                seed=graine_mflux(graine),
                steps=self.etapes,
                resolution=self.resolution,
            ),
            # Les deux drapeaux sont posés **au moment de la génération** : reconstitués après
            # coup, ils seraient faux (`INTERFACES.md` § assets).
            realistic=shot.asset_request.realistic,
            has_text=False,
            c2pa_present=False,
        )
        licence.write_text(
            json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        # Le prompt complet ne tient pas dans le contrat `Asset` (qui n'en garde que le hachage) :
        # il est gardé à part, sans quoi « même graine » ne veut rien dire à la relecture.
        (licence.with_suffix(".prompt.txt")).write_text(prompt + "\n", encoding="utf-8")
        return asset


def copier_vers_run(source: Path, run: RunPaths, shot_id: str, asset: Asset) -> Asset:
    """Dépose l'image de bibliothèque dans `assets/<shot>/image.png` et y écrit sa licence.

    La copie est volontaire : un run doit rester lisible et rejouable **seul**, sans dépendre de
    l'état de la bibliothèque au moment où on le relit. Le `licence.json` du run porte le chemin
    du run, l'`asset_id` reste celui du fichier d'origine — c'est lui qui joint les deux.
    """
    dossier = run.asset_dir(shot_id)
    dossier.mkdir(parents=True, exist_ok=True)
    destination = dossier / "image.png"
    if not destination.exists() or destination.stat().st_size != source.stat().st_size:
        shutil.copy2(source, destination)
    dans_le_run = asset.model_copy(update={"path": f"assets/{shot_id}/image.png"})
    run.licence(shot_id).write_text(
        json.dumps(dans_le_run.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dans_le_run
