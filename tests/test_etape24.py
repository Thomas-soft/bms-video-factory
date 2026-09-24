"""Étape 24 — déclinaison multilingue : squelette enfant, héritage d'images, calendrier.

Aucun modèle n'est chargé : l'adaptation par LLM et le DAG sont exercés par le vrai run
de l'étape (`factory localize`), pas ici.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from factory.core import runs
from factory.core.models import Asset, AssetRequest, Shot
from factory.core.paths import RACINE_DEFAUT, RunPaths
from factory.publish import calendar
from factory.steps import localize

PARENT = "bms-science-fr-20260917-rtmk"
SOURCE = Path(RACINE_DEFAUT) / "workspace" / "runs" / PARENT
LEGERS = {"spec.json", "manifest.json", "script.json", "shotlist.json", "research.json",
          "metadata.json", ".done", "thumbnails"}

pytestmark = pytest.mark.skipif(not (SOURCE / "shotlist.json").exists(),
                                reason="run parent rtmk absent de cette machine")


@pytest.fixture
def bac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    shutil.copytree(Path(RACINE_DEFAUT) / "config", tmp_path / "config")
    # La production est en anglais seul et `derive_from` est désactivé en vrai (23/09/2026) :
    # le bac le réactive pour éprouver le mécanisme, qui reste livré.
    en = tmp_path / "config" / "channels" / "bms-science-en.yaml"
    en.write_text(re.sub(r"(?m)^derive_from: .*$", "derive_from: bms-science-fr",
                         en.read_text(encoding="utf-8")), encoding="utf-8")
    (tmp_path / "registre").mkdir()
    shutil.copy2(Path(RACINE_DEFAUT) / "registre" / "REFERENTIEL.json", tmp_path / "registre")
    run = tmp_path / "workspace" / "runs" / PARENT
    run.mkdir(parents=True)
    for nom in LEGERS:
        element = SOURCE / nom
        if element.exists():
            (shutil.copytree if element.is_dir() else shutil.copy2)(element, run / nom)
    # Deux images de parent suffisent à l'héritage ; le reste n'est pas lu par ces tests.
    for shot in ("shot_00", "shot_05"):
        shutil.copytree(SOURCE / "assets" / shot, run / "assets" / shot)
    manifeste = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    manifeste["children"] = []
    (run / "manifest.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return tmp_path


def test_enfant_template_et_miniature_differents(bac: Path) -> None:
    video_id, _ = localize.creer_enfant(PARENT, "bms-science-en", bac)
    spec = runs.charger_spec(video_id, bac)
    enfant = runs.charger_manifest(video_id, bac)
    parent = runs.charger_manifest(PARENT, bac)
    assert spec.parent_id == PARENT and spec.lang == "en"
    assert enfant.identite.template_id != parent.identite.template_id
    d = enfant.declinaison
    assert d is not None and d.parent_template_id == parent.identite.template_id
    cfg_mini = ["bandeau_bas", "bloc_gauche"]
    assert cfg_mini[spec.seed % 2] != d.parent_thumbnail_template
    assert [c.video_id for c in parent.children] == [video_id]
    # plan et research marqués faits : le DAG reprend à `script`, donc à l'adaptation.
    chemins = RunPaths.depuis_video_id(video_id, bac)
    assert chemins.done("plan").exists() and chemins.done("research").exists()
    assert not chemins.done("script").exists()
    # Idempotent : un second appel rend le même enfant.
    assert localize.creer_enfant(PARENT, "bms-science-en", bac)[0] == video_id


def test_meme_langue_refusee(bac: Path) -> None:
    with pytest.raises(localize.DeclinaisonImpossible, match="même langue"):
        localize.creer_enfant(PARENT, "bms-science-fr", bac)


def test_heritage_par_prompt_puis_par_segment(bac: Path) -> None:
    from factory.assets import images
    from factory.core import db

    video_id, _ = localize.creer_enfant(PARENT, "bms-science-en", bac)
    chemins = RunPaths.depuis_video_id(video_id, bac)
    gen = images.GenerateurImages(conn=db.ouvrir(bac / "workspace" / "factory.db"),
                                  style_id="illustre", racine=bac)
    gen.charger_heritage(chemins)
    parent_shots = json.loads((SOURCE / "shotlist.json").read_text(encoding="utf-8"))["shots"]
    p0 = parent_shots[0]

    def plan(shot_id: str, segment: str, demande: str) -> Shot:
        return Shot(id=shot_id, segment_id=segment, start_s=0, end_s=1, duration_s=1,
                    visual_intent=demande, asset_request=AssetRequest(
                        type="image", prompt_or_keywords=demande),
                    seed=1)

    exact = gen.image_heritee(plan("shot_00", p0["segment_id"],
                                   p0["asset_request"]["prompt_or_keywords"]))
    assert exact is not None and exact[2] == "prompt"
    assert isinstance(exact[1], Asset)
    # Demande inconnue, segment connu : image du même segment, pas de génération.
    meme_segment = gen.image_heritee(plan("shot_00", p0["segment_id"], "demande inédite"))
    assert meme_segment is not None and meme_segment[2] == "segment"
    # Segment inconnu : plan réellement nouveau, rien d'hérité.
    assert gen.image_heritee(plan("shot_00", "seg_99", "demande inédite")) is None
    assert gen.herites == {"prompt": 1, "segment": 1}


def test_calendrier_jamais_le_meme_jour_que_le_parent(bac: Path) -> None:
    video_id, _ = localize.creer_enfant(PARENT, "bms-science-en", bac)
    ctx = calendar.contexte(bac)
    t = datetime(2026, 10, 6, 16, 0, tzinfo=UTC)
    E = calendar.Evenement
    parent = E(PARENT, "bms-science-fr", t, "queued")
    chaine = ctx.chaines["bms-science-en"]
    assert "même jour" in (calendar.admissible(ctx, chaine, t + timedelta(hours=6), [parent],
                                               video_id) or "")
    regles = {v.regle for v in calendar.verifier(
        ctx, [parent, E(video_id, "bms-science-en", t + timedelta(hours=6), "queued")],
        t - timedelta(days=3))[0]}
    assert "meme_jour_parent" in regles
    assert calendar.admissible(ctx, chaine, t + timedelta(hours=30), [parent], video_id) is None


def test_derive_de_langue() -> None:
    assert localize._derive("Les muscles se contractent et la routine commence", "fr") > 0.3
    assert localize._derive("Your muscles contract and the routine begins", "fr") == 0.0


def test_orchestrateur_enfile_les_chaines_derive_from(bac: Path) -> None:
    from factory.core import db

    conn = db.ouvrir(bac / "workspace" / "factory.db")
    db.migrer(conn)
    enfants = localize.enfiler_declinaisons(conn, PARENT, bac)
    assert [cible for cible in localize.chaines_derivees("bms-science-fr", bac)] == ["bms-science-en"]
    assert len(enfants) == 1
    video_id, job_id = enfants[0]
    ligne = conn.execute("SELECT channel_id, stage, status FROM jobs WHERE id = ?",
                         (job_id,)).fetchone()
    assert tuple(ligne) == ("bms-science-en", "script", "queued")
    # Rejouer ne double ni l'enfant ni le job.
    assert localize.enfiler_declinaisons(conn, PARENT, bac) == []
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    # Une déclinaison ne se décline pas.
    assert localize.enfiler_declinaisons(conn, video_id, bac) == []
