"""Chargement et validation croisée de `config/`.

Une chaîne, une niche, un style, une langue, un produit sont des **données validées**.
Le chargement est en pydantic v2 `extra="forbid"` : une clé mal orthographiée est une
erreur, pas un silence.
"""

from __future__ import annotations

import hashlib
import json
import secrets as _secrets
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from factory.core.models import (
    ALPHABET_ID,
    Channel,
    EconomicsConfig,
    EditorialConfig,
    Language,
    ModeleRacine,
    Niche,
    Product,
    QcConfig,
    Style,
    TeamConfig,
    VideoSpec,
    Voice,
)
from factory.core.paths import RunPaths, dossier_config, racine_projet

#: Moteurs de style connus et étape de `ROADMAP.md` qui les livre (INTERFACES § 3).
MOTEURS_CONNUS: dict[str, str] = {
    "cartes": "12.1",
    "illustre_anime": "12.2",
    "documentaire": "17",
    "motion_design": "30.1",
    "whiteboard": "30.2",
    "avatar2d": "29",
}

#: Un dossier de configuration, son modèle et la clé qui doit valoir le nom du fichier.
DOSSIERS: dict[str, tuple[type[ModeleRacine], str]] = {
    "languages": (Language, "code"),
    "niches": (Niche, "id"),
    "styles": (Style, "id"),
    "channels": (Channel, "id"),
    "products": (Product, "id"),
}

#: Fichiers uniques de configuration.
FICHIERS: dict[str, type[ModeleRacine]] = {
    "team.yaml": TeamConfig,
    "qc.yaml": QcConfig,
    "editorial.yaml": EditorialConfig,
    "economics.yaml": EconomicsConfig,
}

Niveau = Literal["erreur", "avertissement"]


@dataclass(frozen=True)
class Probleme:
    """Un défaut de configuration, localisé et lisible."""

    fichier: str
    message: str
    niveau: Niveau = "erreur"

    def __str__(self) -> str:
        marque = "ERREUR" if self.niveau == "erreur" else "ALERTE"
        return f"[{marque}] {self.fichier} : {self.message}"


class ErreurConfig(RuntimeError):
    """La configuration ne valide pas. Porte la liste complète des problèmes."""

    def __init__(self, problemes: list[Probleme]) -> None:
        self.problemes = problemes
        super().__init__("\n".join(str(p) for p in problemes))


def _messages_pydantic(erreur: ValidationError) -> list[str]:
    """Traduit une erreur pydantic en lignes lisibles."""
    lignes: list[str] = []
    for detail in erreur.errors():
        champ = ".".join(str(part) for part in detail["loc"]) or "(racine)"
        message = detail["msg"].removeprefix("Value error, ")
        lignes.append(f"champ « {champ} » : {message}")
    return lignes


def _lire_yaml(fichier: Path) -> dict[str, Any]:
    """Charge un YAML et exige un objet à la racine."""
    contenu = yaml.safe_load(fichier.read_text(encoding="utf-8"))
    if contenu is None:
        raise ValueError("fichier vide")
    if not isinstance(contenu, dict):
        raise ValueError(f"objet attendu à la racine, {type(contenu).__name__} trouvé")
    return contenu


def charger_fichier(
    fichier: Path, modele: type[ModeleRacine], cle_nom: str | None = None
) -> tuple[ModeleRacine | None, list[Probleme]]:
    """Charge un fichier de configuration en modèle. Retourne le modèle et ses problèmes."""
    nom = fichier.name
    try:
        brut = _lire_yaml(fichier)
    except (yaml.YAMLError, ValueError, OSError) as erreur:
        return None, [Probleme(nom, str(erreur).splitlines()[0])]
    try:
        objet = modele.model_validate(brut)
    except ValidationError as erreur:
        return None, [Probleme(nom, message) for message in _messages_pydantic(erreur)]

    problemes: list[Probleme] = []
    if cle_nom is not None:
        attendu = fichier.stem
        trouve = getattr(objet, cle_nom)
        if trouve != attendu:
            problemes.append(
                Probleme(nom, f"{cle_nom} « {trouve} » ne correspond pas au nom du fichier")
            )
    if objet.mineure_inferieure():
        problemes.append(
            Probleme(
                nom,
                f"schema_version {objet.schema_version} plus ancienne que "
                f"{modele.model_fields['schema_version'].default} : défauts appliqués",
                "avertissement",
            )
        )
    return objet, problemes


@dataclass
class ConfigSet:
    """L'ensemble de la configuration résolue."""

    racine: Path
    languages: dict[str, Language] = field(default_factory=dict)
    niches: dict[str, Niche] = field(default_factory=dict)
    styles: dict[str, Style] = field(default_factory=dict)
    channels: dict[str, Channel] = field(default_factory=dict)
    products: dict[str, Product] = field(default_factory=dict)
    team: TeamConfig | None = None
    qc: QcConfig | None = None
    editorial: EditorialConfig | None = None
    economics: EconomicsConfig | None = None
    problemes: list[Probleme] = field(default_factory=list)

    @property
    def erreurs(self) -> list[Probleme]:
        """Problèmes bloquants."""
        return [p for p in self.problemes if p.niveau == "erreur"]

    @property
    def avertissements(self) -> list[Probleme]:
        """Problèmes non bloquants."""
        return [p for p in self.problemes if p.niveau == "avertissement"]

    def get_channel(self, channel_id: str) -> Channel:
        """Chaîne d'identifiant donné. Lève `KeyError` si elle n'existe pas."""
        if channel_id not in self.channels:
            connues = ", ".join(sorted(self.channels)) or "aucune"
            raise KeyError(f"chaîne inconnue : {channel_id} (connues : {connues})")
        return self.channels[channel_id]

    def list_channels(self) -> list[Channel]:
        """Toutes les chaînes, triées par identifiant."""
        return [self.channels[cle] for cle in sorted(self.channels)]

    def langue_de(self, channel: Channel) -> Language:
        """Langue d'une chaîne."""
        return self.languages[channel.lang]

    def voix_de(self, channel: Channel) -> Voice | None:
        """Voix retenue par une chaîne, si elle appartient bien à sa langue."""
        langue = self.languages.get(channel.lang)
        return langue.voix(channel.voice_id) if langue else None

    def produits_de(self, channel: Channel) -> list[Product]:
        """Produits d'affiliation configurés sur une chaîne."""
        return [self.products[pid] for pid in channel.products if pid in self.products]

    def cible_rythme(self, channel: Channel) -> float:
        """Rythme de coupe visé : cible de montage, repli cible, repli valeur de secours."""
        return self.niches[channel.niche].rythme_coupe_s.cible_effective()


def charger(racine: Path | None = None, strict: bool = True) -> ConfigSet:
    """Charge tout `config/`, valide chaque fichier puis les renvois croisés."""
    dossier = dossier_config(racine)
    cfg = ConfigSet(racine=dossier)
    if not dossier.is_dir():
        cfg.problemes.append(Probleme(str(dossier), "dossier de configuration absent"))
        if strict:
            raise ErreurConfig(cfg.problemes)
        return cfg

    for nom_dossier, (modele, cle) in DOSSIERS.items():
        cible: dict[str, Any] = getattr(cfg, nom_dossier)
        chemin = dossier / nom_dossier
        if not chemin.is_dir():
            cfg.problemes.append(Probleme(nom_dossier, "dossier absent"))
            continue
        for fichier in sorted(chemin.glob("*.yaml")):
            objet, problemes = charger_fichier(fichier, modele, cle)
            cfg.problemes.extend(
                Probleme(f"{nom_dossier}/{p.fichier}", p.message, p.niveau) for p in problemes
            )
            if objet is not None:
                cible[getattr(objet, cle)] = objet

    for nom_fichier, modele in FICHIERS.items():
        fichier = dossier / nom_fichier
        attribut = nom_fichier.removesuffix(".yaml")
        if not fichier.is_file():
            cfg.problemes.append(Probleme(nom_fichier, "fichier absent"))
            continue
        objet, problemes = charger_fichier(fichier, modele)
        cfg.problemes.extend(problemes)
        if objet is not None:
            setattr(cfg, attribut, objet)

    cfg.problemes.extend(croiser(cfg))
    if strict and cfg.erreurs:
        raise ErreurConfig(cfg.erreurs)
    return cfg


def croiser(cfg: ConfigSet) -> list[Probleme]:
    """Validations croisées : rien ne référence ce qui n'existe pas."""
    problemes: list[Probleme] = []
    taxonomie = _taxonomie_hooks()

    for niche in cfg.niches.values():
        fichier = f"niches/{niche.id}.yaml"
        inconnus = sorted(set(niche.hooks.parts) - taxonomie) if taxonomie else []
        if inconnus:
            problemes.append(
                Probleme(fichier, f"types de hook hors taxonomie du référentiel : {inconnus}")
            )
        if niche.rythme_coupe_s.a_mesurer:
            problemes.append(
                Probleme(
                    fichier,
                    "rythme de coupe non mesuré : valeur de secours "
                    f"{niche.rythme_coupe_s.fallback_provisoire_s} s employée, à mesurer "
                    "au banc (étape 15)",
                    "avertissement",
                )
            )

    for style in cfg.styles.values():
        fichier = f"styles/{style.id}.yaml"
        if style.engine not in MOTEURS_CONNUS:
            problemes.append(
                Probleme(fichier, f"moteur inconnu : {style.engine} (connus : "
                                  f"{sorted(MOTEURS_CONNUS)})")
            )
        elif not style.executable:
            problemes.append(
                Probleme(
                    fichier,
                    f"style en statut « {style.statut} » : accepté par le validateur, refusé "
                    f"à l'exécution — livré par l'étape {MOTEURS_CONNUS[style.engine]}",
                    "avertissement",
                )
            )

    for produit in cfg.products.values():
        for code in produit.disclosure_override:
            if code not in cfg.languages:
                problemes.append(
                    Probleme(f"products/{produit.id}.yaml",
                             f"disclosure_override pour une langue inconnue : {code}")
                )

    couples: dict[tuple[str, str], str] = {}
    voix_prises: dict[tuple[str, str], str] = {}
    for channel in cfg.channels.values():
        fichier = f"channels/{channel.id}.yaml"
        langue = cfg.languages.get(channel.lang)
        if langue is None:
            problemes.append(Probleme(fichier, f"langue inconnue : {channel.lang}"))
        elif langue.voix(channel.voice_id) is None:
            disponibles = ", ".join(v.id for v in langue.voices)
            problemes.append(
                Probleme(
                    fichier,
                    f"voix « {channel.voice_id} » absente de la langue {channel.lang} "
                    f"(disponibles : {disponibles})",
                )
            )
        if channel.niche not in cfg.niches:
            problemes.append(Probleme(fichier, f"niche inconnue : {channel.niche}"))
        style = cfg.styles.get(channel.style)
        if style is None:
            problemes.append(Probleme(fichier, f"style inconnu : {channel.style}"))
        elif style.templates:
            hors = sorted(set(channel.templates) - set(style.templates))
            if hors:
                problemes.append(
                    Probleme(fichier, f"gabarits absents du style {style.id} : {hors}")
                )
        for produit_id in channel.products:
            produit = cfg.products.get(produit_id)
            if produit is None:
                problemes.append(Probleme(fichier, f"produit inconnu : {produit_id}"))
                continue
            if langue is None:
                continue
            ligne = langue.disclosure.pour_reseau(produit.network)
            if channel.lang not in produit.disclosure_override and not ligne.strip():
                problemes.append(
                    Probleme(
                        fichier,
                        f"produit {produit_id} ({produit.network}) : aucune ligne de "
                        f"divulgation en {channel.lang} (CONFORMITE § 3)",
                    )
                )
        if channel.derive_from:
            parent = cfg.channels.get(channel.derive_from)
            if parent is None:
                problemes.append(Probleme(fichier, f"derive_from inconnu : {channel.derive_from}"))
            elif parent.derive_from:
                problemes.append(
                    Probleme(fichier, "derive_from : la parenté est d'un seul niveau")
                )
        if channel.google_account.alias != channel.id:
            problemes.append(
                Probleme(fichier, "google_account.alias devrait valoir l'identifiant de chaîne",
                         "avertissement")
            )
        attendu = f"secrets/tokens/{channel.id}.json"
        if channel.google_account.token_ref != attendu:
            problemes.append(
                Probleme(fichier, f"token_ref attendu {attendu} (chemin fixé par l'étape 14)",
                         "avertissement")
            )
        deja = voix_prises.get((channel.lang, channel.voice_id))
        if deja:
            problemes.append(
                Probleme(
                    fichier,
                    f"voix « {channel.voice_id} » déjà employée par {deja} dans la même "
                    "langue : deux chaînes qui parlent de la même voix signent l'exploitation "
                    "commune (CONFORMITE § 5)",
                )
            )
        else:
            voix_prises[(channel.lang, channel.voice_id)] = channel.id
        precedente = couples.get((channel.lang, channel.niche))
        if precedente:
            problemes.append(
                Probleme(
                    fichier,
                    f"même langue et même niche que {precedente} : risque de clonage "
                    "(CONFORMITE § 5), les assets de premier plan ne doivent jamais être partagés",
                    "avertissement",
                )
            )
        else:
            couples[(channel.lang, channel.niche)] = channel.id

    if cfg.team is not None:
        for relecteur in cfg.team.relecteurs:
            inconnues = sorted(set(relecteur.langues) - set(cfg.languages))
            if inconnues:
                problemes.append(
                    Probleme("team.yaml", f"{relecteur.id} : langues inconnues {inconnues}")
                )
    for channel in cfg.channels.values():
        if cfg.team and not any(
            channel.lang in r.langues for r in cfg.team.relecteurs
        ) and not channel.auto_approve:
            problemes.append(
                Probleme(
                    f"channels/{channel.id}.yaml",
                    f"aucun relecteur ne lit le {channel.lang} : le run resterait bloqué en "
                    "attente de relecture",
                )
            )
    return problemes


def _taxonomie_hooks() -> set[str]:
    """Types de hook du référentiel ; ensemble vide si le référentiel est absent."""
    fichier = racine_projet() / "registre" / "REFERENTIEL.json"
    if not fichier.is_file():
        return set()
    try:
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    taxonomie = donnees.get("hooks_taxonomie", {})
    if isinstance(taxonomie, dict):
        return set(taxonomie)
    return {t.get("id", "") for t in taxonomie if isinstance(t, dict)}


def valider(racine: Path | None = None) -> list[Probleme]:
    """Valide toute la configuration sans lever. Retourne erreurs et avertissements."""
    return charger(racine, strict=False).problemes


def valider_fichier(fichier: Path, kind: str | None = None) -> list[Probleme]:
    """Valide un seul fichier, hors de son dossier. Le genre est déduit si besoin."""
    if not fichier.is_file():
        return [Probleme(str(fichier), "fichier introuvable")]
    genre = kind or _deduire_genre(fichier)
    if genre is None:
        return [
            Probleme(
                fichier.name,
                "genre indéterminé : passe --kind parmi "
                f"{sorted(list(DOSSIERS) + list(FICHIERS))}",
            )
        ]
    if genre in DOSSIERS:
        modele, cle = DOSSIERS[genre]
        objet, problemes = charger_fichier(fichier, modele, None)
        if objet is not None:
            cfg = charger(strict=False)
            setattr(cfg, genre, {**getattr(cfg, genre), getattr(objet, cle): objet})
            problemes.extend(p for p in croiser(cfg) if fichier.stem in p.fichier)
        return problemes
    modele_unique = FICHIERS[genre]
    _, problemes = charger_fichier(fichier, modele_unique)
    return problemes


def _deduire_genre(fichier: Path) -> str | None:
    """Déduit le genre d'un fichier de configuration : dossier parent, puis clés présentes."""
    if fichier.parent.name in DOSSIERS:
        return fichier.parent.name
    if fichier.name in FICHIERS:
        return fichier.name
    try:
        brut = _lire_yaml(fichier)
    except (yaml.YAMLError, ValueError, OSError):
        return None
    signatures: list[tuple[str, set[str]]] = [
        ("channels", {"charte", "cadence", "voice_id", "google_account"}),
        ("languages", {"voices", "disclosure", "asr"}),
        ("styles", {"engine", "backend", "statut"}),
        ("products", {"network", "tracking_id", "target_url"}),
        ("niches", {"rythme_coupe_s", "duree_s", "mots_par_minute"}),
        ("team.yaml", {"relecteurs"}),
        ("qc.yaml", {"poids", "seuils"}),
        ("editorial.yaml", {"topics_queue", "dedupe"}),
        ("economics.yaml", {"tarif_kwh_eur"}),
    ]
    cles = set(brut)
    for genre, marqueurs in signatures:
        if cles & marqueurs:
            return genre
    return None


# --------------------------------------------------------------------------------------
# Identifiants de run
# --------------------------------------------------------------------------------------


def nouvelle_graine() -> int:
    """Tire une graine de 64 bits. Tirée une fois par run, jamais retirée."""
    return _secrets.randbits(64)


def generer_video_id(channel_id: str, seed: int, jour: date | None = None) -> str:
    """`<channel_id>-<AAAAMMJJ>-<4 caractères>` dérivés de la graine (ARCHITECTURE § 3.1)."""
    if not channel_id:
        raise ValueError("channel_id vide")
    jour = jour or datetime.now(UTC).date()
    empreinte = hashlib.sha256(f"{channel_id}:{jour:%Y%m%d}:{seed}".encode()).digest()
    entier = int.from_bytes(empreinte[:8], "big")
    suffixe = ""
    for _ in range(4):
        entier, reste = divmod(entier, len(ALPHABET_ID))
        suffixe += ALPHABET_ID[reste]
    return f"{channel_id}-{jour:%Y%m%d}-{suffixe}"


def video_id_libre(video_id: str, racine: Path | None = None, conn: Any = None) -> bool:
    """Vrai si l'identifiant n'existe ni sur disque ni en base (ARCHITECTURE § 3.1)."""
    if RunPaths.depuis_video_id(video_id, racine).existe():
        return False
    if conn is not None:
        ligne = conn.execute(
            "SELECT 1 FROM runs WHERE video_id = ?", (video_id,)
        ).fetchone()
        if ligne is not None:
            return False
    return True


def attribuer_video_id(
    channel_id: str, seed: int, jour: date | None = None,
    racine: Path | None = None, conn: Any = None,
) -> str:
    """Identifiant libre pour ce jour : la graine est dérivée jusqu'à en trouver un."""
    graine = seed
    for _ in range(64):
        video_id = generer_video_id(channel_id, graine, jour)
        if video_id_libre(video_id, racine, conn):
            return video_id
        graine = int.from_bytes(hashlib.sha256(str(graine).encode()).digest()[:8], "big")
    raise RuntimeError(f"aucun identifiant libre pour {channel_id} après 64 tentatives")


def verifier_spec(spec: VideoSpec, cfg: ConfigSet) -> list[Probleme]:
    """Vérifie un `spec.json` contre la configuration chargée."""
    problemes: list[Probleme] = []
    fichier = f"runs/{spec.video_id}/spec.json"
    channel = cfg.channels.get(spec.channel_id)
    if channel is None:
        return [Probleme(fichier, f"chaîne inconnue : {spec.channel_id}")]
    if spec.lang != channel.lang:
        problemes.append(
            Probleme(fichier, f"lang {spec.lang} ≠ lang de la chaîne {channel.lang}")
        )
    if spec.niche != channel.niche:
        problemes.append(Probleme(fichier, f"niche {spec.niche} ≠ niche de la chaîne", "avertissement"))
    if spec.style not in cfg.styles:
        problemes.append(Probleme(fichier, f"style inconnu : {spec.style}"))
    if spec.product_id and spec.product_id not in cfg.products:
        problemes.append(Probleme(fichier, f"produit inconnu : {spec.product_id}"))
    if spec.product_id and spec.product_id not in channel.products:
        problemes.append(
            Probleme(fichier, f"produit {spec.product_id} non configuré sur {channel.id}")
        )
    return problemes
