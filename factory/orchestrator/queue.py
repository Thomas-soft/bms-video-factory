"""File de production : enfiler, regarder, débloquer.

Trois décisions, toutes prises ici et pas dans le runner.

1. **`queue add` crée le run tout de suite.** `plan` tourne au moment de l'enfilement, pas
   au premier tour du daemon : le job naît donc avec un `video_id` réel, un `spec.json` sur
   disque et un sujet retiré de `topics_queue`. Autrement deux jobs de la même chaîne
   tireraient le même sujet la nuit venue, et personne ne le verrait avant le montage.
   Conséquence assumée : `queue add` prend quelques secondes par job et peut échouer
   devant l'humain qui l'a lancé — c'est le bon moment pour échouer.
2. **L'étape courante est celle qui *reste à faire*.** `stage` vaut `research` sur un job
   neuf, jamais `plan` : la reprise relit cette colonne et relance exactement ce qu'elle
   nomme. Un `stage` qui désignerait la dernière étape *faite* obligerait chaque lecteur à
   faire un +1 dans sa tête, et un lecteur sur deux l'oublierait.
3. **Un run n'a qu'un job vivant** (index unique de la migration 007). Ré-enfiler un run
   déjà en file est une erreur lisible, pas un doublon silencieux.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from factory.core import config as config_module
from factory.core import runs as runs_module
from factory.core.paths import RunPaths, racine_projet
from factory.orchestrator import journal
from factory.run import NOEUDS

#: Le DAG du runner : celui de `factory run`, **plus `qc`**. C'est la différence entre les
#: deux orchestrateurs et elle est voulue : `factory run` s'arrête à l'export (le portillon
#: n'y est pas câblé, résidu assumé de l'étape 15), le runner du daemon passe le banc parce
#: que personne ne sera là pour le lancer à la main. Un `qc` en FAIL bloque le job ;
#: l'étape 22.2 y branchera la régénération.
ETAPES: tuple[str, ...] = (*NOEUDS, "qc")

#: Statuts de la file — mêmes valeurs que la contrainte `CHECK` de la migration 007.
STATUTS: tuple[str, ...] = (
    "queued", "running", "awaiting_review", "blocked", "failed", "exported", "published",
)
#: Statuts qui occupent encore le run : un seul job vivant par `video_id`.
VIVANTS: tuple[str, ...] = ("queued", "running", "awaiting_review", "blocked")


class ErreurFile(RuntimeError):
    """Une demande sur la file qui ne peut pas être satisfaite, avec la raison lisible."""


def maintenant() -> str:
    """Horodatage ISO-8601 UTC, format d'`INTERFACES` § 0."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Job:
    """Une ligne de la file, telle que le runner la manipule."""

    id: int
    video_id: str
    channel_id: str
    stage: str
    status: str
    attempts: int
    next_run_at: str | None
    last_error: str | None
    priority: int
    locked_by: str | None = None
    locked_at: str | None = None
    publish_at: str | None = None

    @classmethod
    def depuis_ligne(cls, ligne: sqlite3.Row) -> Job:
        """Construit depuis une ligne SQLite."""
        return cls(
            id=int(ligne["id"]), video_id=str(ligne["video_id"]),
            channel_id=str(ligne["channel_id"]), stage=str(ligne["stage"]),
            status=str(ligne["status"]), attempts=int(ligne["attempts"]),
            next_run_at=ligne["next_run_at"], last_error=ligne["last_error"],
            priority=int(ligne["priority"]), locked_by=ligne["locked_by"],
            locked_at=ligne["locked_at"],
            publish_at=ligne["publish_at"] if "publish_at" in ligne.keys() else None,
        )


# --------------------------------------------------------------------------------------
# Enfiler
# --------------------------------------------------------------------------------------


def _executer_plan(channel_id: str, topic: str | None, racine: Path) -> str:
    """Lance `factory plan` dans un sous-processus et renvoie le `video_id` créé.

    Sous-processus, comme toute étape : `plan` interroge le LLM pour l'angle, et la règle
    « un seul modèle résident » ne souffre pas d'exception pour la commodité.
    """
    commande = [sys.executable, "-m", "factory.cli", "plan", "--channel", channel_id]
    if topic:
        commande += ["--topic", topic]
    termine = subprocess.run(commande, cwd=racine, capture_output=True, text=True,
                             timeout=600, check=False)
    if termine.returncode != 0:
        sortie = (termine.stdout + termine.stderr).strip().splitlines()
        raise ErreurFile(
            f"`factory plan --channel {channel_id}` a rendu {termine.returncode} : "
            + (" | ".join(l.strip() for l in sortie[-3:])[:400] or "aucune sortie")
        )
    return _dernier_run(channel_id, racine)


def _dernier_run(channel_id: str, racine: Path) -> str:
    """Identifiant du run que `plan` vient de créer, lu en base et non deviné."""
    from factory.core import db

    conn = db.ouvrir(racine / "workspace" / "factory.db")
    ligne = conn.execute(
        "SELECT video_id FROM runs WHERE channel_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1", (channel_id,),
    ).fetchone()
    conn.close()
    if ligne is None:
        raise ErreurFile(f"aucun run en base pour {channel_id} après `plan`")
    return str(ligne[0])


def purger_sujets(conn: sqlite3.Connection, racine: Path | None = None,
                  channel_id: str | None = None) -> dict:
    """Applique les plafonds de `config/editorial.yaml` à `topics_queue`.

    Ici et pas ailleurs : la file de sujets se regarde au moment où l'on y puise. Le
    résidu était porté par `SUIVI.md` § 3 (étape 20) — `taille_max: 200` et
    `age_max_jours: 45` déclarés depuis l'étape 8, appliqués nulle part.
    """
    from factory.editorial import topics as tp

    cfg = config_module.charger(racine, strict=False)
    reglages = cfg.editorial.topics_queue if cfg.editorial else None
    if reglages is None:
        return {"par_age": 0, "par_plafond": 0, "chaines": 0, "taille_max": 0,
                "age_max_jours": 0}
    return tp.purger(conn, taille_max=reglages.taille_max,
                     age_max_jours=reglages.age_max_jours, channel_id=channel_id)


def enfiler(conn: sqlite3.Connection, video_id: str, channel_id: str, *,
            stage: str = "research", priority: int = 0,
            racine: Path | None = None) -> Job:
    """Ajoute un job pour un run **qui existe déjà**. Lève si le run est déjà en file."""
    if stage not in ETAPES:
        raise ErreurFile(f"étape inconnue : {stage} ({', '.join(ETAPES)})")
    vivant = conn.execute(
        f"SELECT id, status FROM jobs WHERE video_id = ? AND status IN "
        f"({','.join('?' * len(VIVANTS))})", (video_id, *VIVANTS),
    ).fetchone()
    if vivant is not None:
        raise ErreurFile(
            f"{video_id} est déjà en file (job {vivant['id']}, {vivant['status']}) — "
            "`factory queue retry` le relance, `factory queue block` l'arrête"
        )
    quand = maintenant()
    curseur = conn.execute(
        "INSERT INTO jobs (video_id, channel_id, stage, status, attempts, priority, "
        "created_at, updated_at) VALUES (?, ?, ?, 'queued', 0, ?, ?, ?)",
        (video_id, channel_id, stage, priority, quand, quand),
    )
    job_id = int(curseur.lastrowid or 0)
    journal.evenement("INFO", f"job {job_id} enfilé à l'étape {stage}", job=job_id,
                      video_id=video_id, stage=stage,
                      donnees={"channel_id": channel_id, "priority": priority},
                      racine=racine, conn=conn)
    return lire(conn, job_id)


def ajouter(
    conn: sqlite3.Connection, channel_id: str, *, n: int = 1, topic: str | None = None,
    priority: int = 0, racine: Path | None = None,
    echo: Callable[[str], None] | None = None,
) -> list[Job]:
    """`factory queue add` : crée `n` plans via `topics_queue` et les enfile.

    Un `--topic` explicite ne vaut que pour le **premier** job : imposer le même sujet à
    deux vidéos produirait deux fois la même, ce que la règle « un sujet une seule fois »
    de `plan` refuserait de toute façon au deuxième tour.
    """
    racine = racine or racine_projet()
    dire = echo or (lambda _: None)
    purge = purger_sujets(conn, racine, channel_id=channel_id)
    if purge["par_age"] or purge["par_plafond"]:
        dire(f"file de sujets purgée : {purge['par_age']} périmé(s), "
             f"{purge['par_plafond']} au-delà du plafond de {purge['taille_max']}")
    crees: list[Job] = []
    for rang in range(n):
        sujet = topic if rang == 0 else None
        dire(f"plan {rang + 1}/{n} — chaîne {channel_id}"
             + (f", sujet imposé « {sujet} »" if sujet else ""))
        video_id = _executer_plan(channel_id, sujet, racine)
        crees.append(enfiler(conn, video_id, channel_id, priority=priority, racine=racine))
        dire(f"  → {video_id} (job {crees[-1].id})")
    return crees


# --------------------------------------------------------------------------------------
# Lire et modifier
# --------------------------------------------------------------------------------------


def lire(conn: sqlite3.Connection, job_id: int) -> Job:
    """Un job par son identifiant."""
    ligne = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if ligne is None:
        raise ErreurFile(f"job inconnu : {job_id}")
    return Job.depuis_ligne(ligne)


def lister(conn: sqlite3.Connection, statuts: Iterable[str] | None = None) -> list[Job]:
    """Tous les jobs, du plus prioritaire au plus ancien."""
    if statuts is None:
        lignes = conn.execute(
            "SELECT * FROM jobs ORDER BY priority DESC, created_at, id"
        ).fetchall()
    else:
        voulus = tuple(statuts)
        lignes = conn.execute(
            f"SELECT * FROM jobs WHERE status IN ({','.join('?' * len(voulus))}) "
            "ORDER BY priority DESC, created_at, id", voulus,
        ).fetchall()
    return [Job.depuis_ligne(l) for l in lignes]


def _mettre_a_jour(conn: sqlite3.Connection, job_id: int, **champs: Any) -> Job:
    """Écrit des colonnes et `updated_at`. Aucun autre chemin n'écrit dans `jobs`."""
    champs["updated_at"] = maintenant()
    colonnes = ", ".join(f"{cle} = ?" for cle in champs)
    conn.execute(f"UPDATE jobs SET {colonnes} WHERE id = ?", (*champs.values(), job_id))
    return lire(conn, job_id)


def relancer(conn: sqlite3.Connection, job_id: int, *,
             racine: Path | None = None) -> Job:
    """`factory queue retry` : remet un job en file, compteur de tentatives à zéro.

    Le `stage` n'est **pas** touché : reprendre, c'est reprendre où ça s'est arrêté. Pour
    repartir d'ailleurs, `factory run --run <id> --from <etape>` puis `queue add`.
    """
    job = lire(conn, job_id)
    if job.status == "running":
        raise ErreurFile(f"job {job_id} en cours d'exécution — arrête le daemon d'abord")
    nouveau = _mettre_a_jour(conn, job_id, status="queued", attempts=0, next_run_at=None,
                             last_error=None, locked_by=None, locked_at=None)
    journal.evenement("INFO", f"job {job_id} relancé à l'étape {job.stage}", job=job_id,
                      video_id=job.video_id, stage=job.stage,
                      donnees={"depuis": job.status}, racine=racine, conn=conn)
    return nouveau


def bloquer(conn: sqlite3.Connection, job_id: int, raison: str,
            racine: Path | None = None) -> Job:
    """`factory queue block` : sort un job de la file avec une raison lisible."""
    job = lire(conn, job_id)
    if not raison.strip():
        raise ErreurFile("`--reason` est obligatoire : un job bloqué sans raison est perdu")
    # `next_run_at` est effacé : un job bloqué n'a pas de « prochaine tentative », et en
    # afficher une ferait croire qu'il repartira tout seul.
    nouveau = _mettre_a_jour(conn, job_id, status="blocked", last_error=raison.strip()[:500],
                             next_run_at=None, locked_by=None, locked_at=None)
    journal.evenement("BLOCK", f"job {job_id} bloqué : {raison.strip()[:200]}", job=job_id,
                      video_id=job.video_id, stage=job.stage, racine=racine, conn=conn)
    return nouveau


def prioriser(conn: sqlite3.Connection, job_id: int, priorite: int,
              racine: Path | None = None) -> Job:
    """`factory queue prioritize` : change la priorité. Plus grand passe d'abord."""
    job = lire(conn, job_id)
    nouveau = _mettre_a_jour(conn, job_id, priority=int(priorite))
    journal.evenement("INFO", f"job {job_id} : priorité {job.priority} → {priorite}",
                      job=job_id, video_id=job.video_id, stage=job.stage,
                      racine=racine, conn=conn)
    return nouveau


# --------------------------------------------------------------------------------------
# Statut
# --------------------------------------------------------------------------------------


def compter(conn: sqlite3.Connection) -> dict[str, int]:
    """Nombre de jobs par statut, tous les statuts connus présents, même à zéro."""
    compte = dict.fromkeys(STATUTS, 0)
    for ligne in conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"):
        compte[str(ligne["status"])] = int(ligne["n"])
    return compte


def temps_par_etape(conn: sqlite3.Connection, racine: Path | None = None,
                    derniers: int = 10) -> dict[str, dict[str, float]]:
    """Temps moyen par étape sur les `derniers` runs, relus dans leurs manifestes.

    En base plutôt qu'au fichier ? Non : `manifest.execution.timings` est la mesure prise
    **par l'orchestrateur**, la seule qui compte l'électricité (`factory/run.py`
    `_timing`). La base n'en garde pas le détail par étape.
    """
    racine = racine or racine_projet()
    lignes = conn.execute(
        "SELECT video_id FROM runs ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (derniers,),
    ).fetchall()
    cumuls: dict[str, list[float]] = {}
    for (video_id,) in lignes:
        chemins = RunPaths.depuis_video_id(str(video_id), racine)
        if not chemins.manifest.exists():
            continue
        try:
            charge = json.loads(chemins.manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        timings = (charge.get("execution") or {}).get("timings") or {}
        for etape in ETAPES:
            valeur = timings.get(etape)
            if isinstance(valeur, (int, float)) and valeur > 0:
                cumuls.setdefault(etape, []).append(float(valeur))
    return {
        etape: {"moyenne_s": round(sum(v) / len(v), 1), "n": len(v),
                "min_s": round(min(v), 1), "max_s": round(max(v), 1)}
        for etape, v in cumuls.items()
    }


def etat_runs(conn: sqlite3.Connection, video_ids: Iterable[str]) -> dict[str, str]:
    """`run_state` de chaque run cité, pour afficher la file sans relire les manifestes."""
    voulus = tuple(video_ids)
    if not voulus:
        return {}
    lignes = conn.execute(
        f"SELECT video_id, run_state FROM runs WHERE video_id IN "
        f"({','.join('?' * len(voulus))})", voulus,
    ).fetchall()
    return {str(l["video_id"]): str(l["run_state"] or "—") for l in lignes}


def reindexer(conn: sqlite3.Connection, racine: Path | None = None) -> int:
    """Rappelle que la source de vérité est le disque : relit les manifestes en base."""
    racine = racine or racine_projet()
    dossier = (racine / "workspace" / "runs")
    n = 0
    for manifeste in sorted(dossier.glob("*/manifest.json")):
        video_id = manifeste.parent.name
        try:
            spec = runs_module.charger_spec(video_id, racine)
            manifest = runs_module.charger_manifest(video_id, racine)
        except (FileNotFoundError, ValueError):
            continue
        runs_module.enregistrer(conn, spec, manifest, racine)
        n += 1
    return n


# --------------------------------------------------------------------------------------
# Relecture minimale — la barrière humaine, en attendant l'étape 22.2
# --------------------------------------------------------------------------------------


def approuver(conn: sqlite3.Connection, job_id: int, relecteur: str,
              racine: Path | None = None, *, sans_relecture: bool = False,
              motif: str | None = None) -> Job:
    """`factory queue approve` : lève la barrière de relecture d'un job, et la journalise.

    Minimale et volontairement laide : l'étape 22.2 livre la relecture par lots, avec le
    texte du script sous les yeux. Ce qui est déjà **définitif** ici, c'est la trace —
    relecteur nommé, date, empreinte du script dans `review_log` (`CONFORMITE` § 4, RIA
    art. 50 §4). Approuver sans lire est une décision humaine ; approuver sans laisser de
    trace est une non-conformité, et c'est ce que ce code rend impossible.

    `sans_relecture=True` est la **levée sans lecture** : le relecteur enregistré devient
    `auto-approve`, la décision `auto_approved`, le motif est obligatoire et un `WARN`
    part au journal. Elle existe pour les bancs d'essai et pour la reprise d'urgence ;
    elle ne doit jamais servir à produire une vidéo destinée à la publication, parce
    qu'elle retire l'exception éditoriale du RIA art. 50 §4 (`ARCHITECTURE` § 2.1). Écrire
    le nom d'un humain qui n'a rien lu serait pire : ce serait une trace **fausse**.
    """
    racine = racine or racine_projet()
    job = lire(conn, job_id)
    if job.status != "awaiting_review":
        raise ErreurFile(f"job {job_id} n'attend pas de relecture (statut {job.status})")
    cfg = config_module.charger(racine, strict=False)
    connus = {r.id for r in (cfg.team.relecteurs if cfg.team else [])}
    if sans_relecture:
        if not (motif or "").strip():
            raise ErreurFile("`--sans-relecture` exige un `--motif` : une levée sans "
                             "lecture qui ne dit pas pourquoi est indéfendable")
        relecteur = "auto"
    elif relecteur not in connus:
        raise ErreurFile(
            f"relecteur inconnu : {relecteur} — `config/team.yaml` en connaît "
            f"{', '.join(sorted(connus)) or 'aucun'} ; « l'équipe » n'est pas une réponse"
        )
    chemins = RunPaths.depuis_video_id(job.video_id, racine)
    if not chemins.script.exists():
        raise ErreurFile(f"{job.video_id} : script.json absent, rien à relire")
    decision = "auto_approved" if sans_relecture else "approved"
    # Chemin d'écriture unique depuis l'étape 22.2 : la pièce append-only
    # (`registre/data/reviews.jsonl`), l'index `review_log`, `review.json` et le manifeste
    # sont écrits ensemble. Deux endroits qui écrivent la même preuve finissent toujours
    # par diverger, et c'est la preuve qu'on perd.
    from factory.orchestrator import review as review_module

    empreinte = review_module.enregistrer_decision(
        conn, job.video_id, job.channel_id, reviewer=relecteur, decision=decision,
        motif=motif or ("levée par `factory queue approve`" if not sans_relecture else None),
        racine=racine,
    )
    nouveau = _mettre_a_jour(conn, job_id, status="queued", attempts=0, next_run_at=None,
                             last_error=None, locked_by=None, locked_at=None)
    journal.evenement(
        "WARN" if sans_relecture else "INFO",
        (f"job {job_id} levé SANS RELECTURE ({motif})" if sans_relecture
         else f"job {job_id} approuvé par {relecteur}"),
        job=job_id, video_id=job.video_id, stage=job.stage,
        donnees={"reviewer": relecteur, "decision": decision,
                 "script_sha256": empreinte, "motif": motif},
        racine=racine, conn=conn,
    )
    return nouveau
