"""Étape `assemble` — les 127 clips deviennent une vidéo : transitions, mixage, sous-titres.

**Le problème central de cette étape est la durée, et il n'est pas évident.** Les clips sont
rendus à la durée exacte de leur plan, elle-même calée sur la voix : leur somme *est* la piste
voix. Or un fondu enchaîné consomme du temps — `xfade` de durée *d* rend `lenA + lenB - d`. Sur
les 55 fondus de ce run, un enchaînement naïf raccourcirait la vidéo de **16 s** et décalerait
l'image de la voix un peu plus à chaque fondu, jusqu'à 16 s à la fin. Le critère « durée = durée
de la voix ± 0,5 s » ne serait pas seulement raté : le montage serait faux.

La parade tient en une phrase : **une transition ne prend jamais de temps à la ligne du temps,
elle en emprunte aux plans qu'elle relie**, et le montage est fait de pièces dont la somme des
images est, par construction, celle des clips d'origine.

| Transition | Ce que la pièce contient | Ce qu'elle coûte aux plans |
|---|---|---|
| `cut` | rien | rien |
| `fade` (fondu enchaîné, *d*) | dernière image du plan sortant, gelée, fondue sur les *d* premières secondes du plan entrant | le plan entrant perd *d* en tête |
| `dip_black` (fondu au noir, *d*) | queue du sortant qui s'éteint (*d*/2) puis tête de l'entrant qui s'allume (*d*/2) | *d*/2 à chacun |

Le plan sortant d'un fondu enchaîné est donc *gelé* pendant *d* — 0,33 s — pendant que le plan
suivant, lui, est déjà en mouvement sous le fondu. C'est le seul compromis du dispositif, et il
est du bon côté : le mouvement du plan entrant démarre à l'heure.

Les pièces sont encodées **aux réglages exacts des clips** (`factory.video.arguments_encodage`),
puis jointes par le démultiplexeur `concat` en **copie de flux** : un plan sur lequel aucune
transition ne mord n'est pas réencodé du tout. Le compte d'images du fichier produit est
ensuite vérifié contre la somme attendue — c'est la preuve que le dispositif tient.

Côté son : voix + lit musical ducké (`sidechaincompress`), normalisation -14 LUFS en deux
passes, et `video_nomusic.mp4` livré d'abord pour que le défaut, s'il y en a un, se voie sans
la musique par-dessus.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from factory.core import config as config_module
from factory.core import db, runs
from factory.core.models import Channel, Shot, Shotlist
from factory.core.paths import RunPaths, racine_projet
from factory.video import CRF, FPS, InfoClip, arguments_encodage, ffprobe_clip, lancer_ffmpeg

#: Journal de l'étape (`CLAUDE.md` § 2) — toute la sortie ffmpeg y va, jamais à l'écran.
JOURNAL = "workspace/logs/etape13_1.log"
#: Atténuation du lit sous la voix, en dB (prompt de l'étape 13.1).
MUSIQUE_DB = -18.0
#: Atténuation du lit pendant un segment sponsorisé — la mention légale doit s'entendre.
MUSIQUE_SPONSOR_DB = -24.0
#: Codes ISO 639-2/B attendus par le conteneur MP4 pour la piste de sous-titres.
LANGUES_ISO3 = {"fr": "fra", "en": "eng", "es": "spa", "it": "ita", "de": "deu", "pt": "por"}


class MontageImpossible(RuntimeError):
    """Le montage ne peut pas se faire ; le message dit ce qui manque, sans repli silencieux."""


@dataclass(frozen=True)
class Piece:
    """Un morceau de la ligne du temps : un corps de plan, ou une transition."""

    chemin: Path
    images: int
    genre: str  # corps | fondu | noir_sortie | noir_entree
    origine: str


@dataclass
class ResultatMontage:
    """Ce que le montage a produit, et ce qu'il a mesuré."""

    video_nomusic: Path
    assembled: Path
    images: int
    images_attendues: int
    duree_video_s: float
    duree_voix_s: float
    transitions: dict[str, int]
    pieces_reencodees: int
    musique: str
    musique_motif: str
    sous_titres: str
    lufs: float | None
    true_peak_dbtp: float | None
    secondes: float
    alertes: list[str] = field(default_factory=list)

    @property
    def ecart_duree_s(self) -> float:
        """Écart entre la vidéo montée et la voix — le critère dur de l'étape."""
        return abs(self.duree_video_s - self.duree_voix_s)


# --------------------------------------------------------------------------------------
# Ligne du temps
# --------------------------------------------------------------------------------------


def _transitions_effectives(
    shots: list[Shot], roles: dict[str, str], transitions_charte: set[str]
) -> tuple[list[str], list[str]]:
    """Transition retenue pour chaque plan, et la liste des forçages, en clair.

    Deux règles s'ajoutent à ce qu'a écrit `shotlist` : **le hook coupe franc** (une vidéo dont
    les deux premières secondes s'enchaînent en douceur perd le bénéfice du hook), et une
    transition absente de `charte.transitions[]` retombe sur la coupe plutôt que d'inventer.
    """
    retenues: list[str] = []
    forcages: list[str] = []
    for rang, shot in enumerate(shots):
        voulue = shot.transition_in
        if rang == 0:
            retenues.append(voulue if voulue in transitions_charte else "cut")
            continue
        if voulue not in transitions_charte:
            forcages.append(f"{shot.id} : {voulue} hors charte → cut")
            voulue = "cut"
        elif roles.get(shot.segment_id) == "hook" and voulue != "cut":
            forcages.append(f"{shot.id} : {voulue} dans le hook → cut")
            voulue = "cut"
        retenues.append(voulue)
    return retenues, forcages


def _plan_de_coupe(
    shots: list[Shot], infos: list[InfoClip], transitions: list[str], images_fondu: int
) -> tuple[list[tuple[int, int]], list[str]]:
    """Rognes de tête et de queue de chaque plan, imposées par les transitions qui l'encadrent.

    Un plan trop court pour être rogné fait retomber **sa** transition sur une coupe : mieux vaut
    une coupe franche isolée qu'un plan réduit à trois images.
    """
    minimum = max(FPS // 2, images_fondu + 2)  # un demi-seconde de plan doit survivre
    rognes = [[0, 0] for _ in shots]
    alertes: list[str] = []
    demi = images_fondu // 2
    for rang in range(1, len(shots)):
        genre = transitions[rang]
        if genre == "cut":
            continue
        entrant, sortant = infos[rang], infos[rang - 1]
        if genre == "fade":
            besoin_entrant, besoin_sortant = images_fondu, 0
        else:  # dip_black
            besoin_entrant, besoin_sortant = images_fondu - demi, demi
        reste_entrant = entrant.images - rognes[rang][0] - rognes[rang][1] - besoin_entrant
        reste_sortant = sortant.images - rognes[rang - 1][0] - rognes[rang - 1][1] - besoin_sortant
        if reste_entrant < minimum or reste_sortant < minimum:
            alertes.append(
                f"{shots[rang].id} : {genre} impossible (plan trop court) → cut"
            )
            transitions[rang] = "cut"
            continue
        rognes[rang][0] += besoin_entrant
        rognes[rang - 1][1] += besoin_sortant
    return [(t, q) for t, q in rognes], alertes


# --------------------------------------------------------------------------------------
# Rendu des pièces
# --------------------------------------------------------------------------------------


def _corps(
    clip: Path, info: InfoClip, rogne: tuple[int, int], sortie: Path,
    fondu_ouverture: int, trace: IO[str],
) -> Piece:
    """Corps d'un plan : le clip moins ce que les transitions lui ont pris.

    Un plan qu'aucune transition ne touche **n'est pas réencodé** : il entre tel quel dans la
    liste de concaténation. C'est ce qui fait tomber le montage de 127 réencodages à 84.
    """
    tete, queue = rogne
    images = info.images - tete - queue
    if tete == 0 and queue == 0 and fondu_ouverture == 0:
        return Piece(chemin=clip, images=images, genre="corps", origine=clip.stem)
    filtres = [f"trim=start_frame={tete}:end_frame={info.images - queue}", "setpts=PTS-STARTPTS"]
    if fondu_ouverture:
        filtres.append(f"fade=t=in:st=0:d={fondu_ouverture / FPS:.4f}")
    lancer_ffmpeg(
        ["-i", str(clip), "-vf", ",".join(filtres), *arguments_encodage(sortie, images / FPS)],
        journal=trace,
    )
    return Piece(chemin=sortie, images=images, genre="corps", origine=clip.stem)


def _fondu_enchaine(
    sortant: Path, info_sortant: InfoClip, entrant: Path, images: int, dossier: Path,
    trace: IO[str],
) -> Piece:
    """Fondu enchaîné : dernière image du plan sortant, gelée, fondue sur la tête de l'entrant.

    `-loop 1` sur l'image gelée n'est pas décoratif : sans lui, une image fixe ne fournit qu'une
    seule image à ffmpeg et la pièce sort à 0,033 s (bogue mesuré le 16/09/2026 sur les clips).
    """
    gelee = dossier / f"{sortant.stem}_derniere.png"
    lancer_ffmpeg(
        ["-i", str(sortant), "-vf", f"select='eq(n\\,{info_sortant.images - 1})'",
         "-frames:v", "1", "-update", "1", str(gelee)],
        journal=trace,
    )
    sortie = dossier / f"fondu_{entrant.stem}.mp4"
    duree = images / FPS
    # `settb=AVTB` sur les deux branches n'est pas cosmétique : `xfade` refuse de se configurer
    # quand les bases de temps diffèrent (une image fixe arrive en 1/30, un MP4 en 1/15360) —
    # « First input link main timebase (1/30) do not match … (1/15360) », mesuré le 16/09/2026.
    filtre = (
        f"[0:v]fps={FPS},format=yuv420p,trim=end_frame={images},"
        "setpts=PTS-STARTPTS,settb=AVTB[a];"
        f"[1:v]trim=end_frame={images},setpts=PTS-STARTPTS,settb=AVTB,format=yuv420p[b];"
        f"[a][b]xfade=transition=fade:duration={duree:.4f}:offset=0[v]"
    )
    lancer_ffmpeg(
        ["-loop", "1", "-framerate", str(FPS), "-i", str(gelee), "-i", str(entrant),
         "-filter_complex", filtre, "-map", "[v]", *arguments_encodage(sortie, duree)],
        journal=trace,
    )
    return Piece(chemin=sortie, images=images, genre="fondu", origine=entrant.stem)


def _vers_le_noir(
    clip: Path, info: InfoClip, images: int, dossier: Path, trace: IO[str]
) -> Piece:
    """Queue d'un plan qui s'éteint au noir."""
    sortie = dossier / f"noir_sortie_{clip.stem}.mp4"
    filtre = (
        f"trim=start_frame={info.images - images},setpts=PTS-STARTPTS,"
        f"fade=t=out:st=0:d={images / FPS:.4f}"
    )
    lancer_ffmpeg(
        ["-i", str(clip), "-vf", filtre, *arguments_encodage(sortie, images / FPS)], journal=trace
    )
    return Piece(chemin=sortie, images=images, genre="noir_sortie", origine=clip.stem)


def _depuis_le_noir(clip: Path, images: int, dossier: Path, trace: IO[str]) -> Piece:
    """Tête d'un plan qui s'allume depuis le noir."""
    sortie = dossier / f"noir_entree_{clip.stem}.mp4"
    filtre = (
        f"trim=end_frame={images},setpts=PTS-STARTPTS,fade=t=in:st=0:d={images / FPS:.4f}"
    )
    lancer_ffmpeg(
        ["-i", str(clip), "-vf", filtre, *arguments_encodage(sortie, images / FPS)], journal=trace
    )
    return Piece(chemin=sortie, images=images, genre="noir_entree", origine=clip.stem)


def _concatener(pieces: list[Piece], sortie: Path, dossier: Path, trace: IO[str]) -> None:
    """Joint les pièces en **copie de flux** : aucune image n'est réencodée une seconde fois."""
    liste = dossier / "pieces.txt"
    liste.write_text(
        "".join(f"file '{p.chemin.resolve()}'\n" for p in pieces), encoding="utf-8"
    )
    lancer_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy",
         "-movflags", "+faststart", str(sortie)],
        journal=trace,
    )


# --------------------------------------------------------------------------------------
# Son
# --------------------------------------------------------------------------------------


def _filtre_lit(sponsors: list[tuple[float, float]]) -> str:
    """Gain du lit : -18 dB sous la voix, -24 dB pendant un segment sponsorisé."""
    chaine = [f"volume={MUSIQUE_DB}dB"]
    for debut, fin in sponsors:
        surplus = MUSIQUE_SPONSOR_DB - MUSIQUE_DB
        chaine.append(
            f"volume=enable='between(t,{debut:.3f},{fin:.3f})':volume={surplus}dB"
        )
    return ",".join(chaine)


def mixer(
    voix: Path, lit: Path | None, sortie: Path, duree_s: float,
    sponsors: list[tuple[float, float]], trace: IO[str], sample_rate: int = 48000,
) -> None:
    """Voix + lit ducké. Sans lit, la voix est simplement portée au format de sortie.

    Le ducking est un `sidechaincompress` dont **la clé est la voix et l'entrée le lit** : le lit
    baisse quand la voix parle et remonte dans les silences. Un `amix` sans `normalize=0`
    diviserait les deux entrées par deux et ferait perdre 6 dB à la voix — le piège classique.
    """
    commun = f"aresample={sample_rate},aformat=sample_fmts=fltp:channel_layouts=stereo"
    if lit is None:
        lancer_ffmpeg(
            ["-i", str(voix), "-af", f"{commun},apad", "-t", f"{duree_s:.3f}",
             "-c:a", "pcm_s16le", str(sortie)],
            journal=trace,
        )
        return
    filtre = (
        f"[0:a]{commun},apad,asplit=2[voix][cle];"
        f"[1:a]{commun},{_filtre_lit(sponsors)}[lit];"
        f"[lit][cle]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
        f"[voix][duck]amix=inputs=2:duration=first:normalize=0[mix]"
    )
    lancer_ffmpeg(
        ["-i", str(voix), "-i", str(lit), "-filter_complex", filtre, "-map", "[mix]",
         "-t", f"{duree_s:.3f}", "-c:a", "pcm_s16le", str(sortie)],
        journal=trace,
    )


def _filtres_disponibles() -> set[str]:
    """Filtres que le ffmpeg de la machine expose réellement — mesuré, jamais supposé."""
    sortie = subprocess.run(
        [shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-filters"],
        capture_output=True, text=True, check=False,
    ).stdout
    return {ligne.split()[1] for ligne in sortie.splitlines() if len(ligne.split()) > 2}


# --------------------------------------------------------------------------------------
# Étape
# --------------------------------------------------------------------------------------


def executer(video_id: str, racine: Path | None = None, force: bool = False) -> ResultatMontage:
    """Monte le run : transitions, voix, lit musical, sous-titres, normalisation."""
    t0 = time.perf_counter()
    base = racine or racine_projet()
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel: Channel = cfg.get_channel(spec.channel_id)
    chemins = RunPaths.depuis_video_id(video_id, racine)

    if not chemins.shotlist.exists():
        raise FileNotFoundError(f"shotlist.json absent : `factory shotlist --run {video_id}`")
    if not chemins.voice_wav.exists():
        raise FileNotFoundError(f"voice/voice.wav absent : `factory voice --run {video_id}`")
    shotlist = Shotlist.model_validate_json(chemins.shotlist.read_text(encoding="utf-8"))
    script = None
    if chemins.script.exists():
        from factory.core.models import Script

        script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    roles = {s.id: s.role for s in script.segments} if script else {}

    manquants = [s.id for s in shotlist.shots if not chemins.clip(s.id).exists()]
    if manquants:
        raise FileNotFoundError(
            f"{len(manquants)} clip(s) absent(s) — `factory render --run {video_id}` "
            f"(premiers : {', '.join(manquants[:5])})"
        )

    journal = base / JOURNAL
    journal.parent.mkdir(parents=True, exist_ok=True)
    dossier = chemins.racine / ".assemble"
    if dossier.exists() and force:
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    alertes: list[str] = []
    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n===== assemble {video_id} — {runs.maintenant()} =====\n")

        # --- ligne du temps ------------------------------------------------------------
        infos = [ffprobe_clip(chemins.clip(s.id)) for s in shotlist.shots]
        images_attendues = sum(i.images for i in infos)
        images_fondu = round(channel.charte.transition_duration_s * FPS)
        transitions, forcages = _transitions_effectives(
            shotlist.shots, roles, set(channel.charte.transitions)
        )
        rognes, alertes_rogne = _plan_de_coupe(shotlist.shots, infos, transitions, images_fondu)
        alertes.extend(forcages + alertes_rogne)
        trace.write(
            f"transitions : {images_fondu} images ({images_fondu / FPS:.3f} s) · "
            + " ".join(f"{g}={transitions.count(g)}" for g in ("cut", "fade", "dip_black"))
            + f" · images attendues {images_attendues}\n"
        )

        # --- pièces --------------------------------------------------------------------
        pieces: list[Piece] = []
        for rang, shot in enumerate(shotlist.shots):
            clip = chemins.clip(shot.id)
            genre = transitions[rang]
            if rang > 0 and genre == "fade":
                pieces.append(
                    _fondu_enchaine(
                        chemins.clip(shotlist.shots[rang - 1].id), infos[rang - 1],
                        clip, images_fondu, dossier, trace,
                    )
                )
            elif rang > 0 and genre == "dip_black":
                demi = images_fondu // 2
                pieces.append(
                    _vers_le_noir(
                        chemins.clip(shotlist.shots[rang - 1].id), infos[rang - 1],
                        demi, dossier, trace,
                    )
                )
                pieces.append(_depuis_le_noir(clip, images_fondu - demi, dossier, trace))
            ouverture = images_fondu if (rang == 0 and genre == "fade") else 0
            pieces.append(
                _corps(clip, infos[rang], rognes[rang], dossier / f"corps_{shot.id}.mp4",
                       ouverture, trace)
            )

        somme = sum(p.images for p in pieces)
        if somme != images_attendues:
            raise MontageImpossible(
                f"ligne du temps incohérente : {somme} images de pièces pour {images_attendues} "
                "attendues — une transition a pris du temps à la vidéo"
            )
        reencodees = sum(1 for p in pieces if p.chemin.parent == dossier)

        # --- piste vidéo ---------------------------------------------------------------
        piste_video = dossier / "video_track.mp4"
        _concatener(pieces, piste_video, dossier, trace)
        info_video = ffprobe_clip(piste_video)
        if info_video.images != images_attendues:
            raise MontageImpossible(
                f"concaténation : {info_video.images} images au lieu de {images_attendues}"
            )
        trace.write(
            f"piste vidéo : {info_video.images} images · {info_video.duree_s:.3f} s · "
            f"{reencodees} pièce(s) réencodée(s) sur {len(pieces)}\n"
        )

        # --- son -----------------------------------------------------------------------
        from factory import audio as audio_module
        from factory.assets import music as music_module

        duree_voix = audio_module.duree(chemins.voice_wav)
        duree_video = info_video.duree_s

        pistes, refus = music_module.charger_bibliotheque(racine)
        alertes.extend(refus)
        niche = cfg.niches.get(channel.niche)
        mood = (script.music_mood if script else None) or (
            niche.musique.mood if niche else "curieux"
        )
        conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
        music_module.indexer(conn, pistes, racine)
        piste, motif = music_module.choisir(pistes, mood, conn, channel.id)

        lit = None
        if piste is not None:
            lit = dossier / "lit.wav"
            music_module.preparer_lit(piste, duree_video, lit, journal=trace)
            music_module.enregistrer_usage(conn, piste, video_id, channel.id)
            trace.write(f"lit musical : {piste.slug} ({piste.licence}) — {motif}\n")
        else:
            alertes.append(
                f"lit silencieux : aucune piste sous licence dans workspace/library/music/ "
                f"({motif}) — la vidéo se monte, mais `music_track` reste vide et la "
                "publication est bloquée (CONFORMITE.md § 10.1)"
            )
            trace.write(f"lit musical : AUCUN — {motif}\n")

        sponsors = [
            (s.start_s, s.end_s) for s in shotlist.shots if s.is_sponsor
        ]
        melange = dossier / "mix.wav"
        mixer(chemins.voice_wav, lit, melange, duree_video, sponsors, trace)
        normalise = dossier / "mix_norm.wav"
        mesure = audio_module.loudnorm_two_pass(
            melange, normalise, sample_rate=48000, channels=2
        )
        trace.write(
            f"loudnorm : {mesure.mesure_i:.2f} → {mesure.apres.lufs} LUFS "
            f"(mode {mesure.mode}, crête {mesure.apres.true_peak_dbtp} dBTP)\n"
        )

        # --- livrables -----------------------------------------------------------------
        aac = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
        lancer_ffmpeg(
            ["-i", str(piste_video), "-i", str(chemins.voice_wav),
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", *aac,
             "-movflags", "+faststart", str(chemins.video_nomusic)],
            journal=trace,
        )

        assemble = chemins.racine / "assembled.mp4"
        sous_titres = _muxer(
            piste_video, normalise, chemins, channel, assemble, aac, trace
        )

        conn.close()

    secondes = time.perf_counter() - t0
    resultat = ResultatMontage(
        video_nomusic=chemins.video_nomusic, assembled=assemble,
        images=info_video.images, images_attendues=images_attendues,
        duree_video_s=duree_video, duree_voix_s=duree_voix,
        transitions={g: transitions.count(g) for g in ("cut", "fade", "dip_black")},
        pieces_reencodees=reencodees,
        musique=piste.slug if piste else "silence",
        musique_motif=motif, sous_titres=sous_titres,
        lufs=mesure.apres.lufs, true_peak_dbtp=mesure.apres.true_peak_dbtp,
        secondes=secondes, alertes=alertes,
    )
    _ecrire_manifeste(video_id, racine, channel, piste, resultat, mood)
    return resultat


def _muxer(
    piste_video: Path, audio: Path, chemins: RunPaths, channel: Channel, sortie: Path,
    aac: list[str], trace: IO[str],
) -> str:
    """Sous-titres : incrustation si la charte l'exige, sinon piste `mov_text` muxée.

    `burn_in: true` sur ce poste **échoue** au lieu de retomber en silence sur le mux : la build
    ffmpeg de la machine est compilée sans `libass`, et une vidéo livrée sans les sous-titres
    qu'on croyait incrustés est le pire des deux résultats.
    """
    langue = LANGUES_ISO3.get(channel.lang, channel.lang)
    if channel.charte.subtitles.burn_in:
        if "subtitles" not in _filtres_disponibles():
            raise MontageImpossible(
                "charte.subtitles.burn_in = true mais le filtre `subtitles` est absent de cette "
                "build ffmpeg (compilée sans libass) : incrustation impossible. Passe la charte "
                "en burn_in: false (route mov_text) ou installe un ffmpeg avec libass."
            )
        lancer_ffmpeg(
            ["-i", str(piste_video), "-i", str(audio),
             "-vf", f"subtitles={chemins.subtitles_ass}", "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF),
             "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
             *aac, "-movflags", "+faststart", str(sortie)],
            journal=trace,
        )
        return "incrustés (subtitles.ass)"
    if not chemins.subtitles_srt.exists():
        raise FileNotFoundError(f"subtitles.srt absent : `factory subtitles --run {chemins.video_id}`")
    lancer_ffmpeg(
        ["-i", str(piste_video), "-i", str(audio), "-i", str(chemins.subtitles_srt),
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy", *aac,
         "-c:s", "mov_text", "-metadata:s:s:0", f"language={langue}",
         "-movflags", "+faststart", str(sortie)],
        journal=trace,
    )
    return f"piste mov_text ({langue})"


def _ecrire_manifeste(
    video_id: str, racine: Path | None, channel: Channel, piste, resultat: ResultatMontage,
    mood: str,
) -> None:
    """Inscrit au manifeste ce que le montage a **mesuré**, jamais ce qu'il visait."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    manifest.execution.timings["assemble"] = round(resultat.secondes, 2)
    manifest.decisions.loudness_lufs = resultat.lufs
    manifest.decisions.true_peak_dbtp = resultat.true_peak_dbtp
    manifest.decisions.music_track = piste.vers_manifeste(channel.id) if piste else None
    manifest.decisions.music_warning = None if piste else (
        f"lit silencieux : aucune piste sous licence dans workspace/library/music/ pour le mood "
        f"« {mood} ». Freesound est écarté depuis le 15/09/2026 (CGU de l'API non commerciales) ; "
        "la source retenue reste la bibliothèque audio du Studio de la chaîne."
    )
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    runs.enregistrer(conn, runs.charger_spec(video_id, racine), manifest, racine)
    conn.close()
