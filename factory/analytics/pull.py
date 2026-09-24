"""`factory analytics pull` — résultats des vidéos publiées, stockés localement chaque jour.

Sources (developers.google.com, lues le 23/09/2026) :

- **Analytics API `reports.query`.** Aucun rapport de chaîne ne documente
  `dimensions=day,video` : la série quotidienne se demande **vidéo par vidéo**
  (`dimensions=day`, `filters=video==ID`). Même chose pour les sources de trafic
  (`day,insightTrafficSourceType`) et la courbe de rétention (`elapsedVideoTimeRatio`, filtre
  `video` obligatoire, une seule valeur). La réponse s'arrête au dernier jour complet :
  latence de 48 à 72 h, d'où la relecture des 5 derniers jours à chaque passage.
- **Reporting API.** `jobs.reports.list` puis GET sur `downloadUrl`. `channel_reach_basic_a1`
  (impressions, CTR) est la seule source d'impressions. Un rapport **révisé** arrive avec un
  nouvel identifiant et la même période : il remplace les lignes déjà chargées. Rétention
  côté Google : 60 jours — tout fichier est gardé brut sous `workspace/analytics/reports/`.
- **Dates** : jour du Pacifique, jamais converti.

Une chaîne en échec n'arrête pas les autres ; chaque appel est inscrit au ledger de quota.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from factory.core import db as db_module
from factory.core.paths import RunPaths, dossier_workspace, racine_projet
from factory.orchestrator.journal import journaliser
from factory.publish import oauth, quota
from factory.publish import reporting_jobs as rj

#: Fenêtre relue à chaque passage (latence YouTube jusqu'à 72 h).
FENETRE_J = 5
#: Jalons de capture de la courbe de rétention (jours après publication).
JALONS_RETENTION = (2, 7, 30)
#: Rapports téléchargés ; seul « reach » est chargé en table, « basic » reste brut.
RAPPORTS = ("channel_reach_basic_a1", "channel_basic_a3")

METRIQUES = ["views", "estimatedMinutesWatched", "averageViewDuration",
             "averageViewPercentage", "subscribersGained", "likes", "shares", "comments",
             "engagedViews"]


@dataclass
class Bilan:
    """Ce qu'un passage a fait sur une chaîne."""

    channel: str
    rows: int = 0
    calls: int = 0
    skipped: int = 0
    videos: int = 0
    curves: int = 0
    reports: int = 0
    reach_rows: int = 0
    erreurs: list[str] = field(default_factory=list)
    status: str = "ok"


def _maintenant() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _aujourdhui() -> date:
    return datetime.now(UTC).date()


def _jour(texte: str | None) -> date | None:
    if not texte:
        return None
    try:
        return date.fromisoformat(texte[:10])
    except ValueError:
        return None


def _date_rapport(brut: str) -> str:
    """`20260920` ou `2026-09-20` → `2026-09-20` (format non documenté par Google)."""
    brut = brut.strip()
    if len(brut) == 8 and brut.isdigit():
        return f"{brut[:4]}-{brut[4:6]}-{brut[6:]}"
    return brut[:10]


# --- clients ---------------------------------------------------------------------------------

def client_analytics(channel: str, racine: Path | None = None) -> Any:
    return oauth.service(channel, "youtubeAnalytics", "v2", racine=racine)


def telecharger_http(channel: str, url: str, destination: Path,
                     racine: Path | None = None) -> None:
    """GET authentifié sur `downloadUrl` ; écrit le fichier brut tel quel."""
    from google.auth.transport.requests import AuthorizedSession

    session = AuthorizedSession(oauth.charger_identifiants(channel, racine))
    reponse = session.get(url, timeout=120)
    reponse.raise_for_status()
    destination.write_bytes(reponse.content)


# --- Analytics API ---------------------------------------------------------------------------

class _Compteur:
    """Inscrit chaque appel au ledger et compte ceux de la chaîne."""

    def __init__(self, conn: sqlite3.Connection, bilan: Bilan, plafonds: quota.Plafonds):
        self.conn, self.bilan, self.plafonds = conn, bilan, plafonds

    def __call__(self, appel: str, video_id: str | None = None) -> None:
        quota.consommer(self.conn, appel, video_id=video_id, channel_id=self.bilan.channel,
                        plafonds=self.plafonds)
        self.bilan.calls += 1


def _requete(api: Any, compter: _Compteur, video_id: str, **params: Any) -> list[dict]:
    """`reports.query` ; rend les lignes en dictionnaires colonne → valeur."""
    compter("analytics.reports.query", video_id)
    reponse = api.reports().query(ids="channel==MINE", **params).execute()
    noms = [c["name"] for c in reponse.get("columnHeaders", [])]
    return [dict(zip(noms, ligne, strict=False)) for ligne in reponse.get("rows", []) or []]


def _series_jour(api: Any, compter: _Compteur, yt: str, debut: date, fin: date,
                 video_id: str) -> tuple[list[dict], bool]:
    """Série quotidienne ; retente sans `engagedViews` si l'API la refuse. Rend (lignes, engaged)."""
    params = dict(startDate=debut.isoformat(), endDate=fin.isoformat(), dimensions="day",
                  filters=f"video=={yt}", sort="day")
    try:
        return _requete(api, compter, video_id, metrics=",".join(METRIQUES), **params), True
    except Exception as erreur:  # noqa: BLE001 — HttpError 400 si la métrique est refusée
        if "engagedViews" not in str(erreur):
            raise
        metriques = [m for m in METRIQUES if m != "engagedViews"]
        return _requete(api, compter, video_id, metrics=",".join(metriques), **params), False


def _num(valeur: Any, entier: bool = False) -> float | int | None:
    if valeur is None:
        return None
    return int(valeur) if entier else float(valeur)


def tirer_video(conn: sqlite3.Connection, api: Any, compter: _Compteur, pub: sqlite3.Row,
                *, depuis: date | None, aujourd_hui: date) -> tuple[int, int]:
    """perf_daily + perf_traffic + rétention d'une vidéo. Rend (lignes, courbes)."""
    vid, yt = pub["video_id"], pub["youtube_video_id"]
    d0 = _jour(pub["publish_at"]) or _jour(pub["uploaded_at"]) or aujourd_hui
    deja = conn.execute("SELECT count(*) FROM perf_daily WHERE video_id = ?", (vid,)).fetchone()[0]
    # Premier passage : rattrapage depuis la publication ; ensuite, fenêtre glissante.
    debut = depuis or (d0 if not deja else aujourd_hui - timedelta(days=FENETRE_J))
    debut = max(debut, d0)
    if debut > aujourd_hui:
        return 0, 0
    lignes = 0
    serie, engaged = _series_jour(api, compter, yt, debut, aujourd_hui, vid)
    for r in serie:
        conn.execute(
            "INSERT OR REPLACE INTO perf_daily (video_id, youtube_video_id, channel_id, date, "
            "views, minutes_watched, avg_view_duration_s, avg_view_pct, subs_gained, likes, "
            "shares, comments, engaged_views, pulled_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (vid, yt, pub["channel_id"], r["day"], _num(r.get("views"), True),
             _num(r.get("estimatedMinutesWatched")), _num(r.get("averageViewDuration")),
             _num(r.get("averageViewPercentage")), _num(r.get("subscribersGained"), True),
             _num(r.get("likes"), True), _num(r.get("shares"), True),
             _num(r.get("comments"), True),
             _num(r.get("engagedViews"), True) if engaged else None, _maintenant()),
        )
        lignes += 1

    trafic = _requete(api, compter, vid, startDate=debut.isoformat(),
                      endDate=aujourd_hui.isoformat(),
                      dimensions="day,insightTrafficSourceType", filters=f"video=={yt}",
                      metrics="views,estimatedMinutesWatched", sort="day")
    for r in trafic:
        conn.execute(
            "INSERT OR REPLACE INTO perf_traffic (video_id, date, source_type, views, "
            "minutes_watched, pulled_at) VALUES (?,?,?,?,?,?)",
            (vid, r["day"], r["insightTrafficSourceType"], _num(r.get("views"), True),
             _num(r.get("estimatedMinutesWatched")), _maintenant()),
        )
        lignes += 1

    courbes = 0
    age = (aujourd_hui - d0).days
    captures = {x[0] for x in conn.execute(
        "SELECT day_after_publish FROM retention_curves WHERE video_id = ?", (vid,))}
    for jalon in JALONS_RETENTION:
        if age < jalon or jalon in captures:
            continue
        # J+2 ne sert qu'au premier retour : inutile si J+7 est déjà atteignable.
        if jalon == 2 and age >= 7:
            continue
        points = _requete(api, compter, vid, startDate=d0.isoformat(),
                          endDate=(d0 + timedelta(days=jalon)).isoformat(),
                          dimensions="elapsedVideoTimeRatio", filters=f"video=={yt}",
                          metrics="audienceWatchRatio,relativeRetentionPerformance",
                          sort="elapsedVideoTimeRatio")
        if not points:  # pas encore de données (latence) : on retentera demain
            continue
        serie_json = json.dumps([[float(p["elapsedVideoTimeRatio"]),
                                  float(p["audienceWatchRatio"]),
                                  _num(p.get("relativeRetentionPerformance"))]
                                 for p in points])
        conn.execute(
            "INSERT OR IGNORE INTO retention_curves (video_id, captured_at, day_after_publish, "
            "points_json) VALUES (?,?,?,?)", (vid, _maintenant(), jalon, serie_json))
        courbes += 1
    return lignes, courbes


# --- Reporting API ---------------------------------------------------------------------------

def dossier_rapports(racine: Path | None = None) -> Path:
    return dossier_workspace(racine) / "analytics" / "reports"


def charger_reach(conn: sqlite3.Connection, fichier: Path, report_type: str,
                  correspondance: dict[str, str]) -> tuple[int, int]:
    """Agrège un CSV reach par (vidéo, jour) et remplace les lignes de ces jours.

    CTR pondéré par les impressions. Rend (lignes écrites, lignes hors usine ignorées).
    """
    impressions: dict[tuple[str, str], float] = defaultdict(float)
    clics: dict[tuple[str, str], float] = defaultdict(float)
    ignorees = 0
    with fichier.open(encoding="utf-8", newline="") as flux:
        for ligne in csv.DictReader(flux):
            vid = correspondance.get(ligne.get("video_id", ""))
            if vid is None:
                ignorees += 1
                continue
            cle = (vid, _date_rapport(ligne.get("date", "")))
            imp = float(ligne.get("video_thumbnail_impressions") or 0)
            impressions[cle] += imp
            clics[cle] += imp * float(ligne.get("video_thumbnail_impressions_ctr") or 0)
    for (vid, jour), imp in impressions.items():
        conn.execute(
            "INSERT OR REPLACE INTO perf_reach (video_id, date, impressions, ctr, source_report) "
            "VALUES (?,?,?,?,?)",
            (vid, jour, int(imp), (clics[(vid, jour)] / imp) if imp else None, report_type))
    return len(impressions), ignorees


def compter_lignes(fichier: Path) -> int:
    with fichier.open(encoding="utf-8", newline="") as flux:
        return max(0, sum(1 for _ in flux) - 1)


def tirer_rapports(conn: sqlite3.Connection, api: Any, compter: _Compteur, channel: str,
                   *, racine: Path, telecharger: Callable[[str, str, Path], None],
                   correspondance: dict[str, str]) -> tuple[int, int, int]:
    """Nouveaux fichiers des jobs reach et basic. Rend (fichiers, lignes reach, ignorées)."""
    fichiers = lignes_reach = ignorees = 0
    jobs = conn.execute(
        "SELECT job_id, report_type FROM reporting_jobs WHERE channel_id = ? AND state = 'active' "
        f"AND report_type IN ({','.join('?' * len(RAPPORTS))})", (channel, *RAPPORTS)).fetchall()
    connus = {r[0] for r in conn.execute("SELECT report_id FROM reporting_reports")}
    for job in jobs:
        rapports: list[dict] = []
        jeton = None
        while True:
            compter("jobs.reports.list")
            reponse = api.jobs().reports().list(jobId=job["job_id"], pageToken=jeton).execute()
            rapports.extend(reponse.get("reports", []))
            jeton = reponse.get("nextPageToken")
            if not jeton:
                break
        # Ordre de création : un rapport révisé (backfill) remplace l'original.
        for rapport in sorted(rapports, key=lambda r: r.get("createTime", "")):
            if rapport["id"] in connus:
                continue
            debut = _date_rapport(rapport.get("startTime", "")[:10] or "inconnu")
            dossier = dossier_rapports(racine) / channel / job["report_type"]
            dossier.mkdir(parents=True, exist_ok=True)
            destination = dossier / f"{debut}_{rapport['id']}.csv"
            compter("media.download")
            telecharger(channel, rapport["downloadUrl"], destination)
            n = compter_lignes(destination)
            charge = 0
            if job["report_type"].startswith("channel_reach_basic"):
                ecrites, hors = charger_reach(conn, destination, job["report_type"],
                                              correspondance)
                lignes_reach += ecrites
                ignorees += hors
                charge = 1
            conn.execute(
                "INSERT INTO reporting_reports (report_id, job_id, channel_id, report_type, "
                "start_time, end_time, create_time, path, rows, loaded, downloaded_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rapport["id"], job["job_id"], channel, job["report_type"],
                 rapport.get("startTime"), rapport.get("endTime"), rapport.get("createTime"),
                 str(destination.relative_to(racine) if destination.is_relative_to(racine) else destination), n, charge, _maintenant()))
            fichiers += 1
    return fichiers, lignes_reach, ignorees


# --- recopie au manifeste --------------------------------------------------------------------

def recopier_manifestes(conn: sqlite3.Connection, channel: str,
                        racine: Path | None = None) -> int:
    """`manifest.resultats.metrics_7d/30d` ← `v_video_perf` (sommes des jours 0-6 et 0-29).

    Tient lieu de `perf_window` du contrat : la vue agrège, le manifeste en garde la copie
    avec `complete` (fenêtre close depuis plus de 72 h) et `day_count`. Rend le nombre de
    manifestes réécrits.
    """
    n = 0
    for v in conn.execute("SELECT * FROM v_video_perf WHERE channel_id = ?", (channel,)):
        chemins = RunPaths.depuis_video_id(v["video_id"], racine)
        if not chemins.manifest.is_file():
            continue
        manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
        res = manifeste.setdefault("resultats", {})
        res["youtube_video_id"] = v["youtube_video_id"]
        if v["publish_status"] == "public":
            res["published_at"] = v["publish_at"]
        commun = {"pulled_at": _maintenant(), "day_count": v["days_pulled"],
                  "retention_curve_ref": f"retention_curves:{v['video_id']}"}
        res["metrics_7d"] = {**commun, "views": v["views_7d"], "watch_time_min": v["minutes_7d"],
                             "avg_view_duration_s": v["avg_view_duration_7d"],
                             "avg_view_percentage": v["avg_view_pct_7d"],
                             "subscribers_gained": v["subs_7d"],
                             "impressions": v["impressions_7d"], "ctr": v["ctr_7d"],
                             "complete": bool(v["complete_7d"])}
        res["metrics_30d"] = {**commun, "views": v["views_30d"],
                              "subscribers_gained": v["subs_30d"],
                              "complete": bool(v["complete_30d"])}
        texte = json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n"
        chemins.manifest.write_text(texte, encoding="utf-8")
        conn.execute("UPDATE runs SET manifest_json = ?, youtube_video_id = ?, "
                     "published_at = coalesce(?, published_at) WHERE video_id = ?",
                     (texte, v["youtube_video_id"], res.get("published_at"), v["video_id"]))
        n += 1
    return n


# --- orchestration ---------------------------------------------------------------------------

def tirer_chaine(conn: sqlite3.Connection, channel: str, *, racine: Path,
                 depuis: date | None = None, analytics: Any = None, reporting: Any = None,
                 telecharger: Callable[[str, str, Path], None] | None = None,
                 aujourd_hui: date | None = None, manifestes: bool = True) -> Bilan:
    """Un passage complet sur une chaîne ; les erreurs sont rendues, jamais levées."""
    bilan = Bilan(channel)
    aujourd_hui = aujourd_hui or _aujourdhui()
    compter = _Compteur(conn, bilan, quota.Plafonds.depuis_config(racine))
    debut_run = _maintenant()
    pubs = conn.execute(
        "SELECT * FROM publications WHERE channel_id = ? AND youtube_video_id IS NOT NULL "
        "AND status != 'failed' ORDER BY publish_at", (channel,)).fetchall()
    bilan.videos = len(pubs)
    try:
        analytics = analytics or client_analytics(channel, racine)
    except Exception as erreur:  # noqa: BLE001
        bilan.erreurs.append(f"client Analytics : {erreur}")
    if analytics is not None:
        for pub in pubs:
            try:
                n, c = tirer_video(conn, analytics, compter, pub, depuis=depuis,
                                   aujourd_hui=aujourd_hui)
                bilan.rows += n
                bilan.curves += c
            except Exception as erreur:  # noqa: BLE001 — une vidéo en échec n'arrête pas la chaîne
                bilan.erreurs.append(f"{pub['video_id']} : {type(erreur).__name__} {erreur}"[:300])
    try:
        reporting = reporting or rj.service(channel, racine)
        correspondance = {p["youtube_video_id"]: p["video_id"] for p in pubs}
        telecharger = telecharger or (lambda ch, url, dest: telecharger_http(ch, url, dest, racine))
        f, r, ign = tirer_rapports(conn, reporting, compter, channel, racine=racine,
                                   telecharger=telecharger, correspondance=correspondance)
        bilan.reports, bilan.reach_rows, bilan.skipped = f, r, ign
        bilan.rows += r
    except Exception as erreur:  # noqa: BLE001
        bilan.erreurs.append(f"Reporting API : {type(erreur).__name__} {erreur}"[:300])
    try:
        if manifestes:
            recopier_manifestes(conn, channel, racine)
    except Exception as erreur:  # noqa: BLE001
        bilan.erreurs.append(f"recopie manifeste : {type(erreur).__name__} {erreur}"[:300])
    if bilan.erreurs:
        bilan.status = "partial" if (bilan.rows or bilan.reports) else "error"
    conn.execute(
        "INSERT INTO analytics_runs (date, channel_id, rows, status, error, calls, skipped, "
        "started_at, ended_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (aujourd_hui.isoformat(), channel, bilan.rows, bilan.status,
         " | ".join(bilan.erreurs)[:2000] or None, bilan.calls, bilan.skipped, debut_run,
         _maintenant()))
    journaliser(f"analytics {channel} : {bilan.status}, {bilan.videos} vidéos, "
                f"{bilan.rows} lignes, {bilan.curves} courbes, {bilan.reports} rapports, "
                f"{bilan.calls} appels", racine)
    return bilan


def tirer(channels: list[str] | None = None, *, depuis: date | None = None,
          racine: Path | None = None, conn: sqlite3.Connection | None = None) -> list[Bilan]:
    """Toutes les chaînes authentifiées (ou celles demandées). Aucune n'est consentie ici."""
    racine = racine or racine_projet()
    cibles = channels or rj.chaines_authentifiees(racine)
    fermer = conn is None
    conn = conn or db_module.ouvrir()
    try:
        bilans = []
        for nom in cibles:
            if not oauth.chemin_jeton(nom, racine).is_file():
                b = Bilan(nom, status="skipped", erreurs=["aucun jeton OAuth"])
                conn.execute(
                    "INSERT INTO analytics_runs (date, channel_id, rows, status, error, "
                    "started_at, ended_at) VALUES (?,?,0,'skipped',?,?,?)",
                    (_aujourdhui().isoformat(), nom, b.erreurs[0], _maintenant(), _maintenant()))
                bilans.append(b)
                continue
            bilans.append(tirer_chaine(conn, nom, racine=racine, depuis=depuis))
        if not cibles:
            conn.execute(
                "INSERT INTO analytics_runs (date, channel_id, rows, status, error, started_at, "
                "ended_at) VALUES (?, '*', 0, 'skipped', ?, ?, ?)",
                (_aujourdhui().isoformat(), "aucune chaîne authentifiée (secrets/tokens/ vide)",
                 _maintenant(), _maintenant()))
            journaliser("analytics : aucune chaîne authentifiée", racine)
        return bilans
    finally:
        if fermer:
            conn.close()
