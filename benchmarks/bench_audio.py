#!/usr/bin/env python3
"""Banc de mesure des briques texte et audio — étape 5.1.

Un sous-processus par outil (règle CLAUDE.md § 4 : un seul modèle résident).
Appelé par bench_audio.sh, qui l'enveloppe dans /usr/bin/time -l pour le pic
memoire. Chaque mesure est ajoutée à benchmarks/results_audio.jsonl.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "benchmarks" / "samples" / "audio"
RESULTS = ROOT / "benchmarks" / "results_audio.jsonl"

LLM_REPO = "bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M"
LLM_FALLBACK = "bartowski/google_gemma-4-E4B-it-GGUF:Q4_K_M"
ASR_MODEL = "mlx-community/parakeet-tdt-0.6b-v3"
TTS_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

# Sujet porteur n°1 de la niche science_pop (registre/REFERENTIEL.json)
SUJET = "What Happens Every Day When You Quit Sugar For 30 Days"
PROMPTS = {
    "fr": (
        f"Écris un script de 600 mots pour une vidéo YouTube sur « {SUJET} », "
        "en français, avec un hook de 2 phrases."
    ),
    "en": (
        f"Write a 600-word script for a YouTube video about « {SUJET} », "
        "in English, with a 2-sentence hook."
    ),
}


def record(entry):
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with RESULTS.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("MESURE " + json.dumps(entry, ensure_ascii=False), flush=True)


# --------------------------------------------------------------------------
# WER
# --------------------------------------------------------------------------
def normalise(text):
    """Minuscules, sans ponctuation ni accents, espaces normalisés."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return text.split()


# Les ASR rendent les nombres en chiffres (« 30 jours », « 16 heures ») là où le texte
# source les écrit en toutes lettres (« trente jours », « seize heures »). Ce n'est pas
# une erreur de reconnaissance : c'est une convention d'écriture. Sur un paragraphe de
# 126 mots qui en contient 8, cela suffit à créer un WER de 6 % à partir de rien, et
# donc à déclencher la « alerte WER > 8 % » sur une voix parfaitement intelligible.
# On mesure donc les deux : le WER brut, et le WER hors nombres.
NOMBRES = set("""
zero un une deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze
quinze seize dix-sept dix-huit dix-neuf vingt trente quarante cinquante soixante cent
mille premier premiere deuxieme troisieme quatrieme cinquieme quinzieme trentieme
zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen
fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty hundred
thousand first second third fourth fifteenth thirtieth
cero uno una dos tres cuatro cinco seis siete ocho nueve diez quince veinte treinta
cuarenta cincuenta sesenta cien mil primero segundo tercero decimoquinto
due tre quattro cinque sei sette otto nove dieci quindici venti trenta quaranta
cinquanta sessanta cento mille primo secondo terzo quindicesimo trentesimo
""".split())


def sans_nombres(mots):
    """Retire les chiffres et les nombres écrits en toutes lettres."""
    return [m for m in mots if not any(c.isdigit() for c in m) and m not in NOMBRES]


def wer(reference, hypothesis, ignorer_nombres=False):
    """Distance de Levenshtein sur les mots / nombre de mots de référence."""
    ref, hyp = normalise(reference), normalise(hypothesis)
    if ignorer_nombres:
        ref, hyp = sans_nombres(ref), sans_nombres(hyp)
    if not ref:
        return None, 0, 0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref), len(ref), len(hyp)


# --------------------------------------------------------------------------
# LLM (llama.cpp)
# --------------------------------------------------------------------------
def run_llama(repo, prompt, n_predict, ctx=8192):
    """Lance llama-cli et renvoie (texte, temps, tok/s prompt, tok/s génération)."""
    cmd = [
        "llama-cli", "-hf", repo,
        "-c", str(ctx), "-n", str(n_predict),
        "-st", "--no-warmup", "--temp", "0.7", "--seed", "42",
        "-rea", "off",  # pas de chaîne de pensée : on mesure l'écriture, pas le raisonnement
        "-p", prompt,
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    elapsed = time.perf_counter() - t0
    blob = proc.stdout + proc.stderr
    # Ce build affiche « [ Prompt: 24.3 t/s | Generation: 14.5 t/s ] », rafraîchi en
    # continu par retour chariot : le débit final est la DERNIÈRE occurrence, pas la
    # première (la première vaut ~0,8 t/s, mesurée sur le tout premier token).
    pp_all = re.findall(r"Prompt:\s*([\d.]+)\s*t/s", blob)
    tg_all = re.findall(r"Generation:\s*([\d.]+)\s*t/s", blob)
    pp = pp_all[-1] if pp_all else None
    tg = tg_all[-1] if tg_all else None
    ntok = re.search(r"\n\s*eval time =.*?/\s*(\d+) runs", blob)
    texte = re.sub(r"\[ Prompt:.*?\]", "", proc.stdout, flags=re.S)
    return {
        "texte": texte,
        "temps_s": round(elapsed, 2),
        "tok_s_prompt": float(pp) if pp else None,
        "tok_s_generation": float(tg) if tg else None,
        "tokens_generes": int(ntok.group(1)) if ntok else None,
        "returncode": proc.returncode,
        "erreur": proc.stderr[-400:] if proc.returncode != 0 else None,
    }


def stage_llm(args):
    repo = LLM_FALLBACK if args.repli else LLM_REPO
    nom = "Gemma-4-E4B Q4_K_M" if args.repli else "Qwen3.5-9B Q4_K_M"
    for lang in ("fr", "en"):
        r = run_llama(repo, PROMPTS[lang], n_predict=1100)
        texte = r.pop("texte")
        (SAMPLES.parent / f"script_{'repli_' if args.repli else ''}{lang}.txt").write_text(
            texte, encoding="utf-8"
        )
        r["mots_generes"] = len(texte.split())
        record({"brique": "LLM", "outil": nom, "modele": repo, "langue": lang, **r})


def extraire_reponse(sortie):
    """Isole la réponse du modèle dans la sortie de llama-cli.

    llama-cli imprime une bannière ASCII, la liste de ses commandes, puis réaffiche
    le prompt (préfixé « > ») avec le texte source, et termine par « Exiting... ».
    La réponse d'un tour unique est la dernière ligne non vide avant cette fin.
    """
    lignes = [l.strip() for l in sortie.splitlines()]
    lignes = [l for l in lignes if l and not l.startswith("Exiting")]
    reponse = lignes[-1] if lignes else ""
    return re.sub(r"^(Traduction|Translation|Traducción|Traduzione)\s*:\s*", "", reponse).strip()


def stage_translate(args):
    """Traduit le texte source FR en EN, ES, IT avec le LLM principal."""
    src = (SAMPLES / "texte_fr.txt").read_text(encoding="utf-8").strip()
    cibles = {"en": "anglais", "es": "espagnol", "it": "italien"}
    for code, nom in cibles.items():
        prompt = (
            f"Traduis ce paragraphe en {nom}. Réponds uniquement par la traduction, "
            f"sans commentaire, sans guillemets, sans titre.\n\n{src}"
        )
        r = run_llama(LLM_REPO, prompt, n_predict=400)
        txt = extraire_reponse(r["texte"])
        (SAMPLES / f"texte_{code}.txt").write_text(txt + "\n", encoding="utf-8")
        print(f"TRADUIT {code} : {len(txt.split())} mots", flush=True)


# --------------------------------------------------------------------------
# TTS
# --------------------------------------------------------------------------
# Aucun locuteur natif FR/ES/IT parmi les 9 préréglés : tout passe en cross-lingual.
# Deux timbres par langue, un masculin et un féminin, pour tester l'exigence « ≥ 2 voix ».
LANGUES_TTS = {"fr": "French", "en": "English", "es": "Spanish", "it": "Italian"}
VOIX_TTS = ["Ryan", "Serena"]


def mesure_niveau(wav):
    """Contrôle technique du WAV : la session n'entend rien, mais elle peut vérifier
    que le fichier contient bien de la parole continue et non du silence.
    Niveau intégré (LUFS), crête réelle (dBFS), nombre de silences de plus de 1,5 s."""
    def ff(filtre, motif):
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav),
             "-af", filtre, "-f", "null", "-"],
            capture_output=True, text=True,
        )
        return p.stderr
    # ebur128 imprime une ligne de niveau par trame puis le résumé final :
    # la valeur intégrée est la DERNIÈRE occurrence, pas la première.
    sortie = ff("ebur128=peak=true", None)
    lufs = re.findall(r"I:\s*(-?[\d.]+) LUFS", sortie)
    crete = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", sortie)
    silences = ff("silencedetect=n=-45dB:d=1.5", None).count("silence_start")
    return {
        "lufs": float(lufs[-1]) if lufs else None,
        "crete_dbfs": float(crete[-1]) if crete else None,
        "silences_longs": silences,
    }


def stage_tts(args):
    """Synthèse d'un texte dans une langue avec une voix (API officielle qwen-tts)."""
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    lang, voix = args.lang, args.voix
    texte = (SAMPLES / f"texte_{lang}.txt").read_text(encoding="utf-8").strip()
    # Configuration retenue après comparaison des trois disponibles sur cette
    # machine (sonde sur une phrase, voir RESULTATS.md § 1) :
    #   fp16 MPS 4,73 · bf16 MPS 5,05 · fp32 CPU 5,94 (facteur temps réel)
    # flash_attention_2 n'existe pas sur Metal : attention « eager » obligatoire.
    t_charge = time.perf_counter()
    modele = Qwen3TTSModel.from_pretrained(
        TTS_MODEL, device_map="mps", dtype=torch.float16,
        attn_implementation="eager",
    )
    charge_s = time.perf_counter() - t_charge

    t0 = time.perf_counter()
    wavs, sr = modele.generate_custom_voice(
        text=texte, language=LANGUES_TTS[lang], speaker=voix
    )
    calcul = time.perf_counter() - t0

    wav = SAMPLES / f"qwen3tts_{lang}_{voix}.wav"
    sf.write(str(wav), wavs[0], sr)
    duree = len(wavs[0]) / sr
    niveau = mesure_niveau(wav)
    record({
        "brique": "TTS", "outil": "Qwen3-TTS-12Hz-1.7B", "modele": TTS_MODEL,
        "langue": lang, "voix": voix, "fichier": wav.name, "config": "fp16/mps",
        "temps_chargement_s": round(charge_s, 2),
        "temps_s": round(calcul, 2), "duree_audio_s": round(duree, 2),
        "rtf": round(calcul / duree, 3) if duree else None,
        "mots_texte": len(texte.split()),
        "mots_par_minute": round(len(texte.split()) / (duree / 60), 1) if duree else None,
        **niveau,
    })


# --------------------------------------------------------------------------
# ASR
# --------------------------------------------------------------------------
def stage_asr(args):
    from parakeet_mlx import from_pretrained

    modele = from_pretrained(ASR_MODEL)
    for wav in sorted(SAMPLES.glob("*.wav")):
        lang = wav.stem.split("_")[1]
        ref_file = SAMPLES / f"texte_{lang}.txt"
        if not ref_file.exists():
            continue
        t0 = time.perf_counter()
        res = modele.transcribe(str(wav))
        calcul = time.perf_counter() - t0
        jetons = [t for s in res.sentences for t in s.tokens]
        # parakeet rend des sous-mots : un nouveau mot commence par une espace.
        mots = [t for t in jetons if t.text.startswith(" ")] or jetons
        horodatage_mot = bool(jetons) and all(
            hasattr(t, "start") and hasattr(t, "end") for t in jetons[:5]
        )
        # Cohérence : les horodatages doivent être croissants et tenir dans l'audio.
        croissants = all(
            jetons[i].start <= jetons[i + 1].start for i in range(len(jetons) - 1)
        )
        texte = res.text
        (SAMPLES / f"asr_{wav.stem}.txt").write_text(texte, encoding="utf-8")
        ref = ref_file.read_text(encoding="utf-8")
        taux, n_ref, n_hyp = wer(ref, texte)
        net, _, _ = wer(ref, texte, ignorer_nombres=True)
        duree = sum(s.end - s.start for s in res.sentences) or None
        record({
            "brique": "ASR", "outil": "parakeet-tdt-0.6b-v3", "modele": ASR_MODEL,
            "fichier": wav.name, "langue": lang,
            "temps_s": round(calcul, 2),
            "rtf": round(calcul / duree, 3) if duree else None,
            "horodatage_mot": horodatage_mot, "n_mots_horodates": len(mots),
            "horodatages_croissants": croissants,
            "wer": round(taux * 100, 2) if taux is not None else None,
            "wer_hors_nombres": round(net * 100, 2) if net is not None else None,
            "mots_reference": n_ref, "mots_transcrits": n_hyp,
            "couverture": round(n_hyp / n_ref, 3) if n_ref else None,
        })


def stage_asr_repli(args):
    import mlx_whisper

    repo = "mlx-community/whisper-large-v3-turbo"
    for wav in sorted(SAMPLES.glob("*.wav")):
        lang = wav.stem.split("_")[1]
        ref_file = SAMPLES / f"texte_{lang}.txt"
        if not ref_file.exists():
            continue
        t0 = time.perf_counter()
        res = mlx_whisper.transcribe(
            str(wav), path_or_hf_repo=repo, word_timestamps=True, language=lang
        )
        calcul = time.perf_counter() - t0
        mots = [w for s in res["segments"] for w in s.get("words", [])]
        duree = res["segments"][-1]["end"] if res["segments"] else None
        (SAMPLES / f"asrw_{wav.stem}.txt").write_text(res["text"], encoding="utf-8")
        ref = ref_file.read_text(encoding="utf-8")
        taux, n_ref, n_hyp = wer(ref, res["text"])
        net, _, _ = wer(ref, res["text"], ignorer_nombres=True)
        record({
            "brique": "ASR", "outil": "mlx-whisper large-v3-turbo", "modele": repo,
            "fichier": wav.name, "langue": lang,
            "temps_s": round(calcul, 2),
            "rtf": round(calcul / duree, 3) if duree else None,
            "horodatage_mot": bool(mots), "n_mots_horodates": len(mots),
            "wer": round(taux * 100, 2) if taux is not None else None,
            "wer_hors_nombres": round(net * 100, 2) if net is not None else None,
            "mots_reference": n_ref, "mots_transcrits": n_hyp,
            "couverture": round(n_hyp / n_ref, 3) if n_ref else None,
        })


STAGES = {
    "llm": stage_llm, "translate": stage_translate, "tts": stage_tts,
    "asr": stage_asr, "asr-repli": stage_asr_repli,
}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=sorted(STAGES))
    p.add_argument("--lang", default="fr")
    p.add_argument("--voix", default="")
    p.add_argument("--repli", action="store_true")
    a = p.parse_args()
    os.environ.setdefault("HF_HOME", str(ROOT / "models" / "hf"))
    os.environ.setdefault("LLAMA_CACHE", str(ROOT / "models" / "llamacpp"))
    sys.exit(STAGES[a.stage](a) or 0)
