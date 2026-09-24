"""Étape 29 — bibliothèque, voix, chartes et gabarits, avatar 2D (sans modèle ni Rhubarb)."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import yaml

from factory import library
from factory.core import config as config_module
from factory.core import db, runs
from factory.core.paths import racine_projet
from factory.styles import STYLE_ENGINES
from factory.styles.avatar2d import Avatar2dEngine


@pytest.fixture(scope="module")
def configuration():
    return config_module.charger(racine_projet(), strict=False)


@pytest.fixture()
def conn(tmp_path) -> sqlite3.Connection:
    return db.ouvrir(tmp_path / "factory.db")


def _vecteur(graine: int) -> np.ndarray:
    v = np.random.default_rng(graine).normal(size=384).astype(np.float32)
    return v / np.linalg.norm(v)


# -- bibliothèque ----------------------------------------------------------------------


def test_migration_ajoute_colonnes_et_journal(conn):
    colonnes = {l[1] for l in conn.execute("PRAGMA table_info(library_assets)")}
    assert {"description", "tags", "embedding", "embed_hash", "size_bytes"} <= colonnes
    assert "library_semantic_reuse" in db.tables(conn)


def test_reemploi_semantique_respecte_seuil_cooldown_et_run(conn):
    a, b = _vecteur(1), _vecteur(2)
    index = library.IndexSemantique(ids=["a" * 16, "b" * 16], chemins=["x/a.png", "x/b.png"],
                                    matrice=np.vstack([a, b]))
    index.requetes["intention"] = a  # similarité 1 avec a, ≈ 0 avec b
    libre = lambda _id: (True, "libre")  # noqa: E731
    trouve = library.reemploi_semantique(conn, index, "intention", seuil=0.9, libre=libre,
                                         deja_dans_run=set(), video_id="v1", shot_id="shot_00",
                                         kind="images")
    assert trouve and trouve[0] == "a" * 16
    assert conn.execute("SELECT count(*) FROM library_semantic_reuse").fetchone()[0] == 1
    # déjà servi dans ce run → rien (b est sous le seuil)
    assert library.reemploi_semantique(conn, index, "intention", seuil=0.9, libre=libre,
                                       deja_dans_run={"a" * 16}, video_id="v1",
                                       shot_id="shot_01", kind="images") is None
    # cooldown refusé → rien
    assert library.reemploi_semantique(conn, index, "intention", seuil=0.9,
                                       libre=lambda _id: (False, "cooldown"), deja_dans_run=set(),
                                       video_id="v1", shot_id="shot_02", kind="images") is None


def test_description_image_retire_prefixe_et_suffixe():
    prefixes = [("flat vector", "16:9 composition", "prefixe:x")]
    desc, tag = library._description_image(
        "flat vector, Diagram of a clock — rupture, 16:9 composition", prefixes)
    assert desc == "Diagram of a clock" and tag == "prefixe:x"
    assert library._description_image("autre style, sujet", prefixes)[1] == "prefixe:inconnu"


def test_taux_reemploi_ne_compte_que_les_assets_anterieurs(conn):
    conn.executemany("INSERT INTO library_uses VALUES (?,?,?,?)", [
        ("a", "v1", "c", "2026-09-01T00:00:00Z"), ("a", "v2", "c", "2026-09-02T00:00:00Z"),
        ("b", "v2", "c", "2026-09-02T00:00:00Z")])
    r = library.taux_reemploi(conn, ["v2"])
    assert (r["reemplois"], r["emplois"]) == (1, 2)


def test_prune_simule_par_defaut(conn, tmp_path):
    fichier = tmp_path / "workspace/library/images/k.png"
    fichier.parent.mkdir(parents=True)
    fichier.write_bytes(b"x")
    conn.execute("INSERT INTO library_assets (asset_id, kind, path, provider, licence,"
                 " licence_url, created_at, last_used_at) VALUES ('k','images',?,'flux','A','u',"
                 "'2020-01-01T00:00:00Z','2020-01-01T00:00:00Z')",
                 (str(fichier.relative_to(tmp_path)),))
    r = library.prune(conn, tmp_path, unused_days=180)
    assert r["candidats"] == 1 and fichier.exists()
    library.prune(conn, tmp_path, unused_days=180, executer=True)
    assert not fichier.exists()


# -- voix -------------------------------------------------------------------------------


def test_chaque_chaine_a_un_profil_de_voix(configuration):
    for channel in configuration.list_channels():
        profil = configuration.profil_voix(channel)
        assert profil is not None and profil.lang == channel.lang


def test_validateur_refuse_meme_locuteur_sous_deux_identifiants(tmp_path):
    copie = tmp_path / "config"
    shutil.copytree(racine_projet() / "config", copie)
    shutil.copytree(racine_projet() / "outils", tmp_path / "outils",
                    ignore=lambda *_: [n for n in _[1] if n not in ("LICENCES.md",)])
    fichier = copie / "voices" / "ryan_en.yaml"
    donnees = yaml.safe_load(fichier.read_text())
    donnees["speaker"] = "serena"  # même locuteur que serena_en, sous un autre id
    fichier.write_text(yaml.safe_dump(donnees))
    problemes = config_module.valider(tmp_path)
    assert any("locuteur qwen3_tts/serena" in p.message for p in problemes)


# -- chartes et gabarits -----------------------------------------------------------------


@pytest.mark.parametrize("cid", ["bms-science-en", "bms-histoire-en"])
def test_charte_externe_trois_gabarits(configuration, cid):
    channel = configuration.get_channel(cid)
    assert len(channel.charte.layouts) >= 3
    assert set(channel.templates) <= set(channel.charte.layouts)
    assert channel.charte.version and channel.charte.intro


def test_rotation_des_gabarits(conn):
    gabarits = ["a", "b", "c"]
    assert runs.gabarit_suivant(conn, "ch", gabarits) == "a"
    conn.execute("INSERT INTO runs (video_id, channel_id, lang, niche, style, template_id,"
                 " charte_version, run_state, created_at, updated_at) VALUES"
                 " ('v1','ch','en','n','s','c','1','exported','2026-09-01T00:00:00Z',"
                 "'2026-09-01T00:00:00Z')")
    assert runs.gabarit_suivant(conn, "ch", gabarits) == "a"
    conn.execute("INSERT INTO runs (video_id, channel_id, lang, niche, style, template_id,"
                 " charte_version, run_state, created_at, updated_at) VALUES"
                 " ('v2','ch','en','n','s','a','1','exported','2026-09-02T00:00:00Z',"
                 "'2026-09-02T00:00:00Z')")
    assert runs.dernier_gabarit_avant(conn, "ch", "v2") == "c"
    assert runs.gabarit_suivant(conn, "ch", gabarits) == "b"


# -- avatar 2D ----------------------------------------------------------------------------


def test_moteur_avatar_enregistre(configuration):
    assert STYLE_ENGINES["avatar2d"] is Avatar2dEngine
    assert configuration.styles["avatar2d"].executable


def test_clignements_deterministes_et_espaces():
    a = Avatar2dEngine._tirer_clignements("bms-x-1", 60.0)
    assert a == Avatar2dEngine._tirer_clignements("bms-x-1", 60.0)
    ecarts = [b[0] - a_[0] for a_, b in zip(a, a[1:])]
    assert ecarts and min(ecarts) >= 2.5 and max(ecarts) <= 5.0


def test_visemes_par_intervalle(configuration):
    moteur = Avatar2dEngine(style=configuration.styles["avatar2d"])
    moteur._timelines["seg_00"] = [(0.0, 0.2, "X"), (0.2, 0.5, "D"), (0.5, 0.7, "F")]
    assert [moteur.visemes_a("seg_00", t) for t in (0.1, 0.3, 0.6, 0.9)] == ["X", "D", "F", "X"]
