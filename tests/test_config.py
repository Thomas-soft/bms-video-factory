"""Chargement de la configuration d'exemple, validations croisées et identifiants de run."""

from __future__ import annotations

from datetime import date

import pytest
from typer.testing import CliRunner

from factory.cli import app
from factory.core import config as cfgmod
from factory.core.models import ALPHABET_ID, Channel, VideoSpec
from factory.core.paths import racine_projet

FIXTURE_INVALIDE = racine_projet() / "tests" / "fixtures" / "channel_invalide.yaml"
runner = CliRunner()


@pytest.fixture(scope="module")
def cfg() -> cfgmod.ConfigSet:
    """Configuration d'exemple du dépôt, chargée une fois."""
    return cfgmod.charger(strict=False)


def test_exemples_du_depot_valident(cfg: cfgmod.ConfigSet) -> None:
    """`config/` valide sans erreur ; les alertes restent des alertes."""
    assert cfg.erreurs == [], "\n".join(str(p) for p in cfg.erreurs)
    assert len(cfg.channels) >= 4
    assert set(cfg.languages) >= {"fr", "en", "es", "it"}
    assert len(cfg.niches) == 8
    assert set(cfg.styles) == {"cartes", "illustre", "documentaire", "motion",
                               "whiteboard", "avatar2d"}
    assert cfg.team is not None and {r.id for r in cfg.team.relecteurs} == {
        "thomas", "alek", "sofiane"
    }


def test_get_channel_et_list_channels(cfg: cfgmod.ConfigSet) -> None:
    """Accès nommé à une chaîne, et liste triée."""
    channel = cfg.get_channel("bms-science-en")
    assert channel.lang == "en" and channel.niche == "science_pop"
    assert [c.id for c in cfg.list_channels()] == sorted(cfg.channels)
    with pytest.raises(KeyError, match="chaîne inconnue"):
        cfg.get_channel("bms-inexistante")


def test_chaque_style_declare_un_moteur_connu(cfg: cfgmod.ConfigSet) -> None:
    """Un moteur « planifié » est accepté par le validateur, et signalé — un moteur livré, non.

    Depuis l'étape 12.1, `cartes` est en `retenu_v1` : l'avertissement doit disparaître pour lui
    seul, sinon « planifié » ne voudrait plus rien dire.
    """
    assert {s.engine for s in cfg.styles.values()} <= set(cfgmod.MOTEURS_CONNUS)
    planifies = [s for s in cfg.styles.values() if s.statut == "planifie"]
    alertes = [p for p in cfg.avertissements if "planifie" in p.message]
    assert len(alertes) == len(planifies) < len(cfg.styles)
    assert cfg.styles["cartes"].executable
    assert not any("cartes" in p.message for p in alertes)


def test_voix_doit_appartenir_a_la_langue_de_la_chaine(cfg: cfgmod.ConfigSet) -> None:
    """Validation croisée n° 1 : la voix appartient à la langue de la chaîne."""
    channel = cfg.get_channel("bms-science-en").model_copy(update={"voice_id": "serena_fr"})
    casse = cfgmod.ConfigSet(racine=cfg.racine, languages=cfg.languages, niches=cfg.niches,
                             styles=cfg.styles, channels={channel.id: channel},
                             products=cfg.products, team=cfg.team)
    messages = [p.message for p in cfgmod.croiser(casse)]
    assert any("absente de la langue en" in msg for msg in messages)


def test_style_et_niche_references_doivent_exister(cfg: cfgmod.ConfigSet) -> None:
    """Validation croisée n° 2 : le style et la niche référencés existent."""
    channel = cfg.get_channel("bms-science-en").model_copy(
        update={"style": "hologramme", "niche": "inconnue"}
    )
    casse = cfgmod.ConfigSet(racine=cfg.racine, languages=cfg.languages, niches=cfg.niches,
                             styles=cfg.styles, channels={channel.id: channel},
                             products=cfg.products, team=cfg.team)
    messages = [p.message for p in cfgmod.croiser(casse)]
    assert "style inconnu : hologramme" in messages
    assert "niche inconnue : inconnue" in messages


def test_produit_exige_une_divulgation_dans_la_langue(cfg: cfgmod.ConfigSet) -> None:
    """Validation croisée n° 3 : un produit configuré impose la divulgation dans la langue."""
    channel = cfg.get_channel("bms-science-en").model_copy(update={"products": ["exemple-affilie"]})
    assert channel.paid_promotion is True
    langue_sans_impact = cfg.languages["en"].model_copy(
        update={"disclosure": cfg.languages["en"].disclosure.model_copy(
            update={"impact": [""]})}
    )
    casse = cfgmod.ConfigSet(racine=cfg.racine, languages={"en": langue_sans_impact},
                             niches=cfg.niches, styles=cfg.styles,
                             channels={channel.id: channel}, products=cfg.products,
                             team=cfg.team)
    messages = [p.message for p in cfgmod.croiser(casse)]
    assert any("aucune ligne de divulgation" in msg for msg in messages)


def test_produit_inconnu_refuse(cfg: cfgmod.ConfigSet) -> None:
    """Une chaîne ne référence pas un produit qui n'existe pas."""
    channel = cfg.get_channel("bms-science-en").model_copy(update={"products": ["fantome"]})
    casse = cfgmod.ConfigSet(racine=cfg.racine, languages=cfg.languages, niches=cfg.niches,
                             styles=cfg.styles, channels={channel.id: channel},
                             products=cfg.products, team=cfg.team)
    assert "produit inconnu : fantome" in [p.message for p in cfgmod.croiser(casse)]


def test_incrustation_et_piste_de_sous_titres_sont_exclusives(cfg: cfgmod.ConfigSet) -> None:
    """Incruster et envoyer la piste = double affichage et 400 unités de quota perdues."""
    brut = cfg.get_channel("bms-science-en").model_dump()
    brut["charte"]["subtitles"]["burn_in"] = True
    with pytest.raises(Exception, match="exclusifs"):
        Channel.model_validate(brut)


def test_fichier_volontairement_casse_est_refuse() -> None:
    """Le YAML de non-régression est rejeté, avec un message par défaut."""
    problemes = cfgmod.valider_fichier(FIXTURE_INVALIDE)
    messages = [p.message for p in problemes]
    assert len(problemes) >= 5
    assert any("Extra inputs are not permitted" in msg for msg in messages)
    assert any("less than or equal to 2" in msg for msg in messages)


def test_genre_du_fichier_deduit_hors_de_son_dossier() -> None:
    """Le validateur reconnaît une chaîne même hors de `config/channels/`."""
    assert cfgmod._deduire_genre(FIXTURE_INVALIDE) == "channels"


def test_video_id_deterministe_et_bien_forme(cfg: cfgmod.ConfigSet) -> None:
    """L'identifiant est dérivé de la graine : même graine, même identifiant."""
    jour = date(2026, 9, 18)
    premier = cfgmod.generer_video_id("bms-science-en", 8123457690123456789, jour)
    assert premier == cfgmod.generer_video_id("bms-science-en", 8123457690123456789, jour)
    assert premier != cfgmod.generer_video_id("bms-science-en", 1, jour)
    assert premier.startswith("bms-science-en-20260918-")
    suffixe = premier.rsplit("-", 1)[1]
    assert len(suffixe) == 4 and set(suffixe) <= set(ALPHABET_ID)
    assert not set(suffixe) & set("ilo01")
    VideoSpec.model_validate({
        "video_id": premier, "channel_id": "bms-science-en", "lang": "en",
        "niche": "science_pop", "style": "illustre",
        "topic": {"sujet": "s", "angle": "a", "source": "manuel", "evidence": {}},
        "target_duration_s": 648, "cut_rhythm_target_s": 5.85, "seed": 1,
        "created_at": "2026-09-18T21:14:07Z",
    })


def test_video_id_libre_et_attribution(tmp_path) -> None:
    """Un identifiant déjà pris sur disque n'est pas réattribué."""
    from factory.core.paths import RunPaths

    premier = cfgmod.attribuer_video_id("bms-science-en", 7, date(2026, 9, 18), racine=tmp_path)
    RunPaths.depuis_video_id(premier, racine=tmp_path).creer()
    assert not cfgmod.video_id_libre(premier, racine=tmp_path)
    second = cfgmod.attribuer_video_id("bms-science-en", 7, date(2026, 9, 18), racine=tmp_path)
    assert second != premier


def test_spec_verifiee_contre_la_configuration(cfg: cfgmod.ConfigSet) -> None:
    """La langue du run est celle de la chaîne, pas une autre."""
    spec = VideoSpec.model_validate({
        "video_id": "bms-science-en-20260918-k7q2", "channel_id": "bms-science-en",
        "lang": "fr", "niche": "science_pop", "style": "illustre",
        "topic": {"sujet": "s", "angle": "a", "source": "manuel", "evidence": {}},
        "target_duration_s": 648, "cut_rhythm_target_s": 5.85, "seed": 1,
        "created_at": "2026-09-18T21:14:07Z",
    })
    messages = [p.message for p in cfgmod.verifier_spec(spec, cfg)]
    assert any("lang fr ≠" in msg for msg in messages)


def test_rythme_de_coupe_retombe_sur_la_valeur_de_secours(cfg: cfgmod.ConfigSet) -> None:
    """Une niche non mesurée fournit une valeur de secours, jamais une cible inventée."""
    mesuree = cfg.niches["science_pop"].rythme_coupe_s
    assert mesuree.cible_effective() == 5.85
    non_mesuree = cfg.niches["niche_monetisable_longevite"].rythme_coupe_s
    assert non_mesuree.a_mesurer and non_mesuree.cible is None
    assert non_mesuree.cible_effective() == non_mesuree.fallback_provisoire_s


def test_cli_config_validate_retourne_zero() -> None:
    """`factory config validate` : 0 sur les exemples."""
    resultat = runner.invoke(app, ["config", "validate"])
    assert resultat.exit_code == 0, resultat.output


def test_cli_config_validate_retourne_un_sur_fichier_invalide() -> None:
    """`factory config validate --file <cassé>` : 1 et des messages lisibles."""
    resultat = runner.invoke(app, ["config", "validate", "--file", str(FIXTURE_INVALIDE)])
    assert resultat.exit_code == 1
    assert "ERREUR" in resultat.output


def test_cli_config_show() -> None:
    """`factory config show` affiche la configuration résolue, et 1 sur une chaîne inconnue."""
    resultat = runner.invoke(app, ["config", "show", "bms-science-en"])
    assert resultat.exit_code == 0
    assert "science_pop" in resultat.output
    assert runner.invoke(app, ["config", "show", "bms-inconnue"]).exit_code == 1
