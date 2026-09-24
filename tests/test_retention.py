"""Étape 16 — hook, boucles ouvertes, ruptures de rythme, densité d'information.

Ce que ces tests couvrent : les **règles**, c'est-à-dire tout ce qui se décide sans modèle.
Ce qu'ils ne couvrent pas, et qui est dit ici plutôt que tu : le duel entre deux accroches,
le juge de cohérence de boucle et le juge de densité passent par `llm.generate_json` et ne
sont pas rejoués en test — un 9B quantifié n'est pas déterministe et une suite de tests qui
charge 6,6 Go de poids n'est plus une suite de tests. Leur **absence** est testée à la place :
un juge indisponible laisse `coherente = None`, jamais `True`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.core.models import (
    Hook,
    Interrupt,
    Script,
    ScriptSegment,
    SignatureEditoriale,
)
from factory.retention import density, hooks, interrupts, loops, patterns, verify

FIXTURE = Path(__file__).parent / "fixtures" / "patterns_test.yaml"


@pytest.fixture()
def patrons(tmp_path: Path) -> patterns.Patterns:
    """Charge la table réduite des tests via le mécanisme de production."""
    dossier = tmp_path / "factory" / "retention"
    dossier.mkdir(parents=True)
    (dossier / "patterns_en.yaml").write_text(FIXTURE.read_text(encoding="utf-8"),
                                              encoding="utf-8")
    patterns.charger.cache_clear()
    table = patterns.charger("en", tmp_path)
    patterns.charger.cache_clear()
    return table


def _script(segments: list[tuple[str, str, str]], hook_texte: str = "What if gravity was wrong?",
            hook_type: str = "question_contrarienne",
            ruptures: dict[str, str] | None = None) -> Script:
    """Script minimal : `(role, open_loop, narration)` par segment, hook compris.

    L'objet est monté par `model_construct`, **sans** le validateur de `Script`. Ce n'est pas
    un contournement : le validateur vérifie la structure (deux boucles plantées, autant de
    paiements que de promesses), déjà couverte par `tests/test_models.py`, et il refuserait
    justement les scripts mal formés que ces tests-ci doivent donner à lire à `verify`. Ce qui
    est testé ici est ce que le validateur **ne voit pas** : le texte.
    """
    ruptures = ruptures or {}
    liste = [ScriptSegment(id="seg_00", role="hook", narration=hook_texte,
                           visual_intent="Diagram of an orbit.", open_loop="plant")]
    for index, (role, boucle, texte) in enumerate(segments, start=1):
        identifiant = f"seg_{index:02d}"
        liste.append(ScriptSegment(
            id=identifiant, role=role, narration=texte, visual_intent="Diagram of a thing.",
            open_loop=boucle,
            interrupt=(Interrupt(type=ruptures[identifiant], at_s_relative=5.0)
                       if identifiant in ruptures else None),
        ))
    mots = sum(s.word_count for s in liste)
    return Script.model_construct(
        schema_version="1.0", lang="en", hook=Hook(type=hook_type, text=hook_texte),
        segments=liste, editorial_signature=SignatureEditoriale(
            angle="comparaison_chiffree", elements_proprietaires=["mesure maison"]),
        music_mood=None, word_count=mots,
        estimated_duration_s=round(mots / (135 / 60), 1), disclosure_lines=None)


# --------------------------------------------------------------------------------------
# 1 à 4 — règles de hook : bons et mauvais exemples
# --------------------------------------------------------------------------------------

def test_hook_conforme_obtient_la_note_pleine(patrons: patterns.Patterns) -> None:
    """Une question contrarienne, dans la fourchette de longueur, sans formule proscrite."""
    texte = ("What if the thing you were told about the deep ocean turned out to be exactly "
             "backwards, and the proof has been sitting in plain sight?")
    candidat = hooks.noter(texte, "question_contrarienne", 36, patrons, plancher_mots=22)
    assert candidat.infractions == []
    assert candidat.score == 100.0
    assert candidat.acceptable


def test_hook_sans_element_cle_est_refuse(patrons: patterns.Patterns) -> None:
    """Un hook de type `question_contrarienne` qui ne pose aucune question tombe sous la barre."""
    texte = ("The deep ocean holds more water than every lake on the surface combined, and it "
             "stays dark all the way down to the floor.")
    candidat = hooks.noter(texte, "question_contrarienne", 36, patrons, plancher_mots=22)
    assert any("élément clé" in i for i in candidat.infractions)
    assert candidat.score == pytest.approx(100.0 - hooks.PENALITE_ELEMENT_ABSENT)
    assert not candidat.acceptable


def test_hook_trop_long_est_penalise_a_proportion(patrons: patterns.Patterns) -> None:
    """Le dépassement coûte par mot : dix mots de trop, trente points."""
    base = "What if this were false? " + " ".join(["word"] * 40)
    candidat = hooks.noter(base, "question_contrarienne", 35, patrons)
    trop = candidat.mots - 35
    assert trop > 0
    assert candidat.score == pytest.approx(max(0.0, 100.0 - trop * hooks.PENALITE_MOT_EN_TROP))
    assert any("plafond" in i for i in candidat.infractions)


def test_hook_trop_court_est_penalise_aussi(patrons: patterns.Patterns) -> None:
    """Plafonner seul donnait 100 à un hook de deux mots : le plancher p25 existe pour ça."""
    candidat = hooks.noter("What if?", "question_contrarienne", 36, patrons, plancher_mots=22)
    assert any("plancher" in i for i in candidat.infractions)
    assert candidat.score < 100.0


def test_in_medias_res_refuse_la_deuxieme_personne(patrons: patterns.Patterns) -> None:
    """La part mécanique du type : ni `you` ni question dans les quinze premiers mots."""
    bon = hooks.noter("Lying in the middle of a plain in modern Iran is a forgotten city.",
                      "in_medias_res", 36, patrons)
    mauvais = hooks.noter("You are standing in the middle of a plain in modern Iran today.",
                          "in_medias_res", 36, patrons)
    assert bon.infractions == []
    assert any("élément clé" in i for i in mauvais.infractions)


# --------------------------------------------------------------------------------------
# 5 — formulations proscrites
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("texte, attendu", [
    ("In this video we look at the deep ocean.", ["in this video"]),
    ("Hey guys, welcome back to the channel.", ["hey guys", "welcome back"]),
    ("Don’t forget to subscribe before we begin.", ["don't forget to subscribe",
                                                    "before we begin"]),
    ("The deep ocean holds more water than every lake.", []),
])
def test_formulations_proscrites_sont_detectees(
    patrons: patterns.Patterns, texte: str, attendu: list[str],
) -> None:
    """La détection ignore la casse et l'apostrophe typographique, que le modèle écrit aussi."""
    assert patrons.proscrites_trouvees(texte) == attendu


def test_une_formulation_proscrite_coute_quarante_points(patrons: patterns.Patterns) -> None:
    candidat = hooks.noter("What if, in this video, everything changed?",
                           "question_contrarienne", 36, patrons)
    assert any("proscrite" in i for i in candidat.infractions)
    assert candidat.score <= 100.0 - hooks.PENALITE_PROSCRITE


# --------------------------------------------------------------------------------------
# 6 à 8 — boucles ouvertes : plantation et paiement
# --------------------------------------------------------------------------------------

def test_boucle_plantee_et_payee_est_reconnue(patrons: patterns.Patterns) -> None:
    """Deux promesses, deux paiements : chaque promesse est appariée au premier qui la suit."""
    script = _script([
        ("contexte", "plant", "The floor is not flat. Stick around: the reason is stranger "
                              "than the shape."),
        ("point", "payoff", "Here is the answer: the crust itself is bending."),
        ("point", "none", "Pressure rises with depth in a straight line."),
        ("point", "payoff", "As I promised, the bending explains the ridges too."),
        ("conclusion", "none", "That is what the floor hides."),
    ], hook_texte="What if the sea floor was not flat? Stick around.")
    boucles = loops.apparier(script, patrons)
    assert [b.plant_id for b in boucles] == ["seg_00", "seg_01"]
    assert [b.payoff_id for b in boucles] == ["seg_02", "seg_04"]
    boucle = boucles[1]
    assert boucle.marqueurs_plant == ["stick around"]
    assert boucle.marqueurs_payoff == ["as i promised"]
    assert boucle.payee
    assert loops.resume(boucles) == (2, 2)


def test_etiquette_payoff_sans_marqueur_ne_compte_pas(patrons: patterns.Patterns) -> None:
    """Le défaut que l'étape 15 ne voyait pas : la boucle existe dans le JSON, pas dans le texte."""
    script = _script([
        ("contexte", "plant", "The floor is not flat. Stick around: the reason is stranger."),
        ("point", "payoff", "Pressure rises with depth in a straight line."),
        ("conclusion", "none", "That is what the floor hides."),
    ])
    boucle = next(b for b in loops.apparier(script, patrons) if b.plant_id == "seg_01")
    assert boucle.plantee
    assert boucle.marqueurs_payoff == []
    assert not boucle.payee


def test_payoff_place_avant_son_plant_ne_le_paie_pas(patrons: patterns.Patterns) -> None:
    """L'ordre des segments fait foi, comme au banc."""
    script = _script([
        ("point", "payoff", "As I promised, here is the reason."),
        ("contexte", "plant", "Stick around: the reason is stranger than the shape."),
        ("conclusion", "none", "That is what the floor hides."),
    ])
    boucle = next(b for b in loops.apparier(script, patrons) if b.plant_id == "seg_02")
    assert boucle.payoff_id is None
    assert not boucle.payee


def test_juge_indisponible_laisse_la_boucle_non_jugee(
    patrons: patterns.Patterns, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un juge qui échoue ne valide rien : `coherente` reste `None`, jamais `True`."""
    script = _script([
        ("contexte", "plant", "Stick around: the reason is stranger than the shape."),
        ("point", "payoff", "As I promised, here is the reason."),
        ("conclusion", "none", "That is what the floor hides."),
    ])
    def _echoue(*_args, **_kwargs):
        raise RuntimeError("poids GGUF absents")
    monkeypatch.setattr("factory.retention.loops.llm.generate_json", _echoue)
    boucles = loops.juger(script, loops.apparier(script, patrons))
    assert all(b.coherente is None for b in boucles)
    assert all("juge indisponible" in b.motif for b in boucles if b.payoff_id)


def test_planification_des_boucles_respecte_les_roles() -> None:
    """Deux promesses en tête, deux paiements avant la conclusion, jamais sur un rôle réservé."""
    roles = ["hook", "contexte", "point", "point", "point", "point", "cta", "conclusion"]
    plan = loops.planifier(roles, minimum=2)
    assert plan[0] == "plant" and plan[1] == "plant"
    assert plan.count("payoff") == 2
    for index, role in enumerate(roles):
        if role in loops.ROLES_RESERVES:
            assert plan[index] == "none"
    assert max(i for i, b in enumerate(plan) if b == "payoff") \
        > max(i for i, b in enumerate(plan) if b == "plant")


# --------------------------------------------------------------------------------------
# 9 à 11 — ruptures de rythme
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("rythme, attendu", [
    (5.85, 23.4),   # science_pop : 4 × 5,85, dans la fourchette
    (4.5, 20.0),    # histoire_doc : 18 s, remonté au plancher
    (15.7, 45.0),   # true_crime : 62,8 s, ramené au plafond
])
def test_cadence_est_bornee_entre_vingt_et_quarante_cinq(rythme: float, attendu: float) -> None:
    assert interrupts.intervalle_s(rythme) == pytest.approx(attendu)


def test_une_rupture_par_tranche_et_une_seule_par_segment() -> None:
    """Douze segments de 30 s, cadence 25 s : une rupture par segment au plus, pas deux."""
    durees = [30.0] * 12
    roles = ["hook"] + ["point"] * 10 + ["conclusion"]
    plan = interrupts.planifier(durees, roles, 25.0, seed=7)
    assert plan.n >= 8
    assert all(0 <= (r.at_s_relative if r else 0) <= 30.0 for r in plan.par_segment)
    assert plan.par_segment[0] is None          # le hook n'en porte jamais
    assert plan.par_segment[-1] is None         # la conclusion non plus
    assert plan.ecart_max_s is not None and plan.ecart_max_s <= 25.0 * 2


def test_ecart_de_rupture_ignore_la_conclusion_que_le_planificateur_refuse(
        patrons: patterns.Patterns) -> None:
    """`interrupts.py` refuse de poser une rupture sur une `conclusion` ; `verify` ne doit donc
    pas compter cette queue comme un écart, sans quoi l'infraction est **incorrigible** et les
    trois régénérations y passent (mesuré sur `avwf` le 18/09/2026 : 46 s d'écart pour une
    conclusion de 21 s)."""
    corps = [("point", "none", "The figure is forty two units. " * 12) for _ in range(6)]
    script = _script([*corps, ("conclusion", "none", "That is the whole story here. " * 12)],
                     ruptures={f"seg_{i:02d}": "chiffre" for i in range(1, 7)})
    rapport = _verifier(script, patrons, boucles_minimum=0, duree_cible_s=600.0)
    codes = {i.code for i in rapport.infractions}
    assert "rupture_trop_espacee" not in codes, [str(i) for i in rapport.infractions]


def test_rupture_trop_espacee_nomme_le_segment_trop_long(
        patrons: patterns.Patterns) -> None:
    """Un segment ne porte qu'une rupture : un écart trop large vient d'un segment plus long
    que la cadence. L'infraction doit le **nommer**, sinon la réparation n'a rien à réécrire
    et les trois essais se perdent (mesuré sur `avwf`, 18/09/2026 : `seg_25`, 39,4 s)."""
    long = ("The measured value is forty two units per second in this region. " * 20)
    script = _script(
        [("point", "none", "A short fact of twelve units here. " * 3),
         ("point", "none", long),
         ("point", "none", "Another short fact of nine units. " * 3)],
        ruptures={"seg_01": "chiffre", "seg_02": "question", "seg_03": "silence"})
    rapport = _verifier(script, patrons, boucles_minimum=0, duree_cible_s=600.0)
    ruptures = [i for i in rapport.infractions if i.code == "rupture_trop_espacee"]
    assert ruptures, [str(i) for i in rapport.infractions]
    assert "seg_02" in ruptures[0].segments
    assert ruptures[0].consigne, "sans consigne, la réparation ne sait pas quoi faire"


def test_les_types_de_rupture_ne_se_repetent_pas_dos_a_dos() -> None:
    plan = interrupts.planifier([40.0] * 10, ["point"] * 10, 30.0, seed=3)
    poses = [r.type for r in plan.par_segment if r is not None]
    assert len(poses) >= 4
    assert all(a != b for a, b in zip(poses, poses[1:]))
    assert set(poses) <= set(interrupts.TYPES)


def test_planification_seedee_est_rejouable() -> None:
    a = interrupts.planifier([40.0] * 8, ["point"] * 8, 30.0, seed=11)
    b = interrupts.planifier([40.0] * 8, ["point"] * 8, 30.0, seed=11)
    assert [None if r is None else r.type for r in a.par_segment] == \
           [None if r is None else r.type for r in b.par_segment]


# --------------------------------------------------------------------------------------
# 12 à 14 — densité par règles
# --------------------------------------------------------------------------------------

def test_densite_compte_les_categories_attendues() -> None:
    texte = ("According to researchers at MIT, the crust bends by twelve centimetres a year. "
             "In 1977 the first measurement put it at half that, which is twice as slow as "
             "the plates above it.")
    par_categorie, total, pondere, _ = density.compter(texte)
    assert par_categorie.get("attribution", 0) >= 1
    assert par_categorie.get("quantite_unite", 0) >= 1
    assert par_categorie.get("date_periode", 0) >= 1
    assert par_categorie.get("comparatif", 0) >= 1
    assert total >= 4
    assert pondere > total   # l'attribution pèse trois, pas un


def test_un_meme_empan_nest_compte_quune_fois() -> None:
    """« 1977 » est une date, pas une date **et** un nombre nu."""
    par_categorie, total, _, _ = density.compter("The survey of 1977 changed everything.")
    assert par_categorie.get("date_periode", 0) == 1
    assert par_categorie.get("nombre_nu", 0) == 0
    assert total == 1


def test_les_nombres_outils_ne_comptent_pas() -> None:
    """« one of the » n'est pas une information : sans ce garde-fou, « one » pèse un dixième."""
    _, avec, _, _ = density.compter("One of the plates is moving.")
    _, sans, _, _ = density.compter("Four plates are moving.")
    assert avec == 0
    assert sans >= 1


def test_la_majuscule_de_debut_de_phrase_nest_pas_une_entite() -> None:
    _, total, _, _ = density.compter("Plates move. Water covers them.")
    assert total == 0


def test_densite_par_minute_suit_le_debit_de_la_niche() -> None:
    texte = " ".join(["In 1977 the crust moved twelve centimetres."] * 10)
    comptage = density.mesurer([texte], mots_par_minute=120.0)
    assert comptage.mots == 70
    assert comptage.duree_min == pytest.approx(70 / 120)
    assert comptage.faits_par_minute == pytest.approx(
        comptage.total / (70 / 120), rel=1e-3)


def test_segments_a_enrichir_designe_les_plus_maigres() -> None:
    script = _script([
        ("contexte", "none", "In 1977 the crust moved twelve centimetres according to NASA."),
        ("point", "none", "It is a thing that happens sometimes in a way people notice."),
        ("point", "none", "Another vague statement with nothing anyone could ever check."),
        ("conclusion", "none", "That is what the floor hides."),
    ])
    maigres = density.segments_a_enrichir(script, n=2)
    assert "seg_02" in maigres and "seg_03" in maigres
    assert "seg_01" not in maigres


# --------------------------------------------------------------------------------------
# 15 à 17 — vérification complète
# --------------------------------------------------------------------------------------

def _verifier(script: Script, patrons: patterns.Patterns, **surcharges):
    defauts = dict(niche="science_pop", lang="en", mots_par_minute=135.0,
                   plafond_hook_mots=36, plancher_hook_mots=22, boucles_minimum=2,
                   cut_rhythm_target_s=5.85, duree_cible_s=60.0, tolerance_duree=0.15,
                   patterns=patrons, densite_cible=None, juge_boucles=False)
    defauts.update(surcharges)
    return verify.verifier(script, **defauts)


def test_verify_nomme_les_segments_a_reecrire(patrons: patterns.Patterns) -> None:
    script = _script([
        ("contexte", "plant", "In this video the floor is not flat."),
        ("point", "none", "Pressure rises with depth."),
        ("point", "payoff", "Pressure keeps rising."),
        ("conclusion", "none", "That is what the floor hides."),
    ], ruptures={"seg_02": "question"})
    rapport = _verifier(script, patrons)
    codes = {i.code for i in rapport.infractions}
    assert "formulation_proscrite" in codes
    assert "boucle_non_plantee" in codes
    assert "seg_01" in rapport.segments_a_reecrire()
    assert not rapport.conforme
    assert "in this video" in rapport.consignes()


def test_verify_refuse_un_texte_a_lecran_de_plus_de_six_mots(
    patrons: patterns.Patterns,
) -> None:
    script = _script([
        ("contexte", "plant", "Stick around: the reason is stranger than the shape."),
        ("point", "payoff", "As I promised, here is the reason."),
        ("conclusion", "none", "That is what the floor hides."),
    ])
    script.segments[1].on_screen_text = "ONE TWO THREE FOUR FIVE SIX SEVEN"
    rapport = _verifier(script, patrons)
    assert any(i.code == "texte_ecran_trop_long" for i in rapport.infractions)


def test_verify_signale_labsence_de_cible_de_densite_sans_bloquer(
    patrons: patterns.Patterns,
) -> None:
    """Une niche sans cible mesurée est signalée, jamais notée de force."""
    script = _script([
        ("contexte", "plant", "Stick around: the reason is stranger than the shape."),
        ("point", "payoff", "As I promised, here is the reason: the crust is bending."),
        ("conclusion", "none", "That is what the floor hides."),
    ], ruptures={"seg_01": "question"})
    rapport = _verifier(script, patrons, densite_cible=None)
    sans_cible = [i for i in rapport.infractions if i.code == "densite_sans_cible"]
    assert sans_cible and not sans_cible[0].bloquante


def test_verify_bloque_sous_la_cible_de_densite(patrons: patterns.Patterns) -> None:
    script = _script([
        ("contexte", "plant", "Stick around: the reason is stranger than the shape."),
        ("point", "payoff", "As I promised, here is the reason: it simply bends."),
        ("point", "none", "The shape of it is something people talk about a great deal."),
        ("conclusion", "none", "That is what the floor hides."),
    ], ruptures={"seg_01": "question"})
    rapport = _verifier(script, patrons, densite_cible=99.0)
    infraction = next(i for i in rapport.infractions if i.code == "densite_sous_cible")
    assert infraction.bloquante
    assert infraction.segments
    assert "verifiable facts per minute" in infraction.consigne
