"""Étape 13.2 — titres, miniature, métadonnées, orchestrateur.

Quatre familles d'invariants, choisies sur ce qui s'est réellement cassé pendant l'étape.

- **Le score doit départager.** Un score qui rend 1,0 à toutes les variantes ne choisit pas,
  il constate l'ordre d'arrivée : c'est arrivé aux trois miniatures et aux cinq textes du
  premier jet. Deux tests exigent donc des scores **distincts**.
- **La forme prime sur la déclaration.** Le LLM étiquette ses propres titres ; en casse de
  titre, une expression régulière « majuscule + majuscule » reconnaît `nom_propre_en_tete`
  partout. Le test fixe la règle : forme vérifiable d'abord, étiquette déclarée ensuite.
- **La conformité se calcule, elle ne se déclare pas.** `contains_synthetic_media` et
  « Images virtuelles » ont deux déclencheurs distincts (`CONFORMITE` § 3) : quatre tests
  couvrent les quatre combinaisons.
- **La reprise doit voir qu'un amont a changé.** Un marqueur `.done` qui ne porterait que le
  nom de l'étape rejouerait un run sur des entrées périmées.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from factory import run as orchestrateur
from factory.core import models as m
from factory.core.paths import RunPaths
from factory.editorial import seo as M
from factory.steps import metadata as MS
from factory.editorial import thumbnails_variants as T
from factory.editorial import titles as TT

PATRONS = [
    {"id": "nom_propre_en_tete", "template": "{Nom} {verbe}", "part": 0.306},
    {"id": "question_en_tete", "template": "{Mot interrogatif} ?", "part": 0.252},
    {"id": "deux_points", "template": "{Sujet} : {promesse}", "part": 0.127},
    {"id": "superlatif", "template": "The {sup}", "part": 0.104},
    {"id": "nombre_en_tete", "template": "{Nombre} {choses}", "part": 0.017},
]
CIBLE = {"longueur_car": {"mediane": 58.0, "p90": 87.0, "plafond_recommande": 87.0}}
INTERDITS = ["vous ne croirez jamais", "cliquez ici"]


# --- titres ---------------------------------------------------------------------------


def test_un_mot_interdit_annule_le_score() -> None:
    """Le filtre anti-appât est éliminatoire, pas pondéré."""
    score, _patron, motifs = TT.scorer_titre(
        "Vous ne croirez jamais ce que fait le sucre", PATRONS, CIBLE, INTERDITS
    )
    assert score == 0.0
    assert any("mot interdit" in motif for motif in motifs)


def test_un_titre_trop_long_perd_la_note_de_longueur() -> None:
    """Au-delà de 70 caractères, YouTube tronque : la note de longueur tombe à zéro."""
    long_titre = "Pourquoi " + "le sucre " * 8
    score_long, _p, motifs = TT.scorer_titre(long_titre, PATRONS, CIBLE, INTERDITS)
    score_court, _p2, _m2 = TT.scorer_titre(
        "Pourquoi le sucre transforme vos cellules ?", PATRONS, CIBLE, INTERDITS
    )
    assert len(long_titre) > TT.PLAFOND_CARACTERES
    assert any("plafond" in motif for motif in motifs)
    assert score_court > score_long


@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        ("Pourquoi le sucre transforme vos cellules", "question_en_tete"),
        ("3 choses que le sucre fait à votre foie", "nombre_en_tete"),
        ("Le sucre : un code que votre corps ignore", "deux_points"),
        ("The Most Dangerous Sugar In Your Kitchen", "superlatif"),
    ],
)
def test_le_patron_se_lit_sur_la_forme(titre: str, attendu: str) -> None:
    """Les patrons vérifiables se reconnaissent sans croire l'étiquette du modèle."""
    assert TT._patron_detecte(titre, PATRONS, declare="nom_propre_en_tete") == attendu


def test_l_etiquette_du_modele_ne_sert_qu_en_repli() -> None:
    """Aucune forme ne tranche : l'étiquette déclarée passe, si elle existe au corpus."""
    assert TT._patron_detecte("Marie Curie et le sucre", PATRONS, "nom_propre_en_tete") == \
        "nom_propre_en_tete"
    assert TT._patron_detecte("Marie Curie et le sucre", PATRONS, "patron_invente") is None
    assert TT._patron_detecte("Marie Curie et le sucre", PATRONS, None) is None


def test_la_casse_de_phrase_est_imposee_mais_garde_les_noms_propres() -> None:
    """La charte tranche la casse ; « Curie » n'est pas décapitalisé pour autant."""
    texte, modifie = TT.normaliser_casse(
        "Le Sucre De Curie Change Tout", "phrase_case", {"curie"}
    )
    assert texte == "Le sucre de Curie change tout"
    assert modifie
    intact, touche = TT.normaliser_casse("The Sugar Code", "title_case", set())
    assert intact == "The Sugar Code" and not touche


def test_les_textes_de_miniature_se_departagent() -> None:
    """Trois textes recevables ne peuvent pas avoir le même score : sinon rien n'est choisi."""
    scores = {
        texte: TT.scorer_texte_miniature(texte, 1.5, 9, INTERDITS)[0]
        for texte in ("Insuline Cachée", "Métabolisme Détruit", "Sucre Toxicité")
    }
    assert len(set(scores.values())) == len(scores), scores
    un_mot, motifs = TT.scorer_texte_miniature("Un", 1.5, 9, INTERDITS)
    assert un_mot < min(scores.values()) and any("hors de" in motif for motif in motifs)


# --- miniature ------------------------------------------------------------------------


def test_le_contraste_wcag_est_celui_de_la_norme() -> None:
    """Noir sur blanc = 21, la borne haute de WCAG 2.1 ; une couleur sur elle-même = 1."""
    assert T.contraste_wcag((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=0.01)
    assert T.contraste_wcag((23, 45, 67), (23, 45, 67)) == pytest.approx(1.0, abs=0.001)


def test_la_miniature_composee_tient_ses_trois_seuils(tmp_path: Path) -> None:
    """Rendu réel par Playwright : 1280×720, texte ≥ 12 % de la hauteur, moins de 2 Mo."""
    from PIL import Image

    fond = tmp_path / "fond.png"
    Image.new("RGB", (1280, 720), (18, 90, 80)).save(fond)
    charte = m.Charte(
        version="test", fonts=m.Polices(title="Inter SemiBold", body="Inter Regular"),
        palette=m.Palette(bg="#101820", text="#ffffff", text_outline="#0a0a0a",
                          accent="#2f9e8f", highlight="#ffd166"),
        transitions=["cut"],
    )
    combo = T.Combinaison(index=1, texte="Sucre Toxicité", gabarit="bandeau_bas",
                          palette="charte", note_texte=0.8)
    variantes, _alertes = T.composer(
        [combo], fond, charte, "BMS SCIENCE",
        Path("assets/fonts/Inter[opsz,wght].ttf").resolve(), tmp_path, tmp_path / ".compo",
    )
    variante = variantes[0]
    sortie = tmp_path / "variant_1.png"
    with Image.open(sortie) as image:
        assert image.size == (T.LARGEUR, T.HAUTEUR)
    assert sortie.stat().st_size / 1e6 < T.POIDS_MAX_MO
    assert (variante.text_height_ratio or 0) >= charte.thumbnail.hauteur_texte_min
    assert (variante.contrast_ratio or 0) >= 4.5
    assert variante.legible_at_320px


def test_deux_gabarits_au_minimum() -> None:
    """La rotation de gabarits est une exigence anti-clonage (CONFORMITE § 5)."""
    with pytest.raises(ValidationError):
        m.MiniatureCharte(templates=["bandeau_bas"])


# --- métadonnées ----------------------------------------------------------------------


def _script(n: int = 8) -> m.Script:
    segments = [m.ScriptSegment(id="seg_00", role="hook", narration="Et si le sucre parlait.",
                                on_screen_text="LE SUCRE EST UN CODE",
                                visual_intent="un cristal de sucre", open_loop="plant")]
    segments += [
        m.ScriptSegment(id=f"seg_{i:02d}", role="point",
                        narration=f"Le point numéro {i} se démontre ici. Et il tient.",
                        on_screen_text=f"POINT NUMERO {i}", visual_intent=f"le point {i}",
                        open_loop="payoff" if i == 1 else "none")
        for i in range(1, n)
    ]
    segments.append(m.ScriptSegment(id=f"seg_{n:02d}", role="point",
                                    narration="Deuxième boucle plantée puis payée.",
                                    visual_intent="une boucle", open_loop="plant"))
    segments.append(m.ScriptSegment(id=f"seg_{n + 1:02d}", role="conclusion",
                                    narration="Et voilà la réponse promise.",
                                    visual_intent="la réponse", open_loop="payoff"))
    return m.Script(
        lang="fr", hook=m.Hook(type="question_contrarienne", text="Et si le sucre parlait ?"),
        segments=segments,
        editorial_signature=m.SignatureEditoriale(
            angle="comparaison_chiffree",
            elements_proprietaires=["Trois études ramenées à une même échelle."],
        ),
        word_count=120, estimated_duration_s=600.0,
    )


def _timings(script: m.Script, pas: float = 30.0) -> m.Timings:
    segments = [
        m.SegmentVoix(id=s.id, file=f"voice/segment_{i:02d}.wav", start_s=i * pas,
                      end_s=(i + 1) * pas, duration_s=pas, text=s.narration)
        for i, s in enumerate(script.segments)
    ]
    return m.Timings(voice_id="serena_fr", engine="qwen3_tts", sample_rate=24000, channels=1,
                     loudness_lufs=-14.0, true_peak_dbtp=-3.8,
                     total_duration_s=pas * len(segments), speed=1.0, segments=segments)


def test_les_chapitres_partent_de_zero_et_respirent() -> None:
    """Premier chapitre à 0 s, 10 s d'écart au minimum, et pas un chapitre par phrase."""
    script = _script(10)
    timings = _timings(script, pas=12.0)
    chapitres, _alertes = M.chapitres_depuis_timings(timings, script, timings.total_duration_s)
    assert chapitres[0].start_s == 0.0
    assert len(chapitres) <= M.CHAPITRES_MAX
    ecarts = [b.start_s - a.start_s for a, b in zip(chapitres, chapitres[1:], strict=False)]
    assert all(e >= M.ECART_CHAPITRE_MIN_S for e in ecarts)
    assert chapitres[1].title == chapitres[1].title.capitalize()  # pas de capitales criées


def test_moins_de_trois_chapitres_ne_produit_aucun_sommaire() -> None:
    """YouTube n'affiche rien sous trois chapitres : mieux vaut aucun qu'un sommaire mort."""
    script = _script(2)
    chapitres, alertes = M.chapitres_depuis_timings(_timings(script, pas=5.0), script, 15.0)
    assert chapitres == []
    assert alertes


def test_l_horodatage_est_celui_que_youtube_reconnait() -> None:
    """`0:00`, `10:40`, `1:02:03` — pas de millisecondes, pas d'heure à zéro inutile."""
    assert m.Chapitre(start_s=0, title="a").horodatage() == "0:00"
    assert m.Chapitre(start_s=640.2, title="a").horodatage() == "10:40"
    assert m.Chapitre(start_s=3723, title="a").horodatage() == "1:02:03"


def _asset(shot: str, realiste: bool) -> m.Asset:
    return m.Asset(
        asset_id=f"{abs(hash(shot)):016x}"[:16], path=f"assets/{shot}/image.png",
        provider="flux", author="BMS (généré)", licence="Apache-2.0",
        licence_url="https://www.apache.org/licenses/LICENSE-2.0",
        downloaded_at="2026-09-17T08:00:00Z", realistic=realiste,
        generator=m.Generateur(model="mlx-community/FLUX.2-Klein-4B-4bit",
                               prompt_hash="a" * 64, seed=1, steps=4, resolution="1280x720"),
    )


def _shotlist(personnes: dict[str, bool]) -> m.Shotlist:
    shots = [
        m.Shot(id=shot, segment_id="seg_00", start_s=i * 5.0, end_s=(i + 1) * 5.0,
               duration_s=5.0, visual_intent="un cristal", motion="static", transition_in="cut",
               asset_request=m.AssetRequest(type="image", prompt_or_keywords="cristal",
                                            contains_person=personne, realistic=False),
               seed=1)
        for i, (shot, personne) in enumerate(personnes.items())
    ]
    return m.Shotlist(
        shots=shots,
        stats=m.StatsShotlist(n_shots=len(shots), target_s=5.0, median_shot_s=5.0,
                              p10_shot_s=5.0, p90_shot_s=5.0, tolerance=0.15,
                              hook_shots_max_s=3.0),
    )


@pytest.mark.parametrize(
    ("realiste", "personne", "synthetique", "virtuelles"),
    [(False, False, False, False), (False, True, False, True),
     (True, False, True, False), (True, True, True, True)],
)
def test_les_deux_divulgations_ont_deux_declencheurs(
    realiste: bool, personne: bool, synthetique: bool, virtuelles: bool
) -> None:
    """§ 3 : le réalisme déclenche le label YouTube, la silhouette la mention française."""
    assets = [_asset("shot_00", realiste)]
    shotlist = _shotlist({"shot_00": personne})
    drapeau, motif, mention, scenes = MS.evaluer_synthetique(assets, shotlist, "illustre")
    assert drapeau is synthetique
    assert mention is virtuelles
    assert (motif is not None) is synthetique
    assert len(scenes) == 1 and scenes[0].realistic is realiste


def test_les_tags_tiennent_le_plafond_de_cinq_cents_caracteres() -> None:
    """Le plafond est cumulé, séparateurs compris — il se coupe, il ne se dépasse pas."""
    from factory.core import config as config_module

    script = _script(30)
    channel = config_module.charger(strict=False).get_channel("bms-science-fr")
    tags = M.tags(script, channel, None)
    assert sum(len(t) for t in tags) + max(0, len(tags) - 1) <= M.TAGS_MAX_CARACTERES


def test_metadata_refuse_ce_que_youtube_refuse() -> None:
    """Trois refus du modèle : tags trop longs, sommaire trop court, public enfants."""
    blocs = m.BlocsDescription(hook="Accroche.")
    base = {
        "title_chosen": "Un titre", "description": "Texte", "description_blocks": blocs,
        "category_id": "28", "default_language": "fr", "default_audio_language": "fr",
    }
    with pytest.raises(ValidationError, match="500 au maximum"):
        m.VideoMetadata(**base, tags=["x" * 60] * 10)
    with pytest.raises(ValidationError, match="au moins 3"):
        m.VideoMetadata(**base, chapters=[m.Chapitre(start_s=0, title="a"),
                                          m.Chapitre(start_s=30, title="b")])
    with pytest.raises(ValidationError, match="enfants"):
        m.VideoMetadata(**base, made_for_kids=True)


# --- orchestrateur --------------------------------------------------------------------


def test_un_amont_modifie_invalide_le_marqueur(tmp_path: Path) -> None:
    """Sans empreinte d'entrées, une reprise rejouerait un run sur des fichiers périmés."""
    chemins = RunPaths.depuis_video_id("bms-science-fr-20260917-ts24", tmp_path)
    chemins.racine.mkdir(parents=True)
    (chemins.racine / "script.json").write_text('{"a": 1}', encoding="utf-8")
    (chemins.racine / "shotlist.json").write_text('{"b": 2}', encoding="utf-8")
    orchestrateur.marquer(chemins, "thumbnail", "2026-09-17T08:00:00Z", 12.0, 0)
    assert orchestrateur.etape_faite(chemins, "thumbnail")
    (chemins.racine / "script.json").write_text('{"a": 2}', encoding="utf-8")
    assert not orchestrateur.etape_faite(chemins, "thumbnail")


def test_le_dag_va_du_plan_a_l_export() -> None:
    """L'ordre du DAG est un contrat : la miniature passe avant les métadonnées."""
    assert orchestrateur.NOEUDS[0] == "plan" and orchestrateur.NOEUDS[-1] == "export"
    assert orchestrateur.NOEUDS.index("thumbnail") < orchestrateur.NOEUDS.index("metadata")
    assert orchestrateur.NOEUDS.index("metadata") < orchestrateur.NOEUDS.index("export")
    assert set(orchestrateur.TIMEOUTS) | {"render"} == set(orchestrateur.NOEUDS)


def test_chaque_etape_est_un_sous_processus_du_meme_interpreteur() -> None:
    """Un modèle par processus : c'est la commande qui le garantit, pas une intention."""
    commande = orchestrateur._commande("voice", "bms-science-fr-20260917-rtmk", None, None, None)
    assert commande[1:3] == ["-m", "factory.cli"]
    assert commande[3:] == ["voice", "--run", "bms-science-fr-20260917-rtmk"]
    avec_style = orchestrateur._commande("render", "x-1", None, None, "cartes")
    assert avec_style[-2:] == ["--style", "cartes"]


def test_le_cout_est_calcule_et_porte_son_drapeau_d_estimation() -> None:
    """30 W de repli, 0,2516 €/kWh : le coût sort, et il se dit estimé."""
    economics = m.EconomicsConfig(
        tarif_kwh_eur=m.ValeurSourcee(valeur=0.25, source="tarif"),
        puissance_moyenne_w=m.ValeurSourcee(valeur=None, a_mesurer=True, defaut=30.0,
                                            note="ordre de grandeur, non mesuré"),
        cout_horaire_relecture_eur=m.ValeurSourcee(valeur=None, a_mesurer=True, note="Alek"),
    )
    energie, eur, estime = economics.cout_run(compute_min=180.0)
    assert energie == pytest.approx(0.09, abs=1e-6)  # 3 h × 30 W
    assert eur == pytest.approx(0.0225, abs=1e-6)
    assert estime


def test_une_valeur_de_repli_sans_note_est_refusee() -> None:
    """Une valeur inventée doit dire d'où elle vient, sinon elle n'entre pas."""
    with pytest.raises(ValidationError, match="valeur inventée"):
        m.ValeurSourcee(valeur=None, a_mesurer=True, defaut=30.0)


def test_le_bloc_publicite_porte_la_mention_et_le_subid() -> None:
    """Un produit configuré ⇒ « PUBLICITÉ » en tête du bloc, lien suivi, mention du réseau."""
    from factory.core import config as config_module

    cfg = config_module.charger(strict=False)
    channel = cfg.get_channel("bms-science-fr").model_copy(update={"products": ["exemple-affilie"]})
    langue = cfg.langue_de(channel)
    spec = m.VideoSpec(
        video_id="bms-science-fr-20260917-ts22", channel_id=channel.id, lang="fr",
        niche="science_pop", style="illustre",
        topic=m.Topic(sujet="Le sucre", angle="à définir par la recherche", source="manuel"),
        target_duration_s=648, cut_rhythm_target_s=5.85, seed=7,
        product_id="exemple-affilie", created_at="2026-09-17T08:00:00Z",
    )
    lignes, liens = M.bloc_affiliation(channel, cfg, langue, spec)
    assert lignes[0].startswith(langue.disclosure.overlay_generic.upper())
    assert langue.disclosure.pour_reseau(liens[0].network) in lignes[0]  # precheck 7-9
    assert liens and liens[0].subid_value == spec.video_id  # sub_id_format "{video_id}" (étape 27)
    assert liens[0].subid_param in lignes[1]  # le paramètre de suivi est bien dans l'URL
    assert any(langue.disclosure.pour_reseau(liens[0].network) in ligne for ligne in lignes)


def test_sans_produit_aucun_bloc_publicite() -> None:
    """Pas de produit, pas de mention : une divulgation sans promotion serait fausse."""
    from factory.core import config as config_module

    cfg = config_module.charger(strict=False)
    channel = cfg.get_channel("bms-science-fr")
    spec = m.VideoSpec(
        video_id="bms-science-fr-20260917-ts23", channel_id=channel.id, lang="fr",
        niche="science_pop", style="illustre",
        topic=m.Topic(sujet="Le sucre", angle="à définir par la recherche", source="manuel"),
        target_duration_s=648, cut_rhythm_target_s=5.85, seed=7,
        created_at="2026-09-17T08:00:00Z",
    )
    assert M.bloc_affiliation(channel, cfg, cfg.langue_de(channel), spec) == ([], [])


def test_la_mention_commerciale_ouvre_la_description() -> None:
    """CONFORMITE § 3 couche 3 prime sur l'ordre d'INTERFACES : la mention passe en tête."""
    blocs = m.BlocsDescription(
        disclosure="Vidéo produite avec l'assistance d'outils d'intelligence artificielle.",
        hook="Accroche.", affiliate=["PUBLICITÉ", "Produit : https://exemple.tld"],
        attribution=["Illustrations générées localement"],
    )
    description = M.composer_description(blocs)
    assert description.startswith("PUBLICITÉ")
    assert description.index("PUBLICITÉ") < description.index("intelligence artificielle")
    sans_produit = M.composer_description(m.BlocsDescription(disclosure="Divulgation.",
                                                             hook="Accroche."))
    assert sans_produit.startswith("Divulgation.")


def test_deux_chapitres_ne_portent_pas_le_meme_titre() -> None:
    """Un texte à l'écran réemployé ne doit pas produire deux chapitres homonymes."""
    script = _script(10)
    for segment in script.segments[1:]:
        segment.on_screen_text = "ARRIVEE A L'OBJECTIF"
    chapitres, _alertes = M.chapitres_depuis_timings(_timings(script, pas=60.0), script, 660.0)
    titres = [c.title.lower() for c in chapitres]
    assert len(titres) == len(set(titres)), titres
