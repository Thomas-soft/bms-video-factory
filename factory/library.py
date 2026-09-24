"""Bibliothèque d'assets : index unifié, recherche sémantique, réemploi, purge (étape 29).

Les fichiers de `workspace/library/` restent la source de vérité (licence JSON frère) ; la table
`library_assets` n'en est que l'index. Ce module y ajoute ce qui manquait pour que la vidéo n
coûte moins que la vidéo 1 :

- **une description et son embedding** par asset (`factory/editorial/embed.py`, e5-small, un
  sous-processus) : une intention visuelle proche d'un asset existant le réemploie sans
  génération ni téléchargement, si la similarité dépasse `channel.library.semantic_threshold` et
  que l'asset n'a pas servi à la chaîne dans ses `cooldown_videos` derniers runs ;
- **des tags** : `prefixe:<empreinte>` pour une image générée — une image n'est réemployée que
  sous le même préfixe de style, sinon la charte d'une autre chaîne entrerait dans la vidéo ;
- **les emplois** restent dans `library_uses` : `used_by` s'en déduit, il n'est pas recopié.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from factory.core.paths import LibraryPaths, racine_projet

TYPES = ("images", "stock", "music", "sfx", "characters", "intros")
EXT_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
EXT_MEDIAS = EXT_IMAGES | {".mp4", ".mov", ".webm", ".wav", ".mp3", ".flac", ".ogg"}
#: Types jamais purgés automatiquement : ils sont choisis à la main, pas produits par un run.
NON_PURGEABLES = {"characters", "intros"}


def maintenant() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()[:16]


def tag_prefixe(style_prefix: str) -> str:
    """Tag de style d'une image générée : même préfixe de charte mot pour mot = même style."""
    return f"prefixe:{empreinte(style_prefix.strip())}" if style_prefix.strip() else "prefixe:aucun"


# --------------------------------------------------------------------------------------
# Inventaire
# --------------------------------------------------------------------------------------


@dataclass
class Entree:
    """Un asset trouvé sur disque, prêt à indexer."""

    asset_id: str
    kind: str
    chemin: Path
    provider: str
    licence: str
    licence_url: str
    description: str
    tags: list[str] = field(default_factory=list)
    attribution: str | None = None
    has_text: bool = False


def _lire_json(fichier: Path) -> dict[str, Any]:
    try:
        return json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _prefixes_connus(racine: Path) -> list[tuple[str, str, str]]:
    """(préfixe, suffixe, tag) de chaque charte déclarée — pour étiqueter les images générées."""
    try:
        from factory.core import config

        cfg = config.charger(racine, strict=False)
    except Exception:
        return []
    vus: dict[str, tuple[str, str, str]] = {}
    for channel in cfg.channels.values():
        p = channel.charte.style_prefix.strip()
        if p and p not in vus:
            vus[p] = (p, channel.charte.style_suffix.strip(), tag_prefixe(p))
    return list(vus.values())


def _description_image(prompt: str, prefixes: list[tuple[str, str, str]]) -> tuple[str, str]:
    """Retire préfixe et suffixe de charte d'un prompt : reste l'intention visuelle."""
    for prefixe, suffixe, tag in prefixes:
        if prompt.startswith(prefixe):
            coeur = prompt[len(prefixe):]
            if suffixe and suffixe in coeur:
                coeur = coeur[: coeur.rindex(suffixe)]
            coeur = coeur.split(" — ")[0]  # « — rupture … » : consigne de cadrage, pas sujet
            return coeur.strip(" ,.;"), tag
    return prompt.strip(), "prefixe:inconnu"


def inventaire(racine: Path, conn: sqlite3.Connection) -> tuple[list[Entree], list[str]]:
    """Tout ce que `workspace/library/` contient d'indexable, et les refus (sans licence)."""
    lib = LibraryPaths.depuis_racine(racine)
    entrees: list[Entree] = []
    refus: list[str] = []
    prefixes = _prefixes_connus(racine)
    mots_cles = {
        str(l["path"]): l["keywords"]
        for l in conn.execute("SELECT path, keywords FROM library_assets WHERE kind = 'stock'")
    }

    # images générées : <clé>.png + <clé>.json (licence) + <clé>.prompt.txt
    for png in sorted((lib.racine / "images").glob("*.png")):
        meta = _lire_json(png.with_suffix(".json"))
        if not meta.get("licence"):
            refus.append(f"{png.name} : licence absente")
            continue
        invite = png.with_suffix(".prompt.txt")
        prompt = invite.read_text(encoding="utf-8") if invite.exists() else ""
        description, tag = _description_image(prompt, prefixes)
        entrees.append(Entree(
            meta["asset_id"], "images", png, meta.get("provider", "flux"), meta["licence"],
            meta.get("licence_url", ""), description or png.stem, [tag],
            meta.get("attribution_line"), bool(meta.get("has_text")),
        ))

    # stock : <fournisseur>/<id>.<ext> + <id>.json
    for fichier in sorted((lib.racine / "stock").glob("*/*")):
        if fichier.suffix.lower() not in EXT_MEDIAS:
            continue
        meta = _lire_json(fichier.with_suffix(".json"))
        if not meta.get("licence"):
            refus.append(f"stock/{fichier.parent.name}/{fichier.name} : licence absente")
            continue
        relatif = str(fichier.relative_to(racine))
        description = mots_cles.get(relatif) or fichier.stem.replace("_", " ").replace("-", " ")
        entrees.append(Entree(
            meta["asset_id"], "stock", fichier, meta.get("provider", fichier.parent.name),
            meta["licence"], meta.get("licence_url", ""), description,
            [f"provider:{fichier.parent.name}", "video" if fichier.suffix == ".mp4" else "photo"],
            meta.get("attribution_line"), bool(meta.get("has_text")),
        ))

    # music, sfx, intros : fichier + JSON frère (licence, description, tags)
    for kind in ("music", "sfx", "intros"):
        for fichier in sorted((lib.racine / kind).glob("*")) if (lib.racine / kind).is_dir() else []:
            if fichier.suffix.lower() not in EXT_MEDIAS:
                continue
            meta = _lire_json(fichier.with_suffix(".json"))
            if not meta.get("licence"):
                refus.append(f"{kind}/{fichier.name} : licence absente")
                continue
            entrees.append(Entree(
                meta.get("asset_id") or empreinte(str(fichier.relative_to(racine))), kind,
                fichier, meta.get("provider", "local"), meta["licence"],
                meta.get("licence_url", ""), meta.get("description") or fichier.stem,
                list(meta.get("tags") or []), meta.get("attribution_line"),
            ))

    # personnages : characters/<id>/character.yaml + base.png
    import yaml

    for fiche in sorted((lib.racine / "characters").glob("*/character.yaml")):
        donnees = yaml.safe_load(fiche.read_text(encoding="utf-8")) or {}
        base = fiche.parent / "base.png"
        if not base.exists() or not donnees.get("licence"):
            refus.append(f"characters/{fiche.parent.name} : base.png ou licence absente")
            continue
        entrees.append(Entree(
            hashlib.sha256(base.read_bytes()).hexdigest()[:16], "characters", base, "flux", donnees["licence"],
            donnees.get("licence_url", ""), " ".join(str(donnees["description"]).split()),
            [f"channel:{donnees.get('channel')}"],
        ))
    return entrees, refus


# --------------------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------------------


def _phash(chemin: Path) -> str | None:
    if chemin.suffix.lower() not in EXT_IMAGES:
        return None
    try:
        import imagehash
        from PIL import Image

        with Image.open(chemin) as image:
            return str(imagehash.phash(image.convert("RGB")))
    except Exception:
        return None


def scan(
    conn: sqlite3.Connection, racine: Path | None = None, *, avec_embeddings: bool = True,
    echo: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Réindexe `workspace/library/` : ajoute, met à jour, retire les entrées orphelines."""
    racine = racine or racine_projet()
    depart = time.perf_counter()
    entrees, refus = inventaire(racine, conn)
    existants = {
        str(l["asset_id"]): l for l in conn.execute(
            "SELECT asset_id, path, phash, embed_hash FROM library_assets")
    }
    ajoutes = maj = 0
    vus: set[str] = set()
    for e in entrees:
        relatif = str(e.chemin.relative_to(racine))
        vus.add(e.asset_id)
        ancien = existants.get(e.asset_id)
        phash = (ancien["phash"] if ancien and ancien["phash"] else None) or _phash(e.chemin)
        if ancien is None:
            ajoutes += 1
            conn.execute(
                "INSERT INTO library_assets (asset_id, kind, layer, path, provider, licence,"
                " licence_url, attribution_line, has_text, keywords, phash, uses, created_at,"
                " description, tags, size_bytes) VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?)",
                (e.asset_id, e.kind, "character" if e.kind == "characters" else "background",
                 relatif, e.provider, e.licence, e.licence_url, e.attribution, int(e.has_text),
                 e.description, phash, maintenant(), e.description, json.dumps(e.tags),
                 e.chemin.stat().st_size),
            )
        else:
            maj += 1
            conn.execute(
                "UPDATE library_assets SET path = ?, phash = ?, description = ?, tags = ?,"
                " size_bytes = ? WHERE asset_id = ?",
                (relatif, phash, e.description, json.dumps(e.tags), e.chemin.stat().st_size,
                 e.asset_id),
            )
    orphelins = [a for a, l in existants.items()
                 if a not in vus and not (racine / str(l["path"])).exists()]
    for asset_id in orphelins:
        conn.execute("DELETE FROM library_assets WHERE asset_id = ?", (asset_id,))

    calcules = _completer_embeddings(conn, racine, echo) if avec_embeddings else 0
    return {"indexes": len(entrees), "ajoutes": ajoutes, "mis_a_jour": maj,
            "orphelins_retires": len(orphelins), "refus": refus,
            "embeddings_calcules": calcules, "secondes": round(time.perf_counter() - depart, 1)}


def _completer_embeddings(conn: sqlite3.Connection, racine: Path, echo=None) -> int:
    """Embeddings manquants ou périmés (description changée), en un seul sous-processus."""
    from factory.editorial import embed

    lignes = [
        (str(l["asset_id"]), str(l["description"]))
        for l in conn.execute(
            "SELECT asset_id, description, embed_hash, embed_model FROM library_assets"
            " WHERE description IS NOT NULL")
        if l["embed_hash"] != empreinte(str(l["description"]))
        or l["embed_model"] != embed.MODELE_DEFAUT
    ]
    if not lignes:
        return 0
    vecteurs = embed.embed([d for _, d in lignes], racine=racine, echo=echo)
    conn.executemany(
        "UPDATE library_assets SET embedding = ?, embed_model = ?, embed_hash = ? WHERE asset_id = ?",
        [(np.asarray(v, dtype=np.float32).tobytes(), embed.MODELE_DEFAUT, empreinte(d), a)
         for (a, d), v in zip(lignes, vecteurs, strict=True)],
    )
    return len(lignes)


# --------------------------------------------------------------------------------------
# Recherche et réemploi sémantique
# --------------------------------------------------------------------------------------
#
# **Cosinus centré, pas cosinus brut.** Mesuré le 24/09/2026 sur 554 images : en cosinus e5
# brut, 17 % des paires d'intentions distinctes dépassent 0,9 (« cristal de sucre » ≈ « pile
# de carrés et horloge » à 0,912) — le seuil ne trie rien. Après soustraction du vecteur moyen
# de la bibliothèque, 0,3 % des paires dépassent 0,9, et ce sont des paraphrases du même sujet.


def _moyenne(conn: sqlite3.Connection) -> np.ndarray | None:
    vecteurs = [np.frombuffer(l[0], dtype=np.float32)
                for l in conn.execute("SELECT embedding FROM library_assets WHERE embedding IS NOT NULL")]
    return np.vstack(vecteurs).mean(axis=0) if vecteurs else None


def _centrer(v: np.ndarray, mu: np.ndarray | None) -> np.ndarray:
    if mu is None:
        return v
    c = v - mu
    n = np.linalg.norm(c, axis=-1, keepdims=True)
    return c / np.where(n == 0, 1, n)


@dataclass
class IndexSemantique:
    """Vecteurs d'un type d'asset en mémoire, et ceux des intentions d'un run."""

    ids: list[str]
    chemins: list[str]
    matrice: np.ndarray
    moyenne: np.ndarray | None = None
    requetes: dict[str, np.ndarray] = field(default_factory=dict)

    @classmethod
    def charger(cls, conn: sqlite3.Connection, kind: str, tag: str | None = None) -> IndexSemantique:
        ids, chemins, vecteurs = [], [], []
        for l in conn.execute(
            "SELECT asset_id, path, tags, embedding FROM library_assets"
            " WHERE kind = ? AND embedding IS NOT NULL AND has_text = 0", (kind,)
        ):
            if tag and tag not in json.loads(l["tags"] or "[]"):
                continue
            ids.append(str(l["asset_id"]))
            chemins.append(str(l["path"]))
            vecteurs.append(np.frombuffer(l["embedding"], dtype=np.float32))
        mu = _moyenne(conn)
        matrice = _centrer(np.vstack(vecteurs), mu) if vecteurs else np.zeros((0, 384), np.float32)
        return cls(ids, chemins, matrice, mu)

    def preparer(self, intentions: list[str], racine: Path | None = None, echo=None) -> None:
        """Embeddings des intentions d'un run, en un seul sous-processus."""
        from factory.editorial import embed

        a_faire = sorted({i.strip() for i in intentions if i.strip()} - set(self.requetes))
        if not a_faire or not self.ids:
            return
        for texte, v in zip(a_faire, embed.embed(a_faire, racine=racine, echo=echo), strict=True):
            self.requetes[texte] = _centrer(np.asarray(v, dtype=np.float32), self.moyenne)

    def classement(self, intention: str, k: int = 5) -> list[tuple[str, str, float]]:
        vecteur = self.requetes.get(intention.strip())
        if vecteur is None or not self.ids:
            return []
        scores = self.matrice @ vecteur
        ordre = np.argsort(-scores)[:k]
        return [(self.ids[i], self.chemins[i], float(scores[i])) for i in ordre]


def reemploi_semantique(
    conn: sqlite3.Connection, index: IndexSemantique | None, intention: str, *,
    seuil: float, libre: Callable[[str], tuple[bool, str]], deja_dans_run: set[str],
    video_id: str, shot_id: str, kind: str,
) -> tuple[str, str, float] | None:
    """Le meilleur asset au-dessus du seuil, libre pour la chaîne, pas déjà dans ce run.

    `libre` est la règle de cooldown du module appelant (`images._reutilisable`, etc.) : la
    bibliothèque ne la redéfinit pas. Le réemploi est inscrit dans `library_semantic_reuse`.
    """
    if index is None:
        return None
    for asset_id, chemin, score in index.classement(intention, k=8):
        if score <= seuil:
            return None
        if asset_id in deja_dans_run:
            continue
        ok, _motif = libre(asset_id)
        if not ok:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO library_semantic_reuse (video_id, shot_id, asset_id, kind,"
            " similarity, intention, reused_at) VALUES (?,?,?,?,?,?,?)",
            (video_id, shot_id, asset_id, kind, round(score, 4), intention, maintenant()),
        )
        return asset_id, chemin, score
    return None


def find(conn: sqlite3.Connection, texte: str, *, kind: str | None = None, k: int = 10,
         racine: Path | None = None) -> list[dict[str, Any]]:
    """Recherche sémantique libre dans la bibliothèque."""
    from factory.editorial import embed

    mu = _moyenne(conn)
    requete = _centrer(np.asarray(embed.embed([texte], racine=racine)[0], dtype=np.float32), mu)
    lignes = conn.execute(
        "SELECT asset_id, kind, path, description, uses, embedding FROM library_assets"
        " WHERE embedding IS NOT NULL" + (" AND kind = ?" if kind else ""),
        (kind,) if kind else (),
    ).fetchall()
    if not lignes:
        return []
    matrice = _centrer(np.vstack([np.frombuffer(l["embedding"], dtype=np.float32)
                                  for l in lignes]), mu)
    scores = matrice @ requete
    return [
        {"asset_id": lignes[i]["asset_id"], "kind": lignes[i]["kind"],
         "path": lignes[i]["path"], "description": lignes[i]["description"],
         "uses": lignes[i]["uses"], "similarity": round(float(scores[i]), 4)}
        for i in np.argsort(-scores)[:k]
    ]


# --------------------------------------------------------------------------------------
# Statistiques et purge
# --------------------------------------------------------------------------------------


def derniers_runs(conn: sqlite3.Connection, n: int = 10) -> list[str]:
    return [str(l[0]) for l in conn.execute(
        "SELECT video_id FROM library_uses GROUP BY video_id ORDER BY max(used_at) DESC LIMIT ?",
        (n,))]


def taux_reemploi(conn: sqlite3.Connection, video_ids: list[str]) -> dict[str, Any]:
    """Part des emplois de ces runs servis par un asset **déjà présent avant le run**.

    Un emploi est un réemploi si l'asset a été employé par une autre vidéo plus tôt. Le partage
    d'une image entre deux plans du même run n'en est pas un : il est compté au manifeste.
    """
    total = reemplois = 0
    par_run: dict[str, tuple[int, int]] = {}
    for vid in video_ids:
        lignes = conn.execute(
            "SELECT u.asset_id, u.used_at, (SELECT min(p.used_at) FROM library_uses p"
            " WHERE p.asset_id = u.asset_id AND p.video_id != u.video_id) AS avant"
            " FROM library_uses u WHERE u.video_id = ?", (vid,)).fetchall()
        r = sum(1 for l in lignes if l["avant"] and l["avant"] < l["used_at"])
        par_run[vid] = (r, len(lignes))
        total += len(lignes)
        reemplois += r
    return {"runs": len(video_ids), "emplois": total, "reemplois": reemplois,
            "taux": round(reemplois / total, 3) if total else 0.0, "par_run": par_run}


def stats(conn: sqlite3.Connection, racine: Path | None = None) -> dict[str, Any]:
    racine = racine or racine_projet()
    par_type = {
        str(l["kind"]): {"assets": l["n"], "octets": l["o"] or 0, "emplois": l["u"] or 0,
                         "sans_embedding": l["se"]}
        for l in conn.execute(
            "SELECT kind, count(*) n, sum(size_bytes) o, sum(uses) u,"
            " sum(embedding IS NULL) se FROM library_assets GROUP BY kind")
    }
    top = [
        {"asset_id": l["asset_id"], "kind": l["kind"], "uses": l["uses"],
         "used_by": l["used_by"], "description": (l["description"] or "")[:70]}
        for l in conn.execute(
            "SELECT a.asset_id, a.kind, a.uses, a.description, (SELECT group_concat(DISTINCT"
            " channel_id) FROM library_uses u WHERE u.asset_id = a.asset_id) used_by"
            " FROM library_assets a ORDER BY a.uses DESC, a.last_used_at DESC LIMIT 5")
    ]
    semantiques = conn.execute("SELECT count(*) FROM library_semantic_reuse").fetchone()[0]
    return {"par_type": par_type, "reemploi_10_runs": taux_reemploi(conn, derniers_runs(conn)),
            "top": top, "reemplois_semantiques": semantiques}


def prune(conn: sqlite3.Connection, racine: Path | None = None, *, unused_days: int = 180,
          executer: bool = False) -> dict[str, Any]:
    """Assets non employés depuis `unused_days` jours. Simulation par défaut.

    Jamais les personnages ni les intros (choisis à la main) ; le fichier et sa licence JSON
    partent ensemble, puis l'entrée d'index. Les emplois passés restent dans `library_uses`.
    """
    racine = racine or racine_projet()
    limite = (datetime.now(timezone.utc) - timedelta(days=unused_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    candidats = conn.execute(
        "SELECT asset_id, kind, path, size_bytes FROM library_assets WHERE"
        " coalesce(last_used_at, created_at) < ? AND kind NOT IN ('characters', 'intros')",
        (limite,)).fetchall()
    octets = sum(int(l["size_bytes"] or 0) for l in candidats)
    if executer:
        for l in candidats:
            fichier = racine / str(l["path"])
            for f in (fichier, fichier.with_suffix(".json"), fichier.with_suffix(".prompt.txt")):
                f.unlink(missing_ok=True)
            conn.execute("DELETE FROM library_assets WHERE asset_id = ?", (l["asset_id"],))
    return {"candidats": len(candidats), "octets": octets, "execute": executer,
            "limite": limite, "exemples": [str(l["path"]) for l in candidats[:5]]}


# --------------------------------------------------------------------------------------
# Intros et outros de charte
# --------------------------------------------------------------------------------------


def construire_intros(channel: Any, racine: Path | None = None, journal=None) -> list[Path]:
    """Intro (1,5 s) et outro (3 s) de la charte, versées dans `library/intros/` avec licence.

    Composées par Pillow (police OFL de la charte, palette) puis encodées par ffmpeg avec un
    fondu : aucun pixel tiers, licence « BMS » + OFL des polices.
    """
    from PIL import Image

    from factory import video

    racine = racine or racine_projet()
    charte = channel.charte
    sortie_dir = LibraryPaths.depuis_racine(racine).racine / "intros"
    sortie_dir.mkdir(parents=True, exist_ok=True)
    titre = video.resoudre_police(charte.fonts.title, racine)
    faits: list[Path] = []
    for nom, texte, duree in (("intro", channel.name, 1.5),
                              ("outro", "Thanks for watching", 3.0)):
        cible = racine / (charte.intro if nom == "intro" else charte.outro or "")
        if not (charte.intro if nom == "intro" else charte.outro):
            continue
        image = Image.new("RGBA", (video.LARGEUR, video.HAUTEUR), charte.palette.bg)
        bloc = video.rasteriser_texte(texte, titre, 110, charte.palette.text,
                                      largeur_max=video.LARGEUR - 400, lignes_max=2)
        x, y = (video.LARGEUR - bloc.width) // 2, (video.HAUTEUR - bloc.height) // 2
        video.coller(image, bloc, (x, y))
        barre = video.rectangle_arrondi((max(160, bloc.width // 3), 12), 6, charte.palette.highlight, 1.0)
        video.coller(image, barre, ((video.LARGEUR - barre.width) // 2, y + bloc.height + 40))
        png = cible.with_suffix(".png")
        image.save(png)
        fondu = min(0.4, duree / 4)
        video.lancer_ffmpeg([
            "-loop", "1", "-i", str(png), "-vf",
            f"fade=t=in:st=0:d={fondu},fade=t=out:st={duree - fondu:.2f}:d={fondu}",
            *video.arguments_encodage(cible, duree)], journal)
        png.unlink()
        (cible.with_suffix(".json")).write_text(json.dumps({
            "asset_id": empreinte(str(cible.relative_to(racine)) + charte.version),
            "provider": "bms", "licence": "BMS (composé) + SIL OFL 1.1 (polices)",
            "licence_url": "https://openfontlicense.org",
            "description": f"{nom} card of {channel.name}, charte {charte.version}",
            "tags": [f"channel:{channel.id}", nom, f"charte:{charte.version}"],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        faits.append(cible)
    return faits
