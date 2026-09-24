"""Alertes et digest quotidien — la supervision sans terminal d'Alek et de Sofiane.

Le canal, et pourquoi il y en a deux.

- **Telegram** dès que `.env` porte `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`. Un bot est
  gratuit et se crée en deux minutes auprès de `@BotFather` (procédure dans
  `docs/EXPLOITATION.md`). C'est le seul canal qui atteigne quelqu'un **qui n'est pas
  devant ce Mac** — donc le seul qui serve à Alek et à Sofiane.
- **Notification macOS** sinon, par `osascript`. Elle ne sort pas de la machine : elle
  dépanne Thomas, elle ne supervise personne. Le système ne s'arrête pas pour autant, et ne
  réclame aucune clé : un canal manquant n'est pas une panne.

Trois règles de fond.

1. **Aucun secret dans une notification.** Ni jeton, ni URL contenant un jeton, ni chemin de
   `secrets/`. `_expurger` du journal fait le même travail sur les événements ; ici, le
   jeton ne figure que dans l'URL d'appel, jamais dans un message ni dans un journal — et
   l'échec d'envoi est journalisé **sans** le corps de la requête.
2. **Une alerte dit quoi faire.** « job 4 bloqué » n'est pas une alerte, c'est un constat.
   Chaque message porte la raison mesurée et la commande qui débloque.
3. **Le digest est la seule lecture quotidienne prévue.** Dix minutes par jour, dont la
   relecture des scripts : tout ce qui n'y figure pas n'existe pas pour l'exploitant.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from factory.core import config as config_module
from factory.core.models import NotificationsConfig, OrchestratorConfig
from factory.core.paths import RunPaths, racine_projet
from factory.orchestrator import journal

#: Motifs d'alerte prévus par l'étape 22.2. Sert au filtrage et aux tests.
MOTIFS: tuple[str, ...] = (
    "job_blocked", "job_failed", "awaiting_review", "disque", "quota", "daemon_arrete",
    "test",
)

#: Plafond de longueur d'un message Telegram (limite de l'API : 4096 caractères).
TAILLE_MAX = 3500


def maintenant() -> str:
    """Horodatage ISO-8601 UTC."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def aujourdhui(racine: Path | None = None) -> str:
    """Date locale au format `AAAA-MM-JJ`, dans le fuseau de l'orchestrateur."""
    from zoneinfo import ZoneInfo

    cfg = _config(racine)
    return datetime.now(UTC).astimezone(ZoneInfo(cfg.timezone)).strftime("%Y-%m-%d")


def _config(racine: Path | None = None) -> OrchestratorConfig:
    """`config/orchestrator.yaml`, ou les valeurs par défaut du modèle."""
    cfg = config_module.charger(racine, strict=False)
    return cfg.orchestrator or OrchestratorConfig()


# --------------------------------------------------------------------------------------
# Choix du canal
# --------------------------------------------------------------------------------------


@dataclass
class Canal:
    """Le canal retenu, et pourquoi. `jeton` ne sort jamais de cet objet."""

    nom: str                    # "telegram" | "macos" | "aucun"
    pourquoi: str
    jeton: str | None = None
    chat: str | None = None

    @property
    def configure(self) -> bool:
        """Vrai si un message peut réellement partir."""
        return self.nom != "aucun"


def canal(racine: Path | None = None, cfg: NotificationsConfig | None = None) -> Canal:
    """Décide par quoi passer. Lit `.env` sans jamais recopier sa valeur ailleurs."""
    cfg = cfg or _config(racine).notifications
    from factory.doctor import charge_env

    charge_env()
    jeton = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if cfg.canal == "aucun":
        return Canal("aucun", "canal désactivé dans config/orchestrator.yaml")
    if cfg.canal in {"auto", "telegram"} and jeton and chat:
        return Canal("telegram", "TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID présents dans .env",
                     jeton=jeton, chat=chat)
    if cfg.canal == "telegram":
        return Canal("aucun", "canal telegram forcé mais TELEGRAM_BOT_TOKEN ou "
                              "TELEGRAM_CHAT_ID manque dans .env")
    if shutil.which("osascript"):
        manque = "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID absents de .env — " if not (jeton and chat) else ""
        return Canal("macos", f"{manque}repli sur la notification locale (elle ne sort pas "
                              f"de cette machine)")
    return Canal("aucun", "ni Telegram configuré ni osascript disponible")


# --------------------------------------------------------------------------------------
# Envoi
# --------------------------------------------------------------------------------------


@dataclass
class Envoi:
    """Résultat d'un envoi. `reponse` est le texte rendu par l'API, jeton exclu."""

    canal: str
    ok: bool
    motif: str
    reponse: str = ""


def envoyer(titre: str, corps: str, *, motif: str = "test", racine: Path | None = None,
            conn: sqlite3.Connection | None = None,
            poster: Callable[[str, str, str], tuple[bool, str]] | None = None) -> Envoi:
    """Envoie une alerte par le canal disponible et journalise le résultat.

    `poster` remplace l'appel réseau dans les tests. Le jeton ne traverse jamais le journal
    ni le message : il n'existe que dans l'URL construite à l'intérieur de `_telegram`.
    """
    racine = racine or racine_projet()
    voie = canal(racine)
    message = f"{titre}\n{corps}".strip()
    if len(message) > TAILLE_MAX:
        message = message[:TAILLE_MAX] + "\n… (tronqué — voir le digest)"
    if not voie.configure:
        resultat = Envoi("aucun", False, motif, voie.pourquoi)
    elif voie.nom == "telegram":
        ok, reponse = (poster or _telegram)(voie.jeton or "", voie.chat or "", message)
        resultat = Envoi("telegram", ok, motif, reponse)
    else:
        ok, reponse = _macos(titre, corps)
        resultat = Envoi("macos", ok, motif, reponse)
    journal.evenement(
        "INFO" if resultat.ok else "WARN",
        f"alerte {motif} : {'envoyée par ' + resultat.canal if resultat.ok else 'NON envoyée'}",
        donnees={"motif": motif, "canal": resultat.canal, "titre": titre,
                 "reponse": resultat.reponse[:300]},
        racine=racine, conn=conn,
    )
    return resultat


def _telegram(jeton: str, chat: str, message: str) -> tuple[bool, str]:
    """`sendMessage` de l'API Bot. Le jeton n'est que dans l'URL, jamais dans un journal."""
    url = f"https://api.telegram.org/bot{jeton}/sendMessage"
    charge = urllib.parse.urlencode({
        "chat_id": chat, "text": message, "disable_web_page_preview": "true",
    }).encode("utf-8")
    requete = urllib.request.Request(url, data=charge, method="POST")
    try:
        with urllib.request.urlopen(requete, timeout=20) as reponse:
            brut = reponse.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError) as erreur:
        # Le message d'erreur d'urllib peut contenir l'URL, donc le jeton : on ne garde que
        # le type et le motif, jamais la chaîne complète.
        return False, f"{type(erreur).__name__} — envoi Telegram impossible"
    try:
        charge_json = json.loads(brut)
    except json.JSONDecodeError:
        return False, "réponse Telegram illisible"
    if not charge_json.get("ok"):
        return False, f"Telegram a refusé : {str(charge_json.get('description'))[:200]}"
    resultat = charge_json.get("result") or {}
    return True, (f"ok message_id={resultat.get('message_id')} "
                  f"chat={(resultat.get('chat') or {}).get('type', '?')} "
                  f"date={resultat.get('date')}")


def _macos(titre: str, corps: str) -> tuple[bool, str]:
    """Notification du centre de notifications. Une ligne : le reste va au digest."""
    def echapper(texte: str) -> str:
        return texte.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " · ")[:240]

    script = (f'display notification "{echapper(corps)}" with title "BMS" '
              f'subtitle "{echapper(titre)}"')
    try:
        termine = subprocess.run(["osascript", "-e", script], capture_output=True, text=True,
                                 timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as erreur:
        return False, f"osascript indisponible : {erreur}"
    if termine.returncode != 0:
        return False, (termine.stderr or termine.stdout).strip()[:200]
    return True, "osascript code 0 — notification affichée sur cette machine"


# --------------------------------------------------------------------------------------
# Les six alertes de l'étape 22.2
# --------------------------------------------------------------------------------------


def alerte_job_bloque(job_id: int, video_id: str, raison: str, *, racine: Path | None = None,
                      conn: sqlite3.Connection | None = None) -> Envoi:
    """Job `blocked` : il attend un humain, et on lui dit lequel et quoi taper."""
    return envoyer(
        f"⛔ job {job_id} bloqué — {video_id}",
        f"{raison}\n\nPour le relancer : factory queue retry {job_id}\n"
        f"Pour l'abandonner : factory queue block {job_id} --reason \"…\"",
        motif="job_blocked", racine=racine, conn=conn,
    )


def alerte_job_echoue(job_id: int, video_id: str, raison: str, *, racine: Path | None = None,
                      conn: sqlite3.Connection | None = None) -> Envoi:
    """Job `failed` après épuisement des tentatives — un défaut, pas une attente."""
    return envoyer(
        f"❌ job {job_id} en échec définitif — {video_id}",
        f"{raison}\n\nJournal : workspace/logs/run_{video_id}.log\n"
        f"Reprendre : factory queue retry {job_id}",
        motif="job_failed", racine=racine, conn=conn,
    )


def alerte_relecture(fiches: list[Any], *, racine: Path | None = None,
                     conn: sqlite3.Connection | None = None) -> Envoi | None:
    """Scripts en attente, **regroupés** : une alerte par lot, jamais une par script.

    C'est la contrainte « par lots » de `ROADMAP` § 3.4 appliquée à l'alerte elle-même. Dix
    notifications pour dix scripts feraient couper les notifications au bout d'une semaine.
    """
    if not fiches:
        return None
    lignes = [f"• {f.titre} ({f.channel_id}, {f.duree_estimee_s:.0f} s)" for f in fiches[:8]]
    if len(fiches) > 8:
        lignes.append(f"… et {len(fiches) - 8} autre(s)")
    return envoyer(
        f"📝 {len(fiches)} script(s) à relire",
        "\n".join(lignes) + "\n\nfactory review --reviewer <ton identifiant>",
        motif="awaiting_review", racine=racine, conn=conn,
    )


def alerte_disque(libre_go: float, seuil_go: float, *, racine: Path | None = None,
                  conn: sqlite3.Connection | None = None) -> Envoi:
    """Disque sous le seuil d'alerte — au-dessus du plancher dur, pour prévenir avant d'arrêter."""
    return envoyer(
        f"💾 disque : {libre_go:.1f} Go libres",
        f"Seuil d'alerte {seuil_go:.0f} Go ; la production s'arrête à 8 Go (CLAUDE.md § 3).\n"
        f"Libérer : factory backup list, puis purge des runs exportés.",
        motif="disque", racine=racine, conn=conn,
    )


def alerte_quota(part: float, seuil: float, detail: str = "", *, racine: Path | None = None,
                 conn: sqlite3.Connection | None = None) -> Envoi:
    """Quota d'API consommé au-delà du seuil. Aucun identifiant de projet dans le message."""
    return envoyer(
        f"📊 quota API à {part * 100:.0f} %",
        f"Seuil d'alerte {seuil * 100:.0f} %. {detail}".strip(),
        motif="quota", racine=racine, conn=conn,
    )


def alerte_daemon_arrete(detail: str, *, racine: Path | None = None,
                         conn: sqlite3.Connection | None = None) -> Envoi:
    """Le daemon n'est plus là : plus rien ne se produit, et personne ne le verrait sinon."""
    return envoyer(
        "🛑 daemon arrêté",
        f"{detail}\n\nRedémarrer : factory daemon install",
        motif="daemon_arrete", racine=racine, conn=conn,
    )


def verifier_et_alerter(conn: sqlite3.Connection, *, racine: Path | None = None) -> list[Envoi]:
    """Passe en revue les six motifs et envoie ce qui doit partir. Appelé par le daemon.

    Une alerte n'est envoyée qu'au **changement d'état** : l'empreinte de ce qui a déjà été
    signalé est gardée dans `workspace/logs/alertes.json`. Sans cela, un job bloqué la nuit
    produirait une notification par tour de boucle, soit 60 par heure.
    """
    racine = racine or racine_projet()
    cfg = _config(racine)
    envois: list[Envoi] = []
    vus = _deja_signale(racine)
    neufs: dict[str, str] = {}

    from factory.orchestrator import review as review_module
    from factory.orchestrator import runner as runner_module

    for job in _jobs(conn, "blocked"):
        cle = f"blocked:{job['id']}:{job['updated_at']}"
        neufs[f"blocked:{job['id']}"] = cle
        if vus.get(f"blocked:{job['id']}") != cle:
            envois.append(alerte_job_bloque(int(job["id"]), str(job["video_id"]),
                                            str(job["last_error"] or "raison non enregistrée"),
                                            racine=racine, conn=conn))
    for job in _jobs(conn, "failed"):
        cle = f"failed:{job['id']}:{job['updated_at']}"
        neufs[f"failed:{job['id']}"] = cle
        if vus.get(f"failed:{job['id']}") != cle:
            envois.append(alerte_job_echoue(int(job["id"]), str(job["video_id"]),
                                            str(job["last_error"] or "raison non enregistrée"),
                                            racine=racine, conn=conn))

    fiches = review_module.en_attente(conn, None, racine)
    if fiches:
        cle = "review:" + ",".join(sorted(f.job.video_id for f in fiches))
        neufs["review"] = cle
        if vus.get("review") != cle:
            envoi = alerte_relecture(fiches, racine=racine, conn=conn)
            if envoi is not None:
                envois.append(envoi)

    libre = runner_module.disque_libre_go()
    if libre < cfg.notifications.disque_alerte_go:
        cle = f"disque:{int(libre)}"
        neufs["disque"] = cle
        if vus.get("disque") != cle:
            envois.append(alerte_disque(libre, cfg.notifications.disque_alerte_go,
                                        racine=racine, conn=conn))

    part, detail = quota_consomme(conn, racine)
    if part is not None and part > cfg.notifications.quota_alerte_part:
        cle = f"quota:{int(part * 20)}"
        neufs["quota"] = cle
        if vus.get("quota") != cle:
            envois.append(alerte_quota(part, cfg.notifications.quota_alerte_part, detail,
                                       racine=racine, conn=conn))

    _noter_signale(racine, neufs)
    return envois


def _jobs(conn: sqlite3.Connection, statut: str) -> list[sqlite3.Row]:
    """Jobs d'un statut donné, les plus récents d'abord."""
    return conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY updated_at DESC", (statut,),
    ).fetchall()


def _chemin_alertes(racine: Path) -> Path:
    """`workspace/logs/alertes.json` — mémoire de ce qui a déjà été signalé."""
    return journal.dossier_logs(racine) / "alertes.json"


def _deja_signale(racine: Path) -> dict[str, str]:
    """Empreintes des alertes déjà parties. Dictionnaire vide si le fichier manque."""
    fichier = _chemin_alertes(racine)
    if not fichier.exists():
        return {}
    try:
        charge = json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return charge if isinstance(charge, dict) else {}


def _noter_signale(racine: Path, neufs: dict[str, str]) -> None:
    """Remplace la mémoire par l'état courant : un job débloqué doit pouvoir réalerter."""
    _chemin_alertes(racine).write_text(
        json.dumps(neufs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Quota d'API
# --------------------------------------------------------------------------------------


def quota_consomme(conn: sqlite3.Connection,
                   racine: Path | None = None) -> tuple[float | None, str]:
    """Part du quota YouTube consommée aujourd'hui, ou `(None, motif)` si non mesurable.

    Depuis l'étape 23.1, `quota_ledger` porte **tous** les appels, publication comprise, et
    les deux compartiments sont distincts : les uploads (100/jour) et les 10 000 unités de
    tout le reste. La part rendue est celle du compartiment **le plus consommé** — une alerte
    à 80 % doit partir dès qu'un des deux sature, pas quand leur moyenne sature.

    `collect_runs` reste la source de repli si l'étape 18 a tourné sans passer par le ledger.
    Rendre `None` plutôt qu'un zéro rassurant : un quota « à 0 % » non mesuré est un mensonge
    qui ferait rater le jour où l'upload s'arrête.
    """
    racine = racine or racine_projet()
    from factory.publish import quota as quota_module

    try:
        plafonds = quota_module.Plafonds.depuis_config(racine)
        etat = quota_module.etat(conn, plafonds)
    except (sqlite3.Error, OSError, ValueError):
        etat = None
    if etat is not None and etat.appels:
        return etat.part_max, (
            f"{etat.unites_utilisees} unités sur {etat.unites_max} et "
            f"{etat.uploads_utilises} upload(s) sur {etat.uploads_max} — "
            f"{quota_module.publications_possibles(etat)} publication(s) encore possible(s)"
        )
    try:
        ligne = conn.execute(
            "SELECT sum(units_used) AS u FROM collect_runs WHERE date = date('now')"
        ).fetchone()
    except sqlite3.Error:
        return None, "quota non comptabilisé"
    if ligne is None or ligne["u"] is None:
        return None, "aucun appel d'API aujourd'hui — rien à comptabiliser"
    unites = float(ligne["u"])
    return unites / 10000.0, f"{unites:.0f} unités sur 10 000 (collecte seule)"


# --------------------------------------------------------------------------------------
# Digest quotidien
# --------------------------------------------------------------------------------------


@dataclass
class Digest:
    """Le contenu du digest, séparé de sa mise en forme pour être testable."""

    date: str
    produits: list[dict[str, Any]] = field(default_factory=list)
    en_attente: list[Any] = field(default_factory=list)
    bloques: list[dict[str, Any]] = field(default_factory=list)
    echoues: list[dict[str, Any]] = field(default_factory=list)
    a_publier: list[dict[str, Any]] = field(default_factory=list)
    #: Vidéos **déjà en ligne et privées** qu'un humain doit programmer dans Studio
    #: (étape 23.1). Distinct de `a_publier`, qui porte les runs pas encore téléversés.
    a_publier_manuel: list[Any] = field(default_factory=list)
    publies: list[dict[str, Any]] = field(default_factory=list)
    quota: tuple[float | None, str] = (None, "")
    disque_go: float = 0.0
    sauvegarde: str = ""
    regenerations: list[dict[str, Any]] = field(default_factory=list)
    daemon: str = ""


def collecter(conn: sqlite3.Connection, date: str | None = None,
              racine: Path | None = None) -> Digest:
    """Rassemble l'état du jour. Ne juge rien : la mise en forme est ailleurs."""
    racine = racine or racine_projet()
    from factory.orchestrator import backup as backup_module
    from factory.orchestrator import daemon as daemon_module
    from factory.orchestrator import review as review_module
    from factory.orchestrator import runner as runner_module

    jour = date or aujourdhui(racine)
    digest = Digest(date=jour)
    depuis = f"{jour}T00:00:00Z"

    for ligne in conn.execute(
        "SELECT * FROM jobs WHERE status IN ('exported', 'published') AND updated_at >= ? "
        "ORDER BY updated_at", (depuis,),
    ):
        entree = {"job": ligne["id"], "video_id": ligne["video_id"],
                  "channel_id": ligne["channel_id"], "statut": ligne["status"],
                  "note": ligne["last_error"] or ""}
        digest.produits.append(entree)
        (digest.publies if ligne["status"] == "published" else digest.a_publier).append(entree)

    digest.en_attente = review_module.en_attente(conn, None, racine)
    for statut, cible in (("blocked", digest.bloques), ("failed", digest.echoues)):
        for ligne in conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY updated_at",
                                  (statut,)):
            cible.append({"job": ligne["id"], "video_id": ligne["video_id"],
                          "channel_id": ligne["channel_id"],
                          "raison": ligne["last_error"] or "raison non enregistrée",
                          "stage": ligne["stage"]})

    for evenement in journal.lire_events(racine, depuis=depuis):
        if "régénération" in str(evenement.get("msg", "")):
            donnees = evenement.get("data") or {}
            digest.regenerations.append({
                "video_id": evenement.get("video_id"), "mesure": donnees.get("mesure"),
                "depuis": donnees.get("depuis"), "levier": donnees.get("levier"),
                "rang": donnees.get("rang"),
            })

    from factory.publish import youtube as publication
    try:
        digest.a_publier_manuel = publication.liste_manuelle(conn, racine)
    except sqlite3.Error:
        digest.a_publier_manuel = []
    digest.quota = quota_consomme(conn, racine)
    digest.disque_go = runner_module.disque_libre_go()
    archive = backup_module.derniere_archive(racine)
    if archive is None:
        digest.sauvegarde = "aucune archive dans ~/BMS-backups"
    else:
        taille = archive.stat().st_size / 1e6
        quand = datetime.fromtimestamp(archive.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        neuve = "" if quand.startswith(jour) else "  ⚠ pas d'archive aujourd'hui"
        digest.sauvegarde = f"{archive.name} — {taille:.1f} Mo, {quand}{neuve}"
    etat = daemon_module.etat(racine)
    digest.daemon = (f"en cours, pid {etat.pid} depuis {etat.depuis}" if etat.vivant
                     else "arrêté" + (" (agent launchd chargé)" if etat.charge_launchd else ""))
    return digest


def rendre(digest: Digest) -> str:
    """Le digest en Markdown — destiné à Alek et Sofiane, donc sans jargon de pipeline."""
    lignes = [f"# Digest BMS — {digest.date}", ""]

    lignes.append(f"## À faire maintenant ({len(digest.en_attente)} script(s) à relire)")
    lignes.append("")
    if digest.en_attente:
        lignes.append("Commande : `factory review --reviewer <ton identifiant>` "
                      "(alek, sofiane ou thomas).")
        lignes.append("")
        lignes.append("| Titre | Chaîne | Durée | Densité | Hook |")
        lignes.append("|---|---|---|---|---|")
        for fiche in digest.en_attente:
            densite = "—" if fiche.densite is None else f"{fiche.densite:.2f}"
            hook = fiche.hook.replace("|", "/")[:70]
            lignes.append(f"| {fiche.titre[:60]} | {fiche.channel_id} | "
                          f"{fiche.duree_estimee_s:.0f} s | {densite} | {hook} |")
    else:
        lignes.append("Rien à relire.")
    lignes.append("")

    lignes.append(f"## Produit aujourd'hui ({len(digest.produits)})")
    lignes.append("")
    if digest.produits:
        for entree in digest.produits:
            note = f" — {entree['note']}" if entree["note"] else ""
            lignes.append(f"- `{entree['video_id']}` ({entree['channel_id']}) : "
                          f"{entree['statut']}{note}")
    else:
        lignes.append("Aucune vidéo terminée aujourd'hui.")
    lignes.append("")

    lignes.append(f"## Bloqué ({len(digest.bloques)}) et en échec ({len(digest.echoues)})")
    lignes.append("")
    if digest.bloques or digest.echoues:
        for entree in digest.bloques + digest.echoues:
            lignes.append(f"- **job {entree['job']}** `{entree['video_id']}` à l'étape "
                          f"`{entree['stage']}` : {entree['raison']}")
    else:
        lignes.append("Rien de bloqué.")
    lignes.append("")

    if digest.regenerations:
        lignes.append(f"## Régénérations du jour ({len(digest.regenerations)})")
        lignes.append("")
        for entree in digest.regenerations:
            lignes.append(f"- `{entree['video_id']}` : {entree['mesure']} → reprise depuis "
                          f"`{entree['depuis']}` ({entree['levier']}, "
                          f"tentative {entree['rang']})")
        lignes.append("")

    lignes.append("## À publier")
    lignes.append("")
    if digest.a_publier_manuel:
        lignes.append("L'audit de l'API n'étant pas passé, ces vidéos sont **en ligne et "
                      "privées** : elles exigent un geste manuel dans YouTube Studio "
                      "(~2 min chacune). Commande : `factory publish manual-list`.")
        lignes.append("")
        lignes.append("| Titre | Chaîne | Date et heure prévues | Studio |")
        lignes.append("|---|---|---|---|")
        for ligne_m in digest.a_publier_manuel:
            lignes.append(f"| {ligne_m.titre[:55]} | {ligne_m.channel_id} | "
                          f"{ligne_m.heure_locale} | {ligne_m.studio_url} |")
        lignes.append("")
    if digest.a_publier:
        lignes.append("Runs exportés, pas encore téléversés :")
        for entree in digest.a_publier:
            lignes.append(f"- `{entree['video_id']}` — `factory publish upload --run "
                          f"{entree['video_id']} --channel {entree['channel_id']}`")
    elif not digest.a_publier_manuel:
        lignes.append("Rien en attente de publication.")
    lignes.append("")

    part, detail = digest.quota
    lignes += [
        "## Machine",
        "",
        f"- Quota API : " + ("non mesuré — " + detail if part is None
                             else f"{part * 100:.0f} % — {detail}"),
        f"- Disque libre : {digest.disque_go:.1f} Go (plancher dur 8 Go)",
        f"- Sauvegarde : {digest.sauvegarde}",
        f"- Daemon : {digest.daemon}",
        "",
        "> ⚠ `~/BMS-backups` est sur le même disque que l'original. Le copier chaque semaine "
        "sur un support externe est un geste **humain** que rien dans le code ne fera.",
        "",
    ]
    return "\n".join(lignes)


def ecrire_digest(conn: sqlite3.Connection, date: str | None = None,
                  racine: Path | None = None) -> Path:
    """Écrit `reports/digest_<date>.md` et renvoie son chemin."""
    racine = racine or racine_projet()
    digest = collecter(conn, date, racine)
    dossier = racine / "reports"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"digest_{digest.date}.md"
    chemin.write_text(rendre(digest), encoding="utf-8")
    return chemin


def envoyer_digest(conn: sqlite3.Connection, date: str | None = None,
                   racine: Path | None = None) -> tuple[Path, Envoi]:
    """Écrit le digest puis en envoie le résumé par le canal d'alerte."""
    racine = racine or racine_projet()
    chemin = ecrire_digest(conn, date, racine)
    digest = collecter(conn, date, racine)
    corps = (f"{len(digest.produits)} produite(s) · {len(digest.en_attente)} à relire · "
             f"{len(digest.bloques)} bloquée(s) · {len(digest.echoues)} en échec\n"
             f"Disque {digest.disque_go:.1f} Go · sauvegarde {digest.sauvegarde.split(' —')[0]}\n"
             f"{chemin.relative_to(racine)}")
    return chemin, envoyer(f"📅 Digest BMS {digest.date}", corps, motif="test",
                           racine=racine, conn=conn)
