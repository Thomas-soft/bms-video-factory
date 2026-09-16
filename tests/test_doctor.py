"""Garde-fous de `factory doctor` — les contrôles bon marché, sans modèle chargé."""
import subprocess
import sys

from factory.doctor import ROOT, charge_env, check_disque, check_env, modeles_retenus


def test_ledger_lisible():
    """Le ledger doit rester analysable : c'est lui qui pilote le contrôle modèles."""
    lignes = modeles_retenus()
    assert len(lignes) >= 7
    noms = [n for n, _, _ in lignes]
    assert not any(n.startswith("Mod") for n in noms), "en-tête du tableau pris pour un modèle"
    assert all(chemin and not chemin.startswith("|") for _, chemin, _ in lignes)


def test_caches_sous_models():
    charge_env()
    assert check_env().ok


def test_plancher_disque():
    assert check_disque().ok, "moins de 8 Go libres : aucun run ne doit démarrer"


def test_quick_ne_charge_aucun_modele():
    """--quick doit rendre la main en quelques secondes et sortir en 0."""
    p = subprocess.run(
        [sys.executable, "-m", "factory.cli", "doctor", "--quick"],
        capture_output=True, text=True, timeout=60, cwd=ROOT,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert "SKIP" in p.stdout


def test_asr_refuse_une_sous_chaine():
    """Régression : « Bonsour, Cecil Dontest. » contient « test » et passait.

    Le contrôle d'origine faisait `"test" in texte.lower()` — trois mots sur
    quatre faux et un PASS. La comparaison au texte attendu doit le refuser.
    """
    from factory.doctor import ASR_WER_MAX, compare_transcription

    taux, manques = compare_transcription("Bonjour, ceci est un test.", "Bonsour, Cecil Dontest.")
    assert taux > ASR_WER_MAX
    assert "test" in manques and "bonjour" in manques

    # Un seul mot faux reste toléré (homophone « est » / « et », observé en 5.1).
    taux, manques = compare_transcription("Bonjour, ceci est un test.", "Bonjour, ceci et un test.")
    assert taux <= ASR_WER_MAX and manques == ["est"]

    # Exact, ponctuation et casse comprises.
    assert compare_transcription("Hello, this is a test.", "hello this is a TEST") == (0.0, [])


def test_la_sonde_fr_ne_condamne_pas_l_environnement():
    """Le français de Serena échoue une fois sur deux (mesuré, 16 synthèses).

    C'est un défaut de voix, pas d'environnement : il doit s'afficher en WARN et
    laisser le code de retour à 0. L'anglais, lui, est mesuré propre et reste un
    vrai verrou.
    """
    from factory.doctor import SONDES_NON_BLOQUANTES

    assert "asr_fr" in SONDES_NON_BLOQUANTES
    assert "asr_en" not in SONDES_NON_BLOQUANTES
