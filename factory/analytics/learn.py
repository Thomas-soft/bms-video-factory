"""`factory learn` — ce que les vidéos publiées apprennent au système (étape 26).

Principe : peu de données, donc **rétrécir plutôt que conclure**.
- Cible principale y = log(vues J+7 ÷ médiane J+7 des autres vidéos de la chaîne) ; la fenêtre
  fixe de 7 jours fait l'« âge égal ». Cibles secondaires : % moyen regardé et CTR, en écart à
  la médiane de la chaîne.
- Effet d'un niveau = moyenne de y du niveau − moyenne générale, rétrécie vers 0 par Bayes
  empirique normal-normal (τ² de DerSimonian-Laird avec plancher ; τ fixé à 2 niveaux).
- Un niveau n'agit que si n ≥ `n_min_par_niveau` ET P(effet > 0) ≥ `prob_min_action` (ou ≤ 1 −) ;
  sinon multiplicateur 1,0. Multiplicateurs bornés [0,7 ; 1,4].
Références : Morris 1983 (JASA 78) ; DerSimonian & Laird 1986 ; Gelman et al., BDA3 chap. 5 ;
Russo et al. 2018 (Thompson) ; Bonett & Wright 2000 (IC de Spearman).
"""

from __future__ import annotations

import json
import math
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from factory.analytics import retention_analysis as ra
from factory.analytics import weights as wmod
from factory.core.models import ApprentissageConfig

# --------------------------------------------------------------------------------------
# Audit de fuite : chaque colonne de v_video_perf est classée. Un prédicteur doit être connu
# AVANT la publication ; tout ce qui est mesuré après est une cible ou un filtre.
# --------------------------------------------------------------------------------------

#: Facteurs catégoriels (connus avant publication).
CATEGORIELS = {
    "hook_type": "script (étape 16), avant rendu",
    "title_pattern": "titres (étape 13), avant upload",
    "thumbnail_template": "miniature INITIALE (thumbnail_chosen) — une rotation J+7 ne la réécrit pas",
    "style": "identité du run",
    "topic_cluster": "plan (étape 20)",
    "topic_source": "plan",
    "niche": "identité du run",
    "lang": "identité du run",
    "voice_id": "voice",
    "publish_weekday": "créneau planifié (slot_local_day)",
    "publish_hour": "créneau planifié (slot_local_hour)",
    "is_child": "run enfant (déclinaison)",
}
#: Facteurs continus, découpés en terciles.
CONTINUS = {
    "cut_rhythm_ratio": "cut_rhythm_measured_s ÷ cut_rhythm_target_s, mesuré au rendu",
    "duration_s": "durée du rendu",
    "density_facts_per_min": "script",
    "thumbnail_text_len": "miniature initiale",
}
#: Colonnes exclues comme prédicteurs, et pourquoi.
EXCLUES = {
    "views_7d": "cible", "avg_view_pct_7d": "cible", "ctr_7d": "cible (mesurée après publication)",
    "views_30d": "après publication", "avg_view_duration_7d": "après publication",
    "impressions_7d": "après publication — dépend du CTR et des vues (fuite)",
    "subs_7d": "après publication", "subs_30d": "après publication",
    "minutes_7d": "après publication", "days_pulled": "filtre de complétude",
    "last_date": "filtre", "complete_7d": "filtre", "complete_30d": "filtre",
    "publish_status": "état de publication, peut changer après", "youtube_video_id": "identifiant",
    "topic": "texte libre, un niveau par vidéo", "template_id": "redondant avec style",
    "cut_rhythm_target_s": "redondant avec niche (utilisé seulement comme dénominateur)",
    "cut_rhythm_measured_s": "remplacé par cut_rhythm_ratio (les niches diffèrent d'un facteur 10)",
    "qc_score": "évalué séparément (Banc vs résultats), pas comme facteur",
    "publish_at": "sert à l'ordre de publication (diagnostic de tendance), pas comme facteur",
}
#: Diagnostic de confusion : rang de publication dans la chaîne. Jamais exporté en poids.
DIAGNOSTIC = "publication_rank"

SIGMA_DEFAUT = {"y": 0.8, "pct": 8.0, "ctr": 0.01}
TAU_PLANCHER = {"y": 0.05, "pct": 0.5, "ctr": 0.001}
TAU_DEUX_NIVEAUX = {"y": 0.25, "pct": 3.0, "ctr": 0.004}
Z90 = 1.6449
NU0 = 10
#: Référence de vues : 5 vidéos avant, 5 après, dans la même chaîne.
FENETRE_REF = 5
#: Impressions comptées au plus par vidéo dans l'a priori Beta (unité = la vidéo).
IMPRESSIONS_MAX_PAR_VIDEO = 300
JOURS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# --------------------------------------------------------------------------------------
# Rétrécissement empirique de Bayes
# --------------------------------------------------------------------------------------


@dataclass
class Effet:
    n: int
    brut: float  # moyenne du niveau − moyenne générale
    effet: float  # rétréci
    ic90: tuple[float, float]
    p_positif: float
    retrecissement: float  # B_j : 0 = conservé, 1 = ramené à 0


def effets_eb(groupes: dict[str, list[float]], cible: str = "y") -> tuple[dict[str, Effet], dict[str, float]]:
    """Effets rétrécis par niveau, et hyperparamètres (σ², τ², k, méthode)."""
    groupes = {k: [float(v) for v in vs] for k, vs in groupes.items() if vs}
    tous = [v for vs in groupes.values() for v in vs]
    if not tous:
        return {}, {"sigma2": float("nan"), "tau2": float("nan"), "k": 0}
    mu = statistics.fmean(tous)
    k, n_tot = len(groupes), len(tous)
    ss_intra = sum(sum((v - statistics.fmean(vs)) ** 2 for v in vs) for vs in groupes.values())
    # σ² intra-niveau, poolé avec un a priori de NU0 pseudo-observations à SIGMA_DEFAUT :
    # à 3 degrés de liberté, la variance estimée est elle-même du bruit (BDA3 § 3.3).
    ddl = max(0, n_tot - k)
    sigma2 = (ss_intra + NU0 * SIGMA_DEFAUT[cible] ** 2) / (ddl + NU0)
    sigma2 = max(sigma2, 1e-12)
    moyennes = {c: statistics.fmean(vs) - mu for c, vs in groupes.items()}
    s2 = {c: sigma2 / len(vs) for c, vs in groupes.items()}
    if k >= 3:
        w = {c: 1.0 / s2[c] for c in groupes}
        sw = sum(w.values())
        yw = sum(w[c] * moyennes[c] for c in groupes) / sw
        q = sum(w[c] * (moyennes[c] - yw) ** 2 for c in groupes)
        denom = sw - sum(x * x for x in w.values()) / sw
        tau2 = max(0.0, (q - (k - 1)) / denom) if denom > 0 else 0.0
        tau2, methode = max(tau2, TAU_PLANCHER[cible] ** 2), "DerSimonian-Laird, plancher"
    elif k == 2:
        tau2, methode = TAU_DEUX_NIVEAUX[cible] ** 2, "τ fixé a priori (2 niveaux)"
    else:
        tau2, methode = 0.0, "un seul niveau : aucun contraste"
    effets = {}
    for c, vs in groupes.items():
        b = 1.0 if tau2 == 0 else s2[c] / (s2[c] + tau2)
        theta = (1 - b) * moyennes[c]
        # Incertitude sur μ et τ² ignorée par la formule plug-in : inflation de Morris
        # (k−1)/(k−3) quand k > 3 (objection 4).
        v = max(s2[c] * (1 - b) * ((k - 1) / (k - 3) if k > 3 else 1.0), 1e-12)
        sd = math.sqrt(v)
        effets[c] = Effet(len(vs), moyennes[c], theta, (theta - Z90 * sd, theta + Z90 * sd),
                          _phi(theta / sd) if k > 1 else 0.5, b)
    return effets, {"sigma2": sigma2, "tau2": tau2, "k": k, "method": methode, "mu": mu}


def multiplicateur(e: Effet, p: ApprentissageConfig, gele: bool) -> tuple[float, bool, str]:
    """(multiplicateur, actif, motif). Règle de garde : n < seuil → 1,0."""
    if gele:
        return 1.0, False, "gelé"
    if e.n < p.n_min_par_niveau:
        return 1.0, False, f"non décidable (n={e.n} < {p.n_min_par_niveau})"
    if (1 - p.prob_min_action) < e.p_positif < p.prob_min_action:
        return 1.0, False, f"incertain (P(effet>0)={e.p_positif:.2f})"
    m = min(p.multiplicateur_max, max(p.multiplicateur_min, math.exp(e.effet)))
    return round(m, 3), True, "actif"


# --------------------------------------------------------------------------------------
# Données
# --------------------------------------------------------------------------------------


def charger_lignes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Vidéos à fenêtre J+7 complète, avec la version du banc."""
    conn.row_factory = sqlite3.Row
    try:
        lignes = conn.execute(
            """SELECT v.*, r.qc_version AS qc_version, r.manifest_path AS manifest_path
                 FROM v_video_perf v LEFT JOIN runs r ON r.video_id = v.video_id
                WHERE v.views_7d IS NOT NULL AND v.complete_7d = 1
                  AND coalesce(v.days_pulled, 0) >= 7
                  AND coalesce(v.is_child, 0) = 0""").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(x) for x in lignes]


def _mediane_loo(valeurs: list[tuple[str, float]], exclu: str) -> tuple[float | None, int]:
    autres = [v for i, v in valeurs if i != exclu and v is not None and v > 0]
    return (statistics.median(autres) if autres else None), len(autres)


def normaliser(lignes: list[dict[str, Any]], p: ApprentissageConfig,
               cibles_rythme: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Ajoute y, pct, ctr, cut_rhythm_ratio et publication_rank (objections du 23/09/2026).

    - Référence de vues = médiane GLISSANTE des `FENETRE_REF` vidéos précédentes et suivantes
      de la même chaîne, la vidéo exclue : une chaîne qui grandit ne fait pas gagner tout
      facteur adopté tard (objection 1).
    - Moins de `n_min_chaine_mediane` voisines → y = None, vidéo exclue des estimations, plutôt
      qu'un repli sur la niche qui ferait mesurer la niche (objection 5).
    - y = log((v + 1) / (ref + 1)) : les vidéos à 0 vue restent dans l'échantillon (objection 8).
    - Rythme rapporté à la cible du RÉFÉRENTIEL de la niche, pas à la cible déjà ajustée
      (objection 7).
    """
    cibles_rythme = cibles_rythme or {}
    par_chaine: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for x in lignes:
        par_chaine[x["channel_id"]].append(x)
    for chaine, vs in par_chaine.items():
        vs.sort(key=lambda x: x.get("publish_at") or "")
        for rang, x in enumerate(vs):
            x[DIAGNOSTIC] = rang
            voisines = vs[max(0, rang - FENETRE_REF):rang] + vs[rang + 1:rang + 1 + FENETRE_REF]
            vues = [o["views_7d"] for o in voisines if o.get("views_7d") is not None]
            x["n_ref"] = len(vues)
            ref = statistics.median(vues) if len(vues) >= p.n_min_chaine_mediane else None
            x["views_ref"] = ref
            x["y"] = (math.log((x["views_7d"] + 1) / (ref + 1))
                      if ref is not None and x.get("views_7d") is not None else None)
            for src, dst in (("avg_view_pct_7d", "pct"), ("ctr_7d", "ctr")):
                autres = [o[src] for o in voisines if o.get(src) is not None]
                x[dst] = (x[src] - statistics.median(autres)) \
                    if x.get(src) is not None and len(autres) >= p.n_min_chaine_mediane else None
    for x in lignes:
        jour = x.get("publish_weekday")
        if isinstance(jour, int) or (isinstance(jour, str) and jour.isdigit()):
            x["publish_weekday"] = JOURS[int(jour) % 7]  # strftime('%w') : 0 = dimanche
        t = cibles_rythme.get(x.get("niche")) or x.get("cut_rhythm_target_s")
        mes = x.get("cut_rhythm_measured_s")
        x["cut_rhythm_ratio"] = (mes / t) if t and mes else None
    return lignes


def terciles(valeurs: list[float]) -> tuple[float, float] | None:
    if len(set(valeurs)) < 3:
        return None
    a, b = np.quantile(valeurs, [1 / 3, 2 / 3])
    return float(a), float(b)


def niveau_tercile(v: float | None, bornes: tuple[float, float] | None) -> str | None:
    if v is None or bornes is None:
        return None
    a, b = bornes
    # Clés stables d'un run à l'autre ; les bornes sont publiées à part (`bounds`).
    return "T1" if v <= a else ("T2" if v <= b else "T3")


# --------------------------------------------------------------------------------------
# Effets par facteur
# --------------------------------------------------------------------------------------


@dataclass
class ResultatFacteur:
    nom: str
    type: str
    origine: str
    gele: bool
    niveaux: dict[str, dict[str, Any]] = field(default_factory=dict)
    hyper: dict[str, Any] = field(default_factory=dict)
    secondaires: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    bornes: tuple[float, float] | None = None


def _niveau(x: dict[str, Any], nom: str, bornes) -> str | None:
    if nom in CONTINUS or nom == DIAGNOSTIC:
        return niveau_tercile(x.get(nom), bornes)
    v = x.get(nom)
    return None if v is None else str(v)


#: Facteurs dont la garde de n se compte à l'intérieur d'une niche (objection 10) : leurs
#: parts de référence diffèrent par niche, un effet marginal mélangerait niche et facteur.
GARDE_PAR_NICHE = {"hook_type", "topic_cluster", "title_pattern"}


def gel_global(lignes: list[dict[str, Any]], p: ApprentissageConfig) -> str | None:
    """Motif de gel de TOUS les multiplicateurs, ou `None`.

    Aucun poids actif avant n ≥ `n_min_global` vidéos à y calculable ET
    `n_min_chaines` chaînes à ≥ `n_min_par_chaine` vidéos (objection « gel global »).
    """
    avec_y = [x for x in lignes if x.get("y") is not None]
    par_chaine = defaultdict(int)
    for x in avec_y:
        par_chaine[x["channel_id"]] += 1
    chaines = sum(1 for v in par_chaine.values() if v >= p.n_min_par_chaine)
    if len(avec_y) < p.n_min_global or chaines < p.n_min_chaines:
        return (f"gel global : n={len(avec_y)} vidéo(s) (≥ {p.n_min_global} exigées), "
                f"{chaines} chaîne(s) à ≥ {p.n_min_par_chaine} vidéos ({p.n_min_chaines} exigées)")
    return None


def estimer_facteurs(lignes: list[dict[str, Any]], p: ApprentissageConfig) -> list[ResultatFacteur]:
    resultats = []
    tous = [(DIAGNOSTIC, "diagnostic (tendance)", "ordre de publication dans la chaîne")] + \
           [(n, "catégoriel", o) for n, o in CATEGORIELS.items()] + \
           [(n, "continu (terciles)", o) for n, o in CONTINUS.items()]
    motif_global = gel_global(lignes, p)
    for nom, typ, origine in tous:
        bornes = None
        if nom in CONTINUS or nom == DIAGNOSTIC:
            bornes = terciles([x[nom] for x in lignes if x.get(nom) is not None and x.get("y") is not None])
        gele = nom in p.facteurs_geles or nom == DIAGNOSTIC or motif_global is not None
        rf = ResultatFacteur(nom, typ, origine, gele, bornes=bornes)
        for cible in ("y", "pct", "ctr"):
            groupes: dict[str, list[float]] = defaultdict(list)
            par_niche: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            for x in lignes:
                niv = _niveau(x, nom, bornes)
                if niv is not None and x.get(cible) is not None:
                    groupes[niv].append(x[cible])
                    par_niche[niv][x.get("niche") or "?"] += 1
            effets, hyper = effets_eb(groupes, cible)
            if cible == "y":
                rf.hyper = hyper
                for niv, e in sorted(effets.items()):
                    m, actif, motif = multiplicateur(e, p, nom in p.facteurs_geles or nom == DIAGNOSTIC)
                    n_niche = max(par_niche[niv].values()) if par_niche[niv] else 0
                    if actif and nom in GARDE_PAR_NICHE and n_niche < p.n_min_par_niveau:
                        m, actif, motif = 1.0, False, (f"non décidable par niche (n max dans une "
                                                       f"niche = {n_niche} < {p.n_min_par_niveau})")
                    if motif_global:
                        m, actif = 1.0, False
                        motif = motif_global if motif == "actif" else f"{motif_global} ; {motif}"
                    rf.niveaux[niv] = {
                        "n": e.n, "raw": round(e.brut, 4), "effect": round(e.effet, 4),
                        "ci90": [round(e.ic90[0], 4), round(e.ic90[1], 4)],
                        "p_positive": round(e.p_positif, 3), "shrinkage": round(e.retrecissement, 3),
                        "multiplier": m, "active": actif, "status": motif}
            else:
                rf.secondaires[cible] = {
                    niv: {"n": e.n, "effect": round(e.effet, 4),
                          "ci90": [round(e.ic90[0], 4), round(e.ic90[1], 4)]}
                    for niv, e in sorted(effets.items())}
        resultats.append(rf)
    # Objection 1 : si le rang de publication a un effet rétréci > seuil, la chaîne a une
    # tendance que la médiane glissante n'absorbe pas — tous les poids sont gelés.
    diag = resultats[0]
    tendance = max((abs(v["effect"]) for v in diag.niveaux.values()), default=0.0)
    if tendance > p.tendance_max:
        for rf in resultats[1:]:
            for v in rf.niveaux.values():
                v.update(multiplier=1.0, active=False,
                         status=f"gelé : tendance de publication {tendance:.2f} > {p.tendance_max}"
                                f" ; {v['status']}")
    return resultats


# --------------------------------------------------------------------------------------
# Spearman et banc
# --------------------------------------------------------------------------------------


def _rangs(v: list[float]) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    ordre = a.argsort(kind="mergesort")
    rangs = np.empty(len(a))
    rangs[ordre] = np.arange(1, len(a) + 1)
    for val in np.unique(a):  # rangs moyens en cas d'égalité
        idx = a == val
        rangs[idx] = rangs[idx].mean()
    return rangs


def spearman(x: list[float], y: list[float]) -> dict[str, Any]:
    """ρ de Spearman et IC 95 % par Fisher z, se = √(1,06 / (n − 3)) (Fieller et al. 1957)."""
    paires = [(a, b) for a, b in zip(x, y, strict=True) if a is not None and b is not None]
    n = len(paires)
    if n < 4:
        return {"n": n, "rho": None, "ci95": None}
    rx, ry = _rangs([a for a, _ in paires]), _rangs([b for _, b in paires])
    if rx.std() == 0 or ry.std() == 0:
        return {"n": n, "rho": None, "ci95": None}
    rho = float(np.corrcoef(rx, ry)[0, 1])
    z, se = math.atanh(max(-0.9999, min(0.9999, rho))), math.sqrt(1.06 / (n - 3))
    return {"n": n, "rho": round(rho, 3),
            "ci95": [round(math.tanh(z - 1.96 * se), 3), round(math.tanh(z + 1.96 * se), 3)]}


def banc_vs_resultats(lignes: list[dict[str, Any]], racine: Path, p: ApprentissageConfig) -> dict[str, Any]:
    """Corrélations qc_score ↔ y et familles du banc ↔ % regardé, par version du banc."""
    versions = defaultdict(list)
    for x in lignes:
        versions[x.get("qc_version") or "inconnue"].append(x)
    version, sous = max(versions.items(), key=lambda kv: len(kv[1])) if versions else ("aucune", [])
    global_ = {"qc_score ↔ y": spearman([x.get("qc_score") for x in sous], [x.get("y") for x in sous]),
               "qc_score ↔ avg_view_pct_7d": spearman([x.get("qc_score") for x in sous],
                                                      [x.get("avg_view_pct_7d") for x in sous])}
    familles: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for x in sous:
        qc = Path(x["manifest_path"]).parent / "qc.json" if x.get("manifest_path") else None
        if qc is None or not (qc if qc.is_absolute() else racine / qc).is_file():
            continue
        qc = qc if qc.is_absolute() else racine / qc
        for nom_fam, fam in (json.loads(qc.read_text("utf-8")).get("families") or {}).items():
            if (fam or {}).get("score") is not None and x.get("avg_view_pct_7d") is not None:
                familles[nom_fam].append((fam["score"], x["avg_view_pct_7d"]))
    composantes = {f"{k} ↔ avg_view_pct_7d": spearman([a for a, _ in v], [b for _, b in v])
                   for k, v in sorted(familles.items())}
    n = global_["qc_score ↔ y"]["n"]
    r = global_["qc_score ↔ avg_view_pct_7d"]
    if n < p.n_min_banc:
        decision = (f"seuils inchangés — non décidable (n={n} vidéo(s), version du banc {version} ; "
                    f"docs/QC.md § 8 exige n ≥ {p.n_min_banc})")
    elif r["ci95"] and r["ci95"][0] > 0:
        decision = "seuils inchangés — le score global prédit le % regardé (IC 95 % > 0)"
    else:
        decision = ("seuils inchangés, barème global INVALIDÉ tel quel (IC 95 % contient 0) : "
                    "recalibration par famille selon docs/QC.md § 8, pas de retouche à l'aveugle")
    return {"qc_version": version, "versions": {k: len(v) for k, v in versions.items()},
            "global": global_, "components": composantes, "decision": decision}


# --------------------------------------------------------------------------------------
# Poids dérivés
# --------------------------------------------------------------------------------------


def _facteur(facteurs: list[ResultatFacteur], nom: str) -> ResultatFacteur | None:
    return next((f for f in facteurs if f.nom == nom), None)


def _mults(f: ResultatFacteur | None) -> dict[str, float]:
    if f is None:
        return {}
    return {k: v["multiplier"] for k, v in f.niveaux.items() if v["active"]}


def deriver_poids(facteurs: list[ResultatFacteur], lignes: list[dict[str, Any]],
                  p: ApprentissageConfig, racine: Path, retention: dict[str, Any],
                  maintenant: str) -> dict[str, Any]:
    from factory.core import config as config_module
    from factory.core import referentiel

    cfg = config_module.charger(racine, strict=False)
    niches = sorted({c.niche for c in cfg.channels.values() if getattr(c, "niche", None)})
    m_hook = _mults(_facteur(facteurs, "hook_type"))

    hooks = {}
    for niche in niches:
        try:
            ref = dict(referentiel.niche(niche, racine)["hooks"]["parts"])
        except (KeyError, TypeError):
            continue
        brut = {t: part * m_hook.get(t, 1.0) for t, part in ref.items()}
        total = sum(brut.values()) or 1.0
        parts = {t: v / total for t, v in brut.items()}
        # Plancher d'exploration 1/(2K) pour les types présents au référentiel : un type
        # défavorisé reste produit, donc reste mesurable (objection 3).
        plancher = 1 / (2 * max(1, sum(1 for v in ref.values() if v > 0)))
        parts = {t: (max(v, plancher) if ref[t] > 0 else v) for t, v in parts.items()}
        total = sum(parts.values()) or 1.0
        hooks[niche] = {"parts": {t: round(v / total, 4) for t, v in parts.items()},
                        "changed": any(t in m_hook for t in ref)}

    rythme = {}
    f_r = _facteur(facteurs, "cut_rhythm_ratio")
    meilleur = None
    if f_r is not None:
        actifs = [(k, v) for k, v in f_r.niveaux.items() if v["active"] and v["effect"] > 0]
        if actifs:
            meilleur = max(actifs, key=lambda kv: kv[1]["effect"])[0]
    ratio = 1.0
    if meilleur:
        vals = [x["cut_rhythm_ratio"] for x in lignes
                if niveau_tercile(x.get("cut_rhythm_ratio"), f_r.bornes) == meilleur]
        ratio = min(1 + p.rythme_ajustement_max, max(1 - p.rythme_ajustement_max,
                                                      statistics.median(vals)))
    for niche in niches:
        donnees = (referentiel.niche(niche, racine).get("rythme_coupe_s") or {})
        ref = next((donnees[c] for c in ("cible_montage", "cible", "fallback_provisoire_s")
                    if isinstance(donnees.get(c), (int, float))), None)
        if ref is None:
            continue
        rythme[niche] = {"reference_s": ref, "factor": round(ratio, 3),
                         "adjusted_s": round(ref * ratio, 3),
                         "source": f"tercile {meilleur}" if meilleur else "référentiel (aucun tercile actif)"}

    jours_m = _mults(_facteur(facteurs, "publish_weekday"))
    heures_m = _mults(_facteur(facteurs, "publish_hour"))
    creneaux = {}
    # Un créneau n'est retiré que si son niveau est ACTIF et nettement défavorable (< 0,85).
    for cid, ch in cfg.channels.items():
        jours = [j for j in ch.cadence.days if jours_m.get(j, 1.0) >= 0.85]
        heures = [h for h in ch.cadence.hours_local if heures_m.get(str(int(h[:2])), 1.0) >= 0.85]
        if (jours and heures) and (jours != list(ch.cadence.days) or heures != list(ch.cadence.hours_local)):
            creneaux[cid] = {"days": jours, "hours_local": heures}

    ctrs = [x["ctr_7d"] for x in lignes if x.get("ctr_7d") is not None]
    ctr0 = statistics.median(ctrs) if ctrs else p.ctr_prior_defaut
    a0, b0 = ctr0 * p.thompson_force_prior, (1 - ctr0) * p.thompson_force_prior
    gabarits: dict[str, dict[str, float]] = defaultdict(lambda: {"impressions": 0.0, "clicks": 0.0, "n": 0})
    for x in lignes:
        t = x.get("thumbnail_template")
        if t and x.get("impressions_7d") and x.get("ctr_7d") is not None:
            g = gabarits[t]
            # Unité = la vidéo : 10⁴ impressions d'une seule vidéo ne sont pas 10⁴ tirages
            # indépendants et écraseraient l'a priori (objection 2).
            imp = min(x["impressions_7d"], IMPRESSIONS_MAX_PAR_VIDEO)
            g["impressions"] += imp
            g["clicks"] += imp * x["ctr_7d"]
            g["n"] += 1
    politique = {
        "prior": {"ctr": round(ctr0, 5), "strength": p.thompson_force_prior,
                  "source": "médiane observée" if ctrs else "défaut de config (aucun CTR observé)"},
        "active": any(g["n"] >= p.n_min_par_niveau for g in gabarits.values())
        and "thumbnail_template" not in p.facteurs_geles,
        "templates": {t: {"alpha": round(a0 + g["clicks"], 3),
                          "beta": round(b0 + g["impressions"] - g["clicks"], 3),
                          "n_videos": int(g["n"]), "impressions": int(g["impressions"])}
                      for t, g in sorted(gabarits.items())},
        "rotation": {"after_days": 7, "criterion": "ctr_7d < médiane CTR de la chaîne"},
    }

    return {
        "version": wmod.VERSION,
        "generated_at": maintenant,
        "n_videos": len(lignes),
        "n_videos_with_y": sum(1 for x in lignes if x.get("y") is not None),
        "n_min_per_level": p.n_min_par_niveau,
        "multiplier_bounds": [p.multiplicateur_min, p.multiplicateur_max],
        "target": "y = log(views_7d / médiane J+7 des autres vidéos de la chaîne)",
        "frozen": sorted(set(p.facteurs_geles)),
        "factors": {f.nom: {"type": f.type, "frozen": f.gele,
                            **({"bounds": [round(f.bornes[0], 4), round(f.bornes[1], 4)]}
                               if f.bornes else {}),
                            "levels": {k: {kk: v[kk] for kk in ("n", "effect", "ci90", "multiplier",
                                                                "active", "status")}
                                       for k, v in f.niveaux.items()}}
                    for f in facteurs if f.nom != DIAGNOSTIC},
        "topics": {"cluster": _mults(_facteur(facteurs, "topic_cluster")),
                   "niche": _mults(_facteur(facteurs, "niche"))},
        "hooks": hooks,
        "titles": {"patterns": _mults(_facteur(facteurs, "title_pattern"))},
        "cut_rhythm": rythme,
        "channels": creneaux,
        "thumbnail_policy": politique,
        "retention_rules": [r for r in retention.get("rules", []) if r["status"] == "candidate"],
    }


# --------------------------------------------------------------------------------------
# Rétention sur les données réelles
# --------------------------------------------------------------------------------------


def courbes_reelles(conn: sqlite3.Connection, lignes: list[dict[str, Any]], racine: Path) -> list[dict]:
    videos = []
    for x in lignes:
        row = conn.execute(
            """SELECT points_json FROM retention_curves WHERE video_id = ?
                ORDER BY (day_after_publish = 7) DESC, day_after_publish DESC LIMIT 1""",
            (x["video_id"],)).fetchone()
        if not row or not x.get("manifest_path"):
            continue
        run = Path(x["manifest_path"]).parent
        run = run if run.is_absolute() else racine / run
        try:
            segs, scripts, sponsors, duree = ra.charger_segments(run)
        except (OSError, ValueError, KeyError):
            continue
        if not duree:
            continue
        videos.append({"video_id": x["video_id"], "channel_id": x["channel_id"],
                       "points": json.loads(row[0]), "duree_s": duree, "segments": segs,
                       "scripts": scripts, "sponsors": sponsors})
    return videos


# --------------------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------------------


def _fmt_ic(ic: list[float] | None) -> str:
    return "—" if not ic else f"[{ic[0]:+.2f} ; {ic[1]:+.2f}]"


def rapport(poids: dict[str, Any], facteurs: list[ResultatFacteur], banc: dict[str, Any],
            retention: dict[str, Any], lignes: list[dict[str, Any]], p: ApprentissageConfig,
            objections: str | None = None) -> str:
    n = poids["n_videos"]
    actifs = [(f.nom, k, v) for f in facteurs for k, v in f.niveaux.items() if v["active"]]
    L = [f"# Ce que le système a appris — {poids['generated_at'][:10]}", "",
         f"- Vidéos à fenêtre J+7 complète : **n = {n}** ({poids['n_videos_with_y']} avec une cible y calculable).",
         f"- Cible : {poids['target']}. Secondaires : % moyen regardé et CTR, en écart à la médiane de la chaîne.",
         f"- Règle de garde : un niveau n'agit qu'à **n ≥ {p.n_min_par_niveau}** et P(effet > 0) ≥ {p.prob_min_action} "
         f"(ou ≤ {1 - p.prob_min_action:.1f}) ; multiplicateurs bornés [{p.multiplicateur_min} ; {p.multiplicateur_max}].",
         f"- Facteurs gelés : {', '.join(poids['frozen']) or 'aucun'}.", ""]
    L += ["## 1. Ce qui est appris", ""]
    if not actifs:
        L += [f"**Rien.** Aucun niveau de facteur n'atteint le seuil (n = {n}). Le système continue "
              "sur le référentiel ; tous les multiplicateurs valent 1,0.", ""]
    else:
        L += ["| Facteur | Niveau | n | Effet rétréci (log) | IC 90 % | Multiplicateur |", "|---|---|---|---|---|---|"]
        for nom, k, v in actifs:
            L.append(f"| {nom} | {k} | {v['n']} | {v['effect']:+.3f} | {_fmt_ic(v['ci90'])} | ×{v['multiplier']} |")
        L.append("")
    L += ["## 2. Ce qui n'est pas encore décidable", ""]
    for f in facteurs:
        if not f.niveaux:
            L.append(f"- **{f.nom}** ({f.type}) : non décidable (n=0) — aucune observation.")
            continue
        niv = "; ".join(f"{k} : n={v['n']}, effet {v['effect']:+.2f} {_fmt_ic(v['ci90'])} → {v['status']}"
                        for k, v in f.niveaux.items() if not v["active"])
        if niv:
            L.append(f"- **{f.nom}** ({f.type}) : {niv}.")
    diag = _facteur(facteurs, DIAGNOSTIC)
    L += ["", f"Diagnostic de tendance (rang de publication, jamais exporté) : "
          + ("aucune donnée." if not (diag and diag.niveaux) else
             "; ".join(f"{k} n={v['n']} effet {v['effect']:+.2f}" for k, v in diag.niveaux.items())
             + " — un effet ici signale que la chaîne grandit et que tout facteur adopté tard en profite."), ""]
    L += ["## 3. Règles de rétention candidates", ""]
    regles = retention.get("rules", [])
    if not regles:
        L += [f"Non décidable (n={retention.get('n_curves', 0)} courbe(s) de rétention alignée(s)).", ""]
    else:
        for r in regles:
            L.append(f"- {r['text']} — **{r['status']}**.")
        L.append("")
    L += ["## 4. Banc vs résultats", "",
          f"Version du banc retenue : `{banc['qc_version']}` (répartition : {banc['versions'] or 'aucune vidéo'}). "
          "Les scores de deux versions ne se corrèlent pas ensemble (docs/QC.md § 8).", "",
          "| Corrélation (Spearman) | n | ρ | IC 95 % |", "|---|---|---|---|"]
    for nom, s in list(banc["global"].items()) + list(banc["components"].items()):
        rho = "non calculable" if s["rho"] is None else f"{s['rho']:+.3f}"
        L.append(f"| {nom} | {s['n']} | {rho} | {_fmt_ic(s['ci95'])} |")
    if not banc["components"]:
        L.append("| familles du banc ↔ avg_view_pct_7d | 0 | non calculable | — |")
    L += ["", f"**Décision : {banc['decision']}.**",
          "Ordre de grandeur : exclure ρ = 0 exige n ≥ 17 si ρ vaut 0,5 et n ≥ 46 si ρ vaut 0,3 "
          "(Bonett & Wright 2000).", ""]
    L += ["## 5. Les 5 actions que le système va changer", ""]
    actions = []
    for nom, k, v in actifs[:5]:
        sens = "favoriser" if v["multiplier"] > 1 else "réduire"
        actions.append(f"{sens} {nom} = {k} (×{v['multiplier']}, n={v['n']})")
    if poids["thumbnail_policy"]["active"]:
        actions.append("choisir la miniature initiale par échantillonnage de Thompson")
    if not actions:
        L += [f"**Aucune (n = {n}).** Aucun poids n'est actif : sujets, hooks, titres, rythme, "
              "créneaux et miniatures restent décidés par le référentiel. Ce qui changera dès que "
              f"des niveaux atteindront n ≥ {p.n_min_par_niveau} : (1) ordre des sujets de la file par "
              "multiplicateur de cluster et de niche ; (2) parts de tirage des types de hook ; "
              "(3) poids des patrons de titre ; (4) cible de rythme ±20 % ; (5) miniature initiale par "
              "Thompson et rotation J+7 si CTR sous la médiane.", ""]
    else:
        L += [f"{i}. {a}" for i, a in enumerate(actions[:5], 1)] + [""]
    L += ["## 6. Audit de fuite", "",
          "Prédicteurs (tous connus avant publication) : "
          + ", ".join(f"`{k}`" for k in list(CATEGORIELS) + list(CONTINUS)) + ".", "",
          "Colonnes exclues : " + "; ".join(f"`{k}` ({v})" for k, v in EXCLUES.items()) + ".", ""]
    if objections:
        L += ["## 7. Objections", "", objections.strip(), ""]
    return "\n".join(L)


# --------------------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------------------


def _cibles_rythme_referentiel(racine: Path) -> dict[str, float]:
    from factory.core import referentiel

    sortie = {}
    try:
        niches = referentiel.charger(racine).get("niches", {})
    except (OSError, ValueError, KeyError):
        return {}
    for nom, d in niches.items():
        r = d.get("rythme_coupe_s") or {}
        v = next((r[c] for c in ("cible_montage", "cible", "fallback_provisoire_s")
                  if isinstance(r.get(c), (int, float))), None)
        if v:
            sortie[nom] = float(v)
    return sortie


def executer(racine: Path, conn: sqlite3.Connection, p: ApprentissageConfig,
             ecrire: bool = True, objections: str | None = None) -> dict[str, Any]:
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lignes = normaliser(charger_lignes(conn), p, _cibles_rythme_referentiel(racine))
    facteurs = estimer_facteurs(lignes, p)
    retention = ra.analyser(courbes_reelles(conn, lignes, racine), p.n_min_regle_retention)
    banc = banc_vs_resultats(lignes, racine, p)
    poids = deriver_poids(facteurs, lignes, p, racine, retention, maintenant)
    texte = rapport(poids, facteurs, banc, retention, lignes, p, objections)
    chemins = {}
    if ecrire:
        (racine / "learned").mkdir(exist_ok=True)
        cible = racine / wmod.CHEMIN
        cible.write_text(json.dumps(poids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (racine / "reports").mkdir(exist_ok=True)
        rap = racine / "reports" / f"learn_{maintenant[:10]}.md"
        rap.write_text(texte, encoding="utf-8")
        chemins = {"weights": cible, "report": rap}
    return {"weights": poids, "report": texte, "paths": chemins, "bench": banc,
            "retention": retention, "factors": facteurs}
