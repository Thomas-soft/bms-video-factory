"""Étape `subtitles` — alignement souple, `words.json`, `subtitles.srt`, `subtitles.ass`.

**Le texte du script fait foi ; l'ASR ne fournit que le timing.** Un mot mal entendu porte le mot
du script et une confiance basse, jamais le mot faux — c'est le contrat de `words.json`.

Chaîne de traitement :

1. Transcription de `voice/voice.wav` par le moteur principal de la langue (parakeet), dans un
   sous-processus qui meurt ensuite.
2. **Alignement souple** entre les mots du script et ceux de l'ASR (`difflib` sur les formes
   normalisées, appariement des blocs remplacés par similarité) ; les mots sans correspondance
   héritent d'une **interpolation** au prorata de leur longueur entre les deux ancres qui les
   encadrent.
3. **Couverture et WER**, les deux (étape 7 : à 2 s la couverture vaut 100-120 % avec tous les
   mots faux). Sous le seuil, rattrapage parakeet découpé puis bascule sur whisper, et l'on garde
   la meilleure des transcriptions.
4. Groupes de 1 à 5 mots → `.srt` (distribution) et `.ass` (incrustation, style lu dans la charte).
"""

from __future__ import annotations

import difflib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from factory import asr
from factory.core import config as config_module
from factory.core import db, runs
from factory.core.models import (
    MesureSegmentAsr,
    Script,
    Timings,
    Words,
    WordTiming,
)
from factory.core.paths import RunPaths, racine_projet

#: Un groupe de sous-titres porte 1 à 5 mots ; au-delà, le lecteur ne suit plus le rythme.
MOTS_MIN, MOTS_MAX = 1, 5
#: Bornes de durée d'un groupe, en secondes.
DUREE_MIN_S, DUREE_MAX_S = 0.4, 3.0
#: Un silence plus long que cela coupe le groupe : un sous-titre ne traverse pas une respiration.
COUPURE_SILENCE_S = 0.6
#: Plafond absolu de caractères par ligne, quel que soit ce que dit la charte.
PLAFOND_CARACTERES = 42
#: Seuil de couverture sous lequel on rattrape (contrat `INTERFACES.md` → words.json).
COUVERTURE_MIN = 0.98
#: Similarité minimale pour apparier deux mots d'un bloc remplacé.
SIMILARITE_MIN = 0.6
#: Plafond de temps du sous-processus ASR (`INTERFACES.md` § timeouts).
TIMEOUT_ASR_S = 600.0


@dataclass
class MotScript:
    """Un mot du script, avec le segment dont il vient."""

    mot: str
    segment: str


@dataclass
class Tentative:
    """Une transcription et ce qu'elle vaut contre le texte du script."""

    moteur: str
    decoupage: float | None
    mots_asr: list[dict]
    texte: str
    secondes: float
    couverture: float
    wer: float
    wer_hors_nombres: float
    horodatages: list[tuple[float, float]]
    apparies: dict[int, int]
    cache: bool = False

    @property
    def ancres(self) -> int:
        """Nombre de mots du script réellement ancrés sur un mot de l'ASR."""
        return len(self.apparies)

    @property
    def etiquette(self) -> str:
        """Nom lisible de la tentative, pour le journal."""
        return self.moteur + (f" (découpage {self.decoupage:.0f} s)" if self.decoupage else "")


@dataclass
class ResultatSousTitres:
    """Ce que l'étape rend à la CLI."""

    words: Words
    cues: int
    ligne_la_plus_longue: int
    tentatives: list[Tentative]
    retenue: Tentative
    secondes: float
    secondes_asr: float
    trous_max_s: float
    alertes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Alignement
# --------------------------------------------------------------------------------------
def _forme(mot: str) -> str:
    """Forme normalisée d'un mot, pour la comparaison seule. Jamais écrite dans les sorties."""
    formes = asr.normaliser(mot)
    return formes[0] if formes else ""


def aligner(mots_script: list[MotScript], mots_asr: list[dict]) -> dict[int, int]:
    """Apparie les mots du script aux mots de l'ASR. Rend {index script → index ASR}.

    Les blocs `equal` s'apparient un pour un. Dans un bloc `replace`, on apparie par position
    **à condition que les deux mots se ressemblent** (≥ `SIMILARITE_MIN`) : sans ce garde-fou,
    un ASR qui invente trois mots au milieu d'une phrase donnerait trois horodatages faux, ce
    qui est pire qu'une interpolation.
    """
    reference = [_forme(m.mot) for m in mots_script]
    hypothese = [_forme(m["w"]) for m in mots_asr]
    matcher = difflib.SequenceMatcher(None, reference, hypothese, autojunk=False)
    apparies: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for decalage in range(i2 - i1):
                apparies[i1 + decalage] = j1 + decalage
        elif tag == "replace":
            for decalage in range(min(i2 - i1, j2 - j1)):
                gauche, droite = reference[i1 + decalage], hypothese[j1 + decalage]
                if not gauche or not droite:
                    continue
                if difflib.SequenceMatcher(None, gauche, droite).ratio() >= SIMILARITE_MIN:
                    apparies[i1 + decalage] = j1 + decalage
    return apparies


def horodater(mots_script: list[MotScript], mots_asr: list[dict], apparies: dict[int, int],
              duree_totale: float) -> list[tuple[float, float]]:
    """Donne un (début, fin) à chaque mot du script ; interpole ceux qui n'ont pas d'ancre.

    L'interpolation répartit le temps disponible **au prorata du nombre de caractères** : un mot
    long occupe plus de place qu'un article. Les horodatages rendus sont croissants et contenus
    dans la durée de la piste — deux invariants que `WordTiming` refuse de violer.
    """
    total = len(mots_script)
    temps: list[tuple[float, float] | None] = [None] * total
    for index_script, index_asr in apparies.items():
        mot = mots_asr[index_asr]
        temps[index_script] = (float(mot["start_s"]), float(mot["end_s"]))

    ancres = sorted(apparies)
    index = 0
    while index < total:
        if temps[index] is not None:
            index += 1
            continue
        fin_du_trou = index
        while fin_du_trou < total and temps[fin_du_trou] is None:
            fin_du_trou += 1
        precedent = next((a for a in reversed(ancres) if a < index), None)
        suivant = next((a for a in ancres if a >= fin_du_trou), None)
        debut = temps[precedent][1] if precedent is not None else 0.0  # type: ignore[index]
        fin = temps[suivant][0] if suivant is not None else duree_totale  # type: ignore[index]
        if fin <= debut:
            fin = debut + 0.01 * (fin_du_trou - index)
        poids = [len(mots_script[i].mot) + 1 for i in range(index, fin_du_trou)]
        somme = float(sum(poids)) or 1.0
        curseur = debut
        for rang, i in enumerate(range(index, fin_du_trou)):
            part = (fin - debut) * poids[rang] / somme
            temps[i] = (curseur, curseur + part)
            curseur += part
        index = fin_du_trou

    # Invariants : croissance et bornes. Un ASR peut rendre deux mots au même instant.
    resultat: list[tuple[float, float]] = []
    precedent_debut = 0.0
    for debut, fin in temps:  # type: ignore[misc]
        debut = max(0.0, min(float(debut), duree_totale))
        fin = max(debut, min(float(fin), duree_totale))
        debut = max(debut, precedent_debut)
        fin = max(fin, debut)
        resultat.append((round(debut, 3), round(fin, 3)))
        precedent_debut = debut
    return resultat


# --------------------------------------------------------------------------------------
# Découpage en groupes
# --------------------------------------------------------------------------------------
def _replier(mots: list[str], largeur: int, lignes_max: int) -> list[str] | None:
    """Replie une suite de mots en lignes ; None si elle ne tient pas dans le cadre."""
    lignes: list[str] = []
    courante = ""
    for mot in mots:
        candidate = f"{courante} {mot}".strip()
        if len(candidate) <= largeur:
            courante = candidate
            continue
        if courante:
            lignes.append(courante)
        if len(mot) > largeur or len(lignes) >= lignes_max:
            return None
        courante = mot
    if courante:
        lignes.append(courante)
    return lignes if 0 < len(lignes) <= lignes_max else None


@dataclass
class Cue:
    """Un sous-titre : les mots qu'il porte, sa fenêtre et son repli en lignes."""

    indices: list[int]
    debut_s: float
    fin_s: float
    lignes: list[str]

    @property
    def texte(self) -> str:
        """Texte replié, une ligne par élément."""
        return "\n".join(self.lignes)


def grouper(mots: list[str], horodatages: list[tuple[float, float]], largeur: int,
            lignes_max: int) -> list[Cue]:
    """Découpe la suite de mots en groupes de 1 à 5 mots respectant cadre et durées."""
    cues: list[Cue] = []
    courant: list[int] = []

    def fermer() -> None:
        if not courant:
            return
        lignes = _replier([mots[i] for i in courant], largeur, lignes_max)
        if lignes is None:  # un mot plus long que la ligne : on le laisse déborder seul
            lignes = [" ".join(mots[i] for i in courant)]
        cues.append(Cue(indices=list(courant), debut_s=horodatages[courant[0]][0],
                        fin_s=horodatages[courant[-1]][1], lignes=lignes))
        courant.clear()

    for index, _ in enumerate(mots):
        if courant:
            silence = horodatages[index][0] - horodatages[courant[-1]][1]
            candidat = [*courant, index]
            duree = horodatages[index][1] - horodatages[courant[0]][0]
            tient = _replier([mots[i] for i in candidat], largeur, lignes_max) is not None
            if (len(courant) >= MOTS_MAX or silence > COUPURE_SILENCE_S
                    or duree > DUREE_MAX_S or not tient):
                fermer()
        courant.append(index)
    fermer()

    return _borner(cues, mots, largeur, lignes_max)


def _borner(cues: list[Cue], mots: list[str], largeur: int, lignes_max: int) -> list[Cue]:
    """Ramène chaque groupe dans [0,4 s ; 3 s] sans jamais mentir sur le temps.

    Trop court : on absorbe le groupe dans le précédent quand le cadre l'autorise — c'est la
    seule correction qui ne fabrique pas de temps —, sinon on étire la fin jusqu'au groupe
    suivant, jamais au-delà. Trop long : un mot seul peut occuper plus de trois secondes après
    interpolation ; on coupe l'affichage, pas le mot.
    """
    fusionnes: list[Cue] = []
    for cue in cues:
        precedent = fusionnes[-1] if fusionnes else None
        trop_court = cue.fin_s - cue.debut_s < DUREE_MIN_S
        if trop_court and precedent is not None:
            candidat = precedent.indices + cue.indices
            lignes = _replier([mots[i] for i in candidat], largeur, lignes_max)
            if len(candidat) <= MOTS_MAX and lignes is not None \
                    and cue.fin_s - precedent.debut_s <= DUREE_MAX_S:
                precedent.indices = candidat
                precedent.fin_s = cue.fin_s
                precedent.lignes = lignes
                continue
        fusionnes.append(cue)

    for rang, cue in enumerate(fusionnes):
        suivant = fusionnes[rang + 1].debut_s if rang + 1 < len(fusionnes) else None
        duree = cue.fin_s - cue.debut_s
        if duree < DUREE_MIN_S:
            plafond = suivant if suivant is not None else cue.debut_s + DUREE_MIN_S
            cue.fin_s = max(cue.fin_s, min(cue.debut_s + DUREE_MIN_S, plafond))
        elif duree > DUREE_MAX_S:
            cue.fin_s = cue.debut_s + DUREE_MAX_S
        # Deux sous-titres à l'écran en même temps, c'est une ligne qui en cache une autre :
        # les ASR rendent des mots dont la fin déborde sur le début du suivant.
        if suivant is not None:
            cue.fin_s = max(cue.debut_s, min(cue.fin_s, suivant))
    return fusionnes


# --------------------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------------------
def _horloge_srt(secondes: float) -> str:
    heures, reste = divmod(max(0.0, secondes), 3600)
    minutes, secondes_restantes = divmod(reste, 60)
    entier = int(secondes_restantes)
    millisecondes = int(round((secondes_restantes - entier) * 1000))
    if millisecondes == 1000:
        entier, millisecondes = entier + 1, 0
    return f"{int(heures):02d}:{int(minutes):02d}:{entier:02d},{millisecondes:03d}"


def _horloge_ass(secondes: float) -> str:
    heures, reste = divmod(max(0.0, secondes), 3600)
    minutes, secondes_restantes = divmod(reste, 60)
    entier = int(secondes_restantes)
    centiemes = int(round((secondes_restantes - entier) * 100))
    if centiemes == 100:
        entier, centiemes = entier + 1, 0
    return f"{int(heures)}:{int(minutes):02d}:{entier:02d}.{centiemes:02d}"


def ecrire_srt(cues: list[Cue], chemin: Path) -> None:
    """Piste de distribution : c'est elle que `captions.insert` enverra (400 unités de quota)."""
    blocs = [
        f"{rang}\n{_horloge_srt(cue.debut_s)} --> {_horloge_srt(cue.fin_s)}\n{cue.texte}\n"
        for rang, cue in enumerate(cues, 1)
    ]
    chemin.write_text("\n".join(blocs), encoding="utf-8")


def _couleur_ass(hexa: str) -> str:
    """`#rrggbb` → `&H00BBGGRR&` : l'ASS écrit les octets à l'envers, alpha en tête."""
    valeur = hexa.lstrip("#")
    if len(valeur) == 3:
        valeur = "".join(c * 2 for c in valeur)
    rouge, vert, bleu = valeur[0:2], valeur[2:4], valeur[4:6]
    return f"&H00{bleu}{vert}{rouge}".upper()


#: `align` de la charte → alignement ASS (numérotation du pavé numérique).
ALIGNEMENTS = {"bottom_left": 1, "bottom_center": 2, "middle_center": 5}


def ecrire_ass(cues: list[Cue], mots: list[str], horodatages: list[tuple[float, float]],
               chemin: Path, charte: object, largeur_video: int = 1920,
               hauteur_video: int = 1080) -> None:
    """Piste d'incrustation. **Tout le style vient de la charte**, rien n'est écrit en dur.

    Quand la charte demande le karaoké, le mot dit passe de `palette.text` à `palette.highlight`
    au moment où il est prononcé : en ASS, `\\k` fait basculer chaque syllabe de la couleur
    secondaire vers la couleur primaire — la primaire est donc la couleur de surlignage.
    """
    style = charte.subtitles  # type: ignore[attr-defined]
    palette = charte.palette  # type: ignore[attr-defined]
    police = style.font or charte.fonts.title  # type: ignore[attr-defined]
    graisse = -1 if (style.weight or "").lower() not in {"regular", "normal", "light"} else 0
    contour = max(2, round(style.size_px / 16))
    primaire = _couleur_ass(palette.highlight if style.karaoke else palette.text)
    secondaire = _couleur_ass(palette.text)

    entete = [
        "[Script Info]",
        "; Écrit par `factory subtitles` — style lu dans la charte de la chaîne, jamais en dur.",
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {largeur_video}",
        f"PlayResY: {hauteur_video}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: BMS,{police},{style.size_px},{primaire},{secondaire},"
        f"{_couleur_ass(palette.text_outline)},&H64000000,{graisse},0,0,0,100,100,0,0,1,"
        f"{contour},0,{ALIGNEMENTS[style.align]},80,80,{style.margin_v_px},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    evenements = []
    for cue in cues:
        # Les séparateurs viennent du repli déjà calculé pour le SRT : on compte les mots de
        # chaque ligne plutôt que de rechercher un texte, qui peut apparaître deux fois.
        coupures = set()
        rang_courant = 0
        for ligne in cue.lignes[:-1]:
            rang_courant += len(ligne.split())
            coupures.add(rang_courant - 1)
        separateurs = ["\\N" if rang in coupures else " " for rang in range(len(cue.indices))]
        separateurs[-1] = ""

        if style.karaoke:
            morceaux = []
            curseur = cue.debut_s
            for rang, index in enumerate(cue.indices):
                # Le blanc qui précède le mot lui est rattaché, et la fin est **celle du
                # sous-titre** : la somme des \k doit couvrir exactement la fenêtre affichée,
                # sinon le surlignage continue après que la ligne a disparu.
                fin = min(horodatages[index][1], cue.fin_s)
                if rang == len(cue.indices) - 1:
                    fin = cue.fin_s
                duree_cs = max(1, round((fin - curseur) * 100))
                morceaux.append(f"{{\\k{duree_cs}}}{mots[index]}{separateurs[rang]}")
                curseur = max(curseur, fin)
            texte = "".join(morceaux)
        else:
            texte = "".join(f"{mots[index]}{separateurs[rang]}"
                            for rang, index in enumerate(cue.indices))
        evenements.append(
            f"Dialogue: 0,{_horloge_ass(cue.debut_s)},{_horloge_ass(cue.fin_s)},BMS,,0,0,0,,{texte}"
        )
    chemin.write_text("\n".join(entete + evenements) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Transcription
# --------------------------------------------------------------------------------------
def _transcrire(moteur: str, wav: Path, lang: str, chemins: RunPaths, racine: Path,
                journal: Path, decoupage: float | None, force: bool = False) -> dict:
    """Lance le sous-processus ASR et relit son compte rendu.

    Le résultat est mis en cache sous `workspace/cache/asr/` (ignoré par git, comme le cache
    d'appels LLM de l'étape 10) : une transcription coûte 4 minutes, corriger le découpage des
    sous-titres n'a pas à les repayer. Le temps conservé est celui de la transcription d'origine.
    """
    suffixe = f"{moteur}{int(decoupage) if decoupage else ''}"
    cache = racine / "workspace" / "cache" / "asr" / f"{chemins.video_id}_{suffixe}.json"
    if cache.exists() and not force:
        depuis_cache = json.loads(cache.read_text(encoding="utf-8"))
        depuis_cache["cache"] = True
        return depuis_cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    travail_json = chemins.racine / f".asr_job_{suffixe}.json"
    sortie_json = chemins.racine / f".asr_out_{suffixe}.json"
    travail = {
        "engine": moteur, "wav": str(wav), "lang": lang, "out": str(sortie_json),
        "chunk_duration": decoupage, "overlap_duration": 15,
    }
    travail_json.write_text(json.dumps(travail, ensure_ascii=False), encoding="utf-8")
    environnement = dict(os.environ)
    environnement["HF_HUB_OFFLINE"] = "1"
    environnement["TOKENIZERS_PARALLELISM"] = "false"
    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n=== asr {chemins.video_id} — {moteur} découpage {decoupage} ===\n")
        trace.flush()
        proc = subprocess.run(
            [sys.executable, "-m", "factory.asr", str(travail_json)],
            cwd=str(racine), env=environnement, stdout=subprocess.PIPE, stderr=trace,
            text=True, timeout=TIMEOUT_ASR_S,
        )
        trace.write(proc.stdout or "")
    if proc.returncode != 0:
        raise RuntimeError(f"asr {moteur} : code {proc.returncode} (journal {journal})")
    resultat = json.loads(sortie_json.read_text(encoding="utf-8"))
    cache.write_text(json.dumps(resultat, ensure_ascii=False), encoding="utf-8")
    travail_json.unlink(missing_ok=True)
    sortie_json.unlink(missing_ok=True)
    return resultat


def _evaluer(brut: dict, mots_script: list[MotScript], duree_totale: float) -> Tentative:
    """Aligne une transcription sur le script et mesure ce qu'elle vaut."""
    mots_asr = brut["words"]
    apparies = aligner(mots_script, mots_asr)
    horodatages = horodater(mots_script, mots_asr, apparies, duree_totale)
    reference = " ".join(m.mot for m in mots_script)
    return Tentative(
        moteur=brut["engine"], decoupage=brut.get("chunk_duration"), mots_asr=mots_asr,
        texte=brut["text"], secondes=float(brut["secondes"]),
        couverture=len(apparies) / len(mots_script) if mots_script else 0.0,
        wer=asr.wer(reference, brut["text"]) or 0.0,
        wer_hors_nombres=asr.wer(reference, brut["text"], ignorer_nombres=True) or 0.0,
        horodatages=horodatages, apparies=apparies, cache=bool(brut.get("cache")),
    )


def _meilleure(tentatives: list[Tentative]) -> Tentative:
    """La meilleure des transcriptions : couverture d'abord, WER ensuite."""
    return min(tentatives, key=lambda t: (-round(t.couverture, 3), t.wer))


# --------------------------------------------------------------------------------------
# Étape
# --------------------------------------------------------------------------------------
def executer(video_id: str, racine: Path | None = None, moteur: str | None = None,
             force: bool = False) -> ResultatSousTitres:
    """Produit `words.json`, `subtitles.srt` et `subtitles.ass`."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    base = racine or racine_projet()
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    langue = cfg.languages[channel.lang]
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.voice_wav.exists() or not chemins.timings.exists():
        raise FileNotFoundError(f"voix absente : lance `factory voice --run {video_id}`")
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    timings = Timings.model_validate_json(chemins.timings.read_text(encoding="utf-8"))

    mots_script = [
        MotScript(mot=mot, segment=segment.id)
        for segment in script.segments
        for mot in segment.narration.split()
    ]
    if not mots_script:
        raise ValueError("script sans narration : rien à aligner")

    journal = base / "workspace" / "logs" / "etape11.log"
    journal.parent.mkdir(parents=True, exist_ok=True)
    duree_totale = timings.total_duration_s

    principal = moteur or langue.asr.primary
    tentatives = [_evaluer(
        _transcrire(principal, chemins.voice_wav, channel.lang, chemins, base, journal,
                    None, force),
        mots_script, duree_totale,
    )]
    seuil_global = langue.asr.seuil(len(mots_script))
    motif: str | None = None
    if moteur is None and (tentatives[0].couverture < COUVERTURE_MIN
                           or tentatives[0].wer_hors_nombres > seuil_global):
        motif = ("coverage_below_threshold" if tentatives[0].couverture < COUVERTURE_MIN
                 else "wer_above_threshold")
        if principal == "parakeet":
            # Rattrapage mesuré à l'étape 5.1 : le découpage récupère les fichiers tronqués.
            tentatives.append(_evaluer(
                _transcrire("parakeet", chemins.voice_wav, channel.lang, chemins, base,
                            journal, 20.0, force),
                mots_script, duree_totale,
            ))
        candidate = _meilleure(tentatives)
        if candidate.couverture < COUVERTURE_MIN or candidate.wer_hors_nombres > seuil_global:
            tentatives.append(_evaluer(
                _transcrire(langue.asr.fallback, chemins.voice_wav, channel.lang, chemins,
                            base, journal, None, force),
                mots_script, duree_totale,
            ))

    retenue = _meilleure(tentatives)
    if len(tentatives) > 1:
        alertes.append(
            f"repli ASR ({motif}) : "
            + " · ".join(f"{t.etiquette} couverture {t.couverture:.3f}, WER hors nombres "
                         f"{t.wer_hors_nombres:.1%}" for t in tentatives)
            + f" → retenu {retenue.etiquette}"
        )
    if retenue.moteur == langue.asr.primary:
        fallback_reason = None
    elif motif:
        fallback_reason = motif
    else:
        # `--engine whisper` sans cause mesurée : le repli existe, mais il vient de l'opérateur.
        fallback_reason = "operator_override"

    # Mesure par segment : le WER vit ici et jamais dans `voice/timings.json`, sortie de `voice`.
    mesures: list[MesureSegmentAsr] = []
    for segment in script.segments:
        indices = [i for i, m in enumerate(mots_script) if m.segment == segment.id]
        if not indices:
            continue
        debut = retenue.horodatages[indices[0]][0]
        fin = retenue.horodatages[indices[-1]][1]
        entendus = [m["w"] for m in retenue.mots_asr
                    if debut - 0.15 <= float(m["start_s"]) <= fin + 0.15]
        nb_mots = len(indices)
        mesures.append(MesureSegmentAsr(
            id=segment.id,
            coverage=round(sum(1 for i in indices if i in retenue.apparies) / nb_mots, 4),
            wer_vs_script=round(
                asr.wer(segment.narration, " ".join(entendus), ignorer_nombres=True) or 0.0, 4),
            wer_threshold=langue.asr.seuil(nb_mots),
            engine=retenue.moteur,
        ))

    words = Words(
        schema_version="1.0", engine=retenue.moteur, fallback_reason=fallback_reason,
        coverage=round(retenue.couverture, 4), wer_vs_script=round(retenue.wer, 4),
        wer_threshold=seuil_global, segments=mesures,
        words=[
            WordTiming(
                w=mot.mot, start_s=debut, end_s=fin, seg=mot.segment,
                asr_confidence=_confiance(retenue, index),
            )
            for index, (mot, (debut, fin)) in enumerate(
                zip(mots_script, retenue.horodatages, strict=True))
        ],
    )
    runs.ecrire_json(chemins.words, words)

    style = channel.charte.subtitles
    largeur = min(style.max_chars_per_line, PLAFOND_CARACTERES)
    cues = grouper([m.mot for m in mots_script], retenue.horodatages, largeur, style.max_lines)
    for cue in cues:  # un sous-titre ne survit pas à la fin de la piste
        cue.fin_s = min(cue.fin_s, duree_totale)
    ecrire_srt(cues, chemins.subtitles_srt)
    ecrire_ass(cues, [m.mot for m in mots_script], retenue.horodatages, chemins.subtitles_ass,
               channel.charte)

    ligne_max = max((len(ligne) for cue in cues for ligne in cue.lignes), default=0)
    trous = [cues[i + 1].debut_s - cues[i].fin_s for i in range(len(cues) - 1)]
    trou_max = max([*trous, cues[0].debut_s if cues else 0.0,
                    duree_totale - cues[-1].fin_s if cues else 0.0], default=0.0)
    if trou_max > 5.0:
        alertes.append(f"trou de {trou_max:.1f} s sans sous-titre : le critère « ≥ 1 par tranche "
                       "de 5 s » n'est pas tenu")
    if retenue.wer > 0.08:
        alertes.append(
            f"WER {retenue.wer:.1%} contre le script (> 8 %) — hors nombres "
            f"{retenue.wer_hors_nombres:.1%}, moteur {retenue.etiquette}"
        )
    if retenue.couverture < COUVERTURE_MIN:
        alertes.append(
            f"couverture {retenue.couverture:.3f} sous le seuil de {COUVERTURE_MIN} : "
            f"{len(mots_script) - retenue.ancres} mot(s) du script horodatés par interpolation"
        )

    secondes = time.perf_counter() - t0
    secondes_asr = sum(t.secondes for t in tentatives)
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.asr_engine = retenue.moteur
    manifest.decisions.subtitle_coverage = round(retenue.couverture, 4)
    manifest.decisions.wer_vs_script = round(retenue.wer, 4)
    manifest.execution.timings["subtitles"] = round(secondes, 2)
    manifest.execution.timings["subtitles_asr"] = round(secondes_asr, 2)
    manifest.execution.timings["subtitles_cues"] = len(cues)
    # Un temps rejoué n'est pas un temps mesuré : `subtitles_asr` porte alors la durée de la
    # transcription d'origine, et ce drapeau dit qu'elle n'a pas été repayée (règle de l'étape 10).
    manifest.execution.timings["subtitles_asr_cache"] = float(
        all(t.cache for t in tentatives))
    if not any(m.brique == "asr" for m in manifest.execution.modeles):
        from factory.core.models import ModeleUtilise

        manifest.execution.modeles.append(ModeleUtilise(
            brique="asr",
            repo=asr.REPO_PARAKEET if retenue.moteur == "parakeet" else asr.REPO_WHISPER,
            runtime="mlx", runtime_version=_version_mlx(),
        ))
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()

    with journal.open("a", encoding="utf-8") as trace:
        trace.write(json.dumps({
            "etape": "subtitles", "run": video_id, "moteur": retenue.etiquette,
            "couverture": round(retenue.couverture, 4), "wer": round(retenue.wer, 4),
            "wer_hors_nombres": round(retenue.wer_hors_nombres, 4),
            "cues": len(cues), "ligne_max": ligne_max, "trou_max_s": round(trou_max, 2),
            "temps_s": round(secondes, 1), "temps_asr_s": round(secondes_asr, 1),
            "alertes": alertes,
        }, ensure_ascii=False) + "\n")

    return ResultatSousTitres(
        words=words, cues=len(cues), ligne_la_plus_longue=ligne_max, tentatives=tentatives,
        retenue=retenue, secondes=secondes, secondes_asr=secondes_asr, trous_max_s=trou_max,
        alertes=alertes,
    )


def _confiance(tentative: Tentative, index: int) -> float | None:
    """Confiance ASR du mot apparié ; `None` pour un mot horodaté par interpolation.

    Un `None` n'est donc pas une lacune du format : c'est la trace explicite d'un mot que
    l'ASR n'a pas entendu et dont le timing est déduit de ses voisins.
    """
    if index not in tentative.apparies:
        return None
    valeur = tentative.mots_asr[tentative.apparies[index]].get("conf")
    return round(float(valeur), 4) if valeur is not None else None


def _version_mlx() -> str:
    """Version de mlx, lue dans un sous-processus pour ne rien charger ici."""
    proc = subprocess.run(
        [sys.executable, "-c", "import mlx.core as mx; print(mx.__version__)"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip() or "inconnue"
