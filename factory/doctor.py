"""factory doctor — preuve en quelques minutes que chaque brique répond.

Principe : aucun contrôle ne fait confiance à une version affichée. Chaque brique
lourde est réellement exercée (20 jetons générés, une phrase synthétisée puis
retranscrite, une image produite puis sa carte de profondeur), et chacune tourne
dans un SOUS-PROCESSUS séparé qui se termine — règle CLAUDE.md § 4 : un seul
modèle résident en mémoire à la fois. Timeout de 180 s par brique.

Usage interne : `python -m factory.doctor --probe <nom>` exécute une sonde et
imprime une ligne JSON sur la sortie standard. C'est ce que lance le parent.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "workspace" / "logs"
LEDGER = ROOT / "outils" / "MODELES.md"

TIMEOUT_S = 180
DISQUE_MINIMUM_GO = 8.0

# Identifiants figés par les étapes 5.1 et 5.2 (outils/MODELES.md).
LLM_GGUF = "models/llamacpp/models--bartowski--Qwen_Qwen3.5-9B-GGUF/snapshots/182be2fd6c7bc44887d88a91cb03ff009cc9f549/Qwen_Qwen3.5-9B-Q4_K_M.gguf"
TTS_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
ASR_MODEL = "mlx-community/parakeet-tdt-0.6b-v3"
ASR_REPLI = "mlx-community/whisper-large-v3-turbo"
# Piège de licence (STATE.md) : tout autre dépôt FLUX.2 est non commercial.
IMAGE_MODEL = "mlx-community/FLUX.2-Klein-4B-4bit"
DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
RHUBARB = ROOT / "outils" / "rhubarb" / "rhubarb"

PHRASES = {
    "fr": "Bonjour, ceci est un test.",
    "en": "Hello, this is a test.",
}
LANGUES_TTS = {"fr": "French", "en": "English"}
VOIX_TTS = "Serena"

# Seuil du contrôle ASR : taux d'erreur sur les mots (WER) de la phrase de test.
# Les phrases font 5 mots — 0,20 tolère UN mot faux, refuse deux. Une recherche de
# sous-chaîne ne convient pas : « Bonsour, Cecil Dontest. » contient « test » et
# passerait, avec trois mots sur quatre faux (WER 100 %).
ASR_WER_MAX = 0.20

# Le chaînage TTS → ASR mesure DEUX choses à la fois : l'ASR, et la voix qu'on lui
# donne à entendre. Pour que le doctor teste l'ASR, il faut une voix connue bonne.
# Mesuré le 15/09/2026 — 16 synthèses de la phrase FR, une par run, même méthode :
#   FR (parakeet) — 7 propres, 2 à 20 %, 7 à 60 % ou plus. Médiane 20 %, moyenne 36 %.
#                   Échantillons rendus : « Bourjour, Cissy Edentest. », « Society and test ».
#   EN — WER 0 % sur 6 mesures (3 synthèses × 2 ASR).
#   Contre-épreuve : whisper entend le même FR à 0/40/60 %. Les deux ASR tombent
#   d'accord — ce n'est pas l'ASR, c'est le français de Serena (voix chinoise en
#   cross-lingual), qui échoue une fois sur deux. L'ANGLAIS gouverne donc le code de retour ;
# le FRANÇAIS est mesuré et affiché en WARN — c'est le risque « ≥ 2 voix par langue »
# de l'étape 5.1 qui se voit, à chaque session, au lieu de rester dans un document.
SONDES_NON_BLOQUANTES = {"asr_fr"}


# --------------------------------------------------------------------------
# Résultat d'un contrôle
# --------------------------------------------------------------------------
@dataclass
class Resultat:
    nom: str
    ok: bool
    message: str
    secondes: float = 0.0
    saute: bool = False
    alerte: bool = False
    details: dict = field(default_factory=dict)

    @property
    def etat(self) -> str:
        if self.saute:
            return "SKIP"
        if self.alerte:
            return "WARN"
        return "PASS" if self.ok else "FAIL"


def _go_libres() -> float:
    return shutil.disk_usage("/").free / 1e9


def charge_env() -> None:
    """Charge .env puis résout les chemins de cache en absolu.

    `huggingface_hub` lit HF_HOME **à l'import** : la variable doit être posée
    avant tout import de transformers, mlx ou parakeet (panne rencontrée en 5.1,
    qui avait fait télécharger whisper deux fois).
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:  # python-dotenv absent : on se rabat sur l'environnement
        pass
    defauts = {
        "HF_HOME": "./models/hf",
        "OLLAMA_MODELS": "./models/ollama",
        "LLAMA_CACHE": "./models/llamacpp",
    }
    for cle, defaut in defauts.items():
        valeur = os.environ.get(cle) or defaut
        os.environ[cle] = str((ROOT / valeur).resolve()) if not Path(valeur).is_absolute() else valeur
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# --------------------------------------------------------------------------
# Contrôles statiques (dans le processus courant)
# --------------------------------------------------------------------------
def check_python() -> Resultat:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 12)
    return Resultat("python", ok, f"{v.major}.{v.minor}.{v.micro} (requis ≥ 3.12)")


def _version_binaire(nom: str) -> tuple[bool, str]:
    chemin = shutil.which(nom)
    if not chemin:
        return False, "absent du PATH"
    p = subprocess.run([nom, "-version"], capture_output=True, text=True, timeout=20)
    premiere = p.stdout.splitlines()[0] if p.stdout else p.stderr.splitlines()[0]
    m = re.search(r"version (\S+)", premiere)
    return True, m.group(1) if m else premiere[:40]


def check_ffmpeg() -> Resultat:
    ok, msg = _version_binaire("ffmpeg")
    return Resultat("ffmpeg", ok, msg)


def check_ffprobe() -> Resultat:
    ok, msg = _version_binaire("ffprobe")
    return Resultat("ffprobe", ok, msg)


def check_disque() -> Resultat:
    libre = _go_libres()
    return Resultat(
        "disque", libre >= DISQUE_MINIMUM_GO,
        f"{libre:.1f} Go libres (plancher {DISQUE_MINIMUM_GO:.0f} Go)",
    )


def check_env() -> Resultat:
    """HF_HOME, OLLAMA_MODELS et LLAMA_CACHE doivent pointer sous models/."""
    models = (ROOT / "models").resolve()
    manques = []
    for cle in ("HF_HOME", "OLLAMA_MODELS", "LLAMA_CACHE"):
        valeur = os.environ.get(cle)
        if not valeur:
            manques.append(f"{cle} non défini")
            continue
        try:
            Path(valeur).resolve().relative_to(models)
        except ValueError:
            manques.append(f"{cle}={valeur} hors de models/")
    if manques:
        return Resultat("variables", False, " ; ".join(manques))
    return Resultat("variables", True, "HF_HOME, OLLAMA_MODELS, LLAMA_CACHE sous models/")


def modeles_retenus() -> list[tuple[str, str, float]]:
    """Lit outils/MODELES.md et rend les lignes dont le statut porte « retenu ».

    Le ledger est la source de vérité : ajouter un modèle au tableau suffit à le
    faire contrôler ici.
    """
    lignes = []
    for ligne in LEDGER.read_text(encoding="utf-8").splitlines():
        if not ligne.startswith("|"):
            continue
        cols = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cols) < 6 or "retenu" not in cols[4].lower():
            continue
        if cols[0].startswith("Mod") or set(cols[0]) <= {"-", ":"}:
            continue  # ligne d'en-tête ou de séparation du tableau
        nom = cols[0].strip("`*").strip()
        chemin = cols[1].strip("`*").strip().strip("`")
        poids = re.search(r"([\d,]+)", cols[2].replace("**", ""))
        go = float(poids.group(1).replace(",", ".")) if poids else 0.0
        lignes.append((nom, chemin, go))
    return lignes


def check_modeles() -> Resultat:
    attendus = modeles_retenus()
    if not attendus:
        return Resultat("modeles", False, "aucune ligne « retenu » lue dans outils/MODELES.md")
    absents = [n for n, chemin, _ in attendus if not (ROOT / chemin).exists()]
    cumul = sum(go for _, _, go in attendus)
    if absents:
        return Resultat("modeles", False, f"{len(absents)} absent(s) : " + ", ".join(absents)[:80])
    return Resultat(
        "modeles", True,
        f"{len(attendus)} modèles retenus présents, {cumul:.2f} Go déclarés",
    )


def check_rhubarb() -> Resultat:
    if not RHUBARB.exists():
        return Resultat("rhubarb", False, f"binaire absent : {RHUBARB.relative_to(ROOT)}")
    if not os.access(RHUBARB, os.X_OK):
        return Resultat("rhubarb", False, "binaire non exécutable (chmod +x)")
    t0 = time.perf_counter()
    try:
        p = subprocess.run([str(RHUBARB), "--version"], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return Resultat("rhubarb", False, "--version ne répond pas")
    secs = time.perf_counter() - t0
    sortie = (p.stdout + p.stderr).strip().splitlines()
    version = next((l for l in sortie if l.strip()), "")
    # Binaire x86_64 : il ne tourne que si Rosetta 2 est installé (étape 5.2).
    ok = p.returncode == 0 and "Rhubarb" in version
    return Resultat("rhubarb", ok, version[:48] if ok else (p.stderr or p.stdout)[-60:], secs)


# --------------------------------------------------------------------------
# Sondes lourdes — exécutées chacune dans un sous-processus
# --------------------------------------------------------------------------
def _ffprobe_duree(chemin: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(chemin)],
        capture_output=True, text=True, timeout=30,
    )
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def probe_llm() -> dict:
    """20 jetons par llama.cpp, poids locaux, sans accès réseau."""
    gguf = ROOT / LLM_GGUF
    if not gguf.exists():
        return {"ok": False, "message": "poids GGUF absents (voir outils/MODELES.md)"}
    cmd = [
        "llama-cli", "-m", str(gguf), "-c", "512", "-n", "20",
        "-st", "--no-warmup", "--temp", "0.7", "--seed", "42", "-rea", "off",
        "-p", "Écris une seule phrase sur le sucre.",
    ]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S - 10)
    secs = time.perf_counter() - t0
    blob = p.stdout + p.stderr
    tg = re.findall(r"Generation:\s*([\d.]+)\s*t/s", blob)
    if p.returncode != 0:
        return {"ok": False, "message": blob.strip()[-90:], "secondes": secs}
    debit = f"{float(tg[-1]):.1f} tok/s" if tg else "débit non lu"
    return {"ok": True, "message": f"20 jetons, {debit}", "secondes": secs}


def probe_tts(lang: str) -> dict:
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    dest = LOGS / f"doctor_tts_{lang}.wav"
    t0 = time.perf_counter()
    # fp16 / MPS / attention « eager » : configuration retenue en 5.1
    # (flash_attention_2 n'existe pas sur Metal).
    modele = Qwen3TTSModel.from_pretrained(
        TTS_MODEL, device_map="mps", dtype=torch.float16, attn_implementation="eager",
    )
    wavs, sr = modele.generate_custom_voice(
        text=PHRASES[lang], language=LANGUES_TTS[lang], speaker=VOIX_TTS,
    )
    sf.write(str(dest), wavs[0], sr)
    secs = time.perf_counter() - t0
    duree = _ffprobe_duree(dest)
    ok = duree > 0.5
    return {
        "ok": ok,
        "message": f"{dest.name}, {duree:.2f} s audio, voix {VOIX_TTS}"
        if ok else f"{dest.name} : durée {duree:.2f} s ≤ 0,5 s",
        "secondes": secs,
    }


def _mots(texte: str) -> str:
    """Minuscules, sans accents ni ponctuation — même normalisation que le banc 5.1."""
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", texte).split())


def compare_transcription(attendu: str, obtenu: str) -> tuple[float, list[str]]:
    """Rend (WER, mots de la référence manqués). Pas de recherche de sous-chaîne."""
    import jiwer

    ref, hyp = _mots(attendu), _mots(obtenu)
    if not ref:
        return 1.0, []
    sortie = jiwer.process_words(ref, hyp or "-")
    mots_ref = ref.split()
    manques = [
        mot
        for bloc in sortie.alignments[0]
        if bloc.type in ("substitute", "delete")
        for mot in mots_ref[bloc.ref_start_idx:bloc.ref_end_idx]
    ]
    return sortie.wer, manques


def probe_asr(lang: str) -> dict:
    """Retranscrit le WAV produit par la sonde TTS et le compare au texte demandé."""
    from parakeet_mlx import from_pretrained

    source = LOGS / f"doctor_tts_{lang}.wav"
    if not source.exists():
        return {"ok": False, "message": f"{source.name} absent (la sonde TTS a échoué)"}
    t0 = time.perf_counter()
    modele = from_pretrained(ASR_MODEL)
    res = modele.transcribe(str(source))
    secs = time.perf_counter() - t0
    attendu = PHRASES[lang]
    taux, manques = compare_transcription(attendu, res.text or "")
    n = len(_mots(attendu).split())
    ok = taux <= ASR_WER_MAX
    if ok:
        message = f"WER {taux:.0%} sur {n} mots (seuil {ASR_WER_MAX:.0%})"
    else:
        message = (
            f"WER {taux:.0%} > {ASR_WER_MAX:.0%} — manqué : "
            + ", ".join(manques[:4]) + f" | rendu : « {(res.text or '').strip()[:40]} »"
        )
    return {"ok": ok, "message": message, "secondes": secs, "wer": round(taux, 3)}


def probe_image() -> dict:
    """512×512, 1 pas de débruitage (FLUX.2-klein est un modèle turbo)."""
    mflux = shutil.which("mflux-generate-flux2")
    if not mflux:
        return {"ok": False, "message": "mflux-generate-flux2 absent (uv tool install mflux)"}
    dest = LOGS / "doctor_image.png"
    dest.unlink(missing_ok=True)
    cmd = [
        mflux, "--model", IMAGE_MODEL, "--prompt", "a single red apple on a white table",
        "--width", "512", "--height", "512", "--steps", "1", "--seed", "42",
        "--low-ram", "--vae-tiling", "--output", str(dest),
    ]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S - 10)
    secs = time.perf_counter() - t0
    if not dest.exists():
        return {"ok": False, "message": (p.stdout + p.stderr).strip()[-90:], "secondes": secs}
    pic = re.findall(r"Peak MLX memory:\s*([\d.]+)\s*GB", p.stdout + p.stderr)
    suffixe = f", pic MLX {pic[-1]} Go" if pic else ""
    return {"ok": True, "message": f"512×512 en 1 pas{suffixe}", "secondes": secs}


def probe_depth() -> dict:
    import torch  # noqa: F401  (impose le chargement de MPS avant transformers)
    from PIL import Image
    from transformers import pipeline

    source = LOGS / "doctor_image.png"
    if not source.exists():
        return {"ok": False, "message": "doctor_image.png absent (la sonde image a échoué)"}
    t0 = time.perf_counter()
    pipe = pipeline("depth-estimation", model=DEPTH_MODEL, device="mps")
    carte = pipe(Image.open(source))["depth"]
    dest = LOGS / "doctor_depth.png"
    carte.save(dest)
    secs = time.perf_counter() - t0
    # Une carte uniforme est un échec silencieux : on exige un vrai relief.
    extremes = carte.convert("L").getextrema()
    ok = dest.exists() and (extremes[1] - extremes[0]) > 32
    return {
        "ok": ok,
        "message": f"{carte.size[0]}×{carte.size[1]}, amplitude {extremes[1] - extremes[0]}/255"
        if ok else f"carte plate (amplitude {extremes[1] - extremes[0]}/255)",
        "secondes": secs,
    }


SONDES = {
    "llm": ("LLM", probe_llm),
    "tts_fr": ("TTS fr", lambda: probe_tts("fr")),
    "tts_en": ("TTS en", lambda: probe_tts("en")),
    "asr_fr": ("ASR fr", lambda: probe_asr("fr")),
    "asr_en": ("ASR en", lambda: probe_asr("en")),
    "image": ("image", probe_image),
    "profondeur": ("profondeur", probe_depth),
}


def lance_sonde(cle: str) -> Resultat:
    """Exécute une sonde dans un sous-processus fils qui meurt à la fin."""
    titre = SONDES[cle][0]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            [sys.executable, "-m", "factory.doctor", "--probe", cle],
            capture_output=True, text=True, timeout=TIMEOUT_S, cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return Resultat(titre, False, f"dépassement du délai de {TIMEOUT_S} s", TIMEOUT_S)
    secs = time.perf_counter() - t0
    for ligne in reversed(p.stdout.splitlines()):
        if ligne.startswith("{"):
            try:
                data = json.loads(ligne)
            except json.JSONDecodeError:
                continue
            alerte = bool(not data["ok"] and cle in SONDES_NON_BLOQUANTES)
            return Resultat(
                titre, data["ok"] or alerte, data["message"],
                data.get("secondes", secs), alerte=alerte,
            )
    erreur = (p.stderr or p.stdout).strip().splitlines()
    return Resultat(titre, False, erreur[-1][:90] if erreur else "sonde muette", secs)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
STATIQUES = [check_python, check_ffmpeg, check_ffprobe, check_disque, check_env,
             check_modeles, check_rhubarb]
# Ordre imposé : chaque ASR consomme le WAV de sa langue, la profondeur consomme l'image.
ORDRE_SONDES = ["llm", "tts_fr", "tts_en", "asr_fr", "asr_en", "image", "profondeur"]


def execute(quick: bool = False) -> list[Resultat]:
    LOGS.mkdir(parents=True, exist_ok=True)
    resultats = []
    for fonction in STATIQUES:
        t0 = time.perf_counter()
        r = fonction()
        if not r.secondes:
            r.secondes = time.perf_counter() - t0
        resultats.append(r)
    for cle in ORDRE_SONDES:
        if quick:
            resultats.append(Resultat(SONDES[cle][0], True, "sauté (--quick)", 0.0, saute=True))
        else:
            resultats.append(lance_sonde(cle))
    return resultats


def main_probe(cle: str) -> int:
    charge_env()
    try:
        data = SONDES[cle][1]()
    except Exception as exc:  # une sonde qui explose est un FAIL, pas une trace
        data = {"ok": False, "message": f"{type(exc).__name__}: {exc}"[:120]}
    print(json.dumps(data, ensure_ascii=False))
    return 0 if data.get("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--probe":
        sys.exit(main_probe(sys.argv[2]))
    print("usage: python -m factory.doctor --probe <nom>", file=sys.stderr)
    sys.exit(2)
