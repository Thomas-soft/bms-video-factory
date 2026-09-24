"""Assets de banques libres : recherche par mots-clés, licence par fichier, chaîne de repli.

Le style « documentaire » ne génère rien : il **monte du réel**. Ce module va chercher ce réel
dans cinq banques, dans un ordre qui n'est pas arbitraire (`docs/STYLES.md`, `outils/LICENCES.md`) :

1. **Pexels** — vidéos 1080p natives, la seule banque dont le catalogue est pensé pour le montage.
   Attribution *imposée par les conditions de l'API*, pas par la licence.
2. **Pixabay** — vidéos, aucune attribution due, mais **cache 24 h obligatoire** : c'est une
   contrainte de conception, pas une optimisation — les fichiers vivent en bibliothèque.
3. **Openverse** — **images seulement** (le service n'indexe pas de vidéo). Filtré sur `cc0`,
   `pdm` et `by` : les `by-sa` sont écartés en amont comme chez Wikimedia, une clause de partage
   à l'identique n'a rien à faire dans une vidéo commerciale.
4. **Internet Archive** — films du domaine public. Le service « *does not make guarantees as to
   the copyright status* » : on n'accepte donc **que** `licenseurl` explicitement domaine public
   ou CC, jamais un item au seul motif qu'il est ancien.
5. **NASA** — images et vidéos, domaine public américain, crédit « NASA ». Le piège n'est pas la
   licence mais **le droit à l'image** : toute personne identifiable sort du domaine public
   (`outils/LICENCES.md`), et c'est vrai d'un ingénieur au contrôle comme d'un astronaute.

**Un plan n'échoue jamais.** Si les cinq banques ne rendent rien, le module rend `None` et le
moteur sert une image générée — c'est le repli, et il est mesuré au manifeste. Un plan servi par
un repli vaut mieux qu'un run perdu à la dernière minute d'un rendu d'une heure.

**Trois règles dont dépend la conformité, et qui se lisent ici plutôt qu'au montage.**

- **Aucun asset ne descend sans ses sept champs** (`CONFORMITE.md` § 8) : `provider`, `source_url`,
  `author`, `licence`, `licence_url`, `attribution_line`, `downloaded_at`. Le contrôle est à
  l'acquisition ; au montage il est trop tard, le fichier est déjà dans la vidéo.
- **Les personnes identifiables sont écartées par le vocabulaire du titre et des mots-clés**
  (`_annonce_une_personne`). C'est un plancher lexical, assumé comme tel : il ne voit pas un
  visage qu'aucun mot n'annonce. Le plan passe alors par la relecture visuelle
  (`person_review: true` dans `config/styles/documentaire.yaml`).
- **Le quota est compté localement, jamais deviné.** `workspace/library/stock/quotas.json` porte
  un compteur par fournisseur, par heure, par jour et par mois ; proche du plafond, il ralentit,
  au plafond il saute le fournisseur et passe au suivant. Aucune requête n'est envoyée « pour
  voir » : une réponse 429 est une faute de conception, pas un aléa.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, IO
from urllib.parse import quote, urlsplit, urlunsplit

import requests

from factory.core.models import Asset, Channel, Shot
from factory.core.paths import racine_projet

#: Ordre d'interrogation. Il est dans la configuration du style (`params.stock.providers`) ;
#: celui-ci n'est que le défaut quand elle n'en donne pas.
CHAINE_DEFAUT: tuple[str, ...] = ("pexels", "pixabay", "openverse", "internet_archive", "nasa")

#: Banques dont le catalogue ne contient aucune vidéo exploitable. Elles passent derrière les
#: autres quand aucune banque vidéo à clé n'est disponible (`BanqueStock.fournisseurs_actifs`).
IMAGES_SEULEMENT: frozenset[str] = frozenset({"openverse"})

#: Résolution minimale exigée d'un asset retenu. Un 720p agrandi en 1080 se voit sur du réel :
#: le grain de la source ne suit pas l'échelle, contrairement à une image générée.
LARGEUR_MIN, HAUTEUR_MIN = 1920, 1080
#: Marge de durée : un clip doit dépasser son plan d'au moins une seconde pour qu'on puisse
#: choisir **où** couper dedans (début, ou passage le plus mouvementé).
MARGE_DUREE_S = 1.0
#: Rapport largeur/hauteur minimal : en deçà, l'image est carrée ou verticale et le recadrage
#: 16:9 mangerait le sujet.
RATIO_MIN = 1.5
#: Candidats examinés par requête. Au-delà, on paie des requêtes pour des résultats que le
#: filtre écarte de toute façon.
PAR_PAGE = 15
#: Nombre de requêtes distinctes par intention visuelle (le LLM en produit autant).
REQUETES_PAR_PLAN = 3
#: Délai de réseau. Une banque qui ne répond pas ne bloque pas un run d'une heure.
TIMEOUT_S = 25
#: Taille en deçà de laquelle un téléchargement est une page d'erreur, pas une vidéo.
TAILLE_MINIMALE_OCTETS = 65536
#: Poids maximal d'un fichier accepté. Le disque est la ressource rare (`CLAUDE.md` § 3) et un
#: plan consomme 7 s d'un clip : payer 82 Mo pour cela — mesuré le 18/09/2026 sur la vidéo NASA
#: `GSFC_20170920_GPM_m12723_JoseMaria` — n'achète rien. À 60 Mo, les clips 1080p courts passent
#: encore (16,7 Mo pour 10 s, 54,1 Mo pour 20 s, mesurés le même jour) et les longs métrages non.
TAILLE_MAXIMALE_OCTETS = 60 * 1024 * 1024

#: Plafond de la bibliothèque de banque. Au-delà, plus aucun téléchargement : la chaîne descend
#: jusqu'au repli généré, qui ne coûte rien de plus. La roadmap prévoit 0,5 à 1 Go ; ce plafond
#: laisse la marge d'un second run avant que la purge devienne nécessaire.
BUDGET_BIBLIOTHEQUE_OCTETS = 2 * 1024 * 1024 * 1024

#: Quotas déclarés par les fournisseurs, en **requêtes de recherche**. `None` = non documenté :
#: dans ce cas le compteur compte quand même, et le journal le publie, mais rien n'est plafonné.
#:
#: **Le plafond qui mord n'est pas celui de Pexels.** Un run de 130 plans × 3 requêtes fait 390
#: requêtes : c'est déjà deux fois le plafond **journalier** d'Openverse en anonyme (200/jour,
#: relevé sur `x-ratelimit-limit-anon_sustained` le 18/09/2026), et les 200/h de Pexels se
#: passent en une heure. D'où le seau journalier, que la première écriture de ce module n'avait
#: pas : un plafond horaire seul laisse passer ce qui se compte à la journée.
QUOTAS: dict[str, dict[str, int | None]] = {
    "pexels": {"heure": 200, "jour": None, "mois": 20000},
    "pixabay": {"heure": 6000, "jour": None, "mois": None},   # 100 requêtes / 60 s annoncées
    "openverse": {"heure": 1200, "jour": 200, "mois": None},  # 20/min et 200/jour en anonyme
    "internet_archive": {"heure": 300, "jour": None, "mois": None},   # non documentés
    "nasa": {"heure": 300, "jour": None, "mois": None},               # non documentés
}

#: En-tête d'identification exigé par Internet Archive et de bon usage partout ailleurs.
ENTETE_AGENT = {"User-Agent": "BMS-video-factory/1.0 (+contact dans .env FACTORY_CONTACT)"}
#: Sous cette part du plafond horaire restant, on espace les requêtes au lieu de les enchaîner.
SEUIL_RALENTISSEMENT = 0.10
#: Pause appliquée quand on est proche du plafond, en secondes.
PAUSE_PROCHE_LIMITE_S = 2.0

#: Licences acceptées chez Openverse. `by-sa`, `nd` et `nc` sont écartés : partage à l'identique,
#: interdiction de modifier et non-commercial sont tous les trois éliminatoires pour un montage.
LICENCES_OPENVERSE = ("cc0", "pdm", "by")

#: Motifs de `licenseurl` acceptés chez Internet Archive.
LICENCES_ARCHIVE = (
    "creativecommons.org/publicdomain/zero",
    "creativecommons.org/publicdomain/mark",
    "creativecommons.org/licenses/by/",
    "creativecommons.org/licenses/by-sa/",  # accepté en lecture, filtré ensuite par `_licence_ok`
)

#: Vocabulaire qui annonce une personne identifiable — donc un droit à l'image non enregistré.
#: Volontairement large : sur-filtrer coûte un candidat, sous-filtrer coûte un manquement.
MOTS_PERSONNE: frozenset[str] = frozenset({
    "portrait", "portraits", "face", "faces", "facial", "closeup", "close-up", "selfie",
    "model", "models", "woman", "women", "man", "men", "girl", "boy", "child", "children",
    "baby", "person", "people", "couple", "family", "student", "teacher", "worker", "crowd",
    "astronaut", "astronauts", "crew", "smiling", "smile", "posing", "headshot", "influencer",
})

#: Texte d'attribution, par fournisseur (`outils/LICENCES.md` § 3.2). `None` = aucune attribution
#: exigée ; les champs `author` et `source_url` sont enregistrés malgré tout.
GABARITS_ATTRIBUTION: dict[str, str | None] = {
    "pexels": "{genre} by {author} on Pexels — {source_url}",
    "pixabay": None,
    "openverse": "{title} — {author}, via Openverse, {licence} ({licence_url}) — {source_url}",
    "internet_archive": "{title} — {author}, Internet Archive, {licence} — {source_url}",
    "nasa": "Crédit : NASA — {source_url}",
}


#: Dernier compteur restant annoncé par chaque fournisseur, quand il en annonce un. Sert le
#: journal et le manifeste : il confronte notre compte local à celui de la banque.
_dernier_restant: dict[str, str] = {}


class ErreurStock(RuntimeError):
    """Le module ne peut pas travailler : dossier illisible, base indisponible."""


# --------------------------------------------------------------------------------------
# Compteur de quota
# --------------------------------------------------------------------------------------


def dossier_bibliotheque(racine: Path | None = None) -> Path:
    """`workspace/library/stock/` — créé à la demande."""
    dossier = (racine or racine_projet()) / "workspace" / "library" / "stock"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def maintenant() -> str:
    """Horodatage ISO-8601 UTC, comme tous les fichiers du run."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class CompteurQuota:
    """Compteur de requêtes par fournisseur, persistant entre les runs.

    Les banques ne renvoient pas toutes un en-tête de quota restant, et celles qui le font ne le
    font pas sur toutes les routes : **le seul compteur sur lequel on peut s'appuyer est le
    nôtre**. Il est écrit à chaque requête, pas en fin de run : un run interrompu ne doit pas
    faire perdre la trace des requêtes déjà payées.
    """

    chemin: Path
    etat: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)

    @classmethod
    def charger(cls, racine: Path | None = None) -> CompteurQuota:
        chemin = dossier_bibliotheque(racine) / "quotas.json"
        etat: dict = {}
        if chemin.exists():
            try:
                etat = json.loads(chemin.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                etat = {}
        return cls(chemin=chemin, etat=etat)

    @staticmethod
    def _seaux() -> dict[str, str]:
        instant = datetime.now(timezone.utc)
        return {
            "heure": instant.strftime("%Y-%m-%dT%H"),
            "jour": instant.strftime("%Y-%m-%d"),
            "mois": instant.strftime("%Y-%m"),
        }

    def consomme(self, provider: str) -> dict[str, int]:
        """Requêtes déjà envoyées à ce fournisseur, par seau (heure, jour, mois courants)."""
        bloc = self.etat.get(provider, {})
        return {
            periode: bloc.get(periode, {}).get(cle, 0)
            for periode, cle in self._seaux().items()
        }

    def disponible(self, provider: str) -> bool:
        """Faux dès qu'un des plafonds documentés est atteint — horaire, journalier ou mensuel."""
        plafonds = QUOTAS.get(provider, {})
        consomme = self.consomme(provider)
        for periode, plafond in plafonds.items():
            if plafond is not None and consomme.get(periode, 0) >= int(plafond):
                return False
        return True

    def proche_limite(self, provider: str) -> bool:
        """Vrai dans les derniers pour-cent du plafond horaire : on ralentit avant d'y être."""
        plafond = QUOTAS.get(provider, {}).get("heure")
        if plafond is None:
            return False
        par_heure = self.consomme(provider).get("heure", 0)
        return (int(plafond) - par_heure) <= max(1, int(int(plafond) * SEUIL_RALENTISSEMENT))

    def enregistrer(self, provider: str, nombre: int = 1) -> None:
        """Ajoute `nombre` requêtes au fournisseur et écrit le fichier, tout de suite."""
        bloc = self.etat.setdefault(provider, {})
        for periode, cle in self._seaux().items():
            seau = bloc.setdefault(periode, {})
            seau[cle] = seau.get(cle, 0) + nombre
        # Un compteur qui garderait 8 000 seaux horaires deviendrait le plus gros fichier de la
        # bibliothèque : on ne garde que le passé qui sert encore à décider.
        for periode, garde in (("heure", 48), ("jour", 31), ("mois", 13)):
            if periode in bloc:
                bloc[periode] = dict(sorted(bloc[periode].items())[-garde:])
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(
            json.dumps(self.etat, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def resume(self) -> dict[str, dict[str, int | None]]:
        """État lisible du compteur, pour le journal et le manifeste."""
        lignes: dict[str, dict[str, int | None]] = {}
        for provider, plafonds in QUOTAS.items():
            consomme = self.consomme(provider)
            ligne: dict[str, int | None] = {}
            for periode in ("heure", "jour", "mois"):
                ligne[periode] = consomme.get(periode, 0)
                ligne[f"plafond_{periode}"] = plafonds.get(periode)
            lignes[provider] = ligne
        return lignes


# --------------------------------------------------------------------------------------
# Mots-clés : intention visuelle → trois requêtes anglaises
# --------------------------------------------------------------------------------------

#: Ce que le générateur de mots-clés doit produire — et surtout ce qu'il ne doit pas produire.
#: Une banque d'images ne comprend pas une phrase : elle indexe des noms. Une requête de six mots
#: ne rend **rien** chez Pexels là où « roman ruins » rend quatre cents clips.
SYSTEME_MOTS_CLES = (
    "You turn a video shot description into stock-footage search queries.\n"
    "Rules, all mandatory:\n"
    "1. Output ONE line per input, numbered exactly as the input: `1. query | query | query`\n"
    "2. Exactly THREE queries per line, separated by ` | `, ordered from most specific to most "
    "generic.\n"
    "3. Each query is 1 to 3 English words, nouns or adjective+noun. No verbs, no sentences, "
    "no punctuation.\n"
    "4. Describe what a CAMERA would film: places, objects, materials, landscapes, textures, "
    "light.\n"
    "5. Never ask for people, faces, portraits, crowds or named persons.\n"
    "6. Never ask for text, titles, charts, diagrams, logos or screens.\n"
    "7. The third query must be a broad, safe fallback that any stock library holds "
    "(e.g. `stone wall`, `night sky`, `ocean waves`).\n"
    "Answer with the numbered lines and nothing else."
)

#: Taille d'un lot. Chaque appel charge 6,6 Go de poids : grouper divise les chargements.
LOT_MOTS_CLES = 6


def normaliser(texte: str) -> str:
    """Forme canonique d'une requête : accents, casse et ponctuation retirés."""
    sans_accent = unicodedata.normalize("NFKD", texte)
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sans_accent.lower()).strip()


def _requetes_de_repli(intention: str) -> list[str]:
    """Trois requêtes tirées de l'intention elle-même, quand le LLM n'a rien rendu.

    Ce n'est pas une bonne recherche — c'est une recherche **quand même**, et elle vaut mieux
    qu'un plan abandonné parce qu'un sous-processus a échoué.
    """
    mots = [m for m in normaliser(intention).split() if len(m) > 3]
    if not mots:
        return ["abstract texture", "natural landscape", "night sky"]
    return [" ".join(mots[:3]), " ".join(mots[:2]) or mots[0], mots[0]]


def requetes_pour(
    intentions: list[str], racine: Path | None = None, journal: IO[str] | None = None,
) -> dict[str, list[str]]:
    """Intention visuelle → trois requêtes anglaises courtes, par lots, avec le cache LLM.

    L'intention arrive déjà en anglais pour une chaîne anglophone ; elle n'en reste pas moins
    une **phrase**, que les banques n'indexent pas. La traduction n'est donc pas le sujet : la
    réduction en mots-clés l'est, quelle que soit la langue.
    """
    from factory import llm

    base = racine or racine_projet()
    uniques = sorted({i.strip() for i in intentions if i.strip()})
    if not uniques:
        return {}

    sorties: dict[str, list[str]] = {}
    for depart in range(0, len(uniques), LOT_MOTS_CLES):
        lot = uniques[depart : depart + LOT_MOTS_CLES]
        demande = "\n".join(f"{n}. {texte}" for n, texte in enumerate(lot, start=1))
        try:
            reponse = llm.generate(
                demande, system=SYSTEME_MOTS_CLES, max_tokens=40 * len(lot),
                temperature=0.2, seed=23, etiquette="stock_keywords", racine=base,
            )
        except Exception as erreur:  # un lot perdu ne fait pas tomber le run
            if journal is not None:
                journal.write(f"mots-clés : lot {depart // LOT_MOTS_CLES} échoué — {erreur}\n")
            continue
        for ligne in reponse.texte.splitlines():
            trouve = re.match(r"\s*(\d+)[.)]\s*(.+)", ligne.strip())
            if not trouve:
                continue
            rang = int(trouve.group(1)) - 1
            if not 0 <= rang < len(lot):
                continue
            morceaux = [
                normaliser(m)[:60] for m in trouve.group(2).split("|") if normaliser(m)
            ]
            if morceaux:
                sorties[lot[rang]] = morceaux[:REQUETES_PAR_PLAN]

    manquantes = [i for i in uniques if i not in sorties]
    for intention in manquantes:
        sorties[intention] = _requetes_de_repli(intention)
    if journal is not None:
        journal.write(
            f"mots-clés : {len(uniques) - len(manquantes)}/{len(uniques)} intention(s) réduites"
            + (f", {len(manquantes)} par repli lexical" if manquantes else "") + "\n"
        )
        journal.flush()
    return sorties


# --------------------------------------------------------------------------------------
# Candidats
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidat:
    """Un fichier qu'une banque propose, **avant** téléchargement et vérification."""

    provider: str
    identifiant: str
    url_fichier: str
    source_url: str
    author: str
    licence: str
    licence_url: str
    titre: str
    largeur: int
    hauteur: int
    duree_s: float          # 0.0 pour une image fixe
    extension: str
    mots_cles: str = ""
    #: Ligne d'attribution **fournie par la banque**. Elle prime sur le gabarit local : quand une
    #: banque compose elle-même le texte que la licence exige, le recomposer c'est le réécrire.
    attribution: str | None = None

    @property
    def est_video(self) -> bool:
        return self.extension in {"mp4", "mov", "m4v", "webm"}

    @property
    def cle(self) -> str:
        return f"{self.provider}:{self.identifiant}"


def sans_balises(texte: str) -> str:
    """Retire le HTML d'un titre de banque.

    Openverse recopie le champ de sa source telle quelle : un titre Wikimedia arrive en
    `<div class='fn'>Roman Ruins</div>`. Non nettoyé, il part **tel quel** dans la description
    YouTube, où il ne serait pas interprété mais lu (relevé le 18/09/2026 sur `q=roman ruins`).
    """
    sans = re.sub(r"<[^>]+>", " ", texte or "")
    return re.sub(r"\s+", " ", sans).strip()


def _licence_ok(licence: str) -> bool:
    """Licences employables dans un montage commercial modifié.

    « NC » et « ND » sont éliminatoires par définition ; **« SA » l'est par décision de projet**
    (`outils/LICENCES.md`) : une clause de partage à l'identique contaminerait la vidéo entière,
    ce qu'aucune chaîne monétisée ne peut assumer.
    """
    jetons = {j for j in licence.upper().replace("_", "-").replace(" ", "-").split("-") if j}
    return not ({"NC", "ND", "SA"} & jetons)


def _annonce_une_personne(candidat: Candidat) -> bool:
    """Le titre ou les mots-clés annoncent-ils une personne identifiable ?

    Plancher lexical, pas une détection : il voit « portrait of a woman », il ne voit pas un
    visage au fond d'un plan large. Ce que le vocabulaire laisse passer est rattrapé par la
    relecture visuelle (`person_review`), jamais ignoré.
    """
    mots = set(normaliser(f"{candidat.titre} {candidat.mots_cles}").split())
    return bool(mots & MOTS_PERSONNE)


# --------------------------------------------------------------------------------------
# Fournisseurs
# --------------------------------------------------------------------------------------


def _json(url: str, entetes: dict[str, str] | None = None,
          parametres: dict[str, object] | None = None) -> tuple[dict, dict]:
    """Une requête GET JSON. Rend `(charge, en-têtes)` : le compteur restant est dans les seconds.

    L'en-tête d'agent n'est pas une politesse : Internet Archive l'**exige** et sanctionne les
    clients anonymes. Il ne porte aucune donnée personnelle, seulement le nom de l'outil.
    """
    reponse = requests.get(url, headers={**ENTETE_AGENT, **(entetes or {})},
                           params=parametres or {}, timeout=TIMEOUT_S)
    reponse.raise_for_status()
    return reponse.json(), dict(reponse.headers)


def chercher_pexels(requete: str, cle: str) -> list[Candidat]:
    """Vidéos Pexels en paysage. `Authorization: <clé>`, jamais la clé dans l'URL."""
    charge, entetes = _json(
        "https://api.pexels.com/videos/search", entetes={"Authorization": cle},
        parametres={"query": requete, "orientation": "landscape", "size": "medium",
                    "per_page": PAR_PAGE},
    )
    restant = entetes.get("X-Ratelimit-Remaining")
    if restant is not None:
        # Le seul fournisseur qui publie son compteur : il fait foi sur le nôtre.
        _dernier_restant["pexels"] = restant
    candidats: list[Candidat] = []
    for video in charge.get("videos", []):
        fichiers = [
            f for f in video.get("video_files", [])
            if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")
        ]
        if not fichiers:
            continue
        # Le plus petit fichier qui tient le contrat : un 4K coûte 80 Mo pour une vidéo qui
        # sortira en 1080p de toute façon.
        conformes = [f for f in fichiers
                     if int(f["width"]) >= LARGEUR_MIN and int(f["height"]) >= HAUTEUR_MIN]
        if not conformes:
            continue
        fichier = min(conformes, key=lambda f: int(f["width"]) * int(f["height"]))
        auteur = (video.get("user") or {}).get("name") or "Pexels"
        candidats.append(Candidat(
            provider="pexels", identifiant=str(video.get("id")),
            url_fichier=str(fichier["link"]), source_url=str(video.get("url") or ""),
            author=str(auteur), licence="Pexels-License",
            licence_url="https://www.pexels.com/license/",
            titre=str(video.get("alt") or ""), largeur=int(fichier["width"]),
            hauteur=int(fichier["height"]), duree_s=float(video.get("duration") or 0.0),
            extension="mp4", mots_cles=requete,
        ))
    return candidats


def chercher_pixabay(requete: str, cle: str) -> list[Candidat]:
    """Vidéos Pixabay. Le cache 24 h exigé par les conditions est tenu par la bibliothèque."""
    charge, entetes = _json(
        "https://pixabay.com/api/videos/",
        parametres={"key": cle, "q": requete, "video_type": "film", "per_page": PAR_PAGE,
                    "safesearch": "true", "order": "popular",
                    "min_width": LARGEUR_MIN, "min_height": HAUTEUR_MIN},
    )
    restant = entetes.get("X-RateLimit-Remaining")
    if restant is not None:
        _dernier_restant["pixabay"] = restant
    candidats: list[Candidat] = []
    for hit in charge.get("hits", []):
        flux = hit.get("videos") or {}
        conformes = [
            f for f in flux.values()
            if isinstance(f, dict) and int(f.get("width") or 0) >= LARGEUR_MIN
            and int(f.get("height") or 0) >= HAUTEUR_MIN and f.get("url")
        ]
        if not conformes:
            continue
        fichier = min(conformes, key=lambda f: int(f["width"]) * int(f["height"]))
        candidats.append(Candidat(
            provider="pixabay", identifiant=str(hit.get("id")),
            url_fichier=str(fichier["url"]), source_url=str(hit.get("pageURL") or ""),
            author=str(hit.get("user") or "Pixabay"), licence="Pixabay-Content-License",
            licence_url="https://pixabay.com/service/terms/",
            titre=str(hit.get("tags") or ""), largeur=int(fichier["width"]),
            hauteur=int(fichier["height"]), duree_s=float(hit.get("duration") or 0.0),
            extension="mp4", mots_cles=str(hit.get("tags") or ""),
        ))
    return candidats


def _etiquette_licence_cc(code: str, version: str) -> str:
    """`cc0` + `1.0` → `CC0-1.0` ; `by` + `4.0` → `CC-BY-4.0` ; `pdm` → `PDM-1.0`."""
    code = code.lower()
    if code == "cc0":
        return f"CC0-{version or '1.0'}"
    if code == "pdm":
        return f"PDM-{version or '1.0'}"
    return f"CC-{code.upper()}-{version}".rstrip("-")


def chercher_openverse(requete: str) -> list[Candidat]:
    """Images Openverse — le service n'indexe aucune vidéo, et c'est assumé ici.

    `license=cc0,pdm,by` **et** re-vérification locale : la documentation reconnaît que le
    service « does not verify its licensing status », donc le paramètre ne suffit pas.
    """
    charge, entetes = _json(
        "https://api.openverse.org/v1/images/",
        parametres={"q": requete, "license": ",".join(LICENCES_OPENVERSE),
                    "aspect_ratio": "wide", "size": "large",
                    "page_size": PAR_PAGE, "mature": "false"},
    )
    restant = entetes.get("x-ratelimit-available-anon_sustained")
    if restant is not None:
        _dernier_restant["openverse"] = f"{restant}/jour"
    candidats: list[Candidat] = []
    for item in charge.get("results", []):
        largeur, hauteur = int(item.get("width") or 0), int(item.get("height") or 0)
        if largeur < LARGEUR_MIN or hauteur < HAUTEUR_MIN:
            continue
        licence = str(item.get("license") or "")
        if licence.lower() not in LICENCES_OPENVERSE:
            continue
        mots = " ".join(t.get("name", "") for t in (item.get("tags") or [])
                        if isinstance(t, dict))
        candidats.append(Candidat(
            provider="openverse", identifiant=str(item.get("id")),
            url_fichier=str(item.get("url") or ""),
            source_url=str(item.get("foreign_landing_url") or item.get("url") or ""),
            author=str(item.get("creator") or "inconnu"),
            # `cc0` et `pdm` ne sont pas des licences « CC-… » : les préfixer rendait
            # « CC-CC0-1.0 » dans le registre de licences, un libellé qui n'existe pas.
            licence=_etiquette_licence_cc(licence, str(item.get("license_version") or "")),
            licence_url=str(item.get("license_url") or "https://creativecommons.org/"),
            titre=sans_balises(str(item.get("title") or "")),
            largeur=largeur, hauteur=hauteur, duree_s=0.0,
            extension=str(item.get("filetype") or "jpg").lower(), mots_cles=mots,
            # Openverse **compose lui-même** la ligne d'attribution due, et c'est celle-là qui
            # fait foi : la recomposer à partir des champs perdrait la mention de la version de
            # licence et la phrase « To view a copy of this license… » que CC exige.
            attribution=sans_balises(str(item.get("attribution") or "")) or None,
        ))
    return candidats


def chercher_archive(requete: str, duree_min_s: float) -> list[Candidat]:
    """Films du domaine public d'Internet Archive, licence **explicite** seulement."""
    recherche, _ = _json(
        "https://archive.org/advancedsearch.php",
        parametres={
            "q": f'({requete}) AND mediatype:(movies) AND licenseurl:(*creativecommons*)',
            "fl[]": ["identifier", "title", "creator", "licenseurl"],
            "rows": 8, "output": "json", "sort[]": "downloads desc",
        },
    )
    candidats: list[Candidat] = []
    for doc in recherche.get("response", {}).get("docs", []):
        licence_url = doc.get("licenseurl") or ""
        licence_url = licence_url[0] if isinstance(licence_url, list) else licence_url
        if not any(motif in str(licence_url) for motif in LICENCES_ARCHIVE):
            continue
        identifiant = str(doc.get("identifier"))
        try:
            meta, _ = _json(f"https://archive.org/metadata/{identifiant}")
        except requests.RequestException:
            continue
        for fichier in meta.get("files", []):
            if not str(fichier.get("name", "")).lower().endswith(".mp4"):
                continue
            largeur, hauteur = int(fichier.get("width") or 0), int(fichier.get("height") or 0)
            duree = _duree_archive(fichier.get("length"))
            if largeur < LARGEUR_MIN or hauteur < HAUTEUR_MIN or duree < duree_min_s:
                continue
            # Le catalogue d'Archive est fait de **longs métrages** : mesuré le 18/09/2026,
            # « roman forum » rend des films de 5 187 et 5 782 s. Sans ce filtre, chacun était
            # téléchargé jusqu'au plafond de 120 Mo puis jeté — le coût d'un candidat refusé
            # devenait celui d'un candidat accepté. `size` est déjà dans la métadonnée : gratuit.
            if int(fichier.get("size") or 0) > TAILLE_MAXIMALE_OCTETS:
                continue
            titre = doc.get("title") or identifiant
            candidats.append(Candidat(
                provider="internet_archive", identifiant=f"{identifiant}_{fichier['name']}",
                url_fichier=f"https://archive.org/download/{identifiant}/{fichier['name']}",
                source_url=f"https://archive.org/details/{identifiant}",
                author=str(doc.get("creator") or "Internet Archive"),
                licence=_licence_depuis_url(str(licence_url)), licence_url=str(licence_url),
                titre=sans_balises(str(titre)), largeur=largeur, hauteur=hauteur,
                duree_s=duree, extension="mp4", mots_cles=str(titre),
            ))
            break  # un fichier par item : les dérivés se ressemblent trop pour en prendre deux
    return candidats


def _duree_archive(valeur: object) -> float:
    """`length` d'Internet Archive : « 123.45 » ou « 00:02:03 », selon le dérivé."""
    if valeur is None:
        return 0.0
    texte = str(valeur)
    if ":" in texte:
        morceaux = [float(m) for m in texte.split(":") if m.replace(".", "").isdigit()]
        secondes = 0.0
        for morceau in morceaux:
            secondes = secondes * 60 + morceau
        return secondes
    try:
        return float(texte)
    except ValueError:
        return 0.0


def _licence_depuis_url(url: str) -> str:
    """`https://creativecommons.org/licenses/by/4.0/` → `CC-BY-4.0`."""
    trouve = re.search(r"licenses/([a-z-]+)/([\d.]+)", url)
    if trouve:
        return f"CC-{trouve.group(1).upper()}-{trouve.group(2)}"
    if "publicdomain/zero" in url:
        return "CC0-1.0"
    if "publicdomain/mark" in url:
        return "PDM-1.0"
    return "domaine-public"


#: Nombre d'items vidéo de la NASA dont on va lire le `collection.json`. Chaque lecture est un
#: fichier statique sur `images-assets.nasa.gov`, pas un appel d'API — elle ne consomme pas de
#: quota — mais elle coûte un aller-retour, d'où le plafond bas.
NASA_VIDEOS_SONDEES = 3


def chercher_nasa_video(requete: str) -> list[Candidat]:
    """Vidéos de images.nasa.gov — **la seule source de métrage réel sans clé**.

    La recherche ne décrit pas les fichiers : `links[]` ne porte qu'une vignette pour un item
    vidéo. Les dérivés (`~orig.mp4`, `~mobile.mp4`, `~preview.mp4`) sont listés par le
    `collection.json` de l'item, et **leur poids va de 16 Mo à 1,2 Go** (mesuré le 18/09/2026 :
    `GSFC_20141113_Volcanoes…Deg` 1920×1080 10 s 16,7 Mo · `JPL-20240710-Perseverance…`
    3840×2160 125 s 1 184 Mo). Un `HEAD` tranche avant de télécharger : sans lui, un candidat
    hors gabarit coûte les 120 Mo du plafond.

    Le `href` de l'item contient des espaces et des apostrophes non échappés — `urlopen` et
    `requests` le refusent tel quel ; il est requoté.
    """
    charge, _ = _json(
        "https://images-api.nasa.gov/search",
        parametres={"q": requete, "media_type": "video", "page_size": PAR_PAGE},
    )
    candidats: list[Candidat] = []
    for item in charge.get("collection", {}).get("items", []):
        if len(candidats) >= NASA_VIDEOS_SONDEES:
            break
        donnees = (item.get("data") or [{}])[0]
        href = str(item.get("href") or "")
        if not href:
            continue
        decoupe = urlsplit(href)
        href = urlunsplit(decoupe._replace(scheme="https", path=quote(decoupe.path, safe="/")))
        try:
            fichiers = requests.get(href, timeout=TIMEOUT_S, headers=ENTETE_AGENT).json()
        except (requests.RequestException, ValueError):
            continue
        mp4 = [str(u).replace("http://", "https://") for u in fichiers
               if str(u).lower().endswith(".mp4")]
        if not mp4:
            continue
        # `~orig` d'abord : c'est le seul dérivé dont la définition tient le 1080p. Les autres
        # sont des réductions (`~mobile` mesuré à 320×212 sur `ksc_080504_apollo`).
        url = next((u for u in mp4 if "~orig" in u), mp4[0])
        url = urlunsplit(urlsplit(url)._replace(path=quote(urlsplit(url).path, safe="/")))
        try:
            tete = requests.head(url, timeout=TIMEOUT_S, headers=ENTETE_AGENT,
                                 allow_redirects=True)
            poids = int(tete.headers.get("content-length") or 0)
        except (requests.RequestException, ValueError):
            continue
        if not poids or poids > TAILLE_MAXIMALE_OCTETS:
            continue
        nasa_id = str(donnees.get("nasa_id") or "")
        auteur = (donnees.get("photographer") or donnees.get("secondary_creator")
                  or donnees.get("center") or "NASA")
        candidats.append(Candidat(
            provider="nasa", identifiant=nasa_id, url_fichier=url,
            source_url=f"https://images.nasa.gov/details/{nasa_id}",
            author=str(auteur), licence="domaine-public-US",
            licence_url="https://www.nasa.gov/nasa-brand-center/images-and-media/",
            titre=sans_balises(str(donnees.get("title") or "")),
            # Définition et durée ne sont annoncées nulle part : `_mesure_conforme` les constate
            # après téléchargement, et le fichier est effacé s'il ne tient pas le contrat.
            largeur=0, hauteur=0, duree_s=0.0,
            extension="mp4", mots_cles=" ".join(donnees.get("keywords") or []),
        ))
    return candidats


def chercher_nasa(requete: str) -> list[Candidat]:
    """Images de images.nasa.gov — domaine public américain, crédit « NASA ».

    `links[]` porte les dérivés **avec leurs dimensions**, et le `rel: canonical` est l'original
    (`…~orig.jpg`) : aucune requête supplémentaire vers `/asset/{nasa_id}` n'est nécessaire, ce
    qui divise par deux le coût de ce fournisseur. Relevé le 18/09/2026 sur `q=roman ruins` —
    `~orig.jpg` à 4048×3824, `~large.jpg` à 1920×1813.
    """
    charge, _ = _json(
        "https://images-api.nasa.gov/search",
        parametres={"q": requete, "media_type": "image", "page_size": PAR_PAGE},
    )
    candidats: list[Candidat] = []
    for item in charge.get("collection", {}).get("items", [])[:PAR_PAGE]:
        donnees = (item.get("data") or [{}])[0]
        fichiers = [
            l for l in (item.get("links") or [])
            if l.get("render") == "image" and l.get("href")
            and int(l.get("width") or 0) >= LARGEUR_MIN
            and int(l.get("height") or 0) >= HAUTEUR_MIN
        ]
        if not fichiers:
            continue
        # Le plus petit qui tient le contrat : l'original NASA pèse couramment 2,5 Mo pour une
        # image qui sortira recadrée en 1080p.
        fichier = min(fichiers, key=lambda l: int(l["width"]) * int(l["height"]))
        nasa_id = str(donnees.get("nasa_id") or "")
        auteur = (donnees.get("photographer") or donnees.get("secondary_creator")
                  or donnees.get("center") or "NASA")
        candidats.append(Candidat(
            provider="nasa", identifiant=nasa_id,
            url_fichier=str(fichier["href"]).replace("http://", "https://"),
            source_url=f"https://images.nasa.gov/details/{nasa_id}",
            author=str(auteur), licence="domaine-public-US",
            licence_url="https://www.nasa.gov/nasa-brand-center/images-and-media/",
            titre=sans_balises(str(donnees.get("title") or "")),
            largeur=int(fichier["width"]), hauteur=int(fichier["height"]), duree_s=0.0,
            extension="jpg", mots_cles=" ".join(donnees.get("keywords") or []),
        ))
    return candidats


# --------------------------------------------------------------------------------------
# Bibliothèque
# --------------------------------------------------------------------------------------


def cle_requete(requete: str) -> str:
    """Clé de cache d'une requête : `sha256(requête normalisée)[:16]`."""
    return hashlib.sha256(normaliser(requete).encode("utf-8")).hexdigest()[:16]


def _reutilisable(
    conn: sqlite3.Connection, asset_id: str, channel: Channel, video_id: str,
    deja_dans_ce_run: set[str],
) -> tuple[bool, str]:
    """Cet asset de banque peut-il servir ce plan ?

    **La règle diffère de celle des images générées, et l'écart est voulu.** Deux plans peuvent
    partager une image générée — c'est même ce qui fait tomber le coût du moteur illustré. Deux
    plans ne partagent **jamais** un clip de banque : le spectateur reconnaît un plan réel revu
    dix minutes plus tard, là où il ne reconnaît pas deux fois le même aplat vectoriel.
    """
    if asset_id in deja_dans_ce_run:
        return False, "déjà employé dans cette vidéo"
    if conn.execute(
        "SELECT 1 FROM library_uses WHERE asset_id = ? AND video_id = ?", (asset_id, video_id)
    ).fetchone():
        return False, "déjà employé dans cette vidéo"

    usages = [
        ligne["video_id"] for ligne in conn.execute(
            "SELECT video_id FROM library_uses WHERE asset_id = ? AND channel_id = ? "
            "ORDER BY used_at DESC", (asset_id, channel.id),
        )
    ]
    if len(usages) >= channel.library.max_uses_per_channel:
        return False, f"max_uses_per_channel atteint ({len(usages)})"
    if usages and channel.library.cooldown_videos:
        recents = [
            ligne["video_id"] for ligne in conn.execute(
                "SELECT DISTINCT video_id FROM library_uses WHERE channel_id = ? "
                "ORDER BY used_at DESC LIMIT ?", (channel.id, channel.library.cooldown_videos),
            )
        ]
        if set(usages) & set(recents):
            return False, f"employé dans les {channel.library.cooldown_videos} derniers runs"
    return True, "libre"


def _inscrire(
    conn: sqlite3.Connection, asset: Asset, chemin: Path, requete: str,
    channel: Channel, video_id: str, racine: Path,
) -> None:
    """Index `library_assets` (kind = `stock`) + trace d'emploi, toutes deux idempotentes."""
    conn.execute(
        "INSERT INTO library_assets (asset_id, kind, layer, path, provider, licence, licence_url,"
        " attribution_line, person_release, has_text, lang, keywords, phash, prompt_key, uses,"
        " created_at, last_used_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)"
        " ON CONFLICT(asset_id) DO UPDATE SET last_used_at = excluded.last_used_at",
        (
            asset.asset_id, "stock", "background", str(chemin.relative_to(racine)),
            asset.provider, asset.licence, asset.licence_url, asset.attribution_line,
            asset.person_release, int(asset.has_text),
            # Un plan de banque ne porte pas de lettrage : il franchit la frontière de langue.
            None, requete, None, cle_requete(requete), maintenant(), maintenant(),
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


def _ligne_attribution(candidat: Candidat) -> str | None:
    """Texte d'attribution exact du fournisseur (`outils/LICENCES.md` § 3.2)."""
    if candidat.attribution:
        return candidat.attribution
    gabarit = GABARITS_ATTRIBUTION.get(candidat.provider)
    if gabarit is None:
        return None
    return gabarit.format(
        genre="Vidéo" if candidat.est_video else "Photo",
        author=candidat.author, source_url=candidat.source_url,
        title=candidat.titre or candidat.identifiant, licence=candidat.licence,
        licence_url=candidat.licence_url,
    ).strip()


# --------------------------------------------------------------------------------------
# Banque
# --------------------------------------------------------------------------------------


@dataclass
class ResultatStock:
    """Un asset de banque servi à un plan, et d'où il vient."""

    chemin: Path
    asset: Asset
    provider: str
    est_video: bool
    depuis_cache: bool
    requete: str
    secondes: float = 0.0


@dataclass
class BanqueStock:
    """Sert un asset réel par plan, en descendant la chaîne de fournisseurs.

    L'instance vit le temps d'un `prepare_assets` : elle porte le compteur de quota, la
    connexion à l'index et l'ensemble des assets déjà employés **dans cette vidéo**.
    """

    conn: sqlite3.Connection
    racine: Path = field(default_factory=racine_projet)
    journal: IO[str] | None = None
    chaine: tuple[str, ...] = CHAINE_DEFAUT
    compteur: CompteurQuota | None = None
    #: Intention de plan → requêtes anglaises (`requetes_pour`), remplie avant la boucle de plans.
    requetes: dict[str, list[str]] = field(default_factory=dict)
    #: `asset_id` déjà servis dans cette vidéo : un clip réel ne s'y montre jamais deux fois.
    employes: set[str] = field(default_factory=set)
    #: Compte des recherches par fournisseur et des replis, relu par le manifeste.
    stats: dict[str, int] = field(default_factory=dict)
    #: Poids de la bibliothèque en octets, mesuré à la première vérification de budget.
    _poids_bibliotheque: int | None = None
    #: Réemploi sémantique (étape 29) : index `kind = stock`, intentions encodées. `None` = off.
    semantique: Any = None

    def __post_init__(self) -> None:
        if self.compteur is None:
            self.compteur = CompteurQuota.charger(self.racine)

    def tracer(self, message: str) -> None:
        if self.journal is not None:
            self.journal.write(message.rstrip() + "\n")
            self.journal.flush()

    # -- clés ----------------------------------------------------------------------------

    @staticmethod
    def cle_api(provider: str) -> str | None:
        """Clé du fournisseur, lue dans l'environnement (`.env`). Jamais journalisée."""
        return os.environ.get({"pexels": "PEXELS_KEY", "pixabay": "PIXABAY_KEY"}.get(provider, ""))

    def fournisseurs_actifs(self) -> list[str]:
        """Fournisseurs interrogeables, **métrage d'abord quand aucune clé n'est posée**.

        L'ordre nominal (`params.stock.providers`) commence par les deux banques vidéo à clé.
        Sans `PEXELS_KEY` ni `PIXABAY_KEY`, il ne reste devant qu'Openverse, qui n'indexe que des
        images : toutes les banques de vidéo passeraient alors **après** une banque qui répond
        presque toujours, et le style documentaire sortirait en diaporama — un doublon visuel du
        style illustré sur des photographies au lieu d'images générées (`STATE.md`, 18/09/2026).

        Dans ce seul cas, Internet Archive et la NASA repassent devant Openverse. Ils rendent
        peu, et c'est assumé : un plan de métrage réel vaut mieux qu'une photographie animée, et
        ce qu'ils ne servent pas retombe sur Openverse à la ligne suivante, sans requête perdue.
        """
        actifs = []
        for provider in self.chaine:
            if provider in {"pexels", "pixabay"} and not self.cle_api(provider):
                continue
            actifs.append(provider)
        if not ({"pexels", "pixabay"} & set(actifs)):
            rang = {p: i for i, p in enumerate(actifs)}
            actifs.sort(key=lambda p: (p in IMAGES_SEULEMENT, rang[p]))
        return actifs

    # -- recherche -----------------------------------------------------------------------

    def _chercher(self, provider: str, requete: str, duree_min_s: float) -> list[Candidat]:
        """Une requête chez un fournisseur, comptée avant d'être envoyée."""
        assert self.compteur is not None
        if not self.compteur.disponible(provider):
            self.tracer(f"stock : {provider} — quota atteint, fournisseur sauté")
            return []
        if self.compteur.proche_limite(provider):
            self.tracer(f"stock : {provider} — proche du plafond horaire, pause "
                        f"{PAUSE_PROCHE_LIMITE_S:.0f} s")
            time.sleep(PAUSE_PROCHE_LIMITE_S)
        self.compteur.enregistrer(provider)
        self.stats[f"requetes_{provider}"] = self.stats.get(f"requetes_{provider}", 0) + 1
        try:
            if provider == "pexels":
                return chercher_pexels(requete, self.cle_api("pexels") or "")
            if provider == "pixabay":
                return chercher_pixabay(requete, self.cle_api("pixabay") or "")
            if provider == "openverse":
                return chercher_openverse(requete)
            if provider == "internet_archive":
                return chercher_archive(requete, duree_min_s)
            if provider == "nasa":
                # Le métrage d'abord, les photographies ensuite : la NASA est, sans clé Pexels
                # ni Pixabay, la seule banque de la chaîne qui rende de la vidéo exploitable.
                # Deux recherches d'API, donc deux unités de quota.
                videos = chercher_nasa_video(requete)
                self.compteur.enregistrer("nasa")
                self.stats["requetes_nasa"] = self.stats.get("requetes_nasa", 0) + 1
                return videos + chercher_nasa(requete)
        except requests.RequestException as erreur:
            self.tracer(f"stock : {provider} « {requete} » — {type(erreur).__name__} {erreur}")
        except (ValueError, KeyError, TypeError) as erreur:
            self.tracer(f"stock : {provider} « {requete} » — réponse inattendue : {erreur}")
        return []

    def _recevable(self, candidat: Candidat, duree_min_s: float) -> tuple[bool, str]:
        """Critères du projet, appliqués **avant** le téléchargement quand la banque les donne."""
        if not _licence_ok(candidat.licence):
            return False, f"licence {candidat.licence}"
        if _annonce_une_personne(candidat):
            return False, "personne annoncée par le titre ou les mots-clés"
        if candidat.largeur and candidat.hauteur:
            if candidat.largeur < LARGEUR_MIN or candidat.hauteur < HAUTEUR_MIN:
                return False, f"{candidat.largeur}×{candidat.hauteur} sous 1080p"
            # Le ratio n'est exigé que d'une **vidéo** : elle est recadrée telle quelle. Une
            # image fixe de 4000×3000 donne 4000×2250 une fois recadrée en 16:9, avec la marge
            # que le Ken Burns réclame — et la moitié du catalogue d'Openverse est en 4:3.
            if candidat.est_video and candidat.largeur / candidat.hauteur < RATIO_MIN:
                return False, "cadre non paysage"
        if candidat.est_video and candidat.duree_s and candidat.duree_s < duree_min_s:
            return False, f"{candidat.duree_s:.1f} s < {duree_min_s:.1f} s"
        return True, "recevable"

    # -- cache ---------------------------------------------------------------------------

    def _depuis_bibliotheque(
        self, requetes: list[str], channel: Channel, video_id: str, duree_min_s: float,
    ) -> ResultatStock | None:
        """Un asset déjà téléchargé pour l'une de ces requêtes, s'il est libre.

        C'est le cache : aucune requête réseau, aucun quota consommé, aucun octet téléchargé.
        """
        for requete in requetes:
            lignes = self.conn.execute(
                "SELECT asset_id, path FROM library_assets WHERE kind = 'stock' AND "
                "prompt_key = ? ORDER BY uses ASC, last_used_at ASC", (cle_requete(requete),),
            ).fetchall()
            for ligne in lignes:
                chemin = self.racine / str(ligne["path"])
                licence = chemin.with_suffix(".json")
                if not chemin.exists() or not licence.exists():
                    continue
                libre, motif = _reutilisable(
                    self.conn, str(ligne["asset_id"]), channel, video_id, self.employes
                )
                if not libre:
                    continue
                asset = Asset.model_validate_json(licence.read_text(encoding="utf-8"))
                if chemin.suffix == ".mp4" and not self._assez_longue(chemin, duree_min_s):
                    continue
                self.employes.add(asset.asset_id)
                _inscrire(self.conn, asset, chemin, requete, channel, video_id, self.racine)
                self.stats["cache"] = self.stats.get("cache", 0) + 1
                self.tracer(f"stock : bibliothèque {asset.provider}/{asset.asset_id} "
                            f"« {requete} » ({motif})")
                return ResultatStock(
                    chemin=chemin, asset=asset, provider=asset.provider,
                    est_video=chemin.suffix == ".mp4", depuis_cache=True, requete=requete,
                )
        return None

    def _reemploi_semantique(
        self, shot: Shot, intention: str, channel: Channel, video_id: str, duree_min_s: float,
    ) -> ResultatStock | None:
        """Un asset déjà téléchargé dont la description paraphrase l'intention (étape 29)."""
        from factory import library

        def libre(asset_id: str) -> tuple[bool, str]:
            ok, motif = _reutilisable(self.conn, asset_id, channel, video_id, self.employes)
            if ok:
                ligne = self.conn.execute(
                    "SELECT path FROM library_assets WHERE asset_id = ?", (asset_id,)).fetchone()
                chemin = self.racine / str(ligne["path"])
                if chemin.suffix == ".mp4" and not self._assez_longue(chemin, duree_min_s):
                    return False, "trop courte"
            return ok, motif

        trouve = library.reemploi_semantique(
            self.conn, self.semantique, intention, seuil=channel.library.semantic_threshold,
            libre=libre, deja_dans_run=self.employes, video_id=video_id, shot_id=shot.id,
            kind="stock",
        )
        if trouve is None:
            return None
        asset_id, relatif, score = trouve
        chemin = self.racine / relatif
        asset = Asset.model_validate_json(chemin.with_suffix(".json").read_text(encoding="utf-8"))
        self.employes.add(asset.asset_id)
        _inscrire(self.conn, asset, chemin, intention, channel, video_id, self.racine)
        self.stats["semantique"] = self.stats.get("semantique", 0) + 1
        self.tracer(f"stock : réemploi sémantique {asset.provider}/{asset.asset_id} "
                    f"(similarité {score:.3f}) pour « {intention[:80]} »")
        return ResultatStock(chemin=chemin, asset=asset, provider=asset.provider,
                             est_video=chemin.suffix == ".mp4", depuis_cache=True,
                             requete=intention)

    def _assez_longue(self, chemin: Path, duree_min_s: float) -> bool:
        from factory import video as video_module

        try:
            return video_module.ffprobe_clip(chemin).duree_s >= duree_min_s
        except Exception:
            return False

    # -- téléchargement ------------------------------------------------------------------

    def _telecharger(self, candidat: Candidat, duree_min_s: float) -> Path | None:
        """Écrit le fichier en bibliothèque, puis le **mesure**. Hors contrat, il est effacé."""
        dossier = dossier_bibliotheque(self.racine) / candidat.provider
        dossier.mkdir(parents=True, exist_ok=True)
        if self._budget_depasse():
            return None
        nom = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidat.identifiant)[:80]
        destination = dossier / f"{nom}.{candidat.extension}"
        if destination.exists() and destination.stat().st_size >= TAILLE_MINIMALE_OCTETS:
            return destination
        try:
            reponse = requests.get(candidat.url_fichier, timeout=TIMEOUT_S, stream=True)
            reponse.raise_for_status()
            octets = 0
            with destination.open("wb") as sortie:
                for morceau in reponse.iter_content(chunk_size=262144):
                    octets += len(morceau)
                    if octets > TAILLE_MAXIMALE_OCTETS:
                        raise ValueError(f"fichier > {TAILLE_MAXIMALE_OCTETS // 1024 // 1024} Mo")
                    sortie.write(morceau)
        except (requests.RequestException, ValueError, OSError) as erreur:
            destination.unlink(missing_ok=True)
            self.tracer(f"stock : téléchargement {candidat.cle} échoué — {erreur}")
            return None
        if destination.stat().st_size < TAILLE_MINIMALE_OCTETS:
            destination.unlink(missing_ok=True)
            self.tracer(f"stock : {candidat.cle} — fichier trop petit, écarté")
            return None
        if not self._mesure_conforme(destination, candidat, duree_min_s):
            destination.unlink(missing_ok=True)
            return None
        if self._poids_bibliotheque is not None:
            self._poids_bibliotheque += destination.stat().st_size
        return destination

    def _budget_depasse(self) -> bool:
        """La bibliothèque a-t-elle atteint son plafond ? Mesuré une fois, puis mémorisé."""
        if self._poids_bibliotheque is None:
            dossier = dossier_bibliotheque(self.racine)
            self._poids_bibliotheque = sum(
                f.stat().st_size for f in dossier.rglob("*") if f.is_file()
            ) if dossier.exists() else 0
        if self._poids_bibliotheque < BUDGET_BIBLIOTHEQUE_OCTETS:
            return False
        if not self.stats.get("budget_atteint"):
            self.tracer(
                f"stock : bibliothèque à {self._poids_bibliotheque / 1e9:.2f} Go — plafond "
                f"atteint, plus aucun téléchargement, les plans restants iront au repli"
            )
        self.stats["budget_atteint"] = self.stats.get("budget_atteint", 0) + 1
        return True

    def _mesure_conforme(self, chemin: Path, candidat: Candidat, duree_min_s: float) -> bool:
        """Mesure réelle du fichier : la banque annonce, `ffprobe` et Pillow constatent."""
        from factory import video as video_module

        try:
            if candidat.est_video:
                info = video_module.ffprobe_clip(chemin)
                largeur, hauteur, duree = info.largeur, info.hauteur, info.duree_s
                if duree < duree_min_s:
                    self.tracer(f"stock : {candidat.cle} mesuré {duree:.1f} s "
                                f"< {duree_min_s:.1f} s — écarté")
                    return False
            else:
                from PIL import Image

                with Image.open(chemin) as image:
                    largeur, hauteur = image.size
        except Exception as erreur:
            self.tracer(f"stock : {candidat.cle} illisible — {erreur}")
            return False
        if largeur < LARGEUR_MIN or hauteur < HAUTEUR_MIN:
            self.tracer(f"stock : {candidat.cle} mesuré {largeur}×{hauteur} — sous 1080p, écarté")
            return False
        if candidat.est_video and largeur / max(hauteur, 1) < RATIO_MIN:
            self.tracer(f"stock : {candidat.cle} mesuré {largeur}×{hauteur} — non paysage")
            return False
        return True

    def _ecrire_licence(self, chemin: Path, candidat: Candidat) -> Asset:
        """`<id>.json` à côté du fichier : même contrat que `assets/<shot>/licence.json`."""
        asset = Asset(
            asset_id=hashlib.sha256(chemin.read_bytes()).hexdigest()[:16],
            path=str(chemin.relative_to(self.racine)),
            provider=candidat.provider,  # type: ignore[arg-type]
            source_url=candidat.source_url or candidat.url_fichier,
            author=candidat.author or candidat.provider,
            licence=candidat.licence, licence_url=candidat.licence_url,
            attribution_line=_ligne_attribution(candidat),
            downloaded_at=maintenant(),
            # Aucune autorisation de droit à l'image n'est enregistrée pour un asset de banque :
            # le champ reste nul et le filtre lexical garantit qu'aucune personne n'est annoncée.
            person_release=None, generator=None,
            realistic=True,       # c'est du réel : le drapeau doit le dire
            has_text=False, c2pa_present=False,
        )
        chemin.with_suffix(".json").write_text(
            json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return asset

    # -- service d'un plan ---------------------------------------------------------------

    def asset_pour(
        self, shot: Shot, channel: Channel, video_id: str,
    ) -> ResultatStock | None:
        """L'asset d'un plan : bibliothèque d'abord, puis la chaîne de banques. `None` = repli."""
        depart = time.perf_counter()
        intention = shot.asset_request.prompt_or_keywords.strip()
        requetes = self.requetes.get(intention) or _requetes_de_repli(intention)
        duree_min_s = shot.duration_s + MARGE_DUREE_S

        cache = self._depuis_bibliotheque(requetes, channel, video_id, duree_min_s)
        if cache is not None:
            cache.secondes = time.perf_counter() - depart
            return cache
        cache = self._reemploi_semantique(shot, intention, channel, video_id, duree_min_s)
        if cache is not None:
            cache.secondes = time.perf_counter() - depart
            return cache

        for provider in self.fournisseurs_actifs():
            for requete in requetes:
                for candidat in self._chercher(provider, requete, duree_min_s):
                    recevable, motif = self._recevable(candidat, duree_min_s)
                    if not recevable:
                        continue
                    chemin = self._telecharger(candidat, duree_min_s)
                    if chemin is None:
                        continue
                    asset = self._ecrire_licence(chemin, candidat)
                    libre, motif = _reutilisable(
                        self.conn, asset.asset_id, channel, video_id, self.employes
                    )
                    if not libre:
                        self.tracer(f"{shot.id} : {candidat.cle} écarté ({motif})")
                        continue
                    self.employes.add(asset.asset_id)
                    _inscrire(self.conn, asset, chemin, requete, channel, video_id, self.racine)
                    self.stats[provider] = self.stats.get(provider, 0) + 1
                    self.tracer(
                        f"{shot.id} : {provider} {candidat.identifiant} « {requete} » — "
                        f"{candidat.largeur}×{candidat.hauteur}, {candidat.duree_s:.1f} s"
                    )
                    return ResultatStock(
                        chemin=chemin, asset=asset, provider=provider,
                        est_video=candidat.est_video, depuis_cache=False, requete=requete,
                        secondes=time.perf_counter() - depart,
                    )
        self.stats["repli"] = self.stats.get("repli", 0) + 1
        self.tracer(
            f"{shot.id} : aucune banque n'a rendu d'asset pour « {'/'.join(requetes)} » — "
            "repli image générée"
        )
        return None

    # -- mesures -------------------------------------------------------------------------

    def mesures(self) -> dict[str, object]:
        """Ce que la banque a servi, par fournisseur, et l'état du compteur de quota."""
        assert self.compteur is not None
        return {
            "stock_par_fournisseur": {
                p: self.stats.get(p, 0) for p in CHAINE_DEFAUT if self.stats.get(p)
            },
            "stock_cache": self.stats.get("cache", 0),
            "stock_repli": self.stats.get("repli", 0),
            "stock_requetes": {
                p.removeprefix("requetes_"): n for p, n in self.stats.items()
                if p.startswith("requetes_")
            },
            "stock_quota": self.compteur.resume(),
            "stock_quota_annonce": dict(_dernier_restant),
        }


def taille_bibliotheque(racine: Path | None = None) -> tuple[int, float]:
    """Nombre de fichiers et poids en mégaoctets de `workspace/library/stock/`."""
    dossier = (racine or racine_projet()) / "workspace" / "library" / "stock"
    if not dossier.exists():
        return 0, 0.0
    fichiers = [f for f in dossier.rglob("*") if f.is_file()]
    return len(fichiers), round(sum(f.stat().st_size for f in fichiers) / 1e6, 2)
