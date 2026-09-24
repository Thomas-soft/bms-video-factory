"""Étape 23.2 — calendrier de publication et checklist de pré-publication.

Bac à sable : une copie de `config/` et du run exporté `s57f` (sans les vidéos lourdes,
`final.mp4` en lien symbolique) sous `tmp_path`, avec une base neuve. La relecture « humaine »
y est une **fixture** (`relecteur-test`), jamais écrite dans la vraie base.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from factory.core import db
from factory.core.paths import RACINE_DEFAUT
from factory.publish import calendar, precheck

RUN = "bms-science-en-20260920-s57f"
SOURCE = Path(RACINE_DEFAUT) / "workspace" / "runs" / RUN
LOURDS = {"assembled.mp4", "video_nomusic.mp4", "clips", "voice", "final.mp4", "qc"}

pytestmark = pytest.mark.skipif(not (SOURCE / "final.mp4").exists(),
                                reason="run s57f absent de cette machine")


def construire_bac(racine: Path, *, relecture: bool = True) -> Path:
    """Copie config + run, vérifie les comptes, écrit une relecture de fixture."""
    shutil.copytree(Path(RACINE_DEFAUT) / "config", racine / "config")
    (racine / "registre").mkdir(exist_ok=True)
    shutil.copy2(Path(RACINE_DEFAUT) / "registre" / "REFERENTIEL.json", racine / "registre")
    for yaml in (racine / "config" / "channels").glob("*.yaml"):
        texte = yaml.read_text(encoding="utf-8")
        texte = texte.replace("two_fa_enabled: false", "two_fa_enabled: true")
        texte = texte.replace("phone_verified: false", "phone_verified: true")
        yaml.write_text(texte, encoding="utf-8")
    run = racine / "workspace" / "runs" / RUN
    run.mkdir(parents=True)
    for element in SOURCE.iterdir():
        if element.name in LOURDS:
            continue
        (shutil.copytree if element.is_dir() else shutil.copy2)(element, run / element.name)
    (run / "final.mp4").symlink_to(SOURCE / "final.mp4")
    conn = db.ouvrir(racine / "workspace" / "factory.db")
    if relecture:
        empreinte = hashlib.sha256((run / "script.json").read_bytes()).hexdigest()
        conn.execute(
            "INSERT INTO review_log (video_id, channel_id, reviewer, decision, "
            "motif, script_sha256, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (RUN, "bms-science-en", "relecteur-test", "approved",
             "fixture de test", empreinte, "2026-09-23T08:00:00Z"))
        conn.commit()
    conn.close()
    return run


@pytest.fixture
def bac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    construire_bac(tmp_path)
    return tmp_path


def _conn(racine: Path):
    return db.ouvrir(racine / "workspace" / "factory.db")


# --------------------------------------------------------------------------------------
# precheck
# --------------------------------------------------------------------------------------


def test_precheck_pass_sur_run_conforme(bac: Path) -> None:
    rapport = precheck.controler(RUN, "bms-science-en", racine=bac)
    assert rapport.statut == "PASS", [c.detail for c in rapport.bloquants]
    ecrit = json.loads((bac / "workspace" / "runs" / RUN / "precheck.json").read_text())
    assert ecrit["status"] == "PASS"
    assert {c.id for c in rapport.controles} >= {
        "relecture", "qc", "mention_ia", "promotion_payante", "synthetique",
        "licences_assets", "attribution", "clonage_script", "clonage_miniature", "duree",
        "langue_categorie", "titre", "compte"}


def test_precheck_fail_sans_mention_ia(bac: Path) -> None:
    meta = bac / "workspace" / "runs" / RUN / "metadata.json"
    donnees = json.loads(meta.read_text())
    phrase = ("This video was produced with the help of artificial intelligence tools: "
              "research, writing, synthetic voice and illustrations.")
    assert phrase in donnees["description"]
    donnees["description"] = donnees["description"].replace(phrase, "")
    meta.write_text(json.dumps(donnees, ensure_ascii=False))
    rapport = precheck.controler(RUN, "bms-science-en", racine=bac)
    assert rapport.statut == "FAIL"
    assert [c.id for c in rapport.bloquants] == ["mention_ia"]
    assert precheck.bloquants(RUN, "bms-science-en", racine=bac)[0].startswith("[3] mention_ia")


def test_precheck_relecture_sur_autre_texte(bac: Path) -> None:
    script = bac / "workspace" / "runs" / RUN / "script.json"
    script.write_text(script.read_text() + " ")
    rapport = precheck.controler(RUN, "bms-science-en", racine=bac)
    assert "relecture" in {c.id for c in rapport.bloquants}


def test_precheck_lien_affilie_sans_promotion(bac: Path) -> None:
    meta = bac / "workspace" / "runs" / RUN / "metadata.json"
    donnees = json.loads(meta.read_text())
    donnees["description"] += "\nGet it here: https://amzn.to/3abcdef"
    meta.write_text(json.dumps(donnees, ensure_ascii=False))
    ids = {c.id for c in precheck.controler(RUN, "bms-science-en", racine=bac).bloquants}
    assert "promotion_payante" in ids


def test_precheck_clone_sur_autre_chaine(bac: Path) -> None:
    clone = "bms-histoire-en-20260921-cl0n"
    source = bac / "workspace" / "runs" / RUN
    cible = bac / "workspace" / "runs" / clone
    cible.mkdir()
    for nom in ("script.json", "thumbnail.png"):
        shutil.copy2(source / nom, cible / nom)
    spec = json.loads((source / "spec.json").read_text())
    spec.update(video_id=clone, channel_id="bms-histoire-en")
    (cible / "spec.json").write_text(json.dumps(spec))
    conn = _conn(bac)
    conn.execute("INSERT INTO publications (video_id, channel_id, status, updated_at) "
                 "VALUES (?, 'bms-histoire-en', 'published_private', '2026-09-22T00:00:00Z')",
                 (clone,))
    conn.commit()
    conn.close()
    ids = {c.id for c in precheck.controler(RUN, "bms-science-en", racine=bac).bloquants}
    assert {"clonage_script", "clonage_miniature"} <= ids


def test_simhash_separe_deux_textes() -> None:
    a = "the neutron star spins hundreds of times per second and emits beams of radio waves"
    b = "roman legions marched across the alps in winter carrying bread salt and iron tools"
    assert precheck.distance(precheck.simhash(a), precheck.simhash(a + " indeed")) < 12
    assert precheck.distance(precheck.simhash(a), precheck.simhash(b)) >= 12


# --------------------------------------------------------------------------------------
# calendrier
# --------------------------------------------------------------------------------------


def _jobs(racine: Path, n_par_chaine: int) -> list[str]:
    conn = _conn(racine)
    ids = []
    for cid in ("bms-science-en", "bms-histoire-en"):
        for k in range(n_par_chaine):
            vid = f"{cid}-20260923-t{k}{cid[4]}"
            (racine / "workspace" / "runs" / vid).mkdir(parents=True, exist_ok=True)
            (racine / "workspace" / "runs" / vid / "spec.json").write_text(
                json.dumps({"video_id": vid, "channel_id": cid, "lang": "en",
                            "target_duration_s": 600}))
            conn.execute("INSERT INTO jobs (video_id, channel_id, stage, status, created_at, "
                         "updated_at) VALUES (?, ?, 'research', 'queued', ?, ?)",
                         (vid, cid, f"2026-09-23T0{k}:00:00Z", f"2026-09-23T0{k}:00:00Z"))
            ids.append(vid)
    conn.commit()
    conn.close()
    return ids


def test_plan_trois_semaines_sans_violation(bac: Path) -> None:
    _jobs(bac, 4)
    conn = _conn(bac)
    maintenant = datetime(2026, 9, 23, 12, tzinfo=UTC)
    rapport = calendar.planifier(conn, semaines=3, racine=bac, maintenant=maintenant)
    assert len(rapport.decisions) == 8, [d.raison for d in rapport.ecartes]
    ctx = calendar.contexte(bac)
    evts = calendar.evenements(conn, bac)
    violations, _ = calendar.verifier(ctx, evts, maintenant)
    assert violations == []
    for e in evts:
        assert e.at >= maintenant + timedelta(hours=ctx.cal.delai_production_h)
    # jitter réel : pas toutes à la même minute
    assert len({e.at.minute for e in evts}) > 1
    # reproductible : un second plan (dry-run, --replan) redonne les mêmes dates
    avant = {e.video_id: e.at for e in evts}
    rejoue = calendar.planifier(conn, semaines=3, racine=bac, maintenant=maintenant,
                                replan=True, ecrire=False)
    assert {d.video_id: d.publish_at for d in rejoue.decisions} == {
        v: calendar._iso(t) for v, t in avant.items()}
    conn.close()


def test_plan_varie_les_durees(bac: Path) -> None:
    _jobs(bac, 3)
    conn = _conn(bac)
    rapport = calendar.planifier(conn, semaines=3, racine=bac,
                                 maintenant=datetime(2026, 9, 23, 12, tzinfo=UTC))
    assert rapport.durees_ajustees, "des cibles identiques auraient dû être écartées"
    assert not [a for a in rapport.avertissements if "écart" in a]
    conn.close()


def test_check_detecte_les_violations(bac: Path) -> None:
    ctx = calendar.contexte(bac)
    t = datetime(2026, 10, 3, 21, 10, tzinfo=UTC)
    E = calendar.Evenement
    evts = [E("a", "bms-science-en", t, "queued"),
            E("b", "bms-histoire-en", t + timedelta(minutes=20), "queued"),
            E("c", "bms-science-en", t + timedelta(hours=20), "queued"),
            E("d", "bms-histoire-en", t + timedelta(hours=2), "queued")]
    regles = {v.regle for v in calendar.verifier(ctx, evts, t - timedelta(days=5))[0]}
    assert {"espacement_chaine", "exclusion_portefeuille", "meme_heure",
            "max_par_24h", "ecart_meme_langue"} <= regles


def test_plafond_selon_age(bac: Path) -> None:
    ctx = calendar.contexte(bac)
    chaine = ctx.chaines["bms-science-en"]
    assert calendar.plafond_semaine(ctx, chaine, datetime(2026, 10, 1).date()) == 2
    assert chaine.cadence.created_at is None


def test_exporte_sans_relecture_non_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    construire_bac(tmp_path, relecture=False)
    conn = _conn(tmp_path)
    conn.execute("INSERT INTO jobs (video_id, channel_id, stage, status, created_at, updated_at)"
                 " VALUES (?, 'bms-science-en', 'qc', 'exported', ?, ?)",
                 (RUN, "2026-09-20T00:00:00Z", "2026-09-20T00:00:00Z"))
    conn.commit()
    rapport = calendar.planifier(conn, semaines=3, racine=tmp_path)
    assert not rapport.decisions and "review_log" in rapport.ecartes[0].raison
    conn.close()


def test_daemon_bloque_sur_precheck(bac: Path) -> None:
    meta = bac / "workspace" / "runs" / RUN / "metadata.json"
    donnees = json.loads(meta.read_text())
    donnees["default_language"] = "fr"
    meta.write_text(json.dumps(donnees, ensure_ascii=False))
    conn = _conn(bac)
    maintenant = datetime.now(UTC)
    conn.execute("INSERT INTO jobs (video_id, channel_id, stage, status, created_at, updated_at,"
                 " publish_at) VALUES (?, 'bms-science-en', 'qc', 'exported', ?, ?, ?)",
                 (RUN, "2026-09-20T00:00:00Z", "2026-09-20T00:00:00Z",
                  calendar._iso(maintenant + timedelta(hours=10))))
    conn.commit()
    faits = calendar.publier_echeances(conn, racine=bac, maintenant=maintenant)
    assert faits == [f"{RUN} bloqué par precheck"]
    ligne = conn.execute("SELECT status, last_error FROM jobs").fetchone()
    assert ligne["status"] == "blocked" and "langue_categorie" in ligne["last_error"]
    conn.close()


# --------------------------------------------------------------------------------------
# Corrections issues du contradicteur
# --------------------------------------------------------------------------------------


def test_date_depassee_est_une_violation(bac: Path) -> None:
    ctx = calendar.contexte(bac)
    t = datetime(2026, 10, 3, 21, 10, tzinfo=UTC)
    evts = [calendar.Evenement("a", "bms-science-en", t, "exported")]
    regles = {v.regle for v in calendar.verifier(ctx, evts, t + timedelta(hours=1))[0]}
    assert regles == {"date_depassee"}


def test_dates_dans_l_ordre_de_production(bac: Path) -> None:
    ids = _jobs(bac, 3)
    conn = _conn(bac)
    calendar.planifier(conn, semaines=3, racine=bac,
                       maintenant=datetime(2026, 9, 23, 12, tzinfo=UTC))
    dates = {l["video_id"]: l["publish_at"] for l in conn.execute(
        "SELECT video_id, publish_at FROM jobs")}
    for cid in ("bms-science-en", "bms-histoire-en"):
        siens = [dates[v] for v in ids if v.startswith(cid)]
        assert siens == sorted(siens), f"{cid} : {siens}"
    conn.close()


def test_daemon_ne_rattrape_pas_et_n_envoie_qu_un_upload(bac: Path, monkeypatch) -> None:
    from factory.publish import youtube

    envoyes: list[str] = []
    monkeypatch.setattr(youtube, "precheck", lambda *a, **k: [])
    monkeypatch.setattr(youtube, "publier_run", lambda vid, *a, **k: envoyes.append(vid))
    conn = _conn(bac)
    maintenant = datetime(2026, 10, 1, 12, tzinfo=UTC)
    for vid, h in (("passe-aaaa", -5), ("du-bbbb", 11), ("du-cccc", 11.5)):
        conn.execute("INSERT INTO jobs (video_id, channel_id, stage, status, created_at, "
                     "updated_at, publish_at) VALUES (?, 'bms-science-en', 'qc', 'exported', "
                     "?, ?, ?)", (vid, "2026-09-20T00:00:00Z", "2026-09-20T00:00:00Z",
                                  calendar._iso(maintenant + timedelta(hours=h))))
    conn.commit()
    calendar.publier_echeances(conn, racine=bac, maintenant=maintenant)
    assert envoyes == ["du-bbbb"], "une seule vidéo par tour, jamais la date passée"
    conn.close()
