"""Boîte à outils audio : mesure, nettoyage, concaténation, normalisation.

Tout passe par **ffmpeg en binaire externe** (`outils/SELECTION.md` § 12 : le build local est
GPLv3, il ne peut pas être lié dans le processus). Aucune de ces fonctions ne charge de modèle :
elles s'exécutent dans le processus appelant, à côté du sous-processus qui porte le TTS.

Deux règles de méthode y sont codées :

* **`ebur128` imprime une ligne par trame puis un résumé** : la valeur intégrée est la
  *dernière* occurrence de `I:`, jamais la première (piège rencontré à l'étape 5.1).
* **`loudnorm` se fait en deux passes.** En une passe le filtre est dynamique et corrige au fil
  de l'eau ; la mesure préalable rend la correction *linéaire*, donc sans compression de la
  dynamique. Les valeurs mesurées sont retournées : le manifeste porte une mesure, pas la cible.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

#: Format de travail de la voix : celui que rend le TTS retenu (`RESULTATS.md` § 1.2).
SAMPLE_RATE = 24000
CHANNELS = 1
#: Seuil de détection des silences de tête et de queue, en dBFS.
SEUIL_SILENCE_DB = -45.0

_RE_INTEGRATED = re.compile(r"I:\s*(-?[\d.]+)\s*LUFS")
_RE_PEAK = re.compile(r"Peak:\s*(-?[\d.]+)\s*dBFS")
_RE_LRA = re.compile(r"LRA:\s*(-?[\d.]+)\s*LU")


class ErreurAudio(RuntimeError):
    """Un appel ffmpeg a échoué ; le message porte la fin de sa sortie d'erreur."""


@dataclass(frozen=True)
class Loudness:
    """Mesure de niveau d'un fichier, telle que rendue par `ebur128`."""

    lufs: float | None
    true_peak_dbtp: float | None
    lra: float | None
    resume: str

    @property
    def conforme(self) -> bool:
        """Vrai si le fichier tient la norme YouTube : -15 à -13 LUFS et crête ≤ -1 dBTP."""
        return (
            self.lufs is not None
            and -15.0 <= self.lufs <= -13.0
            and self.true_peak_dbtp is not None
            and self.true_peak_dbtp <= -1.0
        )


@dataclass(frozen=True)
class Loudnorm:
    """Ce que la première passe de `loudnorm` a mesuré, et ce que la seconde a produit."""

    mesure_i: float
    mesure_lra: float
    mesure_tp: float
    mesure_seuil: float
    offset: float
    mode: str
    apres: Loudness


def _binaire(nom: str) -> str:
    chemin = shutil.which(nom)
    if not chemin:
        raise ErreurAudio(f"{nom} introuvable dans le PATH")
    return chemin


def _lancer(args: list[str]) -> str:
    """Lance ffmpeg/ffprobe et rend sa sortie d'erreur ; lève si le code de retour n'est pas 0."""
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        queue = (proc.stderr or proc.stdout or "").strip().splitlines()[-12:]
        raise ErreurAudio(f"{Path(args[0]).name} code {proc.returncode} :\n" + "\n".join(queue))
    return proc.stderr + proc.stdout


def duree(chemin: Path) -> float:
    """Durée d'un fichier audio en secondes, lue par `ffprobe` sur le conteneur."""
    sortie = subprocess.run(
        [_binaire("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(chemin)],
        capture_output=True, text=True,
    )
    if sortie.returncode != 0 or not sortie.stdout.strip():
        raise ErreurAudio(f"ffprobe : durée illisible pour {chemin}")
    return float(sortie.stdout.strip())


def measure_lufs(chemin: Path) -> Loudness:
    """Niveau intégré, crête réelle et plage de dynamique, mesurés par `ebur128`.

    `peak=true` demande la **crête réelle** (true peak, sur-échantillonnée) et non la crête
    d'échantillon : c'est elle que la norme YouTube borne à -1 dBTP.

    `-map 0:a:0 -vn` n'est pas cosmétique : sans eux, ffmpeg décode aussi le flux vidéo pour
    l'envoyer au `null`, et la mesure d'un MP4 de 12 minutes passe de **4 s à plus d'une minute**
    (mesuré à l'étape 15). Le résultat, lui, est identique — seul l'audio entre dans `ebur128`.
    """
    sortie = _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-i", str(chemin),
        "-map", "0:a:0", "-vn", "-af", "ebur128=peak=true", "-f", "null", "-",
    ])
    # Le résumé final commence à la dernière ligne « Summary: » ; tout ce qui précède est
    # la trace trame par trame, dont les valeurs sont partielles.
    resume = sortie[sortie.rfind("Summary:"):] if "Summary:" in sortie else sortie[-2000:]
    integres = _RE_INTEGRATED.findall(sortie)
    cretes = _RE_PEAK.findall(sortie)
    lras = _RE_LRA.findall(sortie)
    return Loudness(
        lufs=float(integres[-1]) if integres else None,
        true_peak_dbtp=float(cretes[-1]) if cretes else None,
        lra=float(lras[-1]) if lras else None,
        resume=resume.strip(),
    )


def silence_trim(source: Path, sortie: Path, seuil_db: float = SEUIL_SILENCE_DB,
                 garde_s: float = 0.05) -> tuple[float, float]:
    """Retire le silence de tête et de queue ; rend (durée avant, durée après).

    `garde_s` laisse un court silence de part et d'autre : couper au ras de l'attaque donne
    un « claquement » à la concaténation, et le TTS place souvent une respiration utile.
    Le retournement (`areverse`) est la seule façon de traiter la queue avec `silenceremove`.
    """
    avant = duree(source)
    filtre = (
        f"silenceremove=start_periods=1:start_duration=0.1:start_threshold={seuil_db}dB"
        f":start_silence={garde_s}:detection=rms,"
        "areverse,"
        f"silenceremove=start_periods=1:start_duration=0.1:start_threshold={seuil_db}dB"
        f":start_silence={garde_s}:detection=rms,"
        "areverse"
    )
    _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-y", "-i", str(source),
        "-af", filtre, "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-c:a", "pcm_s16le",
        str(sortie),
    ])
    return avant, duree(sortie)


def atempo(source: Path, sortie: Path, vitesse: float) -> float:
    """Change la vitesse sans toucher à la hauteur. Rend la durée obtenue.

    Le TTS retenu **n'expose aucun paramètre de vitesse** (`Qwen3TTSModel.generate_custom_voice`
    ne prend que `text`, `speaker`, `language` et `instruct`) : la vitesse de la charte est donc
    appliquée après coup. `atempo` est borné à [0,5 ; 100] par filtre ; au-delà on en chaîne deux.
    """
    if abs(vitesse - 1.0) < 1e-3:
        shutil.copyfile(source, sortie)
        return duree(sortie)
    if not 0.5 <= vitesse <= 2.0:
        raise ErreurAudio(f"vitesse {vitesse} hors [0,5 ; 2,0] : refusée plutôt que chaînée")
    _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-y", "-i", str(source),
        "-af", f"atempo={vitesse:.4f}", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
        "-c:a", "pcm_s16le", str(sortie),
    ])
    return duree(sortie)


def hauteur(source: Path, sortie: Path, demi_tons: float) -> float:
    """Décale la hauteur de `demi_tons` sans changer la durée (asetrate + atempo inverse)."""
    facteur = 2 ** (demi_tons / 12)
    _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-y", "-i", str(source),
        "-af", f"asetrate={SAMPLE_RATE * facteur:.2f},aresample={SAMPLE_RATE},"
               f"atempo={1 / facteur:.5f}",
        "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-c:a", "pcm_s16le", str(sortie),
    ])
    return duree(sortie)


def silence(duree_s: float, sortie: Path) -> Path:
    """Écrit un fichier de silence au format de travail."""
    _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
        "-t", f"{max(0.0, duree_s):.3f}", "-c:a", "pcm_s16le", str(sortie),
    ])
    return sortie


def concat(wavs: list[Path], pauses: list[float], sortie: Path) -> list[tuple[float, float]]:
    """Concatène des WAV en insérant `pauses[i]` secondes de silence **avant** `wavs[i]`.

    Rend la position (début, fin) de chaque WAV dans le fichier produit. Les positions sont
    accumulées à partir des durées mesurées pièce par pièce, puis **recalées sur la durée réelle
    du fichier de sortie** : un écart de quelques millisecondes par pièce se cumulerait sur
    vingt-huit segments et décalerait toute la piste de sous-titres.
    """
    if len(pauses) != len(wavs):
        raise ErreurAudio(f"concat : {len(wavs)} fichiers pour {len(pauses)} pauses")
    if not wavs:
        raise ErreurAudio("concat : aucun fichier")

    positions: list[tuple[float, float]] = []
    with tempfile.TemporaryDirectory(prefix="factory-concat-") as tmp:
        dossier = Path(tmp)
        morceaux: list[Path] = []
        horloge = 0.0
        for index, (wav, pause) in enumerate(zip(wavs, pauses, strict=True)):
            if pause > 0:
                blanc = silence(pause, dossier / f"pause_{index:03d}.wav")
                morceaux.append(blanc)
                horloge += duree(blanc)
            morceaux.append(wav)
            longueur = duree(wav)
            positions.append((horloge, horloge + longueur))
            horloge += longueur

        liste = dossier / "liste.txt"
        liste.write_text(
            "".join(f"file '{m.resolve()}'\n" for m in morceaux), encoding="utf-8"
        )
        _lancer([
            _binaire("ffmpeg"), "-hide_banner", "-nostats", "-y",
            "-f", "concat", "-safe", "0", "-i", str(liste),
            "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-c:a", "pcm_s16le", str(sortie),
        ])

    reelle = duree(sortie)
    if horloge > 0 and abs(reelle - horloge) > 0.01:
        facteur = reelle / horloge
        positions = [(d * facteur, f * facteur) for d, f in positions]
    return positions


def loudnorm_two_pass(source: Path, sortie: Path, target: float = -14.0, tp: float = -1.0,
                      lra: float = 11.0, sample_rate: int = SAMPLE_RATE,
                      channels: int = CHANNELS) -> Loudnorm:
    """Normalise à `target` LUFS / `tp` dBTP en deux passes, et rend ce qui a été mesuré.

    Passe 1 : `loudnorm` en analyse seule, sortie JSON. Passe 2 : le même filtre nourri des
    valeurs mesurées, ce qui le rend **linéaire** — un simple gain — au lieu de la compression
    dynamique de la passe unique. `loudnorm` travaille en interne à 192 kHz : `-ar` remet le
    fichier au format de travail, sans quoi `voice.wav` pèserait huit fois son poids.
    """
    brut = _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-i", str(source),
        "-af", f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json",
        "-f", "null", "-",
    ])
    debut = brut.rfind("{")
    fin = brut.rfind("}")
    if debut < 0 or fin < debut:
        raise ErreurAudio("loudnorm : aucune mesure JSON en sortie de la première passe")
    mesure = json.loads(brut[debut:fin + 1])

    filtre = (
        f"loudnorm=I={target}:TP={tp}:LRA={lra}"
        f":measured_I={mesure['input_i']}:measured_LRA={mesure['input_lra']}"
        f":measured_TP={mesure['input_tp']}:measured_thresh={mesure['input_thresh']}"
        f":offset={mesure['target_offset']}:linear=true:print_format=summary"
    )
    resume = _lancer([
        _binaire("ffmpeg"), "-hide_banner", "-nostats", "-y", "-i", str(source),
        "-af", filtre, "-ar", str(sample_rate), "-ac", str(channels), "-c:a", "pcm_s16le",
        str(sortie),
    ])
    # Le mode retenu est celui de la **seconde** passe, pas celui qu'annonçait la première :
    # `loudnorm` retombe en dynamique quand le gain demandé ferait dépasser la crête cible.
    modes = re.findall(r"Normalization Type:\s*(\w+)", resume)
    return Loudnorm(
        mesure_i=float(mesure["input_i"]),
        mesure_lra=float(mesure["input_lra"]),
        mesure_tp=float(mesure["input_tp"]),
        mesure_seuil=float(mesure["input_thresh"]),
        offset=float(mesure["target_offset"]),
        mode=modes[-1].lower() if modes else str(mesure.get("normalization_type", "")),
        apres=measure_lufs(sortie),
    )
