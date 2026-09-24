"""`factory analytics show` — métriques d'une vidéo, courbe de rétention, chutes situées.

Une chute est une baisse de plus de `SEUIL_CHUTE_PTS` points de `audienceWatchRatio` entre
deux points consécutifs de la courbe (1 % de la durée chacun). Son instant est rattaché au
segment du script qui passe à ce moment, via `voice/timings.json` (position dans `voice.wav`,
supposée alignée sur la vidéo finale) et `script.json` (rôle du segment).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.core.paths import RunPaths

SEUIL_CHUTE_PTS = 5.0
COLONNES = 50
HAUTEUR = 10
LATENCE_H = 72


@dataclass
class Chute:
    ratio: float
    pts: float
    t_s: float
    libelle: str


def mmss(secondes: float) -> str:
    s = int(round(secondes))
    return f"{s // 60:02d}:{s % 60:02d}"


def resoudre(conn: sqlite3.Connection, ident: str) -> sqlite3.Row | None:
    """Accepte l'identifiant de run ou l'identifiant YouTube."""
    return conn.execute(
        "SELECT * FROM v_video_perf WHERE video_id = ? OR youtube_video_id = ?",
        (ident, ident)).fetchone()


def age_heures(publish_at: str | None) -> float | None:
    if not publish_at:
        return None
    try:
        quand = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if quand.tzinfo is None:
        quand = quand.replace(tzinfo=UTC)
    return (datetime.now(UTC) - quand).total_seconds() / 3600


def courbe_ascii(points: list[list[float]]) -> list[str]:
    """100 points → 50 colonnes (moyenne par paire), HAUTEUR lignes, axe en %."""
    valeurs = [p[1] for p in points]
    pas = max(1, len(valeurs) // COLONNES)
    cols = [sum(valeurs[i:i + pas]) / len(valeurs[i:i + pas])
            for i in range(0, len(valeurs), pas)][:COLONNES]
    haut = max(1.0, max(cols) if cols else 1.0)
    lignes = []
    for rang in range(HAUTEUR, 0, -1):
        seuil = haut * (rang - 0.5) / HAUTEUR
        etiquette = f"{haut * rang / HAUTEUR * 100:5.0f} %|" if rang in (HAUTEUR, HAUTEUR // 2) \
            else "       |"
        lignes.append(etiquette + "".join("█" if v >= seuil else " " for v in cols))
    lignes.append("       +" + "-" * len(cols))
    lignes.append("        0 %" + " " * (len(cols) - 14) + "100 % de la durée")
    return lignes


def _segments(chemins: RunPaths) -> tuple[list[dict], dict[str, str], list[dict]]:
    """(segments de timings, rôle par id de segment, segments sponsorisés)."""
    timings = json.loads((chemins.racine / "voice" / "timings.json").read_text("utf-8"))
    roles: dict[str, str] = {}
    script = chemins.racine / "script.json"
    if script.is_file():
        for seg in json.loads(script.read_text("utf-8")).get("segments", []):
            roles[seg["id"]] = seg.get("role", "?")
    sponsors: list[dict] = []
    manifeste = chemins.racine / "manifest.json"
    if manifeste.is_file():
        sponsors = json.loads(manifeste.read_text("utf-8")).get("conformite", {}) \
            .get("sponsor_segments", []) or []
    return timings.get("segments", []), roles, sponsors


def situer(t_s: float, segments: list[dict], roles: dict[str, str],
           sponsors: list[dict]) -> str:
    """« segment 4 (seg_04), rôle point, début du segment » pour un instant de la vidéo."""
    for rang, seg in enumerate(segments):
        if seg["start_s"] <= t_s < seg["end_s"] or rang == len(segments) - 1:
            ident = seg["id"]
            role = roles.get(ident) or roles.get((seg.get("merged_from") or [ident])[0], "?")
            morceaux = [f"segment {rang} ({ident})", f"rôle {role}"]
            if t_s - seg["start_s"] <= 3.0:
                morceaux.append("début du segment")
            elif seg["end_s"] - t_s <= 3.0:
                morceaux.append("fin du segment")
            for sp in sponsors:
                debut = sp.get("start_s")
                if debut is not None and abs(t_s - debut) <= 5.0:
                    morceaux.append(f"début du {sp.get('type', 'sponsor')}")
            return ", ".join(morceaux)
    return "hors narration"


def chutes(points: list[list[float]], duree_s: float, segments: list[dict],
           roles: dict[str, str], sponsors: list[dict]) -> list[Chute]:
    """Baisses > SEUIL_CHUTE_PTS entre deux points consécutifs, situées dans le script."""
    trouvees = []
    for avant, apres in zip(points, points[1:], strict=False):
        pts = (avant[1] - apres[1]) * 100
        if pts > SEUIL_CHUTE_PTS:
            t = apres[0] * duree_s
            libelle = situer(t, segments, roles, sponsors) if segments else "timings absents"
            trouvees.append(Chute(apres[0], pts, t, libelle))
    return trouvees


def rapport_video(conn: sqlite3.Connection, ident: str) -> list[str]:
    ligne = resoudre(conn, ident)
    if ligne is None:
        return [f"« {ident} » : aucune publication connue (table publications)."]
    vid = ligne["video_id"]
    sortie = [f"{vid}  ·  youtube {ligne['youtube_video_id']}  ·  {ligne['channel_id']}",
              f"publiée {ligne['publish_at']}  ·  statut {ligne['publish_status']}"]
    age = age_heures(ligne["publish_at"])
    if age is not None and age < LATENCE_H:
        sortie.append(f"⚠ publiée il y a {age:.0f} h (< {LATENCE_H} h) : données provisoires, "
                      "aucune conclusion — un zéro ici n'est pas un zéro.")
    def f(v, fmt="{:.0f}"):
        return "non mesuré" if v is None else fmt.format(v)
    sortie += [
        "",
        f"  vues 7 j / 30 j        {f(ligne['views_7d'])} / {f(ligne['views_30d'])}",
        f"  % moyen vu 7 j         {f(ligne['avg_view_pct_7d'], '{:.1f} %')}",
        f"  durée moyenne 7 j      {f(ligne['avg_view_duration_7d'], '{:.0f} s')}",
        f"  impressions 7 j        {f(ligne['impressions_7d'])}",
        f"  CTR 7 j                {f(None if ligne['ctr_7d'] is None else ligne['ctr_7d'] * 100, '{:.2f} %')}",
        f"  abonnés 7 j / 30 j     {f(ligne['subs_7d'])} / {f(ligne['subs_30d'])}",
        f"  jours relevés          {ligne['days_pulled']} (dernier : {ligne['last_date'] or '—'})",
        f"  fenêtre 7 j complète   {'oui' if ligne['complete_7d'] else 'non'}",
    ]
    trafic = conn.execute(
        "SELECT source_type, sum(views) v FROM perf_traffic WHERE video_id = ? "
        "GROUP BY source_type ORDER BY v DESC LIMIT 5", (vid,)).fetchall()
    if trafic:
        sortie.append("  sources                " +
                      ", ".join(f"{t['source_type']} {t['v']}" for t in trafic))
    courbe = conn.execute(
        "SELECT * FROM retention_curves WHERE video_id = ? ORDER BY day_after_publish DESC "
        "LIMIT 1", (vid,)).fetchone()
    if courbe is None:
        sortie += ["", "Rétention : aucune courbe capturée (jalons J+2, J+7, J+30)."]
        return sortie
    points = json.loads(courbe["points_json"])
    sortie += ["", f"Rétention à J+{courbe['day_after_publish']} "
                   f"(capturée {courbe['captured_at']}, {len(points)} points) :"]
    sortie += courbe_ascii(points)
    chemins = RunPaths.depuis_video_id(vid)
    duree = ligne["duration_s"]
    segments, roles, sponsors = [], {}, []
    if (chemins.racine / "voice" / "timings.json").is_file():
        segments, roles, sponsors = _segments(chemins)
        if duree is None:
            duree = segments[-1]["end_s"] if segments else None
    if duree is None:
        sortie.append("Chutes : durée inconnue, non situées.")
        return sortie
    trouvees = chutes(points, float(duree), segments, roles, sponsors)
    sortie.append("")
    if not trouvees:
        sortie.append(f"Aucune chute > {SEUIL_CHUTE_PTS:.0f} pts entre deux points.")
    for c in trouvees:
        sortie.append(f"chute de {c.pts:.0f} pts à {mmss(c.t_s)} : {c.libelle}")
    return sortie


def rapport_chaine(conn: sqlite3.Connection, channel: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM v_video_perf WHERE channel_id = ? ORDER BY publish_at DESC",
        (channel,)).fetchall()
