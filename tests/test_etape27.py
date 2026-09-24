"""Étape 27 — affiliation par vidéo, import des revenus, économie unitaire."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.core import config as cfgmod
from factory.core import db
from factory.core.models import Product
from factory.monetization import economics, import_revenue, links
from factory.steps.script import construire_squelette

FIXTURES = Path(__file__).parent / "fixtures"
CFG = cfgmod.charger(strict=False)
PRODUIT = CFG.products["exemple-affilie"]


def _base(tmp_path: Path):
    conn = db.ouvrir(tmp_path / "workspace" / "factory.db")
    for vid in ("bms-science-en-20260920-s57f", "bms-science-en-20260919-mtn7",
                "bms-science-en-20260923-c7km"):
        conn.execute("INSERT INTO runs (video_id, channel_id, lang, niche, style, run_state,"
                     " duration_s, created_at, updated_at, manifest_path) VALUES"
                     " (?, 'bms-science-en', 'en', 'science_pop', 'illustre', 'exported', 600,"
                     " '2026-09-20T00:00:00Z', '2026-09-20T00:00:00Z', '')", (vid,))
    return conn


def test_les_cles_de_l_etape_27_sont_acceptees() -> None:
    assert PRODUIT.network == "impact" and PRODUIT.subid_param == "SubId1"
    assert PRODUIT.target_url.startswith("https://") and PRODUIT.cta_text["en"]
    assert PRODUIT.cta_segment.position == "apres_conclusion"


def test_le_subid_vaut_le_video_id_et_ne_se_tronque_jamais() -> None:
    lien = links.lien_pour(PRODUIT, "bms-science-en", "en", "bms-science-en-20260923-c7km")
    assert lien.subid_value == "bms-science-en-20260923-c7km"
    assert lien.target_url.endswith("?SubId1=bms-science-en-20260923-c7km")
    awin = Product.model_validate({**PRODUIT.model_dump(), "network": "awin",
                                   "subid_param": "clickref", "subid_max_len": 50,
                                   "sub_id_format": "{channel_id}_{lang}_{video_id}"})
    with pytest.raises(ValueError, match="invalide"):
        awin.subid("bms-science-en", "en", "bms-science-en-20260923-c7km-trop-long")


def test_digistore24_porte_le_subid_dans_le_chemin() -> None:
    d24 = Product.model_validate({**PRODUIT.model_dump(), "network": "digistore24",
                                  "subid_param": "campaignkey", "subid_max_len": 127,
                                  "target_url": "https://www.digistore24.com/redir/1/aff/"})
    assert links.lien_pour(d24, "c", "en", "v-1").target_url.endswith("/aff/v-1")


def test_la_surcharge_s_ajoute_a_la_mention_du_reseau() -> None:
    langue = CFG.languages["en"]
    lignes = links.mentions(PRODUIT, langue, "en")
    assert lignes[0] == langue.disclosure.pour_reseau("impact")
    assert len(lignes) == 2
    assert "#ad" in links.ligne_de_tete([PRODUIT], langue)


def test_sub_id_format_refuse_un_jeton_inconnu() -> None:
    with pytest.raises(ValueError, match="sub_id_format"):
        Product.model_validate({**PRODUIT.model_dump(), "sub_id_format": "{email}-{video_id}"})


def test_le_cta_produit_se_place_apres_la_conclusion() -> None:
    defaut = [c.role for c in construire_squelette(14, 1500, 40, True, 7, 600.0, 45.0)]
    fin = [c.role for c in construire_squelette(14, 1500, 40, True, 7, 600.0, 45.0,
                                                position="apres_conclusion")]
    assert defaut[3] == "sponsor" and defaut[-1] == "conclusion"
    assert fin[-2:] == ["conclusion", "sponsor"] and fin.count("sponsor") == 1
    assert len(fin) == 14


def test_import_rattache_par_subid_et_ne_double_pas(tmp_path) -> None:
    conn = _base(tmp_path)
    b = import_revenue.importer(conn, "impact", FIXTURES / "revenue_impact.csv", "fixture")
    assert (b.lues, b.inserees, b.annulees) == (6, 5, 1)
    assert b.non_rattachees == ["inconnu-hors-usine"]
    # l'ancien format <channel>_<lang>_<video_id> est reconnu par suffixe
    assert conn.execute("SELECT video_id FROM revenue WHERE sub_id LIKE 'bms-science-en_en_%'"
                        ).fetchone()[0] == "bms-science-en-20260923-c7km"
    again = import_revenue.importer(conn, "impact", FIXTURES / "revenue_impact.csv", "fixture")
    assert (again.inserees, again.doublons) == (0, 5)


def test_import_awin_et_amazon(tmp_path) -> None:
    conn = _base(tmp_path)
    b = import_revenue.importer(conn, "awin", FIXTURES / "revenue_awin.csv")
    assert (b.inserees, b.annulees) == (1, 1)
    montant, devise = conn.execute("SELECT amount, currency FROM revenue").fetchone()
    assert (montant, devise) == (2.5, "GBP")
    a = import_revenue.importer(conn, "amazon", FIXTURES / "revenue_amazon.csv")
    assert a.inserees == 1 and a.non_rattachees == ["bmsscience-20"]


def test_colonne_introuvable_leve_au_lieu_de_zero(tmp_path) -> None:
    conn = _base(tmp_path)
    faux = tmp_path / "x.csv"
    faux.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colonnes introuvables"):
        import_revenue.importer(conn, "cj", faux)


def test_economics_exclut_les_fixtures(tmp_path) -> None:
    conn = _base(tmp_path)
    import_revenue.importer(conn, "impact", FIXTURES / "revenue_impact.csv", "fixture")
    e = economics.calculer(conn, CFG.economics, tmp_path)
    assert len(e.videos) == 3 and e.revenus_fixture == 5
    assert all(v.revenu == 0 for v in e.videos)
    v = e.videos[0]
    rel = CFG.economics.relecture_forfait_min.defaut * CFG.economics.cout_horaire_relecture_eur.defaut / 60
    assert v.cout == pytest.approx(rel)  # compute_min = 0 sans manifeste, coûts fixes à 0
    assert "Trois décisions chiffrées" in economics.rapport(e)
