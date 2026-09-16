"""Aller-retour JSON et validateurs croisés des modèles (étape 9)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from factory.core import models as m
from factory.core.config import charger

CFG = charger(strict=False)


def _spec() -> m.VideoSpec:
    return m.VideoSpec(
        video_id="bms-science-en-20260918-k7q2",
        channel_id="bms-science-en",
        lang="en",
        niche="science_pop",
        style="illustre",
        topic=m.Topic(
            sujet="Why your brain deletes memories while you sleep",
            angle="comparaison_chiffree",
            source="topics_queue",
            evidence=m.TopicEvidence(score=0.81, n=12),
        ),
        target_duration_s=648,
        cut_rhythm_target_s=5.85,
        seed=8123457690123456789,
        created_at="2026-09-18T21:14:07Z",
    )


def _script(**surcharges) -> m.Script:
    base = dict(
        lang="en",
        hook=m.Hook(type="question_contrarienne", text="What if forgetting is the point?"),
        segments=[
            m.ScriptSegment(
                id="seg_00", role="hook", narration="What if forgetting is the point?",
                visual_intent="Gros plan d'un réveil à 3 h du matin", open_loop="plant",
            ),
            m.ScriptSegment(
                id="seg_01", role="contexte", narration="Le cerveau trie pendant la nuit.",
                visual_intent="Schéma de deux synapses", open_loop="plant",
            ),
            m.ScriptSegment(
                id="seg_02", role="point", narration="Le sommeil lent élimine 18 % des synapses.",
                visual_intent="Une synapse s'efface", open_loop="payoff", sources=["f01"],
            ),
            m.ScriptSegment(
                id="seg_03", role="conclusion", narration="Oublier est le prix du souvenir.",
                visual_intent="Réveil qui s'éteint", open_loop="payoff",
            ),
        ],
        editorial_signature=m.SignatureEditoriale(
            angle="comparaison_chiffree",
            elements_proprietaires=["Trois études ramenées à une même échelle"],
        ),
        word_count=1458,
        estimated_duration_s=648.0,
    )
    base.update(surcharges)
    return m.Script(**base)


def _asset(**surcharges) -> m.Asset:
    base = dict(
        asset_id="9c1f4b77ad02e35a",
        path="assets/shot_00/image.png",
        provider="flux",
        source_url=None,
        author="BMS (généré)",
        licence="Apache-2.0",
        licence_url="https://www.apache.org/licenses/LICENSE-2.0",
        downloaded_at="2026-09-19T02:11:40Z",
        generator=m.Generateur(
            model="mlx-community/FLUX.2-Klein-4B-4bit", prompt_hash="77ce",
            seed=3901284771, steps=4, resolution="1280x720",
        ),
    )
    base.update(surcharges)
    return m.Asset(**base)


def _manifest(**conformite) -> m.RunManifest:
    return m.RunManifest(
        identite=m.ManifestIdentite(
            video_id="bms-science-en-20260918-k7q2", channel_id="bms-science-en", lang="en",
            niche="science_pop", style="illustre", template_id="sci-b",
            charte_version="2026.09.1",
        ),
        decisions=m.ManifestDecisions(topic=_spec().topic, hook_type="question_contrarienne"),
        conformite=m.ManifestConformite(**conformite),
    )


def exemples() -> dict[str, m.ModeleRacine]:
    """Une instance valide de chaque modèle racine."""
    return {
        "Language": CFG.languages["en"],
        "Niche": CFG.niches["science_pop"],
        "Style": CFG.styles["illustre"],
        "Product": CFG.products["exemple-affilie"],
        "Channel": CFG.channels["bms-science-en"],
        "TeamConfig": CFG.team,
        "QcConfig": CFG.qc,
        "EditorialConfig": CFG.editorial,
        "EconomicsConfig": CFG.economics,
        "VideoSpec": _spec(),
        "Script": _script(),
        "Words": m.Words(
            engine="parakeet", coverage=1.0, wer_vs_script=0.019, wer_threshold=0.08,
            segments=[m.MesureSegmentAsr(id="seg_00", coverage=1.0, wer_vs_script=0.021,
                                         wer_threshold=0.08, engine="parakeet")],
            words=[m.WordTiming(w="What", start_s=0.32, end_s=0.49, seg="seg_00",
                                asr_confidence=0.99)],
        ),
        "Shotlist": m.Shotlist(
            stats=m.StatsShotlist(median_shot_s=5.8, target_s=5.85, hook_shots_max_s=4.1),
            shots=[m.Shot(
                id="shot_00", segment_id="seg_00", start_s=0.0, end_s=3.9, duration_s=3.9,
                visual_intent="Gros plan d'un réveil", on_screen_text="FORGETTING IS THE POINT",
                asset_request=m.AssetRequest(type="image", prompt_or_keywords="alarm clock, 3am",
                                             reuse_ok=False, layer="background"),
                motion="zoom_in", seed=3901284771,
            )],
        ),
        "Asset": _asset(),
        "ReviewRecord": m.ReviewRecord(
            reviewer="Sofiane", review_date="2026-09-19T08:40:00Z", review_hash="6f" * 32,
            decision="approved_with_edits", comment="Hook raccourci de 4 mots.",
            batch_id="2026-W38-b1",
        ),
        "QCReport": m.QCReport(
            score=86.4, verdict="pass",
            checks=[
                m.QCCheck(id="loudness", measured=-14.1, target=-14.0, tolerance=0.5,
                          status="pass", source="ffmpeg ebur128"),
                m.QCCheck(id="silence", status="skipped",
                          source="cible a_mesurer dans REFERENTIEL.json"),
            ],
        ),
        "PublishRecord": m.PublishRecord(publish_path="manual_studio", publish_state="draft"),
        "RunManifest": _manifest(),
    }


@pytest.mark.parametrize("nom", sorted(exemples()))
def test_aller_retour_json(nom: str) -> None:
    """Chaque modèle racine se sérialise et se relit à l'identique."""
    objet = exemples()[nom]
    relu = type(objet).model_validate_json(objet.model_dump_json())
    assert relu == objet
    assert relu.schema_version == m.SCHEMA_VERSION


def test_tous_les_modeles_racine_sont_couverts() -> None:
    """Le registre MODELES_RACINE et les exemples du test disent la même chose."""
    assert {c.__name__ for c in m.MODELES_RACINE} == set(exemples())


def test_cle_inconnue_refusee() -> None:
    """Une clé mal orthographiée est une erreur, pas un silence."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        m.Language.model_validate({**CFG.languages["en"].model_dump(), "langue": "en"})


def test_majeure_de_schema_incompatible_refusee() -> None:
    """Une majeure différente est refusée ; une mineure inférieure est acceptée."""
    with pytest.raises(ValidationError, match="incompatible"):
        m.PublishRecord(schema_version="2.0", publish_path="manual_studio", publish_state="draft")
    ancien = m.PublishRecord(schema_version="1.0", publish_path="manual_studio",
                             publish_state="draft")
    assert not ancien.mineure_inferieure()


def test_cadence_plafonnee_a_deux_par_semaine() -> None:
    """CONFORMITE § 6 : 2 vidéos par chaîne et par semaine, plafond dur."""
    cadence = CFG.channels["bms-science-en"].cadence
    with pytest.raises(ValidationError, match="less than or equal to 2"):
        m.Cadence.model_validate({**cadence.model_dump(), "per_week_max": 3})


def test_produit_amazon_sans_attribution_par_video() -> None:
    """Amazon : 100 identifiants au maximum, donc aucune granularité par vidéo."""
    produit = CFG.products["exemple-affilie"].model_dump()
    produit.update(network="amazon", subid_param=None, subid_max_len=None,
                   attribution_par_video=True)
    with pytest.raises(ValidationError, match="attribution_par_video"):
        m.Product.model_validate(produit)
    produit["attribution_par_video"] = False
    assert m.Product.model_validate(produit).subid("c", "en", "v") is None


def test_produit_subid_impose_par_le_reseau() -> None:
    """Le nom du paramètre et sa longueur viennent du réseau, jamais du code."""
    produit = CFG.products["exemple-affilie"]
    assert produit.subid("bms-science-en", "en", "bms-science-en-20260918-k7q2").startswith(
        "bms-science-en_en_"
    )
    casse = {**produit.model_dump(), "subid_max_len": 50}
    with pytest.raises(ValidationError, match="subid_max_len 255"):
        m.Product.model_validate(casse)


def test_script_exige_deux_boucles_ouvertes_resolues() -> None:
    """Le référentiel impose ≥ 2 boucles ouvertes, chacune avec son payoff."""
    segments = [s.model_copy() for s in _script().segments]
    segments[1] = segments[1].model_copy(update={"open_loop": "none"})
    with pytest.raises(ValidationError, match="boucle"):
        _script(segments=segments)


def test_script_sponsor_sans_divulgation_orale_refuse() -> None:
    """Contrôle 6 de CONFORMITE § 11, bloquant : la divulgation orale est écrite au script."""
    segments = list(_script().segments)
    segments.insert(2, m.ScriptSegment(
        id="seg_09", role="sponsor", narration="Cette vidéo est sponsorisée.",
        visual_intent="Produit sur fond de charte",
    ))
    with pytest.raises(ValidationError, match="divulgation orale"):
        _script(segments=segments)
    segments[2] = segments[2].model_copy(update={"disclosure_spoken": True})
    with pytest.raises(ValidationError, match="disclosure_lines"):
        _script(segments=segments)
    lignes = m.LignesDivulgation(description_line="Paid promotion", overlay_text="Paid promotion",
                                 spoken_line="This video is sponsored.")
    assert _script(segments=segments, disclosure_lines=lignes).disclosure_lines is not None


def test_asset_licence_non_commerciale_refusee() -> None:
    """Toute licence non commerciale est éliminatoire (CONFORMITE § 8)."""
    with pytest.raises(ValidationError, match="non commerciale"):
        _asset(licence="CC-BY-NC-SA-4.0")
    assert m.licence_commerciale("CC-BY-4.0")
    assert not m.licence_commerciale("CC BY NC 4.0")


def test_asset_provenance_coherente() -> None:
    """Une image locale n'a pas de source_url ; une image de banque en a une."""
    with pytest.raises(ValidationError, match="source_url doit être null"):
        _asset(source_url="https://exemple.tld/i.png")
    with pytest.raises(ValidationError, match="source_url obligatoire"):
        _asset(provider="pexels", generator=None)


def test_controle_non_mesure_est_saute() -> None:
    """« Non mesuré » n'est pas une note : c'est un contrôle sauté."""
    with pytest.raises(ValidationError, match="status skipped"):
        m.QCCheck(id="silence", status="pass", source="ffmpeg silencedetect")


def test_manifeste_bloque_la_publication_si_un_champ_de_conformite_manque() -> None:
    """Un run dont un champ obligatoire est vide n'atteint pas `ready_to_publish`."""
    brouillon = _manifest()
    assert brouillon.conformite.publish_state == "draft"
    assert "reviewer" in brouillon.champs_conformite_manquants()
    with pytest.raises(ValidationError, match="champs obligatoires vides"):
        _manifest(publish_state="ready_to_publish")


def test_manifeste_promotion_payante_exige_ses_champs() -> None:
    """`paid_promotion` entraîne segments, liens, divulgation et case cochée en Studio."""
    manifeste = _manifest(paid_promotion=True)
    manquants = manifeste.champs_conformite_manquants()
    for champ in ("sponsor_segments", "affiliate_links", "paid_promotion_checked_in_studio",
                  "disclosure_lines"):
        assert champ in manquants


def test_divulgation_orale_dans_les_trente_secondes() -> None:
    """La divulgation orale tombe dans les 30 premières secondes du segment sponsorisé."""
    with pytest.raises(ValidationError, match="30 premières secondes"):
        m.SegmentSponsorise(start_s=100.0, end_s=145.0, type="affiliate",
                            product_id="exemple-affilie", spoken_disclosure_at_s=140.0)
    assert m.SegmentSponsorise(start_s=100.0, end_s=145.0, type="affiliate",
                               product_id="exemple-affilie",
                               spoken_disclosure_at_s=112.0).overlay_rendered is False


def test_seuil_wer_depend_de_la_longueur_du_segment() -> None:
    """Sur 5 mots, un seul mot faux vaut déjà 20 % : le seuil suit la longueur (étape 7)."""
    asr = CFG.languages["en"].asr
    assert asr.seuil(4) == 0.20
    assert asr.seuil(19) == 0.15
    assert asr.seuil(120) == 0.08
