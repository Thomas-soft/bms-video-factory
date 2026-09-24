"""`factory run` — l'orchestrateur du DAG, avec reprise et manifeste finalisé.

Quatre décisions, toutes prises pour des raisons écrites ailleurs.

1. **Une étape = un sous-processus qui se termine.** C'est la seule façon de tenir « un seul
   modèle résident à la fois » sur 16 Go (`ROADMAP` § 3.2) : le processus meurt, la mémoire
   revient. L'orchestrateur ne charge jamais un modèle lui-même.
2. **Un code 4 n'est pas un échec de production.** `export` sort en code 4 quand un seuil de
   qualité n'est pas tenu — aujourd'hui « plans détectés à ±10 % », pour une raison de style
   établie à l'étape 13.1 et **arbitrée par Thomas**, pas pour un défaut de montage. Un
   orchestrateur qui s'arrêterait là ne produirait jamais la vidéo complète du jalon de la
   phase 1. Le DAG **continue** donc, le fichier est produit, et le run finit en
   `awaiting_review` avec l'écart inscrit au manifeste. Ce qui n'est pas fait, et ne doit pas
   l'être : abaisser un seuil pour faire passer un run.
3. **La reprise est portée par le disque, pas par la mémoire** : `.done/<etape>.done` est
   écrit après chaque étape réussie, avec l'empreinte de ses entrées. Un `--from` efface les
   marqueurs à partir de l'étape demandée ; sans lui, la reprise part de la première étape
   non faite.
4. **Le coût est calculé, jamais inventé** : `compute_min` est la somme des temps d'étape
   réellement mesurés, et l'énergie est une **estimation** tant que la puissance n'est pas
   lue au wattmètre — le manifeste porte le drapeau `a_mesurer` correspondant.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from factory.core import config as config_module
from factory.core import db, runs
from factory.core.models import ErreurRun, ModeleUtilise, RunManifest, VideoSpec
from factory.core.paths import RunPaths, dossier_workspace, racine_projet

#: Le DAG de la phase 1, dans l'ordre. `review` et `qc` n'y figurent pas : la relecture est
#: une barrière humaine (étape 19) et `qc` est livré par l'étape 15.
NOEUDS: tuple[str, ...] = (
    "plan", "research", "script", "voice", "subtitles", "shotlist",
    "render", "assemble", "thumbnail", "metadata", "export",
)

#: Entrées de chaque étape — sert à l'empreinte du marqueur `.done`, donc à détecter qu'une
#: étape amont a changé depuis. Seuls des fichiers légers y figurent.
ENTREES: dict[str, tuple[str, ...]] = {
    "research": ("spec.json",),
    "script": ("spec.json", "research.json"),
    "voice": ("script.json",),
    "subtitles": ("script.json", "voice/timings.json"),
    "shotlist": ("script.json", "words.json"),
    "render": ("shotlist.json",),
    "assemble": ("shotlist.json", "voice/timings.json", "subtitles.ass"),
    "thumbnail": ("script.json", "shotlist.json"),
    "metadata": ("script.json", "voice/timings.json", "thumbnails/thumbnails.json"),
    "export": ("shotlist.json",),
}

#: Plafonds de temps par étape, en secondes, calés sur les mesures des étapes 10 à 13.1 et
#: non sur des chiffres ronds (`INTERFACES` § Timeouts). `render` est calculé par plan.
TIMEOUTS: dict[str, int] = {
    "plan": 120, "research": 900, "script": 2700, "voice": 7200, "subtitles": 3600,
    "shotlist": 300, "assemble": 3600, "thumbnail": 1200, "metadata": 600, "export": 2700,
}
TIMEOUT_RENDER_PAR_PLAN_S = 960

#: Codes de retour qui ne sont pas des échecs de production (`INTERFACES` § Sémantique).
CODE_QUALITE = 4
CODE_ATTENTE_HUMAINE = 7


class EchecEtape(RuntimeError):
    """Une étape est sortie en erreur ; le message porte le texte exact de l'outil."""

    def __init__(self, etape: str, code: int, message: str) -> None:
        super().__init__(f"{etape} : code {code} — {message}")
        self.etape, self.code, self.message = etape, code, message


@dataclass
class EtapeExecutee:
    """Trace d'une étape pour la CLI."""

    nom: str
    code: int
    secondes: float
    saute: bool = False


@dataclass
class ResultatRun:
    """Ce qu'a produit un `factory run`."""

    video_id: str
    etat: str
    etapes: list[EtapeExecutee]
    secondes: float
    compute_min: float
    cout_eur: float | None
    cout_estime: bool
    disque_mo: float
    journal: Path
    raison: str | None = None
    alertes: list[str] = field(default_factory=list)


def maintenant() -> str:
    """Horodatage ISO-8601 UTC, format imposé par `INTERFACES` § 0."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------------------
# Journal d'événements et marqueurs
# --------------------------------------------------------------------------------------


def journaliser(chemins: RunPaths, etape: str, niveau: str, message: str,
                donnees: dict | None = None) -> None:
    """Une ligne dans `events.jsonl` — append-only, jamais réécrit."""
    entree = {"ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
              "run": chemins.racine.name, "step": etape, "level": niveau, "msg": message,
              "data": donnees or {}}
    chemins.racine.mkdir(parents=True, exist_ok=True)
    with chemins.events.open("a", encoding="utf-8") as flux:
        flux.write(json.dumps(entree, ensure_ascii=False) + "\n")


def empreinte_entrees(chemins: RunPaths, etape: str) -> str:
    """SHA-256 des fichiers d'entrée d'une étape. Un amont modifié change l'empreinte."""
    sha = hashlib.sha256()
    for relatif in ENTREES.get(etape, ()):
        fichier = chemins.racine / relatif
        sha.update(relatif.encode("utf-8"))
        if fichier.exists():
            sha.update(fichier.read_bytes())
    return sha.hexdigest()[:16]


def _sorties(chemins: RunPaths, etape: str) -> list[str]:
    """Fichiers attendus d'une étape, filtrés sur ceux qui existent réellement."""
    attendues = {
        "plan": ["spec.json", "manifest.json"], "research": ["research.json"],
        "script": ["script.json"], "voice": ["voice/voice.wav", "voice/timings.json"],
        "subtitles": ["words.json", "subtitles.srt", "subtitles.ass"],
        "shotlist": ["shotlist.json"], "render": ["clips"],
        "assemble": ["assembled.mp4", "video_nomusic.mp4"],
        "thumbnail": ["thumbnail.png", "thumbnails/thumbnails.json"],
        "metadata": ["metadata.json"], "export": ["final.mp4"],
    }.get(etape, [])
    return [s for s in attendues if (chemins.racine / s).exists()]


def marquer(chemins: RunPaths, etape: str, debut: str, secondes: float, code: int) -> None:
    """Écrit `.done/<etape>.done` — le marqueur d'idempotence d'`ARCHITECTURE` § 1.2."""
    chemins.done_dir.mkdir(parents=True, exist_ok=True)
    charge = {
        "step": etape, "schema_version": "1.0", "started_at": debut, "ended_at": maintenant(),
        "duration_s": round(secondes, 2), "inputs_hash": empreinte_entrees(chemins, etape),
        "outputs": _sorties(chemins, etape), "exit_code": code,
    }
    chemins.done(etape).write_text(json.dumps(charge, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")


def etape_faite(chemins: RunPaths, etape: str) -> bool:
    """Vrai si le marqueur existe **et** que les entrées de l'étape n'ont pas changé."""
    marqueur = chemins.done(etape)
    if not marqueur.exists():
        return False
    try:
        charge = json.loads(marqueur.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return charge.get("inputs_hash") == empreinte_entrees(chemins, etape)


# --------------------------------------------------------------------------------------
# Exécution d'une étape
# --------------------------------------------------------------------------------------


def _commande(etape: str, video_id: str, channel_id: str | None, topic: str | None,
              style: str | None) -> list[str]:
    """Ligne de commande de l'étape. Le même interpréteur, donc le même `.venv`."""
    base = [sys.executable, "-m", "factory.cli", etape]
    if etape == "plan":
        base += ["--channel", channel_id or ""]
        if topic:
            base += ["--topic", topic]
        return base
    base += ["--run", video_id]
    if style and etape in {"shotlist", "render"}:
        base += ["--style", style]
    return base


def _timeout(etape: str, chemins: RunPaths) -> int:
    """Plafond de temps de l'étape ; `render` se calcule sur le nombre de plans."""
    if etape != "render":
        return TIMEOUTS[etape]
    n_shots = 60
    if chemins.shotlist.exists():
        try:
            n_shots = len(json.loads(chemins.shotlist.read_text(encoding="utf-8"))["shots"])
        except (json.JSONDecodeError, KeyError):
            pass
    return n_shots * TIMEOUT_RENDER_PAR_PLAN_S


def _dernieres_lignes(texte: str, n: int = 3) -> str:
    """Les dernières lignes non vides d'une sortie — le message exact de l'outil."""
    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    return " | ".join(lignes[-n:])[:500] if lignes else "aucune sortie"


def executer_etape(
    etape: str, video_id: str, chemins: RunPaths, journal: Path, racine: Path,
    channel_id: str | None = None, topic: str | None = None, style: str | None = None,
    timeout: int | None = None,
) -> tuple[int, float, str]:
    """Lance l'étape dans un sous-processus et journalise. Renvoie `(code, secondes, sortie)`.

    `timeout` surcharge le plafond calculé : l'orchestrateur de l'étape 22.1 lit le sien
    dans `config/orchestrator.yaml`, et une valeur configurée doit primer sur celle du code.
    """
    commande = _commande(etape, video_id, channel_id, topic, style)
    plafond = timeout if timeout is not None else _timeout(etape, chemins)
    debut = time.perf_counter()
    environnement = dict(os.environ)
    environnement.setdefault("PYTHONUNBUFFERED", "1")
    with journal.open("a", encoding="utf-8") as flux:
        flux.write(f"\n===== {etape} — {maintenant()} =====\n{' '.join(commande)}\n")
        flux.flush()
        try:
            termine = subprocess.run(
                commande, cwd=racine, env=environnement, timeout=plafond,
                capture_output=True, text=True, check=False,
            )
            sortie = termine.stdout + termine.stderr
            code = termine.returncode
        except subprocess.TimeoutExpired as expire:
            sortie = (expire.stdout or "") + (expire.stderr or "") if isinstance(
                expire.stdout, str) else ""
            sortie += f"\nTIMEOUT après {plafond} s"
            code = 3
        flux.write(sortie)
        flux.write(f"\n----- {etape} : code {code} en {time.perf_counter() - debut:.1f} s -----\n")
    return code, time.perf_counter() - debut, sortie


# --------------------------------------------------------------------------------------
# Finalisation du manifeste
# --------------------------------------------------------------------------------------


def _taille_mo(dossier: Path) -> float:
    """Poids d'un dossier, en mégaoctets."""
    total = sum(f.stat().st_size for f in dossier.rglob("*") if f.is_file())
    return round(total / 1e6, 1)


def modeles_du_run(manifest: RunManifest, chemins: RunPaths, racine: Path) -> list[ModeleUtilise]:
    """Modèles réellement employés, relus dans les fichiers du run — jamais une liste en dur."""
    trouves: list[ModeleUtilise] = []
    gguf = next(iter(sorted((racine / "models" / "llamacpp").glob("**/*.gguf"))), None)
    if gguf is not None:
        quant = next((p for p in gguf.stem.split("-") if p.startswith("Q")), None)
        trouves.append(ModeleUtilise(
            brique="llm", repo=gguf.stem, quantization=quant,
            runtime="llama.cpp", runtime_version=_version_llama(),
        ))
    if chemins.timings.exists():
        donnees = json.loads(chemins.timings.read_text(encoding="utf-8"))
        trouves.append(ModeleUtilise(
            brique="tts", repo=str(donnees.get("engine", "inconnu")),
            runtime=str(donnees.get("engine", "inconnu")), runtime_version="—",
        ))
    if chemins.words.exists():
        donnees = json.loads(chemins.words.read_text(encoding="utf-8"))
        moteur = str(donnees.get("engine", "inconnu"))
        trouves.append(ModeleUtilise(brique="asr", repo=moteur, runtime=moteur,
                                     runtime_version="—"))
    generateurs = {
        asset.generator.model for asset in manifest.decisions.assets if asset.generator
    }
    for modele in sorted(generateurs):
        trouves.append(ModeleUtilise(brique="image", repo=modele, runtime="mflux",
                                     runtime_version=_version_mflux()))
    return trouves


def _version_llama() -> str:
    """Version de `llama-cli` telle que le binaire la déclare, ou « inconnue »."""
    try:
        sortie = subprocess.run(["llama-cli", "--version"], capture_output=True, text=True,
                                timeout=20, check=False)
        texte = (sortie.stderr or sortie.stdout).strip().splitlines()
        return texte[0][:60] if texte else "inconnue"
    except (OSError, subprocess.SubprocessError):
        return "inconnue"


def _version_mflux() -> str:
    """Version de mflux (installé en `uv tool`), ou « inconnue »."""
    try:
        sortie = subprocess.run(["mflux-generate", "--version"], capture_output=True, text=True,
                                timeout=20, check=False)
        return ((sortie.stdout or sortie.stderr).strip().splitlines() or ["inconnue"])[0][:40]
    except (OSError, subprocess.SubprocessError):
        return "inconnue"


def finaliser(
    video_id: str, racine: Path, etat: str, raison: str | None, debut_iso: str,
    wallclock: float, pic_disque: float,
) -> tuple[float, float | None, bool, float]:
    """Timings, coût, disque, modèles et état du run au manifeste. Renvoie les mesures."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    cfg = config_module.charger(racine, strict=False)

    compute_min = round(
        sum(manifest.execution.timings.get(n, 0.0) for n in NOEUDS) / 60.0, 2
    )
    energie, eur, estime = (0.0, None, True)
    if cfg.economics is not None:
        energie, eur, estime = cfg.economics.cout_run(compute_min)
    manifest.execution.cost.compute_min = compute_min
    manifest.execution.cost.energy_kwh = round(energie, 4)
    manifest.execution.cost.eur = round(eur, 4) if eur is not None else None
    # Le drapeau ne tombe que le jour où la puissance est mesurée au wattmètre (étape 27) :
    # une valeur de repli configurée reste une estimation.
    manifest.execution.cost.energy_kwh_a_mesurer = estime
    manifest.execution.cost.eur_a_mesurer = estime

    disque = _taille_mo(chemins.racine)
    manifest.execution.disk_mb.peak = max(pic_disque, disque)
    manifest.execution.disk_mb.after_export = disque
    manifest.execution.modeles = modeles_du_run(manifest, chemins, racine)
    manifest.execution.run_started_at = debut_iso
    manifest.execution.run_ended_at = maintenant()
    manifest.execution.wallclock_s = round(wallclock, 1)
    manifest.execution.run_state = etat  # type: ignore[assignment]
    manifest.execution.blocked_reason = raison if etat in {"blocked", "failed"} else None
    runs.ecrire_json(chemins.manifest, manifest)

    conn = db.ouvrir(racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, runs.charger_spec(video_id, racine), manifest, racine)
    conn.close()
    return compute_min, manifest.execution.cost.eur, estime, disque


def _timing(video_id: str, racine: Path, etape: str, secondes: float) -> None:
    """Temps **d'orchestrateur** au manifeste : c'est lui qui paie l'électricité.

    Chaque étape inscrit déjà sa propre mesure, prise à l'intérieur du processus ; elle ignore
    donc le démarrage de l'interpréteur et le chargement du modèle. Le coût d'un run se
    calcule sur la mesure du dehors, jamais sur la plus flatteuse des deux.
    """
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    manifest.execution.timings[etape] = round(
        max(secondes, manifest.execution.timings.get(etape, 0.0)), 2
    )
    runs.ecrire_json(chemins.manifest, manifest)


def _inscrire_erreur(video_id: str, racine: Path, etape: str, code: int, message: str) -> None:
    """Une erreur au manifeste, avec le message **exact** de l'outil."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    manifest.execution.errors = [e for e in manifest.execution.errors if e.step != etape]
    manifest.execution.errors.append(
        ErreurRun(step=etape, ts=maintenant(), code=code, message=message[:500], retry=0)
    )
    runs.ecrire_json(chemins.manifest, manifest)


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------


def executer(
    channel_id: str | None = None,
    video_id: str | None = None,
    topic: str | None = None,
    depuis: str | None = None,
    style: str | None = None,
    racine: Path | None = None,
) -> ResultatRun:
    """Enchaîne le DAG avec reprise. S'arrête à la première erreur qui n'est pas un seuil."""
    racine = racine or racine_projet()
    debut_iso, t0 = maintenant(), time.perf_counter()
    alertes: list[str] = []

    if depuis and depuis not in NOEUDS:
        raise ValueError(f"--from {depuis} : étapes connues — {', '.join(NOEUDS)}")

    if video_id is None and channel_id is None:
        raise ValueError("`factory run` exige --channel (nouveau run) ou --run (reprise)")

    # `--channel X --from <etape>` est toujours une **reprise**, jamais une création : un run
    # neuf n'a que sa `spec.json` et l'étape demandée tomberait sur un contrat d'entrée vide.
    # On reprend donc le dernier run de la chaîne, et on le dit.
    if video_id is None and depuis:
        video_id = _dernier_run_reprenable(racine, channel_id or "", depuis)
        if video_id is None:
            raise FileNotFoundError(
                f"--from {depuis} avec --channel {channel_id} : aucun run de cette chaîne "
                f"n'a mené à bien toutes les étapes amont ({', '.join(NOEUDS[:NOEUDS.index(depuis)])}). "
                "Lance `factory run --channel <id>` sans --from."
            )
        alertes.append(f"--from {depuis} : reprise du dernier run de {channel_id} "
                       f"({video_id}), aucun run neuf créé")
        perimees = amont_perime(RunPaths.depuis_video_id(video_id, racine), depuis)
        if perimees:
            alertes.append(
                f"amont périmé sur {video_id} : {', '.join(perimees)} — le marqueur existe mais "
                "les entrées ont changé depuis. Les sorties de ces étapes sont réutilisées "
                "telles quelles ; relance sans --from pour les refaire."
            )

    # Le plan crée le run : sans identifiant, c'est lui qui le donne.
    etapes: list[EtapeExecutee] = []
    journal_dir = dossier_workspace(racine) / "logs"
    journal_dir.mkdir(parents=True, exist_ok=True)

    if video_id is None:
        provisoire = journal_dir / f"run_plan_{int(time.time())}.log"
        chemins_vides = RunPaths.depuis_video_id("bms-x-00000000-0000", racine)
        code, secondes, sortie = executer_etape(
            "plan", "", chemins_vides, provisoire, racine, channel_id=channel_id, topic=topic
        )
        if code != 0:
            raise EchecEtape("plan", code, _dernieres_lignes(sortie))
        video_id = _dernier_run(racine, channel_id or "")
        etapes.append(EtapeExecutee("plan", code, secondes))
        journal = journal_dir / f"run_{video_id}.log"
        journal.write_text(provisoire.read_text(encoding="utf-8"), encoding="utf-8")
        provisoire.unlink(missing_ok=True)
        chemins = RunPaths.depuis_video_id(video_id, racine)
        marquer(chemins, "plan", debut_iso, secondes, code)
        journaliser(chemins, "orchestrator", "INFO", "Run créé", {"video_id": video_id})
    else:
        chemins = RunPaths.depuis_video_id(video_id, racine)
        if not chemins.spec.exists():
            raise FileNotFoundError(f"run inconnu : {chemins.racine}")
        journal = journal_dir / f"run_{video_id}.log"

    spec = VideoSpec.model_validate_json(chemins.spec.read_text(encoding="utf-8"))
    channel_id = spec.channel_id

    if depuis:
        for noeud in NOEUDS[NOEUDS.index(depuis):]:
            chemins.done(noeud).unlink(missing_ok=True)

    debut_index = NOEUDS.index(depuis) if depuis else 0
    pic_disque = _taille_mo(chemins.racine)
    qualite_non_tenue: list[str] = []
    etat, raison = "exported", None

    for noeud in NOEUDS[max(debut_index, 1):]:  # `plan` est déjà passé
        if etape_faite(chemins, noeud):
            etapes.append(EtapeExecutee(noeud, 0, 0.0, saute=True))
            continue
        journaliser(chemins, noeud, "INFO", f"Étape {noeud} lancée")
        code, secondes, sortie = executer_etape(
            noeud, video_id, chemins, journal, racine, style=style
        )
        etapes.append(EtapeExecutee(noeud, code, secondes))
        pic_disque = max(pic_disque, _taille_mo(chemins.racine))

        if code == 0:
            marquer(chemins, noeud, debut_iso, secondes, code)
            _timing(video_id, racine, noeud, secondes)
            journaliser(chemins, noeud, "INFO", f"Étape {noeud} terminée",
                        {"secondes": round(secondes, 1)})
            continue

        message = _dernieres_lignes(sortie)
        if code == CODE_QUALITE:
            # Décision de l'étape 13.2 : le fichier est produit, le seuil ne l'est pas.
            marquer(chemins, noeud, debut_iso, secondes, code)
            _timing(video_id, racine, noeud, secondes)
            qualite_non_tenue.append(noeud)
            _inscrire_erreur(video_id, racine, noeud, code, message)
            journaliser(chemins, noeud, "WARN",
                        f"Seuil de qualité non tenu à l'étape {noeud} : le DAG continue",
                        {"code": code})
            alertes.append(f"{noeud} : seuil de qualité non tenu (code 4) — {message[:160]}")
            continue
        if code == CODE_ATTENTE_HUMAINE:
            etat, raison = "awaiting_review", f"{noeud} attend une décision humaine"
            _inscrire_erreur(video_id, racine, noeud, code, message)
            journaliser(chemins, noeud, "BLOCK", raison)
            break
        etat = "failed"
        raison = f"L'étape « {noeud} » s'est arrêtée (code {code}) : {message}"
        _inscrire_erreur(video_id, racine, noeud, code, message)
        journaliser(chemins, noeud, "ERROR", f"Étape {noeud} en échec",
                    {"code": code, "message": message[:200]})
        break

    if etat == "exported" and qualite_non_tenue:
        etat = "awaiting_review"
        raison = ("seuil de qualité non tenu à l'étape "
                  + ", ".join(qualite_non_tenue)
                  + " — la vidéo est produite, elle attend une décision")

    wallclock = time.perf_counter() - t0
    compute_min, eur, estime, disque = finaliser(
        video_id, racine, etat, raison, debut_iso, wallclock, pic_disque
    )
    journaliser(chemins, "orchestrator", "INFO" if etat != "failed" else "ERROR",
                f"Run terminé : {etat}",
                {"wallclock_s": round(wallclock, 1), "compute_min": compute_min,
                 "cout_eur": eur, "disque_mo": disque})
    return ResultatRun(
        video_id=video_id, etat=etat, etapes=etapes, secondes=wallclock,
        compute_min=compute_min, cout_eur=eur, cout_estime=estime, disque_mo=disque,
        journal=journal, raison=raison, alertes=alertes,
    )


def _dernier_run_reprenable(racine: Path, channel_id: str, depuis: str) -> str | None:
    """Dernier run de la chaîne **dont les entrées de l'étape demandée existent**, ou `None`.

    Le critère est **toutes les étapes amont marquées faites**, pas « les fichiers d'entrée
    existent ». Deux raisons, toutes deux constatées le 20/09 sur cette chaîne. La base garde la
    trace de runs dont le dossier a été purgé (purges de disque du 18/09). Et surtout, les
    entrées déclarées d'une étape ne sont que des **fichiers légers**, ceux qui servent à
    l'empreinte du marqueur : `thumbnail` déclare `script.json` et `shotlist.json`, mais elle a
    besoin des images que `render` produit. Un run porteur des deux JSON et d'aucune image passe
    le test des fichiers et échoue à l'exécution. Les marqueurs, eux, disent ce qui a tourné.
    """
    conn = db.ouvrir(racine / "workspace" / "factory.db")
    lignes = conn.execute(
        "SELECT video_id FROM runs WHERE channel_id = ? ORDER BY created_at DESC, rowid DESC",
        (channel_id,),
    ).fetchall()
    conn.close()
    amont = NOEUDS[:NOEUDS.index(depuis)]
    for (identifiant,) in lignes:
        chemins = RunPaths.depuis_video_id(str(identifiant), racine)
        # Marqueur **présent**, et non `etape_faite` : une empreinte périmée dit qu'un amont a
        # été réécrit depuis, pas que l'étape n'a jamais tourné. C'est précisément ce que `--from`
        # sert à traiter ; l'appelant en est averti par `amont_perime()`.
        if chemins.spec.exists() and all(chemins.done(noeud).exists() for noeud in amont):
            return str(identifiant)
    return None


def amont_perime(chemins: RunPaths, depuis: str) -> list[str]:
    """Étapes amont dont le marqueur existe mais dont les entrées ont changé depuis.

    C'est le piège du 16/09 (`STATE.md`) : `script.json` réécrit hors pipeline pendant que
    `script.done` datait de la veille, et `voice` qui a rendu 12 minutes d'audio en 29 s en
    réutilisant l'ancien découpage. Ici on ne rejoue rien — on **nomme** les étapes concernées.
    """
    return [noeud for noeud in NOEUDS[:NOEUDS.index(depuis)]
            if chemins.done(noeud).exists() and not etape_faite(chemins, noeud)]


def _dernier_run(racine: Path, channel_id: str) -> str:
    """Identifiant du run que `plan` vient de créer, lu en base et non deviné."""
    conn = db.ouvrir(racine / "workspace" / "factory.db")
    ligne = conn.execute(
        "SELECT video_id FROM runs WHERE channel_id = ? ORDER BY created_at DESC, rowid DESC "
        "LIMIT 1", (channel_id,),
    ).fetchone()
    conn.close()
    if ligne is None:
        raise FileNotFoundError(f"aucun run en base pour {channel_id} après `plan`")
    return str(ligne[0])
