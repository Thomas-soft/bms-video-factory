"""Embeddings multilingues de titres — cache en base, modèle en sous-processus.

Règle 4 du projet : un seul modèle résident à la fois. Ce module ne charge donc
jamais le modèle dans le processus appelant. `embed()` écrit les textes manquants
dans un fichier de travail, lance `python -m factory.editorial.embed <travail.json>`,
attend, relit les vecteurs, et le sous-processus meurt avec sa mémoire.

Le cache est la table `embeddings` (migration 006) : une ligne par (video_id,
modèle), vecteur `float32` **L2-normalisé à l'écriture**. Deux conséquences qui
tiennent tout le reste du module :
  - le produit scalaire de deux lignes EST leur similarité cosinus, donc la
    matrice de distances du regroupement se calcule sans renormaliser ;
  - changer de modèle n'invalide rien : la clé porte le nom du modèle.

`text_hash` protège contre le piège silencieux : un titre corrigé chez l'éditeur
garderait sinon le vecteur de l'ancien. La ligne est alors recalculée.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from factory.core.paths import dossier_workspace, racine_projet

#: Modèle retenu à l'étape 20 (rapport de veille du 20/09/2026, ledger `outils/MODELES.md`).
#: `multilingual-e5-small` : 118 M paramètres, 384 dimensions, MIT, 100 langues dont
#: fr/en/es/it. Le préfixe `query: ` est **obligatoire** — sans lui la qualité tombe,
#: c'est une exigence de l'entraînement du modèle, pas une option de style.
MODELE_DEFAUT = "intfloat/multilingual-e5-small"
PREFIXE = "query: "
DIMENSION = 384
LICENCE = "MIT"
#: Longueur maximale encodée. Titre + 200 premiers caractères de description : au-delà,
#: la description noie le titre, qui porte l'essentiel du thème.
MAX_CARACTERES = 320
#: Le sous-processus charge le modèle une fois puis encode par lots. Mesuré en fin d'étape.
TAILLE_LOT = 64
#: Plafond de temps du sous-processus : chargement + encodage. 11 000 titres sur M2.
TIMEOUT_S = 3600
#: Caches à rediriger sous `models/` (`CLAUDE.md` § 3), comme `factory/assets/images.py`.
CACHES = {"HF_HOME": "models/hf"}


class ErreurEmbeddings(RuntimeError):
    """Le sous-processus n'a pas rendu de vecteurs exploitables."""


# --------------------------------------------------------------------------- cache


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()[:16]


def vers_blob(vecteur: list[float]) -> bytes:
    return struct.pack(f"<{len(vecteur)}f", *vecteur)


def depuis_blob(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def normaliser(vecteur: list[float]) -> list[float]:
    norme = sum(v * v for v in vecteur) ** 0.5
    if norme == 0:
        return vecteur
    return [v / norme for v in vecteur]


def texte_de(titre: str | None, description: str | None) -> str:
    """Titre + 200 premiers caractères de description, tronqué, jamais vide."""
    titre = (titre or "").strip()
    tete = (description or "").strip().replace("\n", " ")[:200]
    texte = f"{titre}. {tete}".strip() if tete else titre
    return texte[:MAX_CARACTERES] or "(sans titre)"


def lire_cache(
    conn: sqlite3.Connection, video_ids: list[str], modele: str
) -> dict[str, tuple[list[float], str]]:
    """Vecteurs déjà calculés, par lots de 900 (limite de paramètres SQLite)."""
    trouves: dict[str, tuple[list[float], str]] = {}
    for debut in range(0, len(video_ids), 900):
        tranche = video_ids[debut : debut + 900]
        marques = ",".join("?" * len(tranche))
        for vid, blob, th in conn.execute(
            f"SELECT video_id, vector, text_hash FROM embeddings "
            f"WHERE model = ? AND video_id IN ({marques})",
            [modele, *tranche],
        ):
            trouves[vid] = (depuis_blob(blob), th)
    return trouves


def ecrire_cache(
    conn: sqlite3.Connection, lignes: list[tuple[str, list[float], str]], modele: str
) -> int:
    maintenant = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.executemany(
        """INSERT INTO embeddings (video_id, model, dim, vector, text_hash, computed_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(video_id, model) DO UPDATE SET
             dim=excluded.dim, vector=excluded.vector,
             text_hash=excluded.text_hash, computed_at=excluded.computed_at""",
        [(vid, modele, len(vec), vers_blob(vec), th, maintenant) for vid, vec, th in lignes],
    )
    conn.commit()
    return len(lignes)


# ------------------------------------------------------------------- sous-processus


def environnement(racine: Path) -> dict[str, str]:
    env = dict(os.environ)
    for variable, relatif in CACHES.items():
        env[variable] = str((racine / relatif).resolve())
    return env


@dataclass
class ResultatEmbed:
    vecteurs: list[list[float]]
    modele: str
    calcules: int
    depuis_cache: int
    secondes: float


def _encoder_en_sous_processus(
    textes: list[str], modele: str, racine: Path, echo=None
) -> list[list[float]]:
    """Un sous-processus, un chargement de modèle, puis il meurt avec sa mémoire."""
    if not textes:
        return []
    travail = dossier_workspace(racine) / "cache" / "embed"
    travail.mkdir(parents=True, exist_ok=True)
    entree = travail / "travail.json"
    sortie = travail / "vecteurs.jsonl"
    journal = travail / "embed.log"
    sortie.unlink(missing_ok=True)
    entree.write_text(
        json.dumps({"model": modele, "prefix": PREFIXE, "batch": TAILLE_LOT,
                    "texts": textes, "out": str(sortie)}, ensure_ascii=False),
        encoding="utf-8",
    )
    if echo:
        echo(f"embeddings : {len(textes)} texte(s) à calculer — sous-processus, journal {journal}")
    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n=== embed {modele} — {len(textes)} textes ===\n")
        trace.flush()
        proc = subprocess.run(
            [sys.executable, "-m", "factory.editorial.embed", str(entree)],
            cwd=str(racine), env=environnement(racine),
            stdout=trace, stderr=subprocess.STDOUT, timeout=TIMEOUT_S, check=False,
        )
    if proc.returncode != 0 or not sortie.exists():
        queue = journal.read_text(encoding="utf-8").strip().splitlines()[-8:]
        raise ErreurEmbeddings(
            f"sous-processus d'embeddings en code {proc.returncode} — " + " / ".join(queue)
        )
    vecteurs = [json.loads(ligne)["v"] for ligne in sortie.read_text(encoding="utf-8").splitlines()]
    if len(vecteurs) != len(textes):
        raise ErreurEmbeddings(
            f"{len(vecteurs)} vecteurs rendus pour {len(textes)} textes demandés"
        )
    return vecteurs


def embed(
    textes: list[str], *, modele: str = MODELE_DEFAUT, racine: Path | None = None, echo=None
) -> list[list[float]]:
    """Vecteurs L2-normalisés de textes libres. Aucun cache : l'appelant n'a pas d'id."""
    racine = racine or racine_projet()
    return [normaliser(v) for v in _encoder_en_sous_processus(textes, modele, racine, echo)]


def embed_videos(
    conn: sqlite3.Connection,
    lignes: list[tuple[str, str]],
    *,
    modele: str = MODELE_DEFAUT,
    racine: Path | None = None,
    echo=None,
) -> ResultatEmbed:
    """Vecteurs de vidéos, cache compris. `lignes` = [(video_id, texte), …], ordre conservé."""
    racine = racine or racine_projet()
    t0 = time.monotonic()
    ids = [vid for vid, _ in lignes]
    cache = lire_cache(conn, ids, modele)

    a_calculer: list[tuple[int, str, str, str]] = []  # (rang, video_id, texte, empreinte)
    for rang, (vid, texte) in enumerate(lignes):
        emp = empreinte(texte)
        connu = cache.get(vid)
        if connu is None or connu[1] != emp:
            a_calculer.append((rang, vid, texte, emp))

    vecteurs: list[list[float]] = [[] for _ in lignes]
    for rang, (vid, _) in enumerate(lignes):
        connu = cache.get(vid)
        if connu is not None:
            vecteurs[rang] = connu[0]

    if a_calculer:
        bruts = _encoder_en_sous_processus(
            [t for _, _, t, _ in a_calculer], modele, racine, echo
        )
        neufs: list[tuple[str, list[float], str]] = []
        for (rang, vid, _, emp), brut in zip(a_calculer, bruts, strict=True):
            vec = normaliser(brut)
            vecteurs[rang] = vec
            neufs.append((vid, vec, emp))
        ecrire_cache(conn, neufs, modele)

    manquants = [i for i, v in enumerate(vecteurs) if not v]
    if manquants:
        raise ErreurEmbeddings(f"{len(manquants)} vecteur(s) absents après calcul")
    return ResultatEmbed(
        vecteurs=vecteurs, modele=modele, calcules=len(a_calculer),
        depuis_cache=len(lignes) - len(a_calculer), secondes=time.monotonic() - t0,
    )


def similarite(a: list[float], b: list[float]) -> float:
    """Cosinus. Les vecteurs sortent normalisés : c'est un simple produit scalaire."""
    return sum(x * y for x, y in zip(a, b, strict=True))


# ------------------------------------------------------- point d'entrée sous-processus


def main(argv: list[str]) -> int:
    """Charge le modèle une fois, encode par lots, écrit un JSONL. Puis meurt."""
    if len(argv) != 2:
        print("usage : python -m factory.editorial.embed <travail.json>", file=sys.stderr)
        return 2
    travail = json.loads(Path(argv[1]).read_text(encoding="utf-8"))

    # HF_HOME doit être posé **avant** l'import de transformers (panne de l'étape 5.1).
    from factory.doctor import charge_env

    charge_env()

    t_charge = time.perf_counter()
    import torch
    from transformers import AutoModel, AutoTokenizer

    # La clé de cache peut porter un suffixe après `#` (par exemple `…-e5-small#titre`,
    # les vecteurs du titre seul). Le dépôt Hugging Face, lui, s'arrête au `#` — sans quoi
    # `from_pretrained` refuse l'identifiant : « Repo id must use alphanumeric chars ».
    nom = travail["model"].split("#", 1)[0]
    tokenizer = AutoTokenizer.from_pretrained(nom)
    modele = AutoModel.from_pretrained(nom)
    modele.eval()
    # CPU par défaut : mesuré en fin d'étape 20 sur ce corpus. `device` reste ouvert
    # dans le fichier de travail pour qui voudra comparer MPS — non mesuré ici.
    appareil = travail.get("device", "cpu")
    modele.to(appareil)
    print(f"charge : {time.perf_counter() - t_charge:.1f} s ({nom}, {appareil})", flush=True)

    prefixe = travail.get("prefix", "")
    textes = travail["texts"]
    lot = int(travail.get("batch", 64))
    sortie = Path(travail["out"])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with sortie.open("w", encoding="utf-8") as f, torch.no_grad():
        for debut in range(0, len(textes), lot):
            tranche = [prefixe + t for t in textes[debut : debut + lot]]
            entrees = tokenizer(
                tranche, padding=True, truncation=True, max_length=128, return_tensors="pt"
            ).to(appareil)
            etats = modele(**entrees).last_hidden_state
            masque = entrees["attention_mask"].unsqueeze(-1).float()
            # Moyenne masquée : la recette officielle de e5. Un `[CLS]` brut donne des
            # vecteurs sensiblement pires sur des textes courts.
            moyenne = (etats * masque).sum(1) / masque.sum(1).clamp(min=1e-9)
            for vecteur in moyenne.tolist():
                f.write(json.dumps({"v": [round(x, 6) for x in vecteur]}) + "\n")
            if debut % (lot * 20) == 0:
                fait = min(debut + lot, len(textes))
                print(f"{fait}/{len(textes)} — {time.perf_counter() - t0:.0f} s", flush=True)
    ecoule = time.perf_counter() - t0
    debit = len(textes) / ecoule if ecoule > 0 else 0
    print(f"fini : {len(textes)} textes en {ecoule:.1f} s ({debit:.0f} textes/s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
