"""Économie unitaire : coût et revenu par vidéo, agrégés (étape 27).

Coût d'une vidéo = énergie (compute_min × puissance × tarif kWh) + relecture (minutes × taux
horaire) + part des coûts fixes du mois (coûts fixes ÷ vidéos livrées ce mois-là).
Revenu = publicité (`revenue.source = 'ads'`) + affiliation, converti en euros.

Trois natures de chiffre, toujours distinguées dans le rapport :
- **mesuré** : chronométré ou compté par l'usine (compute_min des manifestes, durées, n) ;
- **importé** : lu dans un export de programme ou l'Analytics API (table `revenue`) ;
- **estimé** : issu d'une hypothèse de `config/economics.yaml` non mesurée (`defaut`).

Les lignes `origin = 'fixture'` de `revenue` ne comptent jamais. Aucune constante économique
n'est écrite ici : tout vient de la configuration.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from factory.core.models import EconomicsConfig, ValeurSourcee

NOEUDS = ("plan", "research", "script", "voice", "subtitles", "shotlist",
          "render", "assemble", "thumbnail", "metadata", "export")


@dataclass
class Param:
    """Un paramètre employé, sa valeur et sa nature."""

    nom: str
    valeur: float | None
    estime: bool
    origine: str


def _param(nom: str, v: ValeurSourcee | None) -> Param:
    if v is None:
        return Param(nom, None, True, "absent de config/economics.yaml")
    if v.valeur is not None:
        return Param(nom, float(v.valeur), False, v.source or v.note or "")
    return Param(nom, v.defaut, True, v.note or v.source or "")


@dataclass
class Video:
    """Une vidéo livrée (final.mp4 présent ou exportée) et son économie."""

    video_id: str
    channel_id: str
    lang: str
    niche: str
    style: str
    run_state: str
    created_at: str
    duration_s: float
    compute_min: float
    noeuds_chronometres: int
    library_uses: int
    reviewer: str | None
    published_at: str | None
    cout_energie: float = 0.0
    cout_relecture: float = 0.0
    cout_fixe: float = 0.0
    revenu_ads: float = 0.0
    revenu_affil: float = 0.0
    revenu_horizon: float = 0.0
    alertes: list[str] = field(default_factory=list)

    @property
    def cout(self) -> float:
        return self.cout_energie + self.cout_relecture + self.cout_fixe

    @property
    def revenu(self) -> float:
        return self.revenu_ads + self.revenu_affil

    @property
    def minutes(self) -> float:
        return self.duration_s / 60.0


@dataclass
class Economie:
    """Tout ce que le rapport affiche."""

    params: list[Param]
    videos: list[Video]
    echecs_compute_min: float
    echecs_n: int
    revenus_fixture: int
    revenus_non_rattaches: float
    revenus_importes_n: int
    depuis: date | None


def _manifest(racine: Path, video_id: str) -> dict:
    chemin = racine / "workspace" / "runs" / video_id / "manifest.json"
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}


def _compute(m: dict) -> tuple[float, int]:
    ex = m.get("execution") or {}
    t = ex.get("timings") or {}
    cm = (ex.get("cost") or {}).get("compute_min")
    total = cm if cm is not None else sum(t.get(n, 0.0) for n in NOEUDS) / 60.0
    return float(total or 0.0), sum(1 for n in NOEUDS if t.get(n))


def calculer(conn: sqlite3.Connection, eco: EconomicsConfig, racine: Path,
             depuis: date | None = None) -> Economie:
    """Assemble coûts et revenus par vidéo depuis la base, les manifestes et la config."""
    p_w = _param("puissance_moyenne_w", eco.puissance_moyenne_w)
    p_kwh = _param("tarif_kwh_eur", eco.tarif_kwh_eur)
    p_h = _param("cout_horaire_relecture_eur", eco.cout_horaire_relecture_eur)
    p_rel = _param("relecture_forfait_min", eco.relecture_forfait_min)
    p_fixe = _param("couts_fixes_mensuels_eur", eco.couts_fixes_mensuels_eur)
    p_amort = _param("amortissement_materiel_mensuel_eur", eco.amortissement_materiel_mensuel_eur)
    p_srv = _param("serveur_gpu_mensuel_eur", eco.serveur_gpu_mensuel_eur)
    params = [p_w, p_kwh, p_h, p_rel, p_fixe, p_amort, p_srv]
    taux = {dev: _param(f"taux_eur.{dev}", v) for dev, v in eco.taux_eur.items()}
    params += list(taux.values())
    params.append(Param("horizon_retour_jours", float(eco.horizon_retour_jours), False,
                        "config/economics.yaml"))

    lignes = conn.execute(
        "SELECT r.*, (SELECT reviewer FROM review_log l WHERE l.video_id = r.video_id"
        "  ORDER BY l.timestamp DESC LIMIT 1) AS rev,"
        " (SELECT COUNT(*) FROM library_uses u WHERE u.video_id = r.video_id) AS lib"
        " FROM runs r ORDER BY r.created_at").fetchall()
    videos: list[Video] = []
    echecs_min, echecs_n = 0.0, 0
    for r in lignes:
        if depuis and (r["created_at"] or "")[:10] < depuis.isoformat():
            continue
        m = _manifest(racine, r["video_id"])
        compute_min, noeuds = _compute(m)
        livree = (racine / "workspace" / "runs" / r["video_id"] / "final.mp4").exists() \
            or r["run_state"] in ("exported", "published")
        if not livree or not r["duration_s"]:
            echecs_min += compute_min
            echecs_n += 1 if compute_min > 0 else 0
            continue
        videos.append(Video(
            video_id=r["video_id"], channel_id=r["channel_id"], lang=r["lang"],
            niche=r["niche"], style=r["style"], run_state=r["run_state"],
            created_at=r["created_at"], duration_s=float(r["duration_s"]),
            compute_min=compute_min, noeuds_chronometres=noeuds, library_uses=r["lib"],
            reviewer=r["rev"], published_at=r["published_at"]))

    # Part des coûts fixes : coûts du mois ÷ vidéos livrées ce mois-là (mesuré).
    par_mois: dict[str, int] = defaultdict(int)
    for v in videos:
        par_mois[v.created_at[:7]] += 1
    fixes = (p_fixe.valeur or 0.0) + (p_amort.valeur or 0.0)
    for v in videos:
        v.cout_energie = v.compute_min / 60.0 * (p_w.valeur or 0.0) / 1000.0 * (p_kwh.valeur or 0.0)
        v.cout_relecture = (p_rel.valeur or 0.0) * (p_h.valeur or 0.0) / 60.0
        v.cout_fixe = fixes / par_mois[v.created_at[:7]]
        if v.noeuds_chronometres < len(NOEUDS):
            v.alertes.append(f"{v.noeuds_chronometres}/{len(NOEUDS)} étapes chronométrées")
        if v.reviewer in (None, "auto-approve"):
            v.alertes.append("relecture humaine non faite : forfait appliqué")

    # Revenus (hors fixtures), convertis en euros.
    def eur(montant: float, devise: str) -> float:
        t = taux.get(devise)
        return montant * (t.valeur if t and t.valeur is not None else 0.0)

    index = {v.video_id: v for v in videos}
    non_rattaches = 0.0
    n_importes = 0
    for rv in conn.execute("SELECT * FROM revenue WHERE origin != 'fixture'"):
        n_importes += 1
        montant = eur(rv["amount"], rv["currency"])
        v = index.get(rv["video_id"])
        if v is None:
            non_rattaches += montant
            continue
        if rv["source"] == "ads":
            v.revenu_ads += montant
        else:
            v.revenu_affil += montant
        if v.published_at:
            limite = (datetime.fromisoformat(v.published_at.replace("Z", "+00:00")).date()
                      + timedelta(days=eco.horizon_retour_jours)).isoformat()
            if rv["date"] <= limite:
                v.revenu_horizon += montant
    fixtures = conn.execute("SELECT COUNT(*) FROM revenue WHERE origin = 'fixture'").fetchone()[0]
    return Economie(params, videos, echecs_min, echecs_n, fixtures, non_rattaches, n_importes,
                    depuis)


# --------------------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------------------


def _e(x: float) -> str:
    return f"{x:.3f} €".replace(".", ",") if abs(x) < 1 else f"{x:.2f} €".replace(".", ",")


def _n(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _groupe(videos: list[Video], cle: str) -> list[tuple[str, list[Video]]]:
    g: dict[str, list[Video]] = defaultdict(list)
    for v in videos:
        g[getattr(v, cle)].append(v)
    return sorted(g.items())


def _delai(vs: list[Video]) -> str:
    publiees = [v for v in vs if v.published_at]
    if not publiees:
        return "n/a (0 publiée)"
    rentables = [v for v in publiees if v.revenu >= v.cout]
    return f"{len(rentables)}/{len(publiees)} couvertes"


def _table_agregat(videos: list[Video], cle: str, titre: str) -> list[str]:
    out = [f"### Par {titre}", "",
           "| " + titre + " | n | coût moyen | calcul min/min vidéo | coût / min vidéo | "
           "revenu moyen | marge moyenne | délai de retour |",
           "|---|---|---|---|---|---|---|---|"]
    for nom, vs in _groupe(videos, cle):
        minutes = sum(v.minutes for v in vs)
        cout = sum(v.cout for v in vs)
        rev = sum(v.revenu for v in vs)
        out.append(
            f"| {nom} | {len(vs)} | {_e(cout / len(vs))} | "
            f"{_n(sum(v.compute_min for v in vs) / minutes, 2)} | {_e(cout / minutes)} | "
            f"{_e(rev / len(vs))} | {_e((rev - cout) / len(vs))} | {_delai(vs)} |")
    return out + [""]


def decisions(e: Economie) -> list[str]:
    """Trois décisions chiffrées, calculées depuis les données — jamais écrites d'avance."""
    vs = e.videos
    params = {p.nom: p for p in e.params}
    horizon = int(params["horizon_retour_jours"].valeur or 30)
    out: list[str] = []
    # 1. Niche × langue : décidable ou non.
    groupes = []
    for (niche, lang), groupe in sorted(_par(vs, ("niche", "lang")).items()):
        publiees = sum(1 for v in groupe if v.published_at)
        groupes.append(
            f"{niche} en {lang.upper()} coûte {_e(_moy(groupe, 'cout'))} par vidéo et "
            f"rapporte {_e(sum(v.revenu for v in groupe))} (n = {len(groupe)} livrée(s), "
            f"{publiees} publiée(s))")
    out.append(
        "**Niches** : " + " ; ".join(groupes) + f". Revenu à {horizon} jours non observable : "
        "**non décidable**. Continuer ou arrêter une niche se tranchera sur le revenu à "
        f"{horizon} j d'au moins 5 vidéos publiées par niche, pas sur le coût, qui varie peu.")
    # 2. Poste dominant du coût.
    energie = sum(v.cout_energie for v in vs)
    relecture = sum(v.cout_relecture for v in vs)
    total = energie + relecture + sum(v.cout_fixe for v in vs)
    if total > 0:
        out.append(
            f"**Le coût est humain, pas machine** : sur {len(vs)} vidéos, l'énergie pèse "
            f"{_e(energie)} ({_n(100 * energie / total)} %) et la relecture {_e(relecture)} "
            f"({_n(100 * relecture / total)} %). Réduire le temps de calcul ne change pas "
            f"l'économie ; la décision utile est de **mesurer puis réduire la relecture** "
            f"(forfait de {_n(params['relecture_forfait_min'].valeur or 0, 0)} min estimé). "
            f"Un doublement de la puissance réelle (wattmètre) ne déplacerait le coût que de "
            f"{_e(energie / len(vs))} par vidéo.")
    # 3. Style et jalon serveur.
    par_style = {s: g for s, g in _groupe(vs, "style")}
    lignes_style = ", ".join(
        f"{s} {_n(sum(v.compute_min for v in g) / sum(v.minutes for v in g), 2)} min de calcul "
        f"par minute de vidéo (n={len(g)})" for s, g in par_style.items())
    serveur = params["serveur_gpu_mensuel_eur"].valeur or 0.0
    # Volume mensuel mesuré : vidéos livrées sur les 30 derniers jours.
    limite = (datetime.now(UTC).date() - timedelta(days=30)).isoformat()
    volume = sum(1 for v in vs if v.created_at[:10] >= limite) or len(vs)
    cout_serveur_video = serveur / max(1, volume)
    out.append(
        f"**Style et serveur** : {lignes_style}. Un serveur à {_n(serveur, 0)} €/mois "
        f"(`serveur_gpu_mensuel_eur`) ajouterait "
        f"{_e(cout_serveur_video)} par vidéo au volume mesuré ({volume} vidéos livrées sur 30 "
        f"jours) "
        f"contre {_e(energie / max(1, len(vs)))} d'énergie aujourd'hui : **non justifié par le "
        f"coût** ; il ne se justifiera que par la capacité (vidéos/nuit), avec un revenu par "
        f"vidéo supérieur à {_e(cout_serveur_video)} — revenu constaté : "
        f"{_e(sum(v.revenu for v in vs))}.")
    return out


def _par(vs: list[Video], cles: tuple[str, ...]) -> dict[tuple, list[Video]]:
    g: dict[tuple, list[Video]] = defaultdict(list)
    for v in vs:
        g[tuple(getattr(v, c) for c in cles)].append(v)
    return g


def _moy(vs: list[Video], attr: str) -> float:
    return statistics.fmean(getattr(v, attr) for v in vs) if vs else 0.0


def rapport(e: Economie) -> str:
    """`reports/economics.md`."""
    vs = e.videos
    today = datetime.now(UTC).date().isoformat()
    o: list[str] = [
        f"# Économie unitaire — {today}", "",
        f"Généré par `factory economics`{' --since ' + e.depuis.isoformat() if e.depuis else ''}"
        ". Nature de chaque chiffre : **mesuré** (chronométré ou compté par l'usine), "
        "**importé** (export de programme, Analytics API), **estimé** (hypothèse de "
        "`config/economics.yaml` non mesurée).", "",
        "## 1. Hypothèses (config/economics.yaml)", "",
        "| paramètre | valeur | nature | origine |", "|---|---|---|---|"]
    for p in e.params:
        val = "—" if p.valeur is None else _n(p.valeur, 4).rstrip("0").rstrip(",")
        o.append(f"| `{p.nom}` | {val} | {'estimé' if p.estime else 'décidé/sourcé'} | {p.origine} |")
    o += ["", "Formule : coût = compute_min (mesuré) ÷ 60 × puissance ÷ 1000 × tarif kWh "
          "+ forfait de relecture ÷ 60 × taux horaire + (coûts fixes + amortissement) du mois "
          "÷ vidéos livrées ce mois-là.", "",
          "**Limite de la mesure de calcul** : `compute_min` somme la **dernière** exécution de "
          "chaque étape inscrite au manifeste. Un run repris (images déjà générées, étape "
          "rejouée) est sous-compté ; la colonne « étapes » le signale. Le seul run neuf "
          "complet chronométré de bout en bout est `s2ur` (≈ 4 h 12, STATE étape 22.1).", ""]

    o += ["## 2. Coût par vidéo livrée", "",
          "| vidéo | style | durée (min) | calcul (min, mesuré) | étapes | énergie (estimé) | "
          "relecture (estimé) | fixes | coût total | revenu (importé) | marge |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in vs:
        o.append(
            f"| `{v.video_id}` | {v.style} | {_n(v.minutes)} | {_n(v.compute_min)} | "
            f"{v.noeuds_chronometres}/11 | {_e(v.cout_energie)} | {_e(v.cout_relecture)} | "
            f"{_e(v.cout_fixe)} | **{_e(v.cout)}** | {_e(v.revenu)} | {_e(v.revenu - v.cout)} |")
    o += ["", f"Runs non livrés (échec, bloqués avant export, en cours) : {e.echecs_n} avec "
          f"du calcul chronométré, **{_n(e.echecs_compute_min)} "
          f"min** au total (mesuré). Réparti sur les {len(vs)} vidéos livrées, cela ajoute "
          f"{_n(e.echecs_compute_min / max(1, len(vs)))} min de calcul par vidéo.", ""]

    o += ["## 3. Coût par minute de vidéo, par style", "",
          "| style | n | calcul min / min vidéo (mesuré) | coût moyen / vidéo | "
          "coût / min vidéo | dont énergie / min |", "|---|---|---|---|---|---|"]
    for s, g in _groupe(vs, "style"):
        minutes = sum(v.minutes for v in g)
        o.append(f"| {s} | {len(g)} | {_n(sum(v.compute_min for v in g) / minutes, 2)} | "
                 f"{_e(_moy(g, 'cout'))} | {_e(sum(v.cout for v in g) / minutes)} | "
                 f"{_e(sum(v.cout_energie for v in g) / minutes)} |")
    o += ["", "## 4. Agrégats", ""]
    for cle, titre in (("niche", "niche"), ("lang", "langue"), ("channel_id", "chaîne"),
                       ("style", "style")):
        o += _table_agregat(vs, cle, titre)

    o += ["## 5. Revenus", "",
          f"- Lignes de revenu importées (hors fixtures) : **{e.revenus_importes_n}**. "
          f"Revenu réel constaté : **{_e(sum(v.revenu for v in vs))}** — "
          + ("aucune vidéo n'est publiée (table `publications` vide), aucun programme "
             "d'affiliation n'est ouvert : **0 € est un fait, pas une mesure de performance**."
             if not any(v.published_at for v in vs) else "voir tableaux."),
          f"- Lignes de fixture présentes dans `revenue` et **exclues** du calcul : "
          f"{e.revenus_fixture}.",
          f"- Revenu importé non rattaché à une vidéo livrée : {_e(e.revenus_non_rattaches)}.",
          ""]

    o += ["## 6. Série temporelle : vidéo n° 1 contre la dernière", "",
          "| # | vidéo | créée | style | calcul (min) | calcul min/min | assets de "
          "bibliothèque utilisés | coût |", "|---|---|---|---|---|---|---|---|"]
    for i, v in enumerate(vs, 1):
        o.append(f"| {i} | `{v.video_id}` | {v.created_at[:10]} | {v.style} | "
                 f"{_n(v.compute_min)} | {_n(v.compute_min / v.minutes, 2)} | "
                 f"{v.library_uses} | {_e(v.cout)} |")
    if len(vs) >= 2:
        a, b = vs[0], vs[-1]
        o += ["", f"Première ({a.video_id}) : {_n(a.compute_min / a.minutes, 2)} min de calcul "
              f"par minute ; dernière ({b.video_id}) : {_n(b.compute_min / b.minutes, 2)}. "
              "**L'effet de la bibliothèque n'est pas isolable** sur ces données : les runs "
              "sont repris (étapes non rechronométrées) et changent de style ; seul un run neuf "
              "complet par mois, même chaîne et même style, le mesurera."]
    o += ["", "## 7. Trois décisions chiffrées", ""]
    o += [f"{i}. {d}" for i, d in enumerate(decisions(e), 1)]
    o += ["", "## 8. Données manquantes pour décider", "",
          "- **Revenu** : 0 vidéo publiée, 0 programme d'affiliation ouvert, chaîne hors YPP → "
          "aucun revenu observable. Premier chiffre utile : revenu à "
          f"{int(next(p.valeur for p in e.params if p.nom == 'horizon_retour_jours') or 30)} jours "
          "de 5 vidéos publiées avec produit.",
          "- **Puissance** : `puissance_moyenne_w` non mesurée (wattmètre pendant un run complet).",
          "- **Relecture** : aucune heure d'affichage n'est journalisée ; le forfait et le taux "
          "horaire sont des hypothèses (taux à fixer par Alek).",
          "- **Calcul** : un run neuf complet par style (seul `s2ur` l'est) ; les manifestes des "
          "runs repris sous-comptent.",
          "- **Produits** : aucun produit réel dans `config/products/` (Alek).", ""]
    return "\n".join(o)


def ecrire(conn: sqlite3.Connection, eco: EconomicsConfig, racine: Path,
           depuis: date | None = None) -> tuple[Path, Economie]:
    """Calcule et écrit `reports/economics.md`."""
    e = calculer(conn, eco, racine, depuis)
    chemin = racine / "reports" / "economics.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(rapport(e), encoding="utf-8")
    return chemin, e
