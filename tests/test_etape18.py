"""Étape 18 — entrepôt concurrentiel : schéma, vues de vélocité, collecte, purge.

Aucun appel réseau : la collecte est jouée contre un faux client qui rend la
forme exacte de l'API Data v3. Les vues de vélocité sont éprouvées sur des
instantanés injectés à plusieurs jours — ce que la première collecte réelle ne
peut pas produire, puisqu'elle n'écrit qu'un seul jour.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from factory.core import db
from factory.editorial import collect as ed
from factory.editorial import yt_api



@pytest.fixture(autouse=True)
def _reports_hors_du_depot(tmp_path, monkeypatch):
    """Aucun test n'écrit dans `reports/` du dépôt.

    `collect.ecrire_rapport()` écrivait dans `racine_projet()/reports` : **chaque passage de ce
    fichier réécrivait le vrai rapport de collecte du jour** avec les chiffres du faux client —
    constaté deux fois, le 20/09/2026, le fichier passant de la vraie collecte de 07:52 à un
    test de 13:26 sans qu'aucune ligne n'entre en base. La fonction accepte maintenant une
    racine ; cette fixture la pose pour tout le module, y compris pour les tests à venir.
    """
    monkeypatch.setattr("factory.editorial.collect.racine_projet", lambda: tmp_path)


@pytest.fixture
def conn(tmp_path) -> sqlite3.Connection:
    return db.ouvrir(tmp_path / "factory.db")


def _jour(decalage: int) -> str:
    return (datetime.now(UTC) + timedelta(days=decalage)).strftime("%Y-%m-%d")


def _ts(decalage_jours: float) -> str:
    return (datetime.now(UTC) + timedelta(days=decalage_jours)).isoformat(timespec="seconds")


def _video(conn, video_id: str, channel_id: str, age_jours: float) -> None:
    conn.execute(
        "INSERT INTO videos_ext (video_id, channel_id, published_at, title, description_head,"
        " duration_s, tags_json, category_id, thumbnail_url, first_seen_at, last_seen_at)"
        " VALUES (?,?,?,?,'',600,NULL,'27','',?,?)",
        (video_id, channel_id, _ts(-age_jours), f"titre {video_id}", _ts(0), _ts(0)),
    )


def _snap(conn, video_id: str, age_au_moment: float, vues: int) -> None:
    """Un instantané pris quand la vidéo avait `age_au_moment` jours."""
    ligne = conn.execute(
        "SELECT published_at FROM videos_ext WHERE video_id = ?", (video_id,)
    ).fetchone()
    publie = datetime.fromisoformat(ligne["published_at"])
    pris = publie + timedelta(days=age_au_moment)
    conn.execute(
        "INSERT INTO video_snapshots (video_id, snapshot_date, views, likes, comments, fetched_at)"
        " VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(video_id, snapshot_date) DO UPDATE SET views = excluded.views,"
        " fetched_at = excluded.fetched_at",
        (video_id, pris.strftime("%Y-%m-%d"), vues, 0, 0, pris.isoformat(timespec="seconds")),
    )


# ------------------------------------------------------------------- schéma


def test_migration_004_pose_les_tables_et_les_vues(conn):
    tables = db.tables(conn)
    for attendue in (
        "channels_watch", "videos_ext", "video_snapshots", "channel_snapshots", "collect_runs"
    ):
        assert attendue in tables
    vues = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert "v_video_velocity" in vues


def test_index_demandes_presents(conn):
    index = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    assert "ix_videos_ext_channel_pub" in index
    # (video_id, snapshot_date) est la clé primaire : SQLite en fait un index.
    info = list(conn.execute("PRAGMA index_list('video_snapshots')"))
    pk = [r for r in info if r["origin"] == "pk"]
    assert pk, "pas d'index de clé primaire sur video_snapshots"
    colonnes = [r["name"] for r in conn.execute(f"PRAGMA index_info('{pk[0]['name']}')")]
    assert colonnes == ["video_id", "snapshot_date"]


# -------------------------------------------------------- vues de vélocité


def test_interpolation_des_vues_a_un_age_cible(conn):
    _video(conn, "v1", "UC0", age_jours=40)
    _snap(conn, "v1", 0.0, 0)
    _snap(conn, "v1", 2.0, 200)  # 100 vues/jour entre 0 et 2
    _snap(conn, "v1", 10.0, 1000)

    lignes = {
        r["age_cible"]: r["views"]
        for r in conn.execute("SELECT age_cible, views FROM v_video_views_at WHERE video_id='v1'")
    }
    assert lignes[1.0] == pytest.approx(100, abs=1)  # interpolé entre 0 et 200
    assert lignes[7.0] == pytest.approx(700, abs=2)  # 200 + 800 × (7−2)/(10−2)
    assert lignes[30.0] is None  # pas d'instantané au-delà de j10 : rien à interpoler


def test_pas_d_extrapolation_sans_encadrement(conn):
    _video(conn, "v2", "UC0", age_jours=3)
    _snap(conn, "v2", 3.0, 500)  # un seul instantané
    lignes = {
        r["age_cible"]: r["views"]
        for r in conn.execute("SELECT age_cible, views FROM v_video_views_at WHERE video_id='v2'")
    }
    assert lignes == {1.0: None, 7.0: None, 30.0: None}


def test_velocite_7j_est_delta_vues_sur_delta_jours(conn):
    _video(conn, "v3", "UC0", age_jours=10)
    _snap(conn, "v3", 7.0, 1000)  # il y a 3 jours
    _snap(conn, "v3", 10.0, 1900)  # aujourd'hui : +900 en 3 jours
    ligne = conn.execute(
        "SELECT velocity_7d, velocity_source, velocity FROM v_video_velocity WHERE video_id='v3'"
    ).fetchone()
    assert ligne["velocity_7d"] == pytest.approx(300, abs=1)
    assert ligne["velocity_source"] == "7d"
    assert ligne["velocity"] == pytest.approx(300, abs=1)


def test_un_seul_instantane_donne_la_vitesse_moyenne_et_le_dit(conn):
    _video(conn, "v4", "UC0", age_jours=4)
    _snap(conn, "v4", 4.0, 800)
    ligne = conn.execute(
        "SELECT velocity_7d, velocity_life, velocity, velocity_source"
        " FROM v_video_velocity WHERE video_id='v4'"
    ).fetchone()
    assert ligne["velocity_7d"] is None
    assert ligne["velocity_life"] == pytest.approx(200, abs=1)
    assert ligne["velocity"] == pytest.approx(200, abs=1)
    assert ligne["velocity_source"] == "life"


def test_ratio_contre_la_mediane_de_la_chaine_a_age_egal(conn):
    # Trois vidéos de la même chaîne, même tranche d'âge (0-7 j) : 100, 200, 600 vues/j.
    for nom, vues in (("a", 100), ("b", 200), ("c", 600)):
        _video(conn, nom, "UC1", age_jours=1)
        _snap(conn, nom, 1.0, vues)
    # Une vidéo d'une autre tranche d'âge ne doit pas peser sur la médiane.
    _video(conn, "vieux", "UC1", age_jours=200)
    _snap(conn, "vieux", 200.0, 2_000_000)

    lignes = {
        r["video_id"]: r["ratio"]
        for r in conn.execute("SELECT video_id, ratio FROM v_video_velocity WHERE channel_id='UC1'")
    }
    assert lignes["b"] == pytest.approx(1.0, abs=0.01)  # la médiane elle-même
    assert lignes["c"] == pytest.approx(3.0, abs=0.01)
    assert lignes["a"] == pytest.approx(0.5, abs=0.01)


def test_top_trie_par_velocite_et_filtre(conn):
    conn.execute(
        "INSERT INTO channels_watch (channel_id, title, niche, lang, source, active, added_at)"
        " VALUES ('UC1','Chaîne A','science_pop','en','registre',1,?)", (_ts(0),)
    )
    conn.execute(
        "INSERT INTO channels_watch (channel_id, title, niche, lang, source, active, added_at)"
        " VALUES ('UC2','Chaîne B','true_crime','fr','registre',1,?)", (_ts(0),)
    )
    _video(conn, "rapide", "UC1", age_jours=2)
    _snap(conn, "rapide", 2.0, 10_000)
    _video(conn, "lente", "UC1", age_jours=2)
    _snap(conn, "lente", 2.0, 100)
    _video(conn, "autre", "UC2", age_jours=2)
    _snap(conn, "autre", 2.0, 50_000)
    _video(conn, "ancienne", "UC1", age_jours=90)
    _snap(conn, "ancienne", 90.0, 900_000)

    lignes = ed.top(conn, niche="science_pop", fenetre="30d")
    assert [r["video_id"] for r in lignes] == ["rapide", "lente"]  # « ancienne » hors fenêtre
    assert ed.top(conn, niche="science_pop", fenetre="30d", lang="fr") == []
    assert [r["video_id"] for r in ed.top(conn, fenetre="30d", limite=1)] == ["autre"]


@pytest.mark.parametrize("texte", ["", "abc", "0d", "-3d", "30j"])
def test_fenetre_invalide_refusee(texte):
    with pytest.raises(ValueError):
        ed.parse_fenetre(texte)


def test_fenetre_valide():
    assert ed.parse_fenetre("30d") == 30
    assert ed.parse_fenetre("7") == 7


# ------------------------------------------------------------------ quota


def test_compteur_refuse_avant_de_depasser():
    c = yt_api.Compteur(3)
    c.depense(2, "a")
    with pytest.raises(yt_api.QuotaAtteint):
        c.depense(2, "a")
    assert c.unites == 2  # rien n'a été consommé par l'appel refusé


def test_les_deux_compartiments_sont_independants():
    c = yt_api.Compteur(2)
    c.depense(2, "videos.list")
    c.depense(2, "videos.batchGetStats", batch=True)  # autre compartiment : passe
    assert (c.unites, c.unites_batch, c.total) == (2, 2, 4)
    with pytest.raises(yt_api.QuotaAtteint):
        c.depense(1, "videos.batchGetStats", batch=True)


def test_echantillon_tournant_couvre_tout_en_dix_jours():
    ids = [f"vid{i:04d}" for i in range(500)]
    vus: set[str] = set()
    tailles = []
    for jour in range(10):
        lot = ed._echantillon_du_jour(ids, jour)
        tailles.append(len(lot))
        vus.update(lot)
    assert vus == set(ids), "la rotation doit couvrir toutes les vidéos en 10 jours"
    assert all(20 <= t <= 80 for t in tailles), tailles  # ~10 % chacun
    # déterministe : deux appels le même jour donnent le même lot
    assert ed._echantillon_du_jour(ids, 3) == ed._echantillon_du_jour(ids, 3)


# ---------------------------------------------------------------- faux client


class FauxAppel:
    def __init__(self, charge):
        self._charge = charge

    def execute(self):
        return self._charge


class FauxVideos:
    def __init__(self, parent, avec_batch: bool):
        self._p = parent
        if avec_batch:
            self.batchGetStats = self._batch  # noqa: N815 — nom imposé par l'API

    def list(self, *, part, id, maxResults=None):  # noqa: A002, N803
        self._p.appels.append(("videos.list", part))
        ids = id.split(",")
        return FauxAppel({"items": [self._p.catalogue[v] for v in ids if v in self._p.catalogue]})

    def _batch(self, *, part, id):  # noqa: A002
        self._p.appels.append(("videos.batchGetStats", part))
        ids = id.split(",")
        return FauxAppel(
            {
                "items": [
                    {"id": v, "statistics": self._p.catalogue[v]["statistics"]}
                    for v in ids
                    if v in self._p.catalogue
                ]
            }
        )


class FauxYT:
    """Rend la forme exacte de l'API Data v3, sans réseau."""

    def __init__(self, *, chaines, videos, par_chaine, avec_batch=False):
        self.chaines, self.catalogue, self.par_chaine = chaines, videos, par_chaine
        self.avec_batch = avec_batch
        self.appels: list[tuple[str, str]] = []

    def channels(self):
        parent = self

        class C:
            def list(self, *, part, id, maxResults=None):  # noqa: A002, N803
                parent.appels.append(("channels.list", part))
                ids = id.split(",") if id else []
                return FauxAppel({"items": [parent.chaines[c] for c in ids if c in parent.chaines]})

        return C()

    def playlistItems(self):  # noqa: N802 — nom imposé par l'API
        parent = self

        class P:
            def list(self, *, part, playlistId, maxResults, pageToken=None):  # noqa: N803
                parent.appels.append(("playlistItems.list", part))
                tous = parent.par_chaine[playlistId]
                debut = int(pageToken or 0)
                page = tous[debut : debut + maxResults]
                suite = debut + maxResults
                return FauxAppel(
                    {
                        "items": [
                            {"contentDetails": {"videoId": v}, "status": {"privacyStatus": "public"}}
                            for v in page
                        ],
                        **({"nextPageToken": str(suite)} if suite < len(tous) else {}),
                    }
                )

        return P()

    def videos(self):
        return FauxVideos(self, self.avec_batch)


def _faux_monde(n_videos: int = 120, avec_batch: bool = False) -> FauxYT:
    chaines = {
        "UCtest0000000000000000": {
            "id": "UCtest0000000000000000",
            "snippet": {"title": "Chaîne test", "customUrl": "@test"},
            "statistics": {"subscriberCount": "12300", "viewCount": "4500000", "videoCount": "321"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UUtest"}},
        }
    }
    videos = {}
    for i in range(n_videos):
        vid = f"vid{i:05d}"
        age = i  # la vidéo i a i jours
        videos[vid] = {
            "id": vid,
            "snippet": {
                "channelId": "UCtest0000000000000000",
                "publishedAt": _ts(-age),
                "title": f"Vidéo {i}",
                "description": "d" * 400,
                "tags": ["a", "b"],
                "categoryId": "27",
                "thumbnails": {"high": {"url": f"https://i.ytimg.com/vi/{vid}/hq.jpg"}},
            },
            "contentDetails": {"duration": "PT10M30S"},
            "statistics": {
                "viewCount": str(1000 + i),
                "likeCount": str(10 + i),
                "commentCount": str(i),
            },
        }
    return FauxYT(
        chaines=chaines,
        videos=videos,
        par_chaine={"UUtest": list(videos)},
        avec_batch=avec_batch,
    )


@pytest.fixture
def base_suivie(conn):
    conn.execute(
        "INSERT INTO channels_watch (channel_id, title, niche, lang, source, active, added_at)"
        " VALUES ('UCtest0000000000000000','Chaîne test','science_pop','en','registre',1,?)",
        (_ts(0),),
    )
    return conn


# -------------------------------------------------------------------- collecte


def test_collecte_backfill_ecrit_tout(base_suivie):
    yt = _faux_monde()
    r = ed.collecter(base_suivie, client=yt, echo=None)

    assert r.chaines_faites == 1
    # backfill : 200 vidéos au plus, 4 pages de 50 ; le faux monde en a 120
    assert r.videos_nouvelles == 120
    (n,) = base_suivie.execute("SELECT COUNT(*) FROM videos_ext").fetchone()
    assert n == 120
    (n,) = base_suivie.execute("SELECT COUNT(*) FROM video_snapshots").fetchone()
    assert n == 120
    (n,) = base_suivie.execute("SELECT COUNT(*) FROM channel_snapshots").fetchone()
    assert n == 1
    ligne = base_suivie.execute("SELECT * FROM collect_runs").fetchone()
    assert ligne["channels_done"] == 1 and ligne["videos_new"] == 120
    assert ligne["units_used"] == r.unites + r.unites_batch

    # description tronquée à 200 caractères, durée convertie
    v = base_suivie.execute("SELECT * FROM videos_ext LIMIT 1").fetchone()
    assert len(v["description_head"]) == 200
    assert v["duration_s"] == 630


def test_reprise_saute_les_chaines_deja_faites_et_force_les_reprend(base_suivie):
    ed.collecter(base_suivie, client=_faux_monde(), echo=None)
    r2 = ed.collecter(base_suivie, client=_faux_monde(), echo=None)
    assert r2.chaines_faites == 0 and r2.chaines_sautees == 1
    assert r2.unites == 0  # aucun appel : la reprise ne coûte rien

    r3 = ed.collecter(base_suivie, client=_faux_monde(), echo=None, force=True)
    assert r3.chaines_faites == 1 and r3.videos_nouvelles == 0
    assert r3.unites > 0
    (n,) = base_suivie.execute("SELECT COUNT(*) FROM collect_runs").fetchone()
    assert n == 3  # trois passes, trois lignes, même date


def test_deuxieme_passe_rafraichit_l_instantane_du_jour_sans_doublon(base_suivie):
    ed.collecter(base_suivie, client=_faux_monde(), echo=None)
    monde = _faux_monde()
    monde.catalogue["vid00000"]["statistics"]["viewCount"] = "999999"
    ed.collecter(base_suivie, client=monde, echo=None, force=True)

    lignes = list(
        base_suivie.execute("SELECT * FROM video_snapshots WHERE video_id='vid00000'")
    )
    assert len(lignes) == 1, "un instantané par vidéo et par jour"
    assert lignes[0]["views"] == 999999


def test_passe_quotidienne_ne_lit_qu_une_page(base_suivie):
    ed.collecter(base_suivie, client=_faux_monde(), echo=None)  # backfill : 3 pages
    monde = _faux_monde()
    ed.collecter(base_suivie, client=monde, echo=None, force=True)
    pages = [a for a in monde.appels if a[0] == "playlistItems.list"]
    assert len(pages) == 1


def test_arret_propre_au_plafond(base_suivie):
    yt = _faux_monde()
    r = ed.collecter(base_suivie, client=yt, echo=None, max_units=2)
    assert r.arret_quota is True
    assert r.unites <= 2
    ligne = base_suivie.execute("SELECT * FROM collect_runs").fetchone()
    assert ligne is not None and "ARRÊT_QUOTA" in ligne["note"]
    # la chaîne n'est pas marquée faite : la prochaine passe la reprendra
    (fait,) = base_suivie.execute(
        "SELECT last_collect_date FROM channels_watch"
    ).fetchone()
    assert fait is None


def test_batchgetstats_utilise_quand_l_api_l_expose(base_suivie):
    ed.collecter(base_suivie, client=_faux_monde(avec_batch=True), echo=None)
    monde = _faux_monde(avec_batch=True)
    r = ed.collecter(base_suivie, client=monde, echo=None, force=True)
    assert r.methode_stats == "videos.batchGetStats"
    assert any(a[0] == "videos.batchGetStats" for a in monde.appels)
    assert r.unites_batch > 0


def test_repli_sur_videos_list_sans_batchgetstats(base_suivie):
    ed.collecter(base_suivie, client=_faux_monde(avec_batch=False), echo=None)
    monde = _faux_monde(avec_batch=False)
    r = ed.collecter(base_suivie, client=monde, echo=None, force=True)
    assert r.methode_stats == "videos.list"
    assert r.unites_batch == 0
    assert any(a[1] == "id,statistics" for a in monde.appels)


def test_chaine_absente_de_la_reponse_est_une_erreur_pas_un_plantage(base_suivie):
    base_suivie.execute(
        "INSERT INTO channels_watch (channel_id, source, active, added_at)"
        " VALUES ('UCdisparue000000000000','ajout',1,?)", (_ts(0),)
    )
    r = ed.collecter(base_suivie, client=_faux_monde(), echo=None)
    assert r.chaines_faites == 1
    assert any("UCdisparue" in e for e in r.erreurs)


def test_rapport_markdown_ecrit(base_suivie, tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    r = ed.collecter(base_suivie, client=_faux_monde(), echo=None)
    chemin = tmp_path / "reports" / f"collect_{r.date}.md"
    assert chemin.exists()
    texte = chemin.read_text(encoding="utf-8")
    assert "Vidéos nouvelles | 120" in texte
    assert "batchGetStats" in texte


# --------------------------------------------------------------------- watch


def test_import_du_registre_idempotent(conn, tmp_path):
    csv = tmp_path / "chaines.csv"
    csv.write_text(
        "handle_ou_url,nom,niche,langue\n"
        "https://www.youtube.com/channel/UCaG7EroyixUjRKZF-FnVq4Q,Library of Thoth,spiritualite,en\n"
        "https://www.youtube.com/@sans-identifiant,Sans ID,science_pop,en\n",
        encoding="utf-8",
    )
    ajoutees, non_resolues = ed.importer_registre(conn, csv)
    assert ajoutees == 1 and non_resolues == ["Sans ID"]
    ajoutees2, _ = ed.importer_registre(conn, csv)
    assert ajoutees2 == 0
    (n,) = conn.execute("SELECT COUNT(*) FROM channels_watch").fetchone()
    assert n == 1


def test_watch_add_refuse_un_handle_sans_identifiant(conn):
    with pytest.raises(ValueError, match="handle"):
        ed.watch_add(conn, "https://www.youtube.com/@veritasium", niche=None, lang=None)


def test_watch_add_et_remove(conn):
    cid = ed.watch_add(
        conn, "https://www.youtube.com/channel/UCaG7EroyixUjRKZF-FnVq4Q", niche="n", lang="en"
    )
    assert cid == "UCaG7EroyixUjRKZF-FnVq4Q"
    assert len(ed.watch_list(conn)) == 1
    ed.watch_remove(conn, cid)
    assert ed.watch_list(conn) == []
    assert len(ed.watch_list(conn, toutes=True)) == 1


def test_chaine_desactivee_n_est_plus_collectee(base_suivie):
    ed.watch_remove(base_suivie, "UCtest0000000000000000")
    r = ed.collecter(base_suivie, client=_faux_monde(), echo=None)
    assert r.chaines_total == 0 and r.unites == 0


# --------------------------------------------------------------------- purge


def test_purge_supprime_les_instantanes_de_plus_de_30_jours(conn):
    _video(conn, "vieille", "UC0", age_jours=100)
    conn.execute(
        "INSERT INTO video_snapshots (video_id, snapshot_date, views, likes, comments, fetched_at)"
        " VALUES ('vieille',?,10,0,0,?)", (_jour(-40), _ts(-40)),
    )
    conn.execute(
        "INSERT INTO video_snapshots (video_id, snapshot_date, views, likes, comments, fetched_at)"
        " VALUES ('vieille',?,20,0,0,?)", (_jour(-2), _ts(-2)),
    )
    conn.execute(
        "INSERT INTO channel_snapshots (channel_id, snapshot_date, subscribers, views,"
        " video_count, fetched_at) VALUES ('UC0',?,1,1,1,?)", (_jour(-40), _ts(-40)),
    )

    p = ed.purger(conn, simulation=True)
    assert (p.instantanes_video, p.instantanes_chaine) == (1, 1)
    (reste,) = conn.execute("SELECT COUNT(*) FROM video_snapshots").fetchone()
    assert reste == 2, "la simulation ne supprime rien"

    ed.purger(conn)
    dates = [r[0] for r in conn.execute("SELECT snapshot_date FROM video_snapshots")]
    assert dates == [_jour(-2)]
    (n,) = conn.execute("SELECT COUNT(*) FROM channel_snapshots").fetchone()
    assert n == 0


def test_purge_supprime_une_video_qui_n_est_plus_rafraichie(conn):
    _video(conn, "supprimee", "UC0", age_jours=100)
    conn.execute("UPDATE videos_ext SET last_seen_at = ? WHERE video_id='supprimee'", (_ts(-45),))
    _video(conn, "vivante", "UC0", age_jours=100)
    p = ed.purger(conn)
    assert p.videos == 1
    restantes = [r[0] for r in conn.execute("SELECT video_id FROM videos_ext")]
    assert restantes == ["vivante"]


def test_purge_consolide_les_mesures_avant_de_supprimer(conn):
    _video(conn, "v", "UC0", age_jours=10)
    _snap(conn, "v", 7.0, 1000)
    _snap(conn, "v", 10.0, 1900)
    p = ed.purger(conn)
    assert p.metriques_consolidees == 1
    m = conn.execute("SELECT * FROM video_metrics WHERE video_id='v'").fetchone()
    assert m["velocity_7d"] == pytest.approx(300, abs=1)
    assert m["n_snapshots"] == 2


def test_purge_stricte_vide_les_mesures_derivees(conn):
    _video(conn, "v", "UC0", age_jours=10)
    _snap(conn, "v", 7.0, 1000)
    _snap(conn, "v", 10.0, 1900)
    ed.purger(conn)
    (avant,) = conn.execute("SELECT COUNT(*) FROM video_metrics").fetchone()
    assert avant == 1
    p = ed.purger(conn, strict=True)
    assert p.metriques_supprimees == 1
    (apres,) = conn.execute("SELECT COUNT(*) FROM video_metrics").fetchone()
    assert apres == 0


# ------------------------------------------------------------- planification


def test_plist_ecrit_entre_3h_et_5h(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "factory").write_text("#!/bin/sh\n")
    monkeypatch.setattr(ed.Path, "home", staticmethod(lambda: tmp_path / "home"))
    for _ in range(20):
        chemin, heure, minute = ed.ecrire_plist()
        assert heure in (3, 4)
        assert 0 <= minute <= 59
    texte = chemin.read_text(encoding="utf-8")
    assert "com.bms.factory.collect" in texte
    assert str(tmp_path) in texte
    assert "collect_launchd.log" in texte
    assert "<string>editorial</string>" in texte


def test_plist_refuse_sans_executable(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    monkeypatch.setattr(ed.Path, "home", staticmethod(lambda: tmp_path / "home"))
    with pytest.raises(FileNotFoundError):
        ed.ecrire_plist()


# ------------------------------------------------------------- normalisation


def test_normalise_video_tronque_et_convertit():
    item = {
        "id": "x",
        "snippet": {
            "channelId": "UC0",
            "publishedAt": "2026-01-01T00:00:00Z",
            "title": "T",
            "description": "z" * 500,
            "categoryId": "27",
            "thumbnails": {"default": {"url": "d"}, "maxres": {"url": "m"}},
        },
        "contentDetails": {"duration": "PT1H2M3S"},
        "statistics": {"viewCount": "42", "commentCount": "3"},
    }
    v = yt_api.normalise_video(item)
    assert len(v["description_head"]) == 200
    assert v["duration_s"] == 3723
    assert v["thumbnail_url"] == "m"  # la meilleure définition disponible
    assert v["views"] == 42
    assert v["likes"] is None  # likeCount absent : NULL, pas 0


@pytest.mark.parametrize(
    "iso,attendu",
    [("PT10M30S", 630), ("PT1H", 3600), ("P1DT2H", 93600), ("PT45S", 45), ("", None)],
)
def test_duree_iso(iso, attendu):
    assert yt_api.iso_duration_seconds(iso) == attendu


def test_channel_id_of():
    assert (
        yt_api.channel_id_of("https://www.youtube.com/channel/UCaG7EroyixUjRKZF-FnVq4Q")
        == "UCaG7EroyixUjRKZF-FnVq4Q"
    )
    assert yt_api.channel_id_of("https://www.youtube.com/@veritasium") is None


def test_reinstaller_ne_deplace_pas_l_heure(tmp_path, monkeypatch):
    """Revérifier l'accès disque impose de réinstaller : l'horaire doit tenir."""
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "factory").write_text("#!/bin/sh\n")
    monkeypatch.setattr(ed.Path, "home", staticmethod(lambda: tmp_path / "home"))
    _, h1, m1 = ed.ecrire_plist()
    for _ in range(10):
        _, h2, m2 = ed.ecrire_plist()
        assert (h2, m2) == (h1, m1)
    _, h3, m3 = ed.ecrire_plist(heure=4, minute=17)
    assert (h3, m3) == (4, 17)  # une valeur explicite l'emporte
