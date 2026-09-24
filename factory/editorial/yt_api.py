"""Accès à l'API YouTube Data v3 pour l'entrepôt éditorial.

Les fonctions d'appel viennent de `registre/collecte.py` (étape 2), qui reste
inchangé : ce script s'exécute dans un environnement éphémère (`uv run --with …`)
où le paquet `factory` n'est pas installé. C'est ici la version canonique ; le
script de l'étape 2 est un livrable clos qui garde sa copie.

Conformité (docs/CONFORMITE.md § 9) : API officielle seulement, **jamais**
`search.list`, jamais yt-dlp, aucune transcription dans ce pipeline.

Deux compartiments de quota depuis juin 2026 :
  - compartiment principal, 10 000 unités/jour — `channels.list`,
    `playlistItems.list`, `videos.list`, 1 unité par appel ;
  - compartiment propre à `videos.batchGetStats`, 10 000 unités/jour,
    1 unité par appel.
Chacun a son compteur, et chacun son plafond.
"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from factory.core.paths import racine_projet

PAGE_SIZE = 50  # maximum imposé par l'API pour playlistItems.list

# Ni `videos.list` ni `videos:batchGetStats` ne documentent de maximum
# d'identifiants par appel. **Mesuré le 20/09/2026 sur l'API réelle** : 50 passent,
# 100 renvoient une 400 sur les deux méthodes. La limite est donc 50.
IDS_PAR_APPEL = 50


class QuotaAtteint(Exception):
    """Le plafond d'unités fixé pour l'exécution est atteint."""


class Compteur:
    """Compteur d'unités à deux compartiments, avec arrêt propre au plafond.

    `depense()` refuse **avant** l'appel : le plafond est une garantie, pas une
    constatation après coup.
    """

    def __init__(self, plafond: int, plafond_batch: int | None = None) -> None:
        self.plafond = plafond
        self.plafond_batch = plafond if plafond_batch is None else plafond_batch
        self.unites = 0
        self.unites_batch = 0
        self.appels: dict[str, int] = {}

    def depense(self, unites: int, label: str, *, batch: bool = False) -> None:
        if batch:
            if self.unites_batch + unites > self.plafond_batch:
                raise QuotaAtteint(
                    f"batchGetStats : {self.unites_batch} + {unites} dépasserait "
                    f"{self.plafond_batch} ({label})"
                )
            self.unites_batch += unites
        else:
            if self.unites + unites > self.plafond:
                raise QuotaAtteint(
                    f"{self.unites} + {unites} dépasserait {self.plafond} ({label})"
                )
            self.unites += unites
        self.appels[label] = self.appels.get(label, 0) + unites

    @property
    def total(self) -> int:
        """Unités consommées, tous compartiments confondus — ce que dit le rapport."""
        return self.unites + self.unites_batch


# --------------------------------------------------------------------- outils


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def aujourdhui() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def slug(nom: str) -> str:
    """Nom de dossier déterministe, calculable sans appel API."""
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "chaine"


def channel_id_of(url_ou_handle: str) -> str | None:
    """Extrait un UC… d'une URL de chaîne. Les @handles ne portent pas l'identifiant."""
    m = re.search(r"(UC[0-9A-Za-z_-]{22})", url_ou_handle or "")
    return m.group(1) if m else None


def iso_duration_seconds(iso: str) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _entier(valeur) -> int | None:
    """Les compteurs de l'API arrivent en chaînes ; un champ masqué arrive absent."""
    if valeur is None:
        return None
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def charge_cle() -> str:
    """Clé API depuis l'environnement ou `.env`. Jamais journalisée, jamais affichée."""
    cle = os.environ.get("YT_API_KEY", "").strip()
    if cle:
        return cle
    env = racine_projet() / ".env"
    if env.exists():
        for ligne in env.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if ligne.startswith("YT_API_KEY="):
                return ligne.split("=", 1)[1].strip().strip("'\"")
    raise RuntimeError("YT_API_KEY absente de l'environnement et de .env")


def construire_client(cle: str | None = None):
    """Client Data v3. `cache_discovery=False` : le cache de découverte casse sous uv."""
    from googleapiclient.discovery import build

    return build("youtube", "v3", developerKey=cle or charge_cle(), cache_discovery=False)


def batch_disponible(yt) -> bool:
    """`videos.batchGetStats` est-il exposé par le document de découverte ?

    Sonde réelle, pas une date codée en dur : la méthode apparaît dans le client
    construit si et seulement si l'API la publie.
    """
    try:
        return hasattr(yt.videos(), "batchGetStats")
    except Exception:  # noqa: BLE001 — une sonde ne doit jamais casser la collecte
        return False


# ----------------------------------------------------------------- appels API


def fetch_channels(yt, compteur: Compteur, ids: list[str]) -> dict[str, dict]:
    """channels.list par lots de 50 — 1 unité par appel, pas par chaîne."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), PAGE_SIZE):
        lot = ids[i : i + PAGE_SIZE]
        compteur.depense(1, "channels.list")
        resp = (
            yt.channels()
            .list(part="snippet,statistics,contentDetails", id=",".join(lot), maxResults=PAGE_SIZE)
            .execute()
        )
        for item in resp.get("items", []):
            out[item["id"]] = item
    return out


def fetch_upload_ids(
    yt, compteur: Compteur, uploads_playlist: str, *, max_videos: int, pages_max: int
) -> tuple[list[str], bool]:
    """playlistItems.list — 1 unité par page de 50. Retourne (ids, tronqué).

    L'API ne **garantit** aucun ordre pour cette playlist (documentation muette) ;
    l'ordre observé est antéchronologique. On ne s'appuie donc pas sur l'ordre pour
    décider ce qui est nouveau : c'est l'absence en base qui le décide.
    """
    ids: list[str] = []
    token = None
    pages = 0
    while len(ids) < max_videos and pages < pages_max:
        compteur.depense(1, "playlistItems.list")
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
        pages += 1
        for item in resp.get("items", []):
            if item.get("status", {}).get("privacyStatus") != "public":
                continue
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                ids.append(vid)
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids[:max_videos], bool(token)


def fetch_videos(yt, compteur: Compteur, ids: list[str]) -> list[dict]:
    """videos.list par lots — 1 unité par appel. Métadonnées complètes + statistiques."""
    out: list[dict] = []
    for i in range(0, len(ids), IDS_PAR_APPEL):
        lot = ids[i : i + IDS_PAR_APPEL]
        compteur.depense(1, "videos.list")
        resp = (
            yt.videos()
            .list(part="snippet,contentDetails,statistics", id=",".join(lot), maxResults=PAGE_SIZE)
            .execute()
        )
        out.extend(resp.get("items", []))
    return out


def fetch_stats(yt, compteur: Compteur, ids: list[str], *, batch: bool) -> dict[str, dict]:
    """Statistiques seules : {video_id: {views, likes, comments}}.

    `videos.batchGetStats` quand l'API l'expose — 1 unité dans **son propre**
    compartiment, donc sans toucher au budget des autres appels. Repli
    `videos.list` par 50 sinon. Les deux chemins rendent la même forme.

    `dislikeCount` est privé depuis décembre 2021 et `favoriteCount` vaut 0 depuis
    2015 : ni l'un ni l'autre n'est demandé ni stocké.
    """
    out: dict[str, dict] = {}
    for i in range(0, len(ids), IDS_PAR_APPEL):
        lot = ids[i : i + IDS_PAR_APPEL]
        if batch:
            compteur.depense(1, "videos.batchGetStats", batch=True)
            resp = yt.videos().batchGetStats(part="id,statistics", id=",".join(lot)).execute()
        else:
            compteur.depense(1, "videos.list(statistics)")
            resp = (
                yt.videos()
                .list(part="id,statistics", id=",".join(lot), maxResults=PAGE_SIZE)
                .execute()
            )
        for item in resp.get("items", []):
            st = item.get("statistics", {})
            out[item["id"]] = {
                "views": _entier(st.get("viewCount")),
                "likes": _entier(st.get("likeCount")),
                "comments": _entier(st.get("commentCount")),
            }
    return out


def normalise_video(item: dict) -> dict:
    """Une entrée `videos.list` → les colonnes de videos_ext et son instantané."""
    sn = item.get("snippet", {})
    cd = item.get("contentDetails", {})
    st = item.get("statistics", {})
    vignettes = sn.get("thumbnails", {})
    meilleure = None
    for cle in ("maxres", "standard", "high", "medium", "default"):
        if cle in vignettes:
            meilleure = vignettes[cle].get("url")
            break
    return {
        "video_id": item["id"],
        "channel_id": sn.get("channelId"),
        "published_at": sn.get("publishedAt"),
        "title": sn.get("title"),
        "description_head": (sn.get("description") or "")[:200],
        "duration_s": iso_duration_seconds(cd.get("duration", "")),
        "tags_json": sn.get("tags"),
        "category_id": sn.get("categoryId"),
        "thumbnail_url": meilleure,
        "views": _entier(st.get("viewCount")),
        "likes": _entier(st.get("likeCount")),
        "comments": _entier(st.get("commentCount")),
    }


def normalise_channel(item: dict) -> dict:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    rel = item.get("contentDetails", {}).get("relatedPlaylists", {})
    return {
        "channel_id": item["id"],
        "title": sn.get("title"),
        "handle": sn.get("customUrl"),
        "uploads_playlist_id": rel.get("uploads"),
        # `subscriberCount` est arrondi à trois chiffres significatifs par YouTube.
        "subscribers": _entier(st.get("subscriberCount")),
        "views": _entier(st.get("viewCount")),
        "video_count": _entier(st.get("videoCount")),
    }


def chemin_log() -> Path:
    return racine_projet() / "workspace" / "logs" / "collect.log"
