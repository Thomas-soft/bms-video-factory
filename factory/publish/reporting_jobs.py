"""`factory publish reporting-jobs` — les jobs de la Reporting API, créés avant de publier.

**C'est le module le plus irréversible du projet.** Les rapports de la Reporting API ne sont
pas rétroactifs au-delà du backfill : « Once you create a reporting job, YouTube generates a
daily report… and also generates historical data reports covering the 30-day period prior to
the job's creation » (developers.google.com/youtube/reporting/v1/reports). Une chaîne qui
publie sa première vidéo sans job perd ses impressions et son CTR pour tout ce qui précède
ces 30 jours — et les impressions ne s'obtiennent **nulle part ailleurs** : ni la Data API ni
l'Analytics API ne les exposent. D'où l'ordre imposé par l'étape 23.1 : les jobs d'abord.

Trois points de fait, vérifiés le 22/09/2026 sur developers.google.com.

- **Les types de rapports en `_a2` n'existent pas.** Le prompt de l'étape nommait
  `channel_basic_a2`, `channel_traffic_source_a2` et `channel_playback_location_a2` ; la liste
  officielle porte des `_a3` (/youtube/reporting/v1/reports/channel_reports). Un `jobs.create`
  sur un `reportTypeId` inconnu échoue, et l'échec ne se verrait que des semaines plus tard.
  C'est pourquoi ce module interroge `reportTypes.list` **avant** de créer quoi que ce soit :
  la liste de Google prime sur la nôtre, toujours.
- **Le premier rapport arrive sous 48 h**, et les données du jour J ne sont pas disponibles
  avant J+1. Un tableau vide le lendemain de la création n'est pas une panne.
- **La rétention est de 60 jours** pour les rapports quotidiens. Les tirer et les stocker est
  le travail de l'étape 25 ; ici on se contente de faire exister la source.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from factory.core import config as config_module
from factory.core import db as db_module
from factory.core.paths import racine_projet
from factory.publish import oauth, quota
from factory.publish import upload_min as base

#: Délai annoncé par Google avant le premier rapport d'un job neuf.
DELAI_PREMIER_RAPPORT_H = 48


class ErreurRapports(RuntimeError):
    """Consentement absent, scope manquant ou refus de l'API."""


@dataclass
class Job:
    """Un job de rapport, tel que `jobs.create` ou `jobs.list` le rend."""

    job_id: str
    report_type: str
    nom: str
    created_at: str
    nouveau: bool = False


def service(channel: str, racine: Path | None = None, injecte: Any = None):
    """Client `youtubereporting v1` d'une chaîne.

    Scope : `yt-analytics.readonly` suffit pour les rapports d'activité ; la variante
    `-monetary` n'est requise que pour les revenus. Les deux sont déjà dans `oauth.SCOPES`,
    donc dans le dossier d'audit — n'en ajoute pas sans l'y ajouter aussi.
    """
    if injecte is not None:
        return injecte
    from googleapiclient.discovery import build

    identifiants = oauth.charger_identifiants(channel, racine)
    return build("youtubereporting", "v1", credentials=identifiants, cache_discovery=False)


def types_disponibles(api: Any) -> dict[str, str]:
    """`reportTypes.list` — ce que Google propose vraiment, indexé par `id`.

    Les types marqués `deprecateTime` sont exclus : créer un job sur un type en fin de vie
    revient à programmer une perte de données à date connue.
    """
    connus: dict[str, str] = {}
    jeton = None
    while True:
        reponse = api.reportTypes().list(pageToken=jeton).execute()
        for item in reponse.get("reportTypes", []):
            if item.get("deprecateTime"):
                continue
            connus[item["id"]] = item.get("name", "")
        jeton = reponse.get("nextPageToken")
        if not jeton:
            break
    return connus


def lister(channel: str, *, racine: Path | None = None, api: Any = None,
           conn: sqlite3.Connection | None = None) -> list[Job]:
    """`jobs.list` — les jobs vivants chez Google, et mise à jour de leur état en base."""
    racine = racine or racine_projet()
    api = service(channel, racine, api)
    jobs: list[Job] = []
    jeton = None
    while True:
        reponse = api.jobs().list(pageToken=jeton).execute()
        for item in reponse.get("jobs", []):
            jobs.append(Job(job_id=item["id"], report_type=item["reportTypeId"],
                            nom=item.get("name", ""), created_at=item.get("createTime", "")))
        jeton = reponse.get("nextPageToken")
        if not jeton:
            break
    if conn is not None:
        vivants = {j.job_id for j in jobs}
        for ligne in conn.execute(
            "SELECT job_id FROM reporting_jobs WHERE channel_id = ? AND state = 'active'",
            (channel,),
        ).fetchall():
            if ligne["job_id"] not in vivants:
                conn.execute("UPDATE reporting_jobs SET state = 'deleted' WHERE job_id = ?",
                             (ligne["job_id"],))
        for job in jobs:
            _enregistrer(conn, channel, job)
    return jobs


def creer(channel: str, *, racine: Path | None = None, api: Any = None,
          conn: sqlite3.Connection | None = None,
          types: list[str] | None = None) -> tuple[list[Job], list[str]]:
    """Crée les jobs manquants de la chaîne. Idempotent : rend aussi ceux qui existaient.

    Rend `(jobs, avertissements)`. Un type demandé mais absent de `reportTypes.list` n'est pas
    créé et produit un avertissement nommé : mieux vaut une ligne manquante et dite qu'un
    `jobs.create` qui échoue en silence.
    """
    from googleapiclient.errors import HttpError

    racine = racine or racine_projet()
    cfg = config_module.charger(racine)
    demandes = list(types or cfg.orchestrator.publication.rapports)
    plafonds = quota.Plafonds.depuis_config(racine)

    fermer = conn is None
    conn = conn or db_module.ouvrir()
    api = service(channel, racine, api)
    avertissements: list[str] = []
    try:
        quota.consommer(conn, "reportTypes.list", channel_id=channel, plafonds=plafonds)
        connus = types_disponibles(api)
        quota.consommer(conn, "jobs.list", channel_id=channel, plafonds=plafonds)
        existants = {j.report_type: j for j in lister(channel, racine=racine, api=api,
                                                      conn=conn)}

        resultat: list[Job] = []
        for reporttype in demandes:
            if reporttype in existants:
                resultat.append(existants[reporttype])
                continue
            if reporttype not in connus:
                avertissements.append(
                    f"{reporttype} : absent de reportTypes.list pour cette chaîne — job non "
                    f"créé. Types proposés : {', '.join(sorted(connus)) or 'aucun'}"
                )
                continue
            quota.consommer(conn, "jobs.create", channel_id=channel, plafonds=plafonds)
            try:
                reponse = api.jobs().create(
                    body={"reportTypeId": reporttype, "name": f"bms {channel} {reporttype}"}
                ).execute()
            except HttpError as erreur:
                message = base._message_http(erreur)
                quota.noter_echec(conn, "jobs.create", message)
                avertissements.append(f"{reporttype} : jobs.create refusé ({message})")
                continue
            job = Job(job_id=reponse["id"], report_type=reponse["reportTypeId"],
                      nom=reponse.get("name", ""), created_at=reponse.get("createTime", ""),
                      nouveau=True)
            _enregistrer(conn, channel, job)
            resultat.append(job)
        return resultat, avertissements
    finally:
        if fermer:
            conn.close()


def _enregistrer(conn: sqlite3.Connection, channel: str, job: Job) -> None:
    """Inscrit le job en base, avec la date à laquelle son premier rapport est attendu."""
    cree = job.created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        quand = datetime.fromisoformat(cree.replace("Z", "+00:00"))
    except ValueError:
        quand = datetime.now(UTC)
    attendu = (quand + timedelta(hours=DELAI_PREMIER_RAPPORT_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    maintenant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO reporting_jobs (job_id, channel_id, report_type, created_at, state, "
        "first_report_expected_at, seen_at) VALUES (?, ?, ?, ?, 'active', ?, ?) "
        "ON CONFLICT(job_id) DO UPDATE SET state = 'active', seen_at = excluded.seen_at, "
        "created_at = excluded.created_at, "
        "first_report_expected_at = excluded.first_report_expected_at",
        (job.job_id, channel, job.report_type, cree, attendu, maintenant),
    )


def chaines_authentifiees(racine: Path | None = None) -> list[str]:
    """Chaînes de `config/channels/` dont le jeton existe sur le disque.

    Sert à `--toutes` : les jobs se créent pour toute chaîne déjà consentie, sans jamais
    déclencher de consentement — celui-ci est un geste humain, pas une décision de programme.
    """
    racine = racine or racine_projet()
    cfg = config_module.charger(racine)
    return [nom for nom in sorted(cfg.channels)
            if oauth.chemin_jeton(nom, racine).is_file()]
