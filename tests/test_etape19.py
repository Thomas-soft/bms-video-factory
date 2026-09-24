"""Étape 19 — notation des niches : décomposition de la demande, concurrence, score.

Aucun appel réseau : les séries mensuelles sont fabriquées, et les deux points
d'entrée HTTP (`pageviews_mensuels`, `autocomplete_youtube`) sont remplacés par des
faux dans les tests de bout en bout. Ce qui est éprouvé ici est ce qui décide du
classement : la séparation tendance/saisonnalité, le refus de la moyenne pour une
donnée absente, et le fait qu'aucune note subjective ne vienne du code.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta

import pytest

from factory.core import db
from factory.editorial import demand as dm
from factory.editorial import niches as nz


@pytest.fixture
def conn(tmp_path) -> sqlite3.Connection:
    return db.ouvrir(tmp_path / "factory.db")


def _ts(decalage_jours: float) -> str:
    return (datetime.now(UTC) + timedelta(days=decalage_jours)).isoformat(timespec="seconds")


def _serie(n=24, base=1000.0, croissance=0.0, saison=None) -> list[tuple[str, int]]:
    """Série mensuelle synthétique : `base · (1+croissance)^t · saison[mois]`."""
    points = []
    annee, mois = 2024, 10
    for t in range(n):
        facteur = (saison or {}).get(mois, 1.0)
        points.append((f"{annee:04d}-{mois:02d}", int(base * (1 + croissance) ** t * facteur)))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return points


# ------------------------------------------------------------------- fenêtre


def test_le_mois_courant_est_exclu():
    """Au 20 du mois, le mois courant est aux deux tiers : l'inclure fabrique une chute."""
    debut, fin = dm.mois_complets(date(2026, 9, 20), 24)
    assert fin == "2026080100"
    assert debut == "2024090100"


def test_bascule_de_janvier():
    debut, fin = dm.mois_complets(date(2026, 1, 5), 12)
    assert fin == "2025120100"
    assert debut == "2025010100"


# --------------------------------------------- niveau, tendance, saisonnalité


def test_niveau_est_la_mediane_des_douze_derniers_mois():
    s = dm.decomposer("X", "en.wikipedia", _serie(base=500.0))
    assert s.niveau == pytest.approx(500.0, rel=0.01)


def test_pente_positive_sur_serie_croissante():
    s = dm.decomposer("X", "en.wikipedia", _serie(croissance=0.05))
    assert s.pente_mensuelle == pytest.approx(0.05, abs=0.005)
    assert s.r2 > 0.99


def test_pente_negative_sur_serie_en_decrue():
    s = dm.decomposer("X", "en.wikipedia", _serie(croissance=-0.04))
    assert s.pente_mensuelle < 0


def test_la_tendance_est_retiree_avant_la_saisonnalite():
    """Une série en croissance pure ne doit produire AUCUN pic saisonnier.

    C'est l'objection centrale : sans retrait de tendance, les derniers mois de
    l'année civile ramassent mécaniquement la croissance et passent pour une saison.
    """
    s = dm.decomposer("X", "en.wikipedia", _serie(croissance=0.06))
    indices = [indice for indice, _ in s.saisonnalite.values()]
    assert max(indices) - min(indices) < 0.05


def test_un_vrai_pic_saisonnier_ressort_malgre_la_croissance():
    s = dm.decomposer("X", "en.wikipedia", _serie(croissance=0.03, saison={12: 2.0}))
    meilleur = max(s.saisonnalite, key=lambda m: s.saisonnalite[m][0])
    assert meilleur == 12
    assert s.saisonnalite[12][0] > 1.5


def test_la_saisonnalite_porte_son_nombre_d_observations():
    """Sur 23 mois, certains mois civils n'ont qu'une observation : il faut le savoir."""
    s = dm.decomposer("X", "en.wikipedia", _serie(n=23))
    compte = {n for _, n in s.saisonnalite.values()}
    assert compte == {1, 2}


def test_le_dernier_mois_non_consolide_est_retire():
    """Le `monthly` de Wikimedia rend un mois de queue partiel : il fausse toute la pente."""
    points = _serie(n=24, base=1000.0)
    points[-1] = (points[-1][0], 30)  # ce que rend réellement l'API pour le mois le plus récent
    restants, coupes = dm.couper_queue_incomplete(points)
    assert coupes == 1 and len(restants) == 23


def test_une_vraie_chute_moderee_nest_pas_coupee():
    points = _serie(n=24, base=1000.0)
    points[-1] = (points[-1][0], 600)
    _, coupes = dm.couper_queue_incomplete(points)
    assert coupes == 0


def test_la_coupe_sauve_la_pente():
    points = _serie(n=24, base=1000.0, croissance=0.02)
    points[-1] = (points[-1][0], 25)
    s = dm.decomposer("X", "en.wikipedia", points)
    assert s.n_mois_non_consolides == 1
    assert s.pente_mensuelle == pytest.approx(0.02, abs=0.005)


def test_serie_vide_ne_fabrique_aucun_chiffre():
    s = dm.decomposer("X", "en.wikipedia", [])
    assert s.niveau is None and s.pente_mensuelle is None and s.saisonnalite == {}


# ---------------------------------------------------------------- agrégation


def test_la_pente_est_ponderee_par_le_niveau():
    """Un article confidentiel qui double ne doit pas emporter la pente de la niche."""
    gros = dm.decomposer("gros", "en.wikipedia", _serie(base=100_000.0, croissance=0.001))
    petit = dm.decomposer("petit", "en.wikipedia", _serie(base=40.0, croissance=0.06))
    a = dm.agreger([gros, petit], r2_minimal=0.0)
    assert a["pente"] == pytest.approx(0.001, abs=0.005)


def test_le_niveau_agrege_est_une_mediane_pas_une_somme():
    """Une somme récompense le nombre de seeds ; deux articles massifs gonflaient la niche."""
    seeds = [dm.decomposer(f"s{i}", "en.wikipedia", _serie(base=b))
             for i, b in enumerate([100.0, 200.0, 300.0])]
    a = dm.agreger(seeds)
    assert a["niveau"] == pytest.approx(200.0, rel=0.02)
    assert a["niveau_somme"] == pytest.approx(600.0, rel=0.02)


def test_un_seed_mal_ajuste_n_apporte_pas_sa_pente():
    """`r2` était calculé, stocké, jamais lu : une série bruitée pesait comme une tendance."""
    import random

    random.seed(7)
    bruit = [(m, int(1000 * random.uniform(0.4, 2.5))) for m, _ in _serie(n=24)]
    a = dm.agreger([dm.decomposer("bruit", "en.wikipedia", bruit)], r2_minimal=0.3)
    assert a["pente"] is None and a["pente_n_seeds"] == 0


def test_les_seeds_sans_donnee_sont_comptes_a_part():
    a = dm.agreger([
        dm.decomposer("vivant", "en.wikipedia", _serie()),
        dm.decomposer("mort", "en.wikipedia", []),
    ])
    assert a["n_seeds"] == 1 and a["n_seeds_vides"] == 1


# --------------------------------------------------------------- normalisation


def test_une_donnee_absente_vaut_zero_et_non_la_moyenne():
    """La niche sans donnée ne doit pas hériter du score des autres."""
    assert nz.normaliser([10.0, 20.0, None]) == [0.0, 1.0, 0.0]


def test_valeurs_egales_donnent_un_demi():
    assert nz.normaliser([5.0, 5.0]) == [0.5, 0.5]


def test_aucune_valeur_donne_zero():
    assert nz.normaliser([None, None]) == [0.0, 0.0]


# ------------------------------------------------------------------- budgets


def test_le_budget_refuse_avant_l_appel():
    b = dm.BudgetAppels(2)
    assert b.prendre() and b.prendre()
    assert not b.prendre()
    assert b.utilises == 2 and b.refuses == 1


def test_user_agent_reste_encodable_en_latin1(monkeypatch):
    """Un en-tête HTTP est encodé en latin-1 : un caractère hors table casse l'appel."""
    monkeypatch.setenv("FACTORY_CONTACT", "contact—unicode@exemple.fr")
    dm.user_agent().encode("latin-1")


# ------------------------------------------------------------------- Trends


def test_trends_renvoie_null_et_sa_note():
    valeur, note = dm.demande_trends(["x"])
    assert valeur is None
    assert "alpha" in note


# ---------------------------------------------------------------- concurrence


def _chaine(conn, cid, niche, lang="en", titre=None):
    conn.execute(
        "INSERT INTO channels_watch (channel_id, handle, title, niche, lang, source, added_at)"
        " VALUES (?,?,?,?,?,'test',?)",
        (cid, f"@{cid}", titre or cid, niche, lang, _ts(0)),
    )


def _video(conn, vid, cid, age_jours, titre="titre", vues=1000):
    conn.execute(
        "INSERT INTO videos_ext (video_id, channel_id, published_at, title, description_head,"
        " duration_s, tags_json, category_id, thumbnail_url, first_seen_at, last_seen_at)"
        " VALUES (?,?,?,?,'',600,NULL,'27','',?,?)",
        (vid, cid, _ts(-age_jours), titre, _ts(0), _ts(0)),
    )
    conn.execute(
        "INSERT INTO video_snapshots (video_id, snapshot_date, views, likes, comments, fetched_at)"
        " VALUES (?,?,?,10,2,?)",
        (vid, datetime.now(UTC).date().isoformat(), vues, _ts(0)),
    )


REGLAGES = {
    "concurrence": {
        "chaine_active_videos_par_semaine": 1.0, "fenetre_activite_jours": 90,
        "fenetre_velocite_jours": 30, "fenetre_percees_jours": 365, "seuil_percee_ratio": 3.0,
        "plancher_videos": 10, "plancher_chaines": 1,
    }
}


def test_une_chaine_est_active_au_dela_d_une_video_par_semaine(conn):
    _chaine(conn, "UCactive", "test_niche")
    _chaine(conn, "UCmolle", "test_niche")
    for i in range(20):
        _video(conn, f"v{i}", "UCactive", i * 4)
    for i in range(3):
        _video(conn, f"w{i}", "UCmolle", i * 4)
    conn.commit()
    m = nz.mesures_concurrence(conn, {"labels_entrepot": ["test_niche"]}, "en", REGLAGES)
    assert m["n_chaines_actives"] == 1
    assert m["n_chaines_total"] == 2
    assert m["portee"] == "labels de niche"


def test_le_proxy_lexical_est_annonce_comme_tel(conn):
    _chaine(conn, "UCx", "autre_niche")
    _video(conn, "v1", "UCx", 5, titre="A Black Hole Swallowed A Star")
    _video(conn, "v2", "UCx", 5, titre="Cheap Kitchen Hacks")
    conn.commit()
    m = nz.mesures_concurrence(conn, {"filtre_titre": ["%black hole%"]}, "en", REGLAGES)
    assert m["n_videos"] == 1
    assert m["portee"] == "proxy lexical"


def test_une_niche_sous_le_plancher_n_est_pas_notee(conn):
    """Sans plancher, « 0 chaîne active » valait une rareté parfaite : l'ignorance payait."""
    _chaine(conn, "UCmaigre", "maigre")
    for i in range(4):
        _video(conn, f"m{i}", "UCmaigre", i * 3)
    conn.commit()
    m = nz.mesures_concurrence(conn, {"labels_entrepot": ["maigre"]}, "en", REGLAGES)
    assert m["n_videos"] == 4
    assert m["assez_de_donnees"] is False
    assert m["part_percees"] is None and m["n_chaines_actives_notees"] is None
    assert m["part_percees_brute"] is not None or m["n_videos_notees"] >= 0


def test_niche_vide_ne_rend_aucun_chiffre_invente(conn):
    m = nz.mesures_concurrence(conn, {"labels_entrepot": ["inexistante"]}, "en", REGLAGES)
    assert m["n_videos"] == 0
    assert m["velocite_mediane_30j"] is None
    assert m["part_percees"] is None
    assert m["assez_de_donnees"] is False


# ---------------------------------------------------- score composite et table


CONFIG_TEST = {
    "niche_scoring": {
        "ponderations": {"demande": 35, "concurrence": 25, "monetisation": 25, "faisabilite": 15},
        "demande": {"sous_ponderations": {"niveau": 0.55, "tendance": 0.35,
                                          "autocomplete": 0.10},
                    "fenetre_mois": 24, "pente_bornee": 0.06, "r2_minimal": 0.3,
                    "seuil_saison_nomme": 1.20},
        "concurrence": {"sous_ponderations": {"rarete_chaines": 0.45, "part_percees": 0.35,
                                              "pression_velocite": 0.20},
                        **REGLAGES["concurrence"]},
        "wikimedia": {"max_appels_par_execution": 400},
        "autocomplete": {"max_appels_par_execution": 200},
        "autocomplete_regions": {"en": {"hl": "en", "gl": "US"}},
        "limites": ["limite de test"],
        "objections": [{"probleme": "objection de test", "correction": "corrigée",
                        "statut": "appliquée"}],
    },
    "niches_notees": {
        "forte": {
            "origine": "registre", "labels_entrepot": ["forte"],
            "seeds_wikipedia": ["A"], "mots_cles": ["a"],
            "monetisation": {"en": {"note": 5, "resume": "r"}},
            "faisabilite": {"note": 5, "resume": "r"},
        },
        "faible": {
            "origine": "candidate", "filtre_titre": ["%rien%"],
            "seeds_wikipedia": ["B"], "mots_cles": ["b"],
            "monetisation": {"en": {"note": 1, "resume": "r", "eliminatoire": True,
                                    "motif_eliminatoire": "interdit de test"}},
            "faisabilite": {"note": 1, "resume": "r"},
        },
    },
}


@pytest.fixture
def sans_reseau(monkeypatch):
    def faux_pageviews(article, projet="en.wikipedia", **kw):
        return _serie(base=100_000.0, croissance=0.04) if article == "A" else _serie(base=50.0)

    def faux_autocomplete(mot_cle, **kw):
        return [f"{mot_cle} {i}" for i in range(10)] if mot_cle == "a" else ["b b"]

    monkeypatch.setattr(dm, "pageviews_mensuels", faux_pageviews)
    monkeypatch.setattr(dm, "autocomplete_youtube", faux_autocomplete)


def test_la_niche_forte_passe_devant(conn, sans_reseau, tmp_path):
    _chaine(conn, "UC1", "forte")
    for i in range(20):
        _video(conn, f"v{i}", "UC1", i * 4)
    conn.commit()
    notes = nz.noter(conn, lang="en", config=CONFIG_TEST, racine=tmp_path)
    assert [n.niche for n in notes] == ["forte", "faible"]
    # note 5 → 100 ; note 1 → 20, et surtout PAS 0 : 0 est réservé à l'absence de note.
    assert notes[0].monetisation == 100.0 and notes[1].monetisation == 20.0


def test_une_niche_interdite_est_marquee_et_sortie_du_top(conn, sans_reseau, tmp_path):
    notes = nz.noter(conn, lang="en", config=CONFIG_TEST, racine=tmp_path)
    interdite = next(n for n in notes if n.niche == "faible")
    assert interdite.eliminatoire and interdite.motif_eliminatoire == "interdit de test"
    texte = nz.ecrire_rapport(notes, racine=tmp_path, config=CONFIG_TEST).read_text("utf-8")
    assert "⛔" in texte and "interdit de test" in texte


def test_aucune_note_subjective_ne_vient_du_code(conn, sans_reseau, tmp_path):
    """Retirer la grille de la configuration doit faire tomber la note à zéro."""
    cfg = json.loads(json.dumps(CONFIG_TEST))
    cfg["niches_notees"]["forte"]["monetisation"] = {}
    cfg["niches_notees"]["forte"]["faisabilite"] = None
    notes = nz.noter(conn, lang="en", config=cfg, racine=tmp_path)
    forte = next(n for n in notes if n.niche == "forte")
    assert forte.monetisation == 0.0 and forte.faisabilite == 0.0


def test_la_table_garde_les_preuves(conn, sans_reseau, tmp_path):
    notes = nz.noter(conn, lang="en", config=CONFIG_TEST, racine=tmp_path)
    nz.enregistrer(conn, notes, jour="2026-09-20")
    lignes = conn.execute(
        "SELECT niche, lang, score, origine, evidence_json FROM niche_scores WHERE date='2026-09-20'"
    ).fetchall()
    assert len(lignes) == 2
    preuve = json.loads(lignes[0]["evidence_json"])
    assert "demande" in preuve and "concurrence" in preuve
    assert preuve["demande"]["trends"] is None


def test_rejouer_le_meme_jour_remplace_au_lieu_d_empiler(conn, sans_reseau, tmp_path):
    notes = nz.noter(conn, lang="en", config=CONFIG_TEST, racine=tmp_path)
    nz.enregistrer(conn, notes, jour="2026-09-20")
    nz.enregistrer(conn, notes, jour="2026-09-20")
    assert conn.execute("SELECT COUNT(*) FROM niche_scores").fetchone()[0] == 2


def test_le_rapport_nomme_ses_limites_et_son_user_agent(conn, sans_reseau, tmp_path):
    notes = nz.noter(conn, lang="en", config=CONFIG_TEST, racine=tmp_path)
    chemin = nz.ecrire_rapport(notes, racine=tmp_path, duree_s=1.0, config=CONFIG_TEST)
    texte = chemin.read_text(encoding="utf-8")
    assert "Limites des données" in texte
    assert "limite de test" in texte
    assert "BMS-Factory/1.0" in texte
    assert "Candidates hors registre" in texte
    assert "## Objections" in texte and "objection de test" in texte
