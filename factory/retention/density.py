"""Densité d'information : combien de faits vérifiables par minute de narration.

**Ce que la mesure compte.** Un « fait » est ici un élément que le spectateur peut vérifier
ailleurs : un nombre, une date, une entité nommée, une unité, une comparaison chiffrable, une
attribution de source. Ce n'est pas la vérité du propos — elle relève de `review.json` — c'est
sa **prise** : un script sans aucun de ces éléments n'apprend rien et se regarde en diagonale.

**Deux mesures, pas une.** Les règles (ci-dessous) sont gratuites, reproductibles et aveugles
au sens : elles comptent « two thousand years » et « the largest » sans savoir si la phrase
autour dit quelque chose. Le juge LLM (`juger`) lit 200 mots et note sur une grille ; il est
cher et bruité. Les deux sont rapportés séparément, jamais moyennés : c'est la mesure par
règles qui décide de la régénération, le juge qui la commente.

**Aucun fait inventé.** Quand la densité est sous la cible, le module ne demande pas au modèle
« d'ajouter des faits » : il lui redonne `research.json` et exige que chaque ajout cite un `id`
de la liste. **Portée exacte de la garantie**, mesurée le 18/09/2026 : `factory/steps/script.py`
**filtre** les `sources` rendues par le modèle contre les `id` de `research.json` — un identifiant
inventé ne peut pas entrer au script. En revanche un segment `point` qui ne cite **aucune** source
est **signalé** (alerte), pas refusé : la narration n'est pas rapprochée phrase par phrase des
faits. La vérification de la véracité du propos reste `review.json`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from factory import llm
from factory.core.models import Research, Script

# --------------------------------------------------------------------------------------
# Règles de comptage
# --------------------------------------------------------------------------------------
# Jeu de règles **mesuré** : sous-agent B de l'étape 16, 263 transcriptions anglaises du
# registre. Les catégories sont appliquées dans l'ordre de ce dictionnaire — l'ordre EST la
# priorité — et tout empan déjà pris est refusé aux catégories suivantes. Sans cela
# « according to NASA in 1977 » vaudrait cinq faits pour une seule information.
#
# La mesure de référence est le **nombre brut** de faits par minute : c'est elle qui porte les
# cibles de niche de `config/niches/`. Le total pondéré est rapporté en second, il dit de quoi
# la densité est faite (une attribution ne vaut pas un nom propre), il ne décide de rien.

_NUMW = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand|million|billion|trillion)"
)
_NUM = r"(?:\d[\d,]*(?:\.\d+)?|" + _NUMW + r")"
_UNITS = (
    r"(?:kg|grams?|mg|mcg|lbs?|pounds?|ounces?|tons?|tonnes?|miles?|km|meters?|metres?|"
    r"centimet(?:er|re)s?|cm|millimet(?:er|re)s?|mm|kilomet(?:er|re)s?|feet|"
    r"foot|inches|yards?|acres?|hectares?|liters?|litres?|ml|gallons?|degrees?|celsius|"
    r"fahrenheit|volts?|watts?|joules?|calories?|kcal|hertz|hz|light[\s-]?years?|mph|"
    r"decibels?|molecules?|atoms?|species|people|men|women|children|patients?|participants?|"
    r"cases?|deaths?|victims?|years?|months?|weeks?|days?|hours?|minutes?|seconds?|times|"
    r"percent|units?)"
)
_MOIS = (r"(?:January|February|March|April|May|June|July|August|September|October|November|"
         r"December)")

I = re.IGNORECASE

#: `(nom, poids, motif)` dans l'ordre de priorité. Le poids ne sert qu'au total pondéré.
REGLES: list[tuple[str, float, re.Pattern[str]]] = [
    ("attribution", 3.0, re.compile(
        r"\b(?:according to|researchers?\s+(?:at|from|in)|scientists?\s+(?:at|from)|"
        r"a\s+(?:new\s+|recent\s+|large\s+|\d{4}\s+)?(?:study|trial|survey|paper|report|"
        r"experiment|meta[\s-]analysis)\b|studies?\s+(?:show|showed|suggest|found|find|"
        r"indicate)|published\s+in\b|data\s+from\b|peer[\s-]reviewed|clinical\s+trials?|"
        r"randomi[sz]ed\s+controlled|experts?\s+(?:say|believe|estimate|agree)|"
        r"(?:court|police|autopsy|coroner|medical\s+examiner)\s+(?:records?|reports?|"
        r"documents?|files?)|(?:NASA|NOAA|WHO|CDC|FBI|NIH|FDA|MIT|Harvard|Oxford|Stanford|"
        r"Cambridge|Yale|Johns\s+Hopkins|Mayo\s+Clinic|Pew|Gallup)\b)", I)),
    ("percent", 2.5, re.compile(
        r"(?:\b\d+(?:\.\d+)?\s?(?:%|percent\b)|\b" + _NUMW + r"\s+percent\b|"
        r"\b(?:half|a\s+third|a\s+quarter|two[\s-]thirds|three[\s-]quarters|"
        r"nine\s+out\s+of\s+ten|\d+\s+out\s+of\s+\d+)\s+of\b)", I)),
    ("money", 2.0, re.compile(
        r"(?:[$\u20ac\u00a3]\s?\d[\d,.]*\s*(?:million|billion|trillion|thousand|k\b)?|"
        r"\b" + _NUM + r"(?:\s+" + _NUMW + r")*\s+(?:dollars?|euros?)\b)", I)),
    ("date_periode", 2.0, re.compile(
        r"(?:\b(?:in|by|since|around|before|after|from|until)\s+(?:the\s+)?"
        r"(?:1[0-9]{3}|20[0-9]{2})s?\b|\b(?:1[0-9]{3}|20[0-9]{2})s\b|"
        r"\b(?:1[5-9][0-9]{2}|20[0-2][0-9])\b|" + _MOIS + r"\s+\d{1,2}(?:st|nd|rd|th)?"
        r"(?:,?\s+\d{4})?\b|\b" + _NUM + r"\s+(?:years?|decades?|centuries|century|months?|"
        r"weeks?|days?)\s+(?:ago|old|later|earlier|before|after)\b|"
        r"\bthe\s+(?:1[0-9]|20|[1-9])(?:th|st|nd|rd)\s+century\b|\b(?:BCE?|AD|CE)\b)")),
    ("quantite_unite", 2.0, re.compile(
        r"\b" + _NUM + r"(?:[\s,-]+" + _NUMW + r")*\s*" + _UNITS + r"\b", I)),
    ("comparatif", 1.0, re.compile(
        r"(?:\b(?:more|less|fewer|greater|higher|lower|larger|smaller|faster|slower|longer|"
        r"shorter|bigger|heavier|lighter|older|younger|stronger|weaker|cheaper|richer|"
        r"deadlier|safer|better|worse)\s+than\b|"
        r"\b(?:twice|three\s+times|ten\s+times|\d+\s+times)\s+(?:as|more|less|the|higher|"
        r"lower|bigger|smaller|faster|slower|larger)\b|"
        r"\bthe\s+(?:most|least|best|worst|biggest|largest|smallest|highest|lowest|fastest|"
        r"slowest|longest|oldest|deadliest|rarest|first|second|third|only|leading|"
        r"number\s+one)\b|\bthe\s+[a-z]{4,}est\b)", I)),
    ("entite_multi", 1.5, re.compile(
        r"\b[A-Z][a-z]{2,}(?:\s+(?:of|the)\s+)?(?:\s+[A-Z][a-z]{2,})+\b")),
    ("acronyme", 1.5, re.compile(r"\b(?:[A-Z]{2,6}|[A-Z]\.(?:[A-Z]\.){1,4})\b")),
    # Les nombres en toutes lettres comptent autant que les chiffres : le script est écrit
    # pour le TTS (« Write numbers the way they are spoken »), donc **nos** scripts n'en
    # contiennent aucun en chiffres. Les compter en chiffres seulement reviendrait à mesurer
    # une densité systématiquement basse sur notre propre production et haute sur le corpus.
    ("nombre_nu", 1.0, re.compile(
        r"\b\d[\d,]*(?:\.\d+)?\b|\b" + _NUMW + r"(?:[\s-]" + _NUMW + r")*\b", I)),
    ("entite_simple", 1.0, re.compile(r"\b[A-Z][a-z]{2,}\b")),
]

#: Tags non verbaux des transcriptions (`[Music]`) et chevrons de sous-titres : retirés avant
#: comptage, sans quoi « Music » et « Applause » comptent comme des entités.
_TAGS = re.compile(r"\[[^\]]*\]|&gt;&gt;+|>>+")

#: Début de phrase : une majuscule y est grammaticale, pas une entité. Nos scripts sont
#: ponctués (`_normaliser_capitales` de `script.py`), le filtre y est donc efficace — il l'est
#: beaucoup moins sur les transcriptions auto-générées du corpus, ce que le § 8 du rapport B
#: chiffre et que `docs/QC.md` répète.
_DEBUT_PHRASE = re.compile(r"(?:\A|(?<=[.!?\u2026])\s+|(?<=[.!?\u2026][\"\'])\s+)([A-Z][a-z]+)")

#: Mots capitalisés qui ne sont jamais des entités. Liste courte et explicite : la stoplist
#: automatique du rapport B (mots présents dans ≥ 30 % des transcriptions) n'a pas de sens sur
#: un script unique — elle suppose un corpus.
_ENTITES_EXCLUES = frozenset({
    "The", "This", "That", "These", "Those", "There", "Then", "They", "Their", "Them",
    "And", "But", "For", "Not", "You", "Your", "We", "Our", "It", "Its", "He", "She", "His",
    "Her", "What", "When", "Where", "Why", "How", "Who", "Which", "Now", "Here", "Every",
    "Most", "Some", "Many", "More", "Less", "One", "Two", "Three", "Four", "Five", "First",
    "Last", "Next", "Yes", "No", "If", "So", "Because", "After", "Before", "Once", "Still",
    "Even", "Just", "Only", "Also", "Yet", "Today", "Instead", "Imagine", "Look", "Think",
})

#: Nombres qui ne comptent pas : « one of the », « no one ». Sans ce garde-fou, « one » à lui
#: seul pèse près d'un dixième du total (mesuré sur le corpus par le sous-agent B).
_NOMBRES_OUTILS = re.compile(
    r"\b(?:one of|one another|one by one|no one|any one|each one|the one|this one|that one|"
    r"one more|one day|one thing|one way|for one|at one)\b", I)


@dataclass
class Comptage:
    """Ce que les règles ont trouvé, et ce que ça fait par minute."""

    par_categorie: dict[str, int] = field(default_factory=dict)
    total: int = 0
    total_pondere: float = 0.0
    mots: int = 0
    duree_min: float = 0.0
    exemples: dict[str, list[str]] = field(default_factory=dict)

    @property
    def faits_par_minute(self) -> float:
        """**La** mesure : nombre brut de faits par minute de narration.

        C'est celle que le sous-agent B a mesurée sur le corpus et qui porte les cibles de
        `config/niches/`. La pondération sert à décrire, pas à décider.
        """
        return round(self.total / self.duree_min, 2) if self.duree_min > 0 else 0.0

    @property
    def faits_pondere_par_minute(self) -> float:
        """Variante pondérée : une attribution vaut trois, un nom propre un."""
        return round(self.total_pondere / self.duree_min, 2) if self.duree_min > 0 else 0.0

    @property
    def part_entites(self) -> float:
        """Part des noms propres dans le total brut.

        Mesurée à 54,9 % sur `science_pop` (rapport B § 6) : plus de la moitié du score vient
        des entités, pas des preuves. Une densité tenue par les seuls noms propres n'est pas
        la densité qu'on veut ; la part est donc rapportée avec la valeur.
        """
        entites = sum(self.par_categorie.get(nom, 0)
                      for nom in ("entite_simple", "entite_multi", "acronyme"))
        return round(entites / self.total, 3) if self.total else 0.0

    def json(self) -> dict[str, Any]:
        return {"facts_per_min": self.faits_par_minute,
                "facts_per_min_weighted": self.faits_pondere_par_minute,
                "count": self.total, "entity_share": self.part_entites,
                "by_category": dict(self.par_categorie),
                "words": self.mots, "minutes": round(self.duree_min, 2)}


def compter(texte: str) -> tuple[dict[str, int], int, float, dict[str, list[str]]]:
    """Compte les faits d'un texte, sans jamais compter deux fois le même empan.

    Rend `(par_catégorie, total_brut, total_pondéré, exemples)`.
    """
    propre = _TAGS.sub(" ", texte)
    pris: list[tuple[int, int]] = []
    par_categorie: dict[str, int] = {}
    exemples: dict[str, list[str]] = {}
    total_pondere = 0.0
    total = 0

    debuts_de_phrase = {m.start(1) for m in _DEBUT_PHRASE.finditer(propre)}
    outils = [m.span() for m in _NOMBRES_OUTILS.finditer(propre)]
    deja: dict[str, list[tuple[int, int]]] = {nom: [] for nom, _, _ in REGLES}

    for nom, poids, motif in REGLES:
        for trouve in motif.finditer(propre):
            debut, fin = trouve.span()
            if _chevauche(debut, fin, pris) or _chevauche(debut, fin, outils):
                continue
            if _colle_au_precedent(debut, deja[nom]):
                # « According to researchers at NASA » est **une** attribution, pas trois :
                # deux matchs de la même catégorie séparés par un espace décrivent le même
                # fait. Sans cette fusion, l'attribution pesait le triple de son dû.
                pris.append((debut, fin))
                deja[nom].append((debut, fin))
                continue
            if nom in ("entite_simple", "entite_multi"):
                premier = trouve.group().split()[0]
                if debut in debuts_de_phrase or premier in _ENTITES_EXCLUES:
                    continue
            pris.append((debut, fin))
            deja[nom].append((debut, fin))
            par_categorie[nom] = par_categorie.get(nom, 0) + 1
            total += 1
            total_pondere += poids
            exemples.setdefault(nom, [])
            if len(exemples[nom]) < 3:
                exemples[nom].append(trouve.group().strip())
    return par_categorie, total, total_pondere, exemples


def _chevauche(debut: int, fin: int, pris: Iterable[tuple[int, int]]) -> bool:
    return any(debut < f and d < fin for d, f in pris)


#: Écart en caractères sous lequel deux matchs de la même catégorie décrivent le même fait.
COLLE_MAX = 3


def _colle_au_precedent(debut: int, memes: list[tuple[int, int]]) -> bool:
    """Le match commence-t-il dans le prolongement immédiat d'un match de même catégorie ?"""
    return any(0 <= debut - f <= COLLE_MAX for _, f in memes)


def mesurer(textes: Iterable[str], mots_par_minute: float) -> Comptage:
    """Densité d'un ensemble de textes, rapportée au débit de narration de la niche."""
    joint = "\n".join(t for t in textes if t)
    par_categorie, total, pondere, exemples = compter(joint)
    mots = len(joint.split())
    return Comptage(par_categorie=par_categorie, total=total, total_pondere=pondere, mots=mots,
                    duree_min=mots / mots_par_minute if mots_par_minute > 0 else 0.0,
                    exemples=exemples)


def mesurer_script(script: Script, mots_par_minute: float) -> Comptage:
    """Densité du script entier, hook compris : le spectateur ne fait pas la différence."""
    return mesurer([script.hook.text, *(s.narration for s in script.segments
                                        if s.role != "hook")], mots_par_minute)


# --------------------------------------------------------------------------------------
# Cible de niche
# --------------------------------------------------------------------------------------

def _bloc(niche: str, racine: Path | None):
    from factory.core import config as config_module
    cfg = config_module.charger(racine, strict=False)
    bloc = cfg.niches.get(niche)
    return None if bloc is None else getattr(bloc, "densite_faits_par_minute", None)


def cible(niche: str, racine: Path | None = None) -> float | None:
    """Cible de densité de la niche, lue dans `config/niches/<niche>.yaml`.

    `None` quand la niche ne porte pas de cible mesurée : le module ne comble aucun trou,
    à charge de l'appelant de le signaler (règle du module `referentiel`).
    """
    bloc = _bloc(niche, racine)
    return None if bloc is None else (float(bloc.cible) if bloc.cible else None)


def plancher(niche: str, racine: Path | None = None) -> float | None:
    """Densité **sous laquelle le run est refusé**, distincte de la cible.

    Pourquoi deux seuils et non un. La cible est la médiane mesurée des chaînes du registre,
    qui écrivent avec une documentation illimitée ; nos scripts n'ont que les faits de
    `research.json`. Faire du chiffre du corpus le seuil de refus reviendrait à refuser tous
    les runs — et un portillon qui refuse tout ne trie rien. La cible déclenche donc
    l'enrichissement sourcé, le plancher seul fait échouer le run.
    """
    bloc = _bloc(niche, racine)
    return None if bloc is None else (float(bloc.plancher) if bloc.plancher else None)


# --------------------------------------------------------------------------------------
# Juge LLM
# --------------------------------------------------------------------------------------

SYSTEME_JUGE = (
    "You rate how much verifiable information a narration carries. You answer with one JSON "
    "object only, no commentary."
)

GABARIT_JUGE = """Rate this narration excerpt.

"{extrait}"

Score each criterion from 0 to 5, then count.

- checkable_facts: how many statements a viewer could verify elsewhere (a figure, a date, a
  named thing, a measured comparison, a named source). Count them, do not rate them.
- specificity: 0 = only general claims, 5 = every sentence names something precise.
- new_information: 0 = repeats what it already said, 5 = every sentence adds something.
- sourcing: 0 = nothing is attributed, 5 = the claims say where they come from.
- vagueness: 0 = no filler, 5 = mostly filler ("many experts", "it is well known").

Answer with this JSON object and nothing else:
{{"checkable_facts": <integer>, "specificity": 0-5, "new_information": 0-5,
  "sourcing": 0-5, "vagueness": 0-5}}"""

SCHEMA_JUGE = {
    "type": "object",
    "properties": {"checkable_facts": {"type": "integer"},
                   "specificity": {"type": "integer"},
                   "new_information": {"type": "integer"},
                   "sourcing": {"type": "integer"},
                   "vagueness": {"type": "integer"}},
    "required": ["checkable_facts", "specificity", "new_information", "sourcing", "vagueness"],
}

#: Longueur de l'extrait soumis au juge, en mots. Au-delà, un 9B quantifié cesse de compter.
EXTRAIT_MOTS = 200


@dataclass
class Jugement:
    """Note du juge LLM, extrapolée en faits par minute."""

    faits_comptes: int
    specificite: int
    information_nouvelle: int
    sourcage: int
    vague: int
    mots_juges: int
    mots_par_minute: float

    @property
    def faits_par_minute(self) -> float:
        minutes = self.mots_juges / self.mots_par_minute if self.mots_par_minute else 0.0
        return round(self.faits_comptes / minutes, 2) if minutes > 0 else 0.0

    def json(self) -> dict[str, Any]:
        return {"facts_per_min_judge": self.faits_par_minute,
                "counted": self.faits_comptes, "specificity": self.specificite,
                "new_information": self.information_nouvelle, "sourcing": self.sourcage,
                "vagueness": self.vague, "words_judged": self.mots_juges}


def juger(
    script: Script, mots_par_minute: float, seed: int = 0, racine: Path | None = None,
    trace: Any | None = None,
) -> Jugement | None:
    """Fait noter un extrait de ~200 mots pris au milieu du script. `None` si le juge échoue.

    Le milieu, et pas le début : le hook et le contexte sont les parties les plus denses par
    construction, les noter reviendrait à se donner une bonne note.
    """
    corps = [s.narration for s in script.segments if s.role in {"point", "contexte"}]
    if not corps:
        return None
    mots = " ".join(corps).split()
    debut = max(0, len(mots) // 2 - EXTRAIT_MOTS // 2)
    extrait = " ".join(mots[debut : debut + EXTRAIT_MOTS])
    try:
        donnees, _ = llm.generate_json(
            GABARIT_JUGE.format(extrait=extrait), system=SYSTEME_JUGE,
            json_schema=SCHEMA_JUGE, max_tokens=160, temperature=0.2, seed=seed,
            etiquette="retention:densite:juge", trace=trace, racine=racine,
        )
    except Exception:  # noqa: BLE001 — l'absence de juge n'est pas une note
        return None
    return Jugement(
        faits_comptes=int(donnees.get("checkable_facts", 0)),
        specificite=int(donnees.get("specificity", 0)),
        information_nouvelle=int(donnees.get("new_information", 0)),
        sourcage=int(donnees.get("sourcing", 0)),
        vague=int(donnees.get("vagueness", 0)),
        mots_juges=len(extrait.split()), mots_par_minute=mots_par_minute,
    )


# --------------------------------------------------------------------------------------
# Enrichissement sourcé
# --------------------------------------------------------------------------------------

# Le gabarit d'enrichissement vit dans `factory/prompts/script_<lang>.md`
# (section `enrichissement`), pas ici : un texte envoyé au modèle est une donnée,
# pas du code. Ce module ne fournit que ce qui se calcule.

def segments_a_enrichir(script: Script, n: int = 4) -> list[str]:
    """Les `n` segments de contenu les moins denses : c'est là que l'ajout se voit.

    Les segments qui portent une boucle ouverte ou une rupture ne sont pas touchés : leur
    dernière (ou première) phrase fait un travail que l'ajout d'un chiffre détruirait.
    """
    candidats = [s for s in script.segments
                 if s.role in {"point", "contexte"} and s.open_loop == "none"]
    notes: list[tuple[float, str]] = []
    for segment in candidats:
        _, total, _, _ = compter(segment.narration)
        mots = max(1, segment.word_count)
        notes.append((total / mots, segment.id))
    return [identifiant for _, identifiant in sorted(notes)[:n]]


def faits_disponibles(recherche: Research) -> str:
    """Liste des faits de `research.json`, telle qu'elle est donnée au modèle."""
    lignes = []
    for fait in recherche.facts:
        valeur = f" [{fait.value} {fait.unit or ''}]".rstrip() if fait.value else ""
        lignes.append(f"- {fait.id} : {fait.claim}{valeur}")
    return "\n".join(lignes)
