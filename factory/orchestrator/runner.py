"""Exécuteur de la file : une étape, un sous-processus, un job à la fois.

Ce que le runner ajoute à `factory run`, et pourquoi.

1. **Il avance étape par étape, en écrivant l'état après chacune.** `factory run` enchaîne
   le DAG dans un seul processus : tué au milieu, il ne laisse que ses marqueurs `.done`.
   Le runner, lui, écrit `jobs.stage` en base après chaque étape réussie ; un `kill -9`
   pendant `render` laisse donc un job `running` à l'étape `render`, que le tour suivant
   reprend **à la même étape** avec `attempts` incrémenté. C'est le test de l'étape 22.1.
2. **Il reprend les orphelins avant de prendre un job neuf.** Un job `running` dont le
   `locked_by` désigne un PID mort est rendu à la file (`ARCHITECTURE` § 1.3, même règle
   que `run.lock`). Sans cela, un plantage gèle la file jusqu'à intervention humaine.
3. **Il regarde le disque et la mémoire avant chaque étape, pas après.** Une étape lancée
   à 7 Go libres échoue au milieu de l'écriture ; une étape non lancée se rattrape.
4. **Il passe le banc.** Le DAG du runner est celui de `factory run` **plus `qc`** : le
   portillon n'est pas câblé dans `factory run` (résidu assumé de l'étape 15) parce qu'un
   humain était là pour le lancer. Ici, personne. `qc` FAIL bloque le job avec ses raisons
   ; la régénération est le sujet de l'étape 22.2.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from factory import run as run_module
from factory.core import config as config_module
from factory.core.models import OrchestratorConfig
from factory.core.paths import RunPaths, racine_projet
from factory.orchestrator import journal, notify, regenerate
from factory.orchestrator.queue import ETAPES, ErreurFile, Job, lire, lister

#: Codes de retour qui ne sont pas des échecs de production (`INTERFACES` § Sémantique).
CODE_QUALITE = run_module.CODE_QUALITE          # 4 — un seuil n'est pas tenu
CODE_ATTENTE_HUMAINE = run_module.CODE_ATTENTE_HUMAINE   # 7 — une décision humaine manque

#: Attente avant de reprendre un job mis en pause par un garde-fou (disque, mémoire).
PAUSE_GARDE_MIN = 15


def maintenant() -> str:
    """Horodatage ISO-8601 UTC."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dans(minutes: int) -> str:
    """Horodatage UTC dans `minutes` minutes."""
    return (datetime.now(UTC) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def signature() -> str:
    """« hôte:pid » — ce qu'écrit `jobs.locked_by`."""
    return f"{socket.gethostname()}:{os.getpid()}"


# --------------------------------------------------------------------------------------
# Garde-fous
# --------------------------------------------------------------------------------------


def disque_libre_go(chemin: Path | None = None) -> float:
    """Espace libre du volume, en gigaoctets décimaux — la même unité que `df -h`."""
    usage = shutil.disk_usage(chemin or Path("/"))
    return usage.free / 1e9


def memoire_libre_go() -> float | None:
    """Mémoire réellement disponible, lue dans `vm_stat`, ou `None` si illisible.

    « Disponible » = libres + inactives + spéculatives + purgeables. C'est une
    **approximation** : macOS compresse et le chiffre bouge d'une seconde à l'autre. Elle
    suffit pour ce qu'on lui demande — refuser de lancer `render` quand il ne reste rien,
    sachant que le pic mesuré de la génération d'image est 11,15 Go (`ARCHITECTURE` § 8).
    """
    try:
        sortie = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10,
                                check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    taille = re.search(r"page size of (\d+) bytes", sortie)
    if not taille:
        return None
    octets_page = int(taille.group(1))
    total = 0
    for etiquette in ("Pages free", "Pages inactive", "Pages speculative",
                      "Pages purgeable"):
        trouve = re.search(rf"{etiquette}:\s+(\d+)\.", sortie)
        if trouve:
            total += int(trouve.group(1))
    return total * octets_page / 1e9


def _taille_run_mo(chemins: RunPaths) -> float:
    """Poids du dossier du run, en mégaoctets."""
    if not chemins.racine.exists():
        return 0.0
    return sum(f.stat().st_size for f in chemins.racine.rglob("*") if f.is_file()) / 1e6


@dataclass
class Garde:
    """Verdict d'un garde-fou : ce qui a été mesuré, et si ça bloque."""

    nom: str
    valeur: float | None
    seuil: float
    ok: bool
    message: str


def gardes_fous(cfg: OrchestratorConfig, chemins: RunPaths,
                racine: Path | None = None) -> list[Garde]:
    """Les trois mesures prises **avant** chaque étape. Ordre : disque, mémoire, run."""
    libre = disque_libre_go(racine)
    memoire = memoire_libre_go()
    poids = _taille_run_mo(chemins)
    return [
        Garde("disque", round(libre, 2), cfg.gardes.disque_libre_go_min,
              libre >= cfg.gardes.disque_libre_go_min,
              f"{libre:.1f} Go libres pour un plancher de "
              f"{cfg.gardes.disque_libre_go_min:.0f} Go (CLAUDE.md § 3)"),
        Garde("memoire", None if memoire is None else round(memoire, 2),
              cfg.gardes.memoire_libre_go_min,
              memoire is None or memoire >= cfg.gardes.memoire_libre_go_min,
              "vm_stat illisible — garde-fou mémoire non appliqué" if memoire is None
              else f"{memoire:.1f} Go disponibles pour un plancher de "
                   f"{cfg.gardes.memoire_libre_go_min:.1f} Go"),
        Garde("run_disque", round(poids, 1), float(cfg.gardes.run_disque_mo_max),
              poids <= cfg.gardes.run_disque_mo_max,
              f"le run pèse {poids:.0f} Mo pour un plafond de "
              f"{cfg.gardes.run_disque_mo_max} Mo (ARCHITECTURE § 8)"),
    ]


# --------------------------------------------------------------------------------------
# Fenêtre de production
# --------------------------------------------------------------------------------------


def fenetre_ouverte(cfg: OrchestratorConfig, etape: str,
                    quand: datetime | None = None) -> bool:
    """Vrai si l'étape a le droit de tourner maintenant, dans le fuseau configuré."""
    from zoneinfo import ZoneInfo

    local = (quand or datetime.now(UTC)).astimezone(ZoneInfo(cfg.timezone))
    fenetre = (cfg.fenetre_lourdes if etape in cfg.etapes_lourdes else cfg.fenetre_legeres)
    return fenetre.contient(local.time())


# --------------------------------------------------------------------------------------
# Verrou de job et reprise des orphelins
# --------------------------------------------------------------------------------------


def _pid_vivant(locked_by: str | None) -> bool:
    """Vrai si le détenteur du verrou de job répond encore."""
    if not locked_by or ":" not in locked_by:
        return False
    hote, _, pid = locked_by.rpartition(":")
    if hote != socket.gethostname():
        return True  # un verrou d'une autre machine ne se juge pas d'ici
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True
    return True


def reprendre_orphelins(conn: sqlite3.Connection, racine: Path | None = None) -> list[Job]:
    """Rend à la file les jobs `running` dont le processus est mort. `attempts` +1.

    C'est la reprise que teste l'étape 22.1 : le `stage` n'est **pas** touché — le job
    repart exactement là où il a été interrompu — et le compteur de tentatives monte,
    sinon une étape qui fait planter le daemon le ferait planter indéfiniment.
    """
    repris: list[Job] = []
    for job in lister(conn, ["running"]):
        if _pid_vivant(job.locked_by):
            continue
        conn.execute(
            "UPDATE jobs SET status = 'queued', attempts = attempts + 1, locked_by = NULL, "
            "locked_at = NULL, last_error = ?, updated_at = ? WHERE id = ?",
            (f"interrompu à l'étape {job.stage} : processus {job.locked_by} disparu",
             maintenant(), job.id),
        )
        journal.evenement(
            "WARN", f"job {job.id} repris après interruption à l'étape {job.stage}",
            job=job.id, video_id=job.video_id, stage=job.stage,
            donnees={"attempts": job.attempts + 1, "locked_by_mort": job.locked_by},
            racine=racine, conn=conn,
        )
        repris.append(lire(conn, job.id))
    return repris


def prendre_job(conn: sqlite3.Connection, racine: Path | None = None) -> Job | None:
    """Prend le job éligible le plus prioritaire et le verrouille, ou `None`.

    L'ordre : priorité décroissante, puis ancienneté. `next_run_at` dans le futur exclut
    le job — c'est l'attente croissante des nouvelles tentatives et la pause des gardes.
    """
    ligne = conn.execute(
        "SELECT * FROM jobs WHERE status = 'queued' "
        "AND (next_run_at IS NULL OR next_run_at <= ?) "
        "ORDER BY priority DESC, created_at, id LIMIT 1", (maintenant(),),
    ).fetchone()
    if ligne is None:
        return None
    job = Job.depuis_ligne(ligne)
    curseur = conn.execute(
        "UPDATE jobs SET status = 'running', locked_by = ?, locked_at = ?, updated_at = ? "
        "WHERE id = ? AND status = 'queued'",
        (signature(), maintenant(), maintenant(), job.id),
    )
    if curseur.rowcount != 1:
        return None  # un autre processus l'a pris entre le SELECT et l'UPDATE
    return lire(conn, job.id)


# --------------------------------------------------------------------------------------
# Arrêt propre
# --------------------------------------------------------------------------------------


class Arret:
    """Drapeau d'arrêt propre : le signal note, l'étape en cours va jusqu'au bout.

    Interrompre ffmpeg ou un modèle au milieu laisserait un fichier tronqué qu'aucun
    marqueur ne décrit. On finit l'étape, on écrit l'état, on sort.
    """

    def __init__(self) -> None:
        self.demande = False
        self.signal: int | None = None

    def installer(self) -> None:
        """Branche SIGTERM et SIGINT. Sans effet hors du thread principal."""
        def _noter(numero: int, _cadre: Any) -> None:
            self.demande, self.signal = True, numero
        for numero in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(numero, _noter)
            except ValueError:
                pass


# --------------------------------------------------------------------------------------
# Exécution
# --------------------------------------------------------------------------------------


@dataclass
class ResultatTour:
    """Ce qu'a fait un passage du runner sur un job."""

    job_id: int
    video_id: str
    statut: str
    etapes: list[tuple[str, int, float]] = field(default_factory=list)
    raison: str | None = None
    alertes: list[str] = field(default_factory=list)
    #: Reprises ciblées décidées pendant ce tour (étape 22.2).
    regenerations: list[Any] = field(default_factory=list)

    @property
    def secondes(self) -> float:
        """Temps cumulé des étapes exécutées."""
        return round(sum(s for _, _, s in self.etapes), 1)


def _timeout(cfg: OrchestratorConfig, etape: str, chemins: RunPaths) -> int:
    """Plafond de temps : la configuration prime, le calcul par plan de `render` sinon."""
    if etape in cfg.timeouts_s:
        return cfg.timeouts_s[etape]
    return run_module._timeout(etape, chemins)  # noqa: SLF001 — même paquet, règle unique


def _statut(conn: sqlite3.Connection, job: Job, statut: str, *, stage: str | None = None,
            attempts: int | None = None, next_run_at: str | None = None,
            last_error: str | None = None, racine: Path | None = None) -> Job:
    """Écrit le nouvel état du job. Seul chemin d'écriture du runner dans `jobs`."""
    conn.execute(
        "UPDATE jobs SET status = ?, stage = ?, attempts = ?, next_run_at = ?, "
        "last_error = ?, locked_by = ?, locked_at = ?, updated_at = ? WHERE id = ?",
        (statut, stage or job.stage,
         job.attempts if attempts is None else attempts, next_run_at,
         last_error[:500] if last_error else None,
         signature() if statut == "running" else None,
         job.locked_at if statut == "running" else None,
         maintenant(), job.id),
    )
    return lire(conn, job.id)


def executer_job(
    conn: sqlite3.Connection, job: Job, cfg: OrchestratorConfig, *,
    racine: Path | None = None, arret: Arret | None = None,
    respecter_fenetre: bool = True, echo: Callable[[str], None] | None = None,
) -> ResultatTour:
    """Fait avancer **un** job, étape par étape, jusqu'à un état stable.

    États stables : `exported` (qc PASS), `awaiting_review` (relecture ou code 7),
    `blocked` (qc FAIL ou garde-fou durable), `failed` (tentatives épuisées), ou de retour
    en `queued` (attente d'une tentative, d'une fenêtre, ou arrêt demandé).
    """
    racine = racine or racine_projet()
    dire = echo or (lambda _: None)
    chemins = RunPaths.depuis_video_id(job.video_id, racine)
    journal_run = journal.dossier_logs(racine) / f"run_{job.video_id}.log"
    resultat = ResultatTour(job.id, job.video_id, job.status)
    debut_iso, t0 = maintenant(), time.perf_counter()
    cfg_projet = config_module.charger(racine, strict=False)
    auto_approve = bool(
        cfg_projet.channels[job.channel_id].auto_approve
        if job.channel_id in cfg_projet.channels else False
    )
    style = None
    qualite_non_tenue: list[str] = []

    if job.stage not in ETAPES:
        raise ErreurFile(f"job {job.id} : étape inconnue « {job.stage} » "
                         f"({', '.join(ETAPES)})")
    index = ETAPES.index(job.stage)
    # Boucle **indexée** et non `for etape in ETAPES[index:]` : la régénération de l'étape
    # 22.2 doit pouvoir revenir en arrière dans le DAG après un `qc` FAIL, ce qu'un `for`
    # sur une tranche ne permet pas. Rien d'autre ne change.
    while index < len(ETAPES):
        etape = ETAPES[index]
        index += 1
        if arret is not None and arret.demande:
            job = _statut(conn, job, "queued", stage=etape, racine=racine)
            journal.evenement("INFO", f"arrêt demandé — job {job.id} rendu à la file à "
                              f"l'étape {etape}", job=job.id, video_id=job.video_id,
                              stage=etape, racine=racine, conn=conn)
            resultat.statut, resultat.raison = "queued", "arrêt propre demandé"
            return resultat

        if respecter_fenetre and not fenetre_ouverte(cfg, etape):
            job = _statut(conn, job, "queued", stage=etape, racine=racine)
            fenetre = cfg.fenetre_lourdes if etape in cfg.etapes_lourdes else cfg.fenetre_legeres
            raison = (f"hors fenêtre pour {etape} ({fenetre.debut}–{fenetre.fin} "
                      f"{cfg.timezone})")
            journal.evenement("INFO", f"job {job.id} en attente : {raison}", job=job.id,
                              video_id=job.video_id, stage=etape, racine=racine, conn=conn)
            resultat.statut, resultat.raison = "queued", raison
            return resultat

        # --- barrière humaine : la relecture du script (CONFORMITE § 4, RIA art. 50) ---
        # Posée **avant toute étape d'aval**, et non « après un script sorti en 0 ».
        # Constaté le 20/09 sur `s57f` : `script` est sorti en **code 4** (densité sous le
        # plancher de la niche), donc pas en 0, et le job a enchaîné sur `voice` sans
        # qu'aucun humain ait lu le texte. Un seuil de qualité non tenu n'annule pas
        # l'obligation de relecture — il la rend plus nécessaire. Formulée en condition
        # d'entrée, elle tient aussi à la reprise, où `script` est sauté.
        if not auto_approve and ETAPES.index(etape) > ETAPES.index("script") \
                and chemins.script.exists() and not _script_relu(conn, job, chemins):
            raison = (f"script écrit — relecture humaine requise avant {etape} "
                      f"(auto_approve=false sur {job.channel_id})")
            job = _statut(conn, job, "awaiting_review", stage=etape, attempts=0,
                          last_error=None, racine=racine)
            journal.evenement("BLOCK", f"job {job.id} en attente de relecture", job=job.id,
                              video_id=job.video_id, stage=etape,
                              donnees={"channel_id": job.channel_id,
                                       "commande": f"factory queue approve {job.id} "
                                                   "--reviewer <id>"},
                              racine=racine, conn=conn)
            _finaliser(job, racine, "awaiting_review", raison, debut_iso, t0, chemins)
            resultat.statut, resultat.raison = "awaiting_review", raison
            return resultat

        # --- garde-fous, avant l'étape et jamais après ---
        bloquants = [g for g in gardes_fous(cfg, chemins, racine) if not g.ok]
        if bloquants:
            garde = bloquants[0]
            if garde.nom == "run_disque":
                job = _statut(conn, job, "blocked", stage=etape, last_error=garde.message,
                              racine=racine)
                journal.evenement("BLOCK", f"job {job.id} bloqué : {garde.message}",
                                  job=job.id, video_id=job.video_id, stage=etape,
                                  donnees={"garde": garde.nom, "valeur": garde.valeur},
                                  racine=racine, conn=conn)
                _alerter(conn, job, "blocked", garde.message, racine)
                resultat.statut, resultat.raison = "blocked", garde.message
                return resultat
            job = _statut(conn, job, "queued", stage=etape,
                          next_run_at=_dans(PAUSE_GARDE_MIN), last_error=garde.message,
                          racine=racine)
            journal.evenement("ERROR", f"production en pause : {garde.message}", job=job.id,
                              video_id=job.video_id, stage=etape,
                              donnees={"garde": garde.nom, "valeur": garde.valeur,
                                       "seuil": garde.seuil,
                                       "reprise_dans_min": PAUSE_GARDE_MIN},
                              racine=racine, conn=conn)
            resultat.statut, resultat.raison = "queued", garde.message
            resultat.alertes.append(garde.message)
            return resultat

        # `qc` n'a pas de marqueur : il mesure `final.mp4`, pas des fichiers légers, et une
        # reprise à l'étape `qc` doit re-mesurer plutôt que croire un marqueur.
        if etape != "qc" and run_module.etape_faite(chemins, etape):
            dire(f"  {etape} : déjà fait")
            continue

        dire(f"  {etape} …")
        # L'état est écrit **avant** le journal et avant le sous-processus : c'est
        # `jobs.stage` que relit la reprise, pas le journal.
        job = _statut(conn, job, "running", stage=etape, racine=racine)
        journal.evenement("INFO", f"étape {etape} lancée", job=job.id,
                          video_id=job.video_id, stage=etape,
                          donnees={"attempts": job.attempts}, racine=racine, conn=conn)
        code, secondes, sortie = run_module.executer_etape(
            etape, job.video_id, chemins, journal_run, racine, style=style,
            timeout=_timeout(cfg, etape, chemins),
        )
        resultat.etapes.append((etape, code, round(secondes, 1)))
        message = run_module._dernieres_lignes(sortie)  # noqa: SLF001

        # --- le banc : c'est lui qui décide si la vidéo sort ---
        if etape == "qc":
            if code == 0:
                regenerate.noter_resultat(job.video_id, racine, "pass")
                journal.evenement("INFO", "qc PASS", job=job.id, video_id=job.video_id,
                                  stage="qc", donnees={"secondes": round(secondes, 1)},
                                  racine=racine, conn=conn)
                run_module._timing(job.video_id, racine, "qc", secondes)  # noqa: SLF001
                continue
            if code == CODE_QUALITE:
                run_module._timing(job.video_id, racine, "qc", secondes)  # noqa: SLF001
                # Étape 22.2 : le banc refuse — on rejoue **l'étape fautive et ses
                # suivantes**, deux fois au plus, avant de rendre la main à un humain.
                regenerate.noter_resultat(job.video_id, racine, "regenerate")
                decision = regenerate.decider(conn, job, cfg, racine=racine)
                if decision.action == "regenerate" and decision.depuis:
                    resultat.regenerations.append(decision)
                    resultat.alertes.append(f"régénération {decision.rang} : {decision.raison}")
                    dire(f"  qc FAIL → régénération {decision.rang} depuis "
                         f"{decision.depuis} ({decision.raison})")
                    job = _statut(conn, job, "running", stage=decision.depuis, attempts=0,
                                  last_error=f"régénération {decision.rang} : "
                                             f"{decision.raison}", racine=racine)
                    index = ETAPES.index(decision.depuis)
                    continue
                raison = regenerate.raison_lisible(decision)
                job = _statut(conn, job, "blocked", stage="qc", last_error=raison,
                              racine=racine)
                journal.evenement("BLOCK", f"job {job.id} bloqué par le banc", job=job.id,
                                  video_id=job.video_id, stage="qc",
                                  donnees={"code": code, "message": message[:300],
                                           "regenerations": decision.rang,
                                           "raison": decision.raison},
                                  racine=racine, conn=conn)
                _finaliser(job, racine, "blocked", raison, debut_iso, t0, chemins)
                _alerter(conn, job, "blocked", raison, racine)
                resultat.statut, resultat.raison = "blocked", raison
                return resultat
            # tout autre code : échec d'outil, traité comme les autres étapes ci-dessous

        if code == 0:
            run_module.marquer(chemins, etape, debut_iso, secondes, code)
            run_module._timing(job.video_id, racine, etape, secondes)  # noqa: SLF001
            journal.evenement("INFO", f"étape {etape} terminée", job=job.id,
                              video_id=job.video_id, stage=etape,
                              donnees={"secondes": round(secondes, 1)}, racine=racine,
                              conn=conn)
            job = _statut(conn, job, "running", stage=etape, attempts=0, racine=racine)

            continue

        if code == CODE_QUALITE:
            # Décision de l'étape 13.2 : le fichier est produit, le seuil ne l'est pas.
            run_module.marquer(chemins, etape, debut_iso, secondes, code)
            run_module._timing(job.video_id, racine, etape, secondes)  # noqa: SLF001
            qualite_non_tenue.append(etape)
            journal.evenement("WARN", f"seuil de qualité non tenu à l'étape {etape} : "
                              "le DAG continue", job=job.id, video_id=job.video_id,
                              stage=etape, donnees={"code": code, "message": message[:300]},
                              racine=racine, conn=conn)
            resultat.alertes.append(f"{etape} : code 4 — {message[:160]}")
            job = _statut(conn, job, "running", stage=etape, attempts=0, racine=racine)
            continue

        if code == CODE_ATTENTE_HUMAINE:
            raison = f"{etape} attend une décision humaine : {message}"
            job = _statut(conn, job, "awaiting_review", stage=etape, last_error=raison,
                          racine=racine)
            journal.evenement("BLOCK", f"job {job.id} en attente humaine", job=job.id,
                              video_id=job.video_id, stage=etape,
                              donnees={"code": code}, racine=racine, conn=conn)
            _finaliser(job, racine, "awaiting_review", raison, debut_iso, t0, chemins)
            resultat.statut, resultat.raison = "awaiting_review", raison
            return resultat

        # --- échec : tentative suivante, puis abandon ---
        tentative = job.attempts + 1
        raison = f"l'étape « {etape} » s'est arrêtée (code {code}) : {message}"
        run_module._inscrire_erreur(job.video_id, racine, etape, code, message)  # noqa: SLF001
        if tentative < cfg.tentatives.max:
            attente = cfg.tentatives.attente_min(tentative)
            job = _statut(conn, job, "queued", stage=etape, attempts=tentative,
                          next_run_at=_dans(attente), last_error=raison, racine=racine)
            journal.evenement("ERROR", f"étape {etape} en échec — tentative {tentative}/"
                              f"{cfg.tentatives.max}, reprise dans {attente} min",
                              job=job.id, video_id=job.video_id, stage=etape,
                              donnees={"code": code, "message": message[:300],
                                       "attempts": tentative, "attente_min": attente},
                              racine=racine, conn=conn)
            resultat.statut, resultat.raison = "queued", raison
            resultat.alertes.append(raison)
            return resultat
        job = _statut(conn, job, "failed", stage=etape, attempts=tentative,
                      last_error=raison, racine=racine)
        journal.evenement("ERROR", f"job {job.id} en échec définitif après {tentative} "
                          f"tentatives à l'étape {etape}", job=job.id,
                          video_id=job.video_id, stage=etape,
                          donnees={"code": code, "message": message[:300]}, racine=racine,
                          conn=conn)
        _finaliser(job, racine, "failed", raison, debut_iso, t0, chemins)
        _alerter(conn, job, "failed", raison, racine)
        resultat.statut, resultat.raison = "failed", raison
        return resultat

    # Toutes les étapes sont passées, `qc` compris.
    raison = None
    if qualite_non_tenue:
        raison = ("seuil de qualité non tenu à l'étape " + ", ".join(qualite_non_tenue)
                  + " — le banc a néanmoins rendu PASS")
    job = _statut(conn, job, "exported", stage=ETAPES[-1], attempts=0, last_error=raison,
                  racine=racine)
    journal.evenement("INFO", f"job {job.id} exporté", job=job.id, video_id=job.video_id,
                      stage=ETAPES[-1],
                      donnees={"secondes": resultat.secondes,
                               "qualite_non_tenue": qualite_non_tenue},
                      racine=racine, conn=conn)
    _finaliser(job, racine, "exported", raison, debut_iso, t0, chemins)
    resultat.statut, resultat.raison = "exported", raison
    if cfg.declinaison.actif and cfg.declinaison.declencheur == "export":
        enfiler_declinaisons(conn, job, racine)
    return resultat


def enfiler_declinaisons(conn: sqlite3.Connection, job: Job, racine: Path) -> None:
    """Étape 24 : un job par chaîne `derive_from`, sans jamais faire échouer le parent."""
    from factory.steps import localize as localize_module
    try:
        enfants = localize_module.enfiler_declinaisons(conn, job.video_id, racine)
    except Exception as erreur:  # noqa: BLE001 — message exact, le parent reste exporté
        journal.evenement("ERROR", f"déclinaison de {job.video_id} impossible : {erreur}",
                          job=job.id, video_id=job.video_id, racine=racine, conn=conn)
        return
    for video_id, job_id in enfants:
        journal.evenement("INFO", f"déclinaison {video_id} enfilée (job {job_id})", job=job.id,
                          video_id=job.video_id, donnees={"enfant": video_id},
                          racine=racine, conn=conn)


def _script_relu(conn: sqlite3.Connection, job: Job, chemins: RunPaths) -> bool:
    """Vrai si **ce** script (empreinte comprise) porte une approbation dans `review_log`.

    L'empreinte est dans la clé : un script réécrit après approbation redevient non relu,
    ce qui est le comportement voulu — c'est le texte qui est approuvé, pas le run.
    """
    import hashlib

    if not chemins.script.exists():
        return False
    empreinte = hashlib.sha256(chemins.script.read_bytes()).hexdigest()
    ligne = conn.execute(
        "SELECT 1 FROM review_log WHERE video_id = ? AND review_hash = ? "
        "AND decision IN ('approved', 'auto_approved')", (job.video_id, empreinte),
    ).fetchone()
    return ligne is not None


def _alerter(conn: sqlite3.Connection, job: Job, etat: str, raison: str,
             racine: Path) -> None:
    """Prévient un humain qu'un job l'attend. Une alerte qui échoue n'arrête pas la file.

    Le run est déjà fini quand on arrive ici : si le canal est cassé, le job reste
    correctement `blocked` en base et le digest du matin le dira. L'inverse — une file qui
    s'arrête parce qu'une notification n'est pas partie — serait absurde.
    """
    try:
        if etat == "blocked":
            notify.alerte_job_bloque(job.id, job.video_id, raison, racine=racine, conn=conn)
        elif etat == "failed":
            notify.alerte_job_echoue(job.id, job.video_id, raison, racine=racine, conn=conn)
    except Exception as erreur:  # noqa: BLE001 — aucune alerte ne doit tuer un run
        journal.evenement("WARN", f"alerte non envoyée pour le job {job.id} : {erreur}",
                          job=job.id, video_id=job.video_id, racine=racine)


def _finaliser(job: Job, racine: Path, etat: str, raison: str | None, debut_iso: str,
               t0: float, chemins: RunPaths) -> None:
    """Porte l'état au manifeste et en base. Une erreur ici n'annule pas le travail fait."""
    try:
        run_module.finaliser(job.video_id, racine, etat, raison, debut_iso,
                             time.perf_counter() - t0, _taille_run_mo(chemins))
    except (FileNotFoundError, ValueError, KeyError, sqlite3.Error) as erreur:
        journal.evenement("WARN", f"manifeste non finalisé pour {job.video_id} : {erreur}",
                          job=job.id, video_id=job.video_id, racine=racine)


# --------------------------------------------------------------------------------------
# Boucle
# --------------------------------------------------------------------------------------


def caffeinate(actif: bool = True) -> subprocess.Popen | None:
    """Empêche le sommeil par inactivité le temps d'un run (`caffeinate -i -w <pid>`).

    `-i` seulement : `-s` est ignoré sur batterie et **aucune** option n'empêche le sommeil
    déclenché par la fermeture du capot (veille du 20/09/2026). Le capot ouvert et le
    secteur branché restent une condition d'exploitation, écrite dans `EXPLOITATION.md`.
    """
    if not actif:
        return None
    try:
        return subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
    except (OSError, subprocess.SubprocessError):
        return None


def boucle(
    conn: sqlite3.Connection, *, racine: Path | None = None, max_jobs: int | None = None,
    cfg: OrchestratorConfig | None = None, arret: Arret | None = None,
    respecter_fenetre: bool = True, echo: Callable[[str], None] | None = None,
) -> list[ResultatTour]:
    """Vide la file tant qu'il y a des jobs éligibles. Un seul run à la fois.

    `workspace/run.lock` est pris pour toute la durée : les tâches planifiées (collecte,
    analytique, sauvegarde) l'attendent au lieu de tourner à côté d'une étape à 11 Go
    (`ARCHITECTURE` § 1.3).
    """
    racine = racine or racine_projet()
    cfg = cfg or _config(racine)
    dire = echo or (lambda _: None)
    resultats: list[ResultatTour] = []
    with journal.verrou_run(f"runner pid {os.getpid()}", racine):
        veilleur = caffeinate(cfg.daemon.caffeinate)
        try:
            reprendre_orphelins(conn, racine)
            while max_jobs is None or len(resultats) < max_jobs:
                if arret is not None and arret.demande:
                    break
                job = prendre_job(conn, racine)
                if job is None:
                    break
                dire(f"job {job.id} — {job.video_id} à partir de {job.stage}")
                resultats.append(executer_job(
                    conn, job, cfg, racine=racine, arret=arret,
                    respecter_fenetre=respecter_fenetre, echo=echo,
                ))
                # Un job rendu à la file (attente, fenêtre, garde) serait repris aussitôt :
                # on sort, le tour suivant du daemon décidera.
                if resultats[-1].statut == "queued":
                    break
        finally:
            if veilleur is not None:
                veilleur.terminate()
    # Les alertes partent **hors** du verrou et après coup : regroupées (un message pour N
    # scripts à relire), et une seule fois par changement d'état (`alertes.json`).
    try:
        notify.verifier_et_alerter(conn, racine=racine)
    except Exception as erreur:  # noqa: BLE001 — la supervision ne casse pas la production
        journal.evenement("WARN", f"revue des alertes impossible : {erreur}", racine=racine)
    return resultats


def _config(racine: Path | None = None) -> OrchestratorConfig:
    """`config/orchestrator.yaml`, ou les valeurs par défaut du modèle s'il manque."""
    cfg = config_module.charger(racine, strict=False)
    return cfg.orchestrator or OrchestratorConfig()
