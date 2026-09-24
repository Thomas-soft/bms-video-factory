"""Courbes de rétention alignées sur les segments du script (étape 26).

Une courbe YouTube = ~100 points `[elapsedVideoTimeRatio, audienceWatchRatio]`. Chaque segment
de `voice/timings.json` est projeté en ratio de durée ; la chute sur le segment (en points de
rétention) est comparée à la chute de la **courbe moyenne de la chaîne** sur le même intervalle.
L'excès de chute, agrégé par rôle et par position, donne des règles **candidates** — jamais des
décisions sous `n_min_regle_retention` observations.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

GRILLE = np.linspace(0.0, 1.0, 101)
#: Rôles canoniques : `point` avec interruption = `rupture` ; tout segment chevauchant un
#: segment sponsorisé = `sponsor`.
ROLES = ("hook", "contexte", "point", "rupture", "sponsor", "cta", "conclusion")
#: Frontière de position des règles (« avant 40 % »).
COUPURE_POSITION = 0.40


@dataclass
class SegmentAligne:
    video_id: str
    channel_id: str
    segment_id: str
    role: str
    debut: float  # ratio de durée
    fin: float
    chute_pts: float  # rétention(debut) − rétention(fin), en points
    chute_ref_pts: float | None  # même intervalle sur la courbe moyenne de la chaîne
    exces_pts: float | None  # chute − chute_ref (positif = on perd plus que d'habitude)

    @property
    def position(self) -> str:
        return f"avant {COUPURE_POSITION:.0%}" if self.debut < COUPURE_POSITION \
            else f"après {COUPURE_POSITION:.0%}"


def sur_grille(points: list[list[float]]) -> np.ndarray:
    """Courbe interpolée sur 101 points, lissée par moyenne mobile de 3 points."""
    pts = sorted((float(x), float(r)) for x, r in points if x is not None and r is not None)
    if len(pts) < 2:
        raise ValueError("courbe de rétention : moins de 2 points")
    xs, rs = zip(*pts, strict=True)
    brute = np.interp(GRILLE, xs, rs)
    lisse = brute.copy()
    lisse[1:-1] = (brute[:-2] + brute[1:-1] + brute[2:]) / 3.0
    return lisse


def courbe_moyenne(courbes: list[np.ndarray]) -> np.ndarray | None:
    return None if not courbes else np.mean(np.vstack(courbes), axis=0)


def _valeur(courbe: np.ndarray, x: float) -> float:
    return float(np.interp(min(1.0, max(0.0, x)), GRILLE, courbe))


def role_de(seg_script: dict[str, Any] | None, debut_s: float, fin_s: float,
            sponsors: list[dict]) -> str:
    for sp in sponsors:
        a, b = sp.get("start_s"), sp.get("end_s")
        if a is not None and b is not None and a < fin_s and b > debut_s:
            return "sponsor"
    role = (seg_script or {}).get("role") or "?"
    if role == "point" and (seg_script or {}).get("interrupt"):
        return "rupture"
    return role


def aligner(video_id: str, channel_id: str, courbe: np.ndarray, duree_s: float,
            segments: list[dict], scripts: dict[str, dict], sponsors: list[dict],
            reference: np.ndarray | None) -> list[SegmentAligne]:
    """Chute par segment, en points, et excès par rapport à la courbe de référence."""
    if duree_s <= 0:
        raise ValueError("durée nulle : alignement impossible")
    alignes = []
    for seg in segments:
        ident = seg["id"]
        script = scripts.get(ident) or scripts.get((seg.get("merged_from") or [ident])[0])
        debut, fin = seg["start_s"] / duree_s, min(1.0, seg["end_s"] / duree_s)
        if fin <= debut:
            continue
        chute = (_valeur(courbe, debut) - _valeur(courbe, fin)) * 100
        ref = None if reference is None else (_valeur(reference, debut) - _valeur(reference, fin)) * 100
        alignes.append(SegmentAligne(
            video_id, channel_id, ident, role_de(script, seg["start_s"], seg["end_s"], sponsors),
            round(debut, 4), round(fin, 4), round(chute, 2),
            None if ref is None else round(ref, 2),
            None if ref is None else round(chute - ref, 2)))
    return alignes


def regles_candidates(alignes: list[SegmentAligne], n_min: int) -> list[dict[str, Any]]:
    """Agrège l'excès de chute par (rôle, position). `n` = nombre de segments **et** de vidéos."""
    groupes: dict[tuple[str, str], list[SegmentAligne]] = defaultdict(list)
    for a in alignes:
        if a.exces_pts is not None:
            groupes[(a.role, a.position)].append(a)
    regles = []
    for (role, position), segs in sorted(groupes.items()):
        exces = np.array([s.exces_pts for s in segs], dtype=float)
        chutes = np.array([s.chute_pts for s in segs], dtype=float)
        n_videos = len({s.video_id for s in segs})
        moyenne = float(exces.mean())
        et = float(exces.std(ddof=1) / np.sqrt(len(exces))) if len(exces) > 1 else None
        # La décision porte sur le nombre de VIDÉOS : 12 segments d'une seule vidéo
        # ne font pas une règle.
        decidable = n_videos >= n_min
        texte = (f"{role} {position} : chute moyenne de {chutes.mean():.1f} pts, "
                 f"{moyenne:+.1f} pts par rapport à la courbe moyenne de la chaîne, "
                 f"n={len(segs)} segments / {n_videos} vidéos")
        regles.append({
            "role": role, "position": position, "n_segments": len(segs), "n_videos": n_videos,
            "drop_pts_mean": round(float(chutes.mean()), 2),
            "excess_pts_mean": round(moyenne, 2),
            "excess_pts_se": None if et is None else round(et, 2),
            "status": "candidate" if decidable else f"non décidable (n={n_videos} vidéos)",
            "text": texte,
        })
    return regles


def charger_segments(racine_run: Path) -> tuple[list[dict], dict[str, dict], list[dict], float | None]:
    """(segments de timings, segments de script par id, sponsors, durée) d'un run."""
    timings = json.loads((racine_run / "voice" / "timings.json").read_text("utf-8"))
    scripts: dict[str, dict] = {}
    script = racine_run / "script.json"
    if script.is_file():
        scripts = {s["id"]: s for s in json.loads(script.read_text("utf-8")).get("segments", [])}
    sponsors: list[dict] = []
    manifeste = racine_run / "manifest.json"
    if manifeste.is_file():
        sponsors = json.loads(manifeste.read_text("utf-8")).get("conformite", {}) \
            .get("sponsor_segments", []) or []
    segs = timings.get("segments", [])
    duree = timings.get("total_duration_s") or (segs[-1]["end_s"] if segs else None)
    return segs, scripts, sponsors, duree


def analyser(videos: list[dict[str, Any]], n_min: int) -> dict[str, Any]:
    """`videos` : dicts {video_id, channel_id, points, duree_s, segments, scripts, sponsors}.

    Renvoie les segments alignés, les règles candidates et le nombre de courbes par chaîne.
    """
    courbes: dict[str, list[tuple[dict, np.ndarray]]] = defaultdict(list)
    for v in videos:
        courbes[v["channel_id"]].append((v, sur_grille(v["points"])))
    alignes: list[SegmentAligne] = []
    for chaine, liste in courbes.items():
        for v, c in liste:
            # Référence = moyenne des AUTRES courbes de la chaîne (sinon la vidéo se compare
            # à elle-même) ; sans autre courbe, pas de référence et pas d'excès.
            autres = [c2 for v2, c2 in liste if v2 is not v]
            alignes += aligner(v["video_id"], chaine, c, float(v["duree_s"]), v["segments"],
                               v["scripts"], v["sponsors"], courbe_moyenne(autres))
    return {
        "n_curves": sum(len(x) for x in courbes.values()),
        "curves_by_channel": {k: len(x) for k, x in courbes.items()},
        "segments": [asdict(a) | {"position": a.position} for a in alignes],
        "rules": regles_candidates(alignes, n_min),
    }
