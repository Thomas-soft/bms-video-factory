"""Modèles de données de l'usine.

Contrat : `docs/INTERFACES.md`. Champs obligatoires de conformité : `docs/CONFORMITE.md` § 10.
Règle du projet : tout ce qui est chaîne, niche, style, langue ou produit est une donnée
validée, jamais une constante de code.
"""

from __future__ import annotations

import re
from datetime import date as DateJour, time
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"
MAJEURE_ATTENDUE = 1

# --------------------------------------------------------------------------------------
# Types contraints — § 0 « Conventions communes » de INTERFACES.md
# --------------------------------------------------------------------------------------

LangCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")]
Horodatage = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
]
Identifiant = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_.-]*$", max_length=80)]
SegmentId = Annotated[str, StringConstraints(pattern=r"^seg_\d{2,3}$")]
ShotId = Annotated[str, StringConstraints(pattern=r"^shot_\d{2,3}$")]
Couleur = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
HeureLocale = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]

#: Alphabet du suffixe d'identifiant de run : ni i, ni l, ni o, ni 0, ni 1 (ARCHITECTURE § 3.1).
ALPHABET_ID = "abcdefghjkmnpqrstuvwxyz23456789"
VideoId = Annotated[
    str, StringConstraints(pattern=rf"^[a-z0-9]+(?:-[a-z0-9]+)*-\d{{8}}-[{ALPHABET_ID}]{{4}}$")
]

Role = Literal["hook", "contexte", "point", "rupture", "sponsor", "cta", "conclusion"]
OpenLoop = Literal["plant", "payoff", "none"]
# `mini_recit` ajouté à l'étape 16 (18/09/2026) : le prompt en fait un des quatre types de
# rupture. `silence` est conservé — les runs antérieurs en portent — mais n'est plus tiré.
TypeInterrupt = Literal[
    "question", "chiffre", "silence", "changement_de_plan", "mini_recit",
]
AngleEditorial = Literal["opinion", "comparaison_chiffree", "test", "donnee_proprietaire"]
SourceSujet = Literal["topics_queue", "referentiel", "manuel"]
Confiance = Literal["high", "medium", "low"]
TypeEntite = Literal["person", "place", "org", "concept"]
ApiSource = Literal["wikipedia", "wikidata", "pubmed", "openlibrary", "arxiv", "semantic_scholar"]
Mouvement = Literal["zoom_in", "zoom_out", "pan", "parallax", "static"]
Transition = Literal["cut", "fade", "dip_black", "whip", "none"]
#: Ambiance du lit musical. Cinq valeurs, parce qu'une piste se choisit par ambiance et non par
#: titre : la niche en porte une par défaut, un script peut la surcharger pour une vidéo.
Mood = Literal["calme", "tension", "curieux", "energique", "sombre"]
TypeAsset = Literal["image", "stock", "card", "avatar"]
Couche = Literal["foreground", "background"]
Fournisseur = Literal[
    "flux", "pexels", "pixabay", "openverse", "wikimedia", "nasa",
    "internet_archive", "library", "charte",
]
Reseau = Literal["amazon", "awin", "cj", "impact", "digistore24", "clickbank"]
CheminPublication = Literal["manual_studio", "api_scheduled"]
EtatPublication = Literal["draft", "ready_to_publish", "uploaded_private", "scheduled", "public"]
EtatRun = Literal[
    "queued", "running", "awaiting_review", "blocked", "failed",
    "exported", "published", "visual_review_pending",
]
DecisionRelecture = Literal["approved", "approved_with_edits", "rejected", "auto"]
#: Identités que porte `reviewer` quand **aucun humain n'a lu**. Deux orthographes parce que
#: l'étape 22.1 a écrit `auto-approve` avant que l'étape 22.2 ne retienne `auto` : les lignes
#: déjà produites sont des pièces de conformité, on ne les réécrit pas pour faire joli.
RELECTEURS_MACHINE: frozenset[str] = frozenset({"auto", "auto-approve"})
EtatControle = Literal["pass", "warn", "fail", "skipped"]
VerdictQc = Literal["pass", "regenerate", "blocked"]
StatutStyle = Literal["retenu_v1", "retenu_v2", "planifie", "serveur_seulement", "abandonne"]
Backend = Literal["ffmpeg", "revideo"]
MoteurTts = Literal["qwen3_tts", "kokoro", "chatterbox"]
MoteurAsr = Literal["parakeet", "whisper"]
Jour = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
Genre = Literal["f", "m", "n"]

#: Un état « publiable » : c'est à partir de là que les champs de CONFORMITE § 10 sont exigés.
ETATS_PUBLIABLES: frozenset[str] = frozenset(
    {"ready_to_publish", "uploaded_private", "scheduled", "public"}
)

#: Longueur maximale du sous-identifiant d'affiliation, par réseau (CONFORMITE § 10.4).
SUBID_PAR_RESEAU: dict[str, tuple[str | None, int | None]] = {
    "amazon": (None, None),
    "awin": ("clickref", 50),
    "cj": ("sid", 64),
    "impact": ("SubId1", 255),
    # Étape 27 (veille du 23/09/2026) : Digistore24 porte la clé de campagne **dans le chemin**
    # (127 car., lettres, chiffres, `. , _ -`) ; ClickBank `aff_sub1` (100 car.) — `tid`,
    # limité à 24, ne tient pas un video_id de 28.
    "digistore24": ("campaignkey", 127),
    "clickbank": ("aff_sub1", 100),
}

#: Réseaux dont le sous-identifiant est un segment de chemin, pas un paramètre de requête.
SUBID_EN_CHEMIN: frozenset[str] = frozenset({"digistore24"})

#: Jetons admis dans `Product.sub_id_format` — aucun ne porte de donnée personnelle.
JETONS_SUBID: frozenset[str] = frozenset({"video_id", "channel_id", "lang"})


def licence_commerciale(licence: str) -> bool:
    """Vrai si la licence autorise l'usage commercial (toute mention « NC » est éliminatoire)."""
    jetons = {j for j in licence.upper().replace("_", "-").replace(" ", "-").split("-") if j}
    return "NC" not in jetons and "NONCOMMERCIAL" not in licence.upper().replace(" ", "")


# --------------------------------------------------------------------------------------
# Socles
# --------------------------------------------------------------------------------------


class Modele(BaseModel):
    """Socle commun : aucune clé inconnue n'est tolérée."""

    model_config = ConfigDict(extra="forbid")


class ModeleRacine(Modele):
    """Modèle racine d'un fichier : porte `schema_version` (INTERFACES § 0)."""

    schema_version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+$")] = SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def _majeure_compatible(cls, valeur: str) -> str:
        majeure = int(valeur.split(".")[0])
        if majeure != MAJEURE_ATTENDUE:
            raise ValueError(
                f"schema_version {valeur} : majeure {majeure} incompatible avec "
                f"{MAJEURE_ATTENDUE}.x attendue par ce code"
            )
        return valeur

    def mineure_inferieure(self) -> bool:
        """Vrai si le fichier est d'une mineure plus ancienne : accepté, mais à signaler."""
        return int(self.schema_version.split(".")[1]) < int(SCHEMA_VERSION.split(".")[1])


# --------------------------------------------------------------------------------------
# Configuration — langues
# --------------------------------------------------------------------------------------


class Voice(Modele):
    """Une voix de synthèse, déclarée par la langue qui la porte."""

    id: Identifiant
    engine: MoteurTts
    gender: Genre
    native: bool
    note_ecoute: str | None = None


class VoiceProfile(ModeleRacine):
    """`config/voices/<id>.yaml` — profil de voix d'une chaîne (étape 29).

    La langue déclare les voix disponibles ; le profil fixe **comment** une chaîne parle :
    locuteur du moteur, vitesse et hauteur propres, référence WAV éventuelle. Une référence
    n'est admise qu'avec ses droits écrits ici et consignés dans `outils/LICENCES.md`.
    """

    id: Identifiant
    engine: MoteurTts
    #: Identifiant du locuteur côté moteur (`spk_id` de Qwen3-TTS, nom Kokoro…).
    speaker: str = Field(min_length=1)
    lang: LangCode
    gender: Genre
    #: Multiplié par `languages/<lang>.yaml → tts.speed` (atempo, le TTS n'a pas de débit).
    speed: float = Field(default=1.0, ge=0.8, le=1.25)
    #: Décalage de hauteur en demi-tons, appliqué après la synthèse. 0 = inchangé.
    pitch_semitones: float = Field(default=0.0, ge=-3.0, le=3.0)
    reference_wav: str | None = None
    reference_rights: str | None = None
    note_ecoute: str | None = None

    @model_validator(mode="after")
    def _droits_de_reference(self) -> VoiceProfile:
        if self.reference_wav and not (self.reference_rights or "").strip():
            raise ValueError("reference_wav sans reference_rights : droits de la voix non consignés")
        return self


class Typographie(Modele):
    """Règles typographiques de la langue."""

    espace_avant_double_ponctuation: bool
    guillemets: list[str] = Field(min_length=2, max_length=2)
    majuscules_titre: Literal["title_case", "phrase_case", "upper_case"]


class Nombres(Modele):
    """Écriture des nombres, des dates et des unités."""

    decimal: str
    milliers: str
    pourcent: str
    date: str
    unites: Literal["metric", "imperial_first"]


class Disclosure(Modele):
    """Mentions de divulgation. Ce bloc ne se traduit pas librement (CONFORMITE § 3)."""

    amazon: str
    impact: list[str] = Field(min_length=1)
    awin: list[str] = Field(min_length=1)
    overlay_generic: str
    virtual_images: str
    #: Divulgation de production assistée par IA, en description (CONFORMITE § 3 couche 1 :
    #: l'assistance de production n'oblige pas `containsSyntheticMedia`, mais la dire est le
    #: seul moyen de tenir la couche 3 sans attendre le cas réaliste).
    ia_production: str = ""
    #: Clause ajoutée à la ligne précédente **uniquement** quand un humain nommé a relu
    #: (exception éditoriale du RIA art. 50). Sous `auto-approve`, elle ne s'écrit pas.
    ia_controle_humain: str = ""

    def pour_reseau(self, reseau: str) -> str:
        """Ligne de divulgation à employer pour ce réseau ; repli sur la mention générique."""
        if reseau == "amazon":
            return self.amazon
        if reseau == "impact":
            return self.impact[0]
        if reseau == "awin":
            return self.awin[0]
        return self.overlay_generic


class PausesTts(Modele):
    """Respirations de la charte, en millisecondes, insérées à la concaténation de la voix."""

    entre_segments_ms: int = Field(default=350, ge=0, le=3000)
    apres_hook_ms: int = Field(default=600, ge=0, le=3000)
    avant_sponsor_ms: int = Field(default=250, ge=0, le=3000)


class ConfigTts(Modele):
    """Paramètres de synthèse d'une langue. La voix, elle, est une propriété de la chaîne."""

    # Le modèle retenu n'expose aucun paramètre de vitesse : elle est appliquée après coup
    # par `atempo` (ffmpeg), qui ne touche pas à la hauteur. 1,0 = vitesse native du TTS.
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pauses_ms: PausesTts = Field(default_factory=PausesTts)
    # Longueur minimale d'une unité de synthèse : sous ce seuil, le régime nominal est le
    # régime dégradé (ARCHITECTURE § 2.2, mesures de l'étape 7).
    min_segment_s: float = Field(default=15.0, ge=0.0, le=60.0)
    silence_threshold_db: float = Field(default=-45.0, le=0.0)


class ConfigAsr(Modele):
    """Moteurs de transcription et seuils de WER par longueur de segment (étape 7)."""

    primary: MoteurAsr
    fallback: MoteurAsr
    wer_thresholds: dict[str, float] = Field(min_length=1)

    @field_validator("wer_thresholds")
    @classmethod
    def _bornes_entieres(cls, valeur: dict[str, float]) -> dict[str, float]:
        for borne, seuil in valeur.items():
            if not borne.isdigit():
                raise ValueError(f"wer_thresholds : borne « {borne} » non entière")
            if not 0.0 < seuil <= 1.0:
                raise ValueError(f"wer_thresholds[{borne}] = {seuil} hors ]0, 1]")
        return valeur

    def seuil(self, nb_mots: int) -> float:
        """Seuil de WER applicable à un segment de `nb_mots` mots."""
        for borne in sorted(self.wer_thresholds, key=int):
            if nb_mots <= int(borne):
                return self.wer_thresholds[borne]
        return min(self.wer_thresholds.values())


class LibellesDescription(Modele):
    """Les intitulés des blocs de description, **dans la langue de la vidéo**.

    Ils étaient en dur, donc en français, y compris sur une chaîne anglophone : la description
    du run `avwf` sortait « Sources : » et « Crédits : » sous un texte anglais (constaté le
    20/09/2026). Un intitulé est du vocabulaire ; il appartient à la langue, comme les mentions
    de divulgation et les mots interdits.
    """

    sources: str = "Sources"
    credits: str = "Credits"
    #: Ligne de crédit des images générées sur la machine. Elles portent la licence du modèle,
    #: qui n'exige aucun crédit — la dire coûte une ligne et documente la provenance
    #: (RIA art. 50, C2PA § 4). Le nom du modèle est ajouté après.
    generated_locally: str = "Illustrations generated locally"


class TitresLangue(Modele):
    """Ce qu'une langue impose aux titres. Les mots interdits sont du vocabulaire, pas du code.

    La politique « spam, pratiques trompeuses et arnaques » de YouTube vise les métadonnées
    qui promettent ce que la vidéo ne tient pas. La liste ci-dessous est une **heuristique de
    production** (étape 13.2), pas une citation de la politique : elle écarte les formules
    d'appât les plus reconnaissables avant qu'un humain ait à les lire.
    """

    mots_interdits: list[str] = Field(default_factory=list)
    #: Question d'engagement de repli pour le commentaire épinglé, **dans cette langue**.
    #: Employée seulement quand le script n'en porte aucune (ni segment `cta` interrogatif,
    #: ni hook interrogatif) : une question écrite par le script parle de la vidéo, celle-ci
    #: ne parle que du format. Vide = pas de commentaire épinglé, ce qui est un choix
    #: acceptable et non un défaut.
    question_engagement: str = ""
    #: Mots de curiosité, **dans cette langue**, rangés par niche. La clé `_defaut` vaut pour
    #: toutes les niches ; une clé de niche s'y ajoute, elle ne la remplace pas. Le lexique
    #: appartient à la langue (c'est du vocabulaire), le découpage appartient à la niche
    #: (« scientists » ne curiosifie rien en true crime). Aucune liste en dur dans le code.
    mots_curiosite: dict[str, list[str]] = Field(default_factory=dict)

    def curiosite(self, niche: str) -> list[str]:
        """Mots de curiosité applicables à une niche : le défaut, puis les siens."""
        return list(self.mots_curiosite.get("_defaut", [])) + list(
            self.mots_curiosite.get(niche, [])
        )


class TermeGlossaire(Modele):
    """Un terme imposé à l'adaptation (étape 24). `cible` vide = ne pas traduire."""

    source: str = Field(min_length=1)
    cible: str = ""
    note: str | None = None


class LocalisationLangue(Modele):
    """Ce qu'une déclinaison doit respecter pour être écrite **dans** cette langue (étape 24)."""

    #: Consignes d'adaptation (unités, dates, devises, références), en anglais pour le LLM.
    consignes: list[str] = Field(default_factory=list)
    #: Glossaire par niche ; la clé `_defaut` vaut pour toutes.
    glossaire: dict[str, list[TermeGlossaire]] = Field(default_factory=dict)
    #: Rapport de longueur attendu (mots cible ÷ mots source) quand la source est dans la clé.
    rapport_longueur: dict[str, float] = Field(default_factory=dict)


class Language(ModeleRacine):
    """`config/languages/<code>.yaml` — tout ce qui empêche une langue de fuir dans une autre."""

    code: LangCode
    name: str
    voices: list[Voice] = Field(min_length=1)
    typographie: Typographie
    nombres: Nombres
    disclosure: Disclosure
    titres: TitresLangue = Field(default_factory=TitresLangue)
    libelles: LibellesDescription = Field(default_factory=LibellesDescription)
    tts: ConfigTts = Field(default_factory=ConfigTts)
    asr: ConfigAsr
    localisation: LocalisationLangue = Field(default_factory=LocalisationLangue)

    @model_validator(mode="after")
    def _voix_uniques(self) -> Language:
        ids = [v.id for v in self.voices]
        if len(ids) != len(set(ids)):
            raise ValueError(f"voix en double dans la langue {self.code}")
        return self

    def voix(self, voice_id: str) -> Voice | None:
        """Retourne la voix d'identifiant donné, ou None."""
        return next((v for v in self.voices if v.id == voice_id), None)


# --------------------------------------------------------------------------------------
# Configuration — niches
# --------------------------------------------------------------------------------------


class RythmeCoupe(Modele):
    """Rythme de coupe visé, en secondes par plan (registre, étape 3)."""

    cible: float | None = None
    cible_montage: float | None = None
    min: float | None = None
    max: float | None = None
    facteur_hook: float = 0.7
    n: int = 0
    a_mesurer: bool = False
    fallback_provisoire_s: float | None = None

    @model_validator(mode="after")
    def _une_valeur_utilisable(self) -> RythmeCoupe:
        if self.cible is None and not self.a_mesurer:
            raise ValueError("rythme_coupe_s : cible absente sans a_mesurer: true")
        if self.a_mesurer and self.fallback_provisoire_s is None:
            raise ValueError("rythme_coupe_s : a_mesurer sans fallback_provisoire_s")
        return self

    def cible_effective(self) -> float:
        """Cible de montage, repli sur la cible, repli sur la valeur de secours (spec.json)."""
        for valeur in (self.cible_montage, self.cible, self.fallback_provisoire_s):
            if valeur is not None:
                return valeur
        raise ValueError("rythme_coupe_s : aucune valeur utilisable")


class DureeCible(Modele):
    """Durée visée, en secondes."""

    cible: int = Field(gt=0)
    p25: float | None = None
    p75: float | None = None
    tolerance: float = Field(default=0.15, gt=0, lt=1)
    distribution_large: bool = False


class MotsParMinute(Modele):
    """Débit de parole médian de la niche."""

    mediane: float = Field(gt=0)
    n: int = 0


class HooksCible(Modele):
    """Répartition des types de hook et exigence de boucles ouvertes."""

    parts: dict[str, float] = Field(default_factory=dict)
    boucles_minimum: int = Field(default=2, ge=2)
    boucle_position_s_repli: float | None = None


class LongueurTitre(Modele):
    """Longueurs de titre observées et plafonds."""

    mediane: float
    p90: float
    plafond_recommande: float
    plafond_youtube: int = 100


class TitresCible(Modele):
    """Cibles de titre de la niche."""

    longueur_car: LongueurTitre


class MiniaturesCible(Modele):
    """Cibles de miniature de la niche."""

    mots_texte_median: float
    part_visage: float = Field(ge=0, le=1)
    contraste_ratio_cible: float = 4.5


class CadenceNiche(Modele):
    """Cadence de publication observée dans la niche (jamais une autorisation)."""

    mediane: float = Field(ge=0)
    cible: float = Field(ge=0)


class Surcharge(Modele):
    """Une surcharge assumée d'une cible du référentiel — jamais une valeur sans motif."""

    champ: str
    valeur: Any
    motif: str = Field(min_length=10)
    date: str
    qui: str


class MusiqueNiche(Modele):
    """Ambiance du lit musical de la niche — le choix de piste part d'ici, pas d'un titre."""

    mood: Mood = "curieux"


class DensiteCible(Modele):
    """Densité d'information visée, mesurée à l'étape 16 sur les transcriptions du registre.

    `cible` est la **médiane des meilleures vidéos de la niche** ; `mediane_observee` celle
    des vidéos médianes de la même niche, conservée pour que l'écart reste lisible. `origine`
    dit sur quoi la valeur a été mesurée — sans quoi un chiffre n'est qu'une opinion.
    """

    cible: float | None = Field(default=None, gt=0)
    #: Densité sous laquelle le run est refusé. Distincte de `cible` : voir
    #: `factory/retention/density.plancher` pour le motif.
    plancher: float | None = Field(default=None, gt=0)
    mediane_observee: float | None = Field(default=None, ge=0)
    n_meilleures: int = 0
    n_medianes: int = 0
    origine: str = ""
    n_faible: bool = False


class RupturesCible(Modele):
    """Cadence des ruptures de sujet observée sur le corpus (étape 16).

    La cadence **appliquée** reste `4 × rythme_coupe_s.cible_montage`, bornée à [20, 45] s
    (`factory/retention/interrupts.py`) : c'est une décision de production. La valeur mesurée
    ci-dessous sert à dire de combien la production s'écarte de l'usage observé.
    """

    observee_s: float | None = Field(default=None, gt=0)
    p25_s: float | None = Field(default=None, gt=0)
    p75_s: float | None = Field(default=None, gt=0)
    n: int = 0
    origine: str = ""


class Niche(ModeleRacine):
    """`config/niches/<id>.yaml` — copie lisible des cibles de `registre/REFERENTIEL.json`."""

    id: Identifiant
    musique: MusiqueNiche = Field(default_factory=MusiqueNiche)
    rythme_coupe_s: RythmeCoupe
    duree_s: DureeCible
    mots_par_minute: MotsParMinute
    hooks: HooksCible
    #: Étape 16 : cible de densité d'information et cadence de rupture observée.
    densite_faits_par_minute: DensiteCible = Field(default_factory=DensiteCible)
    ruptures_s: RupturesCible = Field(default_factory=RupturesCible)
    titres: TitresCible
    miniatures: MiniaturesCible
    cadence_par_semaine: CadenceNiche
    surcharges: list[Surcharge] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Configuration — styles
# --------------------------------------------------------------------------------------


class Style(ModeleRacine):
    """`config/styles/<id>.yaml` — sélectionne un moteur ; aucun `if style == …` dans le code."""

    id: Identifiant
    engine: Identifiant
    backend: Backend
    statut: StatutStyle
    templates: list[Identifiant] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)

    @property
    def executable(self) -> bool:
        """Vrai si le moteur est livré ; un style `planifie` est validé mais non exécutable."""
        return self.statut in {"retenu_v1", "retenu_v2"}


# --------------------------------------------------------------------------------------
# Configuration — produits d'affiliation
# --------------------------------------------------------------------------------------


class LignesDivulgation(Modele):
    """Les trois lignes de divulgation d'une langue (CONFORMITE § 3)."""

    description_line: str = Field(min_length=1)
    overlay_text: str = Field(min_length=1)
    spoken_line: str = Field(min_length=1)


class SegmentCta(Modele):
    """Emplacement et durée du segment d'appel à l'action."""

    role: Role = "sponsor"
    position: Literal[
        "apres_hook", "apres_premier_point", "fin", "apres_conclusion"
    ] = "apres_premier_point"
    duree_s_max: float = Field(default=45.0, gt=0)


class CommissionIndicative(Modele):
    """Ordre de grandeur de commission, toujours sourcé ; jamais employé dans un calcul."""

    valeur: str = Field(min_length=1)
    source: str = Field(min_length=1)


class Product(ModeleRacine):
    """`config/products/<id>.yaml` — un produit d'affiliation, jamais une constante de code.

    Étape 27 : les clés `program`, `base_url`, `tracking_param` et `disclosure` sont acceptées
    comme synonymes de `network`, `target_url`, `subid_param` et `disclosure_override` (noms de
    l'étape 21, conservés par le code, les tests et le précontrôle).
    """

    id: Identifiant
    name: str
    network: Reseau = Field(validation_alias=AliasChoices("network", "program"))
    tracking_id: str = Field(min_length=1)
    subid_param: str | None = Field(
        default=None, validation_alias=AliasChoices("subid_param", "tracking_param"))
    subid_max_len: int | None = None
    #: `{video_id}` suffit : le video_id porte déjà la chaîne et la langue.
    sub_id_format: str = "{channel_id}_{lang}_{video_id}"
    target_url: str = Field(pattern=r"^https://",
                            validation_alias=AliasChoices("target_url", "base_url"))
    attribution_par_video: bool
    cookie_window_days: int = Field(gt=0)
    disclosure_override: dict[str, LignesDivulgation] = Field(
        default_factory=dict, validation_alias=AliasChoices("disclosure_override", "disclosure"))
    #: Phrase d'appel à l'action par langue, reprise dans le segment sponsor et en description.
    cta_text: dict[str, str] = Field(default_factory=dict)
    landing_type: Literal["product_page", "sales_page", "review", "lead_capture"] | None = None
    commission_hint: CommissionIndicative | None = None
    cta_segment: SegmentCta = Field(default_factory=SegmentCta)

    @model_validator(mode="after")
    def _contraintes_reseau(self) -> Product:
        param, longueur = SUBID_PAR_RESEAU[self.network]
        if self.subid_param != param or self.subid_max_len != longueur:
            raise ValueError(
                f"réseau {self.network} : subid_param attendu {param!r} "
                f"et subid_max_len {longueur} (CONFORMITE § 10.4), "
                f"trouvé {self.subid_param!r} et {self.subid_max_len}"
            )
        if self.network == "amazon" and self.attribution_par_video:
            raise ValueError(
                "amazon : attribution_par_video doit être false "
                "(ascsubtag sur accord d'Amazon seulement ; suivi par tracking ID)"
            )
        jetons = set(re.findall(r"\{(\w+)\}", self.sub_id_format))
        if "video_id" not in jetons or not jetons <= JETONS_SUBID:
            raise ValueError(
                f"sub_id_format {self.sub_id_format!r} : {{video_id}} obligatoire, "
                f"jetons admis {sorted(JETONS_SUBID)}"
            )
        return self

    def subid(self, channel_id: str, lang: str, video_id: str) -> str | None:
        """Sous-identifiant selon `sub_id_format` ; None sans attribution par vidéo (Amazon).

        Un sous-identifiant trop long ou hors de `[A-Za-z0-9_-]` lève une erreur : tronqué, il
        perdrait la fin du video_id et attribuerait les conversions à la mauvaise vidéo.
        """
        if not self.attribution_par_video or self.subid_max_len is None:
            return None
        valeur = self.sub_id_format.format(channel_id=channel_id, lang=lang, video_id=video_id)
        if len(valeur) > self.subid_max_len or not re.fullmatch(r"[A-Za-z0-9_-]+", valeur):
            raise ValueError(
                f"{self.id} : sous-identifiant {valeur!r} invalide pour {self.network} "
                f"({len(valeur)} car., {self.subid_max_len} au maximum, [A-Za-z0-9_-])"
            )
        return valeur


# --------------------------------------------------------------------------------------
# Configuration — chaînes
# --------------------------------------------------------------------------------------


class Polices(Modele):
    """Polices de la charte."""

    title: str
    body: str


class Palette(Modele):
    """Palette de la charte."""

    bg: Couleur
    text: Couleur
    text_outline: Couleur
    accent: Couleur
    highlight: Couleur


class SousTitresCharte(Modele):
    """Style des sous-titres : lu dans la charte, jamais en dur dans le moteur."""

    align: Literal["bottom_center", "bottom_left", "middle_center"] = "bottom_center"
    margin_v_px: int = Field(default=96, ge=0)
    size_px: int = Field(default=64, gt=0)
    max_chars_per_line: int = Field(default=38, gt=0)
    max_lines: int = Field(default=2, ge=1, le=3)
    karaoke: bool = True
    burn_in: bool = False
    font: str | None = None
    weight: str | None = None


class Cadrage(Modele):
    """Cadrage : la parade mesurée à la dérive d'identité et de cadre (étape 5.2, § 2.11).

    `background` et `subject_scale` viennent du constat (i) de l'étape 5.2 : sur 8 plans d'une
    même vidéo, **un plan était encadré d'une marge quand les autres allaient au bord**. Un
    cadrage laissé au modèle change d'un plan à l'autre ; écrit dans la charte, il ne change pas.
    """

    person_shots: Literal["bust_only", "full_body_allowed"] = "bust_only"
    prefer: list[str] = Field(default_factory=list)
    #: Traitement du fond, en mots employables dans un prompt d'image.
    background: str = ""
    #: Part du cadre qu'occupe le sujet, en mots employables dans un prompt d'image.
    subject_scale: str = ""


class MiniatureCharte(Modele):
    """Ce que la charte impose à la miniature. Deux gabarits au moins, en rotation (§ 5)."""

    #: Casse du texte incrusté. Le référentiel mesure des textes de 0 à 4 mots, pas leur casse :
    #: c'est donc une décision de charte, pas une mesure.
    uppercase: bool = True
    #: Gabarits de composition, tirés par la graine du run. ≥ 2 : une chaîne qui sort toujours
    #: la même image de miniature se signale d'elle-même (CONFORMITE § 5, anti-clonage).
    templates: list[Literal["bandeau_bas", "bloc_gauche"]] = Field(
        default_factory=lambda: ["bandeau_bas", "bloc_gauche"], min_length=2
    )
    #: Part de la hauteur de l'image que doit atteindre le texte incrusté. Contrôle de l'étape
    #: 13.2 : sous ce seuil, le texte n'est plus lisible sur une vignette de téléphone.
    hauteur_texte_min: float = Field(default=0.12, gt=0, lt=1)
    #: Assombrissement du fond, sans quoi aucun contraste de texte n'est tenable.
    fond_luminosite: float = Field(default=0.52, gt=0, le=1)


class Gabarit(Modele):
    """Gabarit de mise en page d'une charte (étape 29) : ≥ 3 par chaîne, en rotation (§ 5).

    Ce que le gabarit change se voit : position du texte à l'écran, présence du souligné,
    position et taille de l'avatar incrusté. Le style d'image, lui, reste celui de la charte.
    """

    description: str = ""
    text_anchor: Literal["bottom_center", "bottom_left", "top_left", "top_center"] = "bottom_center"
    accent_bar: bool = True
    avatar_anchor: Literal["bottom_right", "bottom_left", "top_right", "top_left"] = "bottom_right"
    #: Hauteur de l'avatar incrusté, en part de la hauteur du cadre.
    avatar_scale: float = Field(default=0.45, ge=0.2, le=1.0)


class Charte(Modele):
    """Identité visuelle d'une chaîne, versionnée pour que la boucle sache l'attribuer.

    `style_prefix` et `style_suffix` encadrent l'intention visuelle d'un plan pour former le
    prompt d'image (`factory/assets/images.py`). Ils sont **vides par défaut** : une chaîne dont
    le style ne génère aucun pixel (moteur « cartes ») n'en a pas besoin, et un moteur qui en a
    besoin refuse de tourner sans eux plutôt que d'inventer un style en dur.
    """

    version: str
    fonts: Polices
    palette: Palette
    transitions: list[Transition] = Field(min_length=1)
    #: Durée d'un fondu, en secondes. Bornée à [0,25 ; 0,40] par le prompt de l'étape 13.1 : en
    #: deçà le fondu ne se voit pas, au-delà il se substitue au plan. Une coupe franche ne
    #: consomme rien ; un fondu, lui, doit être payé en images — voir `factory/steps/assemble.py`.
    transition_duration_s: float = Field(default=0.32, ge=0.25, le=0.40)
    subtitles: SousTitresCharte = Field(default_factory=SousTitresCharte)
    thumbnail: MiniatureCharte = Field(default_factory=MiniatureCharte)
    framing: Cadrage = Field(default_factory=Cadrage)
    #: Style graphique imposé à toutes les images de la chaîne — le premier levier de cohérence.
    style_prefix: str = ""
    #: Palette en mots, interdiction de texte, tokens de cohérence — refermé après l'intention.
    style_suffix: str = ""
    #: Ce qu'aucune image de la chaîne ne doit contenir. Ignoré si le modèle ne le supporte pas ;
    #: le champ existe pour que la charte reste le seul endroit où cela se décide.
    negative_prompt: str = ""
    #: Gabarits de mise en page par identifiant (`config/chartes/<channel>.yaml`, étape 29).
    layouts: dict[Identifiant, Gabarit] = Field(default_factory=dict)
    #: Intro et outro de la bibliothèque (`workspace/library/intros/…`), relatifs à la racine.
    intro: str | None = None
    outro: str | None = None


class Cadence(Modele):
    """Cadence de publication d'une chaîne (CONFORMITE § 6)."""

    per_week_max: int = Field(default=2, ge=1, le=2)
    days: list[Jour] = Field(min_length=1)
    hours_local: list[HeureLocale] = Field(min_length=1)
    #: Demi-largeur du jitter, en minutes : ± `jitter_min` autour du créneau. 90 = fenêtre de
    #: 3 h, le minimum que CONFORMITE § 6 appelle « plusieurs heures ».
    jitter_min: int = Field(default=90, ge=90)
    timezone: str
    #: Date de création (ou de première publication) de la chaîne. `None` = chaîne neuve :
    #: le plafond des 90 premiers jours s'applique (CONFORMITE § 6).
    created_at: DateJour | None = None

    @field_validator("timezone")
    @classmethod
    def _fuseau_connu(cls, valeur: str) -> str:
        try:
            ZoneInfo(valeur)
        except (ZoneInfoNotFoundError, ValueError) as erreur:
            raise ValueError(f"fuseau horaire inconnu : {valeur}") from erreur
        return valeur

    @model_validator(mode="after")
    def _jours_uniques(self) -> Cadence:
        if len(self.days) != len(set(self.days)):
            raise ValueError("cadence.days : jour en double")
        if len(self.days) < self.per_week_max:
            raise ValueError(
                f"cadence : {len(self.days)} jour(s) déclaré(s) pour per_week_max="
                f"{self.per_week_max}"
            )
        return self


class CompteGoogle(Modele):
    """Compte de publication. Aucune valeur de secret : seulement une référence."""

    alias: Identifiant
    brand_account: str
    owner: str = "BMS"
    gcp_project: Identifiant
    token_ref: str = Field(pattern=r"^secrets/[\w./-]+\.json$")
    two_fa_enabled: bool = False
    phone_verified: bool = False


class ConfigYoutube(Modele):
    """État côté YouTube : tant que l'audit n'est pas obtenu, la publication reste manuelle."""

    audit_passed: bool = False
    channel_id: str | None = None
    playlist_id: str | None = None
    captions_upload: bool = True
    #: Catégorie YouTube de la fiche (`snippet.categoryId`) — 28 Science, 27 Éducation,
    #: 22 People & Blogs. Par chaîne, jamais déduite du code.
    category_id: str = Field(default="22", pattern=r"^\d{1,2}$")
    #: `notifySubscribers` de `videos.insert` : une chaîne qui rattrape un retard de
    #: publication ne doit pas notifier quatre fois dans la journée.
    notify_subscribers: bool = True


class ConfigBibliotheque(Modele):
    """Anti-répétition d'asset sur une même chaîne."""

    cooldown_videos: int = Field(default=10, ge=0)
    max_uses_per_channel: int = Field(default=3, ge=1)
    #: Réemploi sémantique (étape 29) : cosinus **centré** e5 au-delà duquel un asset existant
    #: sert une intention voisine sans génération. 0,9 = paraphrases du même sujet (mesuré).
    semantic_threshold: float = Field(default=0.9, gt=0, le=1)


class TraductionChaine(Modele):
    """Titre et description d'une vidéo dans une autre langue — relus, jamais traduits ici."""

    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)


class Channel(ModeleRacine):
    """`config/channels/<id>.yaml` — le seul endroit où une chaîne existe."""

    id: Identifiant
    name: str
    lang: LangCode
    niche: Identifiant
    style: Identifiant
    templates: list[Identifiant] = Field(min_length=3)
    charte: Charte
    voice_id: Identifiant
    cadence: Cadence
    google_account: CompteGoogle
    products: list[Identifiant] = Field(default_factory=list)
    #: Titre et description traduits, par code de langue. **Vide aujourd'hui** : la langue de
    #: production est l'anglais seulement (arbitrage d'Alek, 15/09/2026) et l'étape 24 —
    #: déclinaison multilingue — est différée. Le champ existe pour que `seo.localizations()`
    #: lise une traduction relue plutôt que d'en inventer une au moment de publier.
    localizations: dict[LangCode, TraductionChaine] = Field(default_factory=dict)
    derive_from: Identifiant | None = None
    auto_approve: bool = False
    youtube: ConfigYoutube = Field(default_factory=ConfigYoutube)
    library: ConfigBibliotheque = Field(default_factory=ConfigBibliotheque)

    @model_validator(mode="after")
    def _coherence_interne(self) -> Channel:
        if len(set(self.templates)) != len(self.templates):
            raise ValueError("templates : gabarit en double (rotation ≥ 3, CONFORMITE § 5)")
        if self.charte.layouts:
            absents = [t for t in self.templates if t not in self.charte.layouts]
            if absents:
                raise ValueError(f"templates sans gabarit dans la charte : {', '.join(absents)}")
        if self.derive_from == self.id:
            raise ValueError("derive_from : une chaîne ne dérive pas d'elle-même")
        if self.charte.subtitles.burn_in and self.youtube.captions_upload:
            raise ValueError(
                "charte.subtitles.burn_in et youtube.captions_upload sont exclusifs : "
                "double affichage chez le spectateur et 400 unités de quota dépensées pour rien"
            )
        return self

    @property
    def paid_promotion(self) -> bool:
        """Un produit configuré implique la promotion payante, sans seuil (CONFORMITE § 3)."""
        return bool(self.products)

    @property
    def publish_path(self) -> str:
        """Tant que l'audit de l'API n'est pas obtenu, le chemin est manuel (CONFORMITE § 2)."""
        return "api_scheduled" if self.youtube.audit_passed else "manual_studio"


# --------------------------------------------------------------------------------------
# Configuration — équipe, qualité, éditorial, économie
# --------------------------------------------------------------------------------------


class Relecteur(Modele):
    """Un relecteur nommé : « l'équipe » n'est pas une réponse valable (CONFORMITE § 4)."""

    id: Identifiant
    nom: str
    role: Literal["developpeur", "proprietaire", "relecteur"]
    langues: list[LangCode] = Field(min_length=1)
    lots_par_semaine: int = Field(ge=0)


class TeamConfig(ModeleRacine):
    """`config/team.yaml`."""

    relecteurs: list[Relecteur] = Field(min_length=1)
    taille_lot: int = Field(default=5, ge=1)
    delai_max_heures: int = Field(default=48, gt=0)

    @model_validator(mode="after")
    def _identites_uniques(self) -> TeamConfig:
        ids = [r.id for r in self.relecteurs]
        if len(ids) != len(set(ids)):
            raise ValueError("team : relecteur en double")
        return self


class SeuilQc(Modele):
    """Paramètres d'une mesure du banc : sa cible, sa plage de note et son statut bloquant.

    `tolerance` et `plage` sont **relatives à la cible** (0,15 = 15 %) : le score partiel vaut
    100 dans la tolérance et tombe à 0 au bord de la plage (`factory/eval/base.py`).
    `poids` est le poids **dans sa famille** ; le poids de la famille au barème global est dans
    `QcConfig.poids`. `bloquant` sort le contrôle du barème : il fait échouer, il ne note pas.
    """

    cible: float | None = None
    min: float | None = None
    max: float | None = None
    tolerance: float | None = None
    plage: float | None = None
    zero: float | None = None
    #: Part maximale admise quand la mesure est un dénombrement rapporté à un total.
    zero_part: float | None = None
    #: Multiple de la cible au-delà duquel un plan est « trop long » (famille coupes).
    facteur_plan_long: float | None = None
    #: Part de la durée occupée par les plans « trop longs » : plafond, bloquant, et zéro.
    part_longue_max: float | None = None
    part_longue_bloquante: float | None = None
    part_longue_zero: float | None = None
    #: Plages propres à une sous-mesure, en multiples de sa cible.
    plage_hook: float | None = None
    plage_position: float | None = None
    poids: int = Field(default=1, ge=0)
    bloquant: bool = False
    source: str | None = None
    verdict_fail: VerdictQc | Literal["warn"] = "warn"


class SeuilsPrecheck(Modele):
    """Anti-clonage inter-chaînes (CONFORMITE § 5, contrôles 18-19). Distances de Hamming sur
    64 bits : **en dessous** du minimum, deux vidéos sont réputées la même."""

    script_simhash_distance_min: Annotated[int, Field(ge=1, le=32)] = 12
    thumbnail_phash_distance_min: Annotated[int, Field(ge=1, le=32)] = 10
    #: Durée minimale d'une vidéo longue publiable.
    duree_min_s: Annotated[float, Field(ge=60)] = 60.0


class QcConfig(ModeleRacine):
    """`config/qc.yaml` — barème du banc de l'étape 15.

    `poids` porte désormais les poids **par famille** (coupes, hook, audio…), et non plus par
    contrôle : le barème de `INTERFACES.md` § config/qc.yaml, écrit à l'étape 9, décrivait des
    contrôles isolés. Divergence consignée dans `INTERFACES.md` § 5 et dans `docs/QC.md`.
    """

    poids: dict[str, int] = Field(min_length=1)
    hors_bareme: list[str] = Field(default_factory=list)
    seuils: dict[str, SeuilQc] = Field(default_factory=dict)
    #: Paramètres d'outillage par famille (seuil PySceneDetect, seuil de silence, échantillons).
    mesure: dict[str, dict[str, Any]] = Field(default_factory=dict)
    #: Règles de hook vérifiables par script, par type du référentiel, et leurs lexiques.
    hooks: dict[str, Any] = Field(default_factory=dict)
    #: Ce que le banc ne couvre pas, recopié dans `qc.json` — le portillon déclare ses trous.
    non_couvert: list[str] = Field(default_factory=list)
    #: Surcharges par niche, fusionnées clé à clé sur le barème par défaut.
    surcharges_par_niche: dict[str, dict[str, Any]] = Field(default_factory=dict)
    score_minimal_pour_publier: int = Field(default=70, ge=0, le=100)
    #: Seuils de la checklist de pré-publication (étape 23.2, `factory precheck`).
    precheck: SeuilsPrecheck = Field(default_factory=lambda: SeuilsPrecheck())
    #: Aucune famille notée ne peut passer sous ce score, quel que soit le score global.
    plancher_par_famille: int = Field(default=0, ge=0, le=100)

    @model_validator(mode="after")
    def _bareme_disjoint(self) -> QcConfig:
        collision = set(self.poids) & set(self.hors_bareme)
        if collision:
            raise ValueError(f"qc : {sorted(collision)} à la fois noté et hors barème")
        return self


class FileSujets(Modele):
    """Paramètres de la file de sujets."""

    taille_max: int = Field(gt=0)
    score_minimal: float = Field(ge=0, le=1)
    age_max_jours: int = Field(gt=0)


class ConfigDedoublonnage(Modele):
    """Distances minimales de dédoublonnage — portée globale (CONFORMITE § 5)."""

    script_simhash_distance_min: int = Field(ge=1)
    thumbnail_phash_distance_min: int = Field(ge=1)
    portee: Literal["globale", "par_chaine"] = "globale"


class PonderationsNiche(Modele):
    """Poids du score composite (étape 19). Ils doivent totaliser 100."""

    demande: int = Field(gt=0)
    concurrence: int = Field(gt=0)
    monetisation: int = Field(gt=0)
    faisabilite: int = Field(gt=0)

    @model_validator(mode="after")
    def _total_cent(self) -> PonderationsNiche:
        total = self.demande + self.concurrence + self.monetisation + self.faisabilite
        if total != 100:
            raise ValueError(f"pondérations : total {total}, attendu 100")
        return self


class SousPonderationsDemande(Modele):
    niveau: float = Field(ge=0, le=1)
    tendance: float = Field(ge=0, le=1)
    autocomplete: float = Field(ge=0, le=1)


class SousPonderationsConcurrence(Modele):
    rarete_chaines: float = Field(ge=0, le=1)
    part_percees: float = Field(ge=0, le=1)
    #: Compte à l'envers : une vélocité médiane élevée = des chaînes en place qui
    #: captent déjà l'attention, donc une place plus chère.
    pression_velocite: float = Field(ge=0, le=1)


class ReglagesDemande(Modele):
    sous_ponderations: SousPonderationsDemande
    fenetre_mois: int = Field(gt=0, le=60)
    pente_bornee: float = Field(gt=0, le=1)
    r2_minimal: float = Field(ge=0, le=1)
    seuil_saison_nomme: float = Field(gt=1.0)


class ReglagesConcurrence(Modele):
    sous_ponderations: SousPonderationsConcurrence
    chaine_active_videos_par_semaine: float = Field(gt=0)
    fenetre_activite_jours: int = Field(gt=0)
    fenetre_velocite_jours: int = Field(gt=0)
    fenetre_percees_jours: int = Field(gt=0)
    seuil_percee_ratio: float = Field(gt=1)
    plancher_videos: int = Field(ge=0)
    plancher_chaines: int = Field(ge=0)


class PlafondSource(Modele):
    """Plafond d'appels d'une source de demande, et son statut."""

    max_appels_par_execution: int = Field(gt=0)
    source: str | None = None
    statut: str | None = None


class RegionAutocomplete(Modele):
    hl: str
    gl: str


class Objection(Modele):
    """Une objection du contradicteur et ce qu'elle a changé. Écartée, elle dit pourquoi."""

    probleme: str
    correction: str
    statut: str


class NicheScoring(Modele):
    """Paramètres de la notation des niches (étape 19)."""

    ponderations: PonderationsNiche
    demande: ReglagesDemande
    concurrence: ReglagesConcurrence
    wikimedia: PlafondSource
    autocomplete: PlafondSource
    autocomplete_regions: dict[str, RegionAutocomplete]
    #: Les biais du classement, énoncés avant lui. Une notation sans limites écrites
    #: se lit comme une mesure, ce qu'elle n'est pas.
    limites: list[str] = Field(min_length=1)
    objections: list[Objection] = Field(default_factory=list)


class BandeCPM(Modele):
    min: float | None = None
    max: float | None = None
    mediane: float | None = None
    unite: str | None = None


class ProgrammeAffiliation(Modele):
    reseau: str
    categorie: str
    taux: str
    url: str | None = None


class GrilleMonetisation(Modele):
    """Note de monétisation d'une (niche, langue) — subjective, donc ici et jamais dans le code."""

    note: int = Field(ge=1, le=5)
    resume: str
    cpm_bande_usd: BandeCPM | None = None
    cpm_source: str | None = None
    cpm_url: str | None = None
    cpm_date: str | None = None
    cpm_fiabilite: int | None = Field(default=None, ge=1, le=5)
    affiliation: list[ProgrammeAffiliation] = Field(default_factory=list)
    restrictions: str | None = None
    #: Porte éliminatoire : la niche est notée pour montrer ce qu'elle vaudrait, mais
    #: le rapport la marque et la sort du top. Un interdit n'est pas un score faible.
    eliminatoire: bool = False
    motif_eliminatoire: str | None = None
    decision_humaine: str | None = None

    @model_validator(mode="after")
    def _un_interdit_porte_son_motif(self) -> GrilleMonetisation:
        if self.eliminatoire and not self.motif_eliminatoire:
            raise ValueError("eliminatoire sans motif : un interdit doit être justifié")
        return self

    @model_validator(mode="after")
    def _une_bande_porte_sa_source(self) -> GrilleMonetisation:
        bande = self.cpm_bande_usd
        chiffree = bande is not None and any(
            v is not None for v in (bande.min, bande.max, bande.mediane)
        )
        if chiffree and not self.cpm_source:
            raise ValueError("bande de CPM sans source : un chiffre sans origine est inventé")
        return self


class GrilleFaisabilite(Modele):
    """Note de faisabilité d'une niche — styles réellement disponibles et sources libres."""

    note: int = Field(ge=1, le=5)
    resume: str
    styles: list[str] = Field(default_factory=list)
    detail: str | None = None
    sources_factuelles: str | None = None


class NicheNotee(Modele):
    """Une niche candidate au classement de l'étape 19."""

    origine: Literal["registre", "candidate"] = "registre"
    #: Étiquettes de `channels_watch` — recensement. Vide pour une niche candidate.
    labels_entrepot: list[str] = Field(default_factory=list)
    #: Motifs SQL `LIKE` sur les titres — proxy lexical, pour les niches candidates.
    filtre_titre: list[str] = Field(default_factory=list)
    seeds_wikipedia: list[str] = Field(min_length=1)
    mots_cles: list[str] = Field(min_length=1)
    justification: str | None = None
    monetisation: dict[str, GrilleMonetisation] = Field(default_factory=dict)
    faisabilite: GrilleFaisabilite | None = None

    @model_validator(mode="after")
    def _une_portee_au_moins(self) -> NicheNotee:
        if not self.labels_entrepot and not self.filtre_titre:
            raise ValueError("niche sans portée : ni labels_entrepot ni filtre_titre")
        if self.origine == "candidate" and not self.justification:
            raise ValueError("niche candidate sans justification tirée de l'entrepôt")
        return self


class ReglagesPercees(Modele):
    """Ce qui fait d'une vidéo une percée (étape 20)."""

    seuil_ratio: float = Field(gt=1.0)
    #: Fenêtre d'âge relative. Comparer une vidéo de 10 jours à une de 300 mesure l'âge.
    fenetre_age_relative: float = Field(gt=0.0, lt=1.0)
    #: Sous ce nombre de comparables la vidéo est **non notée**, pas « non percée ».
    min_comparables: int = Field(ge=2)
    preferer_dN: bool = True


class ReglagesRegroupement(Modele):
    """Seuil de distance du regroupement agglomératif (étape 20).

    Le plafond de 0,5 n'est pas décoratif : mesuré le 20/09/2026, `multilingual-e5-small`
    met **tout le corpus dans un seul cluster** dès 0,22. Un seuil trop haut ne produit pas
    un mauvais découpage, il produit un découpage unique et silencieux.
    """

    seuil_distance: float = Field(gt=0.0, lt=0.5)
    taille_min: int = Field(ge=2)
    reduction_dimension: bool = False


class TrouMultilingue(Modele):
    langues_source: list[str] = Field(min_length=1)
    langue_cible: str
    min_percees_source: int = Field(ge=1)
    max_videos_cible: int = Field(ge=0)


class TrouDemande(Modele):
    max_videos_recentes: int = Field(ge=1)
    fenetre_recente_jours: int = Field(gt=0)
    percentile_demande_min: float = Field(ge=0, le=100)


class TrouResurgence(Modele):
    age_median_min_jours: float = Field(gt=0)
    ratio_velocite_min: float = Field(gt=1.0)
    min_videos_recentes: int = Field(ge=1)


class ReglagesTrous(Modele):
    multilingue: TrouMultilingue
    demande: TrouDemande
    resurgence: TrouResurgence


class PonderationsSujet(Modele):
    """Les cinq composantes du score d'un sujet. Elles somment à 1,00."""

    force_cluster: float = Field(ge=0, le=1)
    velocite: float = Field(ge=0, le=1)
    lacune: float = Field(ge=0, le=1)
    demande: float = Field(ge=0, le=1)
    fit: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _somme_a_un(self) -> PonderationsSujet:
        total = (self.force_cluster + self.velocite + self.lacune
                 + self.demande + self.fit)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"les pondérations de sujet somment à {total}, attendu 1,00")
        return self


class BaremeLacune(Modele):
    multilingue: float = Field(ge=0, le=1)
    demande: float = Field(ge=0, le=1)
    resurgence: float = Field(ge=0, le=1)
    aucune: float = Field(ge=0, le=1)


class MalusSimilarite(Modele):
    """Seuil et poids du malus de répétition (étape 20).

    Le plancher de 0,85 vient d'une mesure : deux sujets **sans rapport** sont déjà à
    0,77-0,84 de cosinus avec ce modèle. Un seuil plus bas rejette tout, et `plan` retombe
    sur le référentiel sans que rien ne le signale — c'est arrivé le 20/09/2026 à 0,80.
    """

    seuil: float = Field(ge=0.85, lt=1.0)
    poids: float = Field(ge=0, le=1)


class TopicsScoring(Modele):
    """Paramètres des percées, du regroupement, des trous et de la file (étape 20)."""

    fenetre_jours: int = Field(gt=0)
    percees: ReglagesPercees
    regroupement: ReglagesRegroupement
    trous: ReglagesTrous
    ponderations: PonderationsSujet
    bareme_lacune: BaremeLacune
    malus_similarite: MalusSimilarite
    #: Au-delà, un sujet reprend un titre de concurrent (`CONFORMITE` § 4-5).
    reformulation_seuil: float = Field(ge=0.9, le=1.0)
    clusters_libelles: int = Field(gt=0)
    clusters_angles: int = Field(gt=0)
    lot_libelles: int = Field(gt=0)
    lot_angles: int = Field(gt=0)
    types_angle: list[str] = Field(min_length=2)

    @model_validator(mode="after")
    def _la_resurgence_doit_etre_atteignable(self) -> TopicsScoring:
        """Un seuil d'âge au-delà de la fenêtre rend le critère toujours faux, en silence.

        Défaut réel : `age_median_min_jours: 365` sur une fenêtre de 180 jours (20/09/2026).
        """
        if self.trous.resurgence.age_median_min_jours >= self.fenetre_jours:
            raise ValueError(
                f"trous.resurgence.age_median_min_jours "
                f"({self.trous.resurgence.age_median_min_jours}) ≥ fenetre_jours "
                f"({self.fenetre_jours}) : aucun cluster ne peut l'atteindre"
            )
        if self.trous.demande.fenetre_recente_jours >= self.fenetre_jours:
            raise ValueError(
                f"trous.demande.fenetre_recente_jours "
                f"({self.trous.demande.fenetre_recente_jours}) ≥ fenetre_jours "
                f"({self.fenetre_jours}) : « peu de vidéos récentes » deviendrait "
                "« petit cluster »"
            )
        return self


class ApprentissageConfig(Modele):
    """`config/editorial.yaml → apprentissage` (étape 26) : seuils de `factory learn`."""

    n_min_par_niveau: int = Field(default=8, ge=2)
    prob_min_action: float = Field(default=0.95, gt=0.5, lt=1)
    multiplicateur_min: float = Field(default=0.7, gt=0, le=1)
    multiplicateur_max: float = Field(default=1.4, ge=1, le=2)
    rythme_ajustement_max: float = Field(default=0.20, ge=0, le=0.5)
    n_min_chaine_mediane: int = Field(default=3, ge=1)
    n_min_regle_retention: int = Field(default=6, ge=2)
    n_min_banc: int = Field(default=30, ge=5)
    thompson_force_prior: float = Field(default=200.0, gt=0)
    ctr_prior_defaut: float = Field(default=0.04, gt=0, lt=1)
    facteurs_geles: list[str] = Field(default_factory=list)
    n_min_global: int = Field(default=30, ge=1)
    n_min_chaines: int = Field(default=3, ge=1)
    n_min_par_chaine: int = Field(default=5, ge=1)
    tendance_max: float = Field(default=0.10, ge=0)


class EditorialConfig(ModeleRacine):
    """`config/editorial.yaml`."""

    topics_queue: FileSujets
    dedupe: ConfigDedoublonnage
    angles_autorises: list[AngleEditorial] = Field(min_length=1)
    sources_blanches: list[str] = Field(min_length=1)
    purge_cache_api_jours: int = Field(default=30, gt=0, le=30)
    niche_scoring: NicheScoring | None = None
    niches_notees: dict[str, NicheNotee] = Field(default_factory=dict)
    topics: TopicsScoring | None = None
    apprentissage: ApprentissageConfig | None = None


class ValeurSourcee(Modele):
    """Une valeur économique qui porte son origine, ou son absence de mesure."""

    valeur: float | None = None
    source: str | None = None
    date: str | None = None
    a_mesurer: bool = False
    note: str | None = None
    #: Valeur employée tant que `valeur` est nulle. Elle ne remplace pas la mesure : le
    #: drapeau `a_mesurer` reste vrai et le coût calculé avec elle porte le même drapeau.
    defaut: float | None = None

    @model_validator(mode="after")
    def _pas_de_valeur_inventee(self) -> ValeurSourcee:
        if self.defaut is not None and not self.note:
            raise ValueError("defaut : une valeur de repli sans note est une valeur inventée")
        if self.valeur is None and not self.a_mesurer:
            raise ValueError("valeur absente sans a_mesurer: true")
        if self.valeur is not None and not (self.source or self.note):
            raise ValueError("valeur sans origine : source ou note obligatoire")
        return self


class EconomicsConfig(ModeleRacine):
    """`config/economics.yaml` — aucune de ces valeurs n'est mesurée aujourd'hui."""

    tarif_kwh_eur: ValeurSourcee
    puissance_moyenne_w: ValeurSourcee
    cout_horaire_relecture_eur: ValeurSourcee
    # Étape 27 — économie unitaire (`factory economics`). Optionnels : absents, le rapport le dit.
    relecture_forfait_min: ValeurSourcee | None = None
    couts_fixes_mensuels_eur: ValeurSourcee | None = None
    amortissement_materiel_mensuel_eur: ValeurSourcee | None = None
    #: Scénario « serveur GPU » : coût mensuel envisagé, jamais imputé aux vidéos d'aujourd'hui.
    serveur_gpu_mensuel_eur: ValeurSourcee | None = None
    #: Taux de conversion vers l'euro, par devise ISO (`USD`, `GBP`…).
    taux_eur: dict[str, ValeurSourcee] = Field(default_factory=dict)
    horizon_retour_jours: int = Field(default=30, gt=0)

    @staticmethod
    def _effective(valeur: ValeurSourcee, repli: float) -> tuple[float, bool]:
        """Valeur employable et drapeau « estimée » : mesurée, de repli configuré, ou de code."""
        if valeur.valeur is not None:
            return float(valeur.valeur), False
        if valeur.defaut is not None:
            return float(valeur.defaut), True
        return repli, True

    def cout_run(self, compute_min: float, relecture_min: float = 0.0) -> tuple[float, float, bool]:
        """`(energy_kwh, eur, estime)` — 0 € d'outils, le calcul ne paie que l'électricité.

        `estime` est vrai dès qu'une des deux valeurs n'est pas mesurée sur cette machine.
        """
        puissance, p_estimee = self._effective(self.puissance_moyenne_w, 30.0)
        tarif, t_estime = self._effective(self.tarif_kwh_eur, 0.25)
        horaire, _ = self._effective(self.cout_horaire_relecture_eur, 0.0)
        energie = compute_min / 60.0 * puissance / 1000.0
        return energie, energie * tarif + relecture_min * horaire / 60.0, p_estimee or t_estime


# --------------------------------------------------------------------------------------
# Fichiers d'un run — spec, script, sous-titres, shotlist
# --------------------------------------------------------------------------------------


class TopicEvidence(Modele):
    """Preuve du choix d'un sujet ; vide si le sujet est manuel."""

    score: float | None = None
    vues_medianes_chaine: float | None = None
    ratio: float | None = None
    n: int | None = None
    requete: str | None = None


class Topic(Modele):
    """Sujet retenu et son angle éditorial propre."""

    sujet: str = Field(min_length=1, max_length=200)
    angle: str = Field(min_length=1)
    source: SourceSujet
    evidence: TopicEvidence = Field(default_factory=TopicEvidence)

    @model_validator(mode="after")
    def _preuve_selon_source(self) -> Topic:
        renseignee = self.evidence.model_dump(exclude_none=True)
        if self.source == "manuel" and renseignee:
            raise ValueError("topic manuel : evidence doit rester vide")
        if self.source != "manuel" and not renseignee:
            raise ValueError(f"topic {self.source} : evidence obligatoire")
        return self


class VideoSpec(ModeleRacine):
    """`spec.json` — le seul fichier qui fixe quoi produire."""

    video_id: VideoId
    parent_id: VideoId | None = None
    channel_id: Identifiant
    lang: LangCode
    niche: Identifiant
    style: Identifiant
    topic: Topic
    target_duration_s: int = Field(gt=0)
    cut_rhythm_target_s: float = Field(gt=0)
    seed: int = Field(ge=0, lt=2**64)
    product_id: Identifiant | None = None
    created_at: Horodatage

    @model_validator(mode="after")
    def _identifiants_coherents(self) -> VideoSpec:
        if not self.video_id.startswith(f"{self.channel_id}-"):
            raise ValueError(
                f"video_id {self.video_id} ne commence pas par channel_id {self.channel_id}"
            )
        if self.parent_id == self.video_id:
            raise ValueError("parent_id : un run n'est pas son propre parent")
        return self


# --------------------------------------------------------------------------------------
# research.json — étape 10
# --------------------------------------------------------------------------------------


class Fait(Modele):
    """Un fait sourcé. `claim` est ce que le script pourra affirmer, et rien de plus."""

    id: Annotated[str, StringConstraints(pattern=r"^f\d{2,3}$")]
    claim: str = Field(min_length=1)
    value: float | str | None = None
    unit: str | None = None
    date: str | None = None
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    confidence: Confiance
    retrieved_at: Horodatage


class Entite(Modele):
    """Une entité citée ; `real_person` alimente le contrôle 11 de la checklist."""

    name: str = Field(min_length=1)
    type: TypeEntite
    real_person: bool = False


class SourceConsultee(Modele):
    """Une source interrogée et retenue : d'où viennent les faits, sous quelle licence."""

    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    api: ApiSource
    lang: LangCode
    licence: str = Field(min_length=1)
    retrieved_at: Horodatage
    fact_ids: list[str] = Field(default_factory=list)


class SourceEcartee(Modele):
    """Une source écartée, avec le motif exact — la trace compte autant que la sélection."""

    url: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AnglePropose(Modele):
    """Un angle éditorial proposé par le LLM, avant arbitrage."""

    type: Literal["contrarien", "comparatif_chiffre", "recit"]
    phrase: str = Field(min_length=1)
    angle_signature: AngleEditorial


class Research(ModeleRacine):
    """`research.json` — faits sourcés et angle éditorial retenu (INTERFACES § 1)."""

    lang: LangCode
    sujet: str = Field(min_length=1)
    facts: list[Fait] = Field(default_factory=list)
    entities: list[Entite] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    sources: list[SourceConsultee] = Field(default_factory=list)
    sources_rejected: list[SourceEcartee] = Field(default_factory=list)
    fact_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    angles_proposes: list[AnglePropose] = Field(default_factory=list)
    angle: str = Field(min_length=1)
    angle_signature: AngleEditorial
    elements_proprietaires: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _compteurs_et_renvois(self) -> Research:
        if self.fact_count != len(self.facts):
            raise ValueError(f"fact_count {self.fact_count} ≠ {len(self.facts)} faits")
        if self.source_count != len(self.sources):
            raise ValueError(f"source_count {self.source_count} ≠ {len(self.sources)} sources")
        ids = [f.id for f in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("research : identifiant de fait en double")
        connus = set(ids)
        for source in self.sources:
            inconnus = [i for i in source.fact_ids if i not in connus]
            if inconnus:
                raise ValueError(f"source {source.url} : faits inconnus {inconnus}")
        return self


class Interrupt(Modele):
    """Rupture de rythme programmée."""

    type: TypeInterrupt
    at_s_relative: float = Field(ge=0)


class Hook(Modele):
    """Accroche : son type est un type du référentiel, jamais `intro_chaine_neutre`."""

    type: Identifiant
    text: str = Field(min_length=1)

    @field_validator("type")
    @classmethod
    def _type_productible(cls, valeur: str) -> str:
        if valeur == "intro_chaine_neutre":
            raise ValueError("hook.type : intro_chaine_neutre n'est pas productible")
        return valeur


class ScriptSegment(Modele):
    """Un segment de script : le texte de `narration` est le seul envoyé au TTS."""

    id: SegmentId
    role: Role
    narration: str = Field(min_length=1)
    on_screen_text: str | None = None
    visual_intent: str = Field(min_length=1)
    open_loop: OpenLoop = "none"
    interrupt: Interrupt | None = None
    sources: list[str] = Field(default_factory=list)
    disclosure_spoken: bool = False

    @property
    def word_count(self) -> int:
        """Nombre de mots de narration."""
        return len(self.narration.split())


class SignatureEditoriale(Modele):
    """Ce que cette vidéo apporte et qu'aucune source ne contient (CONFORMITE § 4)."""

    angle: AngleEditorial
    elements_proprietaires: list[str] = Field(min_length=1)


class Script(ModeleRacine):
    """`script.json` — fait foi pour le texte ; l'ASR ne fournit que le timing."""

    lang: LangCode
    hook: Hook
    segments: list[ScriptSegment] = Field(min_length=1)
    editorial_signature: SignatureEditoriale
    #: Surcharge facultative de l'ambiance musicale de la niche, pour **cette** vidéo seulement.
    music_mood: Mood | None = None
    word_count: int = Field(ge=0)
    estimated_duration_s: float = Field(ge=0)
    disclosure_lines: LignesDivulgation | None = None

    @model_validator(mode="after")
    def _regles_de_script(self) -> Script:
        ids = [s.id for s in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("script : identifiant de segment en double")
        plants = sum(1 for s in self.segments if s.open_loop == "plant")
        payoffs = sum(1 for s in self.segments if s.open_loop == "payoff")
        if plants < 2:
            raise ValueError(f"script : {plants} boucle(s) ouverte(s) plantée(s), 2 exigées")
        if payoffs < plants:
            raise ValueError(
                f"script : {plants} boucle(s) plantée(s) pour {payoffs} résolue(s) ; "
                "chaque plant a son payoff"
            )
        sponsors = [s for s in self.segments if s.role == "sponsor"]
        if sponsors and not any(s.disclosure_spoken for s in self.segments):
            raise ValueError(
                "script : segment sponsor sans phrase de divulgation orale "
                "(CONFORMITE § 11, contrôle 6, bloquant)"
            )
        if sponsors and self.disclosure_lines is None:
            raise ValueError("script : segment sponsor sans disclosure_lines")
        return self


class SegmentVoix(Modele):
    """Un segment synthétisé et sa position dans `voice/voice.wav`."""

    id: SegmentId
    merged_from: list[SegmentId] = Field(default_factory=list)
    file: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    duration_s: float = Field(ge=0)
    text: str = Field(min_length=1)
    disclosure_at_s: float | None = None

    @model_validator(mode="after")
    def _duree_coherente(self) -> SegmentVoix:
        if abs((self.end_s - self.start_s) - self.duration_s) > 0.05:
            raise ValueError(
                f"{self.id} : duration_s {self.duration_s} ≠ end_s − start_s "
                f"{self.end_s - self.start_s:.3f}"
            )
        return self


class Timings(ModeleRacine):
    """`voice/timings.json` — un enregistrement par segment synthétisé, dans l'ordre."""

    voice_id: Identifiant
    engine: MoteurTts
    sample_rate: int = Field(default=24000, gt=0)
    channels: int = Field(default=1, ge=1, le=2)
    loudness_lufs: float
    true_peak_dbtp: float
    total_duration_s: float = Field(gt=0)
    speed: float = Field(default=1.0, gt=0)
    segments: list[SegmentVoix] = Field(min_length=1)

    @model_validator(mode="after")
    def _couvre_la_piste(self) -> Timings:
        precedent = -1.0
        for segment in self.segments:
            if segment.start_s < precedent - 0.001:
                raise ValueError(f"{segment.id} : segments non ordonnés dans voice.wav")
            precedent = segment.end_s
        if precedent > self.total_duration_s + 0.05:
            raise ValueError(
                f"timings : dernier segment à {precedent:.2f} s au-delà de la piste "
                f"({self.total_duration_s:.2f} s)"
            )
        return self


class WordTiming(Modele):
    """Un mot horodaté : le mot vient du script, le timing de l'ASR."""

    w: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    seg: SegmentId
    asr_confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _ordre_temporel(self) -> WordTiming:
        if self.end_s < self.start_s:
            raise ValueError(f"mot « {self.w} » : end_s {self.end_s} < start_s {self.start_s}")
        return self


class MesureSegmentAsr(Modele):
    """Couverture et WER d'un segment : les deux, jamais la couverture seule (étape 7)."""

    id: SegmentId
    coverage: float = Field(ge=0)
    wer_vs_script: float = Field(ge=0)
    wer_threshold: float = Field(gt=0, le=1)
    engine: MoteurAsr


class Words(ModeleRacine):
    """`words.json` — mots horodatés, couverture et WER contre le texte source."""

    engine: MoteurAsr
    fallback_reason: Literal[
        "coverage_below_threshold", "wer_above_threshold", "language_drift", "operator_override"
    ] | None = None
    coverage: float = Field(ge=0)
    wer_vs_script: float = Field(ge=0)
    wer_threshold: float = Field(gt=0, le=1)
    segments: list[MesureSegmentAsr] = Field(default_factory=list)
    words: list[WordTiming] = Field(default_factory=list)

    @model_validator(mode="after")
    def _motif_de_repli(self) -> Words:
        if self.engine == "whisper" and self.fallback_reason is None:
            raise ValueError("words : engine whisper sans fallback_reason")
        if self.engine == "parakeet" and self.fallback_reason is not None:
            raise ValueError("words : fallback_reason renseigné sans repli")
        return self


class AssetRequest(Modele):
    """Ce qu'un plan demande à la brique d'acquisition."""

    type: TypeAsset
    prompt_or_keywords: str = Field(min_length=1)
    reuse_ok: bool = True
    layer: Couche = "background"
    contains_person: bool = False
    realistic: bool = False


class Shot(Modele):
    """Un plan : jointure obligatoire vers un segment de script."""

    id: ShotId
    segment_id: SegmentId
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    duration_s: float = Field(gt=0)
    visual_intent: str = Field(min_length=1)
    on_screen_text: str | None = None
    asset_request: AssetRequest
    motion: Mouvement = "static"
    transition_in: Transition = "cut"
    is_sponsor: bool = False
    interrupt: Interrupt | None = None
    seed: int = Field(ge=0, lt=2**64)

    @model_validator(mode="after")
    def _duree_coherente(self) -> Shot:
        if abs((self.end_s - self.start_s) - self.duration_s) > 0.05:
            raise ValueError(
                f"{self.id} : duration_s {self.duration_s} ≠ end_s − start_s "
                f"{self.end_s - self.start_s:.3f}"
            )
        if self.asset_request.reuse_ok and self.on_screen_text:
            raise ValueError(f"{self.id} : reuse_ok interdit sur un plan à texte incrusté")
        return self


class StatsShotlist(Modele):
    """Ce que la liste de plans a produit, face à ce qu'elle visait.

    `median_shot_s` est mesurée **hors hook** : le hook coupe volontairement plus vite (× 0,6), et
    l'y inclure ferait passer pour une dérive ce qui est une consigne. `median_hook_s` le mesure à
    part, face à `hook_shots_max_s`.
    """

    median_shot_s: float = Field(gt=0)
    target_s: float = Field(gt=0)
    hook_shots_max_s: float = Field(gt=0)
    tolerance: float = Field(default=0.10, gt=0, lt=1)
    # Étape 12.1 : la médiane seule ne dit pas si le jitter a tenu. Les déciles et le compte
    # entrent au contrat pour que le banc de l'étape 15 compare une distribution, pas un point.
    p10_shot_s: float | None = Field(default=None, gt=0)
    p90_shot_s: float | None = Field(default=None, gt=0)
    n_shots: int | None = Field(default=None, gt=0)
    median_hook_s: float | None = Field(default=None, gt=0)

    @property
    def dans_la_tolerance(self) -> bool:
        """Vrai si la médiane produite est à ± `tolerance` de la cible."""
        return abs(self.median_shot_s - self.target_s) <= self.target_s * self.tolerance


class Shotlist(ModeleRacine):
    """`shotlist.json` — pivot du système : il traduit un script en plans."""

    stats: StatsShotlist
    shots: list[Shot] = Field(min_length=1)

    @model_validator(mode="after")
    def _plans_uniques(self) -> Shotlist:
        ids = [s.id for s in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("shotlist : identifiant de plan en double")
        return self


# --------------------------------------------------------------------------------------
# Fichiers d'un run — assets, relecture, qualité, publication
# --------------------------------------------------------------------------------------


class Generateur(Modele):
    """Trace de génération d'un asset local — sans version, « même graine » ne veut rien dire."""

    model: str
    model_revision: str | None = None
    prompt_hash: str
    seed: int = Field(ge=0, lt=2**64)
    steps: int = Field(gt=0)
    resolution: Annotated[str, StringConstraints(pattern=r"^\d+x\d+$")]


class Asset(ModeleRacine):
    """`assets/<shot>/licence.json` — un asset sans ces champs ne descend pas dans le pipeline."""

    asset_id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]
    path: str = Field(min_length=1)
    provider: Fournisseur
    source_url: str | None = None
    author: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    licence_url: str = Field(min_length=1)
    attribution_line: str | None = None
    downloaded_at: Horodatage
    person_release: str | None = None
    generator: Generateur | None = None
    realistic: bool = False
    has_text: bool = False
    c2pa_present: bool = False

    @model_validator(mode="after")
    def _licence_et_provenance(self) -> Asset:
        if not licence_commerciale(self.licence):
            raise ValueError(
                f"licence {self.licence} : non commerciale, éliminatoire (CONFORMITE § 8)"
            )
        if self.provider == "flux":
            if self.source_url is not None:
                raise ValueError("provider flux : source_url doit être null (généré localement)")
            if self.generator is None:
                raise ValueError("provider flux : generator obligatoire")
        elif self.source_url is None:
            raise ValueError(f"provider {self.provider} : source_url obligatoire")
        return self


class ReviewRecord(ModeleRacine):
    """`review.json` — miroir de la ligne append-only de `registre/data/reviews.jsonl`."""

    reviewer: str = Field(min_length=1)
    review_date: Horodatage
    review_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    decision: DecisionRelecture
    comment: str = ""
    edits: list[dict[str, str]] = Field(default_factory=list)
    batch_id: str = Field(min_length=1)
    ria_exception_claimed: bool = True

    @model_validator(mode="after")
    def _commentaire_obligatoire(self) -> ReviewRecord:
        if self.decision in {"rejected", "approved_with_edits"} and not self.comment:
            raise ValueError(f"review {self.decision} : comment obligatoire")
        if self.reviewer in RELECTEURS_MACHINE and self.ria_exception_claimed:
            raise ValueError(
                f"{self.reviewer} : ria_exception_claimed doit être false "
                "(l'exception éditoriale RIA tombe)"
            )
        return self


class QCCheck(Modele):
    """Un contrôle de qualité : une mesure comparée à une cible."""

    id: Identifiant
    measured: float | bool | None = None
    target: float | None = None
    tolerance: float | None = None
    status: EtatControle
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def _non_mesure_est_saute(self) -> QCCheck:
        if self.measured is None and self.status != "skipped":
            raise ValueError(f"contrôle {self.id} : non mesuré, donc status skipped")
        if self.measured is not None and self.status == "skipped":
            raise ValueError(f"contrôle {self.id} : mesuré mais marqué skipped")
        return self


class QCReport(ModeleRacine):
    """`qc.json` — chaque contrôle compare une mesure à la cible de la niche."""

    score: float = Field(ge=0, le=100)
    verdict: VerdictQc
    regenerate_steps: list[str] = Field(default_factory=list)
    checks: list[QCCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def _etapes_a_rejouer(self) -> QCReport:
        if self.verdict == "regenerate" and not self.regenerate_steps:
            raise ValueError("qc : verdict regenerate sans regenerate_steps")
        if self.verdict != "regenerate" and self.regenerate_steps:
            raise ValueError("qc : regenerate_steps renseigné sans verdict regenerate")
        return self


class ControleChecklist(Modele):
    """Un des 30 contrôles de pré-publication (CONFORMITE § 11)."""

    n: int = Field(ge=1, le=30)
    id: Identifiant
    verdict: Literal["pass", "warn", "fail"]
    detail: str = ""


class GesteManuel(Modele):
    """Un geste que l'API ne sait pas faire et qu'un humain doit poser dans Studio."""

    id: Literal["paid_promotion_box", "schedule", "other"]
    required: bool = True
    done: bool = False
    done_at: Horodatage | None = None


class PostCheck(Modele):
    """Relecture après upload — seul détecteur d'un oubli de la case manuelle."""

    has_paid_product_placement: bool | None = None


class PublishRecord(ModeleRacine):
    """`publish.json` — état réel côté YouTube et comptabilité de quota."""

    publish_path: CheminPublication
    publish_state: EtatPublication
    checklist: list[ControleChecklist] = Field(default_factory=list)
    youtube_video_id: str | None = None
    uploaded_at: Horodatage | None = None
    publish_at: Horodatage | None = None
    published_at: Horodatage | None = None
    thumbnail_set: bool = False
    caption_id: str | None = None
    playlist_item_id: str | None = None
    quota_units_spent: int = Field(default=0, ge=0)
    quota_day: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None
    reporting_job_id: str | None = None
    manual_steps: list[GesteManuel] = Field(default_factory=list)
    post_check: PostCheck = Field(default_factory=PostCheck)
    retry_count: int = Field(default=0, ge=0)
    last_error: str | None = None

    @model_validator(mode="after")
    def _etat_coherent(self) -> PublishRecord:
        if self.publish_state != "draft" and self.publish_state != "ready_to_publish":
            if self.youtube_video_id is None:
                raise ValueError(
                    f"publish_state {self.publish_state} sans youtube_video_id : "
                    "la clé de jointure de la boucle de rétroaction manque"
                )
        if self.publish_path == "manual_studio" and self.published_at is not None:
            if not any(g.id == "schedule" and g.done for g in self.manual_steps):
                raise ValueError(
                    "manual_studio : published_at ne peut être renseigné que par le "
                    "rattrapage d'`analytics pull` après le geste manuel"
                )
        return self


# --------------------------------------------------------------------------------------
# manifest.json — cinq blocs (INTERFACES § 1), tous les champs de CONFORMITE § 10.1
# --------------------------------------------------------------------------------------


class Chapitre(Modele):
    """Un chapitre YouTube : un horodatage et un titre. Le premier est à 0 s, sans exception."""

    start_s: float = Field(ge=0)
    title: str = Field(min_length=1, max_length=100)

    def horodatage(self) -> str:
        """`0:00` ou `1:02:03` — le format que YouTube reconnaît dans une description."""
        total = int(self.start_s)
        heures, reste = divmod(total, 3600)
        minutes, secondes = divmod(reste, 60)
        if heures:
            return f"{heures}:{minutes:02d}:{secondes:02d}"
        return f"{minutes}:{secondes:02d}"


class BlocsDescription(Modele):
    """La description est **composée**, jamais écrite à la main (`INTERFACES` § metadata.json).

    Ordre imposé : divulgation → accroche → chapitres → sources → affiliation → attribution
    des assets → crédit musical. `sources` est un bloc de plus que le contrat d'origine
    (étape 13.2) : les faits du script sont sourcés, et taire les sources serait un choix.
    """

    disclosure: str | None = None
    hook: str = Field(min_length=1)
    #: Sommaire en clair — trois à cinq lignes qui disent ce que la vidéo contient, avant les
    #: horodatages. Les chapitres donnent le *quand* ; le sommaire donne le *quoi*, et c'est
    #: lui que lisent les deux lignes visibles avant « …plus ».
    summary: list[str] = Field(default_factory=list)
    chapters: list[Chapitre] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    affiliate: list[str] = Field(default_factory=list)
    attribution: list[str] = Field(default_factory=list)
    music_credit: str | None = None


class VideoMetadata(ModeleRacine):
    """`metadata.json` — ce que `publish` envoie à l'API, mot pour mot, sans transformation."""

    title_chosen: str = Field(min_length=1, max_length=100)
    title_variants: list[VarianteTitre] = Field(default_factory=list)
    description: str = Field(min_length=1, max_length=5000)
    description_blocks: BlocsDescription
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list, max_length=3)
    localizations: dict[str, dict[str, str]] = Field(default_factory=dict)
    pinned_comment: str | None = None
    category_id: str = Field(pattern=r"^\d{1,2}$")
    default_language: LangCode
    default_audio_language: LangCode
    recording_date: Horodatage | None = None
    chapters: list[Chapitre] = Field(default_factory=list)
    contains_synthetic_media: bool = False
    contains_synthetic_media_reason: str | None = None
    paid_promotion: bool = False
    made_for_kids: bool = False
    notify_subscribers: bool = True
    playlist_id: str | None = None
    caption_file: str = "subtitles.srt"
    thumbnail_file: str = "thumbnail.png"

    @staticmethod
    def cout_tag(tag: str) -> int:
        """Coût d'un tag dans le budget de 500 caractères, **guillemets compris**.

        Règle de l'API : « if your request contains a tag with a space, the API server
        handles the tag value as though it were wrapped in quotation marks » — un tag de
        deux mots coûte donc deux caractères de plus que sa longueur. Compter sans eux est
        le moyen d'obtenir un `400 invalidTags` sur une liste qu'on croyait au ras du seuil.
        """
        return len(tag) + (2 if " " in tag else 0)

    @model_validator(mode="after")
    def _limites_youtube(self) -> VideoMetadata:
        cumul = sum(self.cout_tag(t) for t in self.tags) + max(0, len(self.tags) - 1)
        if cumul > 500:
            raise ValueError(f"tags : {cumul} caractères cumulés pour 500 au maximum")
        octets = len(self.description.encode("utf-8"))
        if octets > 5000:
            raise ValueError(
                f"description : {octets} octets pour 5 000 au maximum. Le plafond de l'API "
                "se compte en octets, pas en caractères — un tiret cadratin en vaut trois."
            )
        if self.made_for_kids:
            raise ValueError(
                "made_for_kids : aucune chaîne BMS ne s'adresse aux enfants "
                "(le champ existe pour être déclaré faux, pas pour être mis à vrai)"
            )
        if self.chapters:
            if self.chapters[0].start_s != 0:
                raise ValueError("chapitres : le premier est obligatoirement à 0 s")
            if len(self.chapters) < 3:
                raise ValueError("chapitres : YouTube en exige au moins 3 pour les afficher")
            for precedent, suivant in zip(self.chapters, self.chapters[1:], strict=False):
                if suivant.start_s - precedent.start_s < 10:
                    raise ValueError(
                        f"chapitres : « {suivant.title} » à {suivant.start_s:.0f} s suit le "
                        "précédent de moins de 10 s, YouTube refuse de les afficher"
                    )
        if self.contains_synthetic_media and not self.contains_synthetic_media_reason:
            raise ValueError("contains_synthetic_media : reason obligatoire (CONFORMITE § 3)")
        return self


class ManifestIdentite(Modele):
    """Bloc `identite` : de quelle chaîne, de quelle langue, de quel gabarit vient ce run."""

    video_id: VideoId
    parent_id: VideoId | None = None
    channel_id: Identifiant
    lang: LangCode
    niche: Identifiant
    style: Identifiant
    template_id: Identifiant
    charte_version: str


class VarianteTitre(Modele):
    """Un titre candidat — les non retenus restent, sinon on ne sait pas ce qui a porté.

    Deux notes distinctes, et elles ne mesurent pas la même chose. `heuristic` est la note de
    règles (longueur, patron, forme, mots interdits) : reproductible, explicable, aveugle au
    sens. `llm_rank` est le rang sorti du **tournoi de duels** entre les quatre meilleures
    heuristiques : il juge ce qu'une règle ne sait pas juger, et il n'existe que pour ces
    quatre-là (`None` ailleurs). `score` est le score final qui a servi au classement. La
    phase 5 apprendra laquelle des deux prédit le clic ; les garder séparées est la condition
    pour pouvoir le mesurer un jour.
    """

    text: str = Field(min_length=1)
    #: Identifiant de patron du référentiel. Lu aussi sous l'ancien nom `pattern` : les
    #: manifestes écrits avant l'étape 21 le portent ainsi et doivent rester relisibles.
    pattern_id: str | None = Field(
        default=None, validation_alias=AliasChoices("pattern_id", "pattern")
    )
    length_char: int | None = None
    #: Note de règles, dans [0, 1].
    heuristic: float | None = None
    #: Rang du duel LLM, 1 = meilleur. `None` = le titre n'est pas entré en tournoi.
    llm_rank: int | None = Field(default=None, ge=1)
    #: Le script tient-il la promesse du titre ? `None` = non vérifié (LLM indisponible).
    promise_kept: bool | None = None
    score: float | None = None

    @property
    def pattern(self) -> str | None:
        """Ancien nom de `pattern_id`, gardé pour les lecteurs écrits avant l'étape 21."""
        return self.pattern_id


class RotationMiniature(Modele):
    """Plan de rotation d'une miniature. Écrit à la production, exécuté à la phase 5.

    **YouTube n'expose aucune API de test A/B.** « Test & Compare » existe (3 variantes,
    gagnant départagé sur la part de temps de visionnage, clos en deux semaines) mais vit
    dans Studio bureau et n'a **aucune ressource dans la Data API v3** : ni création, ni
    lecture. La seule comparaison automatisable est donc une **rotation mesurée** — poser la
    variante suivante par `thumbnails.set` (50 unités de quota) et lire l'effet dans la
    Reporting API, qui est la seule à donner les impressions et le CTR.

    Ce que ce plan **ne prétend pas** être : une expérience contrôlée. Une rotation compare
    deux périodes, pas deux populations tirées au sort ; l'âge de la vidéo et la saison s'y
    mélangent. C'est ce que la contrainte permet, et le manifeste dit laquelle.
    """

    #: Jours après publication avant d'envisager la bascule.
    after_days: int = Field(default=7, ge=1)
    #: Condition de bascule, en clair — évaluée par la phase 5, pas ici.
    criterion: str = Field(min_length=1)
    #: Variantes restantes, dans l'ordre de bascule. Vide = plus rien à essayer.
    next_variants: list[str] = Field(default_factory=list)
    #: Nombre de bascules déjà faites.
    rotations_done: int = Field(default=0, ge=0)


class MesuresMiniature(Modele):
    """Ce qu'une miniature composée mesure sur elle-même, sans jugement humain.

    Toutes ces valeurs sont lues **sur le PNG rendu**, pas déduites du HTML : une règle CSS
    dit ce qu'on a demandé, un pixel dit ce qu'on a obtenu. La réduction à **168 × 94 px** est
    la taille d'affichage d'une vignette dans le fil mobile de YouTube ; c'est là que la
    lisibilité se perd, donc c'est là qu'elle se mesure.
    """

    #: Rapport WCAG 2.x entre la couleur du texte et le fond réellement situé derrière lui.
    contrast_ratio: float | None = None
    #: Part de l'image occupée par le bloc de texte, en pourcentage de la surface.
    text_area_pct: float | None = None
    #: Hauteur du plus petit caractère **une fois réduit à 168 px de large**. Sous 10 px, le
    #: texte est une tache. La règle de production mesurée (étape 21) : 10 à 15 % de la
    #: hauteur en 1280×720, soit 9 à 14 px à 168×94.
    text_height_px_168: float | None = None
    #: Variance du laplacien de la vignette 168 px — netteté des contours après réduction.
    sharpness_168: float | None = None
    #: Part de la saillance de l'image (résidu spectral) qui tombe **sous** le bloc de texte.
    #: Élevée = le texte couvre le sujet ; basse = le texte occupe une zone calme.
    saliency_under_text: float | None = None
    #: Écart chromatique moyen (CIE76 sur L*a*b*) entre les couleurs dominantes du fond et
    #: la couleur du texte. Faible = le texte se fond dans l'image.
    palette_distance: float | None = None
    #: Part de la largeur de texte qui sort du cadre, en pourcentage. Zéro attendu : la page
    #: réduit la police jusqu'à ce que tout tienne. Non nul = quarante réductions n'ont pas
    #: suffi, et une lettre est coupée sur l'image publiée.
    text_overflow_pct: float | None = None


class VarianteMiniature(Modele):
    """Une miniature candidate."""

    file: str = Field(min_length=1)
    text: str | None = None
    #: Gabarit de composition employé (`bandeau_bas`, `bloc_gauche`…).
    template: str | None = None
    #: Variante de palette employée — les trois candidates ne diffèrent pas que par le texte.
    palette: str | None = None
    #: Mesures détaillées (étape 21). Les champs plats ci-dessous en sont l'extrait que les
    #: contrôles de l'étape 13.2 et le QC lisent déjà ; ils restent alimentés.
    measures: MesuresMiniature | None = None
    contrast_ratio: float | None = None
    text_area_ratio: float | None = None
    #: Hauteur du bloc de texte ÷ hauteur de l'image, **lue sur la page rendue**. C'est le
    #: critère de l'étape 13.2 (≥ 12 %) ; il ne se déduit pas de `text_area_ratio`, qui compte
    #: une surface et qu'un texte large et plat peut tenir sans être lisible.
    text_height_ratio: float | None = None
    legible_at_320px: bool | None = None
    phash: str | None = None
    score: float | None = None


class VarianteTexteMiniature(Modele):
    """Un texte de miniature candidat — conservé avec son score, comme les titres.

    Séparé de `VarianteMiniature`, qui porte un **fichier** : un texte peut être écarté avant
    d'avoir été composé. La phase 3 met ces textes en concurrence, la phase 5 apprend.
    """

    text: str = Field(min_length=1)
    words: int = Field(ge=1)
    score: float | None = None
    rendered_as: str | None = None


class PisteMusicale(Modele):
    """`music.licence` de CONFORMITE § 10 : la piste se télécharge depuis le Studio de la chaîne."""

    track_title: str
    source: str
    author: str | None = None
    licence: str
    licence_url: str | None = None
    attribution_required: bool
    credit_line: str | None = None
    downloaded_from_channel: Identifiant

    @model_validator(mode="after")
    def _credit_si_exige(self) -> PisteMusicale:
        if self.attribution_required and not self.credit_line:
            raise ValueError("musique : attribution exigée sans credit_line")
        if not licence_commerciale(self.licence):
            raise ValueError(f"musique : licence {self.licence} non commerciale")
        return self


class BouclesOuvertes(Modele):
    """Boucles ouvertes plantées et résolues, avec leur position."""

    planted: int = Field(default=0, ge=0)
    paid: int = Field(default=0, ge=0)
    positions_s: list[float] = Field(default_factory=list)


class ReutilisationBibliotheque(Modele):
    """Mesure de réutilisation — supposée faire baisser le coût, pas encore un fait."""

    assets_reused: int = Field(default=0, ge=0)
    assets_generated: int = Field(default=0, ge=0)
    reuse_ratio: float = Field(default=0.0, ge=0, le=1)


class NoteQualite(Modele):
    """Un jugement porté sur le rendu, avec **qui** l'a porté et **sur quoi**.

    Une note sans juge ni date ne vaut rien : ce que la session perçoit (une image fixe) et ce
    qu'elle ne perçoit pas (le mouvement, le son) ne se jugent pas de la même façon, et le
    manifeste doit dire lequel des deux il porte (`CLAUDE.md` § 5).
    """

    critere: str = Field(min_length=1)
    note_sur_5: float = Field(ge=0, le=5)
    juge: str = Field(min_length=1)
    date: Horodatage
    commentaire: str = ""
    echantillon: str = ""


class CandidatHook(Modele):
    """Un hook proposé, sa note par règles et ce qu'on lui a reproché (étape 16)."""

    text: str = Field(min_length=1)
    words: int = Field(ge=0)
    score: float = Field(ge=0, le=100)
    violations: list[str] = Field(default_factory=list)


class DensiteMesuree(Modele):
    """Densité d'information du script, mesurée par règles avant la voix (étape 16).

    `entity_share` est rapportée avec la valeur parce que plus de la moitié du score vient
    des noms propres (54,9 % mesurés sur `science_pop`) : une densité tenue par les seules
    entités n'est pas celle qu'on cherche.
    """

    facts_per_min: float = Field(ge=0)
    facts_per_min_weighted: float = Field(default=0.0, ge=0)
    target: float | None = Field(default=None, ge=0)
    floor: float | None = Field(default=None, ge=0)
    count: int = Field(default=0, ge=0)
    entity_share: float = Field(default=0.0, ge=0, le=1)
    by_category: dict[str, int] = Field(default_factory=dict)
    #: Note du juge LLM, quand il a répondu. `None` = non jugé, jamais « réussi ».
    judge_facts_per_min: float | None = None
    judge_specificity: int | None = None
    judge_vagueness: int | None = None


class VerificationRetention(Modele):
    """Ce que `factory/retention/verify.py` a trouvé, et ce qu'il a fallu de reprises."""

    #: Nombre de régénérations ciblées déclenchées par une infraction (0 = passé du premier coup).
    regenerations: int = Field(default=0, ge=0)
    #: Infractions restantes à la dernière passe, en clair et en français.
    violations: list[str] = Field(default_factory=list)
    #: Infractions rencontrées à chaque essai, dans l'ordre — la trace du taux de régénération.
    historique: list[str] = Field(default_factory=list)
    interrupts_planned: int = Field(default=0, ge=0)
    interrupt_cadence_s: float | None = None
    interrupt_max_gap_s: float | None = None
    loops_planted_marked: int = Field(default=0, ge=0)
    loops_paid_verified: int = Field(default=0, ge=0)
    #: Boucles dont la cohérence n'a pas pu être jugée : non vérifiées, pas réussies.
    loops_unjudged: int = Field(default=0, ge=0)
    seconds: float | None = Field(default=None, ge=0)


class ManifestDecisions(Modele):
    """Bloc `decisions` : les facteurs que l'étape 26 corrèle aux résultats."""

    topic: Topic
    hook_type: Identifiant
    #: Étape 16 : les trois candidats notés, le choisi, et pourquoi.
    hook_candidates: list[CandidatHook] = Field(default_factory=list)
    hook_chosen: str | None = None
    hook_choice_reason: str | None = None
    density: DensiteMesuree | None = None
    retention: VerificationRetention | None = None
    title_variants: list[VarianteTitre] = Field(default_factory=list)
    title_chosen: str | None = None
    thumbnail_variants: list[VarianteMiniature] = Field(default_factory=list)
    thumbnail_chosen: str | None = None
    #: Plan de rotation de la miniature — écrit à la production, exécuté par la phase 5.
    thumbnail_rotation: RotationMiniature | None = None
    #: Textes candidats, y compris ceux qu'aucune variante n'a composés (étape 13.2).
    thumbnail_text_variants: list[VarianteTexteMiniature] = Field(default_factory=list)
    cut_rhythm_target_s: float | None = None
    # Étape 12.1 : ce que `shotlist` a **planifié** (médiane hors hook de shotlist.json), à ne pas
    # confondre avec `cut_rhythm_measured_s`, que le QC mesure sur `final.mp4` par détection de
    # plans. Les deux peuvent diverger : un fondu enchaîné n'est pas une coupe pour PySceneDetect.
    cut_rhythm_planned_s: float | None = None
    cut_rhythm_measured_s: float | None = None
    duration_s: float | None = None
    density_facts_per_min: float | None = None
    voice_id: Identifiant | None = None
    # Mesures de l'étape 11 : facteurs de rétention (thèse n° 3), donc corrélés par l'étape 26
    # au même titre que le rythme de coupe mesuré juste au-dessus.
    loudness_lufs: float | None = None
    true_peak_dbtp: float | None = None
    asr_engine: MoteurAsr | None = None
    subtitle_coverage: float | None = None
    wer_vs_script: float | None = None
    music_track: PisteMusicale | None = None
    #: Pourquoi il n'y a pas de musique, quand il n'y en a pas. Un lit silencieux est une
    #: décision de production ; sans motif écrit, elle est indistinguable d'un oubli.
    music_warning: str | None = None
    assets: list[Asset] = Field(default_factory=list)
    open_loops: BouclesOuvertes = Field(default_factory=BouclesOuvertes)
    interrupts: list[Interrupt] = Field(default_factory=list)
    library_reuse: ReutilisationBibliotheque = Field(default_factory=ReutilisationBibliotheque)
    #: Notes de qualité du rendu, chacune attribuée à son juge (étape 12.2 et suivantes).
    quality_notes: list[NoteQualite] = Field(default_factory=list)
    # Étape 15 : la note du banc et son verdict entrent au manifeste, là où l'étape 26 va
    # chercher les facteurs à corréler aux vues. Le détail par métrique reste dans `qc.json` ;
    # dupliquer ici la centaine de champs du banc rendrait le manifeste illisible.
    qc_score: float | None = Field(default=None, ge=0, le=100)
    qc_verdict: Literal["PASS", "FAIL"] | None = None
    qc_version: str | None = None
    # Étape 26 : version de learned/weights.json lue par les étapes, et poids appliqué par clé
    # (« topic », « hook », « titles », « cut_rhythm », « thumbnail »). `None` = référentiel.
    learned_version: str | None = None
    learned_applied: dict[str, Any] = Field(default_factory=dict)


class SceneSynthetique(Modele):
    """Une scène générée, posée à la génération et non reconstituée après coup."""

    scene_id: ShotId
    generator: str
    prompt_hash: str
    realistic: bool


class SegmentSponsorise(Modele):
    """Un segment de promotion payante et sa divulgation (CONFORMITE § 3)."""

    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    type: Literal["affiliate", "sponsor"]
    product_id: Identifiant
    overlay_rendered: bool = False
    spoken_disclosure_at_s: float | None = None

    @model_validator(mode="after")
    def _divulgation_dans_les_30_s(self) -> SegmentSponsorise:
        if self.spoken_disclosure_at_s is not None:
            retard = self.spoken_disclosure_at_s - self.start_s
            if retard < 0 or retard > 30:
                raise ValueError(
                    f"divulgation orale à {retard:.1f} s du début du segment sponsor : "
                    "les 30 premières secondes sont exigées (CONFORMITE § 11, contrôle 6)"
                )
        return self


class LienAffiliation(Modele):
    """Un lien d'affiliation et son sous-identifiant de suivi (CONFORMITE § 10.4)."""

    network: Reseau
    tracking_id: str
    subid_param: str | None = None
    subid_value: str | None = None
    target_url: str
    product_id: str | None = None

    @model_validator(mode="after")
    def _contraintes_reseau(self) -> LienAffiliation:
        param, longueur = SUBID_PAR_RESEAU[self.network]
        if self.subid_param != param:
            raise ValueError(f"{self.network} : subid_param attendu {param!r}")
        if self.subid_value is not None:
            if longueur is None:
                raise ValueError(f"{self.network} : aucun subid par vidéo n'est possible")
            if len(self.subid_value) > longueur:
                raise ValueError(
                    f"{self.network} : subid_value de {len(self.subid_value)} caractères "
                    f"pour {longueur} au maximum"
                )
        return self


class VerificationStudio(Modele):
    """Geste manuel confirmé dans Studio — l'API ne sait pas l'écrire."""

    done: bool = False
    at: Horodatage | None = None


class AngleEditorialManifeste(Modele):
    """Angle éditorial revendiqué, liste fermée (CONFORMITE § 4)."""

    type: AngleEditorial
    resume: str = Field(min_length=1)


class EmpreintesDedoublonnage(Modele):
    """Empreintes de dédoublonnage — index global, toutes chaînes confondues."""

    script_simhash: str
    thumbnail_phash: str


class CompteDePublication(Modele):
    """Compte de publication effectif. Aucune valeur de secret (CONFORMITE § 1)."""

    channel_id: str
    brand_account: str
    google_account_alias: Identifiant
    owner: str = "BMS"
    gcp_project: Identifiant
    two_fa_enabled: bool = False
    phone_verified: bool = False


class InstantaneCadence(Modele):
    """Instantané de cadence : une trace d'audit, jamais une autorisation de publier."""

    max_per_week: int = Field(ge=1, le=2)
    window_start: Horodatage | None = None
    published_this_week: int = Field(default=0, ge=0)
    next_allowed_at: Horodatage | None = None
    jitter_window: str = "PT3H"
    read_at: Horodatage | None = None


class ManifestConformite(Modele):
    """Bloc `conformite` : les 25 champs obligatoires de CONFORMITE § 10.1."""

    contains_synthetic_media: bool = False
    contains_synthetic_media_reason: str | None = None
    synthetic_scenes: list[SceneSynthetique] = Field(default_factory=list)
    virtual_images_mention: bool = False
    paid_promotion: bool = False
    paid_promotion_checked_in_studio: VerificationStudio | None = None
    sponsor_segments: list[SegmentSponsorise] = Field(default_factory=list)
    disclosure_lines: dict[str, LignesDivulgation] = Field(default_factory=dict)
    affiliate_links: list[LienAffiliation] = Field(default_factory=list)
    c2pa_preserved: bool = False
    reviewer: str | None = None
    review_hash: str | None = None
    review_date: Horodatage | None = None
    review_decision: DecisionRelecture | None = None
    ria_exception_claimed: bool = False
    editorial_angle: AngleEditorialManifeste | None = None
    dedupe_hash: EmpreintesDedoublonnage | None = None
    publish_channel_account: CompteDePublication | None = None
    cadence_limits: InstantaneCadence | None = None
    publish_path: CheminPublication = "manual_studio"
    publish_state: EtatPublication = "draft"
    person_releases_missing: list[ShotId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _motif_si_synthetique(self) -> ManifestConformite:
        if self.contains_synthetic_media and not self.contains_synthetic_media_reason:
            raise ValueError(
                "contains_synthetic_media : reason obligatoire (scènes, modèle, décision)"
            )
        if self.reviewer in RELECTEURS_MACHINE and self.ria_exception_claimed:
            raise ValueError(f"{self.reviewer} : ria_exception_claimed doit être false")
        return self


class ModeleUtilise(Modele):
    """Un modèle chargé pendant le run, avec sa version d'exécution."""

    brique: Identifiant
    repo: str
    revision: str | None = None
    quantization: str | None = None
    runtime: str
    runtime_version: str


class Cout(Modele):
    """Coût d'un run. Une valeur non mesurée reste nulle et porte son drapeau."""

    compute_min: float | None = None
    energy_kwh: float | None = None
    energy_kwh_a_mesurer: bool = True
    eur: float | None = None
    eur_a_mesurer: bool = True


class DisqueMo(Modele):
    """Pic et reliquat disque, en mégaoctets."""

    peak: float | None = None
    after_export: float | None = None


class ErreurRun(Modele):
    """Une erreur, avec le message exact de l'outil — jamais reformulé."""

    step: Identifiant
    ts: Horodatage
    code: int
    message: str
    retry: int = 0


class Regeneration(Modele):
    """Une reprise ciblée décidée par le banc (étape 22.2), et ce qui l'a décidée.

    Elle nomme la **mesure** fautive, pas seulement l'étape : six mois plus tard, « rejoué
    depuis `shotlist` » ne dit pas si c'était le rythme de coupe ou la variété visuelle, et
    l'étape 26 ne pourra pas corréler les remèdes à leur taux de réussite.
    """

    ts: Horodatage
    #: `cut_rhythm`, `loudness`, `hook_length`… — la mesure du banc sortie en `fail`.
    mesure: Identifiant
    #: Étape d'où le run repart. Elle et ses suivantes seulement, jamais tout le run.
    depuis: Identifiant
    remede: str
    #: Rang de cette régénération dans le run : 1, puis 2, puis `blocked`.
    rang: int = Field(ge=1)
    valeur_mesuree: float | bool | None = None
    cible: float | None = None
    #: Verdict du banc **après** la reprise, écrit au tour suivant : `pass`, `regenerate`,
    #: `blocked`, ou `None` tant que le banc n'a pas repassé.
    resultat: VerdictQc | None = None


class ManifestExecution(Modele):
    """Bloc `execution` : ce qu'a coûté le run et où il en est."""

    timings: dict[str, float] = Field(default_factory=dict)
    modeles: list[ModeleUtilise] = Field(default_factory=list)
    cost: Cout = Field(default_factory=Cout)
    disk_mb: DisqueMo = Field(default_factory=DisqueMo)
    errors: list[ErreurRun] = Field(default_factory=list)
    #: Horloge de l'orchestrateur. `wallclock_s` ≠ somme de `timings` dès qu'un run est repris :
    #: la somme dit ce qu'a coûté le calcul, l'horloge dit ce qu'a duré la production.
    run_started_at: Horodatage | None = None
    run_ended_at: Horodatage | None = None
    wallclock_s: float | None = None
    run_state: EtatRun = "queued"
    blocked_reason: str | None = None
    #: Reprises ciblées décidées par le banc, dans l'ordre. Plafonnées par
    #: `OrchestratorConfig.regenerations_max` ; au-delà, le run passe `blocked`.
    regenerations: list[Regeneration] = Field(default_factory=list)

    @model_validator(mode="after")
    def _motif_de_blocage(self) -> ManifestExecution:
        if self.run_state == "blocked" and not self.blocked_reason:
            raise ValueError(
                "run_state blocked : blocked_reason obligatoire, en français, destiné à Alek"
            )
        return self


class FenetreMetriques(Modele):
    """Somme des jours 0 à 6 ou 0 à 29 — jamais la valeur du 7ᵉ ou du 30ᵉ jour."""

    views: int | None = None
    watch_time_min: float | None = None
    avg_view_duration_s: float | None = None
    avg_view_percentage: float | None = None
    subscribers_gained: int | None = None
    impressions: int | None = None
    ctr: float | None = None
    traffic_sources: dict[str, float] = Field(default_factory=dict)
    retention_curve_ref: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    day_count: int | None = None
    pulled_at: Horodatage | None = None
    complete: bool = False


class Conversions(Modele):
    """Conversions d'affiliation ; toujours nulles sur Amazon."""

    network: Reseau
    clicks: int = Field(default=0, ge=0)
    orders: int = Field(default=0, ge=0)
    revenue_eur: float = Field(default=0.0, ge=0)
    subid_value: str | None = None
    resynced_at: Horodatage | None = None


class ManifestResultats(Modele):
    """Bloc `resultats` : rempli par la phase 5 (étape 25)."""

    youtube_video_id: str | None = None
    published_at: Horodatage | None = None
    reporting_job_id: str | None = None
    metrics_7d: FenetreMetriques | None = None
    metrics_30d: FenetreMetriques | None = None
    conversions: Conversions | None = None


class Declinaison(Modele):
    """Bloc `declinaison` d'un run enfant (étape 24) : ce qu'il doit à son parent."""

    parent_id: VideoId
    parent_lang: LangCode
    parent_template_id: Identifiant
    parent_thumbnail_template: str | None = None
    segments_conserves: int = Field(ge=0)
    assets_reused: int = Field(default=0, ge=0)
    assets_reused_same_segment: int = Field(default=0, ge=0)
    assets_generated: int = Field(default=0, ge=0)
    assets_reused_ratio: float | None = Field(default=None, ge=0, le=1)
    adaptation_s: float | None = None
    parent_compute_min: float | None = None
    compute_ratio: float | None = None
    thumbnail_phash_distance: int | None = None


class EnfantDeclinaison(Modele):
    """Ligne `children[]` du manifeste parent."""

    video_id: VideoId
    channel_id: Identifiant
    lang: LangCode
    created_at: Horodatage
    compute_ratio: float | None = None


class RunManifest(ModeleRacine):
    """`manifest.json` — la pièce produite en cas de contrôle, et la boucle de rétroaction."""

    identite: ManifestIdentite
    decisions: ManifestDecisions
    conformite: ManifestConformite = Field(default_factory=ManifestConformite)
    execution: ManifestExecution = Field(default_factory=ManifestExecution)
    resultats: ManifestResultats = Field(default_factory=ManifestResultats)
    declinaison: Declinaison | None = None
    children: list[EnfantDeclinaison] = Field(default_factory=list)

    def champs_conformite_manquants(self) -> list[str]:
        """Champs de CONFORMITE § 10.1 encore vides. Vide = le run peut être publié."""
        c = self.conformite
        manquants: list[str] = []
        for champ in (
            "reviewer", "review_hash", "review_date", "review_decision",
            "editorial_angle", "dedupe_hash", "publish_channel_account", "cadence_limits",
        ):
            if getattr(c, champ) is None:
                manquants.append(champ)
        if not self.identite.template_id:
            manquants.append("template_id")
        if c.paid_promotion:
            if not c.sponsor_segments:
                manquants.append("sponsor_segments")
            if not c.affiliate_links:
                manquants.append("affiliate_links")
            if c.paid_promotion_checked_in_studio is None:
                manquants.append("paid_promotion_checked_in_studio")
        if (c.paid_promotion or c.virtual_images_mention) and not c.disclosure_lines:
            manquants.append("disclosure_lines")
        if c.paid_promotion or c.virtual_images_mention:
            if self.identite.lang not in c.disclosure_lines:
                manquants.append(f"disclosure_lines[{self.identite.lang}]")
        if not self.decisions.music_track:
            manquants.append("music_track")
        if not self.decisions.assets:
            manquants.append("assets")
        return manquants

    @model_validator(mode="after")
    def _conformite_avant_publication(self) -> RunManifest:
        if self.identite.parent_id == self.identite.video_id:
            raise ValueError("parent_id : un run n'est pas son propre parent")
        if self.conformite.publish_state in ETATS_PUBLIABLES:
            manquants = self.champs_conformite_manquants()
            if manquants:
                raise ValueError(
                    f"publish_state {self.conformite.publish_state} impossible : "
                    f"champs obligatoires vides (CONFORMITE § 10.1) — {', '.join(manquants)}"
                )
        return self


# --------------------------------------------------------------------------------------
# Configuration — orchestrateur (étape 22.1)
# --------------------------------------------------------------------------------------


class FenetreHoraire(Modele):
    """Une plage locale « HH:MM → HH:MM ». Elle peut franchir minuit (22:00 → 07:00)."""

    debut: Annotated[str, StringConstraints(pattern=r"^\d{2}:\d{2}$")]
    fin: Annotated[str, StringConstraints(pattern=r"^\d{2}:\d{2}$")]

    @staticmethod
    def _minutes(valeur: str) -> int:
        heures, minutes = valeur.split(":")
        return int(heures) * 60 + int(minutes)

    def contient(self, quand: time) -> bool:
        """Vrai si l'heure locale tombe dans la fenêtre, minuit franchi compris."""
        courant = quand.hour * 60 + quand.minute
        debut, fin = self._minutes(self.debut), self._minutes(self.fin)
        if debut == fin:
            return True  # 24 h sur 24, façon explicite de désactiver la fenêtre
        if debut < fin:
            return debut <= courant < fin
        return courant >= debut or courant < fin


class Tentatives(Modele):
    """Politique de nouvelle tentative d'une étape."""

    max: Annotated[int, Field(ge=1, le=10)] = 3
    #: Attentes avant la 2ᵉ, la 3ᵉ… tentative, en minutes. La dernière vaut pour les suivantes.
    attentes_min: list[Annotated[int, Field(ge=0)]] = Field(default_factory=lambda: [5, 15, 60])

    def attente_min(self, tentative: int) -> int:
        """Minutes à attendre après la `tentative`-ième (1-indexée) échouée."""
        if not self.attentes_min:
            return 0
        return self.attentes_min[min(max(tentative, 1), len(self.attentes_min)) - 1]


class GardesFous(Modele):
    """Ce qui est vérifié **avant** chaque étape, jamais après."""

    #: Plancher dur de `CLAUDE.md` § 3 et d'`ARCHITECTURE` § 8. Ne pas descendre sous 8.
    disque_libre_go_min: Annotated[float, Field(ge=1.0)] = 8.0
    #: Marge mémoire : le pic mesuré de `assets.image` est 11,15 Go sur 16 (ARCHITECTURE § 8).
    memoire_libre_go_min: Annotated[float, Field(ge=0.0)] = 2.0
    #: Plafond de taille d'un run, qui attrape une boucle de génération (ARCHITECTURE § 8).
    run_disque_mo_max: Annotated[int, Field(ge=100)] = 6000


class JournalConfig(Modele):
    """Rotation applicative de `workspace/logs/factory.log`.

    Applicative et non `newsyslog` : une ligne `newsyslog.conf` qui omet `owner:group`
    recrée le fichier en `root:root` et l'agent utilisateur ne peut plus y écrire.
    """

    taille_max_mo: Annotated[float, Field(gt=0)] = 10.0
    fichiers: Annotated[int, Field(ge=1, le=50)] = 5


class SauvegardeConfig(Modele):
    """Sauvegarde planifiée. La destination reste sur cette machine : la copier ailleurs
    est un geste humain, rappelé par `docs/EXPLOITATION.md`."""

    destination: str = "~/BMS-backups"
    retention_jours: Annotated[int, Field(ge=1)] = 30


class DaemonConfig(Modele):
    """Boucle du daemon."""

    #: Sommeil entre deux tours quand il n'y a rien à faire.
    pause_boucle_s: Annotated[int, Field(ge=5, le=3600)] = 60
    #: `caffeinate -i` pendant un run : empêche le sommeil par inactivité, pas la fermeture
    #: du capot (aucune option de `caffeinate` ne l'empêche — veille du 20/09/2026).
    caffeinate: bool = True


class Remede(Modele):
    """Ce que l'orchestrateur rejoue quand une mesure du banc sort en `fail` (étape 22.2).

    `depuis` est l'étape d'où le run repart : elle **et ses suivantes**, jamais tout le run.
    Un remède qui repartirait de `research` pour un défaut de niveau sonore coûterait quatre
    heures de machine pour trois minutes de travail (mesures de l'étape 22.1).
    """

    depuis: Identifiant
    #: Ce qu'on change avant de rejouer, sans quoi l'étape referait exactement la même chose.
    #: `graine_suivante` incrémente `spec.seed` · `gabarit_suivant` passe au gabarit suivant
    #: de la chaîne · `assets_differents` interdit la réutilisation des assets du run ·
    #: `hook_seul` ne réécrit que l'accroche · `consigne` n'ajoute qu'une consigne au prompt ·
    #: `aucun` rejoue à l'identique (utile quand le défaut vient du montage, pas du choix).
    levier: Literal["graine_suivante", "gabarit_suivant", "assets_differents", "hook_seul",
                    "consigne", "aucun"] = "aucun"
    #: Phrase ajoutée au prompt de l'étape rejouée quand `levier` vaut `consigne` ou
    #: `hook_seul`. En anglais : c'est la langue de production (`ROADMAP` § 3.1).
    consigne: str = ""
    pourquoi: str = ""


class NotificationsConfig(Modele):
    """Canal d'alerte et digest (étape 22.2). Aucun jeton ici : ils vivent dans `.env`."""

    #: `auto` = Telegram si `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` sont posés dans
    #: `.env`, notification macOS sinon. Les deux autres valeurs forcent la main.
    canal: Literal["auto", "telegram", "macos", "aucun"] = "auto"
    #: Disque libre sous lequel une alerte part. Distinct du plancher dur de 8 Go des
    #: garde-fous : l'alerte doit précéder l'arrêt, pas le constater.
    disque_alerte_go: Annotated[float, Field(ge=0)] = 10.0
    #: Part du quota d'API consommée au-delà de laquelle une alerte part.
    quota_alerte_part: Annotated[float, Field(ge=0, le=1)] = 0.80
    #: Heure locale d'envoi du digest quotidien (agent `com.bms.factory.digest`).
    digest_heure: Annotated[int, Field(ge=0, le=23)] = 7
    digest_minute: Annotated[int, Field(ge=0, le=59)] = 30


#: Types de rapports de la Reporting API créés pour chaque chaîne (étape 23.1).
#: **Vérifiés un par un** le 22/09/2026 sur
#: developers.google.com/youtube/reporting/v1/reports/channel_reports : les suffixes `_a2`
#: cités par le prompt de l'étape (`channel_basic_a2`, `channel_traffic_source_a2`,
#: `channel_playback_location_a2`) **n'existent pas** — ce sont des `_a3`. Un `jobs.create`
#: sur un `reportTypeId` inconnu échoue, et l'échec serait découvert des semaines plus tard,
#: quand les données manqueraient.
RAPPORTS_CHAINE: tuple[str, ...] = (
    "channel_reach_basic_a1",       # impressions de miniature et CTR — introuvables ailleurs
    "channel_basic_a3",             # vues, minutes, abonnés
    "channel_traffic_source_a3",    # d'où vient le trafic
    "channel_demographics_a1",      # âge et sexe
    "channel_playback_location_a3",  # page de lecture, suggestions, externe
)


class PublicationConfig(Modele):
    """`config/orchestrator.yaml` § publication — quota, tentatives, rapports (étape 23.1)."""

    #: Projet Google Cloud portant le quota. Identique pour toutes les chaînes : le quota est
    #: une ressource du **projet**, pas du compte — deux chaînes du même projet se partagent
    #: les 10 000 unités, et c'est la raison d'être du ledger.
    gcp_project: Identifiant = "bms-factory"
    #: Plafonds de l'usine, à 80 % de la dotation de Google (100 uploads, 10 000 unités).
    #: La marge absorbe le décalage entre notre jour UTC et le jour Pacifique de Google.
    uploads_max_jour: Annotated[int, Field(ge=0, le=100)] = 80
    unites_max_jour: Annotated[int, Field(ge=0, le=10000)] = 8000
    #: Tentatives sur erreur transitoire (5xx, 404 de propagation), backoff exponentiel.
    tentatives_max: Annotated[int, Field(ge=1, le=10)] = 5
    attente_initiale_s: Annotated[float, Field(ge=0.1, le=60)] = 2.0
    #: Rapports créés par `factory publish reporting-jobs`.
    rapports: list[str] = Field(default_factory=lambda: list(RAPPORTS_CHAINE))
    #: `true` remettrait `videos.insert` dans le compartiment des 10 000 unités, comme avant
    #: juin 2026. Laissé en configuration parce que Google a déjà changé ce modèle une fois :
    #: si le compartiment « Video Uploads » disparaissait, un booléen suffirait à recompter.
    insert_compte_dans_unites: bool = False

    @field_validator("rapports")
    @classmethod
    def _types_plausibles(cls, valeur: list[str]) -> list[str]:
        for nom in valeur:
            if not re.fullmatch(r"(channel|content_owner)_[a-z_]+_a\d+", nom):
                raise ValueError(
                    f"reportTypeId invraisemblable : « {nom} » — la forme est "
                    "channel_<sujet>_a<version> (voir models.RAPPORTS_CHAINE)"
                )
        return valeur


class CalendrierConfig(Modele):
    """`config/orchestrator.yaml` § calendrier — règles du portefeuille (étape 23.2).

    Les bornes des champs sont celles de CONFORMITE § 6 : la configuration peut être plus
    prudente, jamais moins. La cadence par chaîne, elle, vit dans `config/channels/`.
    """

    #: Plafond hebdomadaire d'une chaîne de moins de `age_jeune_chaine_jours` jours.
    plafond_semaine_jeune_chaine: Annotated[int, Field(ge=1, le=2)] = 2
    age_jeune_chaine_jours: Annotated[int, Field(ge=90)] = 90
    #: Écart minimal entre deux publications d'une même chaîne (anti-rafale).
    espacement_chaine_h: Annotated[int, Field(ge=24)] = 48
    #: Écart minimal entre deux publications BMS, toutes chaînes confondues. ≥ 60 garantit
    #: aussi « jamais deux dans la même heure d'horloge » ; CONFORMITE exige ± 30.
    exclusion_portefeuille_min: Annotated[int, Field(ge=60)] = 60
    #: Écart minimal entre deux chaînes **de même langue** (même audience, même fuseau) :
    #: deux vidéos EN à une heure d'intervalle signent l'exploitation commune.
    ecart_meme_langue_min: Annotated[int, Field(ge=60)] = 240
    #: Publications BMS sur toute fenêtre glissante de 24 h, toutes chaînes confondues.
    max_par_jour_portefeuille: Annotated[int, Field(ge=1, le=6)] = 2
    #: Écart relatif minimal de durée entre deux vidéos consécutives d'une chaîne.
    variation_duree_min: Annotated[float, Field(ge=0.0, le=0.5)] = 0.10
    #: Intervalle [min, max] du facteur tiré (graine = run) pour `target_duration_s` d'un job
    #: pas encore scripté quand sa durée prévue colle à la précédente. Vide = avertir seulement.
    facteurs_duree: list[Annotated[float, Field(ge=0.7, le=1.3)]] = Field(
        default_factory=lambda: [0.8, 1.25], max_length=2)
    #: Choix parmi les `k` premiers créneaux admissibles : casse la régularité des jours.
    choix_parmi: Annotated[int, Field(ge=1, le=6)] = 3
    #: Temps de machine réservé par job qui précède dans la file (≈ 2 vidéos par nuit).
    heures_par_job_en_file: Annotated[int, Field(ge=0)] = 12
    #: Délai minimal avant la date d'un job pas encore exporté (temps de production + relecture).
    delai_production_h: Annotated[int, Field(ge=12)] = 72
    delai_exporte_h: Annotated[int, Field(ge=2)] = 24
    #: Le daemon téléverse (en privé) un job exporté entre `avance_upload_h[0]` et `[1]` heures
    #: avant sa date — avance tirée par vidéo, pour que l'heure d'upload ne recopie pas le
    #: calendrier public. Un seul upload par tour, `ecart_uploads_min` au moins entre deux.
    avance_upload_h: list[Annotated[int, Field(ge=2, le=168)]] = Field(
        default_factory=lambda: [12, 60], min_length=2, max_length=2)
    ecart_uploads_min: Annotated[int, Field(ge=30)] = 120
    #: `false` : le daemon planifie mais ne téléverse jamais seul.
    upload_auto: bool = True
    #: Créneaux appris (étape 26). Absent = créneaux de `config/channels/`.
    fichier_creneaux_appris: str = "learned/weights.json"


class DeclinaisonConfig(Modele):
    """Quand l'orchestrateur enfile les déclinaisons des chaînes `derive_from` (étape 24)."""

    actif: bool = True
    #: `export` : dès que le parent est exporté ; `publication` : après son upload.
    declencheur: Literal["export", "publication"] = "export"


class OrchestratorConfig(ModeleRacine):
    """`config/orchestrator.yaml` — file, fenêtres, tentatives, garde-fous, sauvegarde."""

    #: Étapes réputées lourdes : elles ne tournent que dans `fenetre_lourdes`.
    etapes_lourdes: list[str] = Field(
        default_factory=lambda: ["voice", "subtitles", "render", "assemble", "export"]
    )
    fenetre_lourdes: FenetreHoraire = Field(
        default_factory=lambda: FenetreHoraire(debut="22:00", fin="07:00")
    )
    fenetre_legeres: FenetreHoraire = Field(
        default_factory=lambda: FenetreHoraire(debut="00:00", fin="00:00")
    )
    #: Fuseau d'interprétation des deux fenêtres. Les créneaux de publication sont, eux,
    #: dans le fuseau de la chaîne : ce sont deux horloges différentes et c'est voulu.
    timezone: str = "Europe/Paris"
    #: Plafonds de temps par étape, en secondes. Vide = ceux de `factory/run.py`, qui sont
    #: calés sur les mesures des étapes 10 à 21.
    timeouts_s: dict[str, Annotated[int, Field(ge=10)]] = Field(default_factory=dict)
    tentatives: Tentatives = Field(default_factory=Tentatives)
    gardes: GardesFous = Field(default_factory=GardesFous)
    journal: JournalConfig = Field(default_factory=JournalConfig)
    sauvegarde: SauvegardeConfig = Field(default_factory=SauvegardeConfig)
    daemon: DaemonConfig = Field(default_factory=DaemonConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    #: Publication et quota (étape 23.1).
    publication: PublicationConfig = Field(default_factory=PublicationConfig)
    calendrier: CalendrierConfig = Field(default_factory=CalendrierConfig)
    declinaison: DeclinaisonConfig = Field(default_factory=DeclinaisonConfig)
    #: Table des remèdes, indexée par **mesure du banc** (`qc.json → metrics`). Une mesure
    #: absente de la table retombe sur `ETAPE_CORRECTRICE` de `factory/eval/bench.py`, qui
    #: nomme l'étape mais pas le levier — le run repart alors sans rien changer.
    remedes: dict[str, Remede] = Field(default_factory=dict)
    #: Reprises ciblées avant `blocked`. Deux : la troisième coûterait plus cher qu'un humain.
    regenerations_max: Annotated[int, Field(ge=0, le=5)] = 2
    #: Tente un remède même quand le contrôle en échec porte `verdict_fail: blocked` dans
    #: `config/qc.yaml`, **à condition** que `remedes` nomme ce contrôle. Deux documents se
    #: contredisaient : `QC.md` § 4 fait de `loudness` un bloquant sans reprise, le prompt de
    #: l'étape 22.2 demande « loudness → assemble ». Les deux ont raison sur une moitié — un
    #: niveau sonore hors norme est parfois un montage interrompu (cas mesuré le 21/09 :
    #: `shot_19.mp4` tronqué par un `kill -9`), auquel cas 198 s de remontage suffisent ; il
    #: est parfois un défaut de fond, auquel cas la reprise échoue et le job bloque de toute
    #: façon. On tente **une** fois et on mesure, plutôt que de trancher à l'aveugle.
    remedes_sur_bloquant: bool = True
    #: Rejets d'un même script avant que la relecture ne rende la main. Deux également.
    rejets_max: Annotated[int, Field(ge=0, le=5)] = 2

    @field_validator("timezone")
    @classmethod
    def _fuseau_connu(cls, valeur: str) -> str:
        try:
            ZoneInfo(valeur)
        except (ZoneInfoNotFoundError, ValueError) as erreur:
            raise ValueError(f"fuseau inconnu : {valeur}") from erreur
        return valeur


#: Modèles racine — un fichier, un modèle. Sert aux tests d'aller-retour JSON.
MODELES_RACINE: tuple[type[ModeleRacine], ...] = (
    Language, Niche, Style, Product, Channel,
    TeamConfig, QcConfig, EditorialConfig, EconomicsConfig, OrchestratorConfig,
    VideoSpec, Script, Words, Shotlist, Asset, ReviewRecord,
    QCReport, PublishRecord, RunManifest, VideoMetadata,
)
