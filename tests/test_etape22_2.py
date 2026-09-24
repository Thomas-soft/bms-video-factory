"""Étape 22.2 — relecture par lots, régénération ciblée, alertes et digest.

Ce que ces tests éprouvent, et ce qu'ils n'éprouvent pas.

**Éprouvé ici, sans production :** ce qu'une décision de relecture écrit et où, ce qu'un
rejet fait au prompt du modèle, ce qu'un script édité hors cadre ne peut pas faire, quel
remède le banc déclenche pour quelle mesure, ce qu'une reprise invalide et ce qu'elle
préserve, combien de reprises avant `blocked`, et que jamais un jeton ne sorte dans une
alerte. Les étapes du DAG sont des faux sous-processus dont on choisit le code de retour.

**Éprouvé hors d'ici :** la régénération sur une vraie vidéo, mesurée par `ffmpeg` — voir
`STATE.md` et le journal de l'étape.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from factory.core import db
from factory.core.models import OrchestratorConfig, Remede
from factory.core.paths import RunPaths, assets_exclus
from factory.orchestrator import journal, notify, regenerate
from factory.orchestrator import queue as file_module
from factory.orchestrator import review, runner

# --------------------------------------------------------------------------------------
# Dépôt jetable
# --------------------------------------------------------------------------------------


@pytest.fixture
def racine(tmp_path: Path) -> Path:
    """Un dépôt jetable avec la vraie `config/` recopiée."""
    import shutil

    from factory.core.paths import racine_projet as vraie_racine

    for nom in ("workspace/runs", "workspace/logs", "config", "docs", "registre/data",
                "reports"):
        (tmp_path / nom).mkdir(parents=True, exist_ok=True)
    source = vraie_racine() / "config"
    for nom in ("languages", "niches", "styles", "channels", "products"):
        shutil.copytree(source / nom, tmp_path / "config" / nom, dirs_exist_ok=True)
    for nom in ("team.yaml", "qc.yaml", "editorial.yaml", "economics.yaml",
                "orchestrator.yaml"):
        shutil.copy2(source / nom, tmp_path / "config" / nom)
    return tmp_path


@pytest.fixture
def conn(racine: Path) -> sqlite3.Connection:
    """Base migrée du dépôt jetable."""
    connexion = db.ouvrir(racine / "workspace" / "factory.db")
    yield connexion
    connexion.close()


def _auto_approve(racine: Path, valeur: bool) -> None:
    """Bascule `auto_approve` de `bms-science-en`."""
    fichier = racine / "config" / "channels" / "bms-science-en.yaml"
    texte = fichier.read_text(encoding="utf-8")
    fichier.write_text(texte.replace("auto_approve: false", f"auto_approve: {str(valeur).lower()}")
                       .replace("auto_approve: true", f"auto_approve: {str(valeur).lower()}"),
                       encoding="utf-8")


SCRIPT_MINIMAL = {
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

SPEC_MINIMALE = {
    "schema_version": "1.0", "video_id": "bms-science-en-20260922-aaaa", "parent_id": None,
    "channel_id": "bms-science-en", "lang": "en", "niche": "science_pop", "style": "illustre",
    "topic": {"sujet": "Why neutron stars spin", "angle": "comparatif_chiffre — a teaspoon",
              "source": "topics_queue",
              "evidence": {"score": 0.8, "ratio": 1.4, "n": 2, "requete": "test"}},
    "target_duration_s": 660, "cut_rhythm_target_s": 5.7, "seed": 12345, "product_id": None,
    "created_at": "2026-09-22T09:00:00Z",
}

MANIFEST_MINIMAL = {
    "schema_version": "1.0",
    "identite": {"video_id": "bms-science-en-20260922-aaaa", "parent_id": None,
                 "channel_id": "bms-science-en", "lang": "en", "niche": "science_pop",
                 "style": "illustre", "template_id": "sci-a", "charte_version": "2026.09.1"},
    "decisions": {"topic": SPEC_MINIMALE["topic"], "hook_type": "contre_intuitif",
                  "cut_rhythm_target_s": 5.7, "voice_id": "af_heart",
                  "title_chosen": "Why neutron stars spin faster than anything",
                  "density_facts_per_min": 3.4},
    "execution": {"timings": {}},
}

#: Identifiants de run conformes au motif d'`INTERFACES` — quatre caractères de l'alphabet
#: sans ambiguïté visuelle. Les tests en nomment trois.
R1 = "bms-science-en-20260922-aaaa"
R2 = "bms-science-en-20260922-bbbb"
R3 = "bms-science-en-20260922-cccc"


def _run(racine: Path, video_id: str = R1) -> RunPaths:
    """Un dossier de run complet : spec, manifeste, script valides."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    chemins.racine.mkdir(parents=True, exist_ok=True)
    spec = {**SPEC_MINIMALE, "video_id": video_id}
    manifest = json.loads(json.dumps(MANIFEST_MINIMAL))
    manifest["identite"]["video_id"] = video_id
    chemins.spec.write_text(json.dumps(spec), encoding="utf-8")
    chemins.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    chemins.script.write_text(json.dumps(SCRIPT_MINIMAL), encoding="utf-8")
    return chemins


def _job(conn: sqlite3.Connection, racine: Path, video_id: str, stage: str = "voice",
         statut: str = "awaiting_review"):
    """Un run en base et un job à l'état voulu."""
    quand = file_module.maintenant()
    conn.execute(
        "INSERT OR REPLACE INTO runs (video_id, channel_id, lang, created_at, updated_at) "
        "VALUES (?, 'bms-science-en', 'en', ?, ?)", (video_id, quand, quand))
    job = file_module.enfiler(conn, video_id, "bms-science-en", stage=stage, racine=racine)
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (statut, job.id))
    return file_module.lire(conn, job.id)


def _qc(chemins: RunPaths, mesures: dict, verdict_pipeline: str = "regenerate",
        etapes: list[str] | None = None) -> None:
    """Écrit un `qc.json` avec les mesures voulues, aux noms de champs réels du banc."""
    chemins.qc.write_text(json.dumps({
        "schema_version": "1.0", "version": "qc/1.1.0", "run": chemins.video_id,
        "score": 62.0, "verdict": "FAIL", "reasons": ["banc en échec"],
        "metrics": mesures, "verdict_pipeline": verdict_pipeline,
        "regenerate_steps": etapes or [],
    }), encoding="utf-8")


def _mesure(valeur, cible, statut="fail", bloquant=False, unite="", note=""):
    """Une mesure de `qc.json`, aux noms de champs d'`INTERFACES` § qc.json."""
    return {"value": valeur, "target": cible, "status": statut, "blocking": bloquant,
            "unit": unite, "note": note, "score": 0.0, "weight": 1}


# --------------------------------------------------------------------------------------
# 1 — La trace de relecture : ce que la conformité exige
# --------------------------------------------------------------------------------------


def test_migration_008_garde_lhistoire_dune_relecture(conn: sqlite3.Connection,
                                                      racine: Path) -> None:
    """Rejeter puis approuver le même texte laisse **deux** lignes, pas une.

    C'est tout l'objet de la migration : avec `review_hash` en clé primaire, la seconde
    décision écrasait la première et le rejet disparaissait de la pièce. Or c'est
    l'enchaînement « rejeté → corrigé → approuvé » qui démontre le contrôle éditorial du
    RIA art. 50 §4.
    """
    # `table_xinfo` et non `table_info` : les colonnes générées n'apparaissent que là.
    colonnes = {l["name"] for l in conn.execute("PRAGMA table_xinfo(review_log)")}
    assert {"motif", "script_sha256", "timestamp", "review_hash", "review_date"} <= colonnes
    _run(racine, R1)
    review.enregistrer_decision(conn, R1, "bms-science-en", reviewer="thomas",
                                decision="rejected", motif="hook faible", racine=racine)
    review.enregistrer_decision(conn, R1, "bms-science-en", reviewer="thomas",
                                decision="approved", racine=racine)
    lignes = review.relectures(conn, R1)
    assert [l["decision"] for l in lignes] == ["rejected", "approved"]
    # Les deux noms de colonnes désignent la même valeur : un seul stockage, deux lecteurs.
    assert lignes[0]["review_hash"] == lignes[0]["script_sha256"]
    assert lignes[0]["review_date"] == lignes[0]["timestamp"]


def test_une_decision_ecrit_les_quatre_pieces(conn: sqlite3.Connection, racine: Path) -> None:
    """`reviews.jsonl`, `review_log`, `review.json` et le manifeste, d'un seul geste."""
    chemins = _run(racine, R1)
    empreinte = review.enregistrer_decision(conn, R1, "bms-science-en", reviewer="alek",
                                            decision="approved", racine=racine)
    assert empreinte == review.empreinte_script(chemins)

    pieces = review.chemin_reviews_jsonl(racine).read_text(encoding="utf-8").splitlines()
    ligne = json.loads(pieces[-1])
    assert ligne["reviewer"] == "alek" and ligne["review_hash"] == empreinte
    assert ligne["run_id"] == R1 and ligne["decision"] == "approved"

    index = review.relectures(conn, R1)[-1]
    assert index["reviewer"] == "alek" and index["script_sha256"] == empreinte

    miroir = json.loads(chemins.review.read_text(encoding="utf-8"))
    assert miroir["reviewer"] == "alek" and miroir["ria_exception_claimed"] is True

    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    assert manifeste["conformite"]["reviewer"] == "alek"
    assert manifeste["conformite"]["review_hash"] == empreinte
    assert manifeste["conformite"]["review_decision"] == "approved"


def test_la_piece_est_append_only(conn: sqlite3.Connection, racine: Path) -> None:
    """`reviews.jsonl` ne perd jamais une ligne — `CONFORMITE` § 10.2, sans exception."""
    _run(racine, R1)
    for i in range(3):
        review.enregistrer_decision(conn, R1, "bms-science-en", reviewer="thomas",
                                    decision="rejected", motif=f"motif {i}", racine=racine)
    lignes = review.chemin_reviews_jsonl(racine).read_text(encoding="utf-8").strip().splitlines()
    assert len(lignes) == 3
    assert [json.loads(l)["comment"] for l in lignes] == ["motif 0", "motif 1", "motif 2"]


def test_relecteur_inconnu_refuse(racine: Path) -> None:
    """« L'équipe » n'est pas une réponse valable, et le message le dit."""
    with pytest.raises(file_module.ErreurFile, match="relecteur inconnu"):
        review.verifier_relecteur("equipe", racine)
    assert review.verifier_relecteur("THOMAS", racine) == "Thomas"


def test_auto_ne_revendique_pas_lexception_ria(conn: sqlite3.Connection,
                                               racine: Path) -> None:
    """`reviewer = auto` écrit `ria_exception_claimed = false`, en base comme au manifeste."""
    chemins = _run(racine, R1)
    review.enregistrer_decision(conn, R1, "bms-science-en", reviewer="auto",
                                decision="auto_approved", motif="auto_approve actif",
                                racine=racine)
    assert json.loads(chemins.review.read_text(encoding="utf-8"))["ria_exception_claimed"] is False
    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    assert manifeste["conformite"]["ria_exception_claimed"] is False
    assert manifeste["conformite"]["review_decision"] == "auto"


def test_auto_refuse_si_la_chaine_ne_la_pas_acte(conn: sqlite3.Connection,
                                                 racine: Path) -> None:
    """`--auto` sur une chaîne à `auto_approve: false` est refusé, avec le motif complet."""
    _auto_approve(racine, False)
    _run(racine, R1)
    _job(conn, racine, R1)
    with pytest.raises(file_module.ErreurFile, match="auto_approve.*false|RIA"):
        review.auto_approuver(conn, "bms-science-en", racine=racine)
    assert review.relectures(conn, R1) == []


def test_auto_leve_quand_la_chaine_la_acte(conn: sqlite3.Connection, racine: Path) -> None:
    """`auto_approve: true` lève le lot et laisse la trace « aucun humain n'a lu »."""
    _auto_approve(racine, True)
    _run(racine, R1)
    job = _job(conn, racine, R1)
    liberes = review.auto_approuver(conn, "bms-science-en", racine=racine)
    assert [j.id for j in liberes] == [job.id]
    assert file_module.lire(conn, job.id).status == "queued"
    ligne = review.relectures(conn, R1)[-1]
    assert ligne["reviewer"] == "auto" and ligne["decision"] == "auto_approved"
    alerte = [e for e in journal.lire_events(racine) if e["level"] == "WARN"][-1]
    assert "SANS LECTURE" in alerte["msg"]


# --------------------------------------------------------------------------------------
# 2 — Les quatre décisions
# --------------------------------------------------------------------------------------


def test_approuver_libere_le_job_a_son_etape(conn: sqlite3.Connection, racine: Path) -> None:
    """Approuver rend le job à la file **à l'étape où la barrière l'a arrêté**."""
    _auto_approve(racine, False)
    chemins = _run(racine, R1)
    job = _job(conn, racine, R1, stage="voice")
    fiche = review.apercu(conn, job, racine)
    libere = review.approuver(conn, fiche, "thomas", racine=racine)
    assert libere.status == "queued" and libere.stage == "voice"
    assert runner._script_relu(conn, libere, chemins)


def test_rejeter_reecrit_le_script_et_verse_le_motif_au_prompt(
        conn: sqlite3.Connection, racine: Path) -> None:
    """Le rejet ramène le job à `script`, efface l'aval, et le motif atteint le modèle.

    Sans la consigne, la réécriture redemanderait au modèle exactement ce qu'il vient
    d'écrire : le rejet coûterait quinze minutes de LLM pour rien.
    """
    _auto_approve(racine, False)
    chemins = _run(racine, R1)
    chemins.done_dir.mkdir(parents=True, exist_ok=True)
    for etape in ("research", "script", "voice"):
        chemins.done(etape).write_text("{}", encoding="utf-8")
    job = _job(conn, racine, R1, stage="voice")
    fiche = review.apercu(conn, job, racine)
    apres = review.rejeter(conn, fiche, "sofiane", "le hook promet un chiffre qu'il ne donne pas",
                           racine=racine)
    assert apres.status == "queued" and apres.stage == "script"
    # L'amont est préservé, l'étape fautive et l'aval sont à refaire.
    assert chemins.done("research").exists()
    assert not chemins.done("script").exists() and not chemins.done("voice").exists()
    bloc = review.bloc_consignes(chemins)
    assert "ne donne pas" in bloc and "MANDATORY CORRECTIONS" in bloc
    assert review.relectures(conn, R1)[-1]["motif"].startswith("le hook promet")


def test_rejeter_sans_motif_refuse(conn: sqlite3.Connection, racine: Path) -> None:
    """Un rejet qui ne dit pas quoi réécrire n'est pas une décision."""
    _auto_approve(racine, False)
    _run(racine, R1)
    job = _job(conn, racine, R1)
    fiche = review.apercu(conn, job, racine)
    with pytest.raises(file_module.ErreurFile, match="motif"):
        review.rejeter(conn, fiche, "thomas", "   ", racine=racine)


def test_troisieme_rejet_bloque_au_lieu_de_reecrire(conn: sqlite3.Connection,
                                                    racine: Path) -> None:
    """Deux rejets, puis `blocked` : la machine ne réécrit pas indéfiniment."""
    _auto_approve(racine, False)
    _run(racine, R1)
    job = _job(conn, racine, R1)
    for rang in range(3):
        conn.execute("UPDATE jobs SET status = 'awaiting_review' WHERE id = ?", (job.id,))
        fiche = review.apercu(conn, file_module.lire(conn, job.id), racine)
        etat = review.rejeter(conn, fiche, "alek", f"motif {rang}", racine=racine, rejets_max=2)
    assert etat.status == "blocked"
    assert "rejeté 3 fois" in (etat.last_error or "")
    # Les trois décisions sont dans la pièce : la troisième aussi, même si elle bloque.
    assert len(review.relectures(conn, R1)) == 3


def test_editer_refuse_un_script_invalide_et_restaure(conn: sqlite3.Connection,
                                                      racine: Path) -> None:
    """Un script édité que pydantic refuse est **restauré**, et aucune décision n'est écrite.

    L'édition humaine ne doit pas devenir une porte dérobée autour du seul contrôle
    automatique du texte.
    """
    _auto_approve(racine, False)
    chemins = _run(racine, R1)
    avant = chemins.script.read_bytes()
    job = _job(conn, racine, R1)
    fiche = review.apercu(conn, job, racine)

    def _casser(_commande: list[str]) -> int:
        chemins.script.write_text('{"lang": "en"}', encoding="utf-8")
        return 0

    with pytest.raises(file_module.ErreurFile, match="pydantic"):
        review.editer(conn, fiche, "thomas", racine=racine, ouvrir=_casser)
    assert chemins.script.read_bytes() == avant
    assert review.relectures(conn, R1) == []
    assert file_module.lire(conn, job.id).status == "awaiting_review"


def test_editer_valide_ecrit_approved_with_edits(conn: sqlite3.Connection,
                                                 racine: Path) -> None:
    """Un script édité et valide passe en `approved_with_edits`, l'aval invalidé."""
    _auto_approve(racine, False)
    chemins = _run(racine, R1)
    chemins.done_dir.mkdir(parents=True, exist_ok=True)
    for etape in ("script", "voice"):
        chemins.done(etape).write_text("{}", encoding="utf-8")
    job = _job(conn, racine, R1)
    fiche = review.apercu(conn, job, racine)

    def _editer(_commande: list[str]) -> int:
        charge = json.loads(chemins.script.read_text(encoding="utf-8"))
        charge["segments"][1]["narration"] = "A teaspoon of it weighs a billion tons."
        chemins.script.write_text(json.dumps(charge), encoding="utf-8")
        return 0

    apres, _alertes = review.editer(conn, fiche, "thomas", racine=racine, ouvrir=_editer)
    assert apres.status == "queued"
    ligne = review.relectures(conn, R1)[-1]
    assert ligne["decision"] == "approved_with_edits"
    # Le texte a changé : `script` reste fait, la voix est à refaire.
    assert chemins.done("script").exists() and not chemins.done("voice").exists()
    assert ligne["script_sha256"] == review.empreinte_script(chemins)


def test_passer_necrit_rien(conn: sqlite3.Connection, racine: Path) -> None:
    """« Je verrai demain » n'est pas une décision : `review_log` reste vide."""
    _auto_approve(racine, False)
    _run(racine, R1)
    job = _job(conn, racine, R1)
    bilan = review.relire(conn, "thomas", racine=racine, demander=lambda _f: ("s", ""))
    assert bilan.passes == [R1] and bilan.decisions == 0
    assert review.relectures(conn, R1) == []
    assert file_module.lire(conn, job.id).status == "awaiting_review"


def test_relire_un_lot_enchaine_les_decisions(conn: sqlite3.Connection, racine: Path) -> None:
    """Trois scripts, trois touches, trois états — c'est la promesse « dix en quinze min »."""
    _auto_approve(racine, False)
    reponses = {R1: ("a", ""), R2: ("r", "hook creux"), R3: ("s", "")}
    for nom in (R1, R2, R3):
        _run(racine, nom)
        _job(conn, racine, nom)
    bilan = review.relire(conn, "alek", racine=racine,
                          demander=lambda f: reponses[f.job.video_id])
    assert bilan.approuves == [R1] and bilan.rejetes == [R2] and bilan.passes == [R3]
    assert bilan.batch_id.startswith("alek-")
    assert {l["batch_id"] for l in review.relectures(conn, R1)} == {bilan.batch_id}


def test_apercu_donne_ce_qui_se_juge_en_trente_secondes(conn: sqlite3.Connection,
                                                        racine: Path) -> None:
    """Titre, chaîne, sujet, angle, type de hook, hook, durée, densité, trois lignes."""
    _auto_approve(racine, False)
    _run(racine, R1)
    job = _job(conn, racine, R1)
    fiche = review.apercu(conn, job, racine)
    assert fiche.titre == MANIFEST_MINIMAL["decisions"]["title_chosen"]
    assert fiche.hook_type == "contre_intuitif" and fiche.angle == "comparaison_chiffree"
    assert fiche.densite == 3.4 and fiche.duree_cible_s == 660
    assert fiche.ecart_duree == "-9 %"
    assert len(fiche.premieres_lignes) == 3 and "teaspoon" in fiche.premieres_lignes[0]
    texte = review.texte_apercu(fiche, 1, 1)
    assert "contre_intuitif" in texte and "comparaison_chiffree" in texte


def test_un_job_sans_script_nest_pas_une_relecture(conn: sqlite3.Connection,
                                                   racine: Path) -> None:
    """Un `awaiting_review` venu d'un code 7 d'une autre étape n'encombre pas la file."""
    _auto_approve(racine, False)
    chemins = _run(racine, R1)
    chemins.script.unlink()
    _job(conn, racine, R1)
    assert review.en_attente(conn, None, racine) == []


# --------------------------------------------------------------------------------------
# 3 — La régénération
# --------------------------------------------------------------------------------------


def test_lecture_du_banc_nomme_les_mesures_en_echec(racine: Path) -> None:
    """`lire_qc` lit les noms de champs réels du banc, pas des noms inventés."""
    chemins = _run(racine, R1)
    _qc(chemins, {
        "loudness": _mesure(-24.0, -14.0, bloquant=True, unite="LUFS"),
        "cut_rhythm": _mesure(9.1, 5.7, unite="s"),
        "hook_length": _mesure(12, 14, statut="pass"),
    })
    diagnostic = regenerate.lire_qc(R1, racine)
    assert [m.nom for m in diagnostic.echecs] == ["loudness", "cut_rhythm"]
    assert diagnostic.echecs[0].bloquante is True
    assert "loudness = -24.0 LUFS" in str(diagnostic.echecs[0])


@pytest.mark.parametrize(("mesure", "etape", "levier"), [
    ("cut_rhythm", "shotlist", "graine_suivante"),
    ("hook_length", "script", "hook_seul"),
    ("loudness", "assemble", "aucun"),
    ("duree_vs_run", "script", "consigne"),
    ("text_size", "render", "gabarit_suivant"),
    ("visual_variety", "shotlist", "assets_differents"),
])
def test_la_table_des_remedes_suit_le_prompt(racine: Path, mesure: str, etape: str,
                                             levier: str) -> None:
    """Les six remèdes nommés par l'étape 22.2, tels que `config/orchestrator.yaml` les pose."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    _qc(chemins, {mesure: _mesure(1.0, 2.0)})
    plan = regenerate.choisir(regenerate.lire_qc(R1, racine), cfg)
    assert plan is not None and plan.depuis == etape and plan.remede.levier == levier


def test_le_remede_le_moins_cher_gagne(racine: Path) -> None:
    """Deux défauts, deux remèdes : on rejoue le plus tardif — 4 min plutôt que 4 h."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    _qc(chemins, {"duree_vs_run": _mesure(900, 660, unite="s"),
                  "loudness": _mesure(-24.0, -14.0, bloquant=True, unite="LUFS")})
    plan = regenerate.choisir(regenerate.lire_qc(R1, racine), cfg)
    assert plan.depuis == "assemble"


def test_un_remede_deja_tente_nest_pas_rejoue(racine: Path) -> None:
    """Deux tentatives, pas deux fois la même : le second remède est un autre."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    _qc(chemins, {"duree_vs_run": _mesure(900, 660), "loudness": _mesure(-24.0, -14.0)})
    diagnostic = regenerate.lire_qc(R1, racine)
    assert regenerate.choisir(diagnostic, cfg, {("loudness", "assemble")}).depuis == "script"
    assert regenerate.choisir(diagnostic, cfg,
                              {("loudness", "assemble"), ("duree_vs_run", "script")}) is None


def test_le_levier_de_graine_change_vraiment_la_graine(racine: Path) -> None:
    """« Rejouer sans rien changer » ne corrige rien : la graine bouge, et on le prouve."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    _qc(chemins, {"cut_rhythm": _mesure(9.1, 5.7)})
    plan = regenerate.choisir(regenerate.lire_qc(R1, racine), cfg)
    avant = json.loads(chemins.spec.read_text(encoding="utf-8"))["seed"]
    description, donnees = regenerate.appliquer_levier(plan, R1, racine, 1)
    apres = json.loads(chemins.spec.read_text(encoding="utf-8"))["seed"]
    assert apres != avant and donnees["seed_apres"] == apres
    assert str(avant) in description


def test_le_levier_de_gabarit_passe_au_suivant(racine: Path) -> None:
    """Lisibilité insuffisante → gabarit de composition suivant de la chaîne."""
    from factory.core import config as config_module

    cfg_set = config_module.charger(racine, strict=False)
    chaine = cfg_set.channels["bms-science-en"]
    chemins = _run(racine, R1)
    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    manifeste["identite"]["template_id"] = chaine.templates[0]
    chemins.manifest.write_text(json.dumps(manifeste), encoding="utf-8")
    _qc(chemins, {"text_size": _mesure(18, 32, unite="px")})
    plan = regenerate.choisir(regenerate.lire_qc(R1, racine), cfg_set.orchestrator)
    _description, donnees = regenerate.appliquer_levier(plan, R1, racine, 1)
    assert donnees["template_apres"] == chaine.templates[1]
    apres = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    assert apres["identite"]["template_id"] == chaine.templates[1]


def test_le_levier_dassets_interdit_ceux_du_run(racine: Path) -> None:
    """Variété faible → les assets déjà employés sont refusés à la reprise.

    Sans ce fichier, `_reutilisable` autoriserait le rejeu du même run à reprendre les mêmes
    images (objection 18 d'`INTERFACES`), et la variété ne bougerait pas d'un point.
    """
    chemins = _run(racine, R1)
    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    manifeste["decisions"]["assets"] = [
        {"schema_version": "1.0", "asset_id": "a1b2c3d4e5f60718", "path": "assets/shot_00/image.png",
         "provider": "flux", "source_url": None, "author": "BMS (généré)",
         "licence": "Apache-2.0", "licence_url": "https://www.apache.org/licenses/LICENSE-2.0",
         "attribution_line": None, "downloaded_at": "2026-09-22T10:00:00Z",
         "person_release": None,
         "generator": {"model": "mlx-community/FLUX.2-Klein-4B-4bit", "model_revision": None,
                       "prompt_hash": "0" * 64, "seed": 1, "steps": 4,
                       "resolution": "1280x720"},
         "realistic": False, "has_text": False, "c2pa_present": False},
    ]
    chemins.manifest.write_text(json.dumps(manifeste), encoding="utf-8")
    plan = regenerate.Plan(depuis="shotlist", mesure="visual_variety",
                           remede=Remede(depuis="shotlist", levier="assets_differents"),
                           explication="")
    _description, donnees = regenerate.appliquer_levier(plan, R1, racine, 1)
    assert donnees["assets_exclus"] == 1
    assert assets_exclus(R1, racine) == {"a1b2c3d4e5f60718"}


def test_la_regeneration_ninvalide_que_letape_fautive_et_laval(
        conn: sqlite3.Connection, racine: Path) -> None:
    """La contrainte du prompt, vérifiée marqueur par marqueur."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    chemins.done_dir.mkdir(parents=True, exist_ok=True)
    for etape in file_module.ETAPES:
        chemins.done(etape).write_text("{}", encoding="utf-8")
    _qc(chemins, {"loudness": _mesure(-24.0, -14.0, unite="LUFS")})
    job = _job(conn, racine, R1, stage="qc", statut="running")
    decision = regenerate.decider(conn, job, cfg, racine=racine)
    assert decision.action == "regenerate" and decision.depuis == "assemble"
    for amont in ("script", "voice", "subtitles", "shotlist", "render"):
        assert chemins.done(amont).exists(), f"{amont} ne devait pas être invalidée"
    for aval in ("assemble", "thumbnail", "metadata", "export"):
        assert not chemins.done(aval).exists(), f"{aval} devait être invalidée"


def test_deux_regenerations_puis_blocked_avec_les_metriques(
        conn: sqlite3.Connection, racine: Path) -> None:
    """Au troisième refus du banc, le job bloque — et la raison porte les chiffres."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    _qc(chemins, {"loudness": _mesure(-24.0, -14.0, unite="LUFS", note="bornes [-16, -12]"),
                  "duree_vs_run": _mesure(900, 660, unite="s")})
    job = _job(conn, racine, R1, stage="qc", statut="running")

    premiere = regenerate.decider(conn, job, cfg, racine=racine)
    assert premiere.action == "regenerate" and premiere.rang == 1
    deuxieme = regenerate.decider(conn, job, cfg, racine=racine)
    assert deuxieme.action == "regenerate" and deuxieme.rang == 2
    assert deuxieme.depuis != premiere.depuis
    troisieme = regenerate.decider(conn, job, cfg, racine=racine)
    assert troisieme.action == "blocked"
    raison = regenerate.raison_lisible(troisieme)
    assert "loudness = -24.0 LUFS" in raison and "bornes [-16, -12]" in raison
    assert "plafond 2" in raison

    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    entrees = manifeste["execution"]["regenerations"]
    assert [e["rang"] for e in entrees] == [1, 2]
    assert entrees[0]["mesure"] == "loudness" and entrees[0]["depuis"] == "assemble"


def test_un_bloquant_sans_remede_bloque_tout_de_suite(conn: sqlite3.Connection,
                                                      racine: Path) -> None:
    """`verdict_pipeline: blocked` sur un contrôle **absent de la table** bloque sans reprise.

    `subtitle_track` porte `verdict_fail: blocked` dans `config/qc.yaml` et n'a pas de
    remède : rejouer dépenserait le remontage pour se faire refuser par le même contrôle.
    """
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    cfg = cfg.model_copy(update={"remedes": {}})
    chemins = _run(racine, R1)
    _qc(chemins, {"loudness": _mesure(-24.0, -14.0, bloquant=True)},
        verdict_pipeline="blocked")
    job = _job(conn, racine, R1, stage="qc", statut="running")
    decision = regenerate.decider(conn, job, cfg, racine=racine)
    assert decision.action == "blocked" and "bloquant" in decision.raison
    assert regenerate.regenerations_faites(R1, racine) == []


def test_un_bloquant_remediable_a_droit_a_une_tentative(conn: sqlite3.Connection,
                                                        racine: Path) -> None:
    """`loudness` est bloquant **et** porte un remède : on tente une fois, puis on mesure.

    Deux documents se contredisaient — `QC.md` § 4 fait de `loudness` un bloquant sans
    reprise, le prompt de l'étape 22.2 demande « loudness → assemble ». Un niveau sonore
    hors norme est tantôt un montage interrompu (198 s de remontage), tantôt un défaut de
    fond (la reprise échoue et le job bloque). `remedes_sur_bloquant` tranche en mesurant.
    """
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    assert cfg.remedes_sur_bloquant is True
    chemins = _run(racine, R1)
    _qc(chemins, {"loudness": _mesure(-24.0, -14.0, bloquant=True, unite="LUFS")},
        verdict_pipeline="blocked")
    job = _job(conn, racine, R1, stage="qc", statut="running")
    decision = regenerate.decider(conn, job, cfg, racine=racine)
    assert decision.action == "regenerate" and decision.depuis == "assemble"
    # Coupé, le même cas bloque : c'est bien l'option qui décide, pas le hasard.
    prudent = cfg.model_copy(update={"remedes_sur_bloquant": False})
    assert regenerate.decider(conn, job, prudent, racine=racine).action == "blocked"


def test_un_echec_de_plancher_de_famille_se_regenere_quand_meme(racine: Path) -> None:
    """Le banc sait refuser sans qu'aucune mesure soit `fail` : `regenerate_steps` prend la main."""
    from factory.core import config as config_module

    cfg = config_module.charger(racine, strict=False).orchestrator
    chemins = _run(racine, R1)
    _qc(chemins, {"loudness": _mesure(-14.0, -14.0, statut="pass")},
        etapes=["script", "voice", "assemble"])
    plan = regenerate.choisir(regenerate.lire_qc(R1, racine), cfg)
    assert plan is not None and plan.depuis == "assemble" and plan.mesure == ""


# --------------------------------------------------------------------------------------
# 4 — Intégration dans le runner
# --------------------------------------------------------------------------------------


def test_le_runner_rejoue_letape_fautive_puis_repasse_le_banc(
        conn: sqlite3.Connection, racine: Path, monkeypatch) -> None:
    """qc FAIL → remède → étapes rejouées → qc PASS → `exported`, en un seul tour."""
    _auto_approve(racine, True)
    chemins = _run(racine, R1)
    _qc(chemins, {"loudness": _mesure(-24.0, -14.0, unite="LUFS")})
    job = _job(conn, racine, R1, stage="assemble", statut="queued")
    monkeypatch.setattr(runner, "gardes_fous", lambda *_a, **_k: [])
    monkeypatch.setattr(runner, "_finaliser", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "_timing", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "marquer", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "etape_faite", lambda *_a, **_k: False)
    monkeypatch.setattr(runner, "_alerter", lambda *_a, **_k: None)
    lancees: list[str] = []

    def _executer(etape, *_a, **_k):
        lancees.append(etape)
        if etape == "qc":
            # Le premier passage refuse, le second accepte : le remède a servi.
            if lancees.count("qc") == 1:
                return runner.CODE_QUALITE, 0.1, "loudness hors norme"
            _qc(chemins, {"loudness": _mesure(-14.0, -14.0, statut="pass")},
                verdict_pipeline="pass")
            return 0, 0.1, ""
        return 0, 0.1, ""

    monkeypatch.setattr(runner.run_module, "executer_etape", _executer)
    resultat = runner.executer_job(conn, job, runner._config(racine), racine=racine,
                                   respecter_fenetre=False)
    assert resultat.statut == "exported"
    # `assemble` a bien été rejoué après le FAIL, et pas `script`.
    assert lancees.count("assemble") == 2 and "script" not in lancees
    assert len(resultat.regenerations) == 1
    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    assert manifeste["execution"]["regenerations"][-1]["resultat"] == "pass"


def test_le_runner_bloque_apres_deux_regenerations(conn: sqlite3.Connection, racine: Path,
                                                   monkeypatch) -> None:
    """Le banc refuse trois fois : `blocked`, avec les métriques, et une alerte part."""
    _auto_approve(racine, True)
    chemins = _run(racine, R1)
    _qc(chemins, {"loudness": _mesure(-24.0, -14.0, unite="LUFS"),
                  "duree_vs_run": _mesure(900, 660, unite="s")})
    job = _job(conn, racine, R1, stage="assemble", statut="queued")
    monkeypatch.setattr(runner, "gardes_fous", lambda *_a, **_k: [])
    monkeypatch.setattr(runner, "_finaliser", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "_timing", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "marquer", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "etape_faite", lambda *_a, **_k: False)
    alertes: list[tuple] = []
    monkeypatch.setattr(runner, "_alerter",
                        lambda _c, j, etat, raison, _r: alertes.append((j.id, etat, raison)))
    monkeypatch.setattr(runner.run_module, "executer_etape",
                        lambda etape, *_a, **_k: (runner.CODE_QUALITE, 0.1, "banc FAIL")
                        if etape == "qc" else (0, 0.1, ""))
    resultat = runner.executer_job(conn, job, runner._config(racine), racine=racine,
                                   respecter_fenetre=False)
    assert resultat.statut == "blocked"
    assert "loudness = -24.0 LUFS" in (resultat.raison or "")
    assert len(resultat.regenerations) == 2
    assert alertes and alertes[-1][1] == "blocked"


def test_la_barriere_de_relecture_tient_apres_un_rejet(conn: sqlite3.Connection,
                                                       racine: Path) -> None:
    """Un script réécrit après approbation redevient non relu — l'empreinte est dans la clé."""
    _auto_approve(racine, False)
    chemins = _run(racine, R1)
    job = _job(conn, racine, R1, stage="voice")
    fiche = review.apercu(conn, job, racine)
    review.approuver(conn, fiche, "thomas", racine=racine)
    assert runner._script_relu(conn, file_module.lire(conn, job.id), chemins)
    charge = json.loads(chemins.script.read_text(encoding="utf-8"))
    charge["segments"][1]["narration"] = "Texte réécrit hors relecture."
    chemins.script.write_text(json.dumps(charge), encoding="utf-8")
    assert not runner._script_relu(conn, file_module.lire(conn, job.id), chemins)


# --------------------------------------------------------------------------------------
# 5 — Alertes et digest
# --------------------------------------------------------------------------------------


def test_le_canal_choisit_telegram_quand_les_deux_variables_existent(
        racine: Path, monkeypatch) -> None:
    """Telegram dès que jeton et chat sont posés ; repli macOS sinon ; jamais de panne."""
    monkeypatch.setattr("factory.doctor.charge_env", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAUX")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")
    assert notify.canal(racine).nom == "telegram"
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    voie = notify.canal(racine)
    assert voie.nom in {"macos", "aucun"} and "TELEGRAM" in voie.pourquoi


def test_aucun_jeton_ne_sort_dans_une_alerte(racine: Path, monkeypatch) -> None:
    """Le jeton n'entre ni dans le message, ni dans le journal, ni dans le résultat."""
    monkeypatch.setattr("factory.doctor.charge_env", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "7654321:SECRET-QUI-NE-DOIT-PAS-FUIR")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")
    vus: list[str] = []

    def _poster(jeton: str, chat: str, message: str) -> tuple[bool, str]:
        vus.append(jeton)
        assert "SECRET" not in message
        return True, "ok message_id=1 chat=private date=1"

    envoi = notify.envoyer("titre", "corps", motif="test", racine=racine, poster=_poster)
    assert envoi.ok and vus == ["7654321:SECRET-QUI-NE-DOIT-PAS-FUIR"]
    journal_texte = journal.chemin_events(racine).read_text(encoding="utf-8")
    assert "SECRET" not in journal_texte
    assert "SECRET" not in envoi.reponse


def test_une_alerte_de_relecture_est_groupee(conn: sqlite3.Connection, racine: Path,
                                             monkeypatch) -> None:
    """Un message pour N scripts, jamais N messages : sinon les alertes se coupent."""
    _auto_approve(racine, False)
    for nom in (R1, R2, R3):
        _run(racine, nom)
        _job(conn, racine, nom)
    envoyes: list[tuple[str, str]] = []
    monkeypatch.setattr(notify, "envoyer",
                        lambda titre, corps, **_k: envoyes.append((titre, corps))
                        or notify.Envoi("faux", True, "awaiting_review"))
    fiches = review.en_attente(conn, None, racine)
    notify.alerte_relecture(fiches, racine=racine)
    assert len(envoyes) == 1 and "3 script(s)" in envoyes[0][0]
    assert envoyes[0][1].count("•") == 3


def test_une_alerte_ne_part_quune_fois_par_changement_detat(
        conn: sqlite3.Connection, racine: Path, monkeypatch) -> None:
    """Un job bloqué la nuit ne produit pas 60 notifications par heure."""
    _auto_approve(racine, False)
    _run(racine, R1)
    job = _job(conn, racine, R1, stage="qc", statut="blocked")
    conn.execute("UPDATE jobs SET last_error = 'banc en FAIL' WHERE id = ?", (job.id,))
    envois: list[str] = []
    monkeypatch.setattr(notify, "envoyer",
                        lambda titre, corps, motif="test", **_k: envois.append(motif)
                        or notify.Envoi("faux", True, motif))
    notify.verifier_et_alerter(conn, racine=racine)
    premier = list(envois)
    notify.verifier_et_alerter(conn, racine=racine)
    assert envois == premier, "la seconde revue ne doit rien renvoyer"
    assert "job_blocked" in premier


def test_le_digest_porte_les_sept_rubriques(conn: sqlite3.Connection, racine: Path) -> None:
    """Produits, à relire, bloqués avec raisons, à publier, quota, disque, sauvegarde."""
    _auto_approve(racine, False)
    _run(racine, R1)
    _job(conn, racine, R1)
    _run(racine, R2)
    job2 = _job(conn, racine, R2, stage="qc", statut="blocked")
    conn.execute("UPDATE jobs SET last_error = 'loudness = -24.0 LUFS (cible -14.0)' "
                 "WHERE id = ?", (job2.id,))
    _run(racine, R3)
    job3 = _job(conn, racine, R3, stage="qc", statut="exported")
    conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?",
                 (f"{notify.aujourdhui(racine)}T12:00:00Z", job3.id))

    chemin = notify.ecrire_digest(conn, racine=racine)
    texte = chemin.read_text(encoding="utf-8")
    assert chemin.name == f"digest_{notify.aujourdhui(racine)}.md"
    for attendu in ("## À faire maintenant", "## Produit aujourd'hui", "## Bloqué",
                    "## À publier", "## Machine", "Quota API", "Disque libre",
                    "Sauvegarde", "Daemon"):
        assert attendu in texte, attendu
    assert "loudness = -24.0 LUFS" in texte
    assert "factory review --reviewer" in texte
    assert R3 in texte
    # Le rappel de sauvegarde hors machine, à chaque digest : sans lui, personne ne le fait.
    assert "support externe" in texte


def test_le_quota_non_mesure_dit_quil_ne_lest_pas(conn: sqlite3.Connection,
                                                  racine: Path) -> None:
    """Un « 0 % » inventé ferait rater le jour où l'upload s'arrête. On rend `None`."""
    part, detail = notify.quota_consomme(conn, racine)
    assert part is None and detail
    chemin = notify.ecrire_digest(conn, racine=racine)
    assert "non mesuré" in chemin.read_text(encoding="utf-8")
