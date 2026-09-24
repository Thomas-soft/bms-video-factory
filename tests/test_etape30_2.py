"""Étape 30.2 — moteur « whiteboard ».

Ce qui est vérifié ici est ce qui a cassé en exécutant : la translation des `<path>` de vtracer,
le plafond de chemins, l'ordre de dessin, et le fait qu'un remplissage reste solidaire de son
élément d'origine (sans quoi un anneau se remplit comme un disque).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from factory.core import config
from factory.styles import MOTEURS_PLANIFIES, STYLE_ENGINES, get_engine
from factory.styles.whiteboard import (
    ECHELONS_SIMPLIFICATION, PLAFOND_CHEMINS, PROMPT_STYLE, WhiteboardEngine,
    _boite, _longueur, _sous_chemins, _translater, ordonner, prompt_whiteboard, vectoriser,
)


def moteur(**params: object) -> WhiteboardEngine:
    cfg = config.charger(strict=False)
    style = cfg.styles["whiteboard"].model_copy(
        update={"params": {**cfg.styles["whiteboard"].params, **params}}
    )
    return WhiteboardEngine(style=style, racine=Path("."))


# -- prompt ---------------------------------------------------------------------------------

def test_le_prompt_de_style_ne_vient_pas_de_la_charte() -> None:
    """Le style whiteboard impose son propre prompt : la charte décrit des aplats de couleur."""
    prompt = prompt_whiteboard(None, "a human brain")
    assert prompt.startswith(PROMPT_STYLE)
    assert "a human brain" in prompt
    assert "no shading" in prompt and "no text" in prompt


def test_deux_chaines_donnent_le_meme_prompt_donc_la_meme_image() -> None:
    cfg = config.charger(strict=False)
    a = prompt_whiteboard(cfg.get_channel("bms-science-en"), "a gear")
    b = prompt_whiteboard(cfg.get_channel("bms-histoire-en"), "a gear")
    assert a == b


def test_la_rupture_change_le_cadrage_donc_la_cle_de_bibliotheque() -> None:
    assert prompt_whiteboard(None, "a gear") != prompt_whiteboard(None, "a gear", rupture=True)


# -- découpe et translation des chemins -----------------------------------------------------

def test_un_d_multiple_se_decoupe_en_un_contour_par_M() -> None:
    assert _sous_chemins("M0 0 C1 1 2 2 3 3 ZM10 10 C11 11 12 12 13 13 Z") == [
        "M0 0 C1 1 2 2 3 3 Z", "M10 10 C11 11 12 12 13 13 Z",
    ]


def test_la_translation_de_vtracer_est_rabattue_dans_les_coordonnees() -> None:
    """Sans ce rabattage, tous les contours d'une image se superposent à l'origine."""
    assert _translater("M0 0 C1 2 3 4 5 6 Z", 100, 50) == "M100 50 C101 52 103 54 105 56 Z"


def test_la_translation_ne_perd_pas_les_entiers() -> None:
    """`rstrip("0")` amputerait « 100 » en « 1 » sans le point décimal du format."""
    assert _translater("M0 0 Z", 100, 200) == "M100 200 Z"


def test_une_boite_est_lue_sur_des_paires_de_coordonnees() -> None:
    assert _boite("M10 20 C30 40 50 60 70 80 Z") == (10.0, 20.0, 70.0, 80.0)


def test_la_longueur_approchee_croit_avec_le_contour() -> None:
    court = _longueur("M0 0 C1 0 2 0 3 0 Z")
    long = _longueur("M0 0 C10 0 20 0 30 0 Z")
    assert long > court > 0


# -- ordre de dessin ------------------------------------------------------------------------

def test_les_gros_elements_se_dessinent_avant_les_details() -> None:
    gros = (0, "M10 700 C10 700 900 700 900 900 Z")       # tout en bas, mais énorme
    detail = (1, "M20 20 C20 20 30 20 30 30 Z")           # tout en haut, minuscule
    assert ordonner([detail, gros], 1000, 1000)[0] is gros


def test_a_taille_egale_la_main_descend_la_page_de_gauche_a_droite() -> None:
    hautgauche = (0, "M10 10 C10 10 400 10 400 400 Z")
    basdroite = (1, "M500 600 C500 600 900 600 900 990 Z")
    hautdroite = (2, "M500 10 C500 10 900 10 900 400 Z")
    ordre = ordonner([basdroite, hautdroite, hautgauche], 1000, 1000)
    assert [e[0] for e in ordre] == [0, 2, 1]


# -- vectorisation et plafond ---------------------------------------------------------------

def _damier(chemin: Path, cases: int, taille: int = 256) -> Path:
    """Une image au trait synthétique : `cases`² carrés noirs, donc autant de contours."""
    image = Image.new("RGB", (taille, taille), "white")
    dessin = ImageDraw.Draw(image)
    pas = taille / cases
    for i in range(cases):
        for j in range(cases):
            x, y = i * pas, j * pas
            dessin.rectangle([x + 1, y + 1, x + pas - 3, y + pas - 3], fill="black")
    image.save(chemin, "PNG")
    return chemin


def test_le_plafond_de_chemins_est_tenu_par_re_simplification(tmp_path: Path) -> None:
    """Une image trop riche descend l'échelle de simplification jusqu'à tenir le plafond."""
    png = _damier(tmp_path / "damier.png", cases=30, taille=600)
    trace = vectoriser(png, tmp_path / "damier.svg", plafond=120)
    assert len(trace.contours) <= 120
    assert trace.essais > 1, "l'image devait demander plus d'une passe"
    assert trace.reglage in ECHELONS_SIMPLIFICATION


def test_une_image_simple_tient_au_premier_echelon(tmp_path: Path) -> None:
    png = _damier(tmp_path / "petit.png", cases=3, taille=240)
    trace = vectoriser(png, tmp_path / "petit.svg")
    assert trace.essais == 1
    assert trace.echelon == 0
    assert 1 <= len(trace.contours) <= PLAFOND_CHEMINS


def test_les_contours_tiennent_dans_la_toile(tmp_path: Path) -> None:
    """La translation rabattue, aucun contour ne sort de l'image ni ne se colle à l'origine."""
    png = _damier(tmp_path / "toile.png", cases=4, taille=320)
    trace = vectoriser(png, tmp_path / "toile.svg")
    for contour in trace.contours:
        x0, y0, x1, y1 = _boite(contour)
        assert -2 <= x0 and -2 <= y0 and x1 <= trace.largeur + 2 and y1 <= trace.hauteur + 2
    # Deux contours distincts ne partagent pas le même coin : ils seraient superposés.
    coins = {(_boite(c)[0], _boite(c)[1]) for c in trace.contours}
    assert len(coins) > 1


def test_chaque_contour_appartient_a_un_et_un_seul_remplissage(tmp_path: Path) -> None:
    png = _damier(tmp_path / "groupes.png", cases=4, taille=320)
    trace = vectoriser(png, tmp_path / "groupes.svg")
    rangs = [r for groupe in trace.groupes for r in groupe["membres"]]
    assert sorted(rangs) == list(range(len(trace.contours)))


def test_la_boite_de_l_encre_est_plus_serree_que_la_toile(tmp_path: Path) -> None:
    """C'est sur elle qu'on cadre : la toile porte les marges blanches du générateur."""
    image = Image.new("RGB", (400, 400), "white")
    ImageDraw.Draw(image).rectangle([150, 150, 250, 250], outline="black", width=6)
    image.save(tmp_path / "marge.png", "PNG")
    trace = vectoriser(tmp_path / "marge.png", tmp_path / "marge.svg")
    x0, y0, x1, y1 = trace.boite
    assert x0 > 100 and y0 > 100 and x1 < 300 and y1 < 300


# -- moteur ---------------------------------------------------------------------------------

def test_le_moteur_est_au_registre_et_plus_planifie() -> None:
    assert STYLE_ENGINES["whiteboard"] is WhiteboardEngine
    assert "whiteboard" not in MOTEURS_PLANIFIES


def test_le_style_whiteboard_est_executable() -> None:
    cfg = config.charger(strict=False)
    moteur_resolu = get_engine(cfg.styles["whiteboard"], racine=Path("."))
    assert moteur_resolu.name == "whiteboard"
    assert moteur_resolu.backend == "revideo"


def test_les_reglages_viennent_de_la_configuration_jamais_d_une_constante() -> None:
    m = moteur(trace={"plafond_chemins": 42}, draw={"part_trace": 0.5},
               image={"resolution": "512x512"})
    assert m.plafond_chemins == 42
    assert m.part_trace == 0.5
    assert m.resolution == "512x512"


def test_la_police_manuscrite_est_une_police_ofl_du_depot() -> None:
    police = moteur().police_manuscrite
    assert police.fichier.name == "Caveat[wght].ttf"
    assert (Path(".") / "assets" / "fonts" / police.fichier.name).exists()


def test_les_deux_mains_sont_livrees_et_portent_leur_pointe() -> None:
    mains = moteur().mains()
    assert len(mains) == 2
    for main in mains:
        assert main["src"].startswith("data:image/png;base64,")
        assert 0 < main["tip"][0] < 0.5 and 0 < main["tip"][1] < 0.5


def test_une_main_absente_dit_comment_la_regenerer() -> None:
    m = moteur(draw={"mains": ["assets/charte/absente.png"]})
    with pytest.raises(FileNotFoundError, match="mains_whiteboard"):
        m.mains()


# -- props de scène -------------------------------------------------------------------------

def _plan(**surcharge: object):
    from factory.core.models import Shot
    base = {
        "id": "shot_07", "segment_id": "seg_02", "start_s": 10.0, "end_s": 14.0,
        "duration_s": 4.0, "visual_intent": "a gear turning",
        "asset_request": {"type": "image", "prompt_or_keywords": "a gear turning"},
        "seed": 4242,
    }
    return Shot.model_validate({**base, **surcharge})


def test_la_duree_de_trace_vaut_la_part_configuree_de_la_duree_du_plan() -> None:
    props = moteur().props_du_plan(_plan(), None, [], "", 0)
    assert props["draw_ratio"] == 0.80


def test_un_plan_sponsorise_porte_le_bandeau_publicite() -> None:
    m = moteur()
    m.texte_divulgation = "Publicité"
    props = m.props_du_plan(_plan(is_sponsor=True), None, [], "", 0)
    assert props["is_sponsor"] is True
    assert props["disclosure"] == "Publicité"
    assert m.props_du_plan(_plan(), None, [], "", 0)["disclosure"] is None


def test_deux_plans_voisins_ne_tiennent_pas_le_feutre_de_la_meme_facon() -> None:
    m = moteur()
    assert m.props_du_plan(_plan(), None, [], "", 4)["hand"] != \
        m.props_du_plan(_plan(), None, [], "", 5)["hand"]


def test_le_sur_titre_ne_double_pas_le_texte_a_l_ecran() -> None:
    m = moteur()
    plan = _plan(on_screen_text="Gears turn",
                 asset_request={"type": "image", "prompt_or_keywords": "a gear",
                                "reuse_ok": False})
    props = m.props_du_plan(plan, None, [], "Gears turn", 0)
    assert props["on_screen_text"] == "Gears turn"
    assert props["title"] == ""


def test_les_mots_du_plan_sont_recales_sur_son_debut() -> None:
    mots = [{"word": "gear", "start": 10.5, "end": 10.9},
            {"word": "hors", "start": 20.0, "end": 20.4}]
    dedans = moteur()._mots_du_plan(mots, _plan())
    assert [m["w"] for m in dedans] == ["gear"]
    assert dedans[0]["t"] == 0.5
