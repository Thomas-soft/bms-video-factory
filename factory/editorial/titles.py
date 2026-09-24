"""Titres en variantes : patrons tirés au sort, note de règles, tournoi de duels.

Remplace `factory/steps/titles_v1.py`, dont le nom disait la limite : ses scores encodaient
ce que le corpus a mesuré, jamais ce qui a fait cliquer. Trois choses changent ici, et une
seule ne change pas.

1. **Les patrons sont tirés, pas subis.** Le LLM recevait les six premiers patrons de la
   niche et rendait huit titres qui se ressemblaient. Ici, ≥ 3 patrons sont **tirés au sort
   pondérés par leur part** dans le corpus (`registre/REFERENTIEL.json`), et chaque titre est
   commandé sur un patron nommé. Un tirage pondéré fait sortir le patron dominant plus
   souvent qu'un patron rare, sans jamais le faire sortir *toujours* : c'est ce qui laisse
   une chance à la queue de la distribution d'être mesurée un jour.
2. **Un fichier `learned/weights.json` peut déplacer ces poids** (étape 26). Il est lu s'il
   existe, ignoré sinon, et ce qu'il contient **multiplie** la part mesurée au lieu de la
   remplacer : un apprentissage sur trente vidéos ne doit pas pouvoir effacer une mesure
   faite sur 2 200 titres.
3. **Le classement final n'est pas l'heuristique.** Les règles notent la forme et écartent
   l'appât ; elles ne savent pas si un titre donne envie. Les quatre meilleures heuristiques
   entrent donc en **tournoi de duels** — deux demi-finales, une finale, chaque duel étant un
   appel LLM qui compare **deux** titres et rien d'autre. Comparer deux objets est la tâche
   sur laquelle un 9B quantifié se trompe le moins ; lui demander de classer huit titres d'un
   coup produit un ordre qui ne survit pas à une permutation de l'entrée.

Ce qui ne change pas : **aucun titre n'est jeté**. Les huit restent au manifeste avec leur
note de règles, leur rang de duel et le verdict de promesse. Un score jeté est une expérience
perdue, et la phase 5 n'aura rien d'autre à apprendre.

**La promesse est vérifiée.** Un titre peut être bien formé, bien noté, et mentir. Un appel
LLM court demande, sur le titre retenu : « le script répond-il à cette promesse ? ». Un
`non` ne corrige rien tout seul — il fait basculer sur le candidat suivant et inscrit
l'alerte. `None` (LLM indisponible) n'est pas `oui` : il est dit tel quel.
"""

from __future__ import annotations

import json
import random
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factory.core import referentiel
from factory.core.models import (
    Language,
    Niche,
    Script,
    VarianteTexteMiniature,
    VarianteTitre,
)
from factory.llm import ErreurLLM, TraceLLM, generate_json

#: Plafond de titre retenu en production. YouTube en accepte 100, mais tronque l'affichage
#: vers 70 caractères sur bureau et 50 à 60 en suggestion mobile (étape 21, veille) : au-delà,
#: la fin du titre n'est plus lue par personne.
PLAFOND_CARACTERES = 70

#: Ce que le prompt demande. Le nombre de patrons distincts est un contrôle, pas un vœu :
#: huit titres sur un seul patron ne mettent rien en concurrence.
N_TITRES = 8
N_TEXTES_MINIATURE = 5
PATRONS_DISTINCTS_MIN = 3
#: Entrants du tournoi de duels. Quatre = deux demi-finales et une finale, soit trois appels.
FINALISTES = 4

#: Fichier optionnel de poids appris, écrit par l'étape 26. Absent aujourd'hui, et c'est bien.
CHEMIN_POIDS_APPRIS = Path("learned") / "weights.json"

SCHEMA_SORTIE: dict[str, Any] = {
    "type": "object",
    "required": ["titres", "textes_miniature"],
    "properties": {
        "titres": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["texte", "patron"],
                "properties": {"texte": {"type": "string"}, "patron": {"type": "string"}},
            },
        },
        "textes_miniature": {"type": "array", "items": {"type": "string"}},
    },
}

SCHEMA_DUEL: dict[str, Any] = {
    "type": "object",
    "required": ["gagnant"],
    "properties": {
        "gagnant": {"type": "integer"},
        "motif": {"type": "string"},
    },
}

SCHEMA_PROMESSE: dict[str, Any] = {
    "type": "object",
    "required": ["tenue"],
    "properties": {
        "tenue": {"type": "boolean"},
        "motif": {"type": "string"},
    },
}


@dataclass
class ResultatTitres:
    """Ce que l'étape a produit, pour le manifeste et le journal."""

    titres: list[VarianteTitre]
    textes_miniature: list[VarianteTexteMiniature]
    titre_retenu: str
    texte_miniature_retenu: str
    patrons_distincts: int
    patrons_commandes: list[str]
    secondes: float
    duels: list[str] = field(default_factory=list)
    promesse_tenue: bool | None = None
    poids_appris: bool = False
    alertes: list[str] = field(default_factory=list)
    trace: TraceLLM | None = None


# --------------------------------------------------------------------------------------
# Poids des patrons — mesure du corpus, éventuellement corrigée par l'apprentissage
# --------------------------------------------------------------------------------------


def charger_poids_appris(racine: Path | None = None) -> dict[str, float]:
    """Multiplicateurs de patrons écrits par `factory learn` (étape 26), ou `{}`.

    Format : `{"version": "1.x", "titles": {"patterns": {"question_en_tete": 1.2, ...}}}`, lu
    par `factory.analytics.weights` (absent ou version incompatible → `{}`, repli corpus). Tout
    ce qui n'est pas un nombre fini strictement positif est ignoré ; le reste est borné à
    [0,7 ; 1,4] — l'apprentissage corrige la mesure du corpus, il ne l'annule pas.
    """
    from factory.analytics import weights as wmod

    donnees = wmod.charger(racine)
    bruts = ((donnees or {}).get("titles") or {}).get("patterns")
    if not isinstance(bruts, dict):
        return {}
    retenus: dict[str, float] = {}
    for cle, valeur in bruts.items():
        try:
            poids = float(valeur)
        except (TypeError, ValueError):
            continue
        if poids > 0 and poids == poids and poids != float("inf"):
            retenus[str(cle)] = wmod.borne(poids)
    return retenus


def poids_patrons(
    patrons: list[dict[str, Any]], appris: dict[str, float] | None = None
) -> dict[str, float]:
    """Part de chaque patron dans le corpus, multipliée par le poids appris s'il existe."""
    appris = appris or {}
    poids: dict[str, float] = {}
    for patron in patrons:
        identifiant = str(patron["id"])
        part = float(patron.get("part") or 0.0)
        poids[identifiant] = part * appris.get(identifiant, 1.0)
    return poids


def tirer_patrons(
    patrons: list[dict[str, Any]], n: int, seed: int | None = None,
    appris: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """`n` patrons distincts tirés **sans remise, pondérés par leur part**.

    Les patrons de part nulle (mesurés à zéro sur la niche) ne sont pas exclus : ils reçoivent
    un poids plancher, ce qui les fait sortir rarement plutôt que jamais. Une niche où
    `nombre_en_tete` n'a jamais été employé n'a pas prouvé qu'il ne marche pas ; elle a
    prouvé que personne n'a essayé.
    """
    if not patrons:
        return []
    poids = poids_patrons(patrons, appris)
    plancher = max(1e-3, 0.02 * max(poids.values(), default=0.0))
    restants = list(patrons)
    tirage = random.Random(seed)
    sortis: list[dict[str, Any]] = []
    for _ in range(min(n, len(restants))):
        valeurs = [max(plancher, poids.get(str(p["id"]), 0.0)) for p in restants]
        choisi = tirage.choices(restants, weights=valeurs, k=1)[0]
        sortis.append(choisi)
        restants.remove(choisi)
    return sortis


# --------------------------------------------------------------------------------------
# Reconnaissance de patron et note de règles
# --------------------------------------------------------------------------------------


def _sans_accents(texte: str) -> str:
    """Comparaison de mots insensible aux accents et à la casse."""
    decompose = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def mots_interdits_presents(texte: str, interdits: list[str]) -> list[str]:
    """Mots d'appât trouvés dans un titre. Comparaison par sous-chaîne normalisée."""
    aplati = _sans_accents(texte)
    return [mot for mot in interdits if _sans_accents(mot) in aplati]


def mots_curiosite_presents(texte: str, curiosite: list[str]) -> list[str]:
    """Mots de curiosité trouvés dans un titre — comparaison sur le mot entier.

    Sous-chaîne interdite ici, contrairement aux mots interdits : « no one » se trouverait
    dans « no one » comme dans « casino needs », et une note qui monte sur un faux positif
    ne mesure plus rien. Un mot de curiosité composé est cherché comme groupe de mots.
    """
    aplati = _sans_accents(texte)
    trouves = []
    for mot in curiosite:
        motif = r"\b" + r"\s+".join(re.escape(m) for m in _sans_accents(mot).split()) + r"\b"
        if re.search(motif, aplati):
            trouves.append(mot)
    return trouves


def _patron_detecte(texte: str, patrons: list[dict[str, Any]],
                    declare: str | None = None) -> str | None:
    """Patron du titre : **la forme d'abord**, la déclaration du LLM seulement en repli.

    Cinq patrons se vérifient sur le texte (question, nombre en tête, deux-points,
    superlatif, mise en garde, how-to) ; les autres — `nom_propre_en_tete` en tête — ne se
    reconnaissent pas sans analyse morphologique. Une expression régulière « mot capitalisé
    suivi d'un mot capitalisé » les reconnaîtrait **tous** dans une langue en casse de titre
    (mesuré à l'étape 13.2 : 3 titres anglais sur 3), ce qui ne mesure rien. On retient donc
    l'étiquette déclarée quand aucune forme ne tranche, et `None` si elle est inconnue.
    """
    connus = {p["id"] for p in patrons}
    premiers = texte.strip().split()
    premier = premiers[0].lower().strip("«\"'") if premiers else ""
    interrogatifs = {
        "pourquoi", "comment", "que", "qu'est-ce", "quand", "où", "combien", "qui", "quel",
        "quelle", "why", "how", "what", "when", "where", "who", "which", "is", "are", "does",
        "por", "cómo", "qué", "perché", "come", "cosa",
    }
    # Un titre interrogatif sans point d'interrogation reste un titre interrogatif : le
    # corpus mesure la **forme** « mot interrogatif en tête », pas la ponctuation.
    if "question_en_tete" in connus and (premier.rstrip("'") in interrogatifs
                                         or premier.split("'")[0] in interrogatifs):
        return "question_en_tete"
    if re.match(r"^\W*\d", texte) and "nombre_en_tete" in connus:
        return "nombre_en_tete"
    if ":" in texte and "deux_points" in connus:
        return "deux_points"
    superlatifs = ("le plus", "la plus", "les plus", "the most", "the biggest", "the largest",
                   "the strangest", "el más", "la più", "il più")
    if any(s in texte.lower() for s in superlatifs) and "superlatif" in connus:
        return "superlatif"
    verites = ("vérité", "verite", "truth", "verdad", "verità", "ce que", "what nobody",
               "ce qu'on", "personne ne")
    if any(v in texte.lower() for v in verites) and "verite_choc" in connus:
        return "verite_choc"
    gardes = ("n'utilisez", "arrêtez", "stop ", "never ", "jamais ", "ne faites")
    if any(g in texte.lower() for g in gardes) and "mise_en_garde" in connus:
        return "mise_en_garde"
    if texte.lower().startswith(("comment ", "how to ", "cómo ", "come ")) and "how_to" in connus:
        return "how_to"
    return declare if declare in connus else None


def noms_propres(script: Script) -> set[str]:
    """Mots capitalisés **ailleurs qu'en début de phrase** dans le script : des noms propres.

    Approximation assumée, et la seule disponible sans analyse morphologique : elle sert
    uniquement à ne pas décapitaliser « Pasteur » en ramenant un titre à la casse de phrase.
    """
    trouves: set[str] = set()
    textes = [script.hook.text] + [s.narration for s in script.segments]
    for texte in textes:
        for phrase in re.split(r"(?<=[.!?])\s+", texte):
            for mot in phrase.split()[1:]:
                nu = mot.strip("«»\"'’,;:()").strip()
                if nu[:1].isupper() and not nu.isupper():
                    trouves.add(nu.lower())
    return trouves


def normaliser_casse(texte: str, majuscules: str, propres: set[str]) -> tuple[str, bool]:
    """Applique la casse de la langue. Renvoie `(titre, modifié)`.

    Le modèle rend systématiquement de la Casse De Titre, y compris en français où la
    configuration demande une casse de phrase (mesuré à l'étape 13.2 : 8 titres sur 8). La
    charte tranche, pas le modèle — mais un mot reconnu comme nom propre dans le script
    garde sa majuscule.
    """
    if majuscules != "phrase_case":
        return texte, False
    mots = texte.split()
    sortie = [mots[0]] if mots else []
    for mot in mots[1:]:
        nu = mot.strip("«»\"'’,;:()")
        garde = nu.isupper() or nu.lower() in propres or nu[:1].isdigit()
        sortie.append(mot if garde else mot[:1].lower() + mot[1:])
    refait = " ".join(sortie)
    return refait, refait != texte


def majuscules_abusives(texte: str) -> bool:
    """Le titre crie-t-il ? Plus d'un mot de 3 lettres ou plus tout en capitales.

    Un sigle isolé (« NASA », « ADN ») est légitime et ne compte pas ; deux mots criés dans
    un titre de dix, c'est la politique « spam, pratiques trompeuses et arnaques » qui
    commence. Le seuil est une décision de production, pas une citation de la politique.
    """
    cries = [m for m in texte.split() if len(m.strip("«»\"'’,;:()!?")) >= 3
             and m.strip("«»\"'’,;:()!?").isupper()]
    return len(cries) > 1


def scorer_titre(
    texte: str, patrons: list[dict[str, Any]], cible: dict[str, Any], interdits: list[str],
    declare: str | None = None, curiosite: list[str] | None = None,
    appris: dict[str, float] | None = None,
) -> tuple[float, str | None, list[str]]:
    """Note de règles d'un titre, dans [0, 1]. Renvoie aussi le patron et les motifs.

    Cinq termes, tous tirés d'une mesure du référentiel ou d'une règle écrite : longueur
    (fenêtre 40-70, cible = médiane de la niche), patron reconnu pondéré par sa part, nombre
    ou question, mot de curiosité de la liste de la niche. Deux conditions sont
    **éliminatoires** et non pondérées : un mot interdit, ou des majuscules criées — c'est
    ce que la politique spam vise, et une pondération laisserait passer le titre qui compense
    ailleurs.
    """
    motifs: list[str] = []
    interdits_trouves = mots_interdits_presents(texte, interdits)
    patron = _patron_detecte(texte, patrons, declare)
    longueur = len(texte)

    # Fenêtre 40-70 : en deçà de 40 le titre ne porte pas d'information, au-delà de 70 il est
    # tronqué. À l'intérieur, la médiane de la niche reste l'optimum mesuré.
    mediane = float(cible["longueur_car"]["mediane"])
    cible_car = min(max(mediane, 40.0), float(PLAFOND_CARACTERES))
    if longueur > PLAFOND_CARACTERES:
        note_longueur = 0.0
        motifs.append(f"{longueur} caractères > plafond {PLAFOND_CARACTERES}")
    elif longueur < 40:
        note_longueur = max(0.0, longueur / 40.0 * 0.6)
        motifs.append(f"{longueur} caractères < plancher 40")
    else:
        note_longueur = max(0.0, 1.0 - abs(longueur - cible_car) / max(cible_car, 1.0))

    a_nombre = bool(re.search(r"\d", texte))
    a_question = texte.strip().endswith("?")
    note_forme = 0.0
    if a_nombre:
        note_forme += 0.6
        motifs.append("chiffre")
    if a_question:
        note_forme += 0.4
        motifs.append("question")

    poids = poids_patrons(patrons, appris)
    poids_max = max(poids.values(), default=0.0) or 1.0
    note_patron = poids.get(patron or "", 0.0) / poids_max
    if patron:
        motifs.append(f"patron {patron}")
    else:
        motifs.append("aucun patron reconnu")

    curieux = mots_curiosite_presents(texte, curiosite or [])
    # Un mot de curiosité vaut ; deux n'en valent pas deux. Empiler « secret », « nobody » et
    # « actually » dans un titre de dix mots est exactement ce que la politique spam vise.
    note_curiosite = 1.0 if len(curieux) == 1 else (0.5 if curieux else 0.0)
    if curieux:
        motifs.append("curiosité : " + ", ".join(curieux[:3]))

    score = (0.32 * note_longueur + 0.28 * note_patron
             + 0.22 * min(1.0, note_forme) + 0.18 * note_curiosite)
    if interdits_trouves:
        score = 0.0
        motifs.append("mot interdit : " + ", ".join(interdits_trouves))
    if majuscules_abusives(texte):
        score = 0.0
        motifs.append("majuscules abusives")
    return round(score, 3), patron, motifs


def scorer_texte_miniature(
    texte: str, cible_mots: float, maximum_mots: int, interdits: list[str]
) -> tuple[float, list[str]]:
    """Score d'un texte de miniature : nombre de mots, longueur des mots, mots interdits.

    L'étape 13.2 impose 2 à 4 mots quand le corpus en mesure 1,5 de médiane : un texte de
    1 mot ne dit rien d'un sujet de science, et au-delà de 4 il ne se lit plus en vignette.
    """
    motifs: list[str] = []
    mots = texte.split()
    n = len(mots)
    if not 2 <= n <= 4:
        motifs.append(f"{n} mots hors de [2, 4]")
        note_mots = 0.0
    else:
        # 2 mots quand la niche en mesure 1,5 : le plus proche de la cible gagne.
        note_mots = max(0.0, 1.0 - abs(n - max(2.0, cible_mots)) / 3.0)
    # Deux longueurs, deux effets distincts : le mot le plus long fixe la taille de police
    # que la composition peut employer, la longueur totale fixe le nombre de lignes.
    plus_long = max((len(m) for m in mots), default=0)
    note_mot = 1.0 if plus_long <= 8 else max(0.0, 1.0 - (plus_long - 8) / 8.0)
    total = len(texte)
    note_total = 1.0 if total <= 14 else max(0.0, 1.0 - (total - 14) / 16.0)
    if plus_long > 12:
        motifs.append(f"mot de {plus_long} caractères")
    if n > maximum_mots:
        motifs.append(f"au-delà du maximum mesuré de la niche ({maximum_mots})")
    score = 0.45 * note_mots + 0.30 * note_mot + 0.25 * note_total
    interdits_trouves = mots_interdits_presents(texte, interdits)
    if interdits_trouves:
        score = 0.0
        motifs.append("mot interdit : " + ", ".join(interdits_trouves))
    return round(score, 3), motifs


# --------------------------------------------------------------------------------------
# Tournoi de duels et vérification de promesse
# --------------------------------------------------------------------------------------


def duel(
    gauche: str, droite: str, sujet: str, angle: str,
    seed: int | None = None, racine: Path | None = None, trace: TraceLLM | None = None,
) -> tuple[int, str]:
    """Un duel : deux titres, un gagnant. Renvoie `(0 ou 1, motif)`.

    En cas d'échec du LLM, **le gauche gagne** — c'est-à-dire le mieux noté par les règles,
    puisque le tournoi est semé sur l'heuristique. Un duel indisponible ne doit pas produire
    un classement aléatoire : il doit produire le classement d'avant.
    """
    try:
        donnees, _ = generate_json(
            f"Sujet de la vidéo : {sujet}\nAngle : {angle}\n\n"
            f"Deux titres candidats pour cette vidéo :\n"
            f"0. {gauche}\n1. {droite}\n\n"
            "Lequel donne le plus envie de cliquer à quelqu'un qui ne connaît pas la chaîne, "
            "sans rien promettre que la vidéo ne tiendrait pas ? Réponds par un objet JSON "
            '{"gagnant": 0 ou 1, "motif": "<dix mots au plus>"}.',
            system=("Tu compares deux titres de vidéo YouTube et tu en désignes un. "
                    "Tu réponds uniquement par un objet JSON valide."),
            json_schema=SCHEMA_DUEL, max_tokens=120, temperature=0.3, seed=seed,
            etiquette="titles_duel", trace=trace, racine=racine,
        )
    except (ErreurLLM, ValueError, TypeError, KeyError) as erreur:
        return 0, f"duel indisponible ({type(erreur).__name__}) : l'heuristique tranche"
    gagnant = 1 if int(donnees.get("gagnant", 0)) == 1 else 0
    return gagnant, str(donnees.get("motif", "")).strip()[:70] or "choix LLM"


def tournoi(
    titres: list[str], sujet: str, angle: str, seed: int | None = None,
    racine: Path | None = None, trace: TraceLLM | None = None,
) -> tuple[list[int], list[str]]:
    """Tournoi à élimination sur les 4 premiers titres. Renvoie `(rangs, journal des duels)`.

    Les rangs sont des positions dans la liste reçue : `rangs[0]` est l'indice du vainqueur.
    Un tournoi à quatre ne donne qu'un ordre partiel — le finaliste battu est deuxième, mais
    les deux éliminés de demi-finale ne sont pas départagés entre eux. On les range alors sur
    leur semence, c'est-à-dire sur l'heuristique, et le manifeste dit que c'est ce qui a servi.
    """
    if len(titres) < 2:
        return list(range(len(titres))), []
    if len(titres) == 3:  # trois entrants : le mieux semé est exempté de demi-finale
        gagnant_b, motif_b = duel(titres[1], titres[2], sujet, angle, seed, racine, trace)
        b = 1 + gagnant_b
        journal = [f"{titres[1]} vs {titres[2]} → {titres[b]} ({motif_b})"]
        gagnant_f, motif_f = duel(titres[0], titres[b], sujet, angle,
                                  None if seed is None else seed + 10, racine, trace)
        vainqueur = 0 if gagnant_f == 0 else b
        second = b if gagnant_f == 0 else 0
        journal.append(f"finale {titres[0]} vs {titres[b]} → {titres[vainqueur]} ({motif_f})")
        perdant = next(i for i in (1, 2) if i not in (vainqueur, second))
        return [vainqueur, second, perdant], journal

    # Semé 1-4 et 2-3 : le mieux noté ne rencontre le deuxième qu'en finale.
    paires = [(0, 3), (1, 2)]
    demi: list[tuple[int, int]] = []
    journal: list[str] = []
    for index, (a, b) in enumerate(paires):
        gagnant, motif = duel(titres[a], titres[b], sujet, angle,
                              None if seed is None else seed + index, racine, trace)
        vainqueur, perdant = (a, b) if gagnant == 0 else (b, a)
        demi.append((vainqueur, perdant))
        journal.append(f"{titres[a]} vs {titres[b]} → {titres[vainqueur]} ({motif})")
    (v1, p1), (v2, p2) = demi
    gagnant, motif = duel(titres[v1], titres[v2], sujet, angle,
                          None if seed is None else seed + 20, racine, trace)
    champion, finaliste = (v1, v2) if gagnant == 0 else (v2, v1)
    journal.append(f"finale {titres[v1]} vs {titres[v2]} → {titres[champion]} ({motif})")
    # Les deux éliminés de demi-finale gardent leur ordre de semence : rien ne les a départagés.
    elimines = sorted([p1, p2])
    return [champion, finaliste, *elimines], journal


def verifier_promesse(
    titre: str, script: Script, racine: Path | None = None, trace: TraceLLM | None = None,
) -> tuple[bool | None, str]:
    """« Le script répond-il à la promesse du titre ? » Renvoie `(tenue, motif)`.

    `None` quand le LLM n'a pas répondu : **ce n'est pas un oui**. Un titre non vérifié part
    en production avec une alerte, pas avec un blanc-seing.
    """
    resume = " ".join(s.narration for s in script.segments[:6])[:1400]
    try:
        donnees, _ = generate_json(
            f"Titre proposé : {titre}\n\n"
            f"Début du script de la vidéo :\n{resume}\n\n"
            "Le script répond-il à la promesse du titre — le spectateur obtient-il ce que le "
            "titre annonce ? Réponds par un objet JSON "
            '{"tenue": true ou false, "motif": "<quinze mots au plus>"}.',
            system=("Tu vérifies qu'un titre ne promet rien que la vidéo ne tienne. "
                    "Tu réponds uniquement par un objet JSON valide."),
            json_schema=SCHEMA_PROMESSE, max_tokens=140, temperature=0.2,
            etiquette="titles_promesse", trace=trace, racine=racine,
        )
    except (ErreurLLM, ValueError, TypeError, KeyError) as erreur:
        return None, f"vérification indisponible : {erreur}"
    return bool(donnees.get("tenue")), str(donnees.get("motif", "")).strip()[:120]


# --------------------------------------------------------------------------------------
# Génération
# --------------------------------------------------------------------------------------


def _prompt(script: Script, niche_cfg: Niche, langue: Language, tires: list[dict[str, Any]],
            cible_mots_mini: float, nom_langue: str, curiosite: list[str]) -> str:
    """Prompt unique : les deux familles partent du même script et du même corpus."""
    # Huit titres pour N patrons tirés : la commande est explicite, plan par plan, sinon le
    # modèle rend huit variantes du patron le plus facile à écrire.
    commandes = [tires[i % len(tires)] for i in range(N_TITRES)] if tires else []
    lignes = "\n".join(
        f"{i + 1}. patron « {p['id']} » — {p['template']} "
        f"(exemple mesuré : « {str(p.get('exemple') or '')[:70]} »)"
        for i, p in enumerate(commandes)
    )
    resume = " ".join(s.narration for s in script.segments[:4])[:700]
    casse = ("Titres en casse de phrase (une seule majuscule initiale)"
             if langue.typographie.majuscules_titre == "phrase_case"
             else "Titres en Casse De Titre (majuscule à chaque mot important)")
    mots_curieux = (
        f"Mots de curiosité mesurés sur cette niche, à employer avec parcimonie — **un seul "
        f"par titre au maximum** : {', '.join(curiosite[:12])}.\n" if curiosite else ""
    )
    return (
        f"Sujet de la vidéo : {script.hook.text}\n"
        f"Angle éditorial : {script.editorial_signature.angle}\n"
        f"Début du script : {resume}\n\n"
        f"Langue de sortie : {nom_langue}. {casse}.\n\n"
        f"Écris exactement {N_TITRES} titres de vidéo YouTube, **un par ligne de commande "
        f"ci-dessous**, en respectant le patron demandé :\n{lignes}\n\n"
        f"Règles des titres : 40 à {PLAFOND_CARACTERES} caractères, "
        f"{niche_cfg.titres.longueur_car.mediane:.0f} en cible ; aucune promesse que la vidéo "
        "ne tient pas ; pas de mot entier en majuscules, pas d'emoji.\n"
        f"{mots_curieux}"
        f"Écris ensuite {N_TEXTES_MINIATURE} textes de miniature : 2 à 4 mots (le corpus de "
        f"la niche en mesure {cible_mots_mini:.1f} en médiane), lisibles en vignette de "
        "téléphone, sans ponctuation finale ; ils disent ce que l'image montre, ils ne "
        "répètent pas le titre mot pour mot.\n\n"
        "Réponds par un objet JSON : "
        '{"titres": [{"texte": "…", "patron": "id_du_patron"}], "textes_miniature": ["…"]}'
    )


def executer(
    script: Script,
    niche_cfg: Niche,
    langue: Language,
    nom_niche: str,
    seed: int | None = None,
    racine: Path | None = None,
    trace: TraceLLM | None = None,
    verifier: bool = True,
) -> ResultatTitres:
    """Demande, note, met en duel et classe les variantes. Ne touche ni manifeste ni disque."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    trace = trace or TraceLLM()
    patrons = referentiel.patrons_titres(nom_niche, racine)
    cible_titres = referentiel.cible_titres(nom_niche, racine)
    cible_mini = referentiel.cible_miniatures(nom_niche, racine)
    interdits = list(langue.titres.mots_interdits)
    curiosite = langue.titres.curiosite(nom_niche)
    if not curiosite:
        alertes.append(
            f"aucun mot de curiosité pour « {nom_niche} » dans config/languages/"
            f"{langue.code}.yaml : le terme de curiosité de la note vaut zéro pour tous"
        )
    appris = charger_poids_appris(racine)
    if appris:
        alertes.append(f"poids appris appliqués à {len(appris)} patron(s) (learned/weights.json)")

    tires = tirer_patrons(patrons, max(PATRONS_DISTINCTS_MIN, 4), seed, appris)

    donnees, _ = generate_json(
        _prompt(script, niche_cfg, langue, tires,
                float(cible_mini.get("texte_mots", {}).get("mediane", 2.0)),
                langue.name, curiosite),
        system=(
            "Tu écris des titres de vidéos YouTube qui tiennent ce qu'ils promettent. "
            "Tu réponds uniquement par un objet JSON valide."
        ),
        json_schema=SCHEMA_SORTIE,
        max_tokens=900,
        temperature=0.85,
        seed=seed,
        etiquette="titles",
        trace=trace,
        racine=racine,
    )

    vus: set[str] = set()
    titres: list[VarianteTitre] = []
    propres = noms_propres(script)
    recasses = 0
    for entree in donnees.get("titres", []):
        texte = str(entree.get("texte", "")).strip().strip('"')
        if not texte or texte.lower() in vus:
            continue
        vus.add(texte.lower())
        texte, modifie = normaliser_casse(texte, langue.typographie.majuscules_titre, propres)
        recasses += int(modifie)
        note, patron, motifs = scorer_titre(
            texte, patrons, cible_titres, interdits,
            str(entree.get("patron", "")).strip(), curiosite, appris,
        )
        titres.append(VarianteTitre(text=texte[:100], pattern_id=patron,
                                    length_char=len(texte), heuristic=note, score=note))
        if "mot interdit" in " ".join(motifs) or "majuscules abusives" in motifs:
            alertes.append(f"titre écarté ({motifs[-1]}) : « {texte[:60]} »")

    textes: list[VarianteTexteMiniature] = []
    vus_mini: set[str] = set()
    maximum_mots = int(cible_mini.get("texte_mots", {}).get("max", 9))
    cible_mots = float(cible_mini.get("texte_mots", {}).get("mediane", 2.0))
    for brut in donnees.get("textes_miniature", []):
        texte = re.sub(r"[.!]+$", "", str(brut).strip().strip('"')).strip()
        if not texte or texte.lower() in vus_mini:
            continue
        vus_mini.add(texte.lower())
        note, _motifs = scorer_texte_miniature(texte, cible_mots, maximum_mots, interdits)
        textes.append(VarianteTexteMiniature(text=texte, words=len(texte.split()), score=note))

    if recasses:
        alertes.append(f"{recasses} titre(s) ramenés à la casse "
                       f"« {langue.typographie.majuscules_titre} » de la langue")
    if len(titres) < N_TITRES:
        alertes.append(f"{len(titres)} titres retenus pour {N_TITRES} demandés")
    if len(textes) < N_TEXTES_MINIATURE:
        alertes.append(f"{len(textes)} textes de miniature pour {N_TEXTES_MINIATURE} demandés")
    if not titres:
        raise ValueError("titles : aucun titre exploitable produit par le LLM")

    patrons_distincts = len({t.pattern_id for t in titres if t.pattern_id})
    if patrons_distincts < PATRONS_DISTINCTS_MIN:
        alertes.append(
            f"{patrons_distincts} patron(s) distinct(s) reconnu(s) pour "
            f"{PATRONS_DISTINCTS_MIN} demandés — les variantes se ressemblent"
        )

    # Semence du tournoi : l'heuristique, à longueur croissante pour départager les égalités.
    titres.sort(key=lambda v: (-(v.heuristic or 0.0), v.length_char or 0))
    finalistes = [t for t in titres[:FINALISTES] if (t.heuristic or 0.0) > 0.0]
    duels: list[str] = []
    if len(finalistes) >= 2:
        rangs, duels = tournoi([t.text for t in finalistes], script.hook.text,
                               script.editorial_signature.angle, seed, racine, trace)
        for place, index in enumerate(rangs, start=1):
            finalistes[index].llm_rank = place
        # Le score final classe sur le duel quand il a eu lieu, sur l'heuristique sinon. Les
        # deux notes restent lisibles séparément au manifeste : c'est ce que la phase 5
        # comparera aux impressions réelles.
        for variante in finalistes:
            rang = variante.llm_rank or FINALISTES
            variante.score = round(
                0.5 * (variante.heuristic or 0.0) + 0.5 * (1.0 - (rang - 1) / FINALISTES), 3
            )
    elif len(titres) >= 2:
        alertes.append("aucun duel : moins de deux titres au-dessus de zéro")

    titres.sort(key=lambda v: (-(v.score or 0.0), v.llm_rank or 99, v.length_char or 0))
    if (titres[0].score or 0.0) <= 0.0:
        alertes.append("tous les titres sont à zéro (mot interdit, majuscules ou trop longs) : "
                       "le moins mauvais est retenu, à relire")

    # Promesse : vérifiée sur le retenu, et sur le suivant si le premier ment.
    promesse: bool | None = None
    retenu = titres[0]
    if verifier:
        for candidat in titres[:2]:
            tenue, motif = verifier_promesse(candidat.text, script, racine, trace)
            candidat.promise_kept = tenue
            if tenue is None:
                alertes.append(f"promesse non vérifiée : {motif}")
                promesse = None
                break
            if tenue:
                retenu, promesse = candidat, True
                break
            alertes.append(f"titre écarté, promesse non tenue : « {candidat.text[:60]} » — "
                           f"{motif}")
            promesse = False
        else:
            alertes.append("les deux meilleurs titres ne tiennent pas leur promesse : "
                           "le premier est retenu, à relire")
    if retenu is not titres[0]:
        titres.remove(retenu)
        titres.insert(0, retenu)

    # Le texte de miniature de repli est le texte à l'écran du hook, écrit par le script :
    # il existe toujours, et il est déjà à la charte.
    repli_mini = (script.segments[0].on_screen_text or script.hook.text)[:40]
    textes.sort(key=lambda v: -(v.score or 0.0))
    texte_mini = textes[0].text if textes else repli_mini
    if not textes:
        alertes.append("aucun texte de miniature exploitable : repli sur on_screen_text du hook")

    return ResultatTitres(
        titres=titres,
        textes_miniature=textes,
        titre_retenu=titres[0].text,
        texte_miniature_retenu=texte_mini,
        patrons_distincts=patrons_distincts,
        patrons_commandes=[str(p["id"]) for p in tires],
        secondes=time.perf_counter() - t0,
        duels=duels,
        promesse_tenue=promesse,
        poids_appris=bool(appris),
        alertes=alertes,
        trace=trace,
    )
