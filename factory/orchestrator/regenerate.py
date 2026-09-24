"""Régénération ciblée après un FAIL du banc : rejouer l'étape fautive, pas le run.

Trois règles, et chacune vient d'une mesure de l'étape 22.1.

1. **Le remède part de l'étape fautive, jamais du début.** Une vidéo neuve coûte ≈ 4 h 15 de
   machine, dont 3 h 14 de rendu. Rejouer `script` pour un niveau sonore hors norme
   dépenserait ces quatre heures pour un défaut que 198 s de remontage corrigent. La table
   `remedes` de `config/orchestrator.yaml` associe donc chaque **mesure du banc** à une
   étape de départ, et `invalider_depuis` efface les marqueurs de cette étape **et des
   suivantes** seulement.
2. **Rejouer sans rien changer ne change rien.** C'est la leçon de `respiration`, qui a varié
   d'un facteur 95 entre deux runs de la même chaîne sans qu'aucun paramètre ait bougé : le
   hasard n'est pas un remède. Chaque remède porte donc un **levier** — graine suivante,
   gabarit suivant, assets forcément différents, consigne versée au prompt — et un remède
   sans levier (`aucun`) n'est employé que là où le déterminisme est réel : le montage, le
   mixage, l'encodage.
3. **Deux reprises, puis un humain.** Au-delà, la machine dépense sans converger. Le job
   passe `blocked` avec la raison exacte et les métriques, pas avec « qc a échoué ».

Ce module ne lance rien lui-même : il **prépare** le run et rend la main au runner, qui
possède les garde-fous, la fenêtre de production et le verrou. Un module qui lancerait des
étapes de son côté ferait tourner deux runs à la fois.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from factory.core import config as config_module
from factory.core import runs as runs_module
from factory.core.models import OrchestratorConfig, Regeneration, Remede
from factory.core.paths import RunPaths, racine_projet
from factory.eval.bench import ETAPE_CORRECTRICE
from factory.orchestrator import journal, review
from factory.orchestrator.queue import ETAPES, Job

#: Étapes qui ne se rejouent pas : `plan` fixe l'identité du run, `qc` est le juge.
INREJOUABLES: frozenset[str] = frozenset({"plan", "qc"})


def maintenant() -> str:
    """Horodatage ISO-8601 UTC."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Mesure:
    """Une mesure du banc sortie en `fail`, telle que `qc.json` la porte."""

    nom: str
    valeur: float | bool | None
    cible: float | None
    bloquante: bool
    note: str = ""
    unite: str = ""

    def __str__(self) -> str:
        cible = "—" if self.cible is None else f"{self.cible}"
        marque = "[bloquant] " if self.bloquante else ""
        unite = f" {self.unite}" if self.unite else ""
        return f"{marque}{self.nom} = {self.valeur}{unite} (cible {cible})"


@dataclass
class Diagnostic:
    """Ce que le banc reproche au run, et ce que l'orchestrateur compte en faire."""

    video_id: str
    verdict: str
    verdict_pipeline: str
    score: float
    echecs: list[Mesure] = field(default_factory=list)
    raisons: list[str] = field(default_factory=list)
    #: Étapes nommées par `qc.json → regenerate_steps`, telles quelles.
    etapes_qc: list[str] = field(default_factory=list)

    @property
    def resume(self) -> str:
        """Une ligne pour le journal, une alerte ou le digest."""
        if self.echecs:
            return " · ".join(str(m) for m in self.echecs[:4])
        return " · ".join(self.raisons[:2]) or f"score {self.score}"


def lire_qc(video_id: str, racine: Path | None = None) -> Diagnostic:
    """Relit `qc.json` et en extrait les mesures en échec. Lève si le fichier manque."""
    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.qc.exists():
        raise FileNotFoundError(f"{video_id} : qc.json absent — le banc n'a pas tourné")
    charge = json.loads(chemins.qc.read_text(encoding="utf-8"))
    echecs: list[Mesure] = []
    for nom, mesure in (charge.get("metrics") or {}).items():
        # `qc.json` porte les mesures en anglais (`value`, `target`, `blocking`, `status`) :
        # c'est le contrat d'`INTERFACES` § qc.json, pas un choix d'ici.
        if not isinstance(mesure, dict) or mesure.get("status") != "fail":
            continue
        echecs.append(Mesure(
            nom=nom, valeur=mesure.get("value"), cible=mesure.get("target"),
            bloquante=bool(mesure.get("blocking")), note=str(mesure.get("note") or ""),
            unite=str(mesure.get("unit") or ""),
        ))
    # Les bloquantes d'abord : c'est par elles qu'une vidéo est refusée quel que soit le score.
    echecs.sort(key=lambda m: (not m.bloquante, m.nom))
    return Diagnostic(
        video_id=video_id, verdict=str(charge.get("verdict", "FAIL")),
        verdict_pipeline=str(charge.get("verdict_pipeline", "regenerate")),
        score=float(charge.get("score") or 0.0), echecs=echecs,
        raisons=[str(r) for r in (charge.get("reasons") or [])],
        etapes_qc=[str(e) for e in (charge.get("regenerate_steps") or [])],
    )


@dataclass
class Plan:
    """Le remède retenu : d'où l'on repart, pourquoi, et ce qu'on change avant.

    `mesure` peut être vide : `qc.json` sait refuser un run sur un **plancher de famille**
    ou un score global sans qu'aucune mesure n'ait le statut `fail` (objection A1 de l'étape
    15). Le remède se déduit alors de `regenerate_steps`.
    """

    depuis: str
    mesure: str
    remede: Remede
    explication: str


def choisir(diagnostic: Diagnostic, cfg: OrchestratorConfig,
            deja_tentes: set[tuple[str, str]] | None = None) -> Plan | None:
    """Choisit le remède le moins cher qui traite un échec. `None` si aucun ne s'applique.

    « Le moins cher » = **le plus tardif dans le DAG**, et c'est arithmétique, pas esthétique :
    repartir de `assemble` coûte 198 s + 25 s + 45 s ; repartir de `script` coûte 918 s plus
    tout l'aval, soit ≈ 4 h avec le rendu. Quand plusieurs mesures échouent, corriger la
    plus tardive et remesurer est donc toujours préférable à tout rejouer — et si l'échec
    amont persiste, la seconde régénération s'en chargera.

    `deja_tentes` porte les couples `(mesure, étape)` des régénérations précédentes de ce
    run. Un remède qui a déjà échoué sur la même mesure n'est pas rejoué : il produirait le
    même verdict pour le même prix. C'est la différence entre « deux tentatives » et « deux
    fois la même tentative ».
    """
    deja_tentes = deja_tentes or set()
    candidats: list[Plan] = []
    for mesure in diagnostic.echecs:
        remede = cfg.remedes.get(mesure.nom)
        if remede is None:
            etape = ETAPE_CORRECTRICE.get(mesure.nom)
            if not etape:
                continue
            remede = Remede(depuis=etape, levier="aucun",
                            pourquoi="hors table des remèdes : étape déduite du banc, "
                                     "sans levier — la reprise peut redonner le même résultat")
        if remede.depuis in INREJOUABLES or remede.depuis not in ETAPES:
            continue
        if (mesure.nom, remede.depuis) in deja_tentes:
            continue
        candidats.append(Plan(
            depuis=remede.depuis, mesure=mesure.nom, remede=remede,
            explication=f"{mesure} → {remede.depuis} ({remede.levier})",
        ))
    if not candidats:
        # Aucune mesure nommée : le banc refuse sur un plancher de famille ou sur le score.
        for etape in reversed(diagnostic.etapes_qc):
            if etape in ETAPES and etape not in INREJOUABLES:
                return Plan(depuis=etape, mesure="",
                            remede=Remede(depuis=etape, levier="aucun",
                                          pourquoi="étape nommée par qc.json → regenerate_steps"),
                            explication=f"{diagnostic.resume} → {etape} (aucun)")
        return None
    # Le plus tardif dans le DAG gagne. À égalité d'étape, une mesure bloquante prime.
    candidats.sort(key=lambda p: (ETAPES.index(p.depuis),
                                  p.mesure in {m.nom for m in diagnostic.echecs if m.bloquante}))
    return candidats[-1]


def _bloquant_remediable(diagnostic: Diagnostic, cfg: OrchestratorConfig) -> bool:
    """Vrai si **chaque** contrôle bloquant en échec porte un remède nommé dans la table.

    Un seul bloquant sans remède suffit à rendre la reprise inutile : elle dépenserait le
    temps du remontage pour se faire refuser par le contrôle qu'elle ne traite pas.
    """
    bloquants = [m for m in diagnostic.echecs if m.bloquante]
    return bool(bloquants) and all(m.nom in cfg.remedes for m in bloquants)


# --------------------------------------------------------------------------------------
# Leviers — ce qu'on change avant de rejouer
# --------------------------------------------------------------------------------------


def appliquer_levier(plan: Plan, video_id: str, racine: Path,
                     rang: int) -> tuple[str, dict[str, Any]]:
    """Modifie ce qu'il faut pour que la reprise ne refasse pas la même chose.

    Renvoie `(description, données)` — les deux vont au journal. Chaque levier touche un
    fichier d'entrée du run, jamais la configuration du projet : un remède qui modifierait
    `config/` changerait aussi les runs à venir, ce qui serait un effet de bord invisible.
    """
    chemins = RunPaths.depuis_video_id(video_id, racine)
    levier = plan.remede.levier
    if levier == "graine_suivante":
        spec = runs_module.charger_spec(video_id, racine)
        avant = spec.seed
        # +1 suffit : la graine sert d'entrée à des tirages sans structure (découpage,
        # gabarit, assets), pas à un générateur dont les valeurs voisines seraient proches.
        spec.seed = (avant + 1) % (2 ** 64)
        runs_module.ecrire_json(chemins.spec, spec)
        return (f"graine {avant} → {spec.seed}", {"seed_avant": avant, "seed_apres": spec.seed})
    if levier == "gabarit_suivant":
        return _gabarit_suivant(video_id, racine, chemins)
    if levier == "assets_differents":
        exclus, note = _exclure_assets(video_id, racine, chemins)
        return (f"{len(exclus)} asset(s) du run interdits à la reprise{note}",
                {"assets_exclus": len(exclus), "note": note.strip(" —") or None})
    if levier in {"consigne", "hook_seul"}:
        consigne = plan.remede.consigne or (
            f"The bench rejected the previous version on `{plan.mesure}`. Fix that and "
            "nothing else.")
        if levier == "hook_seul":
            # Le hook est retiré du script : l'étape le retire du texte et le réécrit seul.
            consigne = "Rewrite the hook only; keep every other segment unchanged. " + consigne
        review.ajouter_consigne(chemins, f"banc, régénération {rang} ({plan.mesure})", consigne)
        return (f"consigne versée au prompt : « {consigne[:80]}… »",
                {"consigne": consigne[:300]})
    return ("aucun levier — reprise à l'identique", {})


def _gabarit_suivant(video_id: str, racine: Path, chemins: RunPaths) -> tuple[str, dict[str, Any]]:
    """Passe au gabarit de composition suivant de la chaîne, dans `manifest.identite`."""
    manifest = runs_module.charger_manifest(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    chaine = cfg.channels.get(manifest.identite.channel_id)
    gabarits = list(getattr(chaine, "templates", []) or [])
    if len(gabarits) < 2:
        return ("un seul gabarit sur la chaîne — rendu rejoué à l'identique",
                {"gabarits": len(gabarits)})
    actuel = manifest.identite.template_id
    index = (gabarits.index(actuel) + 1) % len(gabarits) if actuel in gabarits else 0
    manifest.identite.template_id = gabarits[index]
    runs_module.ecrire_json(chemins.manifest, manifest)
    return (f"gabarit {actuel} → {gabarits[index]}",
            {"template_avant": actuel, "template_apres": gabarits[index]})


def _exclure_assets(video_id: str, racine: Path,
                    chemins: RunPaths) -> tuple[list[str], str]:
    """Écrit `assets/exclus.json` : les assets déjà employés, interdits à la reprise.

    `factory shotlist` lit ce fichier quand il existe. Sans lui, la reprise redemanderait
    les mêmes images à la bibliothèque et la variété ne bougerait pas d'un point.
    """
    exclus: list[str] = []
    note = ""
    # La `shotlist` ne nomme pas les assets — elle décrit ce qu'il faut (`asset_request`).
    # Les assets réellement employés sont dans le manifeste, écrits par `render`.
    try:
        manifest = runs_module.charger_manifest(video_id, racine)
        exclus = [a.asset_id for a in manifest.decisions.assets if getattr(a, "asset_id", None)]
    except (FileNotFoundError, ValueError, AttributeError) as erreur:
        # Un manifeste illisible ne doit pas tuer la reprise, mais le remède devient vide :
        # le dire, plutôt que laisser croire à une exclusion qui n'a pas eu lieu.
        note = f" — manifeste illisible, aucune exclusion posée : {str(erreur)[:120]}"
    chemins.assets_dir.mkdir(parents=True, exist_ok=True)
    (chemins.assets_dir / "exclus.json").write_text(
        json.dumps({"ts": maintenant(), "asset_ids": sorted(set(exclus))},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sorted(set(exclus)), note


# --------------------------------------------------------------------------------------
# Décision : régénérer ou bloquer
# --------------------------------------------------------------------------------------


@dataclass
class Decision:
    """Ce que l'orchestrateur a décidé après un FAIL du banc."""

    action: str               # "regenerate" | "blocked"
    depuis: str | None
    raison: str
    rang: int = 0
    diagnostic: Diagnostic | None = None
    plan: Plan | None = None


def regenerations_faites(video_id: str, racine: Path) -> list[Regeneration]:
    """Les reprises déjà tentées sur ce run, lues dans le manifeste."""
    try:
        manifest = runs_module.charger_manifest(video_id, racine)
    except (FileNotFoundError, ValueError):
        return []
    return list(manifest.execution.regenerations)


def _inscrire(video_id: str, racine: Path, entree: Regeneration) -> None:
    """Ajoute la régénération au manifeste. Le manifeste est la mémoire du plafond."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs_module.charger_manifest(video_id, racine)
    manifest.execution.regenerations.append(entree)
    runs_module.ecrire_json(chemins.manifest, manifest)


def noter_resultat(video_id: str, racine: Path, verdict: str) -> None:
    """Écrit le verdict du banc sur la dernière régénération — sinon on ignore si elle a servi."""
    try:
        chemins = RunPaths.depuis_video_id(video_id, racine)
        manifest = runs_module.charger_manifest(video_id, racine)
    except (FileNotFoundError, ValueError):
        return
    if not manifest.execution.regenerations:
        return
    manifest.execution.regenerations[-1].resultat = verdict  # type: ignore[assignment]
    runs_module.ecrire_json(chemins.manifest, manifest)


def decider(conn: sqlite3.Connection, job: Job, cfg: OrchestratorConfig, *,
            racine: Path | None = None) -> Decision:
    """Après un `qc` FAIL : prépare une reprise ciblée, ou bloque avec les métriques exactes.

    Ne touche **ni** le statut du job **ni** la file : c'est le runner qui les possède. Ici
    on lit le banc, on choisit le remède, on modifie les entrées du run et on efface les
    marqueurs à partir de l'étape retenue.
    """
    racine = racine or racine_projet()
    try:
        diagnostic = lire_qc(job.video_id, racine)
    except (FileNotFoundError, json.JSONDecodeError) as erreur:
        return Decision("blocked", None, f"banc illisible : {erreur}")

    deja = regenerations_faites(job.video_id, racine)
    rang = len(deja) + 1
    if rang > cfg.regenerations_max:
        return Decision(
            "blocked", None,
            f"{len(deja)} régénération(s) déjà tentées (plafond {cfg.regenerations_max}) — "
            f"le banc refuse toujours : {diagnostic.resume}",
            rang=rang - 1, diagnostic=diagnostic,
        )
    tentes = {(r.mesure, r.depuis) for r in deja}
    if diagnostic.verdict_pipeline == "blocked" and not (
            cfg.remedes_sur_bloquant and _bloquant_remediable(diagnostic, cfg)):
        return Decision(
            "blocked", None,
            "contrôle bloquant sans remède automatique (`verdict_fail: blocked` dans "
            f"config/qc.yaml) : {diagnostic.resume}", rang=rang - 1, diagnostic=diagnostic)

    plan = choisir(diagnostic, cfg, tentes)
    if plan is None:
        motif = ("aucun remède connu" if not deja
                 else "tous les remèdes connus ont déjà été tentés sans succès")
        return Decision("blocked", None, f"{motif} pour : {diagnostic.resume}",
                        rang=rang - 1, diagnostic=diagnostic)

    description, donnees = appliquer_levier(plan, job.video_id, racine, rang)
    chemins = RunPaths.depuis_video_id(job.video_id, racine)
    effaces = review.invalider_depuis(chemins, plan.depuis)
    mesure = next((m for m in diagnostic.echecs if m.nom == plan.mesure), None)
    _inscrire(job.video_id, racine, Regeneration(
        ts=maintenant(), mesure=plan.mesure or "score_global", depuis=plan.depuis,
        remede=f"{plan.remede.levier} — {description}", rang=rang,
        valeur_mesuree=None if mesure is None else mesure.valeur,
        cible=None if mesure is None else mesure.cible,
    ))
    journal.evenement(
        "WARN",
        f"régénération {rang}/{cfg.regenerations_max} du job {job.id} : "
        f"{plan.mesure or 'score global'} → reprise depuis {plan.depuis}",
        job=job.id, video_id=job.video_id, stage=plan.depuis,
        donnees={"rang": rang, "mesure": plan.mesure, "depuis": plan.depuis,
                 "levier": plan.remede.levier, "description": description,
                 "etapes_invalidees": effaces, "score": diagnostic.score,
                 "echecs": [str(m) for m in diagnostic.echecs[:6]], **donnees},
        racine=racine, conn=conn,
    )
    return Decision("regenerate", plan.depuis,
                    f"{plan.explication} — {description}", rang=rang,
                    diagnostic=diagnostic, plan=plan)


def raison_lisible(decision: Decision) -> str:
    """Le texte que lira Alek dans le digest ou l'alerte : les chiffres, pas le code."""
    lignes = [decision.raison]
    if decision.diagnostic is not None:
        for mesure in decision.diagnostic.echecs[:6]:
            note = f" — {mesure.note}" if mesure.note else ""
            lignes.append(f"  · {mesure}{note}")
        if not decision.diagnostic.echecs:
            lignes += [f"  · {r}" for r in decision.diagnostic.raisons[:4]]
        lignes.append(f"  · score {decision.diagnostic.score}")
    return "\n".join(lignes)
