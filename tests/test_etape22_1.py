"""Étape 22.1 — file, reprise, garde-fous, fenêtre, journal, sauvegarde.

Aucune vidéo n'est produite ici : les étapes du DAG sont remplacées par un faux
sous-processus dont on choisit le code de retour. Ce qui est éprouvé, c'est
l'**orchestrateur** — quel job est pris, à quelle étape il repart après une
interruption, ce que le compteur de tentatives fait, et ce qu'une archive contient.
Le test de bout en bout, lui, a tourné sur la vraie chaîne (`STATE.md`).
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest

from factory import video
from factory.core import db
from factory.core.models import FenetreHoraire, OrchestratorConfig, Tentatives
from factory.core.paths import RunPaths
from factory.orchestrator import backup, daemon, journal
from factory.orchestrator import queue as file_module
from factory.orchestrator import runner


@pytest.fixture
def racine(tmp_path: Path) -> Path:
    """Un dépôt jetable : `workspace/`, `config/`, `docs/`."""
    for nom in ("workspace/runs", "workspace/logs", "config", "docs", "registre"):
        (tmp_path / nom).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def conn(racine: Path) -> sqlite3.Connection:
    """Base migrée du dépôt jetable."""
    connexion = db.ouvrir(racine / "workspace" / "factory.db")
    yield connexion
    connexion.close()


def _run_bidon(racine: Path, video_id: str, channel_id: str = "bms-science-en") -> RunPaths:
    """Un dossier de run avec le minimum : `spec.json` et `manifest.json`."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    chemins.racine.mkdir(parents=True, exist_ok=True)
    chemins.spec.write_text(json.dumps({"video_id": video_id, "channel_id": channel_id}),
                            encoding="utf-8")
    chemins.manifest.write_text(json.dumps({"execution": {"timings": {}}}), encoding="utf-8")
    return chemins


def _enregistrer_run(conn: sqlite3.Connection, video_id: str,
                     channel_id: str = "bms-science-en") -> None:
    """Une ligne dans `runs`, ce qui suffit aux requêtes de la file."""
    quand = file_module.maintenant()
    conn.execute(
        "INSERT OR REPLACE INTO runs (video_id, channel_id, lang, created_at, updated_at) "
        "VALUES (?, ?, 'en', ?, ?)", (video_id, channel_id, quand, quand),
    )


# --------------------------------------------------------------------------------------
# Migration et file
# --------------------------------------------------------------------------------------


def test_migration_007_pose_le_verrou_et_la_contrainte(conn: sqlite3.Connection) -> None:
    """`jobs` porte `locked_by`, `locked_at`, et refuse un statut inventé."""
    colonnes = {l["name"] for l in conn.execute("PRAGMA table_info(jobs)")}
    assert {"locked_by", "locked_at", "attempts", "next_run_at", "priority"} <= colonnes
    assert "events" in db.tables(conn)
    quand = file_module.maintenant()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO jobs (video_id, channel_id, stage, status, created_at, updated_at) "
            "VALUES ('x', 'y', 'render', 'en_cours_peut_etre', ?, ?)", (quand, quand),
        )


def test_un_seul_job_vivant_par_run(conn: sqlite3.Connection, racine: Path) -> None:
    """Enfiler deux fois le même run est une erreur lisible, pas un doublon."""
    _enregistrer_run(conn, "r1")
    file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    with pytest.raises(file_module.ErreurFile, match="déjà en file"):
        file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)


def test_ordre_de_prise_priorite_puis_anciennete(conn: sqlite3.Connection,
                                                 racine: Path) -> None:
    """Le plus prioritaire d'abord ; à égalité, le plus ancien."""
    for nom in ("r1", "r2", "r3"):
        _enregistrer_run(conn, nom)
        file_module.enfiler(conn, nom, "bms-science-en", racine=racine)
    file_module.prioriser(conn, 3, 5, racine=racine)
    assert runner.prendre_job(conn, racine).video_id == "r3"


def test_next_run_at_dans_le_futur_exclut_le_job(conn: sqlite3.Connection,
                                                 racine: Path) -> None:
    """L'attente croissante n'est pas décorative : le job n'est pas éligible."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    plus_tard = (datetime.now(UTC) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE jobs SET next_run_at = ? WHERE id = ?", (plus_tard, job.id))
    assert runner.prendre_job(conn, racine) is None


def test_block_exige_une_raison(conn: sqlite3.Connection, racine: Path) -> None:
    """Un job bloqué sans raison est un job perdu."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    with pytest.raises(file_module.ErreurFile):
        file_module.bloquer(conn, job.id, "   ", racine=racine)


# --------------------------------------------------------------------------------------
# Reprise après interruption — le cœur de l'étape
# --------------------------------------------------------------------------------------


def test_reprise_meme_etape_tentative_incrementee(conn: sqlite3.Connection,
                                                  racine: Path) -> None:
    """Un job `running` dont le PID est mort repart **à la même étape**, `attempts` +1."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    mort = _pid_mort()
    conn.execute(
        "UPDATE jobs SET status = 'running', stage = 'render', locked_by = ?, "
        "locked_at = ? WHERE id = ?",
        (f"{os.uname().nodename}:{mort}", file_module.maintenant(), job.id),
    )
    repris = runner.reprendre_orphelins(conn, racine)
    assert [j.id for j in repris] == [job.id]
    apres = file_module.lire(conn, job.id)
    assert (apres.status, apres.stage, apres.attempts) == ("queued", "render", 1)
    niveaux = [e for e in journal.lire_events(racine) if e["level"] == "WARN"]
    assert any(e["stage"] == "render" and "interruption" in e["msg"] for e in niveaux)


def test_job_tenu_par_un_vivant_nest_pas_repris(conn: sqlite3.Connection,
                                                racine: Path) -> None:
    """Notre propre PID est vivant : le job reste `running`."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    conn.execute("UPDATE jobs SET status = 'running', locked_by = ? WHERE id = ?",
                 (runner.signature(), job.id))
    assert runner.reprendre_orphelins(conn, racine) == []


def _pid_mort() -> int:
    """Un PID qui n'existe pas — cherché, jamais inventé."""
    for candidat in range(99999, 90000, -1):
        try:
            os.kill(candidat, 0)
        except ProcessLookupError:
            return candidat
        except PermissionError:
            continue
    raise RuntimeError("aucun PID libre trouvé")


def test_verrou_run_orphelin_repris_avec_avertissement(racine: Path) -> None:
    """Un `run.lock` au PID mort ne gèle pas la fabrique."""
    journal.chemin_verrou(racine).write_text(
        json.dumps({"pid": _pid_mort(), "hote": os.uname().nodename, "quoi": "runner",
                    "depuis": journal.maintenant()}), encoding="utf-8")
    with journal.verrou_run("runner neuf", racine):
        assert journal.detenteur(racine).pid == os.getpid()
    assert any("orphelin" in e["msg"] for e in journal.lire_events(racine))


def test_clip_tronque_par_une_interruption_est_un_ecart_pas_une_panne(tmp_path: Path) -> None:
    """Une interruption pendant `render` laisse un `.mp4` sans atome `moov`.

    Mesuré le 21/09/2026 sur `shot_19.mp4` de `bms-science-en-20260920-s57f` : 262 Ko
    écrits, `moov atom not found`. Le réemploi de `render` appelait `verify_clip` sur ce
    fichier, `ffprobe` levait, et **l'étape entière sortait en code 1** — la reprise
    échouait à l'identique à chaque tentative. Un clip illisible doit être rendu comme un
    écart, pour que le plan soit simplement refait.
    """
    tronque = tmp_path / "shot_19.mp4"
    tronque.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 512)  # en-tête sans moov
    ecarts = video.verify_clip(tronque, 6.5)
    assert ecarts, "un clip illisible doit être signalé"
    assert "illisible" in ecarts[0]
    assert video.verify_clip(tmp_path / "absent.mp4", 6.5) == ["absent.mp4 : absent"]


def test_verrou_tenu_par_un_vivant_est_fatal(racine: Path) -> None:
    """Deux runs de front sont un défaut de conception, pas une attente."""
    with journal.verrou_run("premier", racine):
        with pytest.raises(journal.VerrouOccupe):
            with journal.verrou_run("second", racine):
                pass


# --------------------------------------------------------------------------------------
# Garde-fous et fenêtre
# --------------------------------------------------------------------------------------


def test_garde_disque_sous_le_plancher_met_en_pause(conn: sqlite3.Connection, racine: Path,
                                                    monkeypatch) -> None:
    """Sous 8 Go libres, le job repasse `queued` avec une reprise différée et une alerte."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    _run_bidon(racine, "r1")
    monkeypatch.setattr(runner, "disque_libre_go", lambda *_: 3.0)
    monkeypatch.setattr(runner, "memoire_libre_go", lambda: 8.0)
    resultat = runner.executer_job(conn, job, OrchestratorConfig(), racine=racine,
                                   respecter_fenetre=False)
    apres = file_module.lire(conn, job.id)
    assert (resultat.statut, apres.status) == ("queued", "queued")
    assert apres.next_run_at is not None and "3.0 Go libres" in (apres.last_error or "")
    assert any(e["level"] == "ERROR" and "pause" in e["msg"]
               for e in journal.lire_events(racine))


def test_garde_poids_du_run_bloque(conn: sqlite3.Connection, racine: Path,
                                   monkeypatch) -> None:
    """Un run qui dépasse son plafond de disque est bloqué, pas mis en pause."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    _run_bidon(racine, "r1")
    # Disque et mémoire figés : sinon la suite complète, lancée pendant un vrai run,
    # déclenche d'abord le garde mémoire et ce test mesure autre chose que son sujet.
    monkeypatch.setattr(runner, "disque_libre_go", lambda *_: 50.0)
    monkeypatch.setattr(runner, "memoire_libre_go", lambda: 8.0)
    monkeypatch.setattr(runner, "_taille_run_mo", lambda *_: 9999.0)
    resultat = runner.executer_job(conn, job, OrchestratorConfig(), racine=racine,
                                   respecter_fenetre=False)
    assert resultat.statut == "blocked"
    assert file_module.lire(conn, job.id).status == "blocked"


@pytest.mark.parametrize(
    ("debut", "fin", "heure", "attendu"),
    [("22:00", "07:00", 23, True), ("22:00", "07:00", 3, True),
     ("22:00", "07:00", 15, False), ("22:00", "07:00", 7, False),
     ("08:00", "18:00", 12, True), ("08:00", "18:00", 19, False),
     ("00:00", "00:00", 4, True)],
)
def test_fenetre_franchit_minuit(debut: str, fin: str, heure: int, attendu: bool) -> None:
    """Une fenêtre qui franchit minuit se lit dans les deux sens."""
    assert FenetreHoraire(debut=debut, fin=fin).contient(time(heure, 30)) is attendu


def test_fenetre_fermee_rend_le_job_a_la_file(conn: sqlite3.Connection, racine: Path,
                                              monkeypatch) -> None:
    """Hors fenêtre, l'étape lourde n'est pas lancée et le job attend."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="render", racine=racine)
    _run_bidon(racine, "r1")
    monkeypatch.setattr(runner, "fenetre_ouverte", lambda *_a, **_k: False)
    resultat = runner.executer_job(conn, job, OrchestratorConfig(), racine=racine)
    assert resultat.statut == "queued" and "hors fenêtre" in (resultat.raison or "")
    assert file_module.lire(conn, job.id).stage == "render"


# --------------------------------------------------------------------------------------
# Tentatives
# --------------------------------------------------------------------------------------


def test_attente_croissante_puis_echec_definitif(conn: sqlite3.Connection, racine: Path,
                                                 monkeypatch) -> None:
    """3 tentatives, attentes 5 puis 15 minutes, puis `failed` avec l'erreur lisible."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", racine=racine)
    _run_bidon(racine, "r1")
    monkeypatch.setattr(runner, "gardes_fous", lambda *_a, **_k: [])
    monkeypatch.setattr(runner.run_module, "executer_etape",
                        lambda *_a, **_k: (1, 0.1, "boum : contrat d'entrée non satisfait"))
    monkeypatch.setattr(runner, "_finaliser", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "_inscrire_erreur", lambda *_a, **_k: None)
    cfg = OrchestratorConfig(tentatives=Tentatives(max=3, attentes_min=[5, 15, 60]))

    for tentative in (1, 2):
        job = file_module.lire(conn, job.id)
        runner.executer_job(conn, job, cfg, racine=racine, respecter_fenetre=False)
        apres = file_module.lire(conn, job.id)
        assert (apres.status, apres.attempts) == ("queued", tentative)
        assert apres.next_run_at is not None
        conn.execute("UPDATE jobs SET next_run_at = NULL WHERE id = ?", (job.id,))

    job = file_module.lire(conn, job.id)
    runner.executer_job(conn, job, cfg, racine=racine, respecter_fenetre=False)
    apres = file_module.lire(conn, job.id)
    assert (apres.status, apres.attempts) == ("failed", 3)
    assert "boum" in (apres.last_error or "")


def test_attente_min_suit_la_politique() -> None:
    """La dernière attente vaut pour toutes les suivantes."""
    politique = Tentatives(max=5, attentes_min=[5, 15, 60])
    assert [politique.attente_min(n) for n in (1, 2, 3, 4)] == [5, 15, 60, 60]


# --------------------------------------------------------------------------------------
# Journal
# --------------------------------------------------------------------------------------


def test_evenement_expurge_les_clefs_qui_sentent_le_secret(racine: Path) -> None:
    """Aucun jeton n'entre dans un événement, même passé par erreur."""
    journal.evenement("INFO", "appel", donnees={"api_key": "AIzaTOPSECRET",
                                                "quota": 50,
                                                "imbrique": {"refresh_token": "x"}},
                      racine=racine)
    ligne = journal.lire_events(racine)[-1]
    assert ligne["data"]["api_key"] == "[expurgé]"
    assert ligne["data"]["imbrique"]["refresh_token"] == "[expurgé]"
    assert ligne["data"]["quota"] == 50
    assert "TOPSECRET" not in journal.chemin_events(racine).read_text(encoding="utf-8")


def test_events_jsonl_est_append_only(racine: Path) -> None:
    """Chaque appel ajoute une ligne ; aucune n'est réécrite."""
    for index in range(3):
        journal.evenement("INFO", f"ligne {index}", racine=racine)
    lignes = journal.chemin_events(racine).read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 3 and json.loads(lignes[0])["msg"] == "ligne 0"


def test_rotation_de_factory_log(racine: Path) -> None:
    """À 10 Mo, `factory.log` devient `.1` et un fichier neuf le remplace."""
    fichier = journal.chemin_factory_log(racine)
    fichier.write_text("x" * 1_200_000, encoding="utf-8")
    journal.journaliser("après rotation", racine=racine, taille_max_mo=1.0, fichiers=3)
    assert fichier.with_suffix(".log.1").exists()
    assert fichier.stat().st_size < 1_000
    assert "après rotation" in fichier.read_text(encoding="utf-8")


def test_rotation_supprime_le_plus_ancien(racine: Path) -> None:
    """Au-delà de N fichiers, le plus ancien part — le disque ne grossit pas sans fin."""
    fichier = journal.chemin_factory_log(racine)
    for rang in range(1, 4):
        fichier.with_suffix(f".log.{rang}").write_text(f"gen {rang}", encoding="utf-8")
    fichier.write_text("y" * 1_200_000, encoding="utf-8")
    journal.journaliser("neuf", racine=racine, taille_max_mo=1.0, fichiers=3)
    assert not fichier.with_suffix(".log.4").exists()
    assert fichier.with_suffix(".log.2").read_text(encoding="utf-8") == "gen 1"


# --------------------------------------------------------------------------------------
# Sauvegarde
# --------------------------------------------------------------------------------------


def test_archive_ne_contient_aucun_secret(racine: Path, conn: sqlite3.Connection,
                                          monkeypatch) -> None:
    """`.env` et `secrets/` restent dehors, même placés au milieu de `config/`."""
    (racine / "secrets").mkdir()
    (racine / "secrets" / "client_secret.json").write_text("{}", encoding="utf-8")
    (racine / ".env").write_text("YT_API_KEY=secret", encoding="utf-8")
    (racine / "config" / "channels").mkdir(parents=True, exist_ok=True)
    (racine / "config" / "channels" / "bms.yaml").write_text("id: bms", encoding="utf-8")
    (racine / "config" / "token_de_test.yaml").write_text("x: 1", encoding="utf-8")
    _run_bidon(racine, "r1")
    destination = racine / "backups"
    monkeypatch.setattr(backup, "destination", lambda *_a, **_k: destination)

    resultat = backup.executer(racine)
    assert resultat.archive.exists() and resultat.runs == 1
    verdict = backup.tester_restauration(resultat.archive, racine)
    assert verdict.secrets_trouves == []
    assert verdict.runs_archive == verdict.runs_original
    assert verdict.ok


def test_retention_supprime_les_archives_trop_vieilles(tmp_path: Path) -> None:
    """Une archive de 40 jours part, une de 3 jours reste."""
    vieille = tmp_path / "factory-20260101-0600.tar.zst"
    recente = tmp_path / "factory-20260919-0600.tar.zst"
    for chemin, jours in ((vieille, 40), (recente, 3)):
        chemin.write_bytes(b"x")
        age = (datetime.now(UTC) - timedelta(days=jours)).timestamp()
        os.utime(chemin, (age, age))
    assert backup.appliquer_retention(tmp_path, 30) == [vieille.name]
    assert recente.exists() and not vieille.exists()


def test_copie_de_base_coherente(racine: Path, conn: sqlite3.Connection) -> None:
    """La base est copiée par `.backup`, et la copie s'ouvre avec les mêmes lignes."""
    _enregistrer_run(conn, "r1")
    cible = racine / "copie.db"
    backup._copie_coherente(racine / "workspace" / "factory.db", cible)
    lue = sqlite3.connect(cible)
    assert lue.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
    lue.close()


# --------------------------------------------------------------------------------------
# Daemon et plists
# --------------------------------------------------------------------------------------


def test_decharger_un_agent_survit_au_redemarrage(monkeypatch: pytest.MonkeyPatch) -> None:
    """`bootout` seul ne vaut que pour la session de démarrage en cours.

    Mesuré le 21/09/2026 : après une panique noyau, `com.bms.factory.daemon` déchargé la
    veille était de retour dans `launchctl list`, prêt à produire sans surveillance — le
    plist était resté dans `~/Library/LaunchAgents/` et launchd l'a rebootstrappé à
    l'ouverture de session. Seul `disable` écrit un état persistant.
    """
    appels: list[tuple[str, ...]] = []
    monkeypatch.setattr(daemon, "_launchctl", lambda *a: (appels.append(a), (0, ""))[1])

    daemon.decharger_agent("com.bms.test")
    verbes = [a[0] for a in appels]
    assert verbes.index("disable") < verbes.index("bootout"), verbes

    appels.clear()
    daemon.decharger_agent("com.bms.test", durable=False)
    assert [a[0] for a in appels] == ["bootout"]


def test_charger_un_agent_leve_la_desactivation(monkeypatch: pytest.MonkeyPatch,
                                                tmp_path: Path) -> None:
    """Sans `enable`, `bootstrap` réussit et launchd refuse quand même de lancer l'agent."""
    (tmp_path / "com.bms.test.plist").write_text("<plist/>", encoding="utf-8")
    appels: list[tuple[str, ...]] = []
    monkeypatch.setattr(daemon, "dossier_agents", lambda: tmp_path)
    monkeypatch.setattr(daemon, "_launchctl", lambda *a: (appels.append(a), (0, ""))[1])
    monkeypatch.setattr(daemon.time, "sleep", lambda _: None)

    daemon.charger_agent("com.bms.test")
    verbes = [a[0] for a in appels]
    assert verbes.index("enable") < verbes.index("bootstrap"), verbes


def test_plists_portent_ce_que_launchd_exige(racine: Path) -> None:
    """PATH complet, WorkingDirectory, sortie vers un dossier existant, KeepAlive prudent."""
    from factory.orchestrator import daemon as daemon_module

    charge = daemon_module.plist_daemon(racine)
    assert charge["Label"] == "com.bms.factory.daemon"
    assert "/opt/homebrew/bin" in charge["EnvironmentVariables"]["PATH"]
    assert charge["WorkingDirectory"] == str(racine)
    assert charge["StandardOutPath"].endswith("workspace/logs/daemon.log")
    assert charge["ProcessType"] == "Standard"
    # `KeepAlive: true` relancerait le daemon après un `factory daemon stop`.
    assert charge["KeepAlive"] == {"SuccessfulExit": False}
    assert charge["RunAtLoad"] is True

    sauvegarde = daemon_module.plist_backup(racine)
    assert sauvegarde["StartCalendarInterval"] == {"Hour": 6, "Minute": 30}
    assert sauvegarde["RunAtLoad"] is False


def test_arret_propre_laisse_le_job_a_son_etape(conn: sqlite3.Connection, racine: Path,
                                                monkeypatch) -> None:
    """Un arrêt demandé rend le job à la file **avant** de lancer l'étape suivante."""
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="voice", racine=racine)
    _run_bidon(racine, "r1")
    arret = runner.Arret()
    arret.demande = True
    resultat = runner.executer_job(conn, job, OrchestratorConfig(), racine=racine,
                                   arret=arret, respecter_fenetre=False)
    apres = file_module.lire(conn, job.id)
    assert (resultat.statut, apres.status, apres.stage) == ("queued", "queued", "voice")


def test_dag_du_runner_contient_qc(conn: sqlite3.Connection) -> None:
    """Le runner passe le banc ; `factory run` s'arrête à l'export."""
    from factory.run import NOEUDS

    assert file_module.ETAPES[-1] == "qc"
    assert file_module.ETAPES[:-1] == NOEUDS


# --------------------------------------------------------------------------------------
# Purge de la file de sujets — résidu de l'étape 20, traité ici
# --------------------------------------------------------------------------------------


def test_purge_epargne_les_decisions_humaines(conn: sqlite3.Connection) -> None:
    """`taille_max` et `age_max_jours` s'appliquent — mais jamais à `approved` ni `used`."""
    from factory.editorial import topics as tp

    vieux = (datetime.now(UTC) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    frais = file_module.maintenant()
    lignes = [
        ("c1", "périmé proposé", "a", 0.9, "proposed", vieux),
        ("c1", "périmé approuvé", "a", 0.9, "approved", vieux),
        ("c1", "périmé utilisé", "a", 0.9, "used", vieux),
        ("c1", "périmé banni", "a", 0.9, "banned", vieux),
        ("c1", "frais 1", "a", 0.8, "proposed", frais),
        ("c1", "frais 2", "a", 0.7, "proposed", frais),
        ("c2", "autre chaîne", "a", 0.6, "proposed", frais),
    ]
    for channel, topic, angle, score, statut, quand in lignes:
        conn.execute(
            "INSERT INTO topics_queue (channel_id, lang, topic, angle, score, status, "
            "created_at) VALUES (?, 'en', ?, ?, ?, ?, ?)",
            (channel, topic, angle, score, statut, quand),
        )

    mesures = tp.purger(conn, taille_max=1, age_max_jours=45)
    restants = {(l["channel_id"], l["topic"]) for l in
                conn.execute("SELECT channel_id, topic FROM topics_queue")}
    assert mesures["par_age"] == 1          # seul le `proposed` périmé part
    assert mesures["par_plafond"] == 1      # « frais 2 », au-delà du plafond de 1
    assert ("c1", "périmé approuvé") in restants
    assert ("c1", "périmé utilisé") in restants
    assert ("c1", "périmé banni") in restants
    assert ("c1", "frais 1") in restants    # le mieux noté survit au plafond
    assert ("c2", "autre chaîne") in restants   # le plafond est par chaîne


# --------------------------------------------------------------------------------------
# Barrière de relecture — le défaut trouvé le 20/09 par le test de bout en bout
# --------------------------------------------------------------------------------------


def _config_chaine(racine: Path, auto_approve: bool) -> None:
    """Le minimum de `config/` pour que `charger()` connaisse la chaîne et un relecteur."""
    (racine / "config" / "channels").mkdir(parents=True, exist_ok=True)
    import shutil

    from factory.core.paths import racine_projet as vraie_racine

    source = vraie_racine() / "config"
    for nom in ("languages", "niches", "styles", "channels", "products"):
        shutil.copytree(source / nom, racine / "config" / nom, dirs_exist_ok=True)
    for nom in ("team.yaml", "qc.yaml", "editorial.yaml", "economics.yaml",
                "orchestrator.yaml"):
        shutil.copy2(source / nom, racine / "config" / nom)
    fichier = racine / "config" / "channels" / "bms-science-en.yaml"
    texte = fichier.read_text(encoding="utf-8")
    fichier.write_text(
        texte.replace("auto_approve: false", f"auto_approve: {str(auto_approve).lower()}"),
        encoding="utf-8",
    )


def test_code_4_sur_script_ne_saute_pas_la_relecture(conn: sqlite3.Connection,
                                                     racine: Path, monkeypatch) -> None:
    """Le défaut du 20/09 : `script` sorti en **code 4** enchaînait sur `voice` sans relecture.

    Un seuil de qualité non tenu (densité sous le plancher de la niche) n'annule pas
    l'obligation de `CONFORMITE` § 4 — il la rend plus nécessaire.
    """
    _config_chaine(racine, auto_approve=False)
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="script", racine=racine)
    chemins = _run_bidon(racine, "r1")
    monkeypatch.setattr(runner, "gardes_fous", lambda *_a, **_k: [])
    monkeypatch.setattr(runner, "_finaliser", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "_timing", lambda *_a, **_k: None)

    def _script_puis_rien(etape, *_a, **_k):
        if etape == "script":
            chemins.script.write_text('{"segments": []}', encoding="utf-8")
            return 4, 1.0, "densite_sous_plancher : 2.82 fait(s)/min sous le plancher 3.00"
        raise AssertionError(f"l'étape {etape} n'aurait jamais dû être lancée")

    monkeypatch.setattr(runner.run_module, "executer_etape", _script_puis_rien)
    resultat = runner.executer_job(conn, job, runner._config(racine), racine=racine,
                                   respecter_fenetre=False)
    apres = file_module.lire(conn, job.id)
    assert (resultat.statut, apres.status, apres.stage) == ("awaiting_review",
                                                            "awaiting_review", "voice")


def test_la_barriere_tient_aussi_a_la_reprise(conn: sqlite3.Connection, racine: Path,
                                              monkeypatch) -> None:
    """Reprise à `voice` avec un `script.json` jamais relu : le job attend toujours."""
    _config_chaine(racine, auto_approve=False)
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="voice", racine=racine)
    chemins = _run_bidon(racine, "r1")
    chemins.script.write_text('{"segments": []}', encoding="utf-8")
    monkeypatch.setattr(runner, "gardes_fous", lambda *_a, **_k: [])
    monkeypatch.setattr(runner, "_finaliser", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "executer_etape",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("lancée")))
    assert runner.executer_job(conn, job, runner._config(racine), racine=racine,
                               respecter_fenetre=False).statut == "awaiting_review"


def test_approbation_tracee_libere_le_job(conn: sqlite3.Connection, racine: Path,
                                          monkeypatch) -> None:
    """`queue approve` écrit relecteur, date et empreinte, puis la barrière tombe."""
    _config_chaine(racine, auto_approve=False)
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="voice", racine=racine)
    chemins = _run_bidon(racine, "r1")
    chemins.script.write_text('{"segments": []}', encoding="utf-8")
    conn.execute("UPDATE jobs SET status = 'awaiting_review' WHERE id = ?", (job.id,))

    with pytest.raises(file_module.ErreurFile, match="relecteur inconnu"):
        file_module.approuver(conn, job.id, "equipe", racine=racine)

    libere = file_module.approuver(conn, job.id, "thomas", racine=racine)
    assert libere.status == "queued"
    ligne = conn.execute("SELECT * FROM review_log WHERE video_id = 'r1'").fetchone()
    import hashlib

    assert ligne["reviewer"] == "thomas" and ligne["decision"] == "approved"
    assert ligne["review_hash"] == hashlib.sha256(chemins.script.read_bytes()).hexdigest()
    assert runner._script_relu(conn, file_module.lire(conn, job.id), chemins)

    # Un script réécrit après approbation redevient non relu : c'est le texte qu'on approuve.
    chemins.script.write_text('{"segments": [1]}', encoding="utf-8")
    assert not runner._script_relu(conn, file_module.lire(conn, job.id), chemins)


def test_auto_approve_vrai_ne_pose_aucune_barriere(conn: sqlite3.Connection, racine: Path,
                                                   monkeypatch) -> None:
    """`auto_approve: true` court-circuite la barrière — et c'est tout ce qu'il fait."""
    _config_chaine(racine, auto_approve=True)
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="voice", racine=racine)
    chemins = _run_bidon(racine, "r1")
    chemins.script.write_text('{"segments": []}', encoding="utf-8")
    monkeypatch.setattr(runner, "gardes_fous", lambda *_a, **_k: [])
    monkeypatch.setattr(runner, "_finaliser", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "_timing", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.run_module, "marquer", lambda *_a, **_k: None)
    lancees: list[str] = []

    def _tout_passe(etape, *_a, **_k):
        lancees.append(etape)
        return 0, 0.1, ""

    monkeypatch.setattr(runner.run_module, "executer_etape", _tout_passe)
    monkeypatch.setattr(runner.run_module, "etape_faite", lambda *_a, **_k: False)
    resultat = runner.executer_job(conn, job, runner._config(racine), racine=racine,
                                   respecter_fenetre=False)
    assert resultat.statut == "exported" and "voice" in lancees and "qc" in lancees


def test_levee_sans_relecture_est_tracee_comme_telle(conn: sqlite3.Connection,
                                                     racine: Path) -> None:
    """Une levée sans lecture s'enregistre `auto-approve` / `auto_approved`, avec motif.

    Le nom d'un humain qui n'a rien lu ne doit jamais entrer dans `review_log` : une
    trace fausse est pire qu'une trace qui avoue.
    """
    _config_chaine(racine, auto_approve=False)
    _enregistrer_run(conn, "r1")
    job = file_module.enfiler(conn, "r1", "bms-science-en", stage="voice", racine=racine)
    chemins = _run_bidon(racine, "r1")
    chemins.script.write_text('{"segments": []}', encoding="utf-8")
    conn.execute("UPDATE jobs SET status = 'awaiting_review' WHERE id = ?", (job.id,))

    with pytest.raises(file_module.ErreurFile, match="motif"):
        file_module.approuver(conn, job.id, "", racine=racine, sans_relecture=True)

    libere = file_module.approuver(conn, job.id, "", racine=racine, sans_relecture=True,
                                   motif="banc de l'étape 22.1")
    ligne = conn.execute("SELECT * FROM review_log WHERE video_id = 'r1'").fetchone()
    assert libere.status == "queued"
    assert ligne["reviewer"] == "auto"
    assert ligne["decision"] == "auto_approved"
    # Depuis la migration 008, le motif a sa colonne : `batch_id` redevient le lot.
    assert ligne["motif"] == "banc de l'étape 22.1"
    assert runner._script_relu(conn, file_module.lire(conn, job.id), chemins)
    alerte = [e for e in journal.lire_events(racine) if e["level"] == "WARN"][-1]
    assert "SANS RELECTURE" in alerte["msg"]
