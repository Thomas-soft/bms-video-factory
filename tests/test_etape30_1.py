"""Étape 30.1 — moteur « motion design ».

Aucun test ne lance Chromium : ce qui est éprouvé ici, c'est ce qui **décide du contenu d'un
plan publié** — la scène choisie, les propriétés qui lui sont passées, la variété, et le refus
d'un chiffre qui ne figure pas dans la narration. Le rendu lui-même est mesuré par l'exécution,
pas par un test (`CLAUDE.md` § 5).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.core.models import AssetRequest, Shot, Style
from factory.styles.motion import MotionEngine


def moteur(**params: object) -> MotionEngine:
    """Un moteur nu, sans run ni journal ; les tests ne touchent ni disque ni réseau."""
    style = Style(
        schema_version="1.0", id="motion", engine="motion_design", backend="revideo",
        statut="retenu_v1", templates=["kinetic"],
        params={"scene": {"marge_px": 96}, "revideo": {"lot": 20, "workers": 1}, **params},
    )
    return MotionEngine(style=style, racine=Path("."))


def plan(**surcharges: object) -> Shot:
    """Un plan recevable par défaut ; chaque test ne change que ce qu'il éprouve."""
    champs: dict[str, object] = dict(
        id="shot_07", segment_id="seg_03", start_s=10.0, end_s=15.0, duration_s=5.0,
        visual_intent="A diagram of two galaxies drifting apart",
        on_screen_text=None,
        asset_request=AssetRequest(type="card", prompt_or_keywords="plein", reuse_ok=False),
        motion="static", transition_in="cut", is_sponsor=False, seed=42,
    )
    champs.update(surcharges)
    return Shot(**champs)  # type: ignore[arg-type]


# -- choix de scène ----------------------------------------------------------------------


def test_les_regles_ne_tranchent_que_ce_qu_elles_savent_trancher() -> None:
    """Une règle de mots-clés n'a rien à dire sur le contenu visuel d'un plan.

    C'est elle qui produisait 58 plans de texte pur sur 114 — « des textes et un peu du motion
    design très léger » (Thomas, 19/09). Un plan sans chiffre ni rupture est désormais rendu au
    metteur en scène, qui choisit un **dispositif**, pas une mise en page.
    """
    m = moteur()
    assert m.scene_par_regle(plan(), "point", "There are three ways to keep it.", False) is None
    assert m.scene_par_regle(plan(), "point", "He said it changes everything.", False) is None
    assert m.scene_par_regle(plan(end_s=12.0, duration_s=2.0), "point", "anything", False) is None


def test_une_rupture_courte_reste_un_volet_une_longue_est_rendue_au_metteur_en_scene() -> None:
    """Au-delà de 3 s, un volet plein cadre est un plan mort : le dispositif se choisit."""
    from factory.core.models import Interrupt

    rupture = Interrupt(type="question", at_s_relative=2.0)
    m = moteur()
    assert m.scene_par_regle(
        plan(duration_s=2.4, end_s=12.4, interrupt=rupture), "point", "", False,
    ) == "transition_stinger"
    assert m.scene_par_regle(
        plan(duration_s=6.0, end_s=16.0, interrupt=rupture), "point", "", False,
    ) is None


def test_la_rotation_de_remplissage_ne_contient_que_des_scenes_construites() -> None:
    """Quand rien n'a tranché, le plan retombe sur une scène qui **fabrique** quelque chose."""
    from factory.styles import motion

    assert set(motion.ROTATION) <= set(motion.SCENES_CONSTRUITES)
    assert set(motion.ROTATION_COURTE) - set(motion.SCENES_CONSTRUITES) == {"kinetic_text"}


def test_un_texte_incruste_chiffre_donne_un_compteur() -> None:
    """« 93 BILLION LIGHT YEARS » est un chiffre à animer, pas un titre.

    Le seuil est en **mots** : un seuil en caractères refusait ce cas, et le moteur n'a produit
    aucun compteur sur les 114 plans du premier run.
    """
    assert moteur().scene_par_regle(
        plan(on_screen_text="93 BILLION LIGHT YEARS"), "point", "", False
    ) == "stat_counter"


def test_un_texte_incruste_sans_chiffre_n_est_pas_un_compteur() -> None:
    assert moteur().scene_par_regle(
        plan(on_screen_text="THE UNIVERSE IS OLD"), "point", "", False
    ) != "stat_counter"


def test_un_graphique_verifie_est_tranche_par_la_regle() -> None:
    """Le seul contenu qu'une règle décide seule : celui dont les chiffres sont déjà vérifiés."""
    assert moteur().scene_par_regle(plan(), "point", "some narration", True) == "chart"


# -- propriétés --------------------------------------------------------------------------


MOTS = [
    {"w": "The", "start_s": 10.0, "end_s": 10.2, "seg": "seg_03"},
    {"w": "universe", "start_s": 10.2, "end_s": 10.8, "seg": "seg_03"},
    {"w": "expands.", "start_s": 10.8, "end_s": 11.4, "seg": "seg_03"},
    {"w": "Light", "start_s": 12.0, "end_s": 12.4, "seg": "seg_03"},
    {"w": "races", "start_s": 12.4, "end_s": 12.9, "seg": "seg_03"},
    {"w": "away.", "start_s": 12.9, "end_s": 13.4, "seg": "seg_03"},
    {"w": "Hors", "start_s": 16.0, "end_s": 16.4, "seg": "seg_04"},
]


def test_les_mots_du_plan_sont_relatifs_a_son_debut_et_s_arretent_a_sa_fin() -> None:
    mots = MotionEngine.mots_du_plan(MOTS, plan())
    assert [m["w"] for m in mots] == ["The", "universe", "expands.", "Light", "races", "away."]
    assert mots[0]["t"] == 0.0
    assert mots[-1]["e"] == pytest.approx(3.4)


def test_le_texte_d_un_plan_ne_reprend_pas_la_narration_du_segment() -> None:
    """Le texte posé à l'écran est **ce qui est dit pendant le plan**, pas le segment entier."""
    assert MotionEngine.texte_du_plan(MOTS, plan()) == "The universe expands. Light races away."


def test_le_sur_titre_ne_redit_pas_l_en_tete_de_la_scene() -> None:
    props = moteur().props_du_plan(
        plan(on_screen_text="UNIVERSE IS OLD"), "title_card", "Some words.", [], None,
        titre_segment="UNIVERSE IS OLD",
    )
    assert props["title"] == ""
    assert props["heading"] == "UNIVERSE IS OLD"


def test_le_sur_titre_n_est_jamais_le_role_du_segment() -> None:
    """« hook », « point » sont du vocabulaire interne : ils n'ont rien à faire à l'écran."""
    props = moteur().props_du_plan(plan(), "list_reveal", "One. Two. Three.", [], None)
    assert props["title"] not in {"hook", "point", "rupture", "conclusion", "cta"}


def test_le_compteur_separe_le_nombre_de_son_libelle() -> None:
    props = moteur().props_du_plan(
        plan(on_screen_text="93 BILLION LIGHT YEARS"), "stat_counter", "Big.", [], None,
    )
    assert props["value"] == 93.0
    assert props["label"] == "BILLION LIGHT YEARS"


def test_le_bandeau_de_divulgation_n_est_pose_que_sur_un_plan_sponsorise() -> None:
    m = moteur()
    m.texte_divulgation = "Paid promotion"
    assert m.props_du_plan(plan(), "title_card", "x", [], None)["disclosure"] is None
    sponsorise = m.props_du_plan(plan(is_sponsor=True), "title_card", "x", [], None)
    assert sponsorise["disclosure"] == "Paid promotion"
    assert sponsorise["is_sponsor"] is True


# -- vérification des chiffres -----------------------------------------------------------


def test_une_valeur_absente_de_la_narration_est_refusee() -> None:
    """Un graphique n'affirme que ce que le script dit. Le reste serait un chiffre inventé."""
    assert MotionEngine._valeur_dans_le_texte(58, "Recall falls to 58 percent after a day.")
    assert not MotionEngine._valeur_dans_le_texte(61, "Recall falls to 58 percent after a day.")


def test_les_chiffres_sont_lus_avec_leur_unite() -> None:
    assert MotionEngine.chiffres("up 42% in 3 years") == [(42.0, "%"), (3.0, "")]


# -- icônes ------------------------------------------------------------------------------


def test_une_icone_est_toujours_choisie_dans_le_jeu_extrait() -> None:
    from factory.styles import motion

    assert motion.MotionEngine.icone_pour("about the brain and memory", 0) == "brain"
    assert motion.MotionEngine.icone_pour("aucun mot connu ici", 7) in motion.ICONES


def test_un_pronom_ne_signe_pas_une_citation() -> None:
    """« He said gravity changes space geometry » n'est pas signé « He »."""
    m = moteur()
    sans = m.props_du_plan(plan(), "quote", "He said gravity changes space geometry.", [], None)
    assert sans["author"] == ""
    avec = m.props_du_plan(
        plan(), "quote", "Edwin Hubble said the universe expands.", [], None,
    )
    assert avec["author"] == "Edwin Hubble"


# -- mise en scène : ce que le metteur en scène a le droit de rendre ----------------------


def test_un_dispositif_sans_ses_pieces_est_refuse() -> None:
    """`assemble` sans pièces n'est pas un assemblage : le plan part sur une scène sans étiquette.

    Le metteur en scène rend **une forme unique** — `title`, `items`, `number` — parce qu'un 9B
    quantifié s'arrête au premier champ facultatif : mesuré le 19/09, **0 dispositif paramétré
    sur 10** avec un schéma à champs optionnels.
    """
    m = moteur()
    assert m._valider_dispositif(
        {"scene": "assemble", "title": "A galaxy", "items": ["Gas"], "number": 0}, "x", "y",
    ) is None
    retenu = m._valider_dispositif(
        {"scene": "assemble", "title": "A galaxy", "items": ["Gas", "Dust", "Stars"],
         "number": 0}, "x", "y",
    )
    assert retenu == {"scene": "assemble", "parts": ["Gas", "Dust", "Stars"],
                      "heading": "A galaxy"}


def test_un_rapport_d_echelle_absent_du_texte_est_refuse() -> None:
    """Un chiffre que le script ne dit pas ne s'affiche pas — même en gros, même joli."""
    m = moteur()
    dit = "Betelgeuse is about 700 times wider than the Sun."
    forme = {"scene": "echelle", "title": "size", "items": ["The Sun", "Betelgeuse"]}
    assert m._valider_dispositif({**forme, "number": 700}, dit, "") == {
        "scene": "echelle", "small": "The Sun", "big": "Betelgeuse", "ratio": 700.0,
    }
    assert m._valider_dispositif({**forme, "number": 900}, dit, "") is None


def test_un_pourcentage_invente_est_refuse() -> None:
    m = moteur()
    dit = "Only 5% of the universe is ordinary matter."
    forme = {"scene": "quantite", "title": "ordinary matter", "items": []}
    assert m._valider_dispositif({**forme, "number": 5}, dit, "")
    assert m._valider_dispositif({**forme, "number": 40}, dit, "") is None


def test_une_scene_inconnue_ne_passe_pas() -> None:
    assert moteur()._valider_dispositif(
        {"scene": "explosion", "title": "x", "items": ["a", "b"], "number": 0}, "x", "y",
    ) is None


def test_un_plan_joue_n_a_besoin_d_aucune_etiquette() -> None:
    """`tete_parlante`, `duo` et `personnage` se jouent avec la voix : ils ne peuvent pas échouer."""
    m = moteur()
    for scene, cle in (("tete_parlante", "who"), ("duo", "label"), ("personnage", "label")):
        retenu = m._valider_dispositif(
            {"scene": scene, "title": "A star", "items": [], "number": 0}, "x", "y",
        )
        assert retenu == {"scene": scene, cle: "A star"}


def test_le_repli_decoupe_ce_qui_est_dit_en_groupes_courts() -> None:
    """Sans dispositif, une pièce de schéma porte des mots prononcés, jamais une phrase."""
    groupes = MotionEngine._groupes_de_mots(
        "A star burns, then the light crosses space and we see the past.", 3,
    )
    assert len(groupes) == 3
    assert all(len(g.split()) <= 3 for g in groupes)
