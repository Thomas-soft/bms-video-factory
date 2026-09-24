"""Percées, regroupement des thèmes, trous dans l'offre, file de sujets notée.

Quatre mesures, quatre statuts épistémiques — et le rapport les sépare toujours :

  - **percée** — mesurée dans l'entrepôt : une vidéo dont les vues valent au moins
    trois fois la médiane de sa chaîne **à âge comparable** (±30 %). C'est la seule
    grandeur de ce module qui ne dépende d'aucun modèle.
  - **cluster** — produit d'un modèle d'embeddings et d'un seuil de distance. Deux
    seuils différents donnent deux découpages : le nombre de clusters n'est pas un
    fait du monde, c'est une conséquence de `topics.regroupement.seuil_distance`.
  - **trou** — une absence dans **l'échantillon suivi**, jamais dans « YouTube ».
    74 chaînes ne sont pas le marché, et le rapport le répète à chaque chiffre.
  - **score** — une pondération d'opinions documentées (`config/editorial.yaml`),
    utile pour ordonner des candidats, jamais pour prouver qu'un sujet est bon.

Ce que le module ne fait jamais : reprendre un titre de concurrent. Un sujet est un
**thème** (libellé produit par le LLM à partir d'un groupe de vidéos) plus un
**angle propre** ; toute proposition qui ressemble à plus de 0,95 en cosinus à un
titre source est reformulée, puis écartée si elle colle encore (`CONFORMITE` § 4-5).
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from factory.core.paths import dossier_config, racine_projet
from factory.editorial import embed as em

import yaml

#: Statuts de la file. Seul un humain fait passer `proposed` à `approved` ou `banned`.
STATUTS = ("proposed", "approved", "used", "banned")


def charger_config(racine: Path | None = None) -> dict:
    chemin = dossier_config(racine) / "editorial.yaml"
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))


def maintenant() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ------------------------------------------------------------------------- corpus


@dataclass
class Video:
    """Une vidéo de l'entrepôt, dans la fenêtre d'observation."""

    video_id: str
    channel_id: str
    channel_title: str | None
    niche: str | None
    lang: str
    title: str
    description_head: str | None
    published_at: str | None
    age_days: float
    views: int
    velocity: float | None
    views_d7: float | None
    views_d30: float | None
    # renseignés par `marquer_percees`
    ratio: float | None = None
    n_comparables: int = 0
    percee: bool = False
    base_ratio: str = "non notée"
    #: Vélocité rapportée à la médiane des vidéos du **même décile d'âge** du corpus.
    #: Sans elle, « les vidéos récentes du cluster vont plus vite » est vrai partout.
    velocity_index: float | None = None

    @property
    def texte(self) -> str:
        return em.texte_de(self.title, self.description_head)


def corpus(conn: sqlite3.Connection, *, fenetre_jours: int) -> list[Video]:
    """Vidéos de la fenêtre, avec leur vélocité. Requête ciblée : jamais `SELECT *`."""
    lignes = conn.execute(
        """SELECT vv.video_id, vv.channel_id, vv.channel_title, vv.niche,
                  COALESCE(vv.lang, 'en') AS lang, vv.title, ve.description_head,
                  vv.published_at, vv.age_days, vv.views, vv.velocity,
                  vv.views_d7, vv.views_d30
             FROM v_video_velocity vv
             JOIN videos_ext ve ON ve.video_id = vv.video_id
            WHERE vv.age_days IS NOT NULL AND vv.age_days <= ?
              AND vv.views IS NOT NULL AND vv.title IS NOT NULL""",
        (fenetre_jours,),
    ).fetchall()
    return [
        Video(
            video_id=r[0], channel_id=r[1], channel_title=r[2], niche=r[3], lang=r[4],
            title=r[5], description_head=r[6], published_at=r[7], age_days=float(r[8]),
            views=int(r[9]), velocity=r[10], views_d7=r[11], views_d30=r[12],
        )
        for r in lignes
    ]


def _population_par_chaine(conn: sqlite3.Connection) -> dict[str, list[tuple[float, float]]]:
    """(âge, vues) de **toutes** les vidéos de chaque chaîne, fenêtre comprise ou non.

    La médiane de référence se calcule sur tout le catalogue de la chaîne : restreindre
    la référence à 180 jours comparerait les percées récentes aux seules percées récentes.
    """
    par_chaine: dict[str, list[tuple[float, float]]] = {}
    for cid, age, vues in conn.execute(
        """SELECT channel_id, age_days, views FROM v_video_velocity
            WHERE age_days IS NOT NULL AND views IS NOT NULL"""
    ):
        par_chaine.setdefault(cid, []).append((float(age), float(vues)))
    return par_chaine


def marquer_percees(
    videos: list[Video], population: dict[str, list[tuple[float, float]]], reglages: dict
) -> dict:
    """Ratio à la médiane de la chaîne dans une fenêtre d'âge de ±`fenetre_age_relative`.

    Rend un compte rendu : combien de percées, combien de vidéos non notées faute de
    comparables, et sur quelle base (`views_dN` exacte ou vues observées).
    """
    seuil = float(reglages["seuil_ratio"])
    marge = float(reglages["fenetre_age_relative"])
    mini = int(reglages["min_comparables"])
    preferer = bool(reglages.get("preferer_dN", True))

    n_percees = n_non_notees = n_exactes = 0
    for v in videos:
        voisins = [
            vues
            for age, vues in population.get(v.channel_id, [])
            if abs(age - v.age_days) <= marge * max(v.age_days, 1.0) and vues > 0
        ]
        # La vidéo elle-même est dans la population : elle ne se compare pas à elle-même.
        if voisins:
            voisins = list(voisins)
            try:
                voisins.remove(float(v.views))
            except ValueError:
                pass
        v.n_comparables = len(voisins)
        if len(voisins) < mini:
            n_non_notees += 1
            v.base_ratio = f"non notée ({len(voisins)} comparable(s) < {mini})"
            continue
        mediane = statistics.median(voisins)
        mesure = None
        if preferer:
            for colonne, valeur in (("views_d7", v.views_d7), ("views_d30", v.views_d30)):
                if valeur is not None:
                    mesure, v.base_ratio = float(valeur), colonne
                    n_exactes += 1
                    break
        if mesure is None:
            mesure = float(v.views)
            v.base_ratio = "vues observées"
        v.ratio = mesure / mediane if mediane > 0 else None
        if v.ratio is not None and v.ratio >= seuil:
            v.percee = True
            n_percees += 1
    return {
        "seuil_ratio": seuil, "fenetre_age_relative": marge, "min_comparables": mini,
        "n_videos": len(videos), "n_percees": n_percees, "n_non_notees": n_non_notees,
        "n_sur_views_dN": n_exactes,
        "base": ("views_d7/d30 quand disponibles" if n_exactes
                 else "vues observées au dernier instantané — views_d7/d30 NULL faute "
                      "d'un second jour de collecte"),
    }


def indexer_velocite(videos: list[Video], n_deciles: int = 10) -> dict:
    """Vélocité rapportée à la médiane du décile d'âge — sans quoi toute mesure de
    résurgence mesure l'âge.

    **Mesuré le 20/09/2026 sur le corpus** : vélocité médiane de 4 736 vues/j entre 0 et
    30 jours, 227 entre 30 et 90, 150 entre 90 et 180 — un facteur 31. `velocity_life`
    vaut « vues / âge » : elle décroît mécaniquement avec l'âge parce que le pic de
    publication est amorti sur un dénominateur qui grandit. Comparer les vidéos récentes
    d'un cluster à ses vidéos anciennes **sans corriger** revient donc à comparer des
    jeunes à des vieux : 9 clusters éligibles sur 10 passaient le seuil de 1,5.
    """
    notees = sorted(
        (v for v in videos if v.velocity is not None), key=lambda v: v.age_days
    )
    if not notees:
        return {"n_deciles": 0, "medianes": []}
    taille = max(1, len(notees) // n_deciles)
    medianes = []
    for debut in range(0, len(notees), taille):
        tranche = notees[debut : debut + taille]
        med = statistics.median(v.velocity for v in tranche)  # type: ignore[misc]
        medianes.append({"age_min": round(tranche[0].age_days, 1),
                         "age_max": round(tranche[-1].age_days, 1),
                         "velocite_mediane": round(med, 1), "n": len(tranche)})
        for v in tranche:
            v.velocity_index = (v.velocity / med) if med > 0 else None  # type: ignore[operator]
    return {"n_deciles": len(medianes), "medianes": medianes}


# -------------------------------------------------------------------- regroupement


@dataclass
class Cluster:
    cluster_id: str
    videos: list[Video]
    centroide: list[float]
    label: str | None = None
    langues: list[str] = field(default_factory=list)
    n_percees: int = 0
    vues_totales: int = 0
    velocite_mediane: float | None = None
    age_median: float = 0.0
    gap_type: str = ""
    gap_detail: str = ""
    demande_seed: str | None = None
    demande_vues_mois: float | None = None
    # remplis par la notation
    force: float = 0.0
    velocite_normalisee: float = 0.0
    demande_normalisee: float = 0.0

    @property
    def n_videos(self) -> int:
        return len(self.videos)

    @property
    def n_chaines(self) -> int:
        return len({v.channel_id for v in self.videos})

    @property
    def part_percees(self) -> float:
        return self.n_percees / self.n_videos if self.n_videos else 0.0

    def percees_en(self, langues: set[str]) -> list[Video]:
        return [v for v in self.videos if v.percee and v.lang in langues]

    def videos_en(self, langue: str) -> list[Video]:
        return [v for v in self.videos if v.lang == langue]

    def exemples(self, n: int = 3) -> list[Video]:
        return sorted(self.videos, key=lambda v: v.views, reverse=True)[:n]


def regrouper(vecteurs: list[list[float]], seuil_distance: float) -> list[int]:
    """Agglomératif, cosinus, lien moyen — déterministe, sans classe « bruit ».

    Choix du rapport de veille du 20/09/2026 contre HDBSCAN, qui range 30 % et plus des
    titres courts en bruit. Aucune réduction de dimension : UMAP est stochastique et
    déforme précisément les distances que cet algorithme compare.
    """
    if len(vecteurs) < 2:
        return [0] * len(vecteurs)
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering

    X = np.asarray(vecteurs, dtype=np.float32)
    modele = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage="average",
        distance_threshold=float(seuil_distance),
    )
    return [int(e) for e in modele.fit_predict(X)]


def _centroide(vecteurs: list[list[float]]) -> list[float]:
    n = len(vecteurs)
    somme = [0.0] * len(vecteurs[0])
    for v in vecteurs:
        for i, x in enumerate(v):
            somme[i] += x
    return em.normaliser([x / n for x in somme])


def construire_clusters(
    videos: list[Video], vecteurs: list[list[float]], etiquettes: list[int], taille_min: int
) -> tuple[list[Cluster], int]:
    """Clusters au-dessus de `taille_min`, triés par vues. Rend aussi le nombre d'isolés."""
    paquets: dict[int, list[int]] = {}
    for rang, e in enumerate(etiquettes):
        paquets.setdefault(e, []).append(rang)

    clusters: list[Cluster] = []
    isoles = 0
    for e, rangs in sorted(paquets.items()):
        if len(rangs) < taille_min:
            isoles += len(rangs)
            continue
        membres = [videos[r] for r in rangs]
        ages = [v.age_days for v in membres]
        velocites = [v.velocity for v in membres if v.velocity is not None]
        clusters.append(
            Cluster(
                cluster_id=f"c{e:04d}",
                videos=membres,
                centroide=_centroide([vecteurs[r] for r in rangs]),
                langues=sorted({v.lang for v in membres}),
                n_percees=sum(1 for v in membres if v.percee),
                vues_totales=sum(v.views for v in membres),
                velocite_mediane=float(statistics.median(velocites)) if velocites else None,
                age_median=float(statistics.median(ages)),
            )
        )
    clusters.sort(key=lambda c: c.vues_totales, reverse=True)
    return clusters, isoles


# --------------------------------------------------------------------------- trous


def detecter_trous(clusters: list[Cluster], reglages: dict, fenetre_jours: int) -> dict:
    """Les trois familles de trous, dans l'ordre de valeur : multilingue, demande, résurgence.

    Un cluster porte **au plus un** type de trou : le premier qui se déclenche, dans cet
    ordre. Cumuler les lacunes ferait compter deux fois la même absence.
    """
    ml = reglages["multilingue"]
    dem = reglages["demande"]
    res = reglages["resurgence"]
    sources = set(ml["langues_source"])
    cible = ml["langue_cible"]
    # Seuil de « demande élevée » : un percentile des clusters de CETTE exécution, pas une
    # valeur absolue — les niveaux Wikipédia n'ont pas d'échelle commune entre niches.
    connus = sorted(c.demande_vues_mois for c in clusters if c.demande_vues_mois is not None)
    pct = float(dem.get("percentile_demande_min", 60)) / 100.0
    seuil_demande = connus[min(int(pct * len(connus)), len(connus) - 1)] if connus else None

    comptes = {"multilingue": 0, "demande": 0, "resurgence": 0}
    for c in clusters:
        percees_source = c.percees_en(sources)
        n_cible = len(c.videos_en(cible))
        if len(percees_source) >= int(ml["min_percees_source"]) and n_cible <= int(
            ml["max_videos_cible"]
        ):
            c.gap_type = "multilingue"
            langues = sorted({v.lang for v in percees_source})
            c.gap_detail = (
                f"{len(percees_source)} percée(s) en {'/'.join(langues)} pour "
                f"{n_cible} vidéo(s) en {cible} chez les chaînes suivies"
            )
            comptes["multilingue"] += 1
            continue
        recentes = [
            v for v in c.videos if v.age_days <= float(dem["fenetre_recente_jours"])
        ]
        if (
            seuil_demande is not None
            and c.demande_vues_mois is not None
            and c.demande_vues_mois >= seuil_demande
            and len(recentes) < int(dem["max_videos_recentes"])
        ):
            c.gap_type = "demande"
            c.gap_detail = (
                f"{len(recentes)} vidéo(s) de moins de {dem['fenetre_recente_jours']} j "
                f"chez les chaînes suivies, pour une demande de "
                f"{c.demande_vues_mois:,.0f} vues Wikipédia/mois "
                f"(seed « {c.demande_seed} »)".replace(",", " ")
            )
            comptes["demande"] += 1
            continue
        if c.age_median >= float(res["age_median_min_jours"]):
            jeunes = [v for v in c.videos if v.age_days <= fenetre_jours / 2]
            if len(jeunes) >= int(res["min_videos_recentes"]):
                # Indice de vélocité, PAS vélocité brute : voir `indexer_velocite`.
                v_jeunes = [v.velocity_index for v in jeunes if v.velocity_index is not None]
                v_vieux = [
                    v.velocity_index for v in c.videos
                    if v.age_days > fenetre_jours / 2 and v.velocity_index is not None
                ]
                if v_jeunes and v_vieux:
                    m_j, m_v = statistics.median(v_jeunes), statistics.median(v_vieux)
                    if m_v > 0 and m_j / m_v >= float(res["ratio_velocite_min"]):
                        c.gap_type = "resurgence"
                        c.gap_detail = (
                            f"indice de vélocité {m_j:.2f} sur {len(jeunes)} vidéo(s) "
                            f"récente(s) contre {m_v:.2f} sur {len(v_vieux)} ancienne(s) "
                            f"(×{m_j / m_v:.1f}) — indice = vélocité / médiane du décile "
                            f"d'âge, sans quoi la mesure ne mesure que l'âge"
                        )
                        comptes["resurgence"] += 1
    comptes["seuil_demande_vues_mois"] = seuil_demande
    return comptes


# ------------------------------------------------------------------------- demande


def rattacher_demande(
    clusters: list[Cluster], cfg: dict, *, lang: str, racine: Path | None, echo=None
) -> dict:
    """Niveau de demande d'un cluster = celui du seed Wikipédia le plus proche.

    Aucun appel réseau neuf : les séries des 85 seeds de l'étape 19 sont **déjà** en
    cache disque (`workspace/cache/demand/`). Ce que la mesure vaut : les lecteurs de
    Wikipédia ne sont pas les spectateurs de YouTube — c'est un proxy, comme en 19.
    """
    from factory.editorial import demand as dm

    seeds: list[str] = []
    for definition in (cfg.get("niches_notees") or {}).values():
        seeds.extend(definition.get("seeds_wikipedia") or [])
    seeds = sorted(set(seeds))
    if not seeds or not clusters:
        return {"n_seeds": 0, "n_seeds_avec_donnees": 0, "appels_reseau": 0}

    niveaux: dict[str, float] = {}
    appels = 0
    for seed in seeds:
        en_cache = dm.lire_cache("wikimedia", f"{seed}|en.wikipedia|24", racine=racine)
        if en_cache is None:
            appels += 1
        points = dm.pageviews_mensuels(seed, "en.wikipedia", n_mois=24, racine=racine)
        points, _ = dm.couper_queue_incomplete(points)
        if points:
            niveaux[seed] = float(statistics.median(v for _, v in points))

    connus = [s for s in seeds if s in niveaux]
    if not connus:
        return {"n_seeds": len(seeds), "n_seeds_avec_donnees": 0, "appels_reseau": appels}

    vecteurs_seeds = em.embed(connus, racine=racine, echo=echo)
    for c in clusters:
        meilleurs = max(
            range(len(connus)), key=lambda i: em.similarite(c.centroide, vecteurs_seeds[i])
        )
        c.demande_seed = connus[meilleurs]
        c.demande_vues_mois = niveaux[connus[meilleurs]]
    return {
        "n_seeds": len(seeds), "n_seeds_avec_donnees": len(connus), "appels_reseau": appels,
        "source": "Wikimedia Pageviews (cache de l'étape 19), médiane sur 24 mois",
    }


# ------------------------------------------------------------------ normalisation


def _minmax(valeurs: list[float | None]) -> list[float]:
    connues = [v for v in valeurs if v is not None]
    if not connues:
        return [0.0] * len(valeurs)
    bas, haut = min(connues), max(connues)
    if haut - bas < 1e-12:
        return [0.5 if v is not None else 0.0 for v in valeurs]
    return [0.0 if v is None else (v - bas) / (haut - bas) for v in valeurs]


def normaliser_clusters(clusters: list[Cluster]) -> None:
    """Force, vélocité et demande ramenées à 0-1, min-max **sur cette exécution**.

    Échelle relative, comme en 19 : 1,0 veut dire « le meilleur de ce tirage », pas
    « bon dans l'absolu ». Retirer un cluster recalcule les autres.
    """
    forces = _minmax([math.log10(c.vues_totales + 1) for c in clusters])
    velocites = _minmax([
        math.log10(c.velocite_mediane + 1) if c.velocite_mediane else None for c in clusters
    ])
    demandes = _minmax([
        math.log10(c.demande_vues_mois + 1) if c.demande_vues_mois else None for c in clusters
    ])
    for c, f, v, d in zip(clusters, forces, velocites, demandes, strict=True):
        c.force, c.velocite_normalisee, c.demande_normalisee = f, v, d


# ----------------------------------------------------------------- libellés (LLM)


SCHEMA_LIBELLES = {
    "type": "object",
    "required": ["labels"],
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label"],
                "properties": {"id": {"type": "string"}, "label": {"type": "string"}},
            },
        }
    },
}

SYSTEME_LIBELLE = (
    "You name themes. Given a group of YouTube video titles in several languages, you "
    "produce ONE English theme label of at most five words. A label names the SUBJECT, "
    "never a title: no numbers from the titles, no clickbait, no question marks, no "
    "quotation marks. Answer with JSON only."
)


def _nettoyer_label(brut: str) -> str:
    texte = re.sub(r"[\"'`]", "", (brut or "")).strip().strip(".!?")
    texte = re.sub(r"\s+", " ", texte)
    mots = texte.split(" ")[:5]
    return " ".join(mots)[:200]


def libeller(
    clusters: list[Cluster], *, lot: int, racine: Path | None = None, echo=None, trace=None
) -> int:
    """Libellé de 5 mots par cluster, par lots. Repli déterministe si le LLM échoue."""
    from factory import llm

    faits = 0
    for debut in range(0, len(clusters), lot):
        tranche = clusters[debut : debut + lot]
        blocs = []
        for c in tranche:
            titres = " | ".join(v.title[:90] for v in c.exemples(4))
            blocs.append(f'- id "{c.cluster_id}" ({c.n_videos} videos): {titres}')
        prompt = (
            "Name each group of videos with one English theme label of at most five "
            "words.\n\n" + "\n".join(blocs) + "\n\n"
            'Answer: {"labels": [{"id": "...", "label": "..."}, ...]} — one entry per id.'
        )
        if echo:
            echo(f"libellés {debut + 1}-{debut + len(tranche)} / {len(clusters)}")
        try:
            donnees, _ = llm.generate_json(
                prompt, system=SYSTEME_LIBELLE, json_schema=SCHEMA_LIBELLES,
                max_tokens=80 * len(tranche) + 120, temperature=0.3,
                etiquette="topics:label", trace=trace, racine=racine,
            )
        except Exception as exc:  # noqa: BLE001 — le repli vaut mieux qu'un arrêt
            if echo:
                echo(f"[jaune] libellés indisponibles ({exc}) — repli lexical")
            donnees = {"labels": []}
        par_id = {
            str(e.get("id")): _nettoyer_label(str(e.get("label", "")))
            for e in (donnees.get("labels") or [])
            if isinstance(e, dict)
        }
        for c in tranche:
            label = par_id.get(c.cluster_id) or ""
            if not label:
                # Repli : les mots les plus fréquents des titres du cluster. Moins bon,
                # mais traçable — et le rapport signale un libellé de repli par « ~ ».
                label = "~ " + _mots_saillants(c)
            c.label = label
            faits += 1
    return faits


_VIDES = {
    "the", "a", "an", "of", "and", "to", "in", "for", "on", "with", "is", "are", "was",
    "how", "why", "what", "que", "qui", "les", "des", "une", "der", "die", "del", "la",
    "el", "il", "di", "da", "che", "you", "your", "this", "that", "from", "it", "s",
}


def _mots_saillants(c: Cluster, n: int = 4) -> str:
    compte: dict[str, int] = {}
    for v in c.videos:
        for mot in re.findall(r"[\w']+", v.title.lower()):
            if len(mot) > 2 and mot not in _VIDES and not mot.isdigit():
                compte[mot] = compte.get(mot, 0) + 1
    tete = sorted(compte.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
    return " ".join(m for m, _ in tete) or "sujet sans libellé"


# ------------------------------------------------------------------- angles (LLM)


SCHEMA_ANGLES = {
    "type": "object",
    "required": ["topics"],
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "topic", "angles"],
                "properties": {
                    "id": {"type": "string"},
                    "topic": {"type": "string"},
                    "angles": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type", "angle"],
                            "properties": {
                                "type": {"type": "string"},
                                "angle": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }
    },
}


#: Le code ISO ne suffit pas au 9B : « a channel in en » lui a fait rendre des sujets en
#: français sur les clusters d'origine française (mesuré le 20/09/2026). C'est précisément
#: ce que le trou multilingue doit éviter : un thème FR se produit **en anglais**.
NOM_LANGUE = {"en": "English", "fr": "French", "es": "Spanish", "it": "Italian"}


def systeme_angles(channel, types_angle: list[str]) -> str:
    """Persona de la chaîne : sa niche, son style, sa langue. Jamais un titre de concurrent."""
    langue = NOM_LANGUE.get(channel.lang, channel.lang)
    return (
        f"You are the editorial lead of «{channel.name}», a faceless YouTube channel on "
        f"«{channel.niche}», visual style «{channel.style}». "
        f"WRITE EVERYTHING IN {langue.upper()}. Some themes come from videos in French, "
        f"Spanish or Italian; you still answer in {langue}, always, without exception — "
        f"the point is to produce in {langue} what works elsewhere. "
        "For each theme you receive, you write ONE original topic line and TWO distinct "
        f"angles chosen among: {', '.join(types_angle)}. "
        "An angle is one sentence saying what the video argues or tests — not a title, "
        "not a hook, not a question. Never reuse or paraphrase a competitor's title: the "
        "theme is shared, the treatment is ours. Answer with JSON only."
    )


def proposer_angles(
    clusters: list[Cluster], channel, reglages: dict, *,
    racine: Path | None = None, echo=None, trace=None,
) -> dict[str, dict]:
    """Un sujet propre et deux angles par cluster, pour cette chaîne. Rend {cluster_id: {…}}."""
    from factory import llm

    types_angle = list(reglages["types_angle"])
    lot = int(reglages["lot_angles"])
    resultat: dict[str, dict] = {}
    for debut in range(0, len(clusters), lot):
        tranche = clusters[debut : debut + lot]
        blocs = []
        for c in tranche:
            preuve = f"{c.n_videos} videos, {c.n_chaines} channels, {c.vues_totales:,} views"
            if c.gap_type:
                preuve += f", gap: {c.gap_type}"
            blocs.append(f'- id "{c.cluster_id}" — theme «{c.label}» ({preuve.replace(",", " ")})')
        langue = NOM_LANGUE.get(channel.lang, channel.lang)
        prompt = (
            "Themes observed among competitors:\n" + "\n".join(blocs) + "\n\n"
            f"For each id give an original topic line IN {langue.upper()} (max 120 "
            "characters, no numbers copied from competitors) and two angles, also in "
            f"{langue}.\n"
            '{"topics": [{"id": "...", "topic": "...", "angles": '
            '[{"type": "...", "angle": "..."}, {"type": "...", "angle": "..."}]}]}'
        )
        if echo:
            echo(f"angles {debut + 1}-{debut + len(tranche)} / {len(clusters)} — {channel.id}")
        try:
            donnees, _ = llm.generate_json(
                prompt, system=systeme_angles(channel, types_angle),
                json_schema=SCHEMA_ANGLES, max_tokens=190 * len(tranche) + 150,
                temperature=0.6, etiquette="topics:angles", trace=trace, racine=racine,
            )
        except Exception as exc:  # noqa: BLE001
            if echo:
                echo(f"[jaune] angles indisponibles ({exc}) — repli sur le libellé")
            donnees = {"topics": []}
        for entree in donnees.get("topics") or []:
            if not isinstance(entree, dict):
                continue
            cid = str(entree.get("id", ""))
            angles = [
                {"type": str(a.get("type", "")).strip()[:40],
                 "angle": re.sub(r"\s+", " ", str(a.get("angle", ""))).strip()[:400]}
                for a in (entree.get("angles") or [])
                if isinstance(a, dict) and str(a.get("angle", "")).strip()
            ]
            sujet = re.sub(r"\s+", " ", str(entree.get("topic", ""))).strip().strip('"')[:200]
            if cid and sujet and angles:
                resultat[cid] = {"topic": sujet, "angles": angles[:2]}
    return resultat


# -------------------------------------------------------------------- notation


@dataclass
class Sujet:
    channel_id: str
    lang: str
    niche: str | None
    cluster_id: str
    topic: str
    angle: str
    score: float
    evidence: dict


def _fit(cluster: Cluster, channel, vecteur_niche: list[float] | None) -> tuple[float, str]:
    """Proximité cluster / chaîne : étiquette de niche d'abord, embeddings ensuite."""
    niches = {v.niche for v in cluster.videos if v.niche}
    if channel.niche in niches:
        part = sum(1 for v in cluster.videos if v.niche == channel.niche) / cluster.n_videos
        return min(1.0, 0.6 + 0.4 * part), f"niche {channel.niche} sur {part * 100:.0f} % du cluster"
    if vecteur_niche is None:
        return 0.0, "aucune mesure de proximité (mots-clés de niche absents)"
    cos = em.similarite(cluster.centroide, vecteur_niche)
    return max(0.0, min(1.0, cos)), f"cosinus aux mots-clés de la niche {cos:.2f}"


def noter(
    clusters: list[Cluster], channel, reglages: dict, *,
    vecteur_niche: list[float] | None, sujets_bms: list[tuple[str, list[float]]],
    angles: dict[str, dict],
) -> list[Sujet]:
    """Score = pondération des cinq composantes, moins le malus de répétition."""
    poids = reglages["ponderations"]
    bareme = reglages["bareme_lacune"]
    malus_cfg = reglages["malus_similarite"]
    sujets: list[Sujet] = []
    for c in clusters:
        propose = angles.get(c.cluster_id)
        if not propose:
            continue
        lacune = float(bareme.get(c.gap_type or "aucune", 0.0))
        fit, fit_txt = _fit(c, channel, vecteur_niche)
        composantes = {
            "force_cluster": c.force, "velocite": c.velocite_normalisee,
            "lacune": lacune, "demande": c.demande_normalisee, "fit": fit,
        }
        brut = sum(float(poids[k]) * v for k, v in composantes.items())
        for a in propose["angles"]:
            sujets.append(
                Sujet(
                    channel_id=channel.id, lang=channel.lang, niche=channel.niche,
                    cluster_id=c.cluster_id, topic=propose["topic"],
                    angle=f"{a['type']} — {a['angle']}" if a["type"] else a["angle"],
                    score=round(brut, 4),
                    evidence={
                        "cluster_id": c.cluster_id, "label": c.label,
                        "composantes": {k: round(v, 4) for k, v in composantes.items()},
                        "ponderations": dict(poids),
                        "score_avant_malus": round(brut, 4),
                        "fit": fit_txt,
                        "n_videos": c.n_videos, "n_chaines": c.n_chaines,
                        "vues_totales": c.vues_totales, "n_percees": c.n_percees,
                        "part_percees": round(c.part_percees, 3),
                        "langues": c.langues, "age_median_jours": round(c.age_median, 1),
                        "velocite_mediane": (round(c.velocite_mediane, 1)
                                             if c.velocite_mediane else None),
                        "gap_type": c.gap_type or None, "gap_detail": c.gap_detail or None,
                        "demande_seed": c.demande_seed,
                        "demande_vues_mois": (round(c.demande_vues_mois)
                                              if c.demande_vues_mois else None),
                        "type_angle": a["type"],
                        "videos_sources": [
                            {"video_id": v.video_id, "chaine": v.channel_title or v.channel_id,
                             "lang": v.lang, "vues": v.views,
                             "ratio": round(v.ratio, 2) if v.ratio else None,
                             "percee": v.percee, "base_ratio": v.base_ratio}
                            for v in c.exemples(3)
                        ],
                    },
                )
            )
    return _appliquer_malus(sujets, sujets_bms, malus_cfg)


def _appliquer_malus(
    sujets: list[Sujet], sujets_bms: list[tuple[str, list[float]]], reglages: dict
) -> list[Sujet]:
    """Malus de répétition : similarité aux sujets **déjà produits par BMS**.

    Sous le seuil, aucun malus. Au-dessus, il croît linéairement jusqu'au poids plein
    à la similarité 1,0 — un sujet identique perd donc `poids` points de score.
    """
    seuil = float(reglages["seuil"])
    poids = float(reglages["poids"])
    if not sujets or not sujets_bms:
        for s in sujets:
            s.evidence["malus_similarite"] = {"valeur": 0.0, "plus_proche": None,
                                              "note": "aucun sujet BMS produit"}
        return sorted(sujets, key=lambda s: s.score, reverse=True)

    vecteurs = em.embed([s.topic for s in sujets])
    for s, vec in zip(sujets, vecteurs, strict=True):
        proche, cos = max(
            ((titre, em.similarite(vec, v)) for titre, v in sujets_bms), key=lambda kv: kv[1]
        )
        malus = poids * (cos - seuil) / (1.0 - seuil) if cos > seuil else 0.0
        s.score = round(max(0.0, s.score - malus), 4)
        s.evidence["malus_similarite"] = {
            "valeur": round(malus, 4), "cosinus": round(cos, 3),
            "plus_proche": proche, "seuil": seuil, "poids": poids,
        }
    return sorted(sujets, key=lambda s: s.score, reverse=True)


# ------------------------------------------- anti-reprise de titre de concurrent


def proteger_titres(
    sujets: list[Sujet], clusters: list[Cluster], seuil: float, *,
    conn: sqlite3.Connection | None = None,
    racine: Path | None = None, echo=None, trace=None,
) -> tuple[list[Sujet], list[dict]]:
    """Aucun titre de concurrent repris tel quel : > `seuil` en cosinus → reformulation.

    Une passe de reformulation par le LLM, puis **abandon** si la proposition colle
    encore. Un sujet écarté est rapporté, jamais remplacé par une invention.
    """
    from factory import llm

    par_cluster = {c.cluster_id: c for c in clusters}
    titres: list[str] = []
    origine: list[str] = []
    for c in clusters:
        for v in c.videos:
            titres.append(v.title)
            origine.append(f"{v.channel_title or v.channel_id} / {v.video_id}")
    if not sujets or not titres:
        return sujets, []

    # Vecteurs du TITRE SEUL, pas de « titre + description » : la garde porte sur la
    # reprise d'un titre. Cache séparé (suffixe `#titre`) pour ne pas recalculer 5 600
    # vecteurs à chaque exécution, et pour ne pas écraser ceux du regroupement.
    if conn is not None:
        ids = [v.video_id for c in clusters for v in c.videos]
        vec_titres = em.embed_videos(
            conn, list(zip(ids, titres, strict=True)),
            modele=f"{em.MODELE_DEFAUT}#titre", racine=racine, echo=echo,
        ).vecteurs
    else:
        vec_titres = em.embed(titres, racine=racine, echo=echo)
    incidents: list[dict] = []

    def plus_proche(vec: list[float]) -> tuple[float, int]:
        i = max(range(len(vec_titres)), key=lambda k: em.similarite(vec, vec_titres[k]))
        return em.similarite(vec, vec_titres[i]), i

    vecteurs = em.embed([s.topic for s in sujets], racine=racine, echo=echo)
    a_reformuler = [
        (rang, *plus_proche(v)) for rang, v in enumerate(vecteurs)
    ]
    a_reformuler = [(r, cos, i) for r, cos, i in a_reformuler if cos > seuil]
    if not a_reformuler:
        return sujets, []

    if echo:
        echo(f"{len(a_reformuler)} sujet(s) trop proches d'un titre source — reformulation")
    for rang, cos, i in a_reformuler:
        s = sujets[rang]
        c = par_cluster.get(s.cluster_id)
        try:
            reponse = llm.generate(
                f"Rewrite this video topic so it no longer echoes any competitor title.\n"
                f"Topic: {s.topic}\nToo close to: {titres[i]}\n"
                f"Theme: {c.label if c else s.cluster_id}\n"
                "Keep the subject, change the wording and the framing. "
                "Answer with the rewritten topic line only, max 120 characters.",
                system="You rewrite topic lines. One line, no quotes, no explanation.",
                max_tokens=60, temperature=0.8, etiquette="topics:reformule", racine=racine,
            )
            if trace is not None:
                trace.ajouter(reponse)
            neuf = re.sub(r"\s+", " ", reponse.texte).strip().strip('"').split("\n")[0][:200]
        except Exception as exc:  # noqa: BLE001
            neuf, exc_txt = "", str(exc)
            incidents.append({"sujet": s.topic, "titre": titres[i], "cosinus": round(cos, 3),
                              "issue": f"reformulation impossible ({exc_txt})"})
            s.score = -1.0
            continue
        if not neuf:
            incidents.append({"sujet": s.topic, "titre": titres[i], "cosinus": round(cos, 3),
                              "issue": "reformulation vide — sujet écarté"})
            s.score = -1.0
            continue
        cos2, i2 = plus_proche(em.embed([neuf], racine=racine)[0])
        if cos2 > seuil:
            incidents.append({"sujet": s.topic, "reformule": neuf, "titre": titres[i2],
                              "cosinus": round(cos2, 3),
                              "issue": "colle encore après reformulation — sujet écarté"})
            s.score = -1.0
        else:
            incidents.append({"sujet": s.topic, "reformule": neuf, "titre": titres[i],
                              "cosinus": round(cos, 3), "issue": "reformulé"})
            s.evidence["reformulation"] = {
                "avant": s.topic, "titre_source": origine[i], "cosinus_avant": round(cos, 3),
                "cosinus_apres": round(cos2, 3),
            }
            s.topic = neuf
    gardes = [s for s in sujets if s.score >= 0]
    return gardes, incidents


# ----------------------------------------------------------------------- la file


def sujets_bms_existants(
    conn: sqlite3.Connection, *, lang: str, racine: Path | None = None
) -> list[tuple[str, list[float]]]:
    """Sujets déjà produits par BMS dans cette langue : runs **et** file déjà consommée."""
    titres: list[str] = []
    for (sujet,) in conn.execute(
        "SELECT DISTINCT topic_sujet FROM runs WHERE topic_sujet IS NOT NULL AND lang = ?",
        (lang,),
    ):
        if sujet and sujet.strip():
            titres.append(sujet.strip())
    for (sujet,) in conn.execute(
        "SELECT DISTINCT topic FROM topics_queue WHERE status = 'used' AND lang = ?", (lang,)
    ):
        if sujet and sujet.strip():
            titres.append(sujet.strip())
    titres = sorted(set(titres))
    if not titres:
        return []
    return list(zip(titres, em.embed(titres, racine=racine), strict=True))


def enregistrer(conn: sqlite3.Connection, sujets: list[Sujet], *, n_max: int) -> int:
    """Insère ou met à jour la file. Une ligne `used` ou `banned` n'est jamais réécrite."""
    maintenant_iso = maintenant()
    ecrits = 0
    for s in sujets[:n_max]:
        conn.execute(
            """INSERT INTO topics_queue
                 (channel_id, lang, niche, cluster_id, topic, angle, score,
                  evidence_json, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,'proposed',?)
               ON CONFLICT(channel_id, topic, angle) DO UPDATE SET
                 score=excluded.score, cluster_id=excluded.cluster_id,
                 evidence_json=excluded.evidence_json
               WHERE topics_queue.status IN ('proposed', 'approved')""",
            (s.channel_id, s.lang, s.niche, s.cluster_id, s.topic, s.angle, s.score,
             json.dumps(s.evidence, ensure_ascii=False), maintenant_iso),
        )
        ecrits += 1
    conn.commit()
    return ecrits


def enregistrer_clusters(
    conn: sqlite3.Connection, clusters: list[Cluster], *, jour: str | None = None
) -> int:
    jour = jour or datetime.now(UTC).date().isoformat()
    for c in clusters:
        conn.execute(
            """INSERT INTO topic_clusters
                 (cluster_id, run_date, label, n_videos, n_channels, n_breakouts,
                  views_total, velocity_median, part_breakouts, langs, age_median_days,
                  gap_type, demand_score, evidence_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(cluster_id, run_date) DO UPDATE SET
                 label=excluded.label, n_videos=excluded.n_videos,
                 n_channels=excluded.n_channels, n_breakouts=excluded.n_breakouts,
                 views_total=excluded.views_total, velocity_median=excluded.velocity_median,
                 part_breakouts=excluded.part_breakouts, langs=excluded.langs,
                 age_median_days=excluded.age_median_days, gap_type=excluded.gap_type,
                 demand_score=excluded.demand_score, evidence_json=excluded.evidence_json""",
            (c.cluster_id, jour, c.label, c.n_videos, c.n_chaines, c.n_percees,
             c.vues_totales, c.velocite_mediane, round(c.part_percees, 4),
             ",".join(c.langues), round(c.age_median, 1), c.gap_type or None,
             c.demande_vues_mois,
             json.dumps({"gap_detail": c.gap_detail, "demande_seed": c.demande_seed,
                         "exemples": [v.video_id for v in c.exemples(3)]},
                        ensure_ascii=False)),
        )
    conn.commit()
    return len(clusters)


def changer_statut(conn: sqlite3.Connection, topic_id: int, statut: str) -> dict:
    """`approve` / `ban`. Rend la ligne modifiée, ou lève si elle n'existe pas."""
    if statut not in STATUTS:
        raise ValueError(f"statut inconnu : {statut} (attendu : {', '.join(STATUTS)})")
    ligne = conn.execute(
        "SELECT id, channel_id, topic, status FROM topics_queue WHERE id = ?", (topic_id,)
    ).fetchone()
    if ligne is None:
        raise KeyError(f"aucun sujet {topic_id} dans topics_queue")
    conn.execute("UPDATE topics_queue SET status = ? WHERE id = ?", (statut, topic_id))
    conn.commit()
    return {"id": ligne[0], "channel_id": ligne[1], "topic": ligne[2],
            "avant": ligne[3], "apres": statut}


def purger(conn: sqlite3.Connection, *, taille_max: int, age_max_jours: int,
           channel_id: str | None = None) -> dict:
    """Applique `topics_queue.taille_max` et `age_max_jours` de `config/editorial.yaml`.

    Déclarés depuis l'étape 8, appliqués nulle part jusqu'ici : la file grossissait à
    chaque exécution (74 lignes après trois passages, résidu porté par `SUIVI.md` § 3
    étape 20). Deux règles, et la seconde compte autant que la première :

    * seuls les sujets **`proposed`** sont purgés. `approved` est une décision humaine,
      `used` porte le lien d'un run à son sujet, `banned` est un refus explicite : les
      effacer reviendrait à effacer ce que quelqu'un a tranché.
    * **par chaîne**, parce que `taille_max` est un plafond de file éditoriale et qu'une
      chaîne prolifique ne doit pas vider la file d'une autre.
    """
    limite = (datetime.now(UTC) - timedelta(days=age_max_jours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    chaines = ([channel_id] if channel_id else
               [str(l[0]) for l in conn.execute(
                   "SELECT DISTINCT channel_id FROM topics_queue")])
    par_age = par_plafond = 0
    for chaine in chaines:
        curseur = conn.execute(
            "DELETE FROM topics_queue WHERE status = 'proposed' AND channel_id = ? "
            "AND created_at < ?", (chaine, limite),
        )
        par_age += curseur.rowcount or 0
        curseur = conn.execute(
            "DELETE FROM topics_queue WHERE id IN ("
            "  SELECT id FROM topics_queue WHERE status = 'proposed' AND channel_id = ?"
            "  ORDER BY score DESC, id LIMIT -1 OFFSET ?)", (chaine, taille_max),
        )
        par_plafond += curseur.rowcount or 0
    conn.commit()
    return {"par_age": par_age, "par_plafond": par_plafond,
            "chaines": len(chaines), "age_max_jours": age_max_jours,
            "taille_max": taille_max}


# -------------------------------------------------------------------- le rapport


def _fmt(v, n=0, defaut="—"):
    if v is None:
        return defaut
    return f"{v:,.{n}f}".replace(",", " ")


def _md(texte: str | None) -> str:
    """Une barre verticale dans un titre de concurrent casserait la ligne du tableau."""
    return (texte or "").replace("|", "\\|").replace("\n", " ")


def ecrire_rapport(
    channel, sujets: list[Sujet], clusters: list[Cluster], mesures: dict, *,
    racine: Path | None = None, jour: str | None = None,
) -> Path:
    """`reports/topics_<channel>.md` — classement, preuves, trous multilingues."""
    racine = racine or racine_projet()
    jour = jour or datetime.now(UTC).date().isoformat()
    reglages = mesures["reglages"]
    par_cluster = {c.cluster_id: c for c in clusters}

    L: list[str] = [
        f"# Sujets — {channel.name} (`{channel.id}`)",
        "",
        f"Généré le {jour} par `factory editorial topics --channel {channel.id}` "
        f"en {mesures['secondes']:.0f} s.",
        "",
        f"**Ce que ces chiffres sont, et ce qu'ils ne sont pas.** Les percées sont "
        f"**mesurées** dans l'entrepôt. Les clusters sont **produits par un modèle** "
        f"(`{mesures['modele']}`) et un seuil de distance "
        f"(`{reglages['regroupement']['seuil_distance']}`) : un autre seuil donnerait un "
        f"autre découpage. Les trous sont des absences **dans l'échantillon des "
        f"{mesures['n_chaines_suivies']} chaînes suivies**, jamais dans « YouTube ». Le "
        f"score est une pondération d'opinions documentées dans `config/editorial.yaml` : "
        f"il ordonne des candidats, il ne prouve rien.",
        "",
    ]

    p = mesures["percees"]
    L += [
        "## Mesures de l'exécution",
        "",
        f"- **Corpus** — {p['n_videos']} vidéos publiées dans les "
        f"{reglages['fenetre_jours']} derniers jours chez les chaînes suivies "
        f"({mesures['langues_corpus']}).",
        f"- **Percées** — {p['n_percees']} vidéos à ≥ {p['seuil_ratio']:.0f} × la médiane "
        f"de leur chaîne dans une fenêtre d'âge de ±{p['fenetre_age_relative'] * 100:.0f} % ; "
        f"{p['n_non_notees']} vidéos **non notées** faute de {p['min_comparables']} "
        f"comparables. Base : {p['base']}.",
        f"- **Clusters** — {mesures['n_clusters']} groupes d'au moins "
        f"{reglages['regroupement']['taille_min']} vidéos ; {mesures['n_isoles']} vidéos "
        f"restées isolées (comptées, non classées).",
        f"- **Trous** — {mesures['trous']['multilingue']} multilingue(s), "
        f"{mesures['trous']['demande']} de demande, {mesures['trous']['resurgence']} "
        f"résurgence(s).",
        f"- **Embeddings** — {mesures['embeddings']['calcules']} vecteurs calculés, "
        f"{mesures['embeddings']['depuis_cache']} relus en cache, "
        f"{mesures['embeddings']['secondes']:.0f} s.",
        f"- **LLM** — {mesures['llm']['appels']} appels, dont "
        f"{mesures['llm']['caches']} servis par le cache ; "
        f"**{mesures['llm']['secondes_calculees']:.0f} s réellement calculées** "
        f"({mesures['llm']['secondes_cumulees']:.0f} s cumulées si l'on compte la durée "
        f"d'origine des appels mis en cache).",
        "",
    ]
    for avertissement in mesures.get("avertissements", []):
        L += [f"> ⚠️ {avertissement}", ""]

    L += [
        f"## File de sujets — {len(sujets)} propositions",
        "",
        "| # | score | sujet | angle | cluster | lacune | preuve |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(sujets, 1):
        e = s.evidence
        c = par_cluster.get(s.cluster_id)
        preuve = (f"{e['n_videos']} vidéos · {e['n_chaines']} chaînes · "
                  f"{_fmt(e['vues_totales'])} vues · {e['n_percees']} percées · "
                  f"{','.join(e['langues'])}")
        L.append(
            f"| {i} | **{s.score:.3f}** | {_md(s.topic)} | {_md(s.angle[:120])} | "
            f"`{s.cluster_id}` {_md(c.label) if c else ''} | {e['gap_type'] or '—'} | {preuve} |"
        )
    L.append("")

    L += ["### Décomposition des cinq premiers", ""]
    for i, s in enumerate(sujets[:5], 1):
        e = s.evidence
        comp = e["composantes"]
        poids = e["ponderations"]
        detail = " · ".join(
            f"{k} {comp[k]:.2f}×{poids[k]}" for k in
            ("force_cluster", "velocite", "lacune", "demande", "fit")
        )
        mal = e.get("malus_similarite") or {}
        L += [
            f"**{i}. {s.topic}** — score {s.score:.3f}",
            f"- *Angle* — {s.angle}",
            f"- *Composantes* — {detail} = {e['score_avant_malus']:.3f} ; "
            f"malus de répétition −{mal.get('valeur', 0):.3f}"
            + (f" (le plus proche : « {mal['plus_proche']} », cos {mal['cosinus']:.2f})"
               if mal.get("plus_proche") else " (aucun sujet BMS produit dans cette langue)")
            + ".",
            f"- *Fit* — {e['fit']}.",
            f"- *Lacune* — {e['gap_detail'] or 'aucune lacune détectée'}.",
            f"- *Demande* — seed Wikipédia le plus proche « {e['demande_seed']} », "
            f"{_fmt(e['demande_vues_mois'])} vues/mois (proxy : les lecteurs de Wikipédia "
            f"ne sont pas les spectateurs de YouTube).",
            "- *Vidéos sources* — "
            + " ; ".join(
                f"{v['chaine']} [{v['lang']}] {_fmt(v['vues'])} vues"
                + (f", ratio {v['ratio']:.1f}×" if v["ratio"] else "")
                + (" **percée**" if v["percee"] else "")
                for v in e["videos_sources"]
            )
            + ".",
        ]
        if e.get("reformulation"):
            r = e["reformulation"]
            L.append(
                f"- *Reformulé* — la première proposition était à {r['cosinus_avant']:.2f} "
                f"du titre de {r['titre_source']} ; réécrite, elle est à "
                f"{r['cosinus_apres']:.2f}."
            )
        L.append("")

    # ------------------------------------------------------- trous multilingues
    ml = reglages["trous"]["multilingue"]
    multilingues = [c for c in clusters if c.gap_type == "multilingue"]
    L += [
        "## Trous multilingues — à produire en anglais",
        "",
        f"**Le modèle des réseaux Thoth, automatisé, et dans un seul sens.** Un thème qui "
        f"marche en {', '.join(ml['langues_source'])} et que les chaînes "
        f"{ml['langue_cible']} suivies n'ont pas traité (≤ {ml['max_videos_cible']} vidéo) "
        f"vaut le plus haut barème de lacune. L'anglais est la seule langue de production "
        f"(`ROADMAP.md` § 3.1, arbitrage d'Alek du 15/09/2026) : le sens inverse n'est pas "
        f"cherché. **Le thème se reprend, jamais le script ni le titre** "
        f"(`docs/CONFORMITE.md` § 4-5).",
        "",
    ]
    if not multilingues:
        L += [
            f"**Aucun trou multilingue dans cette exécution.** {mesures['diagnostic_ml']}",
            "",
        ]
    else:
        L += ["| cluster | thème | percées source | vidéos EN | vues source | exemple |",
              "|---|---|---|---|---|---|"]
        for c in sorted(multilingues, key=lambda c: c.vues_totales, reverse=True):
            src = c.percees_en(set(ml["langues_source"]))
            ex = max(src, key=lambda v: v.views) if src else c.exemples(1)[0]
            L.append(
                f"| `{c.cluster_id}` | {_md(c.label)} | {len(src)} "
                f"({'/'.join(sorted({v.lang for v in src}))}) | "
                f"{len(c.videos_en(ml['langue_cible']))} | "
                f"{_fmt(sum(v.views for v in src))} | {_md(ex.channel_title or ex.channel_id)} "
                f"[{ex.lang}], {_fmt(ex.views)} vues |"
            )
        L.append("")

    autres = {"demande": "Demande sans offre", "resurgence": "Résurgences"}
    for gap, titre in autres.items():
        lot = [c for c in clusters if c.gap_type == gap]
        L += [f"## {titre} — {len(lot)} cluster(s)", ""]
        if not lot:
            L += ["Aucun dans cette exécution.", ""]
            continue
        L += ["| cluster | thème | détail |", "|---|---|---|"]
        for c in sorted(lot, key=lambda c: c.vues_totales, reverse=True)[:15]:
            L.append(f"| `{c.cluster_id}` | {_md(c.label)} | {_md(c.gap_detail)} |")
        L.append("")

    if mesures.get("incidents"):
        L += ["## Reprises de titre évitées", "",
              "Un sujet dont le cosinus à un titre de concurrent dépasse "
              f"{reglages['reformulation_seuil']} est reformulé une fois, puis **écarté** "
              "s'il colle encore. Aucun sujet écarté n'est remplacé par une invention.", "",
              "| proposition | titre trop proche | cos | issue |", "|---|---|---|---|"]
        for inc in mesures["incidents"]:
            L.append(
                f"| {_md(inc.get('reformule') or inc['sujet'])} | {_md(inc['titre'][:70])} | "
                f"{inc['cosinus']:.2f} | {inc['issue']} |"
            )
        L.append("")

    L += [
        "## Limites",
        "",
        f"- **74 chaînes ne sont pas le marché.** Un « trou » est une absence dans "
        f"l'échantillon suivi. Une chaîne non suivie peut avoir traité le sujet hier.",
        f"- **Un seul jour de collecte en base** au moment de cette exécution : "
        f"`views_d7` et `views_d30` sont NULL et la vélocité vaut `velocity_life` "
        f"(vues / âge). Le ratio de percée compare donc des **vues cumulées** à âge "
        f"comparable, pas des vitesses. Le second jour de collecte lève cette limite "
        f"sans changer une ligne de code (`topics.percees.preferer_dN`).",
        f"- **Le nombre de clusters est un paramètre, pas un fait.** Seuil de distance "
        f"{reglages['regroupement']['seuil_distance']} ; le rapport de veille conseille "
        f"de balayer 0,30 à 0,45.",
        f"- **La demande est un proxy** : vues Wikipédia du seed le plus proche, médiane "
        f"sur 24 mois. Google Trends reste indisponible (étape 19).",
        "",
    ]
    chemin = racine / "reports" / f"topics_{channel.id}.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(L) + "\n", encoding="utf-8")
    return chemin


# ------------------------------------------------------------------ orchestration


def executer(
    conn: sqlite3.Connection, channel_id: str, *, n: int = 30,
    racine: Path | None = None, echo=None,
) -> tuple[list[Sujet], list[Cluster], Path, dict]:
    """La chaîne complète : corpus → percées → embeddings → clusters → trous → file."""
    from factory import llm
    from factory.core import config as config_module

    debut = time.monotonic()
    racine = racine or racine_projet()
    cfg_ed = charger_config(racine)
    reglages = cfg_ed["topics"]
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(channel_id)
    trace = llm.TraceLLM()

    fenetre = int(reglages["fenetre_jours"])
    videos = corpus(conn, fenetre_jours=fenetre)
    if not videos:
        raise ValueError(
            f"aucune vidéo de moins de {fenetre} jours dans l'entrepôt — "
            "lancer `factory editorial collect` d'abord"
        )
    if echo:
        echo(f"corpus : {len(videos)} vidéos sur {fenetre} jours")
    mesure_percees = marquer_percees(videos, _population_par_chaine(conn), reglages["percees"])
    mesure_deciles = indexer_velocite(videos)
    if echo:
        echo(f"percées : {mesure_percees['n_percees']} "
             f"(seuil {mesure_percees['seuil_ratio']:.0f}×, "
             f"{mesure_percees['n_non_notees']} non notées)")

    resultat = em.embed_videos(
        conn, [(v.video_id, v.texte) for v in videos], racine=racine, echo=echo
    )
    etiquettes = regrouper(resultat.vecteurs, reglages["regroupement"]["seuil_distance"])
    clusters, isoles = construire_clusters(
        videos, resultat.vecteurs, etiquettes, int(reglages["regroupement"]["taille_min"])
    )
    if echo:
        echo(f"clusters : {len(clusters)} groupes, {isoles} vidéos isolées")

    mesure_demande = rattacher_demande(
        clusters, cfg_ed, lang=channel.lang, racine=racine, echo=echo
    )
    normaliser_clusters(clusters)
    comptes_trous = detecter_trous(clusters, reglages["trous"], fenetre)
    if echo:
        echo(f"trous : {comptes_trous['multilingue']} multilingue(s), "
             f"{comptes_trous['demande']} demande, {comptes_trous['resurgence']} résurgence(s)")

    # Les clusters envoyés au LLM : les plus forts, plus tous les trous multilingues —
    # un trou est précisément ce qu'un classement par vues ferait tomber.
    tete = clusters[: int(reglages["clusters_libelles"])]
    for c in clusters:
        if c.gap_type == "multilingue" and c not in tete:
            tete.append(c)
    libeller(tete, lot=int(reglages["lot_libelles"]), racine=racine, echo=echo, trace=trace)
    for c in clusters:
        if c.label is None:
            c.label = "~ " + _mots_saillants(c)

    pour_angles = sorted(
        tete,
        key=lambda c: (float(reglages["bareme_lacune"].get(c.gap_type or "aucune", 0.0)),
                       c.force),
        reverse=True,
    )[: int(reglages["clusters_angles"])]
    angles = proposer_angles(
        pour_angles, channel, reglages, racine=racine, echo=echo, trace=trace
    )

    mots_cles = ((cfg_ed.get("niches_notees") or {}).get(channel.niche) or {}).get("mots_cles")
    vecteur_niche = (
        em.embed([", ".join(mots_cles)], racine=racine)[0] if mots_cles else None
    )
    sujets = noter(
        pour_angles, channel, reglages,
        vecteur_niche=vecteur_niche,
        sujets_bms=sujets_bms_existants(conn, lang=channel.lang, racine=racine),
        angles=angles,
    )
    sujets, incidents = proteger_titres(
        sujets, clusters, float(reglages["reformulation_seuil"]),
        conn=conn, racine=racine, echo=echo, trace=trace,
    )
    sujets = sorted(sujets, key=lambda s: s.score, reverse=True)[:n]

    enregistrer_clusters(conn, clusters)
    ecrits = enregistrer(conn, sujets, n_max=n)
    secondes = time.monotonic() - debut

    langues = {}
    for v in videos:
        langues[v.lang] = langues.get(v.lang, 0) + 1
    ml = reglages["trous"]["multilingue"]
    absentes = [lg for lg in ml["langues_source"] if langues.get(lg, 0) == 0]
    diagnostic = (
        f"Langues source présentes dans la fenêtre : "
        + ", ".join(f"{lg} {langues.get(lg, 0)}" for lg in ml["langues_source"])
        + ". "
        + (f"**{', '.join(absentes).upper()} n'a aucune vidéo dans la fenêtre** : le trou "
           f"n'est pas mesurable dans cette langue, il n'est pas absent."
           if absentes else
           "Les trois langues source sont représentées : l'absence de trou est une mesure, "
           "pas une lacune de données.")
    )
    avertissements = []
    if absentes:
        avertissements.append(
            f"Aucune vidéo en {', '.join(absentes)} dans la fenêtre de {fenetre} jours. "
            "Les chaînes suivies dans ces langues n'ont pas publié récemment : le trou "
            "multilingue y est **non mesurable**, pas inexistant."
        )
    if mesure_percees["n_sur_views_dN"] == 0:
        avertissements.append(
            "`views_d7` et `views_d30` sont NULL sur tout le corpus (un seul jour de "
            "collecte en base). Les percées sont mesurées sur les vues observées au "
            "dernier instantané, à âge comparable."
        )

    mesures = {
        "reglages": reglages, "percees": mesure_percees, "demande": mesure_demande,
        "deciles_velocite": mesure_deciles,
        "trous": comptes_trous, "n_clusters": len(clusters), "n_isoles": isoles,
        "modele": resultat.modele, "secondes": secondes,
        "embeddings": {"calcules": resultat.calcules, "depuis_cache": resultat.depuis_cache,
                       "secondes": resultat.secondes},
        "langues_corpus": ", ".join(f"{k} {v}" for k, v in
                                    sorted(langues.items(), key=lambda kv: -kv[1])),
        "n_chaines_suivies": conn.execute(
            "SELECT COUNT(*) FROM channels_watch WHERE active = 1").fetchone()[0],
        "diagnostic_ml": diagnostic, "avertissements": avertissements,
        "incidents": incidents, "ecrits": ecrits,
        # `trace.secondes` compte aussi la durée d'ORIGINE des appels servis par le cache :
        # elle dépasse donc le temps de l'exécution (588 s annoncés pour 381 s réelles,
        # mesuré le 20/09/2026). Ce qui a coûté à CETTE exécution est `secondes_calculees`.
        "llm": {"appels": len(trace.appels), "caches": trace.appels_caches,
                "secondes_calculees": round(trace.secondes_calculees, 1),
                "secondes_cumulees": round(trace.secondes, 1)},
    }
    chemin = ecrire_rapport(channel, sujets, clusters, mesures, racine=racine)
    return sujets, clusters, chemin, mesures


# --------------------------------------------------------------------------------------
# Étape 26 — multiplicateur appris (cluster × niche), borné, 1,0 sans poids actifs
# --------------------------------------------------------------------------------------


def multiplicateur_appris(poids: dict[str, Any] | None, cluster_id: str | None,
                          niche: str | None) -> float:
    """Multiplicateur de score d'un sujet de la file : cluster × niche, borné [0,7 ; 1,4].

    Le produit est rebornée : deux multiplicateurs à 1,4 ne font pas 1,96. Sans
    `learned/weights.json` (ou niveaux sous le seuil de n), vaut 1,0 : le classement est
    celui de l'étape 20.
    """
    from factory.analytics import weights as wmod

    return wmod.borne(wmod.multiplicateur(poids, "topic_cluster", cluster_id)
                      * wmod.multiplicateur(poids, "niche", niche))
