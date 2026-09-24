"""Étape 23.1 — publication par l'API, quota compartimenté, jobs de rapports.

Aucun de ces tests ne touche le réseau : un double d'API est injecté par `service=`. Ce
qu'ils prouvent n'est donc pas que YouTube accepte nos requêtes — seul un vrai jeton le
prouvera — mais que **le code fait ce qu'il dit** sur les points où une erreur coûte cher.

Cinq familles d'invariants.

- **Le quota est débité avant l'appel, et reste débité s'il échoue.** Google facture la
  tentative. Un ledger qui n'inscrirait que les succès ferait croire à du disponible qui ne
  l'est plus.
- **Les deux compartiments ne s'additionnent pas.** `videos.insert` coûte 1 unité d'uploads
  (100/jour) ; tout le reste tire sur les 10 000. Les confondre donne un solde faux dans les
  deux sens.
- **`publishAt` n'est pas envoyé tant que l'audit n'est pas passé.** YouTube ne l'honorerait
  pas ; la date resterait affichée comme une programmation qui n'existe pas.
- **`videos.update` écrase la partie qu'il vise.** Un `status` partiel retirerait le label de
  contenu synthétique — la faute la plus coûteuse de ce module.
- **Rien ne publie sans job de rapports.** Les impressions ne sont pas rétroactives.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from factory.core import db as db_module
from factory.core.paths import RunPaths, racine_projet
from factory.publish import quota
from factory.publish import reporting_jobs as rj
from factory.publish import youtube


# --------------------------------------------------------------------------------------
# Doubles d'API
# --------------------------------------------------------------------------------------


class RequeteFactice:
    """Ce que rend un `insert()` résumable : une requête qu'on avance fragment par fragment."""

    def __init__(self, reponse, fragments: int = 1):
        self._reponse = reponse
        self._restants = fragments

    def next_chunk(self):
        self._restants -= 1
        if self._restants > 0:
            return (_Progression(1 - self._restants / 3), None)
        return (None, self._reponse)

    def execute(self):
        return self._reponse


class _Progression:
    def __init__(self, part: float):
        self._part = part

    def progress(self) -> float:
        return self._part


class Ressource:
    """Une ressource d'API (`videos`, `thumbnails`…) dont chaque méthode est scriptée."""

    def __init__(self, api: YouTubeFactice, nom: str):
        self._api = api
        self._nom = nom

    def __getattr__(self, methode: str):
        def appel(**kwargs):
            self._api.appels.append((f"{self._nom}.{methode}", kwargs))
            reponse = self._api.reponses.get(f"{self._nom}.{methode}")
            if isinstance(reponse, Exception):
                raise reponse
            if callable(reponse):
                reponse = reponse(kwargs)
            if methode == "insert" and "media_body" in kwargs:
                return RequeteFactice(reponse)
            return RequeteFactice(reponse)
        return appel


class YouTubeFactice:
    """Un service d'API entièrement scripté : rien ne sort de la machine."""

    def __init__(self, reponses: dict | None = None):
        self.reponses: dict = reponses or {}
        self.appels: list[tuple[str, dict]] = []

    def videos(self):
        return Ressource(self, "videos")

    def thumbnails(self):
        return Ressource(self, "thumbnails")

    def captions(self):
        return Ressource(self, "captions")

    def playlistItems(self):  # noqa: N802 — nom de l'API Google
        return Ressource(self, "playlistItems")

    def jobs(self):
        return Ressource(self, "jobs")

    def reportTypes(self):  # noqa: N802 — nom de l'API Google
        return Ressource(self, "reportTypes")

    def corps(self, appel: str) -> dict:
        """Le corps envoyé lors du dernier appel de ce nom."""
        for nom, kwargs in reversed(self.appels):
            if nom == appel:
                return kwargs.get("body", {})
        raise AssertionError(f"{appel} n'a pas été appelé ({[n for n, _ in self.appels]})")

    def noms(self) -> list[str]:
        return [nom for nom, _ in self.appels]


def erreur_http(statut: int, motif: str = "forbidden", message: str = "refusé"):
    """Une `HttpError` crédible, avec le corps JSON que googleapiclient sait relire."""
    from googleapiclient.errors import HttpError

    class Reponse:
        status = statut
        reason = motif

    contenu = json.dumps(
        {"error": {"message": message, "errors": [{"reason": motif}]}}
    ).encode("utf-8")
    return HttpError(Reponse(), contenu)


VIDEO_EN_LIGNE = {
    "items": [{
        "id": "VID12345678",
        "snippet": {"title": "Mysteries of the Universe", "defaultLanguage": "en",
                    "defaultAudioLanguage": "en", "categoryId": "28",
                    "thumbnails": {"default": {}, "high": {}, "maxres": {}}},
        "status": {"privacyStatus": "private", "uploadStatus": "uploaded",
                   "madeForKids": False, "license": "youtube", "embeddable": True},
        "processingDetails": {"processingStatus": "succeeded"},
        "paidProductPlacementDetails": {"hasPaidProductPlacement": False},
    }]
}


# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------


@pytest.fixture
def racine(tmp_path: Path) -> Path:
    """Une racine de projet jetable, avec la vraie `config/` recopiée."""
    shutil.copytree(racine_projet() / "config", tmp_path / "config")
    (tmp_path / "workspace" / "logs").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def conn(racine: Path):
    """Une base neuve, migrations comprises."""
    connexion = db_module.ouvrir(racine / "workspace" / "factory.db")
    yield connexion
    connexion.close()


@pytest.fixture
def run(racine: Path) -> RunPaths:
    """Un run exporté de `bms-test` : vidéo, métadonnées, sous-titres, miniature, manifeste."""
    chemins = RunPaths.depuis_video_id("bms-test-20260922-aaaa", racine)
    chemins.racine.mkdir(parents=True)
    chemins.final.write_bytes(b"\x00" * 2048)
    chemins.thumbnail.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    chemins.subtitles_srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello.\n",
                                     encoding="utf-8")
    chemins.metadata.write_text(json.dumps({
        "title_chosen": "Mysteries of the Universe",
        "description": "AI-generated imagery.\n\nCorps.",
        "tags": ["space"], "category_id": "28",
        "default_language": "en", "default_audio_language": "en",
        "contains_synthetic_media": True,
        "made_for_kids": False, "paid_promotion": False, "notify_subscribers": False,
        "playlist_id": None,
        "caption_file": "subtitles.srt", "thumbnail_file": "thumbnail.png",
    }), encoding="utf-8")
    chemins.manifest.write_text(json.dumps({"resultats": {}}), encoding="utf-8")
    return chemins


@pytest.fixture
def api_ok() -> YouTubeFactice:
    return YouTubeFactice({
        "videos.insert": {"id": "VID12345678"},
        "videos.list": VIDEO_EN_LIGNE,
        "thumbnails.set": {"items": []},
        "captions.insert": {"id": "CAP987"},
        "playlistItems.insert": {"id": "PLI555"},
    })


def publier(run, racine, conn, api, **kwargs):
    return youtube.televerser("bms-test-20260922-aaaa", "bms-test", racine=racine,
                              conn=conn, service=api, **kwargs)


# --------------------------------------------------------------------------------------
# 1. Le quota est compté avant l'appel, par compartiment
# --------------------------------------------------------------------------------------


def test_les_deux_compartiments_ne_s_additionnent_pas():
    assert quota.cout("videos.insert") == ("uploads", 1)
    assert quota.cout("captions.insert") == ("units", 400)
    besoin = quota.cout_publication_complete()
    assert besoin["uploads"] == 1
    # 50 (miniature) + 400 (sous-titres) + 50 (playlist) + 1 (vérification).
    assert besoin["units"] == 501


def test_un_appel_sans_cout_connu_est_une_erreur_pas_un_zero():
    with pytest.raises(KeyError, match="coût inconnu"):
        quota.cout("videos.rate")


def test_le_ledger_enregistre_chaque_appel_avant_qu_il_soit_fait(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    lignes = conn.execute("SELECT call, compartment, units, ok FROM quota_ledger "
                          "ORDER BY id").fetchall()
    appels = [(l["call"], l["compartment"], l["units"]) for l in lignes]
    assert ("videos.insert", "uploads", 1) in appels
    assert ("thumbnails.set", "units", 50) in appels
    assert ("captions.insert", "units", 400) in appels
    assert ("videos.list", "units", 1) in appels
    assert all(l["ok"] == 1 for l in lignes)


def test_un_appel_refuse_reste_debite_et_marque_en_echec(run, racine, conn):
    api = YouTubeFactice({
        "videos.insert": {"id": "VID12345678"},
        "videos.list": VIDEO_EN_LIGNE,
        "thumbnails.set": erreur_http(403, "forbidden", "pas de miniature personnalisée"),
        "captions.insert": {"id": "CAP987"},
    })
    resultat = publier(run, racine, conn, api)
    ligne = conn.execute("SELECT ok, units, detail FROM quota_ledger "
                         "WHERE call = 'thumbnails.set'").fetchone()
    assert ligne["units"] == 50, "le quota d'un appel refusé reste dépensé"
    assert ligne["ok"] == 0
    assert "403" in (ligne["detail"] or "")
    assert resultat.thumbnail_set is False
    assert any("miniature refusée" in a for a in resultat.avertissements)


def test_le_plafond_refuse_proprement_sans_appeler_l_api(run, racine, conn, api_ok):
    plafonds = quota.Plafonds(uploads=80, units=8000)
    for _ in range(80):
        quota.consommer(conn, "videos.insert", plafonds=plafonds)
    with pytest.raises(quota.QuotaDepasse, match="upload"):
        publier(run, racine, conn, api_ok)
    assert api_ok.appels == [], "aucun appel ne doit partir quand le plafond est atteint"


def test_le_solde_se_lit_dans_la_base_pas_en_memoire(conn):
    plafonds = quota.Plafonds(uploads=80, units=8000)
    quota.consommer(conn, "captions.insert", plafonds=plafonds)
    quota.consommer(conn, "videos.insert", plafonds=plafonds)
    etat = quota.etat(conn, plafonds)
    assert etat.unites_utilisees == 400
    assert etat.uploads_utilises == 1
    assert etat.inserts == 1
    assert quota.publications_possibles(etat) == (8000 - 400) // 501


# --------------------------------------------------------------------------------------
# 2. Le corps de la requête
# --------------------------------------------------------------------------------------


def test_l_insert_porte_le_label_synthetique_et_le_prive(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    corps = api_ok.corps("videos.insert")
    assert corps["status"]["privacyStatus"] == "private"
    assert corps["status"]["containsSyntheticMedia"] is True
    assert corps["status"]["selfDeclaredMadeForKids"] is False
    assert corps["snippet"]["defaultLanguage"] == "en"
    assert corps["snippet"]["defaultAudioLanguage"] == "en"


def test_notify_subscribers_vient_du_run_pas_du_code(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    kwargs = [k for n, k in api_ok.appels if n == "videos.insert"][0]
    assert kwargs["notifySubscribers"] is False


def test_publish_at_n_est_pas_envoye_tant_que_l_audit_n_est_pas_passe(run, racine, conn, api_ok):
    resultat = publier(run, racine, conn, api_ok, publish_at="2026-12-01T16:00:00Z")
    assert "publishAt" not in api_ok.corps("videos.insert")["status"]
    assert resultat.publish_at == "2026-12-01T16:00:00Z", "la date est gardée comme intention"
    assert any("audit_passed est faux" in a for a in resultat.avertissements)


def test_publish_at_est_envoye_une_fois_l_audit_passe(run, racine, conn, api_ok):
    fichier = racine / "config" / "channels" / "bms-test.yaml"
    fichier.write_text(fichier.read_text(encoding="utf-8")
                       .replace("audit_passed: false", "audit_passed: true"), encoding="utf-8")
    publier(run, racine, conn, api_ok, publish_at="2026-12-01T16:00:00Z")
    statut = api_ok.corps("videos.insert")["status"]
    assert statut["publishAt"] == "2026-12-01T16:00:00Z"
    assert statut["privacyStatus"] == "private", \
        "publishAt n'a de sens que sur une vidéo privée"


def test_une_date_sans_fuseau_est_lue_en_utc():
    assert youtube._normaliser_date("2026-12-01T16:00:00") == "2026-12-01T16:00:00Z"
    assert youtube._normaliser_date("2026-12-01T17:00:00+01:00") == "2026-12-01T16:00:00Z"
    with pytest.raises(youtube.ErreurPublication, match="date illisible"):
        youtube._normaliser_date("demain")


# --------------------------------------------------------------------------------------
# 3. Ce que la publication laisse derrière elle
# --------------------------------------------------------------------------------------


def test_la_ligne_de_publications_porte_l_etat_reel(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    ligne = conn.execute("SELECT * FROM publications").fetchone()
    assert ligne["video_id"] == "bms-test-20260922-aaaa"
    assert ligne["youtube_video_id"] == "VID12345678"
    assert ligne["status"] == "published_private"
    assert ligne["thumbnail_set"] == 1
    assert ligne["captions_set"] == 1
    assert ligne["units_used"] == 451  # 50 + 400 + 1, la playlist n'est pas configurée


def test_publish_json_respecte_le_contrat_et_ne_porte_aucun_jeton(run, racine, conn, api_ok):
    from factory.core.models import PublishRecord

    publier(run, racine, conn, api_ok)
    charge = json.loads(run.publish.read_text(encoding="utf-8"))
    PublishRecord.model_validate({c: v for c, v in charge.items()
                                  if c in PublishRecord.model_fields})
    assert charge["publish_state"] == "uploaded_private"
    assert charge["publish_path"] == "manual_studio"
    assert charge["published_at"] is None, "personne ne peut l'écrire en manual_studio"
    texte = run.publish.read_text(encoding="utf-8").lower()
    for interdit in ("refresh_token", "client_secret", "access_token", "bearer"):
        assert interdit not in texte


def test_le_manifeste_recoit_l_identifiant_sans_passer_en_publie(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    manifeste = json.loads(run.manifest.read_text(encoding="utf-8"))
    assert manifeste["resultats"]["youtube_video_id"] == "VID12345678"
    assert manifeste["resultats"]["published_at"] is None


def test_l_identifiant_est_ecrit_avant_les_appels_qui_peuvent_echouer(run, racine, conn,
                                                                     monkeypatch):
    """Une vidéo en ligne que la base ignore serait une vidéo orpheline."""
    # Le backoff est réel (2, 4, 8, 16 s) : on l'exerce sans le subir.
    monkeypatch.setattr(youtube.time, "sleep", lambda _s: None)
    api = YouTubeFactice({
        "videos.insert": {"id": "VID12345678"},
        "thumbnails.set": erreur_http(500, "backendError"),
        "captions.insert": erreur_http(500, "backendError"),
        "videos.list": VIDEO_EN_LIGNE,
    })
    publier(run, racine, conn, api)
    ligne = conn.execute("SELECT youtube_video_id FROM publications").fetchone()
    assert ligne["youtube_video_id"] == "VID12345678"


def test_un_insert_refuse_laisse_une_ligne_failed(run, racine, conn):
    api = YouTubeFactice({"videos.insert": erreur_http(400, "uploadLimitExceeded",
                                                       "trop de vidéos aujourd'hui")})
    with pytest.raises(youtube.ErreurPublication, match="uploadLimitExceeded"):
        publier(run, racine, conn, api)
    ligne = conn.execute("SELECT status, last_error FROM publications").fetchone()
    assert ligne["status"] == "failed"
    assert "uploadLimitExceeded" in ligne["last_error"]


# --------------------------------------------------------------------------------------
# 4. `release` — la mécanique qui peut effacer le label
# --------------------------------------------------------------------------------------


def test_release_renvoie_le_status_complet_et_conserve_le_label(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    fichier = racine / "config" / "channels" / "bms-test.yaml"
    fichier.write_text(fichier.read_text(encoding="utf-8")
                       .replace("audit_passed: false", "audit_passed: true"), encoding="utf-8")
    programme = dict(VIDEO_EN_LIGNE)
    api = YouTubeFactice({
        "videos.list": lambda _k: {"items": [{
            **VIDEO_EN_LIGNE["items"][0],
            "status": {**VIDEO_EN_LIGNE["items"][0]["status"],
                       "publishAt": "2026-12-01T16:00:00Z"},
        }]},
        "videos.update": {"id": "VID12345678"},
    })
    apres = youtube.programmer("VID12345678", quand="2026-12-01T16:00:00Z", racine=racine,
                               conn=conn, service=api)
    statut = api.corps("videos.update")["status"]
    assert statut["publishAt"] == "2026-12-01T16:00:00Z"
    assert statut["privacyStatus"] == "private"
    assert statut["containsSyntheticMedia"] is True, \
        "un status partiel retirerait le label de contenu synthétique"
    assert "selfDeclaredMadeForKids" in statut
    assert apres["publishAt"] == "2026-12-01T16:00:00Z"
    assert conn.execute("SELECT status FROM publications").fetchone()["status"] == "scheduled"
    assert programme is not None


def test_release_refuse_une_video_non_privee(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    fichier = racine / "config" / "channels" / "bms-test.yaml"
    fichier.write_text(fichier.read_text(encoding="utf-8")
                       .replace("audit_passed: false", "audit_passed: true"), encoding="utf-8")
    api = YouTubeFactice({"videos.list": {"items": [{
        **VIDEO_EN_LIGNE["items"][0],
        "status": {**VIDEO_EN_LIGNE["items"][0]["status"], "privacyStatus": "public"},
    }]}})
    with pytest.raises(youtube.ErreurPublication, match="only if the privacy status"):
        youtube.programmer("VID12345678", quand="2026-12-01T16:00:00Z", racine=racine,
                           conn=conn, service=api)
    assert "videos.update" not in api.noms()


def test_release_refuse_avant_l_audit(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    api = YouTubeFactice({"videos.list": VIDEO_EN_LIGNE})
    with pytest.raises(youtube.ErreurPublication, match="audit_passed est faux"):
        youtube.programmer("VID12345678", quand="2026-12-01T16:00:00Z", racine=racine,
                           conn=conn, service=api)
    assert api.noms() == []


def test_release_refuse_une_date_passee(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    fichier = racine / "config" / "channels" / "bms-test.yaml"
    fichier.write_text(fichier.read_text(encoding="utf-8")
                       .replace("audit_passed: false", "audit_passed: true"), encoding="utf-8")
    with pytest.raises(youtube.ErreurPublication, match="dans le passé"):
        youtube.programmer("VID12345678", quand="2020-01-01T00:00:00Z", racine=racine,
                           conn=conn, service=YouTubeFactice({"videos.list": VIDEO_EN_LIGNE}))


def test_annuler_retire_publish_at_et_repasse_en_prive(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    api = YouTubeFactice({"videos.list": VIDEO_EN_LIGNE, "videos.update": {"id": "VID12345678"}})
    youtube.programmer("VID12345678", annuler=True, racine=racine, conn=conn, service=api)
    statut = api.corps("videos.update")["status"]
    assert "publishAt" not in statut
    assert statut["privacyStatus"] == "private"
    assert conn.execute("SELECT status FROM publications").fetchone()["status"] \
        == "published_private"


# --------------------------------------------------------------------------------------
# 5. Jobs de rapports et liste manuelle
# --------------------------------------------------------------------------------------


TYPES_GOOGLE = {"reportTypes": [
    {"id": "channel_reach_basic_a1", "name": "Reach"},
    {"id": "channel_basic_a3", "name": "Basic"},
    {"id": "channel_traffic_source_a3", "name": "Traffic"},
    {"id": "channel_demographics_a1", "name": "Demographics"},
    {"id": "channel_playback_location_a3", "name": "Playback"},
    {"id": "channel_basic_a2", "name": "Ancien", "deprecateTime": "2024-01-01T00:00:00Z"},
]}


def api_rapports(existants: list[dict] | None = None) -> YouTubeFactice:
    compteur = {"n": 0}

    def creer(kwargs):
        compteur["n"] += 1
        return {"id": f"job{compteur['n']}", "reportTypeId": kwargs["body"]["reportTypeId"],
                "name": kwargs["body"]["name"], "createTime": "2026-09-22T12:00:00Z"}

    return YouTubeFactice({
        "reportTypes.list": TYPES_GOOGLE,
        "jobs.list": {"jobs": existants or []},
        "jobs.create": creer,
    })


def test_les_cinq_jobs_sont_crees_avec_les_bons_identifiants(racine, conn):
    api = api_rapports()
    jobs, alertes = rj.creer("bms-test", racine=racine, conn=conn, api=api)
    assert alertes == []
    types = sorted(j.report_type for j in jobs)
    assert types == ["channel_basic_a3", "channel_demographics_a1",
                     "channel_playback_location_a3", "channel_reach_basic_a1",
                     "channel_traffic_source_a3"]
    assert "channel_reach_basic_a1" in types, "sans lui, pas d'impressions ni de CTR"
    lignes = conn.execute("SELECT * FROM reporting_jobs ORDER BY report_type").fetchall()
    assert len(lignes) == 5
    assert all(l["state"] == "active" for l in lignes)
    assert lignes[0]["first_report_expected_at"] == "2026-09-24T12:00:00Z"


def test_la_creation_est_idempotente(racine, conn):
    api = api_rapports()
    rj.creer("bms-test", racine=racine, conn=conn, api=api)
    deja = [{"id": f"job{i}", "reportTypeId": t, "name": "bms",
             "createTime": "2026-09-22T12:00:00Z"}
            for i, t in enumerate(("channel_reach_basic_a1", "channel_basic_a3",
                                   "channel_traffic_source_a3", "channel_demographics_a1",
                                   "channel_playback_location_a3"), start=1)]
    api2 = api_rapports(deja)
    jobs, _ = rj.creer("bms-test", racine=racine, conn=conn, api=api2)
    assert len(jobs) == 5
    assert "jobs.create" not in api2.noms(), "aucun doublon ne doit être créé"
    assert conn.execute("SELECT count(*) AS n FROM reporting_jobs").fetchone()["n"] == 5


def test_un_type_inconnu_de_google_n_est_pas_cree_mais_est_dit(racine, conn):
    api = api_rapports()
    jobs, alertes = rj.creer("bms-test", racine=racine, conn=conn, api=api,
                             types=["channel_reach_basic_a1", "channel_basic_a2"])
    assert [j.report_type for j in jobs] == ["channel_reach_basic_a1"]
    assert any("channel_basic_a2" in a and "absent de reportTypes.list" in a for a in alertes)


def test_un_type_deprecie_n_est_jamais_propose(racine, conn):
    api = api_rapports()
    connus = rj.types_disponibles(api)
    assert "channel_basic_a2" not in connus
    assert "channel_basic_a3" in connus


def test_publier_sans_job_de_reach_est_refuse(racine, conn):
    motif = youtube.premiere_publication_sans_job(conn, "bms-test")
    assert motif is not None and "ne sont pas rétroactifs" in motif
    rj.creer("bms-test", racine=racine, conn=conn, api=api_rapports())
    assert youtube.premiere_publication_sans_job(conn, "bms-test") is None


def test_publier_run_refuse_tant_que_les_jobs_manquent(racine, conn, monkeypatch):
    # Depuis l'étape 23.2, precheck passe d'abord et bloquerait ce run factice ; on l'isole
    # pour vérifier le second portillon (jobs de rapports).
    monkeypatch.setattr(youtube, "precheck", lambda *a, **k: [])
    with pytest.raises(youtube.ErreurPublication, match="rétroactifs"):
        youtube.publier_run("bms-test-20260922-aaaa", "bms-test", racine=racine, conn=conn)


def test_manual_list_donne_titre_heure_locale_et_lien_studio(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok, publish_at="2026-12-01T16:00:00Z")
    lignes = youtube.liste_manuelle(conn, racine)
    assert len(lignes) == 1
    ligne = lignes[0]
    assert ligne.titre == "Mysteries of the Universe"
    assert ligne.youtube_video_id == "VID12345678"
    assert ligne.studio_url == "https://studio.youtube.com/video/VID12345678/edit"
    assert "2026" in ligne.heure_locale and ligne.heure_locale != "2026-12-01T16:00:00Z", \
        "l'heure est donnée dans le fuseau de la chaîne, pas en UTC"


def test_une_chaine_auditee_sort_de_la_liste_manuelle(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    fichier = racine / "config" / "channels" / "bms-test.yaml"
    fichier.write_text(fichier.read_text(encoding="utf-8")
                       .replace("audit_passed: false", "audit_passed: true"), encoding="utf-8")
    assert youtube.liste_manuelle(conn, racine) == []


def test_status_rend_le_quota_et_les_listes(run, racine, conn, api_ok):
    publier(run, racine, conn, api_ok)
    rj.creer("bms-test", racine=racine, conn=conn, api=api_rapports())
    etat = youtube.etat_du_jour(conn, racine)
    assert etat.quota.uploads_utilises == 1
    assert etat.quota.unites_utilisees == 451
    assert len(etat.a_publier) == 1
    assert len(etat.jobs_rapports) == 5
    assert etat.erreurs == []


# --------------------------------------------------------------------------------------
# 6. Points d'accroche de l'étape 23.2 — présents, inertes tant qu'elle n'existe pas
# --------------------------------------------------------------------------------------


def test_le_precheck_de_l_etape_23_2_est_branche_et_bloque_un_run_incomplet(racine):
    bloquants = youtube.precheck("bms-test-20260922-aaaa", "bms-test", racine)
    assert any("relecture" in b for b in bloquants)


def test_le_calendrier_de_l_etape_23_2_est_appele_et_ne_rend_rien_aujourd_hui(racine, conn):
    assert youtube.date_prevue(conn, "bms-test-20260922-aaaa", "bms-test", racine) is None


def test_le_pense_bete_de_publication_nomme_les_gestes_manuels(run, racine, conn, api_ok):
    """CONFORMITE § 2 : sans ce fichier, l'opérateur oublie la case « promotion payante »."""
    publier(run, racine, conn, api_ok, publish_at="2026-12-01T16:00:00Z")
    texte = run.publication_md.read_text(encoding="utf-8")
    assert "https://studio.youtube.com/video/VID12345678/edit" in texte
    assert "Programmée" in texte and "2026-12-01T16:00:00Z" in texte


def test_release_renvoie_licence_et_integration_sans_les_reinitialiser(run, racine, conn,
                                                                      api_ok):
    """`videos.update` écrase la partie entière : un champ omis est un champ remis à zéro."""
    publier(run, racine, conn, api_ok)
    fichier = racine / "config" / "channels" / "bms-test.yaml"
    fichier.write_text(fichier.read_text(encoding="utf-8")
                       .replace("audit_passed: false", "audit_passed: true"), encoding="utf-8")
    api = YouTubeFactice({
        "videos.list": {"items": [{
            **VIDEO_EN_LIGNE["items"][0],
            "status": {**VIDEO_EN_LIGNE["items"][0]["status"],
                       "license": "creativeCommon", "embeddable": False,
                       "publicStatsViewable": False},
        }]},
        "videos.update": {"id": "VID12345678"},
    })
    youtube.programmer("VID12345678", quand="2026-12-01T16:00:00Z", racine=racine,
                       conn=conn, service=api)
    statut = api.corps("videos.update")["status"]
    assert statut["license"] == "creativeCommon"
    assert statut["embeddable"] is False
    assert statut["publicStatsViewable"] is False
