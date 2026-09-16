"""Modèles de données de l'usine.

Contrat : `docs/INTERFACES.md`. Champs obligatoires de conformité : `docs/CONFORMITE.md` § 10.
Règle du projet : tout ce qui est chaîne, niche, style, langue ou produit est une donnée
validée, jamais une constante de code.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
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
TypeInterrupt = Literal["question", "chiffre", "silence", "changement_de_plan"]
AngleEditorial = Literal["opinion", "comparaison_chiffree", "test", "donnee_proprietaire"]
SourceSujet = Literal["topics_queue", "referentiel", "manuel"]
Confiance = Literal["high", "medium", "low"]
TypeEntite = Literal["person", "place", "org", "concept"]
ApiSource = Literal["wikipedia", "wikidata", "pubmed", "openlibrary", "arxiv", "semantic_scholar"]
Mouvement = Literal["zoom_in", "zoom_out", "pan", "parallax", "static"]
Transition = Literal["cut", "fade", "dip_black", "whip", "none"]
TypeAsset = Literal["image", "stock", "card", "avatar"]
Couche = Literal["foreground", "background"]
Fournisseur = Literal[
    "flux", "pexels", "pixabay", "openverse", "wikimedia", "nasa",
    "internet_archive", "library", "charte",
]
Reseau = Literal["amazon", "awin", "cj", "impact"]
CheminPublication = Literal["manual_studio", "api_scheduled"]
EtatPublication = Literal["draft", "ready_to_publish", "uploaded_private", "scheduled", "public"]
EtatRun = Literal[
    "queued", "running", "awaiting_review", "blocked", "failed",
    "exported", "published", "visual_review_pending",
]
DecisionRelecture = Literal["approved", "approved_with_edits", "rejected", "auto"]
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
}


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


class Language(ModeleRacine):
    """`config/languages/<code>.yaml` — tout ce qui empêche une langue de fuir dans une autre."""

    code: LangCode
    name: str
    voices: list[Voice] = Field(min_length=1)
    typographie: Typographie
    nombres: Nombres
    disclosure: Disclosure
    tts: ConfigTts = Field(default_factory=ConfigTts)
    asr: ConfigAsr

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


class Niche(ModeleRacine):
    """`config/niches/<id>.yaml` — copie lisible des cibles de `registre/REFERENTIEL.json`."""

    id: Identifiant
    rythme_coupe_s: RythmeCoupe
    duree_s: DureeCible
    mots_par_minute: MotsParMinute
    hooks: HooksCible
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
    position: Literal["apres_hook", "apres_premier_point", "fin"] = "apres_premier_point"
    duree_s_max: float = Field(default=45.0, gt=0)


class Product(ModeleRacine):
    """`config/products/<id>.yaml` — un produit d'affiliation, jamais une constante de code."""

    id: Identifiant
    name: str
    network: Reseau
    tracking_id: str = Field(min_length=1)
    subid_param: str | None = None
    subid_max_len: int | None = None
    target_url: str = Field(pattern=r"^https://")
    attribution_par_video: bool
    cookie_window_days: int = Field(gt=0)
    disclosure_override: dict[str, LignesDivulgation] = Field(default_factory=dict)
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
                "(100 identifiants de suivi au maximum, aucune granularité par vidéo)"
            )
        return self

    def subid(self, channel_id: str, lang: str, video_id: str) -> str | None:
        """`<channel_id>_<lang>_<video_id>` tronqué par la droite ; None sur Amazon."""
        if not self.attribution_par_video or self.subid_max_len is None:
            return None
        return f"{channel_id}_{lang}_{video_id}"[: self.subid_max_len]


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
    subtitles: SousTitresCharte = Field(default_factory=SousTitresCharte)
    framing: Cadrage = Field(default_factory=Cadrage)
    #: Style graphique imposé à toutes les images de la chaîne — le premier levier de cohérence.
    style_prefix: str = ""
    #: Palette en mots, interdiction de texte, tokens de cohérence — refermé après l'intention.
    style_suffix: str = ""
    #: Ce qu'aucune image de la chaîne ne doit contenir. Ignoré si le modèle ne le supporte pas ;
    #: le champ existe pour que la charte reste le seul endroit où cela se décide.
    negative_prompt: str = ""


class Cadence(Modele):
    """Cadence de publication d'une chaîne (CONFORMITE § 6)."""

    per_week_max: int = Field(default=2, ge=1, le=2)
    days: list[Jour] = Field(min_length=1)
    hours_local: list[HeureLocale] = Field(min_length=1)
    jitter_min: int = Field(default=180, ge=120)
    timezone: str

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


class ConfigBibliotheque(Modele):
    """Anti-répétition d'asset sur une même chaîne."""

    cooldown_videos: int = Field(default=10, ge=0)
    max_uses_per_channel: int = Field(default=3, ge=1)


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
    derive_from: Identifiant | None = None
    auto_approve: bool = False
    youtube: ConfigYoutube = Field(default_factory=ConfigYoutube)
    library: ConfigBibliotheque = Field(default_factory=ConfigBibliotheque)

    @model_validator(mode="after")
    def _coherence_interne(self) -> Channel:
        if len(set(self.templates)) != len(self.templates):
            raise ValueError("templates : gabarit en double (rotation ≥ 3, CONFORMITE § 5)")
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
    """Seuil et verdict d'un contrôle de qualité."""

    cible: float | None = None
    min: float | None = None
    tolerance: float | None = None
    source: str | None = None
    verdict_fail: VerdictQc | Literal["warn"] = "warn"


class QcConfig(ModeleRacine):
    """`config/qc.yaml` — barème et seuils."""

    poids: dict[str, int] = Field(min_length=1)
    hors_bareme: list[str] = Field(default_factory=list)
    seuils: dict[str, SeuilQc] = Field(default_factory=dict)
    score_minimal_pour_publier: int = Field(default=70, ge=0, le=100)

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


class EditorialConfig(ModeleRacine):
    """`config/editorial.yaml`."""

    topics_queue: FileSujets
    dedupe: ConfigDedoublonnage
    angles_autorises: list[AngleEditorial] = Field(min_length=1)
    sources_blanches: list[str] = Field(min_length=1)
    purge_cache_api_jours: int = Field(default=30, gt=0, le=30)


class ValeurSourcee(Modele):
    """Une valeur économique qui porte son origine, ou son absence de mesure."""

    valeur: float | None = None
    source: str | None = None
    date: str | None = None
    a_mesurer: bool = False
    note: str | None = None

    @model_validator(mode="after")
    def _pas_de_valeur_inventee(self) -> ValeurSourcee:
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
        if self.reviewer == "auto-approve" and self.ria_exception_claimed:
            raise ValueError(
                "auto-approve : ria_exception_claimed doit être false "
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
    """Un titre candidat — les non retenus restent, sinon on ne sait pas ce qui a porté."""

    text: str = Field(min_length=1)
    pattern: str | None = None
    length_char: int | None = None
    score: float | None = None


class VarianteMiniature(Modele):
    """Une miniature candidate."""

    file: str = Field(min_length=1)
    text: str | None = None
    contrast_ratio: float | None = None
    text_area_ratio: float | None = None
    legible_at_320px: bool | None = None
    phash: str | None = None
    score: float | None = None


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


class ManifestDecisions(Modele):
    """Bloc `decisions` : les facteurs que l'étape 26 corrèle aux résultats."""

    topic: Topic
    hook_type: Identifiant
    title_variants: list[VarianteTitre] = Field(default_factory=list)
    title_chosen: str | None = None
    thumbnail_variants: list[VarianteMiniature] = Field(default_factory=list)
    thumbnail_chosen: str | None = None
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
    assets: list[Asset] = Field(default_factory=list)
    open_loops: BouclesOuvertes = Field(default_factory=BouclesOuvertes)
    interrupts: list[Interrupt] = Field(default_factory=list)
    library_reuse: ReutilisationBibliotheque = Field(default_factory=ReutilisationBibliotheque)
    #: Notes de qualité du rendu, chacune attribuée à son juge (étape 12.2 et suivantes).
    quality_notes: list[NoteQualite] = Field(default_factory=list)


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
        if self.reviewer == "auto-approve" and self.ria_exception_claimed:
            raise ValueError("auto-approve : ria_exception_claimed doit être false")
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


class ManifestExecution(Modele):
    """Bloc `execution` : ce qu'a coûté le run et où il en est."""

    timings: dict[str, float] = Field(default_factory=dict)
    modeles: list[ModeleUtilise] = Field(default_factory=list)
    cost: Cout = Field(default_factory=Cout)
    disk_mb: DisqueMo = Field(default_factory=DisqueMo)
    errors: list[ErreurRun] = Field(default_factory=list)
    run_state: EtatRun = "queued"
    blocked_reason: str | None = None

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


class RunManifest(ModeleRacine):
    """`manifest.json` — la pièce produite en cas de contrôle, et la boucle de rétroaction."""

    identite: ManifestIdentite
    decisions: ManifestDecisions
    conformite: ManifestConformite = Field(default_factory=ManifestConformite)
    execution: ManifestExecution = Field(default_factory=ManifestExecution)
    resultats: ManifestResultats = Field(default_factory=ManifestResultats)

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


#: Modèles racine — un fichier, un modèle. Sert aux tests d'aller-retour JSON.
MODELES_RACINE: tuple[type[ModeleRacine], ...] = (
    Language, Niche, Style, Product, Channel,
    TeamConfig, QcConfig, EditorialConfig, EconomicsConfig,
    VideoSpec, Script, Words, Shotlist, Asset, ReviewRecord,
    QCReport, PublishRecord, RunManifest,
)
