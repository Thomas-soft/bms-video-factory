"""Étape 25 — performances jointes au manifeste, prouvées sur API factice."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from factory.analytics import pull, show
from factory.core import db as db_module
from factory.core.paths import racine_projet

RUN = "bms-science-en-20260920-s57f"
YT = "abcDEF12345"
AUJ = date(2026, 9, 23)
D0 = AUJ - timedelta(days=8)


class _Req:
    def __init__(self, reponse):
        self.reponse = reponse

    def execute(self):
        if isinstance(self.reponse, Exception):
            raise self.reponse
        return self.reponse


class FakeAnalytics:
    """Répond comme `youtubeAnalytics v2` ; refuse `engagedViews` si demandé."""

    def __init__(self, refuser_engaged=False):
        self.appels = []
        self.refuser_engaged = refuser_engaged

    def reports(self):
        return self

    def query(self, **p):
        self.appels.append(p)
        if p["dimensions"] == "day":
            if self.refuser_engaged and "engagedViews" in p["metrics"]:
                return _Req(RuntimeError("Unknown identifier (engagedViews)"))
            noms = ["day"] + p["metrics"].split(",")
            debut, fin = date.fromisoformat(p["startDate"]), date.fromisoformat(p["endDate"])
            lignes = []
            for i in range((fin - debut).days - 2):  # latence : 3 derniers jours absents
                j = debut + timedelta(days=i)
                lignes.append([j.isoformat()] + [10 + i] * (len(noms) - 1))
            return _Req({"columnHeaders": [{"name": n} for n in noms], "rows": lignes})
        if p["dimensions"] == "day,insightTrafficSourceType":
            return _Req({"columnHeaders": [{"name": n} for n in
                                           ("day", "insightTrafficSourceType", "views",
                                            "estimatedMinutesWatched")],
                         "rows": [[p["startDate"], "YT_SEARCH", 5, 2.5],
                                  [p["startDate"], "SUGGESTED", 7, 3.0]]})
        # rétention : 100 points, chute de 20 pts à 30 %
        pts = [[(i + 1) / 100, 1.0 - i * 0.003 - (0.2 if i >= 30 else 0), 0.5]
               for i in range(100)]
        return _Req({"columnHeaders": [{"name": n} for n in
                                       ("elapsedVideoTimeRatio", "audienceWatchRatio",
                                        "relativeRetentionPerformance")], "rows": pts})


class FakeReporting:
    def __init__(self, rapports):
        self.rapports = rapports

    def jobs(self):
        return self

    def reports(self):
        return self

    def list(self, jobId, pageToken=None):
        return _Req({"reports": self.rapports.get(jobId, [])})


@pytest.fixture
def conn(tmp_path):
    c = db_module.ouvrir(tmp_path / "f.db")
    reel = db_module.ouvrir()
    manifeste = reel.execute("SELECT manifest_json FROM runs WHERE video_id = ?",
                             (RUN,)).fetchone()[0]
    reel.close()
    c.execute("INSERT INTO runs (video_id, channel_id, lang, created_at, updated_at, "
              "manifest_json) VALUES (?, 'bms-science-en', 'en', 'x', 'x', ?)", (RUN, manifeste))
    c.execute("INSERT INTO publications (video_id, channel_id, youtube_video_id, status, "
              "publish_at, updated_at) VALUES (?, 'bms-science-en', ?, 'public', ?, 'x')",
              (RUN, YT, f"{D0.isoformat()}T16:00:00Z"))
    c.execute("INSERT INTO reporting_jobs (job_id, channel_id, report_type, created_at, "
              "seen_at) VALUES ('J1', 'bms-science-en', 'channel_reach_basic_a1', 'x', 'x')")
    return c


def _csv(tmp_path, jours, ctr=0.05):
    def ecrire(channel, url, dest):
        lignes = ["date,channel_id,video_id,video_thumbnail_impressions,"
                  "video_thumbnail_impressions_ctr"]
        for j in jours:
            lignes.append(f"{j.strftime('%Y%m%d')},UC1,{YT},100,{ctr}")
            lignes.append(f"{j.strftime('%Y%m%d')},UC1,{YT},300,{ctr * 2}")
            lignes.append(f"{j.strftime('%Y%m%d')},UC1,autreVideo,50,0.1")
        dest.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return ecrire


def _tirer(conn, tmp_path, monkeypatch, api, rapports, ecrire):
    monkeypatch.setattr(pull, "dossier_rapports", lambda racine=None: tmp_path / "reports")
    return pull.tirer_chaine(conn, "bms-science-en", racine=racine_projet(), analytics=api,
                             reporting=FakeReporting(rapports), telecharger=ecrire,
                             aujourd_hui=AUJ, manifestes=False)


def test_pull_complet(conn, tmp_path, monkeypatch):
    api = FakeAnalytics()
    rapports = {"J1": [{"id": "R1", "startTime": f"{D0}T07:00:00Z", "createTime": "a",
                        "downloadUrl": "u1"}]}
    b = _tirer(conn, tmp_path, monkeypatch, api, rapports, _csv(tmp_path, [D0, D0 + timedelta(1)]))
    assert b.status == "ok", b.erreurs
    # rattrapage depuis la publication au premier passage
    assert api.appels[0]["startDate"] == D0.isoformat()
    assert conn.execute("SELECT count(*) FROM perf_daily").fetchone()[0] == 6
    assert conn.execute("SELECT count(*) FROM perf_traffic").fetchone()[0] == 2
    # âge 8 j : J+7 capturée, J+2 sautée, J+30 pas encore
    assert [r[0] for r in conn.execute("SELECT day_after_publish FROM retention_curves")] == [7]
    pts = json.loads(conn.execute("SELECT points_json FROM retention_curves").fetchone()[0])
    assert len(pts) == 100
    # reach : 2 jours, CTR pondéré (100×0,05 + 300×0,10) / 400 = 0,0875 ; vidéo étrangère ignorée
    r = conn.execute("SELECT impressions, ctr FROM perf_reach ORDER BY date").fetchall()
    assert len(r) == 2 and r[0][0] == 400 and abs(r[0][1] - 0.0875) < 1e-9
    assert b.skipped == 2
    assert conn.execute("SELECT count(*) FROM quota_ledger WHERE call LIKE 'analytics%'"
                        ).fetchone()[0] == 3
    # second passage : fenêtre glissante de 5 jours, rapport déjà vu non retéléchargé
    api2 = FakeAnalytics()
    b2 = _tirer(conn, tmp_path, monkeypatch, api2, rapports,
                lambda *a: pytest.fail("rapport retéléchargé"))
    assert api2.appels[0]["startDate"] == (AUJ - timedelta(5)).isoformat()
    assert b2.reports == 0 and b2.curves == 0


def test_vue_facteurs_et_metriques(conn, tmp_path, monkeypatch):
    rapports = {"J1": [{"id": "R1", "startTime": f"{D0}T07:00:00Z", "createTime": "a",
                        "downloadUrl": "u"}]}
    _tirer(conn, tmp_path, monkeypatch, FakeAnalytics(), rapports, _csv(tmp_path, [D0]))
    v = conn.execute("SELECT * FROM v_video_perf").fetchone()
    facteurs = ["topic", "topic_cluster", "topic_source", "hook_type", "title_pattern",
                "thumbnail_template", "thumbnail_text_len", "style", "template_id",
                "cut_rhythm_target_s", "cut_rhythm_measured_s", "duration_s", "lang", "niche",
                "voice_id", "publish_weekday", "publish_hour", "density_facts_per_min",
                "qc_score"]
    assert all(v[f] is not None for f in facteurs), [f for f in facteurs if v[f] is None]
    assert v["title_pattern"] == "question_en_tete"
    assert v["thumbnail_template"] == "bandeau_bas" and v["is_child"] == 0
    assert v["views_7d"] == 10 + 11 + 12 + 13 + 14 + 15  # jours 0 à 5 relevés
    assert v["impressions_7d"] == 400


def test_engaged_views_refusee(conn, tmp_path, monkeypatch):
    b = _tirer(conn, tmp_path, monkeypatch, FakeAnalytics(refuser_engaged=True), {}, None)
    assert b.status == "ok"
    assert conn.execute("SELECT count(*) FROM perf_daily WHERE engaged_views IS NULL"
                        ).fetchone()[0] == 6


def test_erreur_toleree(conn, tmp_path, monkeypatch):
    class Casse(FakeAnalytics):
        def query(self, **p):
            return _Req(RuntimeError("quotaExceeded"))
    b = _tirer(conn, tmp_path, monkeypatch, Casse(), {}, None)
    assert b.status == "error" and "quotaExceeded" in b.erreurs[0]
    assert conn.execute("SELECT status FROM analytics_runs").fetchone()[0] == "error"


def test_show_chutes_rattachees(conn, tmp_path, monkeypatch):
    _tirer(conn, tmp_path, monkeypatch, FakeAnalytics(), {}, None)
    sortie = "\n".join(show.rapport_video(conn, YT))
    assert "█" in sortie
    assert "chute de 20 pts à" in sortie and "segment" in sortie and "rôle" in sortie


def test_latence_pas_de_zero(conn):
    conn.execute("UPDATE publications SET publish_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now', "
                 "'-20 hours')")
    assert "données provisoires" in "\n".join(show.rapport_video(conn, RUN))


def test_date_rapport():
    assert pull._date_rapport("20260920") == "2026-09-20"
    assert pull._date_rapport("2026-09-20") == "2026-09-20"


def test_recopie_manifeste(conn, tmp_path, monkeypatch):
    _tirer(conn, tmp_path, monkeypatch, FakeAnalytics(), {}, None)
    dossier = tmp_path / "workspace" / "runs" / RUN
    dossier.mkdir(parents=True)
    source = racine_projet() / "workspace" / "runs" / RUN / "manifest.json"
    (dossier / "manifest.json").write_text(source.read_text("utf-8"), "utf-8")
    assert pull.recopier_manifestes(conn, "bms-science-en", tmp_path) == 1
    res = json.loads((dossier / "manifest.json").read_text("utf-8"))["resultats"]
    assert res["youtube_video_id"] == YT and res["metrics_7d"]["views"] == 75
    assert res["published_at"].startswith(D0.isoformat())
    assert conn.execute("SELECT youtube_video_id FROM runs").fetchone()[0] == YT
