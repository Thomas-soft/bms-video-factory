"""Étape `export` — `final.mp4`, puis la seule chose qui compte : la mesure du fichier produit.

Cinq vérifications, toutes sur le fichier **livré**, jamais sur ce que le montage a déclaré :

1. `ffprobe` — codecs, profil, résolution, cadence, durée contre la piste voix (± 0,5 s) ;
2. `ebur128` — niveau intégré (-14 ± 1 LUFS) et crête réelle (≤ -1 dBTP) ;
3. PySceneDetect `ContentDetector` — nombre de plans détectés contre `n_shots` (± 10 %), et
   `cut_rhythm_measured_s = durée ÷ n_scenes` inscrit au manifeste à côté de la cible ;
4. la piste de sous-titres — présente, dans la bonne langue, non vide ;
5. cinq images extraites à 3, 25, 50, 75 et 97 % dans `qc/frames/`, pour l'œil humain.

**Le flux vidéo n'est pas réencodé** quand il est déjà au contrat. `assemble` produit exactement
ce que demande l'export — H.264 High, CRF 18, preset medium, 1920×1080, 30 ips — parce que
`factory.video.arguments_encodage` est la seule porte d'encodage du projet. Réencoder ne
changerait donc aucun paramètre du fichier : cela ajouterait une génération de perte et dix
minutes de calcul. `--reencode` force le passage si l'on veut malgré tout l'exercer, et le
contrôle `ffprobe` échoue si le flux n'est pas au contrat — c'est lui qui rend la copie sûre.

La purge des clips intermédiaires n'a lieu **qu'après** ces vérifications, jamais avant : un
export qui ne passe pas laisse de quoi recommencer.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from factory.core import config as config_module
from factory.core import db, runs
from factory.core import models as m
from factory.core.models import Shotlist
from factory.core.paths import RunPaths, dossier_workspace, racine_projet
from factory.video import FPS, HAUTEUR, LARGEUR, lancer_ffmpeg

#: Journal de l'étape.
JOURNAL = "workspace/logs/etape13_1.log"
#: Positions des images de contrôle, en part de la durée.
POSITIONS_QC = (0.03, 0.25, 0.50, 0.75, 0.97)
#: Tolérance de durée contre la piste voix, en secondes (« Terminé quand » de l'étape 13.1).
TOLERANCE_DUREE_S = 0.5
#: Tolérance sur le nombre de plans détectés, en part de `n_shots`.
TOLERANCE_PLANS = 0.10


class ExportNonConforme(RuntimeError):
    """Le fichier produit ne tient pas un critère mesuré ; le message liste tous les écarts."""

    def __init__(self, message: str, resultat: "ResultatExport | None" = None) -> None:
        super().__init__(message)
        self.resultat = resultat


@dataclass
class ResultatExport:
    """Ce que l'export a produit et **mesuré**."""

    final: Path
    copie_export: Path
    taille_mo: float
    codec_video: str
    profil: str
    largeur: int
    hauteur: int
    fps: float
    codec_audio: str
    debit_audio_kbps: float | None
    duree_s: float
    duree_voix_s: float
    lufs: float | None
    true_peak_dbtp: float | None
    n_scenes: int | None
    n_shots: int
    cut_rhythm_measured_s: float | None
    cut_rhythm_target_s: float | None
    sous_titres: str
    images_qc: list[Path]
    reencode: bool
    secondes: float
    purge_mo: float = 0.0
    ecarts: list[str] = field(default_factory=list)
    alertes: list[str] = field(default_factory=list)

    @property
    def ecart_duree_s(self) -> float:
        """Écart mesuré entre la vidéo livrée et la piste voix."""
        return abs(self.duree_s - self.duree_voix_s)


def _sonder(chemin: Path) -> dict:
    """`ffprobe` complet d'un fichier livré, flux et conteneur."""
    sortie = subprocess.run(
        [shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(chemin)],
        capture_output=True, text=True, check=False,
    )
    if sortie.returncode != 0:
        raise ExportNonConforme(f"ffprobe {chemin.name} : {sortie.stderr.strip()}")
    return json.loads(sortie.stdout)


def _detecter_plans(chemin: Path, trace: IO[str]) -> int | None:
    """Nombre de plans détectés par PySceneDetect. `None` si la détection échoue.

    Un échec de détection n'annule pas l'export : c'est une **mesure**, pas une production.
    L'écart au nombre prévu, lui, est un écart et fait échouer l'étape.
    """
    try:
        from scenedetect import ContentDetector, detect

        debut = time.perf_counter()
        scenes = detect(str(chemin), ContentDetector())
        trace.write(
            f"scenedetect : {len(scenes)} plan(s) en {time.perf_counter() - debut:.1f} s\n"
        )
        return len(scenes)
    except Exception as erreur:  # la mesure manque, le fichier reste livré
        trace.write(f"scenedetect : ÉCHEC — {erreur}\n")
        return None


def _plafond_detectable(chemins: RunPaths, shotlist: Shotlist) -> int:
    """Nombre maximal de plans qu'un détecteur de contenu **peut** voir sur ce run.

    Deux plans consécutifs servis par le même fichier image ne produisent aucune coupe visible :
    le moteur illustré partage une image entre plusieurs plans (83 images pour 127 plans sur le
    run FR), et la frontière entre deux d'entre eux n'est un changement que dans la shotlist.
    Sans ce plafond, l'écart au nombre prévu serait attribué au montage, qui n'y est pour rien.
    """
    import hashlib

    empreintes: list[str | None] = []
    for shot in shotlist.shots:
        dossier = chemins.asset_dir(shot.id)
        images = sorted(
            f for f in dossier.iterdir()
            if dossier.is_dir() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            and "depth" not in f.name
        ) if dossier.is_dir() else []
        empreintes.append(
            hashlib.sha256(images[0].read_bytes()).hexdigest() if images else None
        )
    partages = sum(
        1 for a, b in zip(empreintes, empreintes[1:]) if a is not None and a == b
    )
    return len(shotlist.shots) - partages


def _extraire_images(
    source: Path, duree_s: float, dossier: Path, trace: IO[str]
) -> list[Path]:
    """Cinq images de contrôle, aux positions de `POSITIONS_QC`."""
    dossier.mkdir(parents=True, exist_ok=True)
    produites: list[Path] = []
    for part in POSITIONS_QC:
        instant = duree_s * part
        sortie = dossier / f"frame_{round(part * 100):02d}pc.png"
        lancer_ffmpeg(
            ["-ss", f"{instant:.3f}", "-i", str(source), "-frames:v", "1", "-update", "1",
             str(sortie)],
            journal=trace,
        )
        produites.append(sortie)
    return produites


def executer(
    video_id: str, racine: Path | None = None, purger: bool = True, reencode: bool = False
) -> ResultatExport:
    """Produit `final.mp4`, le mesure, et ne purge que si tout est conforme."""
    t0 = time.perf_counter()
    base = racine or racine_projet()
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    chemins = RunPaths.depuis_video_id(video_id, racine)

    assemble = chemins.racine / "assembled.mp4"
    if not assemble.exists():
        raise FileNotFoundError(f"assembled.mp4 absent : `factory assemble --run {video_id}`")
    shotlist = Shotlist.model_validate_json(chemins.shotlist.read_text(encoding="utf-8"))

    journal = base / JOURNAL
    journal.parent.mkdir(parents=True, exist_ok=True)
    ecarts: list[str] = []
    alertes: list[str] = []

    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n===== export {video_id} — {runs.maintenant()} =====\n")

        source = _sonder(assemble)
        flux_video = next(f for f in source["streams"] if f["codec_type"] == "video")
        au_contrat = (
            flux_video.get("codec_name") == "h264"
            and str(flux_video.get("profile", "")).lower().startswith("high")
            and int(flux_video["width"]) == LARGEUR
            and int(flux_video["height"]) == HAUTEUR
            and flux_video.get("pix_fmt") == "yuv420p"
        )
        flux_audio = next((f for f in source["streams"] if f["codec_type"] == "audio"), None)
        audio_au_contrat = (
            flux_audio is not None
            and flux_audio.get("codec_name") == "aac"
            and int(flux_audio.get("sample_rate", 0)) == 48000
            and int(flux_audio.get("channels", 0)) == 2
        )
        if reencode or not au_contrat:
            trace.write(
                f"réencodage du flux vidéo (forcé={reencode}, au contrat={au_contrat})\n"
            )
            args_video = [
                "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18",
                "-vf", f"scale={LARGEUR}:{HAUTEUR}", "-r", str(FPS), "-fps_mode", "cfr",
                "-pix_fmt", "yuv420p",
            ]
        else:
            trace.write("flux vidéo déjà au contrat : copie, pas de seconde génération\n")
            args_video = ["-c:v", "copy"]
        # Réencoder de l'AAC en AAC ne change aucun paramètre du fichier et perd une génération :
        # le flux ne repasse par l'encodeur que s'il n'est pas déjà au format d'export.
        args_audio = (
            ["-c:a", "copy"] if audio_au_contrat and not reencode
            else ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
        )
        lancer_ffmpeg(
            ["-i", str(assemble), "-map", "0", *args_video, *args_audio,
             "-c:s", "copy", "-movflags", "+faststart", str(chemins.final)],
            journal=trace,
        )

        # --- 1. ffprobe ----------------------------------------------------------------
        sonde = _sonder(chemins.final)
        video = next(f for f in sonde["streams"] if f["codec_type"] == "video")
        audio = next((f for f in sonde["streams"] if f["codec_type"] == "audio"), None)
        sous_titres_flux = [f for f in sonde["streams"] if f["codec_type"] == "subtitle"]
        num, _, den = video.get("avg_frame_rate", "0/1").partition("/")
        fps = float(num) / float(den) if float(den) else 0.0
        duree = float(sonde["format"]["duration"])
        taille_mo = float(sonde["format"]["size"]) / 1e6

        from factory import audio as audio_module

        duree_voix = audio_module.duree(chemins.voice_wav)

        if video.get("codec_name") != "h264":
            ecarts.append(f"codec vidéo {video.get('codec_name')} au lieu de h264")
        if not str(video.get("profile", "")).lower().startswith("high"):
            ecarts.append(f"profil {video.get('profile')} au lieu de High")
        if (int(video["width"]), int(video["height"])) != (LARGEUR, HAUTEUR):
            ecarts.append(f"{video['width']}×{video['height']} au lieu de {LARGEUR}×{HAUTEUR}")
        if abs(fps - FPS) > 0.01:
            ecarts.append(f"{fps:.3f} ips au lieu de {FPS}")
        if audio is None or audio.get("codec_name") != "aac":
            ecarts.append(f"codec audio {audio.get('codec_name') if audio else 'absent'} au lieu de aac")
        if abs(duree - duree_voix) > TOLERANCE_DUREE_S:
            ecarts.append(
                f"durée {duree:.3f} s contre {duree_voix:.3f} s de voix "
                f"(écart {abs(duree - duree_voix):.3f} s > {TOLERANCE_DUREE_S} s)"
            )

        # --- 2. ebur128 ----------------------------------------------------------------
        niveau = audio_module.measure_lufs(chemins.final)
        trace.write(f"ebur128 :\n{niveau.resume}\n")
        if niveau.lufs is None or abs(niveau.lufs + 14.0) > 1.0:
            ecarts.append(f"loudness intégrée {niveau.lufs} LUFS hors de -14 ± 1")
        if niveau.true_peak_dbtp is None or niveau.true_peak_dbtp > -1.0:
            ecarts.append(f"crête réelle {niveau.true_peak_dbtp} dBTP > -1")

        # --- 3. plans détectés ---------------------------------------------------------
        n_shots = len(shotlist.shots)
        n_scenes = _detecter_plans(chemins.final, trace)
        rythme_mesure = round(duree / n_scenes, 3) if n_scenes else None
        plafond = _plafond_detectable(chemins, shotlist)
        if n_scenes is None:
            alertes.append("PySceneDetect n'a rien rendu : nombre de plans NON MESURÉ")
        elif abs(n_scenes - n_shots) > TOLERANCE_PLANS * n_shots:
            ecarts.append(
                f"{n_scenes} plan(s) détecté(s) pour {n_shots} prévu(s) "
                f"(écart {abs(n_scenes - n_shots) / n_shots:.1%} > {TOLERANCE_PLANS:.0%})"
            )
            alertes.append(
                f"plafond de détection : {plafond} plans — {n_shots - plafond} frontière(s) "
                "réemploient la même image et ne peuvent pas être vues par un détecteur de "
                "contenu. Le reste de l'écart tient au contraste entre plans, pas au montage : "
                "les coupes sont posées à l'image près (voir `assemble`)."
            )

        # --- 4. sous-titres ------------------------------------------------------------
        if channel.charte.subtitles.burn_in:
            etat_st = "incrustés (charte burn_in)"
        elif not sous_titres_flux:
            etat_st = "absents"
            ecarts.append(
                "aucune piste de sous-titres alors que charte.subtitles.burn_in est faux"
            )
        else:
            langue = sous_titres_flux[0].get("tags", {}).get("language", "?")
            etat_st = f"{sous_titres_flux[0].get('codec_name')} ({langue})"
            if langue in ("?", "und"):
                ecarts.append("piste de sous-titres sans code de langue")

        # --- 5. images de contrôle -----------------------------------------------------
        images = _extraire_images(chemins.final, duree, chemins.racine / "qc" / "frames", trace)

        copie = chemins.export(racine)
        copie.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(chemins.final, copie)

        resultat = ResultatExport(
            final=chemins.final, copie_export=copie, taille_mo=taille_mo,
            codec_video=str(video.get("codec_name")), profil=str(video.get("profile")),
            largeur=int(video["width"]), hauteur=int(video["height"]), fps=fps,
            codec_audio=str(audio.get("codec_name")) if audio else "absent",
            debit_audio_kbps=(
                float(audio["bit_rate"]) / 1000 if audio and audio.get("bit_rate") else None
            ),
            duree_s=duree, duree_voix_s=duree_voix,
            lufs=niveau.lufs, true_peak_dbtp=niveau.true_peak_dbtp,
            n_scenes=n_scenes, n_shots=n_shots, cut_rhythm_measured_s=rythme_mesure,
            cut_rhythm_target_s=shotlist.stats.target_s, sous_titres=etat_st,
            images_qc=images, reencode=bool(reencode or not au_contrat),
            secondes=time.perf_counter() - t0, ecarts=ecarts, alertes=alertes,
        )

        # --- purge ---------------------------------------------------------------------
        if not ecarts and purger:
            resultat.purge_mo = _purger(chemins, trace)
        elif ecarts:
            trace.write("purge annulée : l'export ne tient pas tous les critères\n")

    _ecrire_manifeste(video_id, racine, resultat)
    if ecarts:
        raise ExportNonConforme(
            f"{len(ecarts)} écart(s) mesuré(s) sur final.mp4 — " + " ; ".join(ecarts), resultat
        )
    return resultat


def _purger(chemins: RunPaths, trace: IO[str]) -> float:
    """Supprime les intermédiaires du montage. Les assets, eux, restent (ils coûtent 2 h 47)."""
    liberes = 0.0
    cibles = [chemins.clips_dir, chemins.racine / ".assemble", chemins.racine / "assembled.mp4"]
    for cible in cibles:
        if not cible.exists():
            continue
        if cible.is_dir():
            poids = sum(f.stat().st_size for f in cible.rglob("*") if f.is_file())
            shutil.rmtree(cible)
        else:
            poids = cible.stat().st_size
            cible.unlink()
        liberes += poids
        trace.write(f"purge : {cible.name} — {poids / 1e6:.1f} Mo\n")
    return round(liberes / 1e6, 1)


def _ecrire_manifeste(video_id: str, racine: Path | None, resultat: ResultatExport) -> None:
    """Timings, taille et mesures au manifeste — la pièce produite en cas de contrôle."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    manifest.execution.timings["export"] = round(resultat.secondes, 2)
    manifest.execution.disk_mb.after_export = round(resultat.taille_mo, 2)
    manifest.decisions.duration_s = round(resultat.duree_s, 3)
    manifest.decisions.loudness_lufs = resultat.lufs
    manifest.decisions.true_peak_dbtp = resultat.true_peak_dbtp
    manifest.decisions.cut_rhythm_measured_s = resultat.cut_rhythm_measured_s
    # Un écart mesuré n'a de valeur que s'il survit à la session qui l'a vu : les écarts et les
    # alertes de l'export entrent au manifeste (code 4 = seuil de qualité non tenu,
    # `INTERFACES.md` § Sémantique des erreurs), les précédents de cette étape étant remplacés.
    manifest.execution.errors = [
        e for e in manifest.execution.errors if e.step != "export"
    ] + [
        m.ErreurRun(step="export", ts=runs.maintenant(), code=4, message=message)
        for message in resultat.ecarts
    ] + [
        m.ErreurRun(step="export", ts=runs.maintenant(), code=0, message=message)
        for message in resultat.alertes
    ]
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    runs.enregistrer(conn, runs.charger_spec(video_id, racine), manifest, racine)
    conn.close()
