"""Étape 28 — tableau de bord Streamlit, éprouvé par `AppTest` sur un dépôt jetable.

Éprouvé ici : chaque page se rend sans exception, une approbation depuis l'interface écrit
`review_log` avec le relecteur choisi, une cadence invalide est refusée par la validation de
`factory config validate` et une cadence valide est écrite (ancienne version en `.bak`).
Non éprouvé ici : le rendu dans un vrai navigateur (voir les captures de `docs/img/`).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from factory.core import db
from factory.core.paths import RunPaths
from factory.core.paths import racine_projet as vraie_racine
from factory.orchestrator import queue as file_module

DASHBOARD = vraie_racine() / "dashboard"
PAGES = ["app.py", *sorted(f"vues/{p.name}" for p in (DASHBOARD / "vues").glob("*.py"))]
VID = "bms-science-en-20260922-aaaa"

SCRIPT = {
    "schema_version": "1.0", "lang": "en",
    "hook": {"type": "contre_intuitif", "text": "Neutron stars spin faster than a blender."},
    "segments": [
        {"id": "seg_00", "role": "hook", "narration": "Neutron stars spin fast.",
         "visual_intent": "Close-up of a spinning sphere.", "open_loop": "plant"},
        {"id": "seg_01", "role": "contexte", "narration": "A teaspoon weighs a billion tons.",
         "visual_intent": "Diagram of density.", "open_loop": "plant"},
        {"id": "seg_02", "role": "point", "narration": "That is why they spin up.",
         "visual_intent": "Comparison between two stars.", "open_loop": "payoff"},
        {"id": "seg_03", "role": "conclusion", "narration": "And that is the answer.",
         "visual_intent": "Aerial view of a nebula.", "open_loop": "payoff"},
    ],
    "editorial_signature": {"angle": "comparaison_chiffree",
                            "elements_proprietaires": ["mesure maison"]},
    "word_count": 24, "estimated_duration_s": 600.0,
}
TOPIC = {"sujet": "Why neutron stars spin", "angle": "comparatif_chiffre", "source": "topics_queue",
         "evidence": {"score": 0.8, "ratio": 1.4, "n": 2, "requete": "test"}}
SPEC = {
    "schema_version": "1.0", "video_id": VID, "parent_id": None, "channel_id": "bms-science-en",
    "lang": "en", "niche": "science_pop", "style": "illustre", "topic": TOPIC,
    "target_duration_s": 660, "cut_rhythm_target_s": 5.7, "seed": 12345, "product_id": None,
    "created_at": "2026-09-22T09:00:00Z",
}
MANIFEST = {
    "schema_version": "1.0",
    "identite": {"video_id": VID, "parent_id": None, "channel_id": "bms-science-en", "lang": "en",
                 "niche": "science_pop", "style": "illustre", "template_id": "sci-a",
                 "charte_version": "2026.09.1"},
    "decisions": {"topic": TOPIC, "hook_type": "contre_intuitif", "cut_rhythm_target_s": 5.7,
                  "voice_id": "serena_en", "title_chosen": "Why neutron stars spin so fast",
                  "density_facts_per_min": 3.4},
    "execution": {"timings": {}},
}


@pytest.fixture
def racine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Dépôt jetable : vraie `config/` recopiée, un script en attente de relecture."""
    for nom in ("workspace/runs", "workspace/logs", "docs", "registre/data", "reports"):
        (tmp_path / nom).mkdir(parents=True, exist_ok=True)
    shutil.copytree(vraie_racine() / "config", tmp_path / "config")
    shutil.copy2(vraie_racine() / "docs" / "EXPLOITATION.md", tmp_path / "docs")
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))

    chemins = RunPaths.depuis_video_id(VID, tmp_path)
    chemins.racine.mkdir(parents=True)
    chemins.spec.write_text(json.dumps(SPEC), encoding="utf-8")
    chemins.manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    chemins.script.write_text(json.dumps(SCRIPT), encoding="utf-8")
    conn = db.ouvrir(tmp_path / "workspace" / "factory.db")
    quand = file_module.maintenant()
    conn.execute("INSERT INTO runs (video_id, channel_id, lang, topic_sujet, created_at, updated_at) "
                 "VALUES (?, 'bms-science-en', 'en', ?, ?, ?)", (VID, TOPIC["sujet"], quand, quand))
    job = file_module.enfiler(conn, VID, "bms-science-en", stage="voice", racine=tmp_path)
    conn.execute("UPDATE jobs SET status = 'awaiting_review' WHERE id = ?", (job.id,))
    conn.close()
    return tmp_path


def _page(chemin: str) -> AppTest:
    at = AppTest.from_file(str(DASHBOARD / chemin), default_timeout=60)
    at.run()
    return at


@pytest.mark.parametrize("chemin", PAGES)
def test_chaque_page_se_rend(racine: Path, chemin: str) -> None:
    at = _page(chemin)
    assert not at.exception, [e.message for e in at.exception]


def test_la_bascule_anglais_traduit(racine: Path) -> None:
    at = _page("vues/1_vue_ensemble.py")
    assert at.title[0].value == "Vue d'ensemble"
    at.sidebar.radio(key="langue").set_value("en").run()
    assert at.title[0].value == "Overview"


def test_approuver_depuis_linterface_ecrit_review_log(racine: Path) -> None:
    at = _page("vues/3_relecture.py")
    at.selectbox(key="relecteur").set_value("sofiane").run()
    job_id = int(at.button[0].key.split("_")[1])
    at.button(key=f"approuver_{job_id}").click().run()
    assert not at.exception

    conn = sqlite3.connect(racine / "workspace" / "factory.db")
    ligne = conn.execute("SELECT video_id, reviewer, decision FROM review_log "
                         "ORDER BY timestamp DESC LIMIT 1").fetchone()
    statut = conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()[0]
    conn.close()
    assert ligne == (VID, "sofiane", "approved")
    assert statut == "queued"


def _soumettre_cadence(par_semaine: int) -> AppTest:
    at = _page("vues/6_configuration.py")
    at.selectbox(key="cfg_chaine").set_value("bms-science-en").run()
    at.number_input(key="cfg_par_semaine").set_value(par_semaine)
    next(b for b in at.button if b.label in ("Valider et enregistrer",)).click().run()
    return at


def test_cadence_invalide_refusee(racine: Path) -> None:
    fichier = racine / "config" / "channels" / "bms-science-en.yaml"
    avant = fichier.read_text(encoding="utf-8")
    at = _soumettre_cadence(3)  # plafond de 2 par semaine (CONFORMITE § 6)
    assert not at.exception
    assert any("per_week_max" in e.value or "Rien n'est enregistré" in e.value for e in at.error)
    assert fichier.read_text(encoding="utf-8") == avant
    assert not fichier.with_name(fichier.name + ".bak").exists()


def test_cadence_valide_ecrite_avec_bak(racine: Path) -> None:
    fichier = racine / "config" / "channels" / "bms-science-en.yaml"
    avant = fichier.read_text(encoding="utf-8")
    at = _soumettre_cadence(1)
    assert not at.exception, [e.message for e in at.exception]
    apres = fichier.read_text(encoding="utf-8")
    assert "per_week_max: 1" in apres
    # Seule la cadence change ; les commentaires du fichier survivent à l'aller-retour.
    assert "# plafond dur des 90 premiers jours" in apres
    changees = [(a, b) for a, b in zip(avant.splitlines(), apres.splitlines()) if a != b]
    assert len(changees) == 1 and len(avant.splitlines()) == len(apres.splitlines())
    assert fichier.with_name(fichier.name + ".bak").read_text(encoding="utf-8") == avant


def test_ajouter_une_chaine_valide_et_naffiche_aucun_secret(racine: Path) -> None:
    at = _page("vues/6_configuration.py")
    at.text_input(key="cfg_nouvel_id").input("bms-cuisine-en")
    at.text_input(key="cfg_nouveau_nom").input("BMS Cuisine EN")
    at.selectbox(key="cfg_nouvelle_voix").set_value("en:kokoro_af_heart")  # voix libre
    next(b for b in at.button if b.label == "Valider et créer").click().run()
    assert not at.exception, [e.message for e in at.exception]
    fichier = racine / "config" / "channels" / "bms-cuisine-en.yaml"
    texte = fichier.read_text(encoding="utf-8")
    assert "id: bms-cuisine-en" in texte and "voice_id: kokoro_af_heart" in texte
    assert "auto_approve: false" in texte and "token_ref: secrets/tokens/bms-cuisine-en.json" in texte


def test_ajouter_une_chaine_sur_une_voix_prise_est_refuse(racine: Path) -> None:
    at = _page("vues/6_configuration.py")
    at.text_input(key="cfg_nouvel_id").input("bms-cuisine-en")
    at.selectbox(key="cfg_nouvelle_voix").set_value("en:serena_en")  # prise par bms-science-en
    next(b for b in at.button if b.label == "Valider et créer").click().run()
    assert not (racine / "config" / "channels" / "bms-cuisine-en.yaml").exists()
    assert any("CONFORMITE § 5" in e.value for e in at.error)
    assert any("factory publish auth --channel bms-cuisine-en" in c.value for c in at.code)
