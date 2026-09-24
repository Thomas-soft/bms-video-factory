"""Brique ASR — transcription horodatée au mot, dans un sous-processus qui se termine.

Comme `factory.tts`, ce module n'est jamais importé par l'étape appelante : il se lance par
`python -m factory.asr <travail.json>` et meurt en rendant la mémoire (`CLAUDE.md` § 4).

Deux moteurs, et le second n'est pas un luxe (`RESULTATS.md` § 1.3, étape 7) :

* **parakeet-tdt-0.6b-v3** — dix fois plus rapide (facteur temps réel 0,037), horodatage au mot
  **natif**, 0,84 Go en mémoire. Mais il **tronque** deux fichiers sur huit et **dérive vers
  l'anglais** sur les énoncés français de 5 à 10 s.
* **whisper large-v3-turbo** — facteur 0,388, horodatage reconstruit par DTW, 1,92 Go. Il tient
  là où parakeet décroche, et il hallucine parfois en fin de fichier.

C'est l'appelant qui arbitre, sur la couverture *et* le WER mesurés contre le texte du script.
Ici on ne fait que transcrire et rendre des mots horodatés, au même format quel que soit le moteur.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path

REPO_PARAKEET = "mlx-community/parakeet-tdt-0.6b-v3"
REPO_WHISPER = "mlx-community/whisper-large-v3-turbo"


# --------------------------------------------------------------------------------------
# Mesure — normalisation et WER
#
# Reprise à l'identique de la méthode de l'étape 5.1 (`benchmarks/bench_audio.py`) pour que
# les chiffres de production restent comparables à ceux du banc.
# --------------------------------------------------------------------------------------

#: Nombres écrits en toutes lettres, quatre langues. Les ASR rendent « 30 jours » là où le
#: script écrit « trente jours » : ce n'est pas une erreur de reconnaissance mais une
#: convention d'écriture, et elle suffit à créer 5 à 6 % de WER sur une voix parfaite.
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

_RE_NON_MOT = re.compile(r"[^a-z0-9' ]+")


def normaliser(texte: str) -> list[str]:
    """Minuscules, sans ponctuation ni accents, espaces normalisés."""
    texte = texte.lower()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return _RE_NON_MOT.sub(" ", texte).split()


def sans_nombres(mots: list[str]) -> list[str]:
    """Retire les chiffres et les nombres écrits en toutes lettres."""
    return [m for m in mots if not any(c.isdigit() for c in m) and m not in NOMBRES]


def wer(reference: str, hypothese: str, ignorer_nombres: bool = False) -> float | None:
    """Distance de Levenshtein sur les mots, rapportée au nombre de mots de référence."""
    ref, hyp = normaliser(reference), normaliser(hypothese)
    if ignorer_nombres:
        ref, hyp = sans_nombres(ref), sans_nombres(hyp)
    if not ref:
        return None
    precedent = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        courant = [i]
        for j, h in enumerate(hyp, 1):
            courant.append(min(precedent[j] + 1, courant[j - 1] + 1, precedent[j - 1] + (r != h)))
        precedent = courant
    return precedent[-1] / len(ref)



def _mots_parakeet(resultat: object) -> list[dict]:
    """Recompose des mots à partir des sous-mots de parakeet.

    Le modèle rend des jetons de sous-mot ; **un nouveau mot commence par une espace**. Le mot
    hérite du début du premier jeton et de la fin du dernier.
    """
    jetons = [t for phrase in resultat.sentences for t in phrase.tokens]  # type: ignore[attr-defined]
    mots: list[dict] = []
    for jeton in jetons:
        texte = jeton.text
        if not texte.strip():
            continue
        debut_de_mot = texte.startswith(" ") or not mots
        if debut_de_mot:
            mots.append({"w": texte.strip(), "start_s": float(jeton.start),
                         "end_s": float(jeton.end), "conf": None})
        else:
            mots[-1]["w"] += texte.strip()
            mots[-1]["end_s"] = float(jeton.end)
    return mots


def _mots_whisper(resultat: dict) -> list[dict]:
    """Aplati les mots horodatés de whisper. `probability` est la seule confiance disponible."""
    mots: list[dict] = []
    for segment in resultat.get("segments", []):
        for mot in segment.get("words", []):
            texte = str(mot.get("word", "")).strip()
            if not texte:
                continue
            mots.append({
                "w": texte, "start_s": float(mot["start"]), "end_s": float(mot["end"]),
                "conf": round(float(mot["probability"]), 4) if mot.get("probability") else None,
            })
    return mots


def transcrire(travail: dict) -> dict:
    """Transcrit un WAV avec le moteur demandé et rend un compte rendu au format commun."""
    moteur = travail["engine"]
    wav = str(Path(travail["wav"]))
    t0 = time.perf_counter()

    if moteur == "parakeet":
        from parakeet_mlx import from_pretrained

        modele = from_pretrained(travail.get("model", REPO_PARAKEET))
        options: dict[str, float] = {}
        if travail.get("chunk_duration"):
            # Le découpage récupère les fichiers tronqués et en casse d'autres : six réglages
            # mesurés à l'étape 5.1, aucun bon partout. Il n'est donc employé qu'en rattrapage.
            options["chunk_duration"] = float(travail["chunk_duration"])
            options["overlap_duration"] = float(travail.get("overlap_duration", 15))
        resultat = modele.transcribe(wav, **options)
        mots = _mots_parakeet(resultat)
        texte = resultat.text
    elif moteur == "whisper":
        import mlx_whisper

        resultat = mlx_whisper.transcribe(
            wav, path_or_hf_repo=travail.get("model", REPO_WHISPER),
            word_timestamps=True, language=travail.get("lang"),
        )
        mots = _mots_whisper(resultat)
        texte = resultat["text"]
    else:
        raise ValueError(f"moteur ASR inconnu : {moteur}")

    return {
        "engine": moteur, "text": texte, "words": mots,
        "secondes": round(time.perf_counter() - t0, 2),
        "chunk_duration": travail.get("chunk_duration"),
    }


def main(argv: list[str]) -> int:
    """Lit un fichier de travail, transcrit, écrit le résultat en JSON."""
    if len(argv) != 2:
        print("usage : python -m factory.asr <travail.json>", file=sys.stderr)
        return 2
    travail = json.loads(Path(argv[1]).read_text(encoding="utf-8"))

    from factory.doctor import charge_env

    charge_env()
    resultat = transcrire(travail)
    Path(travail["out"]).write_text(
        json.dumps(resultat, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({
        "evenement": "asr", "engine": resultat["engine"], "mots": len(resultat["words"]),
        "temps_s": resultat["secondes"], "chunk_duration": resultat["chunk_duration"],
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
