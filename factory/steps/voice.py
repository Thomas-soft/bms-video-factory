"""Étape `voice` — synthèse de la voix off, concaténation, normalisation, horodatage.

Chaîne de traitement, dans cet ordre :

1. **Fusion** des segments consécutifs de même rôle jusqu'à ≥ `min_segment_s` (15 s par défaut).
   `ARCHITECTURE.md` § 2.2 : sous ce seuil, le WER de re-transcription mesuré à l'étape 7 décroche
   — le régime nominal deviendrait le régime dégradé.
2. **Synthèse** dans un sous-processus (`python -m factory.tts`) qui charge le modèle une fois
   pour tout le run et meurt ensuite : un seul modèle résident (`CLAUDE.md` § 4).
3. **Vitesse** de la langue par `atempo`, le TTS retenu n'ayant aucun paramètre de débit.
4. **Nettoyage** des silences de tête et de queue, puis **concaténation** avec les respirations
   de la charte (350 ms entre segments, 600 ms après le hook, 250 ms avant le sponsor).
5. **Normalisation en deux passes** à -14 LUFS / -1 dBTP, la norme YouTube.
6. `voice/timings.json` : la position de chaque segment dans `voice.wav`, sur laquelle le
   découpage en plans (étape 12.1) viendra se caler.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from factory import audio, tts
from factory.core import config as config_module
from factory.core import db, referentiel, runs
from factory.core.models import Script, SegmentVoix, Timings
from factory.core.paths import RunPaths, racine_projet

#: Marge ajoutée au plafond de temps du sous-processus : chargement du modèle et écriture disque.
MARGE_TIMEOUT_S = 300.0
#: Crête visée par `loudnorm`. Le contrat exige une crête **mesurée** ≤ -1,0 dBTP ; viser
#: exactement -1,0 la fait mesurer à -0,9 (mesuré le 16/09/2026 sur le run FR).
CIBLE_TRUE_PEAK_DBTP = -1.5
#: Sans nouvelle unité pendant ce délai, le sous-processus est considéré figé et relancé.
#: Le pire calcul mesuré sur une unité est de 109 s ; 420 s laisse quatre fois la marge.
WATCHDOG_UNITE_S = 420.0
#: Le chargement du modèle a été mesuré de 16 à 29 s, et bien plus quand la machine comprime.
WATCHDOG_CHARGEMENT_S = 900.0
#: Relances autorisées avant d'abandonner. Les unités déjà écrites ne sont pas resynthétisées.
TENTATIVES_MAX = 3


@dataclass
class Unite:
    """Une unité de synthèse : un segment de script, ou plusieurs fusionnés."""

    identifiant: str
    role: str
    segments: list[str]
    texte: str
    mots: int
    duree_estimee_s: float
    disclosure: bool = False


@dataclass
class ResultatVoix:
    """Ce que l'étape rend à la CLI."""

    timings: Timings
    unites: list[Unite]
    secondes: float
    secondes_tts: float
    rtf: float | None
    duree_estimee_script_s: float
    alertes: list[str] = field(default_factory=list)

    @property
    def ecart_duree(self) -> float:
        """Écart relatif entre la durée réelle de la voix et l'estimation du script."""
        cible = self.duree_estimee_script_s
        return (self.timings.total_duration_s - cible) / cible if cible else 0.0


def construire_unites(script: Script, mots_par_minute: float, min_segment_s: float) -> list[Unite]:
    """Fusionne les segments consécutifs **de même rôle** jusqu'à atteindre `min_segment_s`.

    La contrainte « même rôle » n'est pas cosmétique : fusionner le hook avec le segment suivant
    supprimerait la respiration de 600 ms qui le suit, c'est-à-dire précisément le levier de
    rétention que l'étape sert. Un hook plus court que le seuil reste donc seul, et l'appelant
    le signale.
    """
    unites: list[Unite] = []
    for segment in script.segments:
        duree = len(segment.narration.split()) / (mots_par_minute / 60.0)
        derniere = unites[-1] if unites else None
        if derniere and derniere.role == segment.role and derniere.duree_estimee_s < min_segment_s:
            derniere.segments.append(segment.id)
            derniere.texte = f"{derniere.texte} {segment.narration}".strip()
            derniere.mots += len(segment.narration.split())
            derniere.duree_estimee_s += duree
            derniere.disclosure = derniere.disclosure or segment.disclosure_spoken
        else:
            unites.append(Unite(
                identifiant=segment.id, role=segment.role, segments=[segment.id],
                texte=segment.narration.strip(), mots=len(segment.narration.split()),
                duree_estimee_s=duree, disclosure=segment.disclosure_spoken,
            ))
    return unites


def pauses_de(unites: list[Unite], pauses_ms: object) -> list[float]:
    """Respiration insérée **avant** chaque unité, en secondes, d'après la charte de la langue."""
    valeurs = [0.0]
    for index in range(1, len(unites)):
        precedente, courante = unites[index - 1], unites[index]
        if precedente.role == "hook":
            millisecondes = pauses_ms.apres_hook_ms  # type: ignore[attr-defined]
        elif courante.role == "sponsor":
            millisecondes = pauses_ms.avant_sponsor_ms  # type: ignore[attr-defined]
        else:
            millisecondes = pauses_ms.entre_segments_ms  # type: ignore[attr-defined]
        valeurs.append(millisecondes / 1000.0)
    return valeurs


def _lire_en_fond(flux, file: queue.Queue) -> None:
    """Verse les lignes du sous-processus dans une file, pour que l'attente soit bornée."""
    for ligne in flux:
        file.put(ligne)
    file.put(None)


def _synthetiser(unites: list[Unite], chemins: RunPaths, voix: str, lang: str,
                 racine: Path, journal: Path, force: bool) -> tuple[float, list[dict]]:
    """Synthétise toutes les unités, en relançant le sous-processus s'il se fige.

    **Pourquoi une relance et pas une simple erreur.** Mesuré le 16/09/2026 : sur un segment de
    56 mots comme les vingt-trois précédents, `generate_custom_voice` ne rend jamais la main —
    52 minutes d'horloge, processeur à 72 %, pour un calcul mesuré à 71 s à la tentative
    suivante. La génération est échantillonnée, donc le blocage n'est pas reproductible : le
    remède qui coûte le moins cher est de rendre la main et de reprendre, puisque les unités
    déjà écrites sont sautées.
    """
    bruts = [chemins.voice_dir / f".raw_{index:02d}.wav" for index in range(len(unites))]
    travail = {
        "model": tts.REPO,
        "language": tts.LANGUES[lang],
        "speaker": tts.locuteur(voix),
        "force": force,
        "units": [
            {"id": unite.identifiant, "file": str(brut), "text": unite.texte}
            for unite, brut in zip(unites, bruts, strict=True)
        ],
    }
    fichier = chemins.voice_dir / ".tts_job.json"
    fichier.write_text(json.dumps(travail, ensure_ascii=False, indent=2), encoding="utf-8")

    # `INTERFACES.md` § timeouts : max(180, 5 × durée) par segment, cumulé ici puisque le
    # sous-processus les traite tous. Un dépassement est un code 3, pas un plantage silencieux.
    plafond = MARGE_TIMEOUT_S + sum(max(180.0, 5.0 * u.duree_estimee_s) for u in unites)
    environnement = dict(os.environ)
    # `HF_HUB_OFFLINE=1` fait échouer le chargement : le tokenizer de transformers 4.57 appelle
    # `model_info()` sur le dépôt (contrôle « base mistral ») et l'appel lève en mode hors ligne.
    # Les poids sont déjà dans `models/hf` : rien n'est téléchargé, seule une métadonnée est lue.
    environnement["TOKENIZERS_PARALLELISM"] = "false"

    t0 = time.perf_counter()
    comptes: list[dict] = []
    for tentative in range(1, TENTATIVES_MAX + 1):
        fige, code = _une_passe(fichier, racine, environnement, journal, chemins.video_id,
                                plafond, comptes, tentative)
        if not fige and code == 0:
            break
        if not fige:
            raise RuntimeError(f"tts : sous-processus terminé en code {code} (journal {journal})")
        if tentative == TENTATIVES_MAX:
            raise TimeoutError(
                f"tts : figé {TENTATIVES_MAX} fois de suite au-delà de {WATCHDOG_UNITE_S:.0f} s "
                f"sans nouvelle unité (journal {journal})"
            )
    manquants = [str(b) for b in bruts if not b.exists()]
    if manquants:
        raise RuntimeError(f"tts : {len(manquants)} unité(s) sans WAV, dont {manquants[0]}")
    return time.perf_counter() - t0, comptes


def _une_passe(fichier: Path, racine: Path, environnement: dict[str, str], journal: Path,
               video_id: str, plafond: float, comptes: list[dict],
               tentative: int) -> tuple[bool, int]:
    """Une exécution du sous-processus. Rend (figé, code de retour)."""
    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n=== tts {video_id} — tentative {tentative}, plafond {plafond:.0f} s ===\n")
        trace.flush()
        proc = subprocess.Popen(
            [sys.executable, "-m", "factory.tts", str(fichier)],
            cwd=str(racine), env=environnement, stdout=subprocess.PIPE,
            stderr=trace, text=True, bufsize=1,
        )
        assert proc.stdout is not None
        file: queue.Queue = queue.Queue()
        lecteur = threading.Thread(target=_lire_en_fond, args=(proc.stdout, file), daemon=True)
        lecteur.start()
        debut = time.perf_counter()
        attente = WATCHDOG_CHARGEMENT_S
        while True:
            try:
                ligne = file.get(timeout=attente)
            except queue.Empty:
                proc.kill()
                trace.write(f"WATCHDOG : aucune unité depuis {attente:.0f} s, sous-processus tué\n")
                return True, -1
            if ligne is None:
                break
            trace.write(ligne)
            trace.flush()
            try:
                compte = json.loads(ligne)
            except json.JSONDecodeError:
                continue
            if compte.get("evenement") in {"unite", "saute"}:
                comptes.append(compte)
                attente = WATCHDOG_UNITE_S
            elif compte.get("evenement") == "charge":
                attente = WATCHDOG_UNITE_S
            if time.perf_counter() - debut > plafond:
                proc.kill()
                raise TimeoutError(f"tts : dépassement de {plafond:.0f} s (journal {journal})")
        return False, proc.wait(timeout=60)


def _nettoyer(unites: list[Unite], chemins: RunPaths, langue: object,
              alertes: list[str]) -> list[Path]:
    """Vitesse puis silences de tête et de queue ; rend les `voice/segment_XX.wav`.

    Dans cet ordre : `atempo` déplace les silences, les couper avant serait à refaire.
    """
    fichiers: list[Path] = []
    vitesse = langue.tts.speed  # type: ignore[attr-defined]
    seuil = langue.tts.silence_threshold_db  # type: ignore[attr-defined]
    for index, unite in enumerate(unites):
        brut = chemins.voice_dir / f".raw_{index:02d}.wav"
        segment = chemins.segment_wav(index)
        if abs(vitesse - 1.0) >= 1e-3:
            accelere = chemins.voice_dir / f".spd_{index:02d}.wav"
            audio.atempo(brut, accelere, vitesse)
            source = accelere
        else:
            source = brut
        avant, apres = audio.silence_trim(source, segment, seuil)
        if apres < 0.5 * avant:
            alertes.append(
                f"{unite.identifiant} : le nettoyage des silences a retiré "
                f"{(1 - apres / avant) * 100:.0f} % du fichier ({avant:.1f} s → {apres:.1f} s)"
            )
        fichiers.append(segment)
    return fichiers


def executer(video_id: str, racine: Path | None = None, force: bool = False) -> ResultatVoix:
    """Produit `voice/segment_XX.wav`, `voice/voice.wav` et `voice/timings.json`."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    base = racine or racine_projet()
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    langue = cfg.languages[channel.lang]
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.script.exists():
        raise FileNotFoundError(f"script.json absent : lance `factory script --run {video_id}`")
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))

    voix = cfg.voix_de(channel)
    if voix is None:
        raise ValueError(f"voix {channel.voice_id} absente de config/languages/{channel.lang}.yaml")
    if voix.engine not in tts.MOTEURS:
        raise ValueError(
            f"voix {voix.id} : moteur {voix.engine} non installé — seul {', '.join(tts.MOTEURS)} "
            "est mesuré et retenu (outils/SELECTION.md § 2)"
        )

    chemins.voice_dir.mkdir(parents=True, exist_ok=True)
    journal = base / "workspace" / "logs" / "etape11.log"
    journal.parent.mkdir(parents=True, exist_ok=True)

    mpm = referentiel.mots_par_minute(spec.niche, racine)
    unites = construire_unites(script, mpm, langue.tts.min_segment_s)
    courtes = [u for u in unites if u.duree_estimee_s < langue.tts.min_segment_s]
    if courtes:
        alertes.append(
            f"{len(courtes)} unité(s) sous {langue.tts.min_segment_s:.0f} s estimées "
            f"({', '.join(f'{u.identifiant} {u.duree_estimee_s:.1f} s ({u.role})' for u in courtes[:3])})"
            " : aucune fusion possible sans changer de rôle (ARCHITECTURE § 2.2)"
        )

    # Les `segment_XX.wav` sont le produit fini de la synthèse : s'ils sont tous là et que le
    # découpage n'a pas changé, rejouer l'étape ne doit pas coûter 35 minutes de TTS. C'est ce
    # qui permet de corriger la concaténation ou la normalisation sans re-synthétiser.
    deja_la = [chemins.segment_wav(index) for index in range(len(unites))]
    if not force and all(fichier.exists() for fichier in deja_la):
        alertes.append(
            f"{len(unites)} segment(s) déjà synthétisés réemployés ; `--force` pour resynthétiser"
        )
        secondes_tts, comptes, fichiers = 0.0, [], deja_la
    else:
        secondes_tts, comptes = _synthetiser(
            unites, chemins, voix.id, channel.lang, base, journal, force
        )
        fichiers = _nettoyer(unites, chemins, langue, alertes)

    pauses = pauses_de(unites, langue.tts.pauses_ms)
    brut_concat = chemins.voice_dir / ".concat.wav"
    positions = audio.concat(fichiers, pauses, brut_concat)
    # `loudnorm` visé à -1,0 dBTP rend -0,9 à la mesure `ebur128` : les deux ne sur-échantillonnent
    # pas de la même façon. Le contrat porte sur la **mesure**, on vise donc CIBLE_TRUE_PEAK_DBTP.
    normalisation = audio.loudnorm_two_pass(
        brut_concat, chemins.voice_wav, target=-14.0, tp=CIBLE_TRUE_PEAK_DBTP
    )

    # La normalisation est un gain : elle ne doit pas déplacer les positions. On le vérifie
    # plutôt que de le supposer, et on recale si le rééchantillonnage a bougé d'un cheveu.
    duree_finale = audio.duree(chemins.voice_wav)
    duree_concat = audio.duree(brut_concat)
    if duree_concat > 0 and abs(duree_finale - duree_concat) > 0.01:
        facteur = duree_finale / duree_concat
        positions = [(d * facteur, f * facteur) for d, f in positions]
        alertes.append(
            f"normalisation : durée passée de {duree_concat:.3f} s à {duree_finale:.3f} s, "
            "positions recalées"
        )

    niveau = normalisation.apres
    if not niveau.conforme:
        alertes.append(
            f"loudness hors norme : {niveau.lufs} LUFS (attendu -15 à -13), crête réelle "
            f"{niveau.true_peak_dbtp} dBTP (attendu ≤ -1)"
        )

    segments_timings = [
        SegmentVoix(
            id=unite.identifiant,
            merged_from=unite.segments if len(unite.segments) > 1 else [],
            file=f"voice/{chemins.segment_wav(index).name}",
            start_s=round(debut, 3), end_s=round(fin, 3), duration_s=round(fin - debut, 3),
            text=unite.texte,
            # La phrase de divulgation ouvre le segment sponsor (`script.py` la place en tête) :
            # sa position absolue est donc celle du segment. Chemin non exercé par ces runs.
            disclosure_at_s=round(debut, 3) if unite.disclosure else None,
        )
        for index, (unite, (debut, fin)) in enumerate(zip(unites, positions, strict=True))
    ]
    timings = Timings(
        schema_version="1.0", voice_id=voix.id, engine=voix.engine,
        sample_rate=audio.SAMPLE_RATE, channels=audio.CHANNELS,
        loudness_lufs=niveau.lufs if niveau.lufs is not None else 0.0,
        true_peak_dbtp=niveau.true_peak_dbtp if niveau.true_peak_dbtp is not None else 0.0,
        total_duration_s=round(duree_finale, 3), speed=langue.tts.speed,
        segments=segments_timings,
    )
    runs.ecrire_json(chemins.timings, timings)

    for reste in list(chemins.voice_dir.glob(".raw_*.wav")) + list(chemins.voice_dir.glob(".spd_*.wav")):
        reste.unlink()
    brut_concat.unlink(missing_ok=True)

    secondes = time.perf_counter() - t0
    duree_audio_brute = sum(c.get("duree_audio_s") or 0.0 for c in comptes)
    rtf = secondes_tts / duree_audio_brute if duree_audio_brute else None

    ecart = (duree_finale - script.estimated_duration_s) / script.estimated_duration_s
    if abs(ecart) > 0.10:
        alertes.append(
            f"durée réelle {duree_finale:.0f} s contre {script.estimated_duration_s:.0f} s estimées "
            f"({ecart * 100:+.1f} %) : le débit du référentiel ({mpm:.1f} mots/min) est à "
            "recalibrer — à porter à l'étape 16"
        )

    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.voice_id = voix.id
    manifest.decisions.duration_s = round(duree_finale, 1)
    manifest.decisions.loudness_lufs = niveau.lufs
    manifest.decisions.true_peak_dbtp = niveau.true_peak_dbtp
    manifest.execution.timings["voice"] = round(secondes, 2)
    manifest.execution.timings["voice_tts"] = round(secondes_tts, 2)
    manifest.execution.timings["voice_unites"] = len(unites)
    if not any(m.brique == "tts" for m in manifest.execution.modeles):
        from factory.core.models import ModeleUtilise

        manifest.execution.modeles.append(ModeleUtilise(
            brique="tts", repo=tts.REPO, quantization="fp16", runtime="transformers/mps",
            runtime_version=_version_torch(),
        ))
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()

    with journal.open("a", encoding="utf-8") as trace:
        trace.write(json.dumps({
            "etape": "voice", "run": video_id, "voix": voix.id, "unites": len(unites),
            "duree_s": round(duree_finale, 2), "lufs": niveau.lufs,
            "true_peak_dbtp": niveau.true_peak_dbtp, "rtf": round(rtf, 3) if rtf else None,
            "temps_s": round(secondes, 1), "temps_tts_s": round(secondes_tts, 1),
            "ecart_duree": round(ecart, 4), "alertes": alertes,
        }, ensure_ascii=False) + "\n")

    return ResultatVoix(
        timings=timings, unites=unites, secondes=secondes, secondes_tts=secondes_tts,
        rtf=rtf, duree_estimee_script_s=script.estimated_duration_s, alertes=alertes,
    )


def _version_torch() -> str:
    """Version de torch, lue dans un sous-processus pour ne rien charger ici."""
    proc = subprocess.run(
        [sys.executable, "-c", "import torch; print(torch.__version__)"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip() or "inconnue"
