"""Étape 14 — OAuth en production, upload privé, dossier d'audit.

Quatre familles d'invariants, choisies sur ce qui peut réellement coûter cher ici.

- **Un secret ne sort jamais.** `etat_jeton` décrit un jeton sans en révéler la valeur, et
  `publish.json` ne porte aucun champ d'autorisation : un jeton recopié dans un fichier de
  sortie finirait dans le dépôt au premier `git add`.
- **La vidéo sort privée, et le corps de la requête le dit.** Tant que l'audit n'est pas
  obtenu, YouTube force le privé ; l'écrire explicitement évite de croire à une programmation
  qui n'existe pas.
- **Les refus bloquants coûtent 0 unité.** Un run sans `final.mp4`, sans drapeau synthétique
  ou dans la mauvaise langue doit échouer **avant** le premier appel d'API : un
  `videos.insert` raté coûte 1 600 unités quand même.
- **Le manifeste ne ment pas sur l'état de publication.** Une vidéo privée non relue n'est pas
  publiable : `publish_state` ne bouge pas à l'upload (CONFORMITE § 10.1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory.core import config as config_module
from factory.core import secrets as secrets_module
from factory.core.paths import RunPaths
from factory.publish import oauth
from factory.publish import upload_min as U


# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------


@pytest.fixture
def channel_test():
    """La chaîne `bms-test` telle que `config/channels/bms-test.yaml` la décrit."""
    cfg = config_module.charger()
    return cfg.channels["bms-test"]


@pytest.fixture
def meta_en():
    """Un `metadata.json` anglais minimal mais complet."""
    return {
        "title_chosen": "Mysteries of the Universe",
        "description": "Ligne de divulgation.\n\nCorps.",
        "tags": ["space", "universe"],
        "category_id": "28",
        "default_language": "en",
        "default_audio_language": "en",
        "contains_synthetic_media": False,
        "made_for_kids": False,
        "paid_promotion": False,
        "caption_file": "subtitles.srt",
        "thumbnail_file": "thumbnail.png",
    }


@pytest.fixture
def run_pret(tmp_path, meta_en):
    """Un run exporté : `final.mp4`, `metadata.json`, `manifest.json`."""
    chemins = RunPaths.depuis_video_id("bms-science-en-test", tmp_path)
    chemins.racine.mkdir(parents=True)
    chemins.final.write_bytes(b"\x00" * 1024)
    chemins.metadata.write_text(json.dumps(meta_en), encoding="utf-8")
    chemins.manifest.write_text(json.dumps({"resultats": {}}), encoding="utf-8")
    return chemins


# --------------------------------------------------------------------------------------
# 1. Aucun secret ne fuit
# --------------------------------------------------------------------------------------


def test_etat_jeton_absent_ne_revele_rien(tmp_path):
    assert oauth.etat_jeton("bms-test", tmp_path) == {"present": False}


def test_etat_jeton_present_ne_rend_jamais_la_valeur(tmp_path):
    chemin = tmp_path / "secrets" / "tokens" / "bms-test.json"
    chemin.parent.mkdir(parents=True)
    chemin.write_text(
        json.dumps({"token": "valeur-secrete", "refresh_token": "autre-secret",
                    "scopes": list(oauth.SCOPES), "expiry": "2026-09-18T00:00:00Z"}),
        encoding="utf-8",
    )
    chemin.chmod(0o600)
    etat = oauth.etat_jeton("bms-test", tmp_path)
    rendu = json.dumps(etat)
    assert "valeur-secrete" not in rendu and "autre-secret" not in rendu
    assert etat["refresh_token"] == "présent"
    assert etat["mode_600"] is True


def test_chemin_jeton_reste_dans_secrets(tmp_path):
    assert oauth.chemin_jeton("bms-test", tmp_path).parent.name == "tokens"
    with pytest.raises(secrets_module.ErreurSecret):
        secrets_module.chemin_reference("../ailleurs.json", tmp_path)


def test_publish_json_ne_porte_aucun_champ_d_autorisation(run_pret):
    resultat = U.Resultat(video_id="v", channel="bms-test", youtube_video_id="abc123",
                          url="https://www.youtube.com/watch?v=abc123")
    resultat.etapes.append(U.Etape("videos.insert", True, "abc123", 1600))
    U._ecrire_publish(run_pret, resultat)
    charge = json.loads(run_pret.publish.read_text(encoding="utf-8"))
    interdits = ("token", "refresh", "client_secret", "access_token", "credentials")
    assert not [c for c in json.dumps(charge).lower().split('"') if c in interdits]
    assert charge["quota_units"] == 1600


# --------------------------------------------------------------------------------------
# 2. La vidéo sort privée, avec toutes ses métadonnées
# --------------------------------------------------------------------------------------


def test_corps_insert_force_le_prive(meta_en, channel_test):
    corps = U._corps_insert(meta_en, channel_test)
    assert corps["status"]["privacyStatus"] == "private"
    assert corps["status"]["selfDeclaredMadeForKids"] is False


def test_corps_insert_porte_toutes_les_metadonnees(meta_en, channel_test):
    corps = U._corps_insert(meta_en, channel_test)
    snippet = corps["snippet"]
    assert snippet["title"] == meta_en["title_chosen"]
    assert snippet["description"] == meta_en["description"]
    assert snippet["tags"] == meta_en["tags"]
    assert snippet["categoryId"] == "28"
    assert snippet["defaultLanguage"] == "en"
    assert snippet["defaultAudioLanguage"] == "en"


def test_contains_synthetic_media_est_recopie_du_manifeste(meta_en, channel_test):
    """Le drapeau est posé à la génération (CONFORMITE § 3), jamais recalculé ici."""
    for valeur in (True, False):
        meta_en["contains_synthetic_media"] = valeur
        corps = U._corps_insert(meta_en, channel_test)
        assert corps["status"]["containsSyntheticMedia"] is valeur


def test_categorie_de_la_chaine_si_le_run_n_en_porte_pas(meta_en, channel_test):
    meta_en["category_id"] = None
    assert U._corps_insert(meta_en, channel_test)["snippet"]["categoryId"] == "28"


# --------------------------------------------------------------------------------------
# 3. Les refus bloquants arrivent avant la première unité de quota
# --------------------------------------------------------------------------------------


def test_refus_si_final_mp4_absent(tmp_path, meta_en, channel_test):
    chemins = RunPaths.depuis_video_id("run-sans-video", tmp_path)
    chemins.racine.mkdir(parents=True)
    with pytest.raises(U.ErreurUpload, match="final.mp4 absent"):
        U._controles_prealables(chemins, meta_en, channel_test)


def test_refus_si_la_langue_du_run_n_est_pas_celle_de_la_chaine(run_pret, meta_en, channel_test):
    meta_en["default_language"] = "fr"
    with pytest.raises(U.ErreurUpload, match="langue incohérente"):
        U._controles_prealables(run_pret, meta_en, channel_test)


def test_refus_si_le_drapeau_synthetique_manque(run_pret, meta_en, channel_test):
    del meta_en["contains_synthetic_media"]
    with pytest.raises(U.ErreurUpload, match="contains_synthetic_media absent"):
        U._controles_prealables(run_pret, meta_en, channel_test)


def test_promotion_payante_leve_une_alerte_car_l_api_n_a_pas_de_champ(run_pret, meta_en,
                                                                      channel_test):
    meta_en["paid_promotion"] = True
    alertes = U._controles_prealables(run_pret, meta_en, channel_test)
    assert any("Studio" in a for a in alertes)


def test_compte_non_verifie_annonce_le_refus_de_la_miniature(run_pret, meta_en, channel_test):
    assert channel_test.google_account.phone_verified is False
    alertes = U._controles_prealables(run_pret, meta_en, channel_test)
    assert any("vérifié par téléphone" in a for a in alertes)


def test_dry_run_ne_touche_aucune_api(run_pret, monkeypatch):
    """Le contrôle préalable doit tourner sans jeton : aucun appel réseau, aucun quota."""
    def interdit(*_a, **_k):
        raise AssertionError("aucun appel d'API ne doit partir en dry-run")
    cfg_reel = config_module.charger()
    monkeypatch.setattr(oauth, "service", interdit)
    monkeypatch.setattr(U.config_module, "charger", lambda _racine=None: cfg_reel)
    resultat = U.televerser("bms-science-en-test", "bms-test",
                            racine=run_pret.racine.parents[2], dry_run=True)
    assert resultat.quota_units == 0
    assert resultat.youtube_video_id is None


# --------------------------------------------------------------------------------------
# 4. Le manifeste ne ment pas sur l'état de publication
# --------------------------------------------------------------------------------------


def test_le_manifeste_recoit_l_identifiant_sans_passer_en_publie(run_pret):
    resultat = U.Resultat(video_id="v", channel="bms-test", youtube_video_id="abc123")
    U._completer_manifeste(run_pret, resultat)
    manifeste = json.loads(run_pret.manifest.read_text(encoding="utf-8"))
    assert manifeste["resultats"]["youtube_video_id"] == "abc123"
    assert manifeste["resultats"]["published_at"] is None
    assert "publish_state" not in manifeste.get("conformite", {})


def test_le_cout_en_quota_est_celui_documente_par_google():
    assert U.COUT_QUOTA["videos.insert"] == 1600
    assert U.COUT_QUOTA["captions.insert"] == 400
    assert U.COUT_QUOTA["thumbnails.set"] == 50
    # Six uploads complets saturent le quota de 10 000 unités : c'est le plafond de CONFORMITE § 2.
    par_video = U.COUT_QUOTA["videos.insert"] + U.COUT_QUOTA["captions.insert"] \
        + U.COUT_QUOTA["thumbnails.set"] + U.COUT_QUOTA["videos.list"]
    assert 6 * par_video > 10_000


# --------------------------------------------------------------------------------------
# 5. La chaîne de test et les scopes
# --------------------------------------------------------------------------------------


def test_la_chaine_de_test_publie_en_anglais(channel_test):
    """Arbitrage d'Alek du 15/09/2026 : anglais uniquement. Jamais un run FR sur bms-test."""
    assert channel_test.lang == "en"
    assert channel_test.youtube.audit_passed is False
    assert channel_test.publish_path == "manual_studio"


def test_les_quatre_scopes_sont_ceux_du_dossier_d_audit():
    assert oauth.SCOPES == (
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
    )
    audit = Path("docs/AUDIT-API.md").read_text(encoding="utf-8")
    for scope in oauth.SCOPES:
        assert scope.rsplit("/", 1)[-1] in audit


# --------------------------------------------------------------------------------------
# 6. La reprise des appels qui suivent l'insert
# --------------------------------------------------------------------------------------


class _FausseReponse(dict):
    """Ce que `httplib2` rend : un dict qui porte aussi `status` et `reason`."""

    def __init__(self, status):
        super().__init__(status=status, reason="test")
        self.status = status
        self.reason = "test"


def _http_error(status):
    from googleapiclient.errors import HttpError
    return HttpError(_FausseReponse(status), b'{"error":{"message":"not found"}}')


def test_reessai_sur_404_puis_succes(monkeypatch):
    """Juste après l'insert, thumbnails.set répond 404 quelques secondes : il faut attendre."""
    monkeypatch.setattr(U.time, "sleep", lambda _s: None)
    essais = {"n": 0}

    def appel():
        essais["n"] += 1
        if essais["n"] < 3:
            raise _http_error(404)
        return "ok"

    assert U._reessayer(appel) == "ok"
    assert essais["n"] == 3


def test_pas_de_reessai_sur_un_refus_definitif(monkeypatch):
    """403 = compte non vérifié : réessayer ne fait que dépenser du quota."""
    from googleapiclient.errors import HttpError

    monkeypatch.setattr(U.time, "sleep", lambda _s: None)
    essais = {"n": 0}

    def appel():
        essais["n"] += 1
        raise _http_error(403)

    with pytest.raises(HttpError):
        U._reessayer(appel)
    assert essais["n"] == 1
