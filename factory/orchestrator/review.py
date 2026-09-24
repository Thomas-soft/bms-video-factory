"""Relecture des scripts par lots — la seule intervention éditoriale humaine du système.

Ce que ce module protège, et pourquoi il est écrit ainsi.

1. **Une trace, pas une opinion.** `CONFORMITE` § 4 : la relecture est la pièce qui fait
   tomber l'obligation de divulgation du RIA art. 50 §4 et l'argument central contre la
   qualification « contenu inauthentique » de YouTube. Une approbation qui ne laisse pas de
   relecteur nommé, de date et d'empreinte du texte relu ne vaut rien devant un contrôle.
   Toute décision passe donc par `enregistrer_decision`, qui écrit **quatre** endroits d'un
   coup : `registre/data/reviews.jsonl` (append-only, la pièce), `review_log` (l'index),
   `review.json` (le miroir du run) et le manifeste (les champs de § 10.1).
2. **L'empreinte porte sur le texte, pas sur le run.** Un script réécrit après approbation
   redevient non relu : c'est `runner._script_relu` qui le vérifie, sur `script_sha256`.
   Approuver un run puis en changer le texte est exactement ce qu'un contrôle cherche.
3. **« L'équipe » n'est pas un relecteur.** `--reviewer` est obligatoire et doit exister
   dans `config/team.yaml`. La seule exception est `--auto`, réservée aux chaînes dont
   `auto_approve` est vrai : elle écrit `reviewer = "auto"`, `ria_exception_claimed =
   false`, et affiche un avertissement rouge. Elle n'est pas un raccourci, c'est un risque
   documenté que le client assume par écrit (question ouverte de `STATE.md`).
4. **Un rejet doit produire un texte différent.** Le motif est écrit dans
   `consignes.json`, que `factory script` verse dans son invite système : sans cela, la
   régénération redemanderait au modèle exactement ce qu'il vient d'écrire. Deux rejets au
   plus par script ; au troisième, la machine rend la main à l'humain plutôt que de
   dépenser une heure de LLM de plus.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from factory.core import config as config_module
from factory.core import runs as runs_module
from factory.core.models import RELECTEURS_MACHINE, ReviewRecord, Script
from factory.core.paths import RunPaths, racine_projet
from factory.orchestrator import journal
from factory.orchestrator.queue import ETAPES, ErreurFile, Job, lire, lister

#: Décisions enregistrables. `skipped` n'en est pas une : passer un script, c'est remettre
#: la décision à plus tard, et une ligne « je n'ai pas décidé » polluerait la pièce.
DECISIONS: tuple[str, ...] = ("approved", "approved_with_edits", "rejected", "auto_approved")

#: Décisions qui lèvent la barrière du runner (`runner._script_relu`).
LEVENT: tuple[str, ...] = ("approved", "approved_with_edits", "auto_approved")

#: Fichier de consignes lu par `factory script` — motifs de rejet et remèdes de l'étape 22.2.
NOM_CONSIGNES = "consignes.json"


def maintenant() -> str:
    """Horodatage ISO-8601 UTC, format d'`INTERFACES` § 0."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def empreinte_script(chemins: RunPaths) -> str:
    """SHA-256 du `script.json` tel qu'il est sur le disque, octet pour octet."""
    return hashlib.sha256(chemins.script.read_bytes()).hexdigest()


def chemin_reviews_jsonl(racine: Path | None = None) -> Path:
    """`registre/data/reviews.jsonl` — append-only (`CONFORMITE` § 10.2)."""
    return (racine or racine_projet()) / "registre" / "data" / "reviews.jsonl"


# --------------------------------------------------------------------------------------
# Consignes versées au prompt de `script`
# --------------------------------------------------------------------------------------


def ajouter_consigne(chemins: RunPaths, origine: str, texte: str) -> list[dict[str, str]]:
    """Ajoute une consigne à `consignes.json` du run, et renvoie la liste complète.

    Append, jamais remplacement : un script rejeté deux fois doit porter les deux motifs,
    faute de quoi la seconde réécriture réintroduit le défaut de la première.
    """
    fichier = chemins.racine / NOM_CONSIGNES
    consignes: list[dict[str, str]] = lire_consignes(chemins)
    consignes.append({"ts": maintenant(), "origine": origine, "texte": texte.strip()})
    chemins.racine.mkdir(parents=True, exist_ok=True)
    fichier.write_text(json.dumps(consignes, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return consignes


def lire_consignes(chemins: RunPaths) -> list[dict[str, str]]:
    """Consignes déjà posées sur ce run. Liste vide si le fichier manque ou est illisible."""
    fichier = chemins.racine / NOM_CONSIGNES
    if not fichier.exists():
        return []
    try:
        charge = json.loads(fichier.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return charge if isinstance(charge, list) else []


def bloc_consignes(chemins: RunPaths) -> str:
    """Les consignes mises en forme pour une invite système, ou chaîne vide s'il n'y en a pas.

    Appelé par `factory/steps/script.py` : c'est le seul chemin par lequel un motif de rejet
    humain atteint le modèle.
    """
    consignes = lire_consignes(chemins)
    if not consignes:
        return ""
    lignes = [f"- [{c.get('origine', '?')}] {c.get('texte', '').strip()}"
              for c in consignes if c.get("texte")]
    if not lignes:
        return ""
    return ("\n\nMANDATORY CORRECTIONS — a previous version of this script was rejected. "
            "Apply every point below; producing the same text again is a failure.\n"
            + "\n".join(lignes))


# --------------------------------------------------------------------------------------
# Écriture d'une décision — chemin unique
# --------------------------------------------------------------------------------------


def enregistrer_decision(
    conn: sqlite3.Connection, video_id: str, channel_id: str, *, reviewer: str,
    decision: str, motif: str | None = None, batch_id: str | None = None,
    racine: Path | None = None, edits: list[dict[str, str]] | None = None,
) -> str:
    """Écrit la décision aux quatre endroits qui font preuve. Renvoie l'empreinte du script.

    L'ordre compte : la pièce append-only d'abord (`reviews.jsonl`), l'index ensuite. Si le
    processus meurt entre les deux, `factory queue reindex` reconstruit l'index depuis les
    fichiers ; l'inverse serait une preuve perdue.
    """
    racine = racine or racine_projet()
    if decision not in DECISIONS:
        raise ErreurFile(f"décision inconnue : {decision} ({', '.join(DECISIONS)})")
    if decision in {"rejected", "approved_with_edits", "auto_approved"} and not (motif or "").strip():
        raise ErreurFile(f"décision « {decision} » : un motif est obligatoire")
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.script.exists():
        raise ErreurFile(f"{video_id} : script.json absent, rien à relire")
    empreinte = empreinte_script(chemins)
    quand = maintenant()
    lot = batch_id or f"{reviewer}-{quand[:10]}"

    # 1 — la pièce, append-only, jamais réécrite (CONFORMITE § 10.2).
    fichier = chemin_reviews_jsonl(racine)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    with fichier.open("a", encoding="utf-8") as flux:
        flux.write(json.dumps({
            "review_hash": empreinte, "run_id": video_id, "channel_id": channel_id,
            "reviewer": reviewer, "review_date": quand, "decision": decision,
            "comment": (motif or "").strip(), "script_excerpt_hash": empreinte[:16],
            "batch_id": lot,
        }, ensure_ascii=False) + "\n")

    # 2 — l'index, qui peut se reconstruire.
    conn.execute(
        "INSERT INTO review_log (video_id, channel_id, reviewer, decision, motif, "
        "script_sha256, timestamp, batch_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (video_id, channel_id, reviewer, decision, (motif or "").strip()[:500] or None,
         empreinte, quand, lot),
    )

    # 3 — le miroir du run.
    record = ReviewRecord(
        reviewer=reviewer, review_date=quand, review_hash=empreinte, decision=_decision_modele(decision),
        comment=(motif or "").strip(), edits=edits or [], batch_id=lot,
        ria_exception_claimed=reviewer not in RELECTEURS_MACHINE,
    )
    runs_module.ecrire_json(chemins.review, record)

    # 4 — le manifeste : les champs de CONFORMITE § 10.1 que la publication exige.
    _porter_au_manifeste(video_id, racine, record)
    return empreinte


def _decision_modele(decision: str) -> str:
    """`review_log` garde `auto_approved` (valeur historique) ; le modèle dit `auto`."""
    return "auto" if decision == "auto_approved" else decision


def _porter_au_manifeste(video_id: str, racine: Path, record: ReviewRecord) -> None:
    """Recopie la décision dans `manifest.json`. Une erreur ici n'annule pas la pièce."""
    try:
        manifest = runs_module.charger_manifest(video_id, racine)
    except (FileNotFoundError, ValueError):
        return
    manifest.conformite.reviewer = record.reviewer
    manifest.conformite.review_hash = record.review_hash
    manifest.conformite.review_date = record.review_date
    manifest.conformite.review_decision = record.decision
    manifest.conformite.ria_exception_claimed = record.ria_exception_claimed
    chemins = RunPaths.depuis_video_id(video_id, racine)
    runs_module.ecrire_json(chemins.manifest, manifest)


def relectures(conn: sqlite3.Connection, video_id: str) -> list[sqlite3.Row]:
    """Toutes les décisions portées sur un run, de la plus ancienne à la plus récente."""
    return conn.execute(
        "SELECT * FROM review_log WHERE video_id = ? ORDER BY timestamp, id", (video_id,),
    ).fetchall()


def rejets(conn: sqlite3.Connection, video_id: str) -> int:
    """Combien de fois ce run a déjà été rejeté. Plafonné par `rejets_max`."""
    ligne = conn.execute(
        "SELECT count(*) AS n FROM review_log WHERE video_id = ? AND decision = 'rejected'",
        (video_id,),
    ).fetchone()
    return int(ligne["n"]) if ligne else 0


# --------------------------------------------------------------------------------------
# Ce que le relecteur voit
# --------------------------------------------------------------------------------------


@dataclass
class Apercu:
    """Le script tel qu'il se juge en trente secondes, sans ouvrir de fichier."""

    job: Job
    titre: str
    channel_id: str
    sujet: str
    angle: str
    hook_type: str
    hook: str
    duree_estimee_s: float
    duree_cible_s: int
    densite: float | None
    premieres_lignes: list[str]
    n_segments: int
    mots: int
    rejets: int = 0
    alertes: list[str] = field(default_factory=list)

    @property
    def ecart_duree(self) -> str:
        """Écart à la cible, en pourcentage signé — la lecture utile, pas deux nombres."""
        if not self.duree_cible_s:
            return "—"
        part = (self.duree_estimee_s - self.duree_cible_s) / self.duree_cible_s * 100
        return f"{part:+.0f} %"


def _densite(video_id: str, racine: Path) -> float | None:
    """Densité de faits par minute mesurée à l'étape `script`, lue dans le manifeste."""
    try:
        manifest = runs_module.charger_manifest(video_id, racine)
    except (FileNotFoundError, ValueError):
        return None
    return manifest.decisions.density_facts_per_min


def apercu(conn: sqlite3.Connection, job: Job, racine: Path | None = None) -> Apercu:
    """Construit la fiche d'un job en attente. Lève si le script est illisible."""
    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(job.video_id, racine)
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    spec = runs_module.charger_spec(job.video_id, racine)
    alertes: list[str] = []
    angle = script.editorial_signature.angle
    try:
        manifest = runs_module.charger_manifest(job.video_id, racine)
        titre = manifest.decisions.title_chosen or spec.topic.sujet
    except (FileNotFoundError, ValueError):
        titre = spec.topic.sujet
    lignes = [s.narration.strip() for s in script.segments if s.role != "hook"][:3]
    if not lignes:
        lignes = [s.narration.strip() for s in script.segments][:3]
    if job.last_error:
        alertes.append(job.last_error)
    if spec.parent_id:
        # Étape 24 : le relecteur juge une adaptation, pas un texte neuf.
        alertes.insert(0, f"DÉCLINAISON de {spec.parent_id} → {spec.lang} : relire l'adaptation "
                          "(références, unités, nombres), pas seulement la langue")
    return Apercu(
        job=job, titre=titre, channel_id=job.channel_id, sujet=spec.topic.sujet, angle=angle,
        hook_type=script.hook.type, hook=script.hook.text.strip(),
        duree_estimee_s=script.estimated_duration_s, duree_cible_s=spec.target_duration_s,
        densite=_densite(job.video_id, racine), premieres_lignes=lignes,
        n_segments=len(script.segments), mots=script.word_count,
        rejets=rejets(conn, job.video_id), alertes=alertes,
    )


def en_attente(conn: sqlite3.Connection, channel: str | None = None,
               racine: Path | None = None) -> list[Apercu]:
    """Les jobs `awaiting_review` dont le script est lisible, du plus ancien au plus récent.

    Un job qui attend une décision humaine **sans** script (code 7 d'une autre étape) n'est
    pas une relecture de script : il est écarté de la liste plutôt que d'y figurer vide.
    """
    racine = racine or racine_projet()
    fiches: list[Apercu] = []
    for job in lister(conn, ["awaiting_review"]):
        if channel and job.channel_id != channel:
            continue
        chemins = RunPaths.depuis_video_id(job.video_id, racine)
        if not chemins.script.exists():
            continue
        try:
            fiches.append(apercu(conn, job, racine))
        except (ValueError, FileNotFoundError) as erreur:
            journal.evenement("WARN", f"job {job.id} illisible pour la relecture : {erreur}",
                              job=job.id, video_id=job.video_id, racine=racine)
    return fiches


# --------------------------------------------------------------------------------------
# Les quatre décisions
# --------------------------------------------------------------------------------------


def approuver(conn: sqlite3.Connection, fiche: Apercu, reviewer: str, *,
              racine: Path | None = None, avec_edits: bool = False,
              motif: str | None = None, batch_id: str | None = None) -> Job:
    """`a` — le script passe, le job repart à l'étape où la barrière l'avait arrêté."""
    racine = racine or racine_projet()
    job = fiche.job
    empreinte = enregistrer_decision(
        conn, job.video_id, job.channel_id, reviewer=reviewer,
        decision="approved_with_edits" if avec_edits else "approved",
        motif=motif, batch_id=batch_id, racine=racine,
    )
    conn.execute(
        "UPDATE jobs SET status = 'queued', attempts = 0, next_run_at = NULL, "
        "last_error = NULL, locked_by = NULL, locked_at = NULL, updated_at = ? WHERE id = ?",
        (maintenant(), job.id),
    )
    journal.evenement(
        "INFO", f"job {job.id} approuvé par {reviewer}", job=job.id, video_id=job.video_id,
        stage=job.stage, donnees={"reviewer": reviewer, "script_sha256": empreinte,
                                  "decision": "approved_with_edits" if avec_edits else "approved",
                                  "motif": motif},
        racine=racine, conn=conn,
    )
    return lire(conn, job.id)


def rejeter(conn: sqlite3.Connection, fiche: Apercu, reviewer: str, motif: str, *,
            racine: Path | None = None, batch_id: str | None = None,
            rejets_max: int = 2) -> Job:
    """`r` — le script repart à l'étape `script`, le motif versé dans l'invite du modèle.

    Au-delà de `rejets_max`, le job passe `blocked` : une troisième réécriture coûterait
    quinze minutes de LLM pour un texte que deux humains ont déjà refusé.
    """
    racine = racine or racine_projet()
    job = fiche.job
    motif = (motif or "").strip()
    if not motif:
        raise ErreurFile("un rejet sans motif ne dit pas quoi réécrire : motif obligatoire")
    chemins = RunPaths.depuis_video_id(job.video_id, racine)
    enregistrer_decision(conn, job.video_id, job.channel_id, reviewer=reviewer,
                         decision="rejected", motif=motif, batch_id=batch_id, racine=racine)
    deja = rejets(conn, job.video_id)
    if deja > rejets_max:
        raison = (f"script rejeté {deja} fois (plafond {rejets_max}) — dernier motif : {motif}")
        conn.execute(
            "UPDATE jobs SET status = 'blocked', last_error = ?, locked_by = NULL, "
            "locked_at = NULL, updated_at = ? WHERE id = ?",
            (raison[:500], maintenant(), job.id),
        )
        journal.evenement("BLOCK", f"job {job.id} bloqué : {raison}", job=job.id,
                          video_id=job.video_id, stage=job.stage,
                          donnees={"reviewer": reviewer, "rejets": deja},
                          racine=racine, conn=conn)
        return lire(conn, job.id)

    ajouter_consigne(chemins, f"rejet {deja}/{rejets_max} par {reviewer}", motif)
    # Le script doit être **réécrit**, donc son marqueur d'idempotence saute, ainsi que ceux
    # de l'aval : sans cela, `etape_faite` déclarerait `script` déjà faite et le job
    # repartirait sur le texte refusé.
    invalider_depuis(chemins, "script")
    conn.execute(
        "UPDATE jobs SET status = 'queued', stage = 'script', attempts = 0, "
        "next_run_at = NULL, last_error = ?, locked_by = NULL, locked_at = NULL, "
        "updated_at = ? WHERE id = ?",
        (f"rejeté par {reviewer} : {motif}"[:500], maintenant(), job.id),
    )
    journal.evenement(
        "WARN", f"job {job.id} rejeté par {reviewer} — réécriture du script",
        job=job.id, video_id=job.video_id, stage="script",
        donnees={"reviewer": reviewer, "motif": motif, "rejets": deja,
                 "rejets_max": rejets_max},
        racine=racine, conn=conn,
    )
    return lire(conn, job.id)


def invalider_depuis(chemins: RunPaths, etape: str) -> list[str]:
    """Efface les marqueurs `.done` de l'étape et de toutes ses suivantes. Renvoie la liste.

    C'est la traduction de « seulement l'étape fautive et les suivantes » : les marqueurs en
    amont restent, donc leur travail aussi. Le piège relevé le 18/09/2026 (un `script.json`
    réécrit hors pipeline pendant que `script.done` datait de la veille) vient de l'oubli de
    ce geste.
    """
    if etape not in ETAPES:
        raise ErreurFile(f"étape inconnue : {etape} ({', '.join(ETAPES)})")
    efface: list[str] = []
    for suivante in ETAPES[ETAPES.index(etape):]:
        marqueur = chemins.done(suivante)
        if marqueur.exists():
            marqueur.unlink()
            efface.append(suivante)
    return efface


def editer(conn: sqlite3.Connection, fiche: Apercu, reviewer: str, *,
           racine: Path | None = None, batch_id: str | None = None,
           editeur: str | None = None,
           ouvrir: Callable[[list[str]], int] | None = None) -> tuple[Job, list[str]]:
    """`e` — ouvre `script.json` dans `$EDITOR`, revalide, re-vérifie, puis approuve.

    Trois contrôles après l'édition, dans cet ordre : JSON lisible, modèle pydantic valide,
    puis le vérificateur de l'étape 16 (rétention et règles de hook). Un script édité à la
    main qui ne passe plus le vérificateur est **refusé** — le fichier est restauré et la
    décision n'est pas écrite. Laisser passer reviendrait à faire de l'édition humaine une
    porte dérobée autour du seul contrôle automatique du texte.
    """
    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(fiche.job.video_id, racine)
    avant = chemins.script.read_bytes()
    commande = shlex.split(editeur or os.environ.get("EDITOR") or "vi") + [str(chemins.script)]
    code = (ouvrir or _lancer_editeur)(commande)
    if code != 0:
        raise ErreurFile(f"l'éditeur a rendu {code} — script inchangé")
    apres = chemins.script.read_bytes()
    if apres == avant:
        raise ErreurFile("script inchangé — aucune décision écrite")
    try:
        script = Script.model_validate_json(apres.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as erreur:
        chemins.script.write_bytes(avant)
        raise ErreurFile(f"script édité refusé par pydantic, version d'origine restaurée : "
                         f"{str(erreur)[:400]}") from erreur
    alertes = _verifier(fiche.job.video_id, racine)
    if alertes and any(a.startswith("[bloquant]") for a in alertes):
        chemins.script.write_bytes(avant)
        raise ErreurFile("script édité refusé par le vérificateur (étape 16), version "
                         "d'origine restaurée : " + " ; ".join(alertes[:3]))
    # Le texte a changé : l'aval doit être refait, marqueurs compris.
    invalider_depuis(chemins, "voice")
    edits = [{"champ": "script.json",
              "avant_sha256": hashlib.sha256(avant).hexdigest()[:16],
              "apres_sha256": hashlib.sha256(apres).hexdigest()[:16]}]
    empreinte = enregistrer_decision(
        conn, fiche.job.video_id, fiche.job.channel_id, reviewer=reviewer,
        decision="approved_with_edits",
        motif=f"édité par {reviewer} : {script.word_count} mots, "
              f"{len(script.segments)} segments", batch_id=batch_id, racine=racine, edits=edits,
    )
    conn.execute(
        "UPDATE jobs SET status = 'queued', attempts = 0, next_run_at = NULL, "
        "last_error = NULL, locked_by = NULL, locked_at = NULL, updated_at = ? WHERE id = ?",
        (maintenant(), fiche.job.id),
    )
    journal.evenement(
        "INFO", f"job {fiche.job.id} édité puis approuvé par {reviewer}", job=fiche.job.id,
        video_id=fiche.job.video_id, stage=fiche.job.stage,
        donnees={"reviewer": reviewer, "script_sha256": empreinte, "alertes": alertes},
        racine=racine, conn=conn,
    )
    return lire(conn, fiche.job.id), alertes


def _lancer_editeur(commande: list[str]) -> int:
    """Lance `$EDITOR` en lui rendant le terminal. Séparé pour que les tests l'injectent."""
    return subprocess.run(commande, check=False).returncode


def _verifier(video_id: str, racine: Path) -> list[str]:
    """Rejoue le vérificateur de rétention de l'étape 16 et renvoie ses alertes.

    Import tardif : `factory.steps.script` importe ce module pour y lire les consignes de
    relecture, l'importer en tête créerait un cycle. C'est le prix d'un motif de rejet qui
    atteint réellement le prompt du modèle.
    """
    try:
        from factory.steps import script as script_module
        rapport = script_module.verifier_run(video_id, racine)
    except (FileNotFoundError, ValueError, KeyError, ImportError) as erreur:
        return [f"vérificateur non exécuté : {erreur}"]
    alertes: list[str] = []
    for infraction in getattr(rapport, "bloquantes", []):
        alertes.append(f"[bloquant] {getattr(infraction, 'code', '?')} — "
                       f"{getattr(infraction, 'message', '')}")
    for infraction in getattr(rapport, "avertissements", []):
        alertes.append(f"{getattr(infraction, 'code', '?')} — "
                       f"{getattr(infraction, 'message', '')}")
    return alertes


def passer(conn: sqlite3.Connection, fiche: Apercu, racine: Path | None = None) -> None:
    """`s` — remettre la décision à plus tard. Rien dans `review_log` : rien n'a été décidé."""
    journal.evenement("INFO", f"job {fiche.job.id} passé — décision remise à plus tard",
                      job=fiche.job.id, video_id=fiche.job.video_id, racine=racine, conn=conn)


# --------------------------------------------------------------------------------------
# `--auto` : la levée sans lecture, réservée aux chaînes qui l'ont actée
# --------------------------------------------------------------------------------------


def auto_approuver(conn: sqlite3.Connection, channel: str, *, racine: Path | None = None,
                   motif: str | None = None,
                   echo: Callable[[str], None] | None = None) -> list[Job]:
    """`factory review --auto --channel X` — n'existe que si `channel.auto_approve` est vrai.

    Écrit `reviewer = "auto"` et `ria_exception_claimed = false` : l'exception éditoriale du
    RIA art. 50 §4 **tombe** pour ces vidéos, et le manifeste le dit. C'est le seul mode du
    système qui produise une vidéo qu'aucun humain n'a lue ; il est offert parce que la
    promesse d'autonomie l'exige, et tracé pour que personne ne le découvre après coup.
    """
    racine = racine or racine_projet()
    dire = echo or (lambda _: None)
    cfg = config_module.charger(racine, strict=False)
    chaine = cfg.channels.get(channel)
    if chaine is None:
        raise ErreurFile(f"chaîne inconnue : {channel}")
    if not getattr(chaine, "auto_approve", False):
        raise ErreurFile(
            f"`--auto` refusé sur {channel} : `auto_approve` est false dans "
            f"config/channels/{channel}.yaml. Le passer à true retire l'exception "
            f"éditoriale du RIA art. 50 §4 pour toutes les vidéos de cette chaîne "
            f"(CONFORMITE § 4) — c'est une décision du client, pas une option de confort."
        )
    liberes: list[Job] = []
    for fiche in en_attente(conn, channel, racine):
        empreinte = enregistrer_decision(
            conn, fiche.job.video_id, fiche.job.channel_id, reviewer="auto",
            decision="auto_approved",
            motif=motif or f"auto_approve actif sur {channel} — aucun humain n'a lu ce script",
            racine=racine,
        )
        conn.execute(
            "UPDATE jobs SET status = 'queued', attempts = 0, next_run_at = NULL, "
            "last_error = NULL, locked_by = NULL, locked_at = NULL, updated_at = ? "
            "WHERE id = ?", (maintenant(), fiche.job.id),
        )
        journal.evenement(
            "WARN", f"job {fiche.job.id} levé SANS LECTURE (auto_approve sur {channel})",
            job=fiche.job.id, video_id=fiche.job.video_id, stage=fiche.job.stage,
            donnees={"reviewer": "auto", "script_sha256": empreinte,
                     "ria_exception_claimed": False}, racine=racine, conn=conn,
        )
        liberes.append(lire(conn, fiche.job.id))
        dire(f"{fiche.job.video_id} : levé sans lecture")
    return liberes


# --------------------------------------------------------------------------------------
# Boucle de relecture
# --------------------------------------------------------------------------------------


@dataclass
class Bilan:
    """Ce qu'a produit un passage de relecture."""

    reviewer: str
    batch_id: str
    approuves: list[str] = field(default_factory=list)
    rejetes: list[str] = field(default_factory=list)
    edites: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    erreurs: list[str] = field(default_factory=list)

    @property
    def decisions(self) -> int:
        """Nombre de décisions écrites — les scripts passés n'en sont pas."""
        return len(self.approuves) + len(self.rejetes) + len(self.edites)


def verifier_relecteur(reviewer: str, racine: Path | None = None) -> str:
    """Vérifie que le relecteur existe dans `config/team.yaml`. Renvoie son nom affichable."""
    cfg = config_module.charger(racine, strict=False)
    connus = {r.id: r.nom for r in (cfg.team.relecteurs if cfg.team else [])}
    identifiant = (reviewer or "").strip().lower()
    if identifiant not in connus:
        raise ErreurFile(
            f"relecteur inconnu : « {reviewer} » — `config/team.yaml` en connaît "
            f"{', '.join(sorted(connus)) or 'aucun'}. « L'équipe » n'est pas une réponse "
            f"valable (CONFORMITE § 4) : le champ `reviewer` porte une identité."
        )
    return connus[identifiant]


def relire(
    conn: sqlite3.Connection, reviewer: str, *, channel: str | None = None,
    racine: Path | None = None, demander: Callable[[Apercu], tuple[str, str]] | None = None,
    afficher: Callable[[Apercu, int, int], None] | None = None,
    echo: Callable[[str], None] | None = None, rejets_max: int = 2,
    editeur: str | None = None,
) -> Bilan:
    """Parcourt les scripts en attente et applique la décision rendue pour chacun.

    `demander` rend `(touche, texte)` : c'est l'interface que la CLI branche sur le terminal
    et que les tests branchent sur une liste. Le module ne lit jamais l'entrée standard
    lui-même — c'est ce qui rend la relecture testable sans terminal.
    """
    racine = racine or racine_projet()
    identifiant = (reviewer or "").strip().lower()
    verifier_relecteur(identifiant, racine)
    lot = f"{identifiant}-{maintenant()[:10]}"
    bilan = Bilan(reviewer=identifiant, batch_id=lot)
    fiches = en_attente(conn, channel, racine)
    for rang, fiche in enumerate(fiches, start=1):
        if afficher is not None:
            afficher(fiche, rang, len(fiches))
        touche, texte = (demander or (lambda _f: ("s", "")))(fiche)
        touche = (touche or "s").strip().lower()[:1]
        try:
            if touche == "a":
                approuver(conn, fiche, identifiant, racine=racine, batch_id=lot)
                bilan.approuves.append(fiche.job.video_id)
            elif touche == "r":
                rejeter(conn, fiche, identifiant, texte, racine=racine, batch_id=lot,
                        rejets_max=rejets_max)
                bilan.rejetes.append(fiche.job.video_id)
            elif touche == "e":
                _, alertes = editer(conn, fiche, identifiant, racine=racine, batch_id=lot,
                                    editeur=editeur)
                bilan.edites.append(fiche.job.video_id)
                for alerte in alertes:
                    (echo or (lambda _: None))(f"  {alerte}")
            elif touche == "q":
                break
            else:
                passer(conn, fiche, racine)
                bilan.passes.append(fiche.job.video_id)
        except ErreurFile as erreur:
            bilan.erreurs.append(f"{fiche.job.video_id} : {erreur}")
            (echo or (lambda _: None))(f"  {erreur}")
    return bilan


def texte_apercu(fiche: Apercu, rang: int = 1, total: int = 1) -> str:
    """La fiche en texte brut — même contenu que l'affichage riche, pour les tests et le digest."""
    densite = "—" if fiche.densite is None else f"{fiche.densite:.2f}"
    lignes = [
        f"[{rang}/{total}] {fiche.titre}",
        f"  chaîne {fiche.channel_id} · sujet « {fiche.sujet} » · angle {fiche.angle}",
        f"  hook ({fiche.hook_type}) : {fiche.hook}",
        f"  durée estimée {fiche.duree_estimee_s:.0f} s pour {fiche.duree_cible_s} s "
        f"({fiche.ecart_duree}) · densité {densite} faits/min · {fiche.n_segments} segments "
        f"· {fiche.mots} mots",
    ]
    for ligne in fiche.premieres_lignes:
        lignes.append(f"  │ {ligne}")
    if fiche.rejets:
        lignes.append(f"  déjà rejeté {fiche.rejets} fois")
    for alerte in fiche.alertes:
        lignes.append(f"  ⚠ {alerte}")
    return "\n".join(lignes)


def attente_depassee(conn: sqlite3.Connection, heures: int,
                     racine: Path | None = None) -> list[Apercu]:
    """Scripts en attente depuis plus de `heures` — `team.delai_max_heures` par défaut."""
    limite = datetime.now(UTC).timestamp() - heures * 3600
    tardifs: list[Apercu] = []
    for fiche in en_attente(conn, None, racine):
        ligne = conn.execute("SELECT updated_at FROM jobs WHERE id = ?",
                             (fiche.job.id,)).fetchone()
        if ligne is None or not ligne["updated_at"]:
            continue
        try:
            quand = datetime.strptime(str(ligne["updated_at"]), "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
        if quand.replace(tzinfo=UTC).timestamp() < limite:
            tardifs.append(fiche)
    return tardifs
