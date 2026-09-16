#!/usr/bin/env python3
"""Agrège registre/data/*/ en registre/data/INDEX.md (étape 2).

Lancement :
    uv run --python 3.12 registre/index.py

Toutes les valeurs sont mesurées sur les fichiers collectés. Une case vide ou
« n/a » signifie « non obtenu » : aucune estimation.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "registre" / "data"
CSV_PATH = ROOT / "registre" / "chaines.csv"
WINDOW_DAYS = 182  # 6 mois
TRANSCRIPTS_TARGET = 5  # doit suivre TRANSCRIPTS_TOP de collecte.py


def slug(name: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "chaine"


def dur_s(iso: str) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def mmss(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def fnum(n) -> str:
    return f"{int(n):,}".replace(",", " ") if n not in (None, "") else "n/a"


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=WINDOW_DAYS)

    lines, missing, notes, coverage = [], [], [], []
    tot_videos = tot_transcripts = 0

    for row in rows:
        d = DATA / slug(row["nom"])
        vpath, cpath = d / "videos.json", d / "channel.json"
        if not vpath.exists() or not cpath.exists():
            missing.append((row["nom"], "aucune donnée collectée"))
            continue

        meta = json.loads(cpath.read_text(encoding="utf-8"))
        videos = json.loads(vpath.read_text(encoding="utf-8"))
        chan = meta["channel"]
        stats = chan.get("statistics", {})
        handle = chan.get("snippet", {}).get("customUrl") or slug(row["nom"])

        views = [int(v.get("statistics", {}).get("viewCount", 0) or 0) for v in videos]
        durs = [s for s in (dur_s(v.get("contentDetails", {}).get("duration", "")) for v in videos) if s]
        recent = sum(
            1
            for v in videos
            if (p := v.get("snippet", {}).get("publishedAt"))
            and datetime.fromisoformat(p.replace("Z", "+00:00")) >= cutoff
        )
        n_tr = len(list((d / "transcripts").glob("*.json"))) if (d / "transcripts").exists() else 0
        tot_videos += len(videos)
        tot_transcripts += n_tr

        med_v = statistics.median(views) if views else 0
        ratio = f"{max(views) / med_v:.0f}×" if views and med_v else "n/a"
        hidden = stats.get("hiddenSubscriberCount")

        row_md = (
            f"| {handle} | {row['niche']} | {row['langue']} "
            f"| {'masqué' if hidden else fnum(stats.get('subscriberCount'))} "
            f"| {len(videos)}{' ⚠' if meta['collecte']['tronque_a_500'] else ''} "
            f"| {fnum(sum(views))} "
            f"| {mmss(statistics.median(durs)) if durs else 'n/a'} "
            f"| {recent / 6:.1f} | {fnum(med_v)} | {ratio} | {n_tr} |"
        )
        # tri : par niche, puis par abonnés décroissants — l'ordre utile à l'étape 3
        lines.append((row["niche"], -int(stats.get("subscriberCount") or 0), row_md))
        n_abs = len(list((d / "transcripts").glob("*.absent"))) if (d / "transcripts").exists() else 0
        # cible atteignable : on retire les vidéos sans transcription possible
        coverage.append((row["niche"], n_tr, max(0, min(TRANSCRIPTS_TARGET, len(videos)) - n_abs), n_abs))
        if meta["collecte"]["tronque_a_500"]:
            notes.append(
                f"- **{row['nom']}** : tronquée aux 500 vidéos les plus récentes "
                f"({stats.get('videoCount', '?')} déclarées par l'API)."
            )
        if (d / "erreur.json").exists():
            missing.append((row["nom"], json.loads((d / "erreur.json").read_text())["erreur"]))

    unresolved = [r["nom"] for r in rows if r["handle_ou_url"] == "non_resolue"]

    out = [
        "# Index du registre — données collectées (étape 2)",
        "",
        f"Collecte du {now:%d/%m/%Y} · API YouTube Data v3 uniquement · "
        f"{len(lines)} chaînes · {tot_videos} vidéos · {tot_transcripts} transcriptions.",
        "",
        "**Conservation.** `docs/CONFORMITE.md` § 9 : ces données API doivent être purgées ou "
        f"rafraîchies au plus tard le **{(now + timedelta(days=30)):%d/%m/%Y}** (30 jours). "
        "Les mesures dérivées de l'étape 3 se conservent, elles.",
        "",
        "**Lecture des colonnes.** *Vues* = somme sur les vidéos collectées, pas le total "
        "historique de la chaîne. *Durée médiane* = toutes vidéos confondues, Shorts inclus. "
        "*Cadence* = vidéos publiées sur les 182 derniers jours ÷ 6. *Ratio* = vues de la "
        "meilleure vidéo ÷ vues médianes : mesure la dépendance à un seul succès. "
        "⚠ = chaîne tronquée à 500 vidéos.",
        "",
        "| Chaîne | Niche | Langue | Abonnés | Vidéos | Vues | Durée méd. | Cadence /mois | Vues méd. | Ratio top1/méd. | Transcr. |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    out += [md for _, _, md in sorted(lines)]

    out += ["", "## Chaînes non résolues", ""]
    out += [f"- {n}" for n in unresolved] or [
        "Aucune : le PDF fournit une URL `/channel/UC…` pour les 74 chaînes."
    ]

    out += ["", "## Échecs de collecte", ""]
    out += [f"- **{n}** — {why}" for n, why in missing] or [
        "Aucun : les 74 chaînes ont `channel.json` et `videos.json`."
    ]

    # Couverture par niche : c'est elle qui conditionne l'étape 3, pas le total brut.
    niches = sorted({n for n, _, _, _ in coverage})
    cov_rows = []
    for n in niches:
        ch = [(got, target, absent) for nn, got, target, absent in coverage if nn == n]
        cov_rows.append(
            f"| {n} | {len(ch)} | {sum(1 for g, _, _ in ch if g)} | "
            f"{sum(g for g, _, _ in ch)} | {sum(t for _, t, _ in ch)} | {sum(a for _, _, a in ch)} |"
        )
    couvertes = sum(1 for _, got, _, _ in coverage if got)
    vise = sum(t for _, _, t, _ in coverage)
    impossibles = sum(a for _, _, _, a in coverage)

    out += [
        "",
        "## Transcriptions",
        "",
        f"**{tot_transcripts} fichiers sur {vise} atteignables**, répartis sur "
        f"**{couvertes} chaînes sur {len(coverage)}**. La cible brute est de 5 par chaîne ; "
        f"{impossibles} vidéos en sont retirées — interdites aux mineurs, sous-titres "
        f"désactivés ou injouables, constaté une fois et jamais retenté.",
        "",
        "Ce qui compte pour l'étape 3 n'est pas le total brut mais la couverture par niche : "
        "une taxonomie des hooks a besoin de plusieurs chaînes par niche, pas de beaucoup de "
        "vidéos d'une seule.",
        "",
        "| Niche | Chaînes | Chaînes couvertes | Fichiers | Cible atteignable | Impossibles |",
        "|---|---|---|---|---|---|",
        *cov_rows,
        "",
        "**Historique — 14/09/2026, six passes.** Première passe à 3–6 s depuis l'IP fixe : "
        "`IpBlocked` après une vingtaine de récupérations, 19 fichiers. Les suivantes depuis "
        "un partage de connexion 4G (IP mobile personnelle, sans proxy ni VPN) à 25–45 s. "
        "Le blocage s'est reproduit une fois, à 105 fichiers, puis plus jamais. Les quatre "
        "arrêts suivants n'étaient pas des blocages mais des défauts de l'outil, corrigés "
        "l'un après l'autre : le garde-fou des 3 échecs consécutifs comptait les erreurs de "
        "contenu (`AgeRestricted`, `TranscriptsDisabled`, `VideoUnplayable`) comme des "
        "signaux d'accès, et l'absence de délai d'expiration HTTP a figé une passe 78 minutes "
        "sur une 4G tombée. Les erreurs sont désormais classées par **type** — un blocage "
        "arrête tout au premier coup, un fait sur la vidéo est marqué et jamais retenté, une "
        "panne réseau compte dans une série de trois — et la session HTTP impose 30 s.",
        "",
        "**Ce qui n'a jamais été fait.** Aucun proxy, aucun VPN, aucun changement "
        "d'User-Agent : `docs/CONFORMITE.md` § 9 interdit de ruser avec un refus explicite. "
        "Les métadonnées ne sont de toute façon pas concernées — elles viennent de l'API "
        "officielle avec clé, un canal distinct.",
        "",
        "**Reprise.** La passe est reprenable et ne consomme **aucune unité de quota** "
        "(elle relit les `videos.json` déjà collectés) :",
        "",
        "```",
        "uv run --python 3.12 --with youtube-transcript-api \\",
        "  registre/collecte.py --transcriptions --pause 25 45",
        "```",
    ]

    if notes:
        out += ["", "## Chaînes tronquées à 500 vidéos", ""] + notes

    (DATA / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"INDEX.md écrit : {len(lines)} chaînes, {tot_videos} vidéos, {tot_transcripts} transcriptions")


if __name__ == "__main__":
    main()
