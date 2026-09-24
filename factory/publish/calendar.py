"""Calendrier de publication — `factory calendar plan | show` (étape 23.2).

Publier comme une petite équipe humaine prudente, jamais comme une machine :

- **cadence par chaîne** : `config/channels/<id>.yaml § cadence`, plafonnée par CONFORMITE § 6
  (≤ 2/semaine pendant les 90 premiers jours, `orchestrator.yaml § calendrier`) ;
- **créneaux** : jours et heures locales de l'audience, lus dans la config de la chaîne
  (initialisée depuis `REFERENTIEL.json → niches.<niche>.creneaux`), remplacés par
  `learned/weights.json` quand l'étape 26 l'aura écrit ;
- **jitter** ± `cadence.jitter_min`, tiré par vidéo et reproductible (graine = run + créneau) ;
- **anti-rafale** : 48 h minimum entre deux vidéos d'une chaîne, jamais deux vidéos BMS à
  moins d'une heure (4 h entre chaînes de même langue), jamais plus de 2 vidéos BMS sur
  24 h glissantes ; un seul upload privé par tour du daemon, avance tirée par vidéo ;
- **variation de durée** entre vidéos consécutives d'une chaîne (≥ 10 %), corrigée sur la
  cible des jobs pas encore scriptés, sinon signalée.

Aucune valeur de règle n'est écrite ici : tout vient de `CalendrierConfig` et de `Cadence`,
dont les bornes pydantic sont celles de CONFORMITE. Le module ne publie rien : il écrit
`jobs.publish_at` (UTC) ; `publier_echeances` confie ensuite chaque vidéo due à
`youtube.publier_run`, qui passe par `precheck` avant tout appel d'API.
"""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from factory.core import config as config_module
from factory.core.models import CalendrierConfig, Channel
from factory.core.paths import RunPaths, racine_projet

#: Jobs qu'on date : produits ou en production. `blocked`/`failed` n'ont pas d'avenir certain.
A_PLANIFIER = ("queued", "running", "awaiting_review", "exported")
#: Jobs dont la date compte dans les contraintes.
DATES_VIVANTES = ("queued", "running", "awaiting_review", "exported", "published")
#: Étapes avant lesquelles la durée cible peut encore changer sans rien jeter.
AVANT_SCRIPT = ("plan", "research")
JOURS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ESSAIS_JITTER = 6


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(FORMAT)


def _lire_iso(valeur: str) -> datetime:
    return datetime.strptime(valeur, FORMAT).replace(tzinfo=UTC)


# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------


@dataclass
class Contexte:
    racine: Path
    cal: CalendrierConfig
    chaines: dict[str, Channel]
    appris: dict[str, Any]


def contexte(racine: Path | None = None) -> Contexte:
    racine = racine or racine_projet()
    cfg = config_module.charger(racine, strict=False)
    cal = cfg.orchestrator.calendrier if cfg.orchestrator else CalendrierConfig()
    appris: dict[str, Any] = {}
    # Version vérifiée par le chargeur commun : fichier absent ou incompatible → config.
    from factory.analytics import weights as wmod

    fichier = racine / cal.fichier_creneaux_appris
    if fichier.resolve() == (racine / wmod.CHEMIN).resolve():
        appris = (wmod.charger(racine) or {}).get("channels") or {}
    elif fichier.exists():
        try:
            appris = json.loads(fichier.read_text(encoding="utf-8")).get("channels", {})
        except (OSError, ValueError):
            appris = {}
    return Contexte(racine=racine, cal=cal, chaines=dict(cfg.channels), appris=appris)


def creneaux(ctx: Contexte, chaine: Channel) -> tuple[list[str], list[str], str]:
    """(jours, heures locales, source). `learned/weights.json` prime sur la config.

    Format attendu de l'étape 26 : `{"channels": {"<id>": {"days": [...], "hours_local":
    ["HH:MM", ...]}}}`. Une entrée incomplète est ignorée, pas complétée.
    """
    appris = ctx.appris.get(chaine.id) or {}
    jours = [j for j in appris.get("days", []) if j in JOURS]
    heures = [h for h in appris.get("hours_local", []) if isinstance(h, str) and len(h) == 5]
    if jours and heures:
        return jours, heures, "learned/weights.json"
    return list(chaine.cadence.days), list(chaine.cadence.hours_local), "config"


def plafond_semaine(ctx: Contexte, chaine: Channel, jour: date) -> int:
    """Plafond hebdomadaire à cette date : config, borné par l'âge de la chaîne (§ 6)."""
    cree = chaine.cadence.created_at
    jeune = cree is None or (jour - cree).days < ctx.cal.age_jeune_chaine_jours
    if jeune:
        return min(chaine.cadence.per_week_max, ctx.cal.plafond_semaine_jeune_chaine)
    return chaine.cadence.per_week_max


# --------------------------------------------------------------------------------------
# Événements (dates déjà posées)
# --------------------------------------------------------------------------------------


@dataclass
class Evenement:
    video_id: str
    channel_id: str
    at: datetime
    statut: str
    job_id: int | None = None
    duree_s: float | None = None
    source: str = "config"


def duree_prevue(video_id: str, racine: Path) -> float | None:
    """Durée mesurée (`qc.json`) si le run est exporté, sinon cible de `spec.json`."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    qc = chemins.racine / "qc.json"
    if qc.exists():
        try:
            mesure = json.loads(qc.read_text(encoding="utf-8"))["metrics"]["duree_vs_run"]
            return float(mesure["value"])
        except (KeyError, ValueError, TypeError, OSError):
            pass
    spec = chemins.racine / "spec.json"
    if spec.exists():
        try:
            return float(json.loads(spec.read_text(encoding="utf-8"))["target_duration_s"])
        except (KeyError, ValueError, TypeError, OSError):
            return None
    return None


def evenements(conn: sqlite3.Connection, racine: Path) -> list[Evenement]:
    """Toutes les dates vivantes : jobs datés, plus publications hors file."""
    vus: set[str] = set()
    sortie: list[Evenement] = []
    marques = ",".join("?" * len(DATES_VIVANTES))
    for ligne in conn.execute(
        f"SELECT id, video_id, channel_id, status, publish_at, publish_plan FROM jobs "
        f"WHERE publish_at IS NOT NULL AND status IN ({marques}) ORDER BY id",
        DATES_VIVANTES,
    ):
        if ligne["video_id"] in vus:
            continue
        vus.add(ligne["video_id"])
        plan = json.loads(ligne["publish_plan"] or "{}")
        sortie.append(Evenement(
            video_id=ligne["video_id"], channel_id=ligne["channel_id"],
            at=_lire_iso(ligne["publish_at"]), statut=ligne["status"], job_id=ligne["id"],
            duree_s=duree_prevue(ligne["video_id"], racine),
            source=plan.get("source", "config")))
    for ligne in conn.execute(
        "SELECT video_id, channel_id, status, publish_at FROM publications "
        "WHERE publish_at IS NOT NULL AND status != 'failed'"
    ):
        if ligne["video_id"] in vus:
            continue
        vus.add(ligne["video_id"])
        sortie.append(Evenement(
            video_id=ligne["video_id"], channel_id=ligne["channel_id"],
            at=_lire_iso(ligne["publish_at"]), statut=ligne["status"],
            duree_s=duree_prevue(ligne["video_id"], racine), source="publications"))
    return sorted(sortie, key=lambda e: e.at)


# --------------------------------------------------------------------------------------
# Contraintes — une seule implémentation, pour `plan` comme pour `--check`
# --------------------------------------------------------------------------------------


@dataclass
class Violation:
    regle: str
    message: str
    videos: list[str] = field(default_factory=list)


def _semaine(moment: datetime, chaine: Channel) -> tuple[int, int]:
    iso = moment.astimezone(ZoneInfo(chaine.cadence.timezone)).isocalendar()
    return iso[0], iso[1]


def parente(video_id: str | None, racine: Path) -> set[str]:
    """Parent et enfants d'un run (étape 24) : une déclinaison ne sort jamais le même jour."""
    if not video_id:
        return set()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    liens: set[str] = set()
    try:
        spec = json.loads(chemins.spec.read_text(encoding="utf-8"))
        if spec.get("parent_id"):
            liens.add(spec["parent_id"])
        manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
        liens |= {e.get("video_id") for e in manifeste.get("children") or [] if e.get("video_id")}
    except (OSError, json.JSONDecodeError):
        pass
    return liens


def admissible(ctx: Contexte, chaine: Channel, candidat: datetime,
               existants: list[Evenement], video_id: str | None = None) -> str | None:
    """`None` si `candidat` respecte toutes les règles face à `existants`, sinon la raison."""
    cal = ctx.cal
    # Moins de 24 h d'écart couvre « le même jour » dans tout fuseau.
    for e in existants:
        if e.video_id in parente(video_id, ctx.racine) \
                and abs(e.at - candidat) < timedelta(hours=24):
            return f"même jour que {e.video_id} (parent ou déclinaison)"
    siens = [e for e in existants if e.channel_id == chaine.id]
    for e in siens:
        if abs(e.at - candidat) < timedelta(hours=cal.espacement_chaine_h):
            return f"moins de {cal.espacement_chaine_h} h après {e.video_id}"
    semaine = _semaine(candidat, chaine)
    plafond = plafond_semaine(ctx, chaine, candidat.date())
    if sum(1 for e in siens if _semaine(e.at, chaine) == semaine) >= plafond:
        return f"plafond de {plafond}/semaine atteint"
    for e in existants:
        if abs(e.at - candidat) < timedelta(minutes=cal.exclusion_portefeuille_min):
            return f"à moins de {cal.exclusion_portefeuille_min} min de {e.video_id}"
        if e.at.replace(minute=0, second=0) == candidat.replace(minute=0, second=0):
            return f"même heure que {e.video_id}"
        autre = ctx.chaines.get(e.channel_id)
        if autre is not None and autre.id != chaine.id and autre.lang == chaine.lang \
                and abs(e.at - candidat) < timedelta(minutes=cal.ecart_meme_langue_min):
            return f"à moins de {cal.ecart_meme_langue_min} min de {e.video_id} (même langue)"
    # Fenêtre glissante : aucune tranche de 24 h ne porte plus de N vidéos.
    for pivot in sorted([candidat, *[e.at for e in existants]]):
        fenetre = [t for t in [candidat, *[e.at for e in existants]]
                   if pivot <= t < pivot + timedelta(hours=24)]
        if candidat in fenetre and len(fenetre) > cal.max_par_jour_portefeuille:
            return f"plus de {cal.max_par_jour_portefeuille} vidéos BMS sur 24 h"
    return None


def verifier(ctx: Contexte, evts: list[Evenement],
             maintenant: datetime | None = None) -> tuple[list[Violation], list[str]]:
    """Test de contraintes intégré (`--check`) : (violations, avertissements)."""
    cal = ctx.cal
    maintenant = maintenant or datetime.now(UTC)
    violations: list[Violation] = []
    avertissements: list[str] = []
    par_chaine: dict[str, list[Evenement]] = defaultdict(list)
    for e in evts:
        par_chaine[e.channel_id].append(e)

    for cid, liste in par_chaine.items():
        chaine = ctx.chaines.get(cid)
        if chaine is None:
            violations.append(Violation("chaine", f"{cid} absente de config/channels",
                                        [e.video_id for e in liste]))
            continue
        liste.sort(key=lambda e: e.at)
        for a, b in zip(liste, liste[1:]):
            if b.at - a.at < timedelta(hours=cal.espacement_chaine_h):
                violations.append(Violation(
                    "espacement_chaine",
                    f"{cid} : {a.video_id} et {b.video_id} à "
                    f"{(b.at - a.at).total_seconds() / 3600:.1f} h (< {cal.espacement_chaine_h} h)",
                    [a.video_id, b.video_id]))
        semaines: dict[tuple[int, int], list[Evenement]] = defaultdict(list)
        for e in liste:
            semaines[_semaine(e.at, chaine)].append(e)
        for (annee, num), groupe in semaines.items():
            plafond = plafond_semaine(ctx, chaine, groupe[0].at.date())
            if len(groupe) > plafond:
                violations.append(Violation(
                    "plafond_semaine",
                    f"{cid} : {len(groupe)} vidéos en semaine {annee}-S{num:02d} (> {plafond})",
                    [e.video_id for e in groupe]))
        minutes = {e.at.minute for e in liste}
        if len(liste) >= 3 and len(minutes) == 1:
            avertissements.append(f"{cid} : toutes les dates tombent à la minute "
                                  f":{minutes.pop():02d} — le jitter ne se voit pas")
        fuseau = ZoneInfo(chaine.cadence.timezone)
        locales = [e.at.astimezone(fuseau) for e in liste]
        heures = [t.hour * 60 + t.minute for t in locales]
        if len(liste) >= 3 and max(heures) - min(heures) < 60:
            avertissements.append(f"{cid} : {len(liste)} dates dans la même heure locale "
                                  f"(étendue {max(heures) - min(heures)} min) — trop régulier")
        if len(liste) >= 4 and len({t.weekday() for t in locales}) == 1:
            avertissements.append(f"{cid} : toujours le même jour de semaine")
        for a, b in zip(liste, liste[1:]):
            if a.duree_s and b.duree_s:
                ecart = abs(b.duree_s - a.duree_s) / a.duree_s
                if ecart < cal.variation_duree_min:
                    avertissements.append(
                        f"{cid} : {a.video_id} ({a.duree_s:.0f} s) puis {b.video_id} "
                        f"({b.duree_s:.0f} s) — écart {ecart:.0%} < "
                        f"{cal.variation_duree_min:.0%}")

    tous = sorted(evts, key=lambda e: e.at)
    for a, b in zip(tous, tous[1:]):
        if b.at - a.at < timedelta(minutes=cal.exclusion_portefeuille_min):
            violations.append(Violation(
                "exclusion_portefeuille",
                f"{a.video_id} et {b.video_id} à {(b.at - a.at).total_seconds() / 60:.0f} min "
                f"(< {cal.exclusion_portefeuille_min})", [a.video_id, b.video_id]))
    par_heure: dict[datetime, list[str]] = defaultdict(list)
    for e in tous:
        par_heure[e.at.replace(minute=0, second=0)].append(e.video_id)
    for heure, videos in par_heure.items():
        if len(videos) > 1:
            violations.append(Violation("meme_heure", f"{len(videos)} vidéos BMS dans l'heure "
                                        f"{heure:%Y-%m-%d %H}h UTC", videos))
    for i, a in enumerate(tous):
        for b in tous[i + 1:]:
            if b.at - a.at >= timedelta(minutes=cal.ecart_meme_langue_min):
                break
            la, lb = ctx.chaines.get(a.channel_id), ctx.chaines.get(b.channel_id)
            if la and lb and la.id != lb.id and la.lang == lb.lang:
                violations.append(Violation(
                    "ecart_meme_langue", f"{a.video_id} et {b.video_id} ({la.lang}) à "
                    f"{(b.at - a.at).total_seconds() / 60:.0f} min "
                    f"(< {cal.ecart_meme_langue_min})", [a.video_id, b.video_id]))
    for a in tous:
        for b in tous:
            if a.video_id < b.video_id and b.video_id in parente(a.video_id, ctx.racine) \
                    and abs(b.at - a.at) < timedelta(hours=24):
                violations.append(Violation(
                    "meme_jour_parent", f"{a.video_id} et sa déclinaison {b.video_id} à moins "
                    "de 24 h", [a.video_id, b.video_id]))
    for i, a in enumerate(tous):
        fenetre = [b for b in tous[i:] if b.at - a.at < timedelta(hours=24)]
        if len(fenetre) > cal.max_par_jour_portefeuille:
            violations.append(Violation(
                "max_par_24h", f"{len(fenetre)} vidéos BMS en 24 h à partir de {_iso(a.at)} "
                f"(> {cal.max_par_jour_portefeuille})", [e.video_id for e in fenetre]))
    for e in tous:
        if e.at < maintenant and e.statut in ("queued", "running", "awaiting_review",
                                              "exported"):
            violations.append(Violation(
                "date_depassee", f"{e.video_id} : date {_iso(e.at)} dépassée, statut "
                f"{e.statut} — `factory calendar plan --replan` (jamais de rattrapage)",
                [e.video_id]))
    return violations, avertissements


# --------------------------------------------------------------------------------------
# Planification
# --------------------------------------------------------------------------------------


@dataclass
class Decision:
    job_id: int
    video_id: str
    channel_id: str
    publish_at: str | None
    raison: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RapportPlan:
    decisions: list[Decision] = field(default_factory=list)
    ecartes: list[Decision] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    durees_ajustees: list[str] = field(default_factory=list)


def _graine(*parties: str) -> int:
    return int(hashlib.sha256("|".join(parties).encode()).hexdigest()[:12], 16)


def _candidats(ctx: Contexte, chaine: Channel, video_id: str, debut: datetime,
               fin: datetime) -> tuple[list[tuple[datetime, datetime, int]], str]:
    """Créneaux de base de la chaîne entre `debut` et `fin`, chacun avec ses jitters tirés."""
    jours, heures, source = creneaux(ctx, chaine)
    fuseau = ZoneInfo(chaine.cadence.timezone)
    j = chaine.cadence.jitter_min
    sortie: list[tuple[datetime, datetime, int]] = []
    jour = debut.astimezone(fuseau).date()
    while datetime.combine(jour, time(0), fuseau) <= fin:
        if JOURS[jour.weekday()] in jours:
            for h in heures:
                base = datetime.combine(jour, time.fromisoformat(h), fuseau)
                tirage = random.Random(_graine(video_id, base.isoformat()))
                for _ in range(ESSAIS_JITTER):
                    decal = tirage.randint(-j, j)
                    sortie.append((base, (base + timedelta(minutes=decal)).astimezone(UTC)
                                   .replace(second=0, microsecond=0), decal))
        jour += timedelta(days=1)
    return sortie, source


def _a_planifier(conn: sqlite3.Connection, replan: bool) -> list[sqlite3.Row]:
    marques = ",".join("?" * len(A_PLANIFIER))
    condition = "" if replan else "AND publish_at IS NULL"
    lignes = conn.execute(
        f"SELECT * FROM jobs WHERE status IN ({marques}) {condition} "
        "ORDER BY priority DESC, created_at, id", A_PLANIFIER).fetchall()
    vus: set[str] = set()
    uniques = []
    for l in lignes:
        if l["video_id"] not in vus:
            vus.add(l["video_id"])
            uniques.append(l)
    # Alternance des chaînes : aucune ne prend tous les premiers créneaux.
    par_chaine: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for l in uniques:
        par_chaine[l["channel_id"]].append(l)
    ordre: list[sqlite3.Row] = []
    while any(par_chaine.values()):
        for cid in sorted(par_chaine):
            if par_chaine[cid]:
                ordre.append(par_chaine[cid].pop(0))
    return ordre


def planifier(conn: sqlite3.Connection, *, semaines: int = 3, racine: Path | None = None,
              maintenant: datetime | None = None, replan: bool = False, ecrire: bool = True,
              echo: Callable[[str], None] | None = None) -> RapportPlan:
    """`factory calendar plan` : date chaque job exporté ou en cours qui n'en a pas."""
    from factory.publish import precheck

    ctx = contexte(racine)
    dire = echo or (lambda _: None)
    maintenant = (maintenant or datetime.now(UTC)).replace(second=0, microsecond=0)
    fin = maintenant + timedelta(weeks=semaines)
    rapport = RapportPlan()
    jobs = _a_planifier(conn, replan)
    a_dater = {l["video_id"] for l in jobs}
    existants = [e for e in evenements(conn, ctx.racine) if e.video_id not in a_dater]
    # Rang de production : un job produit après un autre ne publie pas avant lui.
    file_prod = [l["video_id"] for l in sorted(jobs, key=lambda l: (-l["priority"],
                                                                     l["created_at"], l["id"]))
                 if l["status"] != "exported"]
    dernier: dict[str, datetime] = {}

    for job in jobs:
        vid, cid = job["video_id"], job["channel_id"]
        chaine = ctx.chaines.get(cid)
        if chaine is None:
            rapport.ecartes.append(Decision(job["id"], vid, cid, None,
                                            "chaîne absente de config/channels"))
            continue
        if job["status"] == "exported":
            # Un run exporté sans relecture valable ne mérite pas un créneau : precheck le
            # bloquerait de toute façon, et il volerait la place d'une vidéo publiable.
            refus = precheck.refus_relecture(vid, cid, ctx.racine, conn)
            if refus:
                rapport.ecartes.append(Decision(job["id"], vid, cid, None, refus))
                continue
        if job["status"] == "exported":
            delai = ctx.cal.delai_exporte_h
        else:
            delai = ctx.cal.delai_production_h \
                + file_prod.index(vid) * ctx.cal.heures_par_job_en_file
        debut = maintenant + timedelta(hours=delai)
        if cid in dernier:
            debut = max(debut, dernier[cid])
        candidats, source = _candidats(ctx, chaine, vid, debut, fin)
        admis: list[tuple[datetime, datetime, int]] = []
        derniere_base = None
        for base, moment, decal in candidats:
            if base == derniere_base or not (debut <= moment <= fin):
                continue
            if admissible(ctx, chaine, moment, existants, vid) is None:
                admis.append((base, moment, decal))
                derniere_base = base
                if len(admis) >= ctx.cal.choix_parmi:
                    break
        if not admis:
            rapport.ecartes.append(Decision(
                job["id"], vid, cid, None,
                f"aucun créneau admissible d'ici {fin:%Y-%m-%d} (cadence, espacement ou "
                "portefeuille saturés)"))
            continue
        base, moment, decal = random.Random(_graine(vid, "choix")).choice(admis)
        detail = {"base_locale": base.isoformat(), "jitter_min": decal, "source": source,
                  "fuseau": chaine.cadence.timezone, "planifie_le": _iso(maintenant),
                  "plafond_semaine": plafond_semaine(ctx, chaine, moment.date())}
        existants.append(Evenement(vid, cid, moment, job["status"], job["id"],
                                   duree_prevue(vid, ctx.racine), source))
        dernier[cid] = moment
        rapport.decisions.append(Decision(job["id"], vid, cid, _iso(moment), "planifié", detail))
        dire(f"{cid:18} {vid} → {moment.astimezone(ZoneInfo(chaine.cadence.timezone)):%a %d/%m %H:%M} "
             f"({_iso(moment)}, jitter {decal:+d} min)")

    rapport.durees_ajustees = _varier_durees(conn, ctx, existants, ecrire)
    if ecrire:
        with conn:
            for d in rapport.decisions:
                conn.execute("UPDATE jobs SET publish_at = ?, publish_plan = ?, updated_at = ? "
                             "WHERE video_id = ? AND status IN ("
                             + ",".join("?" * len(A_PLANIFIER)) + ")",
                             (d.publish_at, json.dumps(d.detail, ensure_ascii=False),
                              _iso(datetime.now(UTC)), d.video_id, *A_PLANIFIER))
    _, rapport.avertissements = verifier(ctx, evenements(conn, ctx.racine) if ecrire
                                         else existants, maintenant)
    return rapport


def _varier_durees(conn: sqlite3.Connection, ctx: Contexte, evts: list[Evenement],
                   ecrire: bool) -> list[str]:
    """Écarte d'au moins `variation_duree_min` la durée cible d'un job pas encore scripté.

    On ne touche qu'aux jobs dont `script.json` n'existe pas : ailleurs, changer la cible
    jetterait des heures de production pour un avertissement.
    """
    faits: list[str] = []
    if not ctx.cal.facteurs_duree:
        return faits
    par_chaine: dict[str, list[Evenement]] = defaultdict(list)
    for e in sorted(evts, key=lambda e: e.at):
        par_chaine[e.channel_id].append(e)
    for cid, liste in par_chaine.items():
        for rang, (a, b) in enumerate(zip(liste, liste[1:])):
            if not (a.duree_s and b.duree_s):
                continue
            if abs(b.duree_s - a.duree_s) / a.duree_s >= ctx.cal.variation_duree_min:
                continue
            chemins = RunPaths.depuis_video_id(b.video_id, ctx.racine)
            etape = conn.execute("SELECT stage FROM jobs WHERE video_id = ? ORDER BY id DESC",
                                 (b.video_id,)).fetchone()
            if chemins.script.exists() or etape is None or etape["stage"] not in AVANT_SCRIPT:
                continue
            bas, haut = (ctx.cal.facteurs_duree + ctx.cal.facteurs_duree)[:2]
            tirage = random.Random(_graine(b.video_id, "duree"))
            for _ in range(20):
                f = round(tirage.uniform(bas, haut), 3)
                cible = round(a.duree_s * f)
                if abs(cible - a.duree_s) / a.duree_s >= ctx.cal.variation_duree_min:
                    break
            else:
                continue
            spec = chemins.racine / "spec.json"
            donnees = json.loads(spec.read_text(encoding="utf-8"))
            ancienne = donnees.get("target_duration_s")
            if ecrire:
                donnees["target_duration_s"] = int(cible)
                spec.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
            b.duree_s = float(cible)
            faits.append(f"{b.video_id} : cible {ancienne} → {cible} s "
                         f"(×{f:g} de {a.video_id}, {cid})")
    return faits


# --------------------------------------------------------------------------------------
# Lecture
# --------------------------------------------------------------------------------------


def lignes_par_semaine(ctx: Contexte, evts: list[Evenement]) -> dict[str, list[dict[str, str]]]:
    """`factory calendar show` : une liste de lignes par semaine ISO (lundi, UTC)."""
    semaines: dict[str, list[dict[str, str]]] = defaultdict(list)
    for e in sorted(evts, key=lambda e: (e.at, e.channel_id)):
        chaine = ctx.chaines.get(e.channel_id)
        fuseau = ZoneInfo(chaine.cadence.timezone) if chaine else UTC
        local = e.at.astimezone(fuseau)
        lundi = (e.at.date() - timedelta(days=e.at.weekday()))
        cle = f"semaine du {lundi:%d/%m/%Y} (S{e.at.isocalendar()[1]:02d})"
        semaines[cle].append({
            "chaine": e.channel_id, "jour": f"{local:%a %d/%m}", "heure": f"{local:%H:%M}",
            "fuseau": str(fuseau), "utc": f"{e.at:%d/%m %H:%M}",
            "paris": f"{e.at.astimezone(ZoneInfo('Europe/Paris')):%a %d/%m %H:%M}",
            "run": e.video_id, "statut": e.statut,
            "duree": f"{e.duree_s / 60:.1f} min" if e.duree_s else "—",
        })
    return dict(semaines)


def date_pour(conn: sqlite3.Connection, video_id: str, channel_id: str,
              racine: Path | None = None) -> str | None:
    """Point d'accroche de `youtube.date_prevue` : la date posée par `plan`, sinon `None`."""
    ligne = conn.execute(
        "SELECT publish_at FROM jobs WHERE video_id = ? AND channel_id = ? "
        "AND publish_at IS NOT NULL ORDER BY id DESC LIMIT 1", (video_id, channel_id),
    ).fetchone()
    return ligne["publish_at"] if ligne else None


# --------------------------------------------------------------------------------------
# Daemon
# --------------------------------------------------------------------------------------


def publier_echeances(conn: sqlite3.Connection, *, racine: Path | None = None,
                      maintenant: datetime | None = None,
                      echo: Callable[[str], None] | None = None) -> list[str]:
    """Téléverse (en privé) les jobs exportés dont la date approche.

    - precheck bloque → le job passe `blocked` avec la raison ; rien n'est envoyé ;
    - erreur de publication (jeton absent, quota) → journalisée, le job reste `exported` et
      sera retenté au tour suivant ;
    - succès → `published` (en ligne en privé ; public seulement par Studio ou `publishAt`).
    """
    from factory.orchestrator import journal
    from factory.orchestrator import queue as file_module
    from factory.publish import youtube

    ctx = contexte(racine)
    dire = echo or (lambda _: None)
    faits: list[str] = []
    if not ctx.cal.upload_auto:
        return faits
    maintenant = maintenant or datetime.now(UTC)
    # Un seul upload par tour, et jamais deux à moins de `ecart_uploads_min` : pas de lot.
    dernier_upload = conn.execute(
        "SELECT max(uploaded_at) FROM publications WHERE uploaded_at IS NOT NULL").fetchone()[0]
    if dernier_upload and _lire_iso(dernier_upload) > maintenant - timedelta(
            minutes=ctx.cal.ecart_uploads_min):
        return faits
    bas, haut = sorted(ctx.cal.avance_upload_h)
    candidats = conn.execute(
        "SELECT j.* FROM jobs j WHERE j.status = 'exported' AND j.publish_at IS NOT NULL "
        "AND j.publish_at > ? AND j.publish_at <= ? AND NOT EXISTS (SELECT 1 FROM "
        "publications p WHERE p.video_id = j.video_id AND p.status != 'failed') "
        "ORDER BY j.publish_at", (_iso(maintenant),
                                  _iso(maintenant + timedelta(hours=haut)))).fetchall()
    dus = []
    for job in candidats:
        avance = random.Random(_graine(job["video_id"], "upload")).randint(bas, haut)
        if _lire_iso(job["publish_at"]) - timedelta(hours=avance) <= maintenant:
            dus.append(job)
    for job in dus[:1]:
        vid, cid = job["video_id"], job["channel_id"]
        bloquants = youtube.precheck(vid, cid, ctx.racine)
        if bloquants:
            file_module.bloquer(conn, int(job["id"]),
                                "precheck : " + " · ".join(bloquants)[:900], racine=ctx.racine)
            faits.append(f"{vid} bloqué par precheck")
            continue
        try:
            youtube.publier_run(vid, cid, racine=ctx.racine, conn=conn, journal=dire)
        except Exception as erreur:  # noqa: BLE001 — la file ne meurt pas d'un upload
            journal.evenement("WARN", f"upload de {vid} reporté : {erreur}", video_id=vid,
                              donnees={"channel_id": cid, "publish_at": job["publish_at"]},
                              racine=ctx.racine, conn=conn)
            faits.append(f"{vid} reporté : {erreur}")
            continue
        with conn:
            conn.execute("UPDATE jobs SET status = 'published', updated_at = ? WHERE id = ?",
                         (_iso(datetime.now(UTC)), job["id"]))
        faits.append(f"{vid} téléversé (privé), date {job['publish_at']}")
    return faits
