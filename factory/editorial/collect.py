"""Collecte quotidienne de l'entrepôt concurrentiel (étape 18).

Trois opérations, une base : `watch` (qui l'on suit), `collect` (les instantanés du
jour), `purge` (la conservation à 30 jours). Aucun appel à `search.list`, aucun
téléchargement de vidéo : voir docs/CONFORMITE.md § 9.

La collecte est **reprenable** : une chaîne déjà traitée le jour même est sautée,
sauf `--force`. Elle s'arrête **proprement** au plafond d'unités, en enregistrant
ce qui a été fait.
"""

from __future__ import annotations

import csv
import os
import random
import sqlite3
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from factory.core.paths import racine_projet
from factory.editorial import yt_api
from factory.editorial.yt_api import Compteur, QuotaAtteint

PLAFOND_DEFAUT = 6000
JOURS_FRAIS = 90  # au-delà, une vidéo n'est plus rafraîchie tous les jours
PART_ANCIENNES = 10  # 1 vidéo ancienne sur 10 par jour : l'échantillon tourne
BACKFILL_VIDEOS = 200
BACKFILL_PAGES = 4  # 4 × 50 = 200
PAGES_QUOTIDIENNES = 1  # une page suffit à voir les nouveautés du jour
JOURS_CONSERVATION = 30  # Developer Policies III.E.4.d — plafond contractuel

LABEL_AGENT = "com.bms.factory.collect"
LABEL_SONDE = "com.bms.factory.acces"


# --------------------------------------------------------------------- journal


def journalise(message: str, *, echo=None) -> None:
    """Une ligne horodatée dans workspace/logs/collect.log."""
    chemin = yt_api.chemin_log()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ligne = f"{datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')} {message}"
    with chemin.open("a", encoding="utf-8") as f:
        f.write(ligne + "\n")
    if echo is not None:
        echo(message)


# ------------------------------------------------------------------ surveillance


def importer_registre(conn: sqlite3.Connection, chemin: Path | None = None) -> tuple[int, list[str]]:
    """Importe registre/chaines.csv dans channels_watch. Idempotent.

    Retourne (ajoutées, non résolues). Une ligne sans UC… dans son URL ne porte pas
    d'identifiant de chaîne : elle est signalée, jamais devinée.
    """
    csv_path = chemin or racine_projet() / "registre" / "chaines.csv"
    if not csv_path.exists():
        return 0, []
    ajoutees, non_resolues = 0, []
    maintenant = yt_api.now_iso()
    for ligne in csv.DictReader(csv_path.open(encoding="utf-8")):
        cid = yt_api.channel_id_of(ligne.get("handle_ou_url", ""))
        if not cid:
            non_resolues.append(ligne.get("nom", "?"))
            continue
        cur = conn.execute(
            "INSERT INTO channels_watch"
            " (channel_id, handle, title, niche, lang, source, active, added_at)"
            " VALUES (?, ?, ?, ?, ?, 'registre', 1, ?)"
            " ON CONFLICT(channel_id) DO NOTHING",
            (
                cid,
                ligne.get("handle_ou_url"),
                ligne.get("nom"),
                ligne.get("niche"),
                ligne.get("langue"),
                maintenant,
            ),
        )
        ajoutees += cur.rowcount if cur.rowcount > 0 else 0
    return ajoutees, non_resolues


def amorcer(conn: sqlite3.Connection, echo=None) -> None:
    """Importe le registre au premier lancement, quand channels_watch est vide."""
    (n,) = conn.execute("SELECT COUNT(*) FROM channels_watch").fetchone()
    if n:
        return
    ajoutees, non_resolues = importer_registre(conn)
    journalise(
        f"registre importé : {ajoutees} chaînes, {len(non_resolues)} non résolues", echo=echo
    )
    for nom in non_resolues:
        journalise(f"  NON RÉSOLUE (pas d'identifiant UC dans l'URL) : {nom}", echo=echo)


def watch_add(
    conn: sqlite3.Connection, url_ou_id: str, *, niche: str | None, lang: str | None
) -> str:
    cid = yt_api.channel_id_of(url_ou_id) or (
        url_ou_id if url_ou_id.startswith("UC") and len(url_ou_id) == 24 else None
    )
    if not cid:
        raise ValueError(
            f"identifiant de chaîne introuvable dans « {url_ou_id} » : "
            "il faut une URL /channel/UC… ou l'identifiant UC… lui-même "
            "(un @handle ne le porte pas)"
        )
    conn.execute(
        "INSERT INTO channels_watch (channel_id, handle, niche, lang, source, active, added_at)"
        " VALUES (?, ?, ?, ?, 'ajout', 1, ?)"
        " ON CONFLICT(channel_id) DO UPDATE SET active = 1,"
        " niche = COALESCE(excluded.niche, niche), lang = COALESCE(excluded.lang, lang)",
        (cid, url_ou_id, niche, lang, yt_api.now_iso()),
    )
    return cid


def watch_remove(conn: sqlite3.Connection, url_ou_id: str) -> str:
    """Désactive la chaîne. Les données déjà collectées suivent la purge ordinaire."""
    cid = yt_api.channel_id_of(url_ou_id) or url_ou_id
    cur = conn.execute("UPDATE channels_watch SET active = 0 WHERE channel_id = ?", (cid,))
    if not cur.rowcount:
        raise ValueError(f"chaîne inconnue : {cid}")
    return cid


def watch_list(conn: sqlite3.Connection, *, toutes: bool = False) -> list[sqlite3.Row]:
    filtre = "" if toutes else " WHERE active = 1"
    return list(
        conn.execute(
            "SELECT cw.*,"
            " (SELECT COUNT(*) FROM videos_ext v WHERE v.channel_id = cw.channel_id) AS videos"
            f" FROM channels_watch cw{filtre} ORDER BY niche, title"
        )
    )


# ---------------------------------------------------------------------- collecte


@dataclass
class Rapport:
    date: str
    mode: str
    debut: str
    fin: str = ""
    chaines_total: int = 0
    chaines_faites: int = 0
    chaines_sautees: int = 0
    videos_nouvelles: int = 0
    instantanes: int = 0
    unites: int = 0
    unites_batch: int = 0
    appels: dict[str, int] = field(default_factory=dict)
    erreurs: list[str] = field(default_factory=list)
    arret_quota: bool = False
    methode_stats: str = ""


def _echantillon_du_jour(video_ids: list[str], jour: int) -> list[str]:
    """10 % des anciennes, par rotation déterministe : chaque vidéo revient tous les 10 jours.

    `crc32` plutôt qu'un tirage : l'échantillon doit être reproductible d'un jour
    sur l'autre pour que la rotation soit complète, pas aléatoire à chaque fois.
    """
    reste = jour % PART_ANCIENNES
    return [v for v in video_ids if zlib.crc32(v.encode()) % PART_ANCIENNES == reste]


def _enregistre_video(conn: sqlite3.Connection, v: dict, maintenant: str) -> bool:
    """Insère ou rafraîchit videos_ext. Retourne True si la vidéo est nouvelle."""
    import json

    tags = json.dumps(v["tags_json"], ensure_ascii=False) if v.get("tags_json") else None
    cur = conn.execute(
        "INSERT INTO videos_ext (video_id, channel_id, published_at, title, description_head,"
        " duration_s, tags_json, category_id, thumbnail_url, first_seen_at, last_seen_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(video_id) DO UPDATE SET"
        "  title = excluded.title, description_head = excluded.description_head,"
        "  duration_s = excluded.duration_s, tags_json = excluded.tags_json,"
        "  category_id = excluded.category_id, thumbnail_url = excluded.thumbnail_url,"
        "  last_seen_at = excluded.last_seen_at",
        (
            v["video_id"],
            v["channel_id"],
            v["published_at"],
            v["title"],
            v["description_head"],
            v["duration_s"],
            tags,
            v["category_id"],
            v["thumbnail_url"],
            maintenant,
            maintenant,
        ),
    )
    # rowcount vaut 1 sur INSERT comme sur UPDATE : on tranche sur first_seen_at.
    del cur
    (premier,) = conn.execute(
        "SELECT first_seen_at FROM videos_ext WHERE video_id = ?", (v["video_id"],)
    ).fetchone()
    return premier == maintenant


def _enregistre_instantane(
    conn: sqlite3.Connection, video_id: str, jour: str, stats: dict, maintenant: str
) -> None:
    """Un instantané par vidéo et par jour. `--force` rafraîchit celui du jour."""
    conn.execute(
        "INSERT INTO video_snapshots (video_id, snapshot_date, views, likes, comments, fetched_at)"
        " VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(video_id, snapshot_date) DO UPDATE SET"
        "  views = excluded.views, likes = excluded.likes,"
        "  comments = excluded.comments, fetched_at = excluded.fetched_at",
        (video_id, jour, stats.get("views"), stats.get("likes"), stats.get("comments"), maintenant),
    )


def collecter(
    conn: sqlite3.Connection,
    *,
    force: bool = False,
    max_units: int = PLAFOND_DEFAUT,
    client=None,
    echo=None,
    racine: Path | None = None,
) -> Rapport:
    """Une passe de collecte. Voir le module pour le contrat."""
    jour = yt_api.aujourdhui()
    maintenant = yt_api.now_iso()
    rapport = Rapport(date=jour, mode="force" if force else "normal", debut=maintenant)
    compteur = Compteur(max_units)

    amorcer(conn, echo=echo)
    yt = client or yt_api.construire_client()
    batch = yt_api.batch_disponible(yt)
    rapport.methode_stats = "videos.batchGetStats" if batch else "videos.list"
    journalise(
        f"collecte {jour} ({rapport.mode}) · plafond {max_units} unités · "
        f"statistiques par {rapport.methode_stats}",
        echo=echo,
    )

    chaines = list(
        conn.execute(
            "SELECT channel_id, title, uploads_playlist_id, backfilled, last_collect_date"
            " FROM channels_watch WHERE active = 1 ORDER BY COALESCE(last_collect_date, ''), channel_id"
        )
    )
    rapport.chaines_total = len(chaines)
    todo = [c for c in chaines if force or c["last_collect_date"] != jour]
    rapport.chaines_sautees = len(chaines) - len(todo)
    if rapport.chaines_sautees:
        journalise(f"{rapport.chaines_sautees} chaînes déjà collectées aujourd'hui, sautées", echo=echo)

    try:
        # 1. channels.list par lots de 50 : 2 unités pour 74 chaînes, pas 74.
        fiches = yt_api.fetch_channels(yt, compteur, [c["channel_id"] for c in todo])
        for cid, item in fiches.items():
            ch = yt_api.normalise_channel(item)
            conn.execute(
                "UPDATE channels_watch SET title = COALESCE(?, title),"
                " handle = COALESCE(?, handle), uploads_playlist_id = ? WHERE channel_id = ?",
                (ch["title"], ch["handle"], ch["uploads_playlist_id"], cid),
            )
            conn.execute(
                "INSERT INTO channel_snapshots"
                " (channel_id, snapshot_date, subscribers, views, video_count, fetched_at)"
                " VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(channel_id, snapshot_date) DO UPDATE SET"
                "  subscribers = excluded.subscribers, views = excluded.views,"
                "  video_count = excluded.video_count, fetched_at = excluded.fetched_at",
                (cid, jour, ch["subscribers"], ch["views"], ch["video_count"], maintenant),
            )

        for chaine in todo:
            cid = chaine["channel_id"]
            fiche = fiches.get(cid)
            if fiche is None:
                rapport.erreurs.append(f"{cid} : absente de la réponse channels.list")
                journalise(f"[{cid}] ABSENTE de channels.list (supprimée ou privée ?)", echo=echo)
                continue
            uploads = yt_api.normalise_channel(fiche)["uploads_playlist_id"]
            if not uploads:
                rapport.erreurs.append(f"{cid} : pas de playlist d'uploads")
                continue
            try:
                n_new, n_snap = _collecte_chaine(
                    conn, yt, compteur, chaine, uploads, jour, maintenant, batch
                )
            except QuotaAtteint:
                raise
            except Exception as exc:  # noqa: BLE001 — une chaîne en échec n'arrête pas la passe
                rapport.erreurs.append(f"{cid} : {type(exc).__name__}: {exc}")
                journalise(f"[{cid}] ERREUR {type(exc).__name__}: {exc}", echo=echo)
                continue
            rapport.videos_nouvelles += n_new
            rapport.instantanes += n_snap
            rapport.chaines_faites += 1
            conn.execute(
                "UPDATE channels_watch SET last_collect_date = ?, backfilled = 1"
                " WHERE channel_id = ?",
                (jour, cid),
            )
            journalise(
                f"[{chaine['title'] or cid}] {n_new} nouvelles · {n_snap} instantanés"
                f" · unités {compteur.unites}+{compteur.unites_batch}",
                echo=echo,
            )
    except QuotaAtteint as exc:
        rapport.arret_quota = True
        rapport.erreurs.append(f"arrêt au plafond : {exc}")
        journalise(f"ARRÊT PROPRE — plafond d'unités atteint : {exc}", echo=echo)

    rapport.unites = compteur.unites
    rapport.unites_batch = compteur.unites_batch
    rapport.appels = dict(compteur.appels)
    rapport.fin = yt_api.now_iso()

    conn.execute(
        "INSERT INTO collect_runs (date, started_at, finished_at, mode, units_used,"
        " channels_done, videos_new, snapshots_new, errors, note)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            rapport.date,
            rapport.debut,
            rapport.fin,
            rapport.mode,
            compteur.total,
            rapport.chaines_faites,
            rapport.videos_nouvelles,
            rapport.instantanes,
            len(rapport.erreurs),
            f"stats={rapport.methode_stats}"
            + (f" principal={compteur.unites} batch={compteur.unites_batch}")
            + (" ARRÊT_QUOTA" if rapport.arret_quota else ""),
        ),
    )
    ecrire_rapport(rapport, racine)
    journalise(
        f"FIN {jour} · {rapport.chaines_faites}/{rapport.chaines_total} chaînes"
        f" · {rapport.videos_nouvelles} vidéos neuves · {rapport.instantanes} instantanés"
        f" · {compteur.total} unités ({compteur.unites} principal + {compteur.unites_batch} batch)"
        f" · {len(rapport.erreurs)} erreurs",
        echo=echo,
    )
    return rapport


def _collecte_chaine(
    conn: sqlite3.Connection,
    yt,
    compteur: Compteur,
    chaine: sqlite3.Row,
    uploads: str,
    jour: str,
    maintenant: str,
    batch: bool,
) -> tuple[int, int]:
    """Une chaîne : nouveautés, métadonnées des nouvelles, statistiques des suivies."""
    premier_passage = not chaine["backfilled"]
    ids, _ = yt_api.fetch_upload_ids(
        yt,
        compteur,
        uploads,
        max_videos=BACKFILL_VIDEOS if premier_passage else yt_api.PAGE_SIZE,
        pages_max=BACKFILL_PAGES if premier_passage else PAGES_QUOTIDIENNES,
    )

    connues = {
        r["video_id"]
        for r in conn.execute(
            "SELECT video_id FROM videos_ext WHERE channel_id = ?", (chaine["channel_id"],)
        )
    }
    nouvelles = [v for v in ids if v not in connues]

    n_new = n_snap = 0
    # Les nouvelles vidéos passent par videos.list : on a besoin des métadonnées
    # complètes (titre, description, durée, tags), pas seulement des compteurs.
    for item in yt_api.fetch_videos(yt, compteur, nouvelles):
        v = yt_api.normalise_video(item)
        if _enregistre_video(conn, v, maintenant):
            n_new += 1
        _enregistre_instantane(conn, v["video_id"], jour, v, maintenant)
        n_snap += 1

    # Les vidéos déjà connues : compteurs seulement. Toutes celles de moins de
    # 90 jours, plus un dixième tournant des plus anciennes.
    limite = (datetime.now(UTC) - timedelta(days=JOURS_FRAIS)).isoformat(timespec="seconds")
    fraiches = [
        r["video_id"]
        for r in conn.execute(
            "SELECT video_id FROM videos_ext WHERE channel_id = ? AND published_at >= ?",
            (chaine["channel_id"], limite),
        )
    ]
    anciennes = [
        r["video_id"]
        for r in conn.execute(
            "SELECT video_id FROM videos_ext"
            " WHERE channel_id = ? AND (published_at IS NULL OR published_at < ?)",
            (chaine["channel_id"], limite),
        )
    ]
    jour_annee = datetime.now(UTC).timetuple().tm_yday
    a_rafraichir = [
        v for v in fraiches + _echantillon_du_jour(anciennes, jour_annee) if v not in set(nouvelles)
    ]
    if a_rafraichir:
        stats = yt_api.fetch_stats(yt, compteur, a_rafraichir, batch=batch)
        for vid, st in stats.items():
            _enregistre_instantane(conn, vid, jour, st, maintenant)
            conn.execute(
                "UPDATE videos_ext SET last_seen_at = ? WHERE video_id = ?", (maintenant, vid)
            )
            n_snap += 1
    return n_new, n_snap


def ecrire_rapport(rapport: Rapport, racine: Path | None = None) -> Path:
    """Écrit `reports/collect_<date>.md`. **`racine` n'est pas un confort : c'est une garde.**

    Sans elle, chaque passage de `tests/test_etape18.py` réécrivait le vrai rapport de collecte
    du jour avec les chiffres du faux client — constaté deux fois, le fichier passant de la
    vraie collecte de 07:52 à un test de 13:26, sans qu'aucune ligne n'entre en base. Un test
    ne doit pas pouvoir toucher un livrable. Trouvé à l'étape 19, corrigé à l'étape 21.
    """
    dossier = (racine or racine_projet()) / "reports"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"collect_{rapport.date}.md"
    appels = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(rapport.appels.items())) or "| — | 0 |"
    erreurs = "\n".join(f"- {e}" for e in rapport.erreurs) or "- aucune"
    chemin.write_text(
        f"""# Collecte concurrentielle — {rapport.date}

Mode : **{rapport.mode}** · début {rapport.debut} · fin {rapport.fin}
Statistiques récupérées par **{rapport.methode_stats}**.

| Mesure | Valeur |
|---|---|
| Chaînes suivies (actives) | {rapport.chaines_total} |
| Chaînes collectées | {rapport.chaines_faites} |
| Chaînes sautées (déjà faites ce jour) | {rapport.chaines_sautees} |
| Vidéos nouvelles | {rapport.videos_nouvelles} |
| Instantanés écrits | {rapport.instantanes} |
| Unités — compartiment principal | {rapport.unites} |
| Unités — compartiment `batchGetStats` | {rapport.unites_batch} |
| Arrêt au plafond | {"oui" if rapport.arret_quota else "non"} |

## Appels

| Méthode | Unités |
|---|---|
{appels}

## Erreurs

{erreurs}
""",
        encoding="utf-8",
    )
    return chemin


# -------------------------------------------------------------------------- top


def parse_fenetre(fenetre: str) -> int:
    """« 30d » → 30. Refuse plutôt que de deviner."""
    texte = (fenetre or "").strip().lower()
    if texte.endswith("d"):
        texte = texte[:-1]
    if not texte.isdigit() or int(texte) <= 0:
        raise ValueError(f"fenêtre invalide : « {fenetre} » (attendu par exemple 7d, 30d, 90d)")
    return int(texte)


def top(
    conn: sqlite3.Connection,
    *,
    niche: str | None = None,
    fenetre: str = "30d",
    lang: str | None = None,
    limite: int = 20,
) -> list[sqlite3.Row]:
    jours = parse_fenetre(fenetre)
    clauses = ["age_days <= ?", "velocity IS NOT NULL"]
    params: list = [jours]
    if niche:
        clauses.append("niche = ?")
        params.append(niche)
    if lang:
        clauses.append("lang = ?")
        params.append(lang)
    params.append(limite)
    return list(
        conn.execute(
            f"SELECT * FROM v_video_velocity WHERE {' AND '.join(clauses)}"
            " ORDER BY velocity DESC LIMIT ?",
            params,
        )
    )


# ------------------------------------------------------------------------ purge


@dataclass
class Purge:
    instantanes_video: int = 0
    instantanes_chaine: int = 0
    videos: int = 0
    metriques_consolidees: int = 0
    metriques_supprimees: int = 0
    limite: str = ""


def consolider_metriques(conn: sqlite3.Connection) -> int:
    """Fige les mesures dérivées avant que les instantanés bruts ne soient purgés.

    ATTENTION — Developer Policies III.E.4.h interdit d'« access or use API Data to
    create new or derived data or metrics ». Cette table est donc **contestée** :
    voir docs/CONFORMITE.md § 9. `purge --strict` la vide et s'en passe.
    """
    maintenant = yt_api.now_iso()
    lignes = conn.execute(
        "SELECT video_id, channel_id, published_at, views_d1, views_d7, views_d30,"
        " velocity_7d, velocity_life, ratio FROM v_video_velocity"
    ).fetchall()
    # Les comptes d'instantanés en une seule requête : un COUNT par vidéo ferait
    # 11 000 allers-retours sur l'entrepôt réel.
    comptes = {
        r["video_id"]: r["n"]
        for r in conn.execute(
            "SELECT video_id, COUNT(*) AS n FROM video_snapshots GROUP BY video_id"
        )
    }
    n = 0
    for r in lignes:
        compte = comptes.get(r["video_id"], 0)
        conn.execute(
            "INSERT INTO video_metrics (video_id, channel_id, published_at, views_d1, views_d7,"
            " views_d30, velocity_7d, velocity_life, ratio_niche, n_snapshots, computed_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(video_id) DO UPDATE SET"
            "  views_d1 = COALESCE(excluded.views_d1, video_metrics.views_d1),"
            "  views_d7 = COALESCE(excluded.views_d7, video_metrics.views_d7),"
            "  views_d30 = COALESCE(excluded.views_d30, video_metrics.views_d30),"
            "  velocity_7d = COALESCE(excluded.velocity_7d, video_metrics.velocity_7d),"
            "  velocity_life = excluded.velocity_life,"
            "  ratio_niche = COALESCE(excluded.ratio_niche, video_metrics.ratio_niche),"
            "  n_snapshots = excluded.n_snapshots, computed_at = excluded.computed_at",
            (
                r["video_id"],
                r["channel_id"],
                r["published_at"],
                r["views_d1"],
                r["views_d7"],
                r["views_d30"],
                r["velocity_7d"],
                r["velocity_life"],
                r["ratio"],
                compte,
                maintenant,
            ),
        )
        n += 1
    return n


def purger(
    conn: sqlite3.Connection, *, jours: int = JOURS_CONSERVATION, strict: bool = False,
    simulation: bool = False,
) -> Purge:
    """Applique la conservation à 30 jours (Developer Policies III.E.4.d).

    `strict` : supprime aussi les mesures dérivées (video_metrics), lecture la plus
    prudente de III.E.4.h. Sans `strict`, elles sont consolidées puis conservées,
    conformément à la doctrine écrite dans ARCHITECTURE.md § 9 — que ce texte
    contredit et que Thomas doit trancher (SUIVI.md § 1).
    """
    limite_date = (datetime.now(UTC) - timedelta(days=jours)).strftime("%Y-%m-%d")
    limite_ts = (datetime.now(UTC) - timedelta(days=jours)).isoformat(timespec="seconds")
    p = Purge(limite=limite_date)

    if not strict and not simulation:
        p.metriques_consolidees = consolider_metriques(conn)

    (p.instantanes_video,) = conn.execute(
        "SELECT COUNT(*) FROM video_snapshots WHERE snapshot_date < ?", (limite_date,)
    ).fetchone()
    (p.instantanes_chaine,) = conn.execute(
        "SELECT COUNT(*) FROM channel_snapshots WHERE snapshot_date < ?", (limite_date,)
    ).fetchone()
    # Une vidéo dont last_seen_at ne bouge plus a disparu de l'API (supprimée,
    # privée, chaîne désactivée) : elle ne peut plus être rafraîchie, donc elle part.
    (p.videos,) = conn.execute(
        "SELECT COUNT(*) FROM videos_ext WHERE last_seen_at < ?", (limite_ts,)
    ).fetchone()
    if strict:
        (p.metriques_supprimees,) = conn.execute("SELECT COUNT(*) FROM video_metrics").fetchone()

    if simulation:
        return p

    conn.execute("DELETE FROM video_snapshots WHERE snapshot_date < ?", (limite_date,))
    conn.execute("DELETE FROM channel_snapshots WHERE snapshot_date < ?", (limite_date,))
    conn.execute(
        "DELETE FROM video_snapshots WHERE video_id IN"
        " (SELECT video_id FROM videos_ext WHERE last_seen_at < ?)",
        (limite_ts,),
    )
    conn.execute("DELETE FROM videos_ext WHERE last_seen_at < ?", (limite_ts,))
    if strict:
        conn.execute("DELETE FROM video_metrics")
    journalise(
        f"purge à {jours} jours (limite {limite_date}) : {p.instantanes_video} instantanés vidéo,"
        f" {p.instantanes_chaine} instantanés chaîne, {p.videos} vidéos,"
        f" {p.metriques_consolidees} mesures consolidées,"
        f" {p.metriques_supprimees} mesures supprimées"
    )
    return p


# ------------------------------------------------------------------- planification


def chemin_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL_AGENT}.plist"


def _heure_du_plist() -> tuple[int, int] | None:
    """(heure, minute) du plist déjà installé, s'il existe et se laisse lire."""
    chemin = chemin_plist()
    if not chemin.exists():
        return None
    try:
        import plistlib

        with chemin.open("rb") as f:
            intervalle = plistlib.load(f).get("StartCalendarInterval", {})
        return int(intervalle["Hour"]), int(intervalle["Minute"])
    except Exception:  # noqa: BLE001 — un plist illisible se remplace, il ne bloque pas
        return None


def ecrire_plist(*, heure: int | None = None, minute: int | None = None) -> tuple[Path, int, int]:
    """Écrit le plist launchd. Minute tirée une fois, à l'installation, puis figée.

    Le tirage évite que toutes les installations d'un même système tapent l'API à
    la même seconde ; le figer rend l'heure de passage prévisible pour Thomas.
    """
    racine = racine_projet()
    binaire = racine / ".venv" / "bin" / "factory"
    if not binaire.exists():
        raise FileNotFoundError(f"exécutable introuvable : {binaire} (lancer `uv sync`)")
    # L'heure est tirée une fois, puis **relue** du plist existant : réinstaller
    # pour revérifier l'accès disque ne doit pas déplacer le passage nocturne.
    ancienne = _heure_du_plist()
    if heure is None:
        heure = ancienne[0] if ancienne else random.choice([3, 4])
    if minute is None:
        minute = ancienne[1] if ancienne else random.randint(0, 59)
    log = racine / "workspace" / "logs" / "collect_launchd.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL_AGENT}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{binaire}</string>
        <string>editorial</string>
        <string>collect</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{racine}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FACTORY_ROOT</key>
        <string>{racine}</string>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{heure}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{log}</string>
    <key>StandardErrorPath</key>
    <string>{log}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
"""
    chemin = chemin_plist()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(plist, encoding="utf-8")
    return chemin, heure, minute


def binaire_python() -> Path:
    """Le binaire réellement exécuté par launchd — c'est lui qui porte l'autorisation TCC."""
    import sys

    return Path(sys.executable).resolve()


def verifier_acces_launchd(attente_s: float = 30.0) -> tuple[bool | None, str]:
    """Une tâche launchd peut-elle seulement lire le projet ?

    macOS protège `~/Documents` par TCC. Un agent launchd n'hérite d'aucune
    autorisation : il reçoit « Operation not permitted » sur tout le dépôt, et un
    interpréteur Python s'y **bloque** avant même d'avoir démarré (mesuré le
    20/09/2026 : processus suspendu dans `getpath_readlines`). Sans cette sonde,
    la collecte échouerait en silence chaque nuit.

    Retourne (True | False | None, message) ; None = sonde non concluante.
    """
    import shutil
    import subprocess
    import tempfile
    import time

    temoin = racine_projet() / "pyproject.toml"
    dossier = Path(tempfile.mkdtemp(prefix="bms-acces-"))
    script, log, plist = dossier / "s.sh", dossier / "s.log", dossier / "s.plist"
    script.write_text(
        f'#!/bin/sh\ncat "{temoin}" >/dev/null 2>"{dossier}/err"; echo "$?" > "{log}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
        ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        f'<plist version="1.0"><dict>'
        f"<key>Label</key><string>{LABEL_SONDE}</string>"
        f"<key>ProgramArguments</key><array><string>/bin/sh</string>"
        f"<string>{script}</string></array>"
        f"<key>RunAtLoad</key><true/></dict></plist>\n",
        encoding="utf-8",
    )
    cible = f"gui/{os.getuid()}"
    try:
        subprocess.run(["launchctl", "bootout", f"{cible}/{LABEL_SONDE}"], capture_output=True)
        r = subprocess.run(
            ["launchctl", "bootstrap", cible, str(plist)], capture_output=True, text=True
        )
        if r.returncode != 0:
            return None, f"sonde non chargée : {(r.stderr or r.stdout).strip()}"
        fin = time.monotonic() + attente_s
        while time.monotonic() < fin:
            if log.exists() and log.read_text().strip():
                break
            time.sleep(0.5)
        else:
            return None, "sonde sans réponse (délai dépassé)"
        code = log.read_text().strip()
        erreur = (dossier / "err").read_text(encoding="utf-8").strip() if (dossier / "err").exists() else ""
        if code == "0":
            return True, "une tâche launchd lit bien le projet"
        return False, erreur or f"lecture refusée (code {code})"
    finally:
        subprocess.run(["launchctl", "bootout", f"{cible}/{LABEL_SONDE}"], capture_output=True)
        shutil.rmtree(dossier, ignore_errors=True)


def charger_agent() -> tuple[bool, str]:
    """(Re)charge la tâche dans launchd. Retourne (succès, message)."""
    import subprocess

    chemin = chemin_plist()
    cible = f"gui/{os.getuid()}"
    # bootout d'abord : bootstrap refuse une étiquette déjà chargée.
    subprocess.run(
        ["launchctl", "bootout", f"{cible}/{LABEL_AGENT}"], capture_output=True, text=True
    )
    r = subprocess.run(
        ["launchctl", "bootstrap", cible, str(chemin)], capture_output=True, text=True
    )
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()
    return True, f"{LABEL_AGENT} chargée"
