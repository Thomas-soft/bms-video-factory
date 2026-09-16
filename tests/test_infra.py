"""Chemins d'un run, base SQLite et lecture des secrets."""

from __future__ import annotations

import os

import pytest

from factory.core import db, secrets
from factory.core.paths import LibraryPaths, RunPaths, chemin_base, racine_projet

VIDEO_ID = "bms-science-en-20260918-k7q2"


def test_chemins_dun_run_derives_du_seul_video_id(tmp_path) -> None:
    """Tous les chemins d'un run viennent du `video_id` (ARCHITECTURE § 3)."""
    run = RunPaths.depuis_video_id(VIDEO_ID, racine=tmp_path)
    base = tmp_path / "workspace" / "runs" / VIDEO_ID
    assert run.spec == base / "spec.json"
    assert run.timings == base / "voice" / "timings.json"
    assert run.segment_wav(3) == base / "voice" / "segment_03.wav"
    assert run.licence("shot_07") == base / "assets" / "shot_07" / "licence.json"
    assert run.clip("shot_07") == base / "clips" / "shot_07.mp4"
    assert run.done("voice") == base / ".done" / "voice.done"
    assert run.thumbnails_json == base / "thumbnails" / "thumbnails.json"
    assert run.export(racine=tmp_path) == tmp_path / "workspace" / "export" / f"{VIDEO_ID}.mp4"
    assert not run.existe()
    run.creer()
    assert run.existe() and run.done_dir.is_dir() and run.clips_dir.is_dir()
    run.creer()  # idempotent


def test_chemins_de_la_bibliotheque(tmp_path) -> None:
    """La bibliothèque a ses six dossiers et son `cadence.json`."""
    lib = LibraryPaths.depuis_racine(racine=tmp_path).creer()
    for nom in LibraryPaths.SOUS_DOSSIERS:
        assert (lib.racine / nom).is_dir()
    assert lib.cadence == tmp_path / "workspace" / "library" / "cadence.json"
    assert lib.licence(lib.images / "a.png").name == "licence.json"


def test_base_creee_avec_ses_tables_et_idempotente(tmp_path) -> None:
    """`ouvrir` crée la base, applique les migrations, et ne les rejoue pas."""
    chemin = tmp_path / "workspace" / "factory.db"
    conn = db.ouvrir(chemin)
    try:
        assert {"runs", "jobs", "review_log", "schema_migrations",
                "library_assets", "library_uses"} <= db.tables(conn)
        assert db.version_schema(conn) == 2
        colonnes = {ligne["name"] for ligne in conn.execute("PRAGMA table_info(runs)")}
        assert {"video_id", "parent_id", "manifest_json", "cut_rhythm_measured_s",
                "reuse_ratio", "score_qc"} <= colonnes
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.migrer(conn) == []
    finally:
        conn.close()
    conn2 = db.ouvrir(chemin)
    try:
        assert db.version_schema(conn2) == 2
    finally:
        conn2.close()


def test_index_unique_sur_lidentifiant_youtube(tmp_path) -> None:
    """Deux runs ne peuvent pas porter le même identifiant YouTube."""
    conn = db.ouvrir(tmp_path / "f.db")
    try:
        for suffixe in ("k7q2", "m4n8"):
            conn.execute(
                "INSERT INTO runs (video_id, channel_id, lang, youtube_video_id, created_at,"
                " updated_at) VALUES (?, 'bms-science-en', 'en', 'dQw4w9WgXcQ', 'now', 'now')",
                (f"bms-science-en-20260918-{suffixe}",),
            )
    except Exception as erreur:  # noqa: BLE001 — c'est l'erreur attendue
        assert "UNIQUE" in str(erreur)
    else:
        pytest.fail("l'index unique sur youtube_video_id n'a pas joué")
    finally:
        conn.close()


def test_migrations_bien_nommees() -> None:
    """Les migrations sont numérotées ; une migration mal nommée arrête le chargement."""
    numeros = [numero for numero, _ in db.migrations_disponibles()]
    assert numeros == sorted(numeros) and numeros[0] == 1


def test_chemin_de_base_par_defaut() -> None:
    """La base vit dans `workspace/factory.db`."""
    assert chemin_base().relative_to(racine_projet()).as_posix() == "workspace/factory.db"


def test_secret_absent_leve_une_erreur_lisible(monkeypatch) -> None:
    """Un secret manquant dit où le mettre, et n'invente rien."""
    monkeypatch.delenv("BMS_SECRET_DE_TEST", raising=False)
    assert not secrets.present("BMS_SECRET_DE_TEST")
    with pytest.raises(secrets.ErreurSecret, match=r"\.env"):
        secrets.lire("BMS_SECRET_DE_TEST")
    monkeypatch.setenv("BMS_SECRET_DE_TEST", "valeur-de-test")
    assert secrets.lire("BMS_SECRET_DE_TEST") == "valeur-de-test"


def test_secret_jamais_affiche() -> None:
    """`masquer` ne laisse passer que la longueur ; `expurger` remplace les valeurs."""
    assert "valeur-de-test" not in secrets.masquer("valeur-de-test")
    assert secrets.masquer(None) == "(absent)"
    expurge = secrets.expurger({"YT_API_KEY": "valeur-de-test", "HF_HOME": "./models/hf"})
    assert expurge["YT_API_KEY"] == "***"
    assert expurge["HF_HOME"] == "./models/hf"
    assert secrets.est_sensible("YT_API_KEY") and not secrets.est_sensible("HF_HOME")


def test_reference_de_secret_contrainte(tmp_path) -> None:
    """Une référence sort de `secrets/` ou remonte l'arborescence : refusée."""
    with pytest.raises(secrets.ErreurSecret, match="hors de secrets/"):
        secrets.chemin_reference("tokens/bms.json")
    with pytest.raises(secrets.ErreurSecret, match="suspecte"):
        secrets.chemin_reference("secrets/../../etc/passwd")
    with pytest.raises(secrets.ErreurSecret, match="introuvable"):
        secrets.lire_reference_json("secrets/tokens/inexistant.json", racine=tmp_path)


def test_permissions_dun_secret(tmp_path) -> None:
    """Un fichier de secret lisible par tous est refusé."""
    fichier = tmp_path / "secrets" / "tokens" / "chaine.json"
    fichier.parent.mkdir(parents=True)
    fichier.write_text('{"refresh_token": "valeur-de-test"}', encoding="utf-8")
    os.chmod(fichier, 0o644)
    assert not secrets.permissions_sures(fichier)
    with pytest.raises(secrets.ErreurSecret, match="permissions"):
        secrets.lire_reference_json("secrets/tokens/chaine.json", racine=tmp_path)
    os.chmod(fichier, 0o600)
    assert secrets.permissions_sures(fichier)
    assert secrets.lire_reference_json("secrets/tokens/chaine.json", racine=tmp_path)


def test_aucune_valeur_de_secret_dans_la_configuration() -> None:
    """Aucun fichier de `config/` ne porte une valeur de secret, seulement des références."""
    suspects: list[str] = []
    for fichier in (racine_projet() / "config").rglob("*.yaml"):
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            nu = ligne.strip()
            if nu.startswith("#") or ":" not in nu:
                continue
            cle, _, valeur = nu.partition(":")
            valeur = valeur.split("#")[0].strip().strip('"')
            if not valeur:
                continue
            if secrets.est_sensible(cle) and not valeur.startswith("secrets/"):
                suspects.append(f"{fichier.name}:{numero} {cle}")
            if valeur.startswith(("ya29.", "AIza", "sk-", "ghp_")):
                suspects.append(f"{fichier.name}:{numero} valeur en clair")
    assert suspects == [], suspects
