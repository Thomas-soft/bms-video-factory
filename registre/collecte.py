#!/usr/bin/env python3
"""Collecte du registre de chaînes via l'API YouTube Data v3 (étape 2).

Lancement :
    uv run --python 3.12 \
        --with google-api-python-client,youtube-transcript-api,requests,python-dotenv \
        registre/collecte.py > registre/collecte.log 2>&1

Conformité (docs/CONFORMITE.md § 9) : API officielle uniquement, aucun search.list,
aucun yt-dlp. Les transcriptions de vidéos tierces sont réservées à la recherche
(étapes 3 et 16), à faible volume, depuis une IP résidentielle. Chaque
enregistrement porte fetched_at : le cache doit être purgé ou rafraîchi à 30 jours.
"""

from __future__ import annotations

import csv
import json
import os
import random
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "registre" / "chaines.csv"
DATA_DIR = ROOT / "registre" / "data"

MAX_VIDEOS = 500          # plafond par chaîne (les plus récentes)
PAGE_SIZE = 50            # maximum imposé par l'API
THUMBS_TOP = 10           # miniatures téléchargées, par vues décroissantes
TRANSCRIPTS_TOP = 5       # transcriptions tentées, par vues décroissantes
QUOTA_LIMIT = 8000        # arrêt automatique (plafond projet : 10 000 unités/jour)
TRANSCRIPT_FAILS_MAX = 3  # échecs consécutifs avant arrêt des transcriptions
TRANSCRIPT_PAUSE = (3, 6)  # pause aléatoire entre deux appels, en secondes
BLOCKING_ERRORS = {"IpBlocked", "RequestBlocked", "TooManyRequests", "YouTubeRequestFailed"}


HTTP_TIMEOUT = 30  # secondes : sans lui, un socket mort suspend la passe indéfiniment


def _timeout_session():
    """Session HTTP avec délai d'expiration imposé.

    youtube-transcript-api n'en fixe aucun : sur une 4G qui tombe, l'appel reste
    suspendu pour toujours et la passe se fige sans rien écrire — constaté le
    14/09/2026, 78 minutes de blocage muet. Avec un délai, la panne devient une
    exception « transitoire » que le garde-fou sait traiter.
    """

    class _S(requests.Session):
        def request(self, *args, **kwargs):
            kwargs.setdefault("timeout", HTTP_TIMEOUT)
            return super().request(*args, **kwargs)

    return _S()


def classify(exc: BaseException) -> str:
    """« blocage » | « transitoire » | « definitif ».

    Classement par type et non par nom : énumérer les noms d'erreurs de contenu
    revient à en oublier une, et chaque oubli tue la passe entière. Ici, tout ce
    qui hérite de CouldNotRetrieveTranscript sans être un blocage décrit **la
    vidéo** (interdite aux mineurs, sous-titres coupés, injouable) — un fait qui
    ne guérira pas et ne dit rien de notre accès.
    """
    from youtube_transcript_api import _errors as E

    if isinstance(exc, E.RequestBlocked):  # couvre IpBlocked
        return "blocage"
    if isinstance(
        exc,
        (E.YouTubeRequestFailed, E.PoTokenRequired, E.YouTubeDataUnparsable,
         E.FailedToCreateConsentCookie, E.CookieError),
    ):
        return "transitoire"  # panne côté service ou configuration, pas la vidéo
    if isinstance(exc, E.CouldNotRetrieveTranscript):
        return "definitif"
    return "transitoire"  # réseau, délai dépassé, inconnu

quota_used = 0
transcript_fail_streak = 0
transcripts_stopped = False


class QuotaReached(Exception):
    """Le plafond d'unités fixé pour la session est atteint."""


def log(msg: str) -> None:
    print(f"{datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def spend(units: int, label: str) -> None:
    """Comptabilise les unités de quota et arrête la collecte au plafond."""
    global quota_used
    if quota_used + units > QUOTA_LIMIT:
        raise QuotaReached(f"{quota_used} + {units} dépasserait {QUOTA_LIMIT} ({label})")
    quota_used += units


def slug(name: str) -> str:
    """Nom de dossier déterministe, calculable sans appel API (reprise)."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "chaine"


def channel_id_of(row: dict) -> str | None:
    m = re.search(r"(UC[0-9A-Za-z_-]{22})", row["handle_ou_url"])
    return m.group(1) if m else None


def iso_duration_seconds(iso: str) -> int | None:
    m = re.fullmatch(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or ""
    )
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


# --------------------------------------------------------------------------- API


def fetch_channels(yt, ids: list[str]) -> dict[str, dict]:
    """channels.list par lots de 50 identifiants — 1 unité par appel."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), PAGE_SIZE):
        batch = ids[i : i + PAGE_SIZE]
        spend(1, "channels.list")
        resp = (
            yt.channels()
            .list(
                part="snippet,statistics,contentDetails,brandingSettings",
                id=",".join(batch),
                maxResults=PAGE_SIZE,
            )
            .execute()
        )
        for item in resp.get("items", []):
            out[item["id"]] = item
        log(f"  channels.list : {len(batch)} demandées, {len(resp.get('items', []))} reçues")
    return out


def fetch_upload_ids(yt, uploads_playlist: str) -> tuple[list[str], bool]:
    """playlistItems.list paginé — 1 unité par page de 50. Retourne (ids, tronqué)."""
    ids: list[str] = []
    token = None
    skipped = 0
    while len(ids) < MAX_VIDEOS:
        spend(1, "playlistItems.list")
        resp = (
            yt.playlistItems()
            .list(
                part="contentDetails,status",
                playlistId=uploads_playlist,
                maxResults=PAGE_SIZE,
                pageToken=token,
            )
            .execute()
        )
        for item in resp.get("items", []):
            if item.get("status", {}).get("privacyStatus") != "public":
                skipped += 1
                continue
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                ids.append(vid)
        token = resp.get("nextPageToken")
        if not token:
            break
    if skipped:
        log(f"  {skipped} entrées non publiques ignorées")
    truncated = bool(token) and len(ids) >= MAX_VIDEOS
    return ids[:MAX_VIDEOS], truncated


def fetch_videos(yt, ids: list[str]) -> list[dict]:
    """videos.list par lots de 50 identifiants — 1 unité par appel."""
    out: list[dict] = []
    for i in range(0, len(ids), PAGE_SIZE):
        batch = ids[i : i + PAGE_SIZE]
        spend(1, "videos.list")
        resp = (
            yt.videos()
            .list(
                part="snippet,contentDetails,statistics,status",
                id=",".join(batch),
                maxResults=PAGE_SIZE,
            )
            .execute()
        )
        out.extend(resp.get("items", []))
    return out


# ------------------------------------------------------------------ miniatures


def download_thumbs(videos: list[dict], dest: Path) -> int:
    """maxresdefault, repli hqdefault, repli miniature déclarée par l'API."""
    dest.mkdir(parents=True, exist_ok=True)
    ok = 0
    for v in videos:
        vid = v["id"]
        target = dest / f"{vid}.jpg"
        if target.exists():
            ok += 1
            continue
        thumbs = v.get("snippet", {}).get("thumbnails", {})
        urls = [
            f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        ]
        for key in ("maxres", "standard", "high"):
            if key in thumbs:
                urls.append(thumbs[key]["url"])
        for url in urls:
            try:
                r = requests.get(url, timeout=20)
                if r.status_code == 200 and len(r.content) > 2000:
                    target.write_bytes(r.content)
                    ok += 1
                    break
            except requests.RequestException:
                continue
    return ok


# ---------------------------------------------------------------- transcriptions


def fetch_transcripts(videos: list[dict], dest: Path, lang: str) -> tuple[int, list[str]]:
    """5 vidéos les plus vues, pause aléatoire 3–6 s, arrêt après 3 échecs d'affilée."""
    global transcript_fail_streak, transcripts_stopped
    from youtube_transcript_api import YouTubeTranscriptApi

    dest.mkdir(parents=True, exist_ok=True)
    api = YouTubeTranscriptApi(http_client=_timeout_session())
    wanted = [lang, "en"] if lang != "en" else ["en"]
    ok, errors = 0, []

    for v in videos:
        if transcripts_stopped:
            break
        vid = v["id"]
        target = dest / f"{vid}.json"
        if target.exists():
            ok += 1
            continue
        if (dest / f"{vid}.absent").exists():
            continue  # échec définitif déjà constaté : ne pas dépenser une pause
        time.sleep(random.uniform(*TRANSCRIPT_PAUSE))
        try:
            listing = api.list(vid)
            available = [
                {
                    "language_code": t.language_code,
                    "language": t.language,
                    "is_generated": t.is_generated,
                }
                for t in listing
            ]
            tr, last_exc = None, None
            for codes in (wanted, [a["language_code"] for a in available]):
                try:
                    tr = listing.find_transcript(codes).fetch()
                    break
                except Exception as exc:  # noqa: BLE001 — on relaie l'erreur d'origine
                    last_exc = exc
            if tr is None:
                # ne jamais masquer la cause : IpBlocked et NoTranscriptFound
                # appellent des décisions opposées.
                raise last_exc or RuntimeError("aucune piste exploitable")
            target.write_text(
                json.dumps(
                    {
                        "video_id": vid,
                        "language": tr.language,
                        "language_code": tr.language_code,
                        "is_generated": tr.is_generated,
                        "available": available,
                        "fetched_at": now_iso(),
                        "snippets": tr.to_raw_data(),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ok += 1
            transcript_fail_streak = 0
        except Exception as exc:  # noqa: BLE001 — l'API lève des types variés
            name = type(exc).__name__
            errors.append(f"{vid}: {name}")
            genre = classify(exc)
            if genre == "definitif":
                # marqueur non-.json : il n'entre pas dans le compte des transcriptions
                (dest / f"{vid}.absent").write_text(f"{name} {now_iso()}\n", encoding="utf-8")
                transcript_fail_streak = 0
                continue
            if genre == "blocage":
                # YouTube a coupé l'accès : insister aggrave le blocage et sort
                # du « faible volume » autorisé par docs/CONFORMITE.md § 9.
                transcripts_stopped = True
                log(f"  TRANSCRIPTIONS ARRÊTÉES : blocage YouTube ({name}) — reprise dans 24 à 48 h")
                break
            transcript_fail_streak += 1
            if transcript_fail_streak >= TRANSCRIPT_FAILS_MAX:
                transcripts_stopped = True
                log(f"  TRANSCRIPTIONS ARRÊTÉES : {TRANSCRIPT_FAILS_MAX} échecs consécutifs (dernier {name})")
    return ok, errors


# ---------------------------------------------------------------------- chaîne


def collect_channel(yt, row: dict, chan: dict | None, cid: str) -> None:
    name = row["nom"]
    d = DATA_DIR / slug(name)
    d.mkdir(parents=True, exist_ok=True)

    if chan is None:
        log(f"[{name}] ÉCHEC : channels.list ne renvoie rien pour {cid}")
        (d / "erreur.json").write_text(
            json.dumps({"channel_id": cid, "erreur": "introuvable", "fetched_at": now_iso()}),
            encoding="utf-8",
        )
        return

    uploads = chan["contentDetails"]["relatedPlaylists"].get("uploads")
    if not uploads:
        log(f"[{name}] ÉCHEC : pas de playlist d'uploads")
        return

    ids, truncated = fetch_upload_ids(yt, uploads)
    videos = fetch_videos(yt, ids)
    videos.sort(key=lambda v: v.get("snippet", {}).get("publishedAt", ""))

    stats = chan.get("statistics", {})
    (d / "channel.json").write_text(
        json.dumps(
            {
                "fetched_at": now_iso(),
                "registre": row,
                "collecte": {
                    "videos_uploads_listes": len(ids),
                    "videos_resolues": len(videos),
                    "tronque_a_500": truncated,
                    "videos_declarees_api": stats.get("videoCount"),
                },
                "channel": chan,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (d / "videos.json").write_text(json.dumps(videos, ensure_ascii=False), encoding="utf-8")

    top = sorted(
        videos, key=lambda v: int(v.get("statistics", {}).get("viewCount", 0) or 0), reverse=True
    )
    n_thumbs = download_thumbs(top[:THUMBS_TOP], d / "thumbs")
    n_tr, tr_err = (0, [])
    if not transcripts_stopped:
        n_tr, tr_err = fetch_transcripts(top[:TRANSCRIPTS_TOP], d / "transcripts", row["langue"])

    log(
        f"[{name}] {len(videos)} vidéos"
        f"{' (TRONQUÉ à 500)' if truncated else ''}"
        f" · abonnés {stats.get('subscriberCount', 'n/a')}"
        f" · {n_thumbs} miniatures · {n_tr}/{TRANSCRIPTS_TOP} transcriptions"
        f"{' · ' + ', '.join(tr_err) if tr_err else ''}"
        f" · quota {quota_used}"
    )


# ------------------------------------------------------------------------ main


def pass_transcripts_only(pause: tuple[float, float] = (8, 15), limit: int | None = None) -> int:
    """Passe de rattrapage des transcriptions, sans aucun appel à l'API Data v3.

    Rejoue les vidéos manquantes à partir des videos.json déjà collectés, à
    cadence lente. Lancement : registre/collecte.py --transcriptions
    Options : --pause MIN MAX (secondes, défaut 8 15) · --limit N (lot de test).
    """
    global TRANSCRIPT_PAUSE
    TRANSCRIPT_PAUSE = pause  # cadence prudente après un blocage
    rows = {r["nom"]: r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8"))}
    log(f"Passe transcriptions seules · pause {TRANSCRIPT_PAUSE[0]}–{TRANSCRIPT_PAUSE[1]} s · 0 unité de quota")

    # Ordre de parcours : les niches les moins couvertes d'abord. Un blocage peut
    # tomber à tout moment ; mieux vaut qu'il laisse 11 niches entamées qu'une seule
    # complète — l'étape 3 a besoin d'étendue, pas de profondeur sur une niche.
    couverture: dict[str, int] = {}
    for r in rows.values():
        d = DATA_DIR / slug(r["nom"])
        n = len(list((d / "transcripts").glob("*.json"))) if (d / "transcripts").exists() else 0
        couverture[r["niche"]] = couverture.get(r["niche"], 0) + n
    ordre = sorted(rows.values(), key=lambda r: (couverture.get(r["niche"], 0), r["niche"]))

    total, attempted, budget = 0, 0, limit
    for row in ordre:
        if transcripts_stopped or (budget is not None and budget <= 0):
            break
        d = DATA_DIR / slug(row["nom"])
        vpath = d / "videos.json"
        if not vpath.exists():
            continue
        videos = json.loads(vpath.read_text(encoding="utf-8"))
        top = sorted(
            videos, key=lambda v: int(v.get("statistics", {}).get("viewCount", 0) or 0), reverse=True
        )[:TRANSCRIPTS_TOP]
        tdir = d / "transcripts"
        manquantes = [
            v
            for v in top
            if not (tdir / f"{v['id']}.json").exists() and not (tdir / f"{v['id']}.absent").exists()
        ]
        total += len(top) - len(manquantes)  # déjà obtenues lors d'une passe antérieure
        if not manquantes:
            continue
        if budget is not None:
            manquantes = manquantes[:budget]
            budget -= len(manquantes)
        attempted += 1
        n, errs = fetch_transcripts(manquantes, d / "transcripts", row["langue"])
        total += n
        log(f"[{row['nom']}] {n}/{len(manquantes)} transcriptions{' · ' + ', '.join(errs) if errs else ''}")

    log(f"FIN passe transcriptions · {total} fichiers · {attempted} chaînes tentées · quota consommé : 0 unité")
    return 1 if transcripts_stopped else 0


def arg_pair(argv: list[str], flag: str, default):
    """Lit « --flag a b » (ou « --flag n ») ; refuse plutôt que de deviner."""
    if flag not in argv:
        return default
    i = argv.index(flag)
    n = 2 if isinstance(default, tuple) else 1
    vals = argv[i + 1 : i + 1 + n]
    if len(vals) != n:
        raise SystemExit(f"ARRÊT : {flag} attend {n} valeur(s)")
    try:
        nums = [float(v) for v in vals]
    except ValueError:
        raise SystemExit(f"ARRÊT : {flag} attend des nombres, reçu {' '.join(vals)}") from None
    if n == 2:
        if not 0 < nums[0] <= nums[1]:
            raise SystemExit(f"ARRÊT : {flag} MIN MAX exige 0 < MIN ≤ MAX")
        return (nums[0], nums[1])
    return int(nums[0])


def main() -> int:
    argv = sys.argv[1:]
    if "--transcriptions" in argv:
        return pass_transcripts_only(
            pause=arg_pair(argv, "--pause", (8.0, 15.0)),
            limit=arg_pair(argv, "--limit", None),
        )
    load_dotenv(ROOT / ".env")
    key = os.environ.get("YT_API_KEY", "").strip()
    if not key:
        log("ARRÊT : YT_API_KEY absente de .env")
        return 2

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Registre : {len(rows)} chaînes · plafond {QUOTA_LIMIT} unités · max {MAX_VIDEOS} vidéos/chaîne")

    todo, skipped, unresolved = [], 0, []
    for row in rows:
        cid = channel_id_of(row)
        if not cid:
            unresolved.append(row["nom"])
            continue
        if (DATA_DIR / slug(row["nom"]) / "videos.json").exists():
            skipped += 1
            continue
        todo.append((row, cid))
    log(f"À collecter : {len(todo)} · déjà fait (reprise) : {skipped} · non résolues : {len(unresolved)}")
    for n in unresolved:
        log(f"  NON RÉSOLUE : {n}")

    yt = build("youtube", "v3", developerKey=key, cache_discovery=False)
    code = 0
    try:
        chans = fetch_channels(yt, [cid for _, cid in todo])
        for row, cid in todo:
            try:
                collect_channel(yt, row, chans.get(cid), cid)
            except QuotaReached:
                raise
            except HttpError as exc:
                log(f"[{row['nom']}] ERREUR HTTP : {exc}")
                code = 1
            except Exception as exc:  # noqa: BLE001
                log(f"[{row['nom']}] ERREUR : {type(exc).__name__}: {exc}")
                code = 1
    except QuotaReached as exc:
        log(f"ARRÊT AUTOMATIQUE — plafond de quota atteint : {exc}")
        code = 1
    except HttpError as exc:
        log(f"ERREUR HTTP globale : {exc}")
        code = 1

    done = len(list(DATA_DIR.glob("*/videos.json")))
    log(f"FIN · dossiers avec videos.json : {done} · transcriptions arrêtées : {transcripts_stopped}")
    log(f"quota consommé : {quota_used} unités sur un plafond de {QUOTA_LIMIT}")
    return code


if __name__ == "__main__":
    sys.exit(main())
