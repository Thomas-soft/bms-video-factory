"""Étape 26 — apprentissage : rétrécissement, bornes, repli, rétention, corrélation."""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from factory.analytics import learn, retention_analysis as ra, weights as wmod
from factory.core.models import ApprentissageConfig

P = ApprentissageConfig()


def _groupes(n: int, seed: int = 1) -> dict[str, list[float]]:
    """Même profil d'effets (+0,5, −0,5, 0) à n par niveau ; bruit σ=0,8, moyennes exactes."""
    alea = random.Random(seed)

    def tirer(mu: float) -> list[float]:
        vs = [mu + alea.gauss(0, 0.8) for _ in range(n)]
        m = sum(vs) / n
        return [v - m + mu for v in vs]

    return {"A": tirer(0.5), "B": tirer(-0.5), "C": tirer(0.0)}


def test_retrecissement_n2_ramene_vers_zero_n40_conserve() -> None:
    petit, _ = learn.effets_eb(_groupes(2))
    grand, _ = learn.effets_eb(_groupes(40))
    a2, a40 = petit["A"], grand["A"]
    assert a2.brut == pytest.approx(0.5) and a40.brut == pytest.approx(0.5)
    assert abs(a2.effet) < 0.1, f"n=2 : {a2.effet:.3f} pour 0,5 brut — doit être ramené vers 0"
    assert abs(a40.effet) > 0.8 * 0.5, f"n=40 : {a40.effet:.3f} pour 0,5 brut — doit être conservé"
    assert a2.retrecissement > 0.9 and a40.retrecissement < 0.2
    assert a2.ic90[0] < 0 < a2.ic90[1], "n=2 : l'intervalle contient 0"
    assert a40.ic90[0] > 0, "n=40 : l'intervalle exclut 0"


def test_tau_nul_donne_un_rétrécissement_total_mais_borné_par_le_plancher() -> None:
    effets, hyper = learn.effets_eb({"x": [0.0] * 5, "y": [0.01] * 5, "z": [-0.01] * 5})
    assert hyper["tau2"] == pytest.approx(learn.TAU_PLANCHER["y"] ** 2)
    assert all(abs(e.effet) <= abs(e.brut) for e in effets.values())


def test_garde_n_sous_le_seuil_multiplicateur_1() -> None:
    effets, _ = learn.effets_eb(_groupes(2))
    m, actif, motif = learn.multiplicateur(effets["A"], P, gele=False)
    assert (m, actif) == (1.0, False) and "non décidable (n=2" in motif
    grand, _ = learn.effets_eb(_groupes(40))
    m, actif, _ = learn.multiplicateur(grand["A"], P, gele=False)
    assert actif and m == pytest.approx(min(1.4, np.exp(grand["A"].effet)), abs=1e-3)
    m, actif, _ = learn.multiplicateur(grand["A"], P, gele=True)
    assert (m, actif) == (1.0, False), "un facteur gelé n'agit jamais"


def test_multiplicateurs_bornes() -> None:
    fort = learn.Effet(50, 3.0, 3.0, (2.5, 3.5), 0.999, 0.0)
    faible = learn.Effet(50, -3.0, -3.0, (-3.5, -2.5), 0.001, 0.0)
    assert learn.multiplicateur(fort, P, False)[:2] == (1.4, True)
    assert learn.multiplicateur(faible, P, False)[:2] == (0.7, True)
    assert wmod.borne(99) == 1.4 and wmod.borne(0.01) == 0.7
    assert wmod.borne("x") == 1.0 and wmod.borne(float("nan")) == 1.0


def test_repli_quand_weights_absent_ou_incompatible(tmp_path: Path) -> None:
    from factory.editorial import titles, topics
    from factory.steps import shotlist

    assert wmod.charger(tmp_path) is None
    assert titles.charger_poids_appris(tmp_path) == {}
    assert shotlist.facteur_rythme_appris("science_pop", tmp_path) == 1.0
    assert topics.multiplicateur_appris(None, "c1", "science_pop") == 1.0
    (tmp_path / "learned").mkdir()
    (tmp_path / "learned" / "weights.json").write_text(json.dumps(
        {"version": "2.0", "titles": {"patterns": {"a": 1.3}},
         "cut_rhythm": {"science_pop": {"factor": 1.1}}}), encoding="utf-8")
    assert wmod.charger(tmp_path) is None, "version majeure incompatible → repli"
    assert titles.charger_poids_appris(tmp_path) == {}
    assert shotlist.facteur_rythme_appris("science_pop", tmp_path) == 1.0


def test_consommateurs_lisent_un_weights_compatible_et_bornent(tmp_path: Path) -> None:
    from factory.editorial import topics
    from factory.steps import shotlist

    (tmp_path / "learned").mkdir()
    poids = {"version": "1.0", "cut_rhythm": {"science_pop": {"factor": 1.9}},
             "factors": {"topic_cluster": {"levels": {"c1": {"active": True, "multiplier": 1.4}}},
                         "niche": {"levels": {"science_pop": {"active": True, "multiplier": 1.4}}},
                         "hook_type": {"frozen": True,
                                       "levels": {"q": {"active": True, "multiplier": 1.4}}}}}
    (tmp_path / "learned" / "weights.json").write_text(json.dumps(poids), encoding="utf-8")
    assert shotlist.facteur_rythme_appris("science_pop", tmp_path) == 1.2, "±20 % au plus"
    assert topics.multiplicateur_appris(poids, "c1", "science_pop") == 1.4, "produit reborné"
    assert wmod.multiplicateur(poids, "hook_type", "q") == 1.0, "facteur gelé ignoré"


def test_hooks_repli_referentiel_sans_poids(monkeypatch) -> None:
    from factory.core import referentiel
    from factory.core.paths import racine_projet
    from factory.retention import hooks

    racine = racine_projet()
    monkeypatch.setattr(wmod, "charger", lambda _r: None)
    for seed in range(5):
        assert hooks.tirer_type("science_pop", seed, racine) == \
            referentiel.tirer_type_hook("science_pop", seed, racine)
    ref = dict(referentiel.niche("science_pop", racine)["hooks"]["parts"])
    type_ = sorted(t for t in ref if t in referentiel.types_productibles(racine))[0]
    parts = {t: (1.0 if t == type_ else 0.0) for t in ref}
    monkeypatch.setattr(wmod, "charger", lambda _r: {
        "version": "1.0", "hooks": {"science_pop": {"parts": parts, "changed": True}}})
    assert all(hooks.tirer_type("science_pop", s, racine)[0] == type_ for s in range(5))


def _courbe_avec_chute(debut: float, fin: float, pts: float) -> list[list[float]]:
    """Décroissance douce de 1,0 à 0,6, plus une chute de `pts` points sur [debut, fin]."""
    sortie = []
    for i in range(101):
        x = i / 100
        r = 1.0 - 0.4 * x
        if x > debut:
            r -= pts / 100 * min(1.0, (x - debut) / (fin - debut))
        sortie.append([x, r])
    return sortie


def test_alignement_des_courbes_sur_les_segments() -> None:
    segments = [{"id": f"seg_{i:02d}", "start_s": i * 60.0, "end_s": (i + 1) * 60.0} for i in range(10)]
    scripts = {"seg_00": {"role": "hook"}, "seg_03": {"role": "point", "interrupt": {"t": 1}},
               **{f"seg_{i:02d}": {"role": "point"} for i in (1, 2, 4, 5, 6, 7, 8)},
               "seg_09": {"role": "conclusion"}}
    sponsors = [{"start_s": 130.0, "end_s": 170.0, "type": "affiliate"}]
    videos = [{"video_id": "v0", "channel_id": "c", "points": _courbe_avec_chute(0.2, 0.3, 10),
               "duree_s": 600.0, "segments": segments, "scripts": scripts, "sponsors": sponsors}]
    videos += [{"video_id": f"v{i}", "channel_id": "c", "points": _courbe_avec_chute(0.9, 0.95, 0),
                "duree_s": 600.0, "segments": segments, "scripts": scripts, "sponsors": []}
               for i in (1, 2)]
    res = ra.analyser(videos, n_min=6)
    segs = {(s["video_id"], s["segment_id"]): s for s in res["segments"]}
    s2 = segs[("v0", "seg_02")]
    assert s2["role"] == "sponsor" and s2["position"] == "avant 40%"
    assert s2["chute_pts"] == pytest.approx(14.0, abs=1.5), "4 pts de pente + 10 pts de chute"
    assert s2["exces_pts"] == pytest.approx(10.0, abs=1.5), "l'excès isole la chute propre"
    assert segs[("v1", "seg_03")]["role"] == "rupture"
    assert segs[("v1", "seg_00")]["role"] == "hook"
    regle = next(r for r in res["rules"] if r["role"] == "sponsor")
    assert regle["n_videos"] == 1 and regle["status"].startswith("non décidable (n=1")


def test_spearman_calcule_et_ic() -> None:
    x = list(range(20))
    assert learn.spearman(x, [v ** 3 for v in x])["rho"] == pytest.approx(1.0)
    assert learn.spearman(x, [-v for v in x])["rho"] == pytest.approx(-1.0)
    alea = np.random.default_rng(3)
    y = [v + alea.normal(0, 6) for v in x]
    s = learn.spearman(x, y)
    assert s["n"] == 20 and s["ci95"][0] < s["rho"] < s["ci95"][1]
    # valeur de référence calculée à la main : rangs moyens en cas d'égalité
    assert learn.spearman([1, 2, 2, 3], [1, 3, 2, 4])["rho"] == pytest.approx(0.9487, abs=1e-3)
    assert learn.spearman([1, 2, 3], [1, 2, 3])["rho"] is None, "n < 4 : non calculable"


def test_normalisation_mediane_glissante_et_exclusion_des_chaines_trop_courtes() -> None:
    vues = [100, 200, 400, 800, 0]
    lignes = [{"video_id": f"a{i}", "channel_id": "A", "niche": "n", "views_7d": v,
               "publish_at": f"2026-01-0{i + 1}"} for i, v in enumerate(vues)]
    lignes += [{"video_id": f"b{i}", "channel_id": "B", "niche": "n", "views_7d": 300,
                "publish_at": f"2026-01-0{i + 1}"} for i in range(2)]
    out = {x["video_id"]: x for x in learn.normaliser(lignes, P)}
    # a0 : voisines a1..a4 (200, 400, 800, 0) → médiane 300, la vidéo elle-même exclue
    assert out["a0"]["views_ref"] == pytest.approx(300.0)
    assert out["a0"]["y"] == pytest.approx(np.log(101 / 301))
    assert out["a4"]["y"] is not None, "une vidéo à 0 vue reste dans l'échantillon"
    assert out["b0"]["y"] is None, "1 voisine < 3 : exclue, pas de repli sur la niche"
    assert out["a3"][learn.DIAGNOSTIC] == 3


def _lignes_synthetiques(n_par_chaine: int, chaines: int, effet: float, tendance: float = 0.0):
    """Vidéos d'un hook « q » (moitié) avec un vrai effet ; tendance log-linéaire optionnelle."""
    alea = random.Random(7)
    lignes = []
    for c in range(chaines):
        for i in range(n_par_chaine):
            q = i % 2 == 0
            y = (effet if q else 0.0) + tendance * i + alea.gauss(0, 0.3)
            lignes.append({"video_id": f"c{c}v{i}", "channel_id": f"c{c}", "niche": "n",
                           "hook_type": "q" if q else "r", "y": y, learn.DIAGNOSTIC: i})
    return lignes


def test_gel_global_sous_30_videos_puis_actif() -> None:
    peu = learn.estimer_facteurs(_lignes_synthetiques(8, 2, 0.6), P)
    hook = next(f for f in peu if f.nom == "hook_type")
    assert not any(v["active"] for v in hook.niveaux.values())
    assert all("gel global" in v["status"] for v in hook.niveaux.values())
    assert any(v["n"] >= 8 for v in hook.niveaux.values()), "n par niveau atteint, gel global tient"
    assez = learn.estimer_facteurs(_lignes_synthetiques(12, 3, 0.6), P)
    hook = next(f for f in assez if f.nom == "hook_type")
    assert hook.niveaux["q"]["active"] and hook.niveaux["q"]["multiplier"] > 1.0


def test_tendance_de_publication_gele_tout() -> None:
    res = learn.estimer_facteurs(_lignes_synthetiques(12, 3, 0.6, tendance=0.15), P)
    hook = next(f for f in res if f.nom == "hook_type")
    assert all(not v["active"] and "tendance" in v["status"] for v in hook.niveaux.values())


def test_thompson_inactif_garde_le_score_actif_suit_les_clics() -> None:
    from factory.editorial import thumbnails_variants as tv

    class V:
        def __init__(self, t: str) -> None:
            self.template, self.legible_at_320px, self.file = t, True, f"{t}.png"

    vs = [V("a"), V("b")]
    assert tv.choisir_initiale(vs, None, 1)[0] is vs[0]
    pol = {"thumbnail_policy": {"active": True, "prior": {"ctr": 0.04, "strength": 200},
                                "templates": {"b": {"alpha": 900, "beta": 9100}}}}
    choix = [tv.choisir_initiale(vs, pol, s)[0].template for s in range(20)]
    assert choix.count("b") >= 18, "CTR 9 % sur 10 000 impressions contre a priori 4 %"
    assert tv.proposer_rotation(0.05, 0.04, [("v2", "a")], pol, 0)[0] is None
    assert tv.proposer_rotation(0.02, 0.04, [("v2", "a")], None, 0)[0] == "v2"


def test_plan_classe_la_file_avec_et_sans_poids(tmp_path: Path) -> None:
    from factory.steps import plan

    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE topics_queue (id INTEGER, channel_id TEXT, topic TEXT, angle TEXT,
                    score REAL, evidence_json TEXT, status TEXT, used_by_run TEXT)""")
    for i, (score, cl) in enumerate([(0.80, "c1"), (0.75, "c2"), (0.70, "c3")]):
        conn.execute("INSERT INTO topics_queue VALUES (?,?,?,?,?,?,?,NULL)",
                     (i, "ch", f"t{i}", "", score, json.dumps({"cluster_id": cl}), "proposed"))
    sans = [x["topic"] for x in plan.classer_file(conn, "ch", "n", tmp_path, None)]
    poids = {"version": "1.0", "factors": {"topic_cluster": {"levels": {
        "c3": {"active": True, "multiplier": 1.3}, "c1": {"active": False, "multiplier": 0.7}}}}}
    avec = [x["topic"] for x in plan.classer_file(conn, "ch", "n", tmp_path, poids)]
    assert sans == ["t0", "t1", "t2"]
    assert avec == ["t2", "t0", "t1"], "c3 actif monte ; c1 inactif garde 1,0"


def test_learn_sur_base_vide_rend_non_decidable(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    res = learn.executer(tmp_path, conn, P, ecrire=False)
    assert res["weights"]["n_videos"] == 0
    assert all(not v["active"] for f in res["weights"]["factors"].values()
               for v in f["levels"].values())
    assert "non décidable (n=0" in res["report"] and "Banc vs résultats" in res["report"]
