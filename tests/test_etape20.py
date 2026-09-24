"""Étape 20 — percées, regroupement, trous, file de sujets.

Aucun appel au modèle d'embeddings ni au LLM : `embed()` est remplacé par une fonction
déterministe, et les angles sont injectés. Ce qui est éprouvé ici est ce qui décide du
classement et ce qui protège la conformité :

  - une percée se mesure **à âge comparable**, et une vidéo sans comparables n'est
    **ni** percée **ni** non-percée : elle est non notée ;
  - la résurgence porte sur l'**indice** de vélocité, pas sur la vélocité brute — sans
    quoi elle ne mesure que l'âge (mesuré : facteur 31 entre 30 et 180 jours) ;
  - un cluster porte **au plus un** type de trou ;
  - le malus de similarité ne s'applique qu'au-dessus du seuil, et il est proportionnel ;
  - `topics_queue` ne réécrit jamais une ligne `used` ou `banned` ;
  - `plan` prend la file d'abord, puis le référentiel, et marque la ligne consommée.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from factory.core import db
from factory.editorial import embed as em
from factory.editorial import topics as tp


@pytest.fixture
def conn(tmp_path) -> sqlite3.Connection:
    return db.ouvrir(tmp_path / "factory.db")


def _video(vid, canal, age, vues, lang="en", titre="t", niche="science_pop", velocity=None):
    return tp.Video(
        video_id=vid, channel_id=canal, channel_title=canal, niche=niche, lang=lang,
        title=titre, description_head=None,
        published_at=(datetime.now(UTC) - timedelta(days=age)).isoformat(),
        age_days=float(age), views=vues,
        velocity=(vues / age if velocity is None and age else velocity),
        views_d7=None, views_d30=None,
    )


REGLAGES_PERCEES = {"seuil_ratio": 3.0, "fenetre_age_relative": 0.30,
                    "min_comparables": 3, "preferer_dN": True}


# ------------------------------------------------------------------------- percées


def test_percee_se_mesure_a_age_comparable():
    """Une vidéo à 3× la médiane de sa tranche d'âge est une percée ; la médiane l'est pas."""
    videos = [_video(f"v{i}", "c1", 100, 1000) for i in range(5)]
    star = _video("star", "c1", 100, 5000)
    videos.append(star)
    population = {"c1": [(v.age_days, float(v.views)) for v in videos]}
    tp.marquer_percees(videos, population, REGLAGES_PERCEES)
    assert star.percee is True
    assert star.ratio == pytest.approx(5.0)
    assert videos[0].percee is False


def test_une_video_ne_se_compare_pas_a_elle_meme():
    """Sans ce retrait, une chaîne à deux vidéos identiques aurait toujours un ratio de 1."""
    a, b = _video("a", "c1", 50, 900), _video("b", "c1", 50, 900)
    c, d = _video("c", "c1", 50, 900), _video("gros", "c1", 50, 2700)
    videos = [a, b, c, d]
    population = {"c1": [(v.age_days, float(v.views)) for v in videos]}
    tp.marquer_percees(videos, population, REGLAGES_PERCEES)
    assert d.n_comparables == 3
    assert d.ratio == pytest.approx(3.0)
    assert d.percee is True


def test_sans_comparables_la_video_est_non_notee_pas_non_percee():
    """« Non notée » et « pas une percée » ne sont pas la même chose, et le code le dit."""
    seule = _video("seule", "c1", 12, 99999)
    mesure = tp.marquer_percees([seule], {"c1": [(12.0, 99999.0)]}, REGLAGES_PERCEES)
    assert seule.ratio is None
    assert seule.percee is False
    assert "non notée" in seule.base_ratio
    assert mesure["n_non_notees"] == 1


def test_fenetre_age_exclut_les_ages_eloignes():
    """±30 % : une vidéo de 100 jours ne se compare pas à des vidéos de 10 jours."""
    star = _video("star", "c1", 100, 3000)
    lointaines = [(10.0, 100.0)] * 20
    tp.marquer_percees([star], {"c1": [*lointaines, (100.0, 3000.0)]}, REGLAGES_PERCEES)
    assert star.ratio is None  # aucun comparable dans la fenêtre


# ------------------------------------------------- indice de vélocité et résurgence


def test_indice_de_velocite_corrige_le_biais_d_age():
    """Mesuré le 20/09/2026 : vélocité médiane ×31 entre 0-30 j et 90-180 j.

    Sans l'indice, « les vidéos récentes du cluster vont plus vite » est vrai pour
    n'importe quel cluster : 9 clusters éligibles sur 10 passaient le seuil.
    """
    jeunes = [_video(f"j{i}", "c1", 10, 50_000) for i in range(10)]
    vieux = [_video(f"o{i}", "c1", 150, 15_000) for i in range(10)]
    tp.indexer_velocite(jeunes + vieux, n_deciles=2)
    # Vélocités brutes : 5 000 vs 100 vues/j, un facteur 50. Indices : 1,0 des deux côtés.
    assert jeunes[0].velocity == pytest.approx(5000.0)
    assert vieux[0].velocity == pytest.approx(100.0)
    assert jeunes[0].velocity_index == pytest.approx(1.0)
    assert vieux[0].velocity_index == pytest.approx(1.0)


# --------------------------------------------------------------------------- trous


def _cluster(cid, videos, demande=None):
    vecteurs = [[1.0, 0.0]] * len(videos)
    c = tp.Cluster(
        cluster_id=cid, videos=videos, centroide=[1.0, 0.0],
        langues=sorted({v.lang for v in videos}),
        n_percees=sum(1 for v in videos if v.percee),
        vues_totales=sum(v.views for v in videos),
        velocite_mediane=1.0,
        age_median=float(sorted(v.age_days for v in videos)[len(videos) // 2]),
    )
    c.demande_vues_mois = demande
    return c


REGLAGES_TROUS = {
    "multilingue": {"langues_source": ["fr", "es", "it"], "langue_cible": "en",
                    "min_percees_source": 2, "max_videos_cible": 1},
    "demande": {"max_videos_recentes": 3, "fenetre_recente_jours": 90,
                "percentile_demande_min": 90},
    "resurgence": {"age_median_min_jours": 120, "ratio_velocite_min": 1.5,
                   "min_videos_recentes": 2},
}


def test_trou_multilingue_dans_un_seul_sens():
    """Deux percées FR sans vidéo EN = trou. L'inverse n'est jamais un trou."""
    fr = [_video(f"f{i}", "cfr", 30, 90_000, lang="fr") for i in range(2)]
    for v in fr:
        v.percee = True
    vers_en = _cluster("c1", fr)
    en = [_video(f"e{i}", "cen", 30, 90_000, lang="en") for i in range(2)]
    for v in en:
        v.percee = True
    vers_fr = _cluster("c2", en)
    tp.detecter_trous([vers_en, vers_fr], REGLAGES_TROUS, 180)
    assert vers_en.gap_type == "multilingue"
    assert vers_fr.gap_type == ""  # l'anglais est la seule cible


def test_un_cluster_porte_au_plus_un_trou():
    """Cumuler les lacunes ferait compter deux fois la même absence."""
    fr = [_video(f"f{i}", "cfr", 30, 90_000, lang="fr") for i in range(2)]
    for v in fr:
        v.percee = True
    c = _cluster("c1", fr, demande=1_000_000)
    tp.detecter_trous([c], REGLAGES_TROUS, 180)
    assert c.gap_type == "multilingue"  # et pas « demande », pourtant satisfait aussi


def test_seuil_de_demande_est_un_percentile_de_l_execution():
    """Pas de valeur absolue : les niveaux Wikipédia n'ont pas d'échelle commune."""
    clusters = [
        _cluster(f"c{i}", [_video(f"v{i}", "c", 30, 100)], demande=float(i * 1000))
        for i in range(1, 11)
    ]
    comptes = tp.detecter_trous(clusters, REGLAGES_TROUS, 180)
    assert comptes["seuil_demande_vues_mois"] == 10000.0
    assert sum(1 for c in clusters if c.gap_type == "demande") == 1


# ------------------------------------------------------------------ cache et blobs


def test_le_vecteur_survit_a_l_aller_retour_en_base():
    vecteur = em.normaliser([0.3, -0.4, 0.5, 0.1])
    relu = em.depuis_blob(em.vers_blob(vecteur))
    assert relu == pytest.approx(vecteur, abs=1e-6)
    assert math.isclose(sum(x * x for x in relu), 1.0, abs_tol=1e-5)


def test_un_titre_corrige_invalide_sa_ligne_de_cache(conn, monkeypatch):
    """`text_hash` : sans lui, un titre corrigé chez l'éditeur garderait l'ancien vecteur."""
    appels: list[list[str]] = []

    def faux(textes, modele, racine, echo=None):
        appels.append(list(textes))
        return [[float(len(t)), 0.0, 0.0] for t in textes]

    monkeypatch.setattr(em, "_encoder_en_sous_processus", faux)
    em.embed_videos(conn, [("v1", "titre A")], racine=None)
    em.embed_videos(conn, [("v1", "titre A")], racine=None)
    assert len(appels) == 1  # le second passage vient du cache
    em.embed_videos(conn, [("v1", "titre A corrigé")], racine=None)
    assert len(appels) == 2


# ------------------------------------------------------------- malus de similarité


def _sujet(topic, score=0.5):
    return tp.Sujet(channel_id="ch", lang="en", niche="science_pop", cluster_id="c1",
                    topic=topic, angle="a", score=score, evidence={})


def test_le_malus_ne_frappe_qu_au_dessus_du_seuil(monkeypatch):
    monkeypatch.setattr(em, "embed", lambda textes, **k: [[1.0, 0.0] for _ in textes])
    proche = _sujet("identique")
    resultat = tp._appliquer_malus(
        [proche], [("deja produit", [1.0, 0.0])], {"seuil": 0.80, "poids": 0.30}
    )
    # cosinus 1,0 → malus plein : 0,5 − 0,30 = 0,20
    assert resultat[0].score == pytest.approx(0.20)

    monkeypatch.setattr(em, "embed", lambda textes, **k: [[0.0, 1.0] for _ in textes])
    loin = _sujet("sans rapport")
    resultat = tp._appliquer_malus(
        [loin], [("deja produit", [1.0, 0.0])], {"seuil": 0.80, "poids": 0.30}
    )
    assert resultat[0].score == pytest.approx(0.50)
    assert resultat[0].evidence["malus_similarite"]["valeur"] == 0.0


# -------------------------------------------------------------------------- la file


def test_une_ligne_used_n_est_jamais_reecrite(conn):
    sujet = _sujet("Sujet A", 0.9)
    tp.enregistrer(conn, [sujet], n_max=10)
    conn.execute("UPDATE topics_queue SET status='used', used_by_run='r1'")
    conn.commit()
    tp.enregistrer(conn, [_sujet("Sujet A", 0.1)], n_max=10)
    ligne = conn.execute("SELECT score, status, used_by_run FROM topics_queue").fetchone()
    assert ligne[0] == pytest.approx(0.9)
    assert ligne[1] == "used"
    assert ligne[2] == "r1"


def test_ban_et_approve_tracent_le_statut_precedent(conn):
    tp.enregistrer(conn, [_sujet("Sujet A", 0.9)], n_max=10)
    tid = conn.execute("SELECT id FROM topics_queue").fetchone()[0]
    assert tp.changer_statut(conn, tid, "approved")["avant"] == "proposed"
    assert tp.changer_statut(conn, tid, "banned")["avant"] == "approved"
    with pytest.raises(KeyError):
        tp.changer_statut(conn, 9999, "banned")


def test_la_reprise_met_a_jour_au_lieu_d_empiler(conn):
    tp.enregistrer(conn, [_sujet("Sujet A", 0.5)], n_max=10)
    tp.enregistrer(conn, [_sujet("Sujet A", 0.8)], n_max=10)
    lignes = conn.execute("SELECT score FROM topics_queue").fetchall()
    assert len(lignes) == 1
    assert lignes[0][0] == pytest.approx(0.8)  # mise à jour, pas empilement


def test_un_meme_theme_entre_avec_ses_deux_angles(conn):
    """L'angle fait partie de la clé : c'est lui qui distingue deux vidéos du même thème."""
    a = tp.Sujet("ch", "en", "science_pop", "c1", "Sujet A", "contrarien — x", 0.7, {})
    b = tp.Sujet("ch", "en", "science_pop", "c1", "Sujet A", "récit — y", 0.6, {})
    tp.enregistrer(conn, [a, b], n_max=10)
    assert conn.execute("SELECT COUNT(*) FROM topics_queue").fetchone()[0] == 2


# ------------------------------------------------------------------ plan.py (§ 3)


def test_plan_prend_la_file_avant_le_referentiel(conn, monkeypatch):
    from factory.steps import plan

    tp.enregistrer(conn, [
        tp.Sujet("bms-science-en", "en", "science_pop", "c7", "Sujet fort", "récit — x",
                 0.81, {"cluster_id": "c7", "label": "un thème", "n_videos": 12,
                        "n_chaines": 4, "n_percees": 3, "gap_type": "multilingue",
                        "videos_sources": [{"ratio": 3.4}]}),
        tp.Sujet("bms-science-en", "en", "science_pop", "c8", "Sujet faible", "test — y",
                 0.20, {"cluster_id": "c8"}),
    ], n_max=10)
    sujet, ecartes, topic_id = plan._choisir_sujet(
        "bms-science-en", "en", "science_pop", set(), None, conn=conn
    )
    assert sujet.source == "topics_queue"
    assert sujet.sujet == "Sujet fort"
    assert sujet.evidence.score == pytest.approx(0.81)
    assert "cluster c7" in (sujet.evidence.requete or "")
    assert topic_id is not None


def test_plan_saute_un_sujet_deja_pris_par_la_langue(conn):
    from factory.steps import plan

    tp.enregistrer(conn, [_sujet("Sujet A", 0.9)], n_max=10)
    conn.execute("UPDATE topics_queue SET channel_id='bms-science-en'")
    conn.commit()
    resultat = plan._sujet_depuis_file(
        conn, "bms-science-en", "en", {"sujet a"}, None
    )
    assert resultat is None  # la file ne rend rien → repli sur le référentiel


def test_plan_ignore_une_file_absente():
    """Migration 006 non appliquée : `plan` se replie, il ne plante pas."""
    from factory.steps import plan

    vide = sqlite3.connect(":memory:")
    assert plan._sujet_depuis_file(vide, "ch", "en", set(), None) is None


def test_le_suffixe_de_cache_ne_part_pas_au_depot_hugging_face(tmp_path, monkeypatch):
    """`…-e5-small#titre` est une clé de cache, pas un dépôt : `from_pretrained` refuse le `#`.

    Défaut rencontré le 20/09/2026 en exécution réelle — `HFValidationError: Repo id must
    use alphanumeric chars`, 11 minutes de calcul perdues.
    """
    charges: list[str] = []

    class FauxTokenizer:
        @staticmethod
        def from_pretrained(nom):
            charges.append(nom)
            raise SystemExit(0)  # on s'arrête dès que le nom est connu

    import sys
    import types

    faux = types.ModuleType("transformers")
    faux.AutoTokenizer = FauxTokenizer
    faux.AutoModel = FauxTokenizer
    monkeypatch.setitem(sys.modules, "transformers", faux)
    travail = tmp_path / "t.json"
    travail.write_text(json.dumps(
        {"model": "intfloat/multilingual-e5-small#titre", "texts": ["a"],
         "out": str(tmp_path / "v.jsonl")}), encoding="utf-8")
    with pytest.raises(SystemExit):
        em.main(["embed", str(travail)])
    assert charges == ["intfloat/multilingual-e5-small"]


def test_la_persona_impose_la_langue_de_la_chaine_en_toutes_lettres():
    """« a channel in en » a fait rendre des sujets en français au 9B (20/09/2026).

    Le trou multilingue consiste à produire EN ANGLAIS ce qui marche en FR, ES ou IT :
    un sujet rendu en français le rend inutilisable.
    """
    class FausseChaine:
        id, name, lang, niche, style = "bms-science-en", "BMS Science EN", "en", "science_pop", "illustre"

    systeme = tp.systeme_angles(FausseChaine(), ["contrarien", "recit"])
    assert "WRITE EVERYTHING IN ENGLISH" in systeme
    assert "without exception" in systeme
    assert "in en" not in systeme
