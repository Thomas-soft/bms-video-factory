"""Étape 15 — banc d'évaluation et portillon qualité.

Ces tests portent sur ce qui se teste sans vidéo : les fonctions de score, la lecture des
fichiers de sous-titres, l'arithmétique du barème et les règles de hook. La mesure elle-même
(PySceneDetect, ebur128, phash) est vérifiée par la calibration sur les deux runs de la phase 1,
consignée dans `docs/QC.md` — un test unitaire qui rejouerait un rendu de douze minutes n'aurait
pas sa place dans une suite qui doit rester rapide.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.core import config as config_module
from factory.core.models import QcConfig
from factory.eval import base, bench
from factory.eval.contexte import _avec_surcharges
from factory.eval.metrics import FAMILLES, coupes, hook, sous_titres, variete

RACINE = Path(__file__).resolve().parents[1]
FIXTURE = RACINE / "tests" / "fixtures" / "qc_cible.json"


# -- fonctions de score ---------------------------------------------------------------------

def test_score_cible_vaut_100_a_la_cible_et_0_au_bord():
    assert base.score_cible(5.85, 5.85, 0.15, 0.60) == 100.0
    assert base.score_cible(5.85 * 1.15, 5.85, 0.15, 0.60) == 100.0
    assert base.score_cible(5.85 * 1.60, 5.85, 0.15, 0.60) == 0.0
    assert base.score_cible(5.85 * 2.00, 5.85, 0.15, 0.60) == 0.0


def test_score_cible_est_symetrique():
    """Couper deux fois trop vite est puni autant que couper deux fois trop lentement.

    C'est ce qui empêche le banc de récompenser les coupes inutiles : sans symétrie, un montage
    qui hache gagnerait des points en s'éloignant de la cible du bon côté.
    """
    rapide = base.score_cible(5.85 * 0.70, 5.85, 0.15, 0.60)
    lent = base.score_cible(5.85 * 1.30, 5.85, 0.15, 0.60)
    assert rapide == pytest.approx(lent)


def test_scores_bornes():
    assert base.score_min(0.95, 0.90, 0.50) == 100.0
    assert base.score_min(0.50, 0.90, 0.50) == 0.0
    assert base.score_min(0.70, 0.90, 0.50) == pytest.approx(50.0)
    assert base.score_max(1, 2, 8) == 100.0
    assert base.score_max(8, 2, 8) == 0.0
    assert base.score_intervalle(-14.0, -15.0, -13.0, 4.0) == 100.0
    assert base.score_intervalle(-19.0, -15.0, -13.0, 4.0) == 0.0
    assert base.score_booleen(False) == 0.0


def test_contraste_wcag_extremes():
    blanc = base.luminance_relative(255, 255, 255)
    noir = base.luminance_relative(0, 0, 0)
    assert base.contraste_wcag(blanc, noir) == pytest.approx(21.0, abs=0.01)
    assert base.contraste_wcag(blanc, blanc) == pytest.approx(1.0)


def test_percentile():
    valeurs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert coupes._percentile(valeurs, 0.0) == 1.0
    assert coupes._percentile(valeurs, 0.5) == 3.0
    assert coupes._percentile(valeurs, 1.0) == 5.0


# -- barème ---------------------------------------------------------------------------------

def test_le_bareme_couvre_toutes_les_familles():
    """Une famille sans poids serait mesurée puis jetée sans que personne ne le voie."""
    cfg = config_module.charger(RACINE, strict=False)
    assert cfg.qc is not None
    attendus = {module.__name__.rsplit(".", 1)[-1] for module in FAMILLES}
    assert attendus <= set(cfg.qc.poids)


def test_fixture_ideale_au_moins_95():
    """Critère de l'étape 15 : une vidéo exactement aux cibles doit scorer ≥ 95."""
    resultat = bench.noter_fixture(FIXTURE, RACINE)
    assert resultat.score >= 95.0
    assert resultat.verdict == "PASS"
    assert resultat.raisons == []


def test_famille_sautee_quitte_le_denominateur():
    """Une cible `a_mesurer` ne doit ni monter ni descendre le score : elle en sort."""
    notee = base.Famille("coupes", poids=25)
    notee.mesures.append(base.Mesure("x", 1, "u", 1, "s", "o", score=60.0))
    sautee = base.Famille("variete", poids=10)
    sautee.mesures.append(base.Mesure("y", None, "u", None, "s", "o", score=None))
    score, combien = bench._score_global([notee, sautee])
    assert score == pytest.approx(60.0)
    assert combien == 1


def test_un_bloquant_en_echec_fait_echouer_malgre_un_score_haut():
    famille = base.Famille("audio", poids=15)
    famille.mesures.append(base.Mesure(
        "loudness", -30.0, "LUFS", -14.0, "s", "o", score=0.0, bloquant=True, statut="fail"
    ))
    famille.mesures.append(base.Mesure("true_peak", -2.0, "dBTP", -1.0, "s", "o", score=100.0))
    cfg = config_module.charger(RACINE, strict=False)
    raisons, verdict, etapes = bench._verdicts([famille], 99.0, cfg.qc, [])
    assert any("bloquant" in r for r in raisons)
    assert verdict in ("blocked", "regenerate")
    assert "assemble" in etapes


def test_surcharge_de_niche_fusionne_sans_remplacer():
    cfg = QcConfig.model_validate({
        "schema_version": "1.0",
        "poids": {"coupes": 25},
        "seuils": {"cut_rhythm": {"tolerance": 0.15, "plage": 0.60, "part_longue_max": 0.10}},
        "surcharges_par_niche": {
            "true_crime": {"seuils": {"cut_rhythm": {"part_longue_max": 0.20}}}
        },
    })
    surcharge = _avec_surcharges(cfg, "true_crime")
    assert surcharge.seuils["cut_rhythm"].part_longue_max == 0.20
    assert surcharge.seuils["cut_rhythm"].tolerance == 0.15  # non touché
    assert _avec_surcharges(cfg, "science_pop").seuils["cut_rhythm"].part_longue_max == 0.10


# -- sous-titres ----------------------------------------------------------------------------

ASS = """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.80,BMS,,0,0,0,,{\\k20}Un {\\k30}matin
Dialogue: 0,0:00:02.00,0:00:04.00,BMS,,0,0,0,,deux lignes\\Nici la seconde
"""


def test_lecture_ass_saute_les_six_champs_avant_le_texte(tmp_path: Path):
    """Régression : « BMS,,0,0,0,, » comptait pour du texte et allongeait chaque ligne de 12."""
    chemin = tmp_path / "s.ass"
    chemin.write_text(ASS, encoding="utf-8")
    evenements, lignes = sous_titres._lire_ass(chemin)
    assert evenements == [(0.0, 1.8), (2.0, 4.0)]
    assert lignes == ["Un matin", "deux lignes", "ici la seconde"]
    assert max(len(l) for l in lignes) == len("ici la seconde")


def test_couverture_compte_les_secondes_parlees_pas_les_mots():
    mots = [{"start_s": 0.0, "end_s": 1.0}, {"start_s": 10.0, "end_s": 11.0}]
    assert sous_titres._couverture(mots, [(0.0, 1.0)]) == pytest.approx(0.5, abs=0.05)
    assert sous_titres._couverture(mots, [(0.0, 11.0)]) == pytest.approx(1.0)
    assert sous_titres._couverture(mots, []) == 0.0


# -- hook -----------------------------------------------------------------------------------

LEXIQUE_FR = {
    "deuxieme_personne": ["vous", "tu"],
    "salutations": ["bonjour à tous", "dans cette vidéo"],
    "negation": ["jamais", "aucun"],
}


def test_regles_de_hook_mecaniques():
    assert hook._sans_deuxieme_personne("Un matin de novembre, des mains soulèvent", LEXIQUE_FR, 15)
    assert not hook._sans_deuxieme_personne("Vous croyez tout savoir", LEXIQUE_FR, 15)
    assert hook._avec_question("Et si c'était faux ?", LEXIQUE_FR, 15)
    assert hook._sans_salutation("Un matin de novembre", LEXIQUE_FR, 15)
    assert not hook._sans_salutation("Bonjour à tous et bienvenue", LEXIQUE_FR, 15)
    assert hook._avec_negation("On ne le fait jamais", LEXIQUE_FR, 15)
    assert hook._avec_chiffre("En 1947, trois hommes", LEXIQUE_FR, 15)


def test_regle_non_verifiable_rend_none_et_ne_compte_pas():
    """Une règle sans lexique n'est ni tenue ni violée : elle sort du compte."""
    assert hook._sans_deuxieme_personne("peu importe", {}, 15) is None
    assert hook._avec_negation("peu importe", {}, 15) is None


# -- variété --------------------------------------------------------------------------------

class _FauxHash:
    """Empreinte de test : la distance est la valeur absolue de l'écart."""

    def __init__(self, valeur: int) -> None:
        self.valeur = valeur

    def __sub__(self, autre: "_FauxHash") -> int:
        return abs(self.valeur - autre.valeur)


def test_comptage_des_images_distinctes():
    empreintes = [_FauxHash(v) for v in (0, 1, 0, 40, 41, 80)]
    assert variete._compter_distinctes(empreintes, 8) == 3
    assert variete._compter_distinctes(empreintes, 100) == 1
