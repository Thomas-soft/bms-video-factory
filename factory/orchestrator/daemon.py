"""Daemon de production : la fabrique tourne seule, dans une fenêtre horaire.

Trois choix qui méritent d'être écrits.

1. **`KeepAlive` est un dictionnaire, pas `true`.** Le prompt de l'étape 22.1 demandait
   `KeepAlive` ; tel quel, launchd relance le daemon à **chaque** sortie, y compris celle
   que `factory daemon stop` vient de demander — la commande d'arrêt deviendrait un
   redémarrage. Le plist écrit donc `KeepAlive = {SuccessfulExit: false}` : relance sur
   plantage, respect d'un arrêt propre. `ThrottleInterval` évite la boucle serrée si le
   démarrage échoue immédiatement.
2. **La fenêtre est dans le processus, pas dans le plist.** `StartCalendarInterval` ne sait
   pas arrêter un job à 07:00 ; et launchd ne garantit aucun état d'alimentation — un job
   programmé sur une machine endormie part en DarkWake ou ne part pas du tout (forums
   développeurs Apple, 2025). Le daemon vit donc en continu et **refuse** les étapes
   lourdes hors fenêtre : c'est lui qui décide, à chaque étape, pas launchd.
3. **L'arrêt est un signal, pas un `kill`.** SIGTERM pose un drapeau ; l'étape en cours va
   jusqu'à son terme, l'état est écrit, le processus sort en 0. Un ffmpeg interrompu au
   milieu laisserait un fichier tronqué qu'aucun marqueur ne décrit.
"""

from __future__ import annotations

import os
import plistlib
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from factory.core import db
from factory.core.paths import dossier_workspace, racine_projet
from factory.orchestrator import journal, runner

LABEL_DAEMON = "com.bms.factory.daemon"
LABEL_BACKUP = "com.bms.factory.backup"
#: Étape 22.2 — le digest du matin, la seule lecture quotidienne prévue.
LABEL_DIGEST = "com.bms.factory.digest"

#: PATH complet du plist. Celui qu'hérite un LaunchAgent est minimal
#: (`/usr/bin:/bin:/usr/sbin:/sbin`) et aucun `.zshrc` n'est lu : sans `/opt/homebrew/bin`,
#: ni `ffmpeg` ni `llama-cli` ne sont trouvés, et l'étape échoue sur un « command not found ».
PATH_PLIST = "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def chemin_pid(racine: Path | None = None) -> Path:
    """`workspace/daemon.pid`."""
    return dossier_workspace(racine) / "daemon.pid"


def dossier_agents() -> Path:
    """`~/Library/LaunchAgents`."""
    return Path.home() / "Library" / "LaunchAgents"


# --------------------------------------------------------------------------------------
# Boucle
# --------------------------------------------------------------------------------------


@dataclass
class EtatDaemon:
    """Ce que `factory daemon status` sait dire sans lire un log."""

    pid: int | None
    vivant: bool
    depuis: str | None
    charge_launchd: bool
    fenetre_lourdes_ouverte: bool
    jobs: dict[str, int]
    verrou: str | None


def _ecrire_pid(racine: Path) -> bool:
    """Note le PID du daemon, pour `status` et `stop`. Faux si un autre daemon vit déjà.

    Ne pas écraser : `factory daemon stop` doit viser le daemon de fond, pas le
    `run-once` qu'un humain vient de lancer à côté. Le second ne fera de toute façon
    rien d'utile — `run.lock` l'en empêche.
    """
    ancien, _ = _lire_pid(racine)
    if ancien is not None and ancien != os.getpid() and _vivant(ancien):
        journal.evenement("WARN", f"un daemon tourne déjà (pid {ancien}) : "
                          f"le pid {os.getpid()} ne prend pas la main", racine=racine)
        return False
    chemin_pid(racine).write_text(
        f"{os.getpid()}\n{socket.gethostname()}\n{runner.maintenant()}\n", encoding="utf-8"
    )
    return True


def _lire_pid(racine: Path) -> tuple[int | None, str | None]:
    """`(pid, depuis)` du daemon, ou `(None, None)`."""
    fichier = chemin_pid(racine)
    if not fichier.exists():
        return None, None
    lignes = fichier.read_text(encoding="utf-8").splitlines()
    try:
        return int(lignes[0]), (lignes[2] if len(lignes) > 2 else None)
    except (ValueError, IndexError):
        return None, None


def _vivant(pid: int | None) -> bool:
    """Vrai si le PID répond."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def tourner(
    *, racine: Path | None = None, une_fois: bool = False, max_jobs: int | None = None,
    respecter_fenetre: bool = True, echo: Callable[[str], None] | None = None,
) -> list[runner.ResultatTour]:
    """La boucle. `une_fois` vide la file puis sort ; sinon elle dort et recommence."""
    racine = racine or racine_projet()
    dire = echo or (lambda _: None)
    cfg = runner._config(racine)  # noqa: SLF001 — même paquet
    arret = runner.Arret()
    arret.installer()
    proprietaire = _ecrire_pid(racine)
    if not proprietaire and not une_fois:
        # Un daemon vit déjà : ce processus ne servirait qu'à tourner à vide. launchd le
        # relancera au prochain `RunAtLoad` ou après un plantage du premier.
        return []
    journal.evenement("INFO", f"daemon démarré (pid {os.getpid()})",
                      donnees={"une_fois": une_fois, "fenetre": respecter_fenetre},
                      racine=racine)
    tous: list[runner.ResultatTour] = []
    # Le verrou tenu par un autre est un état normal, pas un incident : on ne le journalise
    # qu'au **changement** de détenteur. Sans cela, une nuit de rendu de 2 h produit 120
    # lignes `WARN` identiques et noie les vraies dans `events.jsonl`.
    dernier_bloqueur: str | None = None
    try:
        while True:
            conn = db.ouvrir(racine / "workspace" / "factory.db")
            try:
                faits = runner.boucle(
                    conn, racine=racine, max_jobs=max_jobs, cfg=cfg, arret=arret,
                    respecter_fenetre=respecter_fenetre, echo=echo,
                )
                dernier_bloqueur = None
                # Étape 23.2 : téléverser (en privé) ce que le calendrier rend dû. precheck
                # passe avant tout appel d'API ; un échec bloque le job, jamais la boucle.
                try:
                    from factory.publish import calendar as calendrier

                    for fait in calendrier.publier_echeances(conn, racine=racine, echo=echo):
                        dire(fait)
                except Exception as erreur:  # noqa: BLE001 — la production continue
                    journal.evenement("WARN", f"publication des échéances : {erreur}",
                                      racine=racine, conn=conn)
            except journal.VerrouOccupe as erreur:
                tenu = journal.detenteur(racine)
                signature_bloqueur = f"{tenu.pid}:{tenu.quoi}" if tenu else str(erreur)
                if signature_bloqueur != dernier_bloqueur:
                    journal.evenement("WARN", f"tour sauté : {erreur}", racine=racine,
                                      conn=conn)
                    dernier_bloqueur = signature_bloqueur
                faits = []
            finally:
                conn.close()
            tous.extend(faits)
            if une_fois or arret.demande:
                break
            if max_jobs is not None and len(tous) >= max_jobs:
                break
            dire(f"rien à faire — sommeil de {cfg.daemon.pause_boucle_s} s")
            _dormir(cfg.daemon.pause_boucle_s, arret)
            if arret.demande:
                break
    finally:
        if proprietaire:
            chemin_pid(racine).unlink(missing_ok=True)
        journal.evenement(
            "INFO", f"daemon arrêté ({'signal ' + str(arret.signal) if arret.demande else 'fin'})",
            donnees={"jobs_traites": len(tous)}, racine=racine,
        )
    return tous


def _dormir(secondes: int, arret: runner.Arret) -> None:
    """Sommeil interruptible : le signal ne doit pas attendre la fin du `sleep`."""
    fin = time.monotonic() + secondes
    while time.monotonic() < fin and not arret.demande:
        time.sleep(min(1.0, fin - time.monotonic()))


def arreter(racine: Path | None = None, attendre_s: int = 0) -> bool:
    """Envoie SIGTERM au daemon. Vrai s'il y avait quelqu'un à arrêter.

    `attendre_s > 0` attend la sortie ; l'étape en cours peut durer 90 minutes, l'appelant
    décide s'il patiente ou non. On n'escalade **jamais** en SIGKILL : ce serait le `kill`
    que l'étape 22.1 teste, et il laisse une étape à moitié écrite.
    """
    racine = racine or racine_projet()
    pid, _ = _lire_pid(racine)
    if not _vivant(pid):
        chemin_pid(racine).unlink(missing_ok=True)
        return False
    os.kill(int(pid), signal.SIGTERM)
    journal.evenement("INFO", f"SIGTERM envoyé au daemon (pid {pid})", racine=racine)
    fin = time.monotonic() + attendre_s
    while attendre_s and time.monotonic() < fin and _vivant(pid):
        time.sleep(1.0)
    return True


def etat(racine: Path | None = None) -> EtatDaemon:
    """Ce que `factory daemon status` affiche."""
    from factory.orchestrator import queue as file_module

    racine = racine or racine_projet()
    pid, depuis = _lire_pid(racine)
    cfg = runner._config(racine)  # noqa: SLF001
    conn = db.ouvrir(racine / "workspace" / "factory.db")
    jobs = file_module.compter(conn)
    conn.close()
    tenu = journal.detenteur(racine)
    return EtatDaemon(
        pid=pid, vivant=_vivant(pid), depuis=depuis,
        charge_launchd=charge(LABEL_DAEMON),
        fenetre_lourdes_ouverte=runner.fenetre_ouverte(cfg, "render"),
        jobs=jobs,
        verrou=None if tenu is None else
        f"pid {tenu.pid} ({tenu.quoi}) depuis {tenu.depuis}"
        + ("" if tenu.vivant else " — PID MORT, sera repris"),
    )


# --------------------------------------------------------------------------------------
# launchd
# --------------------------------------------------------------------------------------


def _plist_commun(racine: Path, label: str, arguments: list[str],
                  sortie: Path) -> dict[str, Any]:
    """Squelette de plist partagé par les deux agents."""
    return {
        "Label": label,
        "ProgramArguments": arguments,
        "WorkingDirectory": str(racine),
        "EnvironmentVariables": {
            "PATH": PATH_PLIST,
            "FACTORY_ROOT": str(racine),
            "PYTHONUNBUFFERED": "1",
            # Les caches de modèles vivent sous `models/` (CLAUDE.md § 3) : un agent
            # launchd qui les ignorerait re-téléchargerait 4,3 Go dans ~/.cache.
            "HF_HOME": str(racine / "models" / "hf"),
        },
        # Le dossier doit exister : xpcproxy qui ne peut pas ouvrir StandardOutPath sort
        # en 78 (EX_CONFIG) et l'agent ne démarre jamais.
        "StandardOutPath": str(sortie),
        "StandardErrorPath": str(sortie),
        # Sans `Standard`, launchd throttle le CPU et les E-S : un rendu ffmpeg y perdrait
        # plus que ce que la fenêtre nocturne lui fait gagner.
        "ProcessType": "Standard",
    }


def plist_daemon(racine: Path | None = None) -> dict[str, Any]:
    """`com.bms.factory.daemon` — la boucle de production."""
    racine = racine or racine_projet()
    charge = _plist_commun(
        racine, LABEL_DAEMON,
        [sys.executable, "-m", "factory.cli", "daemon", "start", "--foreground"],
        journal.dossier_logs(racine) / "daemon.log",
    )
    charge["RunAtLoad"] = True
    # Relance sur plantage seulement : `factory daemon stop` sort en 0 et doit le rester.
    charge["KeepAlive"] = {"SuccessfulExit": False}
    charge["ThrottleInterval"] = 60
    return charge


def plist_backup(racine: Path | None = None, heure: int = 6, minute: int = 30) -> dict[str, Any]:
    """`com.bms.factory.backup` — une archive par jour, hors fenêtre de production lourde."""
    racine = racine or racine_projet()
    charge = _plist_commun(
        racine, LABEL_BACKUP,
        [sys.executable, "-m", "factory.cli", "backup", "run"],
        journal.dossier_logs(racine) / "backup.log",
    )
    charge["StartCalendarInterval"] = {"Hour": heure, "Minute": minute}
    charge["RunAtLoad"] = False
    return charge


def plist_digest(racine: Path | None = None, heure: int | None = None,
                 minute: int | None = None) -> dict[str, Any]:
    """`com.bms.factory.digest` — le digest du matin, envoyé après la sauvegarde.

    Après la fin de la fenêtre lourde (07:00) et après la sauvegarde de 06:30 : le digest
    doit pouvoir dire « sauvegarde du jour : faite », ce qu'il ne saurait pas à 06:00.
    """
    racine = racine or racine_projet()
    cfg = runner._config(racine)  # noqa: SLF001 — même paquet
    charge = _plist_commun(
        racine, LABEL_DIGEST,
        [sys.executable, "-m", "factory.cli", "digest", "--envoyer"],
        journal.dossier_logs(racine) / "digest.log",
    )
    charge["StartCalendarInterval"] = {
        "Hour": cfg.notifications.digest_heure if heure is None else heure,
        "Minute": cfg.notifications.digest_minute if minute is None else minute,
    }
    charge["RunAtLoad"] = False
    return charge


def ecrire_plists(racine: Path | None = None) -> list[Path]:
    """Écrit les trois plists dans `~/Library/LaunchAgents`, en 0644."""
    racine = racine or racine_projet()
    dossier = dossier_agents()
    dossier.mkdir(parents=True, exist_ok=True)
    journal.dossier_logs(racine)  # StandardOutPath doit exister avant le chargement
    ecrits: list[Path] = []
    for label, charge in ((LABEL_DAEMON, plist_daemon(racine)),
                          (LABEL_BACKUP, plist_backup(racine)),
                          (LABEL_DIGEST, plist_digest(racine))):
        fichier = dossier / f"{label}.plist"
        fichier.write_bytes(plistlib.dumps(charge))
        fichier.chmod(0o644)  # un plist en 600 ou en 664 fait « Load failed: 5 »
        ecrits.append(fichier)
    return ecrits


def _launchctl(*arguments: str) -> tuple[int, str]:
    """Appelle `launchctl` et rend `(code, sortie)`. Jamais fatal."""
    try:
        termine = subprocess.run(["launchctl", *arguments], capture_output=True, text=True,
                                 timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as erreur:
        return 127, str(erreur)
    return termine.returncode, (termine.stdout + termine.stderr).strip()


def domaine() -> str:
    """`gui/<uid>` — le domaine d'un agent utilisateur."""
    return f"gui/{os.getuid()}"


def charger_agent(label: str, racine: Path | None = None) -> tuple[int, str]:
    """`bootout` puis `bootstrap` : recharger, c'est remplacer, jamais empiler.

    Le `bootout` peut échouer (agent absent) : c'est normal et non fatal. La course entre
    `bootout` et `bootstrap` est une cause connue de « Bootstrap failed: 5 » — d'où
    l'attente d'une seconde entre les deux.
    """
    fichier = dossier_agents() / f"{label}.plist"
    if not fichier.exists():
        return 2, f"plist absent : {fichier}"
    # `enable` lève une désactivation persistante posée par un `decharger_agent(durable=True)`
    # précédent : sans lui, `bootstrap` réussit et launchd refuse quand même de lancer l'agent.
    _launchctl("enable", f"{domaine()}/{label}")
    _launchctl("bootout", f"{domaine()}/{label}")
    time.sleep(1.0)
    return _launchctl("bootstrap", domaine(), str(fichier))


def decharger_agent(label: str, *, durable: bool = True) -> tuple[int, str]:
    """`bootout` — l'agent disparaît de `launchctl list`.

    `bootout` seul ne vaut **que pour la session de démarrage en cours** : le plist reste
    dans `~/Library/LaunchAgents/` et launchd le recharge à l'ouverture de session
    suivante. Mesuré le 21/09/2026 — après une panique noyau, `com.bms.factory.daemon`
    « volontairement déchargé » était de retour, prêt à produire sans surveillance.
    `disable` écrit dans la base d'états persistants de launchd et survit au redémarrage ;
    `charger_agent` le lève par `enable`.
    """
    if durable:
        _launchctl("disable", f"{domaine()}/{label}")
    return _launchctl("bootout", f"{domaine()}/{label}")


def charge(label: str) -> bool:
    """Vrai si l'agent est chargé dans le domaine de l'utilisateur."""
    code, _ = _launchctl("print", f"{domaine()}/{label}")
    return code == 0


def liste_agents() -> str:
    """`launchctl list | grep com.bms.factory` — pour la preuve de l'étape."""
    code, sortie = _launchctl("list")
    if code != 0:
        return sortie
    return "\n".join(l for l in sortie.splitlines() if "com.bms.factory" in l) or "(aucun)"
