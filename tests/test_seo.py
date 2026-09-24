"""Étape 21 — référencement : chapitres, tags, sous-identifiant, mentions, titre.

Ce que ces tests protègent, c'est **ce qui envoie une requête à l'API en erreur ou une vidéo
hors des clous**, pas ce qui est joli.

- Un chapitre mal formé ne fait pas échouer l'upload : il ne s'affiche simplement **pas**, et
  personne ne s'en aperçoit avant de regarder la vidéo publiée. Les trois règles (premier à
  `0:00`, trois au minimum, 10 s d'écart) sont donc vérifiées ici et **aussi** par le modèle.
- Les 500 caractères de tags se comptent **guillemets compris** pour les tags à espace. Une
  liste calculée sans eux passe les tests et sort en `400 invalidTags`.
- Le sous-identifiant est la condition de l'économie unitaire (étape 27) : présent quand un
  produit est configuré, **absent sinon**, et sans la moindre donnée personnelle.
- Les mentions de conformité (`CONFORMITE` § 3) doivent être dans la description **en
  anglais**, qui est la langue de production.
"""

from __future__ import annotations

import pytest

from factory.core import config as config_module
from factory.core import models as m
from factory.editorial import seo


# --------------------------------------------------------------------------------------
# Matériel de test
# --------------------------------------------------------------------------------------


def _script(n: int = 8, lang: str = "en") -> m.Script:
    segments = [m.ScriptSegment(id="seg_00", role="hook",
                                narration="What if sugar could speak?",
                                on_screen_text="SUGAR IS A CODE",
                                visual_intent="a sugar crystal", open_loop="plant")]
    segments += [
        m.ScriptSegment(id=f"seg_{i:02d}", role="point",
                        narration=f"Point number {i} is demonstrated here. And it holds.",
                        on_screen_text=f"POINT NUMBER {i}", visual_intent=f"point {i}",
                        open_loop="payoff" if i == 1 else ("plant" if i == 4 else "none"))
        for i in range(1, n)
    ]
    segments.append(m.ScriptSegment(id=f"seg_{n:02d}", role="cta",
                                    narration="Which one surprised you the most?",
                                    visual_intent="a question", open_loop="none"))
    segments.append(m.ScriptSegment(id=f"seg_{n + 1:02d}", role="conclusion",
                                    narration="And here is the promised answer.",
                                    visual_intent="the answer", open_loop="payoff"))
    return m.Script(
        lang=lang, hook=m.Hook(type="question_contrarienne", text="What if sugar could speak?"),
        segments=segments,
        editorial_signature=m.SignatureEditoriale(
            angle="comparaison_chiffree",
            elements_proprietaires=["Three studies brought to one scale."],
        ),
        word_count=120, estimated_duration_s=600.0,
    )


def _timings(script: m.Script, pas: float = 30.0) -> m.Timings:
    segments = [
        m.SegmentVoix(id=s.id, file=f"voice/segment_{i:02d}.wav", start_s=i * pas,
                      end_s=(i + 1) * pas, duration_s=pas, text=s.narration)
        for i, s in enumerate(script.segments)
    ]
    return m.Timings(voice_id="serena_en", engine="qwen3_tts", sample_rate=24000, channels=1,
                     loudness_lufs=-14.0, true_peak_dbtp=-3.8,
                     total_duration_s=pas * len(segments), speed=1.0, segments=segments)


def _spec(channel_id: str = "bms-science-en", produit: str | None = None) -> m.VideoSpec:
    return m.VideoSpec(
        video_id=f"{channel_id}-20260920-ts2k", channel_id=channel_id, lang="en",
        niche="science_pop", style="illustre",
        topic=m.Topic(sujet="Sugar", angle="à définir par la recherche", source="manuel"),
        target_duration_s=648, cut_rhythm_target_s=5.85, seed=7,
        product_id=produit, created_at="2026-09-20T08:00:00Z",
    )


def _manifest(spec: m.VideoSpec, relecteur: str | None = "thomas") -> m.RunManifest:
    manifest = m.RunManifest(
        identite=m.ManifestIdentite(
            video_id=spec.video_id, channel_id=spec.channel_id, lang=spec.lang,
            niche=spec.niche, style=spec.style, template_id="sci-b",
            charte_version="2026.09.1",
        ),
        decisions=m.ManifestDecisions(topic=spec.topic, hook_type="question_contrarienne"),
    )
    manifest.conformite.reviewer = relecteur
    manifest.decisions.duration_s = 300.0
    return manifest


def _contexte(produit: bool = False, relecteur: str | None = "thomas"):
    """`(spec, script, timings, manifest, channel, cfg, langue)` prêts pour `seo.composer`."""
    cfg = config_module.charger(strict=False)
    channel = cfg.get_channel("bms-science-en")
    if produit:
        channel = channel.model_copy(update={"products": ["exemple-affilie"]})
    spec = _spec(channel.id, "exemple-affilie" if produit else None)
    script = _script()
    return (spec, script, _timings(script), _manifest(spec, relecteur), channel, cfg,
            cfg.langue_de(channel))


def _composer(produit: bool = False, titre: str = "What if sugar could speak to your cells",
              relecteur: str | None = "thomas"):
    spec, script, timings, manifest, channel, cfg, langue = _contexte(produit, relecteur)
    return seo.composer(
        spec=spec, script=script, timings=timings, research=None, manifest=manifest,
        channel=channel, cfg=cfg, langue=langue, titre=titre, miniature="variant_1",
        synthetique=False, motif_synthetique=None, virtuelles=False, reseau=False,
    )


# --------------------------------------------------------------------------------------
# Chapitres
# --------------------------------------------------------------------------------------


def test_les_chapitres_tiennent_les_trois_regles_de_youtube() -> None:
    """Premier à 0:00, trois au minimum, 10 s d'écart : sous l'une des trois, rien ne s'affiche."""
    script = _script()
    chapitres, _alertes = seo.chapitres_depuis_timings(
        _timings(script), script, 300.0, "title_case"
    )
    assert len(chapitres) >= 3
    assert chapitres[0].start_s == 0.0
    ecarts = [b.start_s - a.start_s for a, b in zip(chapitres, chapitres[1:], strict=False)]
    assert all(e >= seo.ECART_CHAPITRE_MIN_S for e in ecarts), ecarts
    assert chapitres == sorted(chapitres, key=lambda c: c.start_s)
    assert chapitres[0].horodatage() == "0:00"


def test_moins_de_trois_chapitres_ne_produit_aucun_sommaire() -> None:
    """YouTube n'affiche rien sous trois chapitres : mieux vaut aucun qu'un sommaire mort."""
    script = _script()
    chapitres, alertes = seo.chapitres_depuis_timings(_timings(script, pas=5.0), script, 15.0)
    assert chapitres == []
    assert any("3" in alerte for alerte in alertes)


def test_le_modele_refuse_les_chapitres_que_youtube_refuserait() -> None:
    """Le contrôle n'est pas seulement dans la fonction : `VideoMetadata` le rejoue."""
    metadata, _liens, _alertes = _composer()
    brut = metadata.model_dump(mode="json")
    for cas, chapitres in (
        ("premier hors de zéro", [{"start_s": 3.0, "title": "Un"}, {"start_s": 40.0,
         "title": "Deux"}, {"start_s": 80.0, "title": "Trois"}]),
        ("moins de trois", [{"start_s": 0.0, "title": "Un"}, {"start_s": 40.0, "title": "Deux"}]),
        ("écart sous 10 s", [{"start_s": 0.0, "title": "Un"}, {"start_s": 5.0, "title": "Deux"},
         {"start_s": 40.0, "title": "Trois"}]),
    ):
        with pytest.raises(ValueError, match="chapitres"):
            m.VideoMetadata.model_validate({**brut, "chapters": chapitres}), cas


# --------------------------------------------------------------------------------------
# Tags et hashtags
# --------------------------------------------------------------------------------------


def test_les_tags_tiennent_le_plafond_guillemets_compris() -> None:
    """Un tag à espace coûte deux caractères de plus : c'est la règle de l'API, pas la nôtre."""
    metadata, _liens, _alertes = _composer()
    cumul = sum(seo.cout_tag(t) for t in metadata.tags) + max(0, len(metadata.tags) - 1)
    assert cumul <= seo.TAGS_MAX_CARACTERES
    assert metadata.tags, "aucun tag produit"
    assert seo.cout_tag("sugar") == 5
    assert seo.cout_tag("sugar code") == 12          # 10 + 2 guillemets


def test_un_tag_a_espace_est_compte_avec_ses_guillemets() -> None:
    """Le même test, mais sur une liste construite pour frôler le plafond."""
    script = _script(n=8)
    cfg = config_module.charger(strict=False)
    channel = cfg.get_channel("bms-science-en")
    longs = [f"a very long multi word tag number {i}" for i in range(40)]
    liste = seo.tags(script, channel, None, suggestions=longs)
    a_espace = [t for t in liste if " " in t]
    assert a_espace, "le cas testé n'est pas atteint : aucun tag à espace retenu"
    cumul = sum(seo.cout_tag(t) for t in liste) + max(0, len(liste) - 1)
    naif = sum(len(t) for t in liste) + max(0, len(liste) - 1)
    assert cumul <= seo.TAGS_MAX_CARACTERES
    # Et le décompte naïf, lui, aurait laissé passer 2 caractères par tag à espace de plus.
    assert cumul == naif + 2 * len(a_espace)
    assert m.VideoMetadata.cout_tag("sugar code") == seo.cout_tag("sugar code")


def test_trois_hashtags_au_plus_et_ils_sont_dans_la_description() -> None:
    """YouTube n'en affiche que trois au-dessus du titre ; ils doivent figurer dans le texte."""
    metadata, _liens, _alertes = _composer()
    assert len(metadata.hashtags) <= seo.HASHTAGS_AFFICHES
    for hashtag in metadata.hashtags:
        assert hashtag.startswith("#") and " " not in hashtag
        assert hashtag in metadata.description


# --------------------------------------------------------------------------------------
# Sous-identifiant d'affiliation
# --------------------------------------------------------------------------------------


def test_le_subid_est_present_quand_un_produit_est_configure() -> None:
    """Sans lui, aucune rentabilité par vidéo n'est mesurable (CONFORMITE § 10.4)."""
    metadata, liens, _alertes = _composer(produit=True)
    assert liens, "un produit est configuré et aucun lien n'a été composé"
    lien = liens[0]
    assert lien.subid_value == _spec().video_id  # sub_id_format "{video_id}" (étape 27)
    assert lien.subid_param and f"{lien.subid_param}={lien.subid_value}" in lien.target_url
    assert lien.target_url in metadata.description
    assert metadata.paid_promotion is True


def test_le_subid_est_absent_sans_produit() -> None:
    """Pas de produit, pas de lien, pas de mention : une divulgation sans promotion est fausse."""
    metadata, liens, _alertes = _composer(produit=False)
    assert liens == []
    assert metadata.paid_promotion is False
    assert metadata.description_blocks.affiliate == []
    langue = config_module.charger(strict=False).languages["en"]
    assert langue.disclosure.overlay_generic.upper() not in metadata.description


def test_le_subid_ne_contient_aucune_donnee_personnelle() -> None:
    """CJ : « keep it to 64 characters or less », sans donnée personnelle : le video_id seul."""
    _metadata, liens, _alertes = _composer(produit=True)
    subid = liens[0].subid_value or ""
    assert subid == _spec().video_id and len(subid) <= 50  # tient même dans clickref (Awin)
    assert "@" not in subid and " " not in subid
    assert subid.replace("-", "").replace("_", "").isalnum()


def test_le_commentaire_epingle_porte_le_meme_subid_que_la_description() -> None:
    """Deux sub-ID sur la même vidéo rendraient l'attribution par vidéo illisible."""
    metadata, liens, _alertes = _composer(produit=True)
    assert metadata.pinned_comment is not None
    assert liens[0].target_url in metadata.pinned_comment
    # Et il pose bien une question au spectateur, sinon il n'a pas de raison d'exister.
    assert "?" in metadata.pinned_comment


# --------------------------------------------------------------------------------------
# Mentions de conformité et titre
# --------------------------------------------------------------------------------------


def test_les_mentions_de_conformite_sont_presentes_en_anglais() -> None:
    """La langue de production est l'anglais : les mentions y sont, mot pour mot du fichier."""
    metadata, _liens, _alertes = _composer()
    langue = config_module.charger(strict=False).languages["en"]
    assert langue.disclosure.ia_production in metadata.description
    assert langue.disclosure.ia_controle_humain in metadata.description
    assert metadata.default_language == "en"


def test_sans_relecteur_humain_la_mention_de_relecture_disparait() -> None:
    """Dire qu'un humain a relu sous `auto-approve` serait une fausse déclaration (RIA art. 50)."""
    metadata, _liens, _alertes = _composer(relecteur="auto-approve")
    langue = config_module.charger(strict=False).languages["en"]
    assert langue.disclosure.ia_production in metadata.description
    assert langue.disclosure.ia_controle_humain not in metadata.description


def test_la_mention_commerciale_ouvre_la_description() -> None:
    """CONFORMITE § 3 couche 3 prime sur l'ordre d'INTERFACES : la mention passe en tête."""
    metadata, _liens, _alertes = _composer(produit=True)
    langue = config_module.charger(strict=False).languages["en"]
    assert metadata.description.startswith(langue.disclosure.overlay_generic.upper())


def test_le_titre_retenu_tient_le_plafond_de_soixante_dix() -> None:
    """Au-delà de 70 caractères, YouTube tronque : le plafond est une règle, pas un conseil."""
    metadata, _liens, alertes = _composer()
    assert len(metadata.title_chosen) <= 70
    assert not any("caractères" in a and "tronque" in a for a in alertes)
    long_titre = "What if sugar could speak to every single cell of your body and to your brain"
    assert len(long_titre) > 70
    _meta, _liens2, alertes_longues = _composer(titre=long_titre)
    assert any("tronque" in a for a in alertes_longues)


# --------------------------------------------------------------------------------------
# Description : blocs, octets, localisations
# --------------------------------------------------------------------------------------


def test_la_description_porte_ses_blocs_et_tient_en_octets() -> None:
    """Le plafond de l'API se compte en octets — un tiret cadratin en vaut trois."""
    metadata, _liens, _alertes = _composer()
    assert len(metadata.description.encode("utf-8")) <= seo.DESCRIPTION_MAX_OCTETS
    assert metadata.description_blocks.summary, "aucun sommaire composé"
    for ligne in metadata.description_blocks.summary:
        assert ligne in metadata.description
    for chapitre in metadata.chapters:
        assert f"{chapitre.horodatage()} {chapitre.title}" in metadata.description


def test_le_sommaire_ne_reprend_ni_le_hook_ni_la_publicite() -> None:
    """Le sommaire décrit la vidéo ; le hook est déjà l'accroche et le sponsor n'est pas du fond."""
    script = _script()
    lignes = seo.sommaire(script, "title_case")
    assert lignes and len(lignes) <= seo.SOMMAIRE_LIGNES
    assert all(ligne.lower() != "sugar is a code" for ligne in lignes)
    assert len(set(lignes)) == len(lignes)


def test_les_localisations_restent_vides_tant_que_l_etape_24_n_a_pas_tourne() -> None:
    """Une localisation non relue serait une traduction publiée que personne n'a lue."""
    metadata, _liens, _alertes = _composer()
    assert metadata.localizations == {}


def test_une_localisation_relue_est_reprise_telle_quelle() -> None:
    """Quand la chaîne en porte une, elle passe — et la langue par défaut part avec elle."""
    cfg = config_module.charger(strict=False)
    channel = cfg.get_channel("bms-science-en").model_copy(update={
        "localizations": {"fr": m.TraductionChaine(title="Et si le sucre parlait ?",
                                                   description="Description française.")}
    })
    sorties = seo.localizations(channel, cfg, "What if sugar could speak", "English body.")
    assert sorties["fr"]["title"] == "Et si le sucre parlait ?"
    assert sorties["en"]["title"] == "What if sugar could speak"


# --------------------------------------------------------------------------------------
# Titres — tirage de patrons, note de règles, tournoi
# --------------------------------------------------------------------------------------

PATRONS = [
    {"id": "nom_propre_en_tete", "template": "{Nom} {verbe}", "part": 0.306},
    {"id": "question_en_tete", "template": "{Mot interrogatif} ?", "part": 0.252},
    {"id": "deux_points", "template": "{Sujet} : {promesse}", "part": 0.127},
    {"id": "superlatif", "template": "The {sup}", "part": 0.104},
    {"id": "nombre_en_tete", "template": "{Nombre} {choses}", "part": 0.0},
]
CIBLE = {"longueur_car": {"mediane": 58.0, "p90": 87.0, "plafond_recommande": 87.0}}
INTERDITS = ["shocking", "you won't believe"]
CURIOSITE = ["nobody", "what happens", "scientists"]


def test_le_tirage_de_patrons_suit_les_parts_sans_jamais_fermer_la_queue() -> None:
    """Pondéré, donc le dominant sort plus souvent ; à plancher, donc le nul sort parfois."""
    from factory.editorial import titles

    sortis = [titles.tirer_patrons(PATRONS, 3, seed=graine) for graine in range(200)]
    premiers = [lot[0]["id"] for lot in sortis]
    assert premiers.count("nom_propre_en_tete") > premiers.count("deux_points")
    assert all(len({p["id"] for p in lot}) == 3 for lot in sortis), "tirage avec remise"
    tous = {p["id"] for lot in sortis for p in lot}
    assert "nombre_en_tete" in tous, "un patron de part nulle ne doit pas être exclu à jamais"


def test_les_poids_appris_multiplient_la_mesure_sans_l_effacer(tmp_path) -> None:
    """Étape 26 : `learned/weights.json` corrige le corpus, il ne le remplace pas."""
    import json

    from factory.editorial import titles

    assert titles.charger_poids_appris(tmp_path) == {}
    (tmp_path / "learned").mkdir()
    (tmp_path / "learned" / "weights.json").write_text(json.dumps(
        {"version": "1.0",
         "titles": {"patterns": {"question_en_tete": 1.2, "deux_points": "x", "superlatif": 99.0}}}
    ), encoding="utf-8")
    appris = titles.charger_poids_appris(tmp_path)
    assert appris["question_en_tete"] == 1.2
    assert "deux_points" not in appris, "une valeur illisible doit être ignorée, pas propagée"
    assert appris["superlatif"] == 1.4, "le multiplicateur est borné : 99 effacerait la mesure"
    poids = titles.poids_patrons(PATRONS, appris)
    assert poids["question_en_tete"] == pytest.approx(0.252 * 1.2)
    assert poids["nom_propre_en_tete"] == pytest.approx(0.306)


def test_les_majuscules_criees_annulent_le_score() -> None:
    """Un sigle passe ; deux mots criés, c'est la politique spam qui commence."""
    from factory.editorial import titles

    crie, _p, motifs = titles.scorer_titre(
        "SUGAR IS DESTROYING your cells and nobody says it", PATRONS, CIBLE, INTERDITS,
        curiosite=CURIOSITE,
    )
    assert crie == 0.0 and "majuscules abusives" in motifs
    sigle, _p2, _m2 = titles.scorer_titre(
        "What NASA found about sugar inside your own cells", PATRONS, CIBLE, INTERDITS,
        curiosite=CURIOSITE,
    )
    assert sigle > 0.0


def test_un_mot_de_curiosite_vaut_mieux_que_trois() -> None:
    """Un mot ouvre une boucle ; trois empilés sont un appât, et la note le dit."""
    from factory.editorial import titles

    un, _p, motifs = titles.scorer_titre(
        "What happens to your cells when you stop eating sugar", PATRONS, CIBLE, INTERDITS,
        curiosite=CURIOSITE,
    )
    trois, _p2, _m2 = titles.scorer_titre(
        "What happens when nobody tells scientists about sugar", PATRONS, CIBLE, INTERDITS,
        curiosite=CURIOSITE,
    )
    assert un > trois
    assert any("curiosité" in motif for motif in motifs)
    # Sous-chaîne interdite : « no one » ne doit pas se trouver dans « casino needs ».
    assert titles.mots_curiosite_presents("A casino needs sugar", ["no one"]) == []


def test_le_tournoi_range_le_vainqueur_en_tete_sans_appeler_le_llm(monkeypatch) -> None:
    """Le duel est remplacé par une règle connue : c'est l'ordre du tournoi qu'on vérifie."""
    from factory.editorial import titles

    # Le plus court gagne toujours — règle arbitraire mais déterministe.
    monkeypatch.setattr(titles, "duel",
                        lambda g, d, *a, **k: (0 if len(g) <= len(d) else 1, "le plus court"))
    candidats = ["aaaa", "aa", "aaaaaa", "a"]
    rangs, journal = titles.tournoi(candidats, "sujet", "angle", seed=1)
    assert candidats[rangs[0]] == "a"
    assert len(rangs) == len(candidats) and len(set(rangs)) == len(candidats)
    assert len(journal) == 3, "deux demi-finales et une finale"


def test_un_duel_indisponible_rend_la_main_a_l_heuristique(monkeypatch) -> None:
    """Un LLM muet ne doit pas produire un classement aléatoire, mais celui d'avant."""
    from factory.editorial import titles
    from factory.llm import ErreurLLM

    def tombe(*_a, **_k):
        raise ErreurLLM("poids absents")

    monkeypatch.setattr(titles, "generate_json", tombe)
    gagnant, motif = titles.duel("premier", "second", "sujet", "angle")
    assert gagnant == 0 and "indisponible" in motif


# --------------------------------------------------------------------------------------
# Miniatures — mesures et rotation
# --------------------------------------------------------------------------------------


def test_les_trois_combinaisons_different_deux_a_deux() -> None:
    """Trois variantes qui ne diffèrent que par le texte ne mesurent pas la composition."""
    from factory.editorial import thumbnails_variants as tv

    combos = tv.combinaisons([("Sugar Code", 0.8), ("Hidden Sugar", 0.7), ("Cell Damage", 0.6)],
                             ["bandeau_bas", "bloc_gauche"], seed=7)
    couples = {(c.gabarit, c.palette) for c in combos}
    assert len(couples) == 3
    assert len({c.texte for c in combos}) == 3


def test_la_distance_de_palette_voit_ce_que_le_contraste_ne_voit_pas() -> None:
    """Deux couleurs de même luminance passent le contraste et restent indiscernables."""
    from factory.editorial import thumbnails_variants as tv

    # Rouge et vert de **même luminance relative** : le contraste WCAG les déclare identiques.
    rouge, vert = (188, 0, 0), (0, 108, 0)
    assert tv.contraste_wcag(rouge, vert) == pytest.approx(1.0, abs=0.02)
    assert tv.distance_lab(rouge, vert) > 40.0
    assert tv.distance_lab((255, 255, 255), (250, 250, 250)) < 5.0


def test_la_variance_du_laplacien_separe_le_net_du_flou() -> None:
    """La netteté n'est pas une opinion : un damier est net, un dégradé ne l'est pas."""
    import numpy as np

    from factory.editorial import thumbnails_variants as tv

    damier = np.indices((94, 168)).sum(axis=0) % 2 * 255.0
    degrade = np.tile(np.linspace(0, 255, 168), (94, 1))
    assert tv.variance_laplacien(damier) > 10 * tv.variance_laplacien(degrade)


def test_le_score_de_miniature_punit_l_illisible_en_vignette() -> None:
    """Sous 10 px de haut à 168 px, la miniature n'est pas moyenne : elle n'existe pas."""
    from factory.core.models import MesuresMiniature
    from factory.editorial import thumbnails_variants as tv

    lisible = MesuresMiniature(contrast_ratio=8.0, text_area_pct=12.0, text_height_px_168=14.0,
                               sharpness_168=400.0, saliency_under_text=0.1,
                               palette_distance=60.0)
    minuscule = lisible.model_copy(update={"text_height_px_168": 4.0})
    terne = lisible.model_copy(update={"contrast_ratio": 2.0})
    assert tv.scorer(lisible, 0.8) > tv.scorer(minuscule, 0.8)
    assert tv.scorer(lisible, 0.8) > tv.scorer(terne, 0.8)
    assert 0.0 <= tv.scorer(minuscule, 0.8) <= 1.0


def test_le_plan_de_rotation_liste_les_variantes_restantes() -> None:
    """Aucune API de test A/B : la rotation est le seul plan exécutable (étape 21)."""
    from factory.core.models import RotationMiniature
    from factory.editorial import thumbnails_variants as tv

    rotation = RotationMiniature(after_days=tv.ROTATION_APRES_JOURS,
                                 criterion=tv.CRITERE_ROTATION,
                                 next_variants=["variant_2", "variant_3"])
    assert rotation.after_days == 7
    assert "CTR" in rotation.criterion and "médiane" in rotation.criterion
    assert rotation.rotations_done == 0


def test_les_intitules_de_blocs_sont_dans_la_langue_de_la_video() -> None:
    """Une description anglaise sortait « Sources : » et « Crédits : » — du français publié."""
    metadata, _liens, _alertes = _composer()
    langue = config_module.charger(strict=False).languages["en"]
    assert langue.libelles.credits == "Credits"
    if metadata.description_blocks.attribution:
        assert f"{langue.libelles.credits} :" in metadata.description
        assert "Crédits :" not in metadata.description
    if metadata.description_blocks.sources:
        assert f"{langue.libelles.sources} :" in metadata.description


def test_le_degraissage_reconnait_le_bloc_de_credits_dans_sa_langue() -> None:
    """Le dégraissage cherchait « Crédits : » littéralement : en anglais il ne trouvait rien."""
    libelles = m.LibellesDescription(sources="Sources", credits="Credits")
    credits = [f'"Photo {n}" by Author {n} is licensed CC BY 4.0 — https://x.org/{n}'
               for n in range(120)]
    blocs = m.BlocsDescription(hook="A hook.", attribution=credits,
                               sources=[f"Source {n} — https://x.org/s{n}" for n in range(20)])
    texte = seo.composer_description(blocs, None, libelles)
    assert len(texte.encode("utf-8")) <= seo.DESCRIPTION_MAX_OCTETS
    assert texte.count("Credits :") == 1
    assert seo.credits_omis, "des crédits ont dû être écartés et n'ont pas été comptés"
    gardees = [ligne[2:] for ligne in texte.splitlines() if ligne.startswith("— ")]
    assert all(ligne in credits or ligne.startswith("Source ") or "autres crédits" in ligne
               for ligne in gardees)
