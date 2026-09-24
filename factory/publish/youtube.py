"""`factory publish upload|release|status|manual-list` — publication industrialisée.

`upload_min.py` (étape 14) reste la **couche d'appel** : corps de requête, contrôles
préalables, reprise sur 404 de propagation, lecture de `videos.list`. Ce module est la
**couche d'industrialisation** posée dessus : quota compté avant chaque appel, playlist,
programmation, écriture en base, `publish.json` au contrat de `INTERFACES.md`, manifeste.
Il n'y a donc qu'un seul corps de `videos.insert` dans le projet, et il est au même endroit
qu'à l'étape 14.

Quatre points méritent d'être lus avant d'y toucher.

- **`publishAt` n'existe que sur une vidéo privée et jamais publiée.** « The value can be set
  only if the privacy status of the video is private » (developers.google.com/youtube/v3/docs/
  videos). Programmer une vidéo publique est silencieusement sans effet : on poserait une date
  et rien ne se passerait. D'où le refus explicite plutôt qu'un appel qui « réussit ».
- **Tant que `audit_passed` est faux, `publishAt` n'est même pas envoyé.** Un projet non
  audité voit tous ses uploads forcés en privé ; une date de programmation posée sur cette
  vidéo ne serait pas honorée et ferait croire le tableau de bord à une publication à venir.
  La date est alors conservée dans `publications.publish_at` comme **intention**, et c'est
  elle que `factory publish manual-list` donne à l'opérateur pour Studio.
- **`videos.update` écrase la partie entière qu'il vise.** « This method will override the
  existing values for all of the mutable properties » : un `update` de `part=status` qui
  omettrait `containsSyntheticMedia` **retirerait le label**. D'où la relecture par
  `videos.list` avant chaque `release`, et le renvoi de l'objet `status` complet.
- **Le quota est débité avant l'appel.** Google facture la tentative ; un `captions.insert`
  refusé coûte ses 400 unités. Voir `quota.py`.
"""

from __future__ import annotations

import json
import random
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from factory.core import config as config_module
from factory.core import db as db_module
from factory.core.models import Channel
from factory.core.paths import RunPaths, racine_projet
from factory.publish import oauth, quota
from factory.publish import upload_min as base

#: Statuts de `publications.status`, dans l'ordre de la vie d'une vidéo.
STATUTS = ("published_private", "scheduled", "public", "failed")

#: Lien d'édition dans Studio, celui que l'opérateur ouvre pour programmer à la main.
LIEN_STUDIO = "https://studio.youtube.com/video/{id}/edit"


class ErreurPublication(RuntimeError):
    """Run inutilisable, configuration incohérente, quota épuisé ou refus de l'API."""


@dataclass
class Resultat:
    """Ce que la session a réellement fait — pas ce qu'elle voulait faire."""

    video_id: str
    channel: str
    youtube_video_id: str | None = None
    url: str | None = None
    statut: str = "failed"
    publish_at: str | None = None
    thumbnail_set: bool = False
    captions_set: bool = False
    playlist_added: bool = False
    caption_id: str | None = None
    playlist_item_id: str | None = None
    etapes: list[base.Etape] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    demarre_a: str = ""
    termine_a: str = ""

    @property
    def unites(self) -> int:
        """Unités du compartiment des 10 000 — l'upload est ailleurs (voir `quota.py`)."""
        return sum(e.unites for e in self.etapes)


def maintenant() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------------------
# Appels, chacun précédé de sa comptabilité
# --------------------------------------------------------------------------------------


def _reessayer_backoff(appel: Callable[[], Any], *, tentatives: int, attente_s: float,
                       journal: Callable[[str], None]) -> Any:
    """Backoff exponentiel sur les erreurs transitoires, à la manière de l'exemple de Google.

    Transitoires : 500, 502, 503, 504 (panne passagère), 409 (conflit), et **404 juste après
    l'insert**, le temps que la vidéo se propage aux autres points d'entrée. Un 403 ou un 400
    ne sont pas transitoires : les rejouer dépenserait du quota pour rien.
    """
    from googleapiclient.errors import HttpError

    for essai in range(tentatives):
        try:
            return appel()
        except HttpError as erreur:
            statut = getattr(erreur.resp, "status", None)
            if statut not in (404, 409, 500, 502, 503, 504) or essai == tentatives - 1:
                raise
            pause = attente_s * (2**essai) + random.random()
            journal(f"erreur {statut} — nouvelle tentative dans {pause:.0f} s "
                    f"({essai + 1}/{tentatives - 1})")
            time.sleep(pause)
    raise RuntimeError("inatteignable")


def _corps_insert(meta: dict[str, Any], channel: Channel,
                  publish_at: str | None) -> dict[str, Any]:
    """Le corps de l'étape 14, complété de la programmation quand elle est permise."""
    corps = base._corps_insert(meta, channel)
    if publish_at and channel.youtube.audit_passed:
        # `privacyStatus` reste `private` : c'est la condition même de `publishAt`.
        corps["status"]["publishAt"] = publish_at
    return corps


# --------------------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------------------


def televerser(
    video_id: str,
    channel_id: str,
    *,
    publish_at: str | None = None,
    racine: Path | None = None,
    conn: sqlite3.Connection | None = None,
    journal: Callable[[str], None] | None = None,
    dry_run: bool = False,
    service: Any = None,
) -> Resultat:
    """Publie un run : insert privé, miniature, sous-titres, playlist, vérification.

    `service` n'existe que pour les tests : un double d'API y est injecté. En production il
    vaut `None` et le service est construit depuis le jeton de la chaîne.
    """
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    dire = journal or (lambda _m: None)
    racine = racine or racine_projet()
    cfg = config_module.charger(racine)
    pub_cfg = cfg.orchestrator.publication
    plafonds = quota.Plafonds(pub_cfg.uploads_max_jour, pub_cfg.unites_max_jour,
                              pub_cfg.gcp_project)

    channel = cfg.channels.get(channel_id)
    if channel is None:
        connues = ", ".join(sorted(cfg.channels)) or "aucune"
        raise ErreurPublication(f"chaîne inconnue : {channel_id} (connues : {connues})")

    chemins = RunPaths.depuis_video_id(video_id, racine)
    meta = base._lire_metadata(chemins)
    resultat = Resultat(video_id=video_id, channel=channel_id, demarre_a=maintenant())
    resultat.avertissements.extend(base._controles_prealables(chemins, meta, channel))

    # --- programmation : permise, ou seulement enregistrée comme intention ---------------
    if publish_at:
        publish_at = _normaliser_date(publish_at)
        if channel.youtube.audit_passed:
            resultat.publish_at = publish_at
        else:
            resultat.publish_at = publish_at
            resultat.avertissements.append(
                f"audit_passed est faux : publishAt={publish_at} n'est pas envoyé à l'API "
                "(YouTube ne l'honorerait pas sur un projet non audité). La date est "
                "conservée comme intention et ressort dans `factory publish manual-list`."
            )

    fermer = conn is None
    conn = conn or db_module.ouvrir()

    try:
        # --- refus avant toute dépense --------------------------------------------------
        etat = quota.verifier(conn, "videos.insert", plafonds=plafonds)
        besoin = quota.cout_publication_complete()
        if etat.unites_restantes < besoin["units"]:
            raise quota.QuotaDepasse(
                f"publication refusée : une publication complète coûte {besoin['units']} "
                f"unités (miniature 50 + sous-titres 400 + playlist 50 + vérification 1) et "
                f"il en reste {etat.unites_restantes} sur {plafonds.units}."
            )

        if dry_run:
            taille = chemins.final.stat().st_size / 1e6
            resultat.etapes.append(base.Etape(
                "dry-run", True,
                f"corps prêt, {taille:.1f} Mo, {quota.publications_possibles(etat)} "
                f"publication(s) possible(s) aujourd'hui", 0))
            resultat.statut = "published_private"
            resultat.termine_a = maintenant()
            return resultat

        yt = service or oauth.service(channel_id, racine=racine)

        # --- videos.insert, résumable ---------------------------------------------------
        corps = _corps_insert(meta, channel, resultat.publish_at)
        quota.consommer(conn, "videos.insert", video_id=video_id, channel_id=channel_id,
                        plafonds=plafonds)
        support = MediaFileUpload(str(chemins.final), chunksize=base.FRAGMENT_OCTETS,
                                  resumable=True, mimetype="video/mp4")
        try:
            # La construction de la requête est dans le `try` : `googleapiclient` peut lever
            # dès l'appel de `insert()` (corps refusé, scope manquant). Le quota est déjà
            # débité à ce point ; le laisser hors du filet perdrait la ligne `failed`.
            requete = yt.videos().insert(
                part="snippet,status", body=corps, media_body=support,
                notifySubscribers=bool(meta.get("notify_subscribers",
                                                channel.youtube.notify_subscribers)),
            )
            reponse = _televerser_par_fragments(requete, dire, pub_cfg.tentatives_max,
                                                pub_cfg.attente_initiale_s)
        except HttpError as erreur:
            message = base._message_http(erreur)
            quota.noter_echec(conn, "videos.insert", message, video_id=video_id)
            resultat.etapes.append(base.Etape("videos.insert", False, message, 0))
            resultat.statut = "failed"
            resultat.termine_a = maintenant()
            _enregistrer(conn, resultat, message)
            _ecrire_publish(chemins, resultat, channel)
            raise ErreurPublication(f"videos.insert refusé : {message}") from erreur

        resultat.youtube_video_id = reponse["id"]
        resultat.url = f"https://www.youtube.com/watch?v={reponse['id']}"
        resultat.statut = "published_private"
        resultat.etapes.append(base.Etape("videos.insert", True, reponse["id"], 0))
        dire(f"vidéo créée : {reponse['id']}")
        # Écriture immédiate : si la suite échoue, l'identifiant ne doit pas être perdu —
        # une vidéo en ligne dont la base ignore l'existence est une vidéo orpheline.
        _enregistrer(conn, resultat)

        _poser_miniature(yt, conn, chemins, resultat, channel, plafonds, pub_cfg, dire)
        _poser_sous_titres(yt, conn, chemins, resultat, channel, meta, plafonds, pub_cfg, dire)
        _ajouter_playlist(yt, conn, resultat, channel, meta, plafonds, pub_cfg, dire)

        # --- vérification ----------------------------------------------------------------
        quota.consommer(conn, "videos.list", video_id=video_id, channel_id=channel_id,
                        plafonds=plafonds)
        resultat.verification = _verifier(yt, resultat.youtube_video_id)
        resultat.etapes.append(base.Etape("videos.list", True, "vérification",
                                          quota.COUT["videos.list"][1]))
        reel = resultat.verification.get("privacyStatus")
        if reel == "public":
            resultat.statut = "public"
            resultat.avertissements.append(
                "la vidéo est PUBLIQUE côté YouTube alors que l'insert la demandait privée — "
                "vérifie immédiatement dans Studio"
            )
        elif resultat.verification.get("publishAt"):
            resultat.statut = "scheduled"

        resultat.termine_a = maintenant()
        _enregistrer(conn, resultat)
        _ecrire_publish(chemins, resultat, channel)
        _ecrire_pense_bete(chemins, resultat, channel)
        _completer_manifeste(chemins, resultat)
        return resultat
    finally:
        if fermer:
            conn.close()


def _televerser_par_fragments(requete: Any, dire: Callable[[str], None],
                              tentatives: int, attente_s: float) -> dict[str, Any]:
    """Boucle d'upload résumable, avec reprise sur erreur transitoire fragment par fragment.

    `next_chunk()` reprend là où la session s'était arrêtée : c'est tout l'intérêt du
    protocole résumable, et c'est ce qui permet de rejouer un 503 sans renvoyer 150 Mo.
    """
    from googleapiclient.errors import HttpError

    reponse = None
    dernier = -10
    echecs = 0
    while reponse is None:
        try:
            etat, reponse = requete.next_chunk()
        except HttpError as erreur:
            statut = getattr(erreur.resp, "status", None)
            echecs += 1
            if statut not in (500, 502, 503, 504) or echecs >= tentatives:
                raise
            pause = attente_s * (2**echecs) + random.random()
            dire(f"fragment refusé ({statut}) — reprise dans {pause:.0f} s")
            time.sleep(pause)
            continue
        if etat and int(etat.progress() * 100) >= dernier + 10:
            dernier = int(etat.progress() * 100)
            dire(f"upload {dernier} %")
    return reponse


def _poser_miniature(yt: Any, conn: sqlite3.Connection, chemins: RunPaths, resultat: Resultat,
                     channel: Channel, plafonds: quota.Plafonds, pub_cfg: Any,
                     dire: Callable[[str], None]) -> None:
    """`thumbnails.set` — 50 unités. Échec non bloquant : la vidéo existe déjà."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not chemins.thumbnail.is_file():
        resultat.avertissements.append("aucune thumbnail.png dans le run : miniature non posée")
        return
    if not channel.google_account.phone_verified:
        # Google ne documente pas la vérification téléphonique côté API ; elle est documentée
        # côté produit (support.google.com/youtube/answer/171664). On tente quand même —
        # le refus, s'il vient, est un 403 `forbidden` explicite et coûte 50 unités.
        dire("compte non vérifié par téléphone : la miniature sera probablement refusée")
    try:
        quota.consommer(conn, "thumbnails.set", video_id=resultat.video_id,
                        channel_id=resultat.channel, plafonds=plafonds)
    except quota.QuotaDepasse as erreur:
        resultat.avertissements.append(f"miniature non posée : {erreur}")
        return
    try:
        _reessayer_backoff(
            lambda: yt.thumbnails().set(
                videoId=resultat.youtube_video_id,
                media_body=MediaFileUpload(str(chemins.thumbnail), mimetype="image/png"),
            ).execute(),
            tentatives=pub_cfg.tentatives_max, attente_s=pub_cfg.attente_initiale_s,
            journal=dire,
        )
        resultat.thumbnail_set = True
        resultat.etapes.append(base.Etape("thumbnails.set", True, chemins.thumbnail.name,
                                          quota.COUT["thumbnails.set"][1]))
    except HttpError as erreur:
        message = base._message_http(erreur)
        quota.noter_echec(conn, "thumbnails.set", message, video_id=resultat.video_id)
        resultat.thumbnail_set = False
        resultat.etapes.append(base.Etape("thumbnails.set", False, message,
                                          quota.COUT["thumbnails.set"][1]))
        resultat.avertissements.append(
            f"miniature refusée ({message}) — la miniature personnalisée exige un compte "
            "vérifié par téléphone (support.google.com/youtube/answer/171664). "
            "Pose-la à la main dans Studio."
        )


def _poser_sous_titres(yt: Any, conn: sqlite3.Connection, chemins: RunPaths,
                       resultat: Resultat, channel: Channel, meta: dict[str, Any],
                       plafonds: quota.Plafonds, pub_cfg: Any,
                       dire: Callable[[str], None]) -> None:
    """`captions.insert` — 400 unités, le poste le plus cher de la publication."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not channel.youtube.captions_upload:
        resultat.avertissements.append(
            "captions_upload est faux pour cette chaîne : sous-titres non envoyés"
        )
        return
    if not chemins.subtitles_srt.is_file():
        resultat.avertissements.append("aucun subtitles.srt dans le run : sous-titres non posés")
        return
    try:
        quota.consommer(conn, "captions.insert", video_id=resultat.video_id,
                        channel_id=resultat.channel, plafonds=plafonds)
    except quota.QuotaDepasse as erreur:
        resultat.avertissements.append(f"sous-titres non posés : {erreur}")
        return
    try:
        reponse = _reessayer_backoff(
            lambda: yt.captions().insert(
                part="snippet",
                body={"snippet": {
                    "videoId": resultat.youtube_video_id,
                    "language": meta["default_language"],
                    "name": "",   # piste par défaut de la langue
                    "isDraft": False,
                }},
                media_body=MediaFileUpload(str(chemins.subtitles_srt),
                                           mimetype="application/octet-stream"),
            ).execute(),
            tentatives=pub_cfg.tentatives_max, attente_s=pub_cfg.attente_initiale_s,
            journal=dire,
        )
        resultat.captions_set = True
        resultat.caption_id = (reponse or {}).get("id")
        resultat.etapes.append(base.Etape("captions.insert", True, "subtitles.srt",
                                          quota.COUT["captions.insert"][1]))
    except HttpError as erreur:
        message = base._message_http(erreur)
        quota.noter_echec(conn, "captions.insert", message, video_id=resultat.video_id)
        resultat.etapes.append(base.Etape("captions.insert", False, message,
                                          quota.COUT["captions.insert"][1]))
        resultat.avertissements.append(f"sous-titres refusés ({message})")


def _ajouter_playlist(yt: Any, conn: sqlite3.Connection, resultat: Resultat, channel: Channel,
                      meta: dict[str, Any], plafonds: quota.Plafonds, pub_cfg: Any,
                      dire: Callable[[str], None]) -> None:
    """`playlistItems.insert` — 50 unités. La playlist du run prime sur celle de la chaîne."""
    from googleapiclient.errors import HttpError

    playlist = meta.get("playlist_id") or channel.youtube.playlist_id
    if not playlist:
        return
    try:
        quota.consommer(conn, "playlistItems.insert", video_id=resultat.video_id,
                        channel_id=resultat.channel, plafonds=plafonds)
    except quota.QuotaDepasse as erreur:
        resultat.avertissements.append(f"playlist non renseignée : {erreur}")
        return
    try:
        reponse = _reessayer_backoff(
            lambda: yt.playlistItems().insert(
                part="snippet",
                body={"snippet": {
                    "playlistId": playlist,
                    "resourceId": {"kind": "youtube#video",
                                   "videoId": resultat.youtube_video_id},
                }},
            ).execute(),
            tentatives=pub_cfg.tentatives_max, attente_s=pub_cfg.attente_initiale_s,
            journal=dire,
        )
        resultat.playlist_added = True
        resultat.playlist_item_id = (reponse or {}).get("id")
        resultat.etapes.append(base.Etape("playlistItems.insert", True, playlist,
                                          quota.COUT["playlistItems.insert"][1]))
    except HttpError as erreur:
        message = base._message_http(erreur)
        quota.noter_echec(conn, "playlistItems.insert", message, video_id=resultat.video_id)
        resultat.etapes.append(base.Etape("playlistItems.insert", False, message,
                                          quota.COUT["playlistItems.insert"][1]))
        resultat.avertissements.append(f"playlist refusée ({message})")


def _verifier(yt: Any, youtube_video_id: str) -> dict[str, Any]:
    """`videos.list` — ce que YouTube dit de la vidéo, `publishAt` compris."""
    reponse = yt.videos().list(
        part="snippet,status,processingDetails,paidProductPlacementDetails",
        id=youtube_video_id,
    ).execute()
    items = reponse.get("items", [])
    if not items:
        return {"trouve": False}
    item = items[0]
    statut = item.get("status", {})
    snippet = item.get("snippet", {})
    return {
        "trouve": True,
        "id": item["id"],
        "title": snippet.get("title"),
        "privacyStatus": statut.get("privacyStatus"),
        "publishAt": statut.get("publishAt"),
        # Ces trois-là ne servent pas à l'affichage : ils sont **relus pour être renvoyés**
        # tels quels par `programmer`. `videos.update` écrase la partie entière qu'il vise ;
        # les omettre remettrait la licence, l'intégration et les statistiques publiques à
        # leur valeur par défaut, en silence.
        "license": statut.get("license"),
        "embeddable": statut.get("embeddable"),
        "publicStatsViewable": statut.get("publicStatsViewable"),
        # Champ en écriture seule chez Google : absent de la réponse ne veut pas dire « faux ».
        "containsSyntheticMedia": statut.get("containsSyntheticMedia", "non renvoyé par l'API"),
        "madeForKids": statut.get("madeForKids"),
        "uploadStatus": statut.get("uploadStatus"),
        "processingStatus": item.get("processingDetails", {}).get("processingStatus"),
        "defaultLanguage": snippet.get("defaultLanguage"),
        "defaultAudioLanguage": snippet.get("defaultAudioLanguage"),
        "categoryId": snippet.get("categoryId"),
        "thumbnails": sorted((snippet.get("thumbnails") or {}).keys()),
        "hasPaidProductPlacement": item.get("paidProductPlacementDetails", {}).get(
            "hasPaidProductPlacement"),
    }


def verifier(channel_id: str, youtube_video_id: str, *, racine: Path | None = None,
             conn: sqlite3.Connection | None = None, service: Any = None) -> dict[str, Any]:
    """`videos.list` d'une vidéo déjà en ligne, quota compté."""
    racine = racine or racine_projet()
    plafonds = quota.Plafonds.depuis_config(racine)
    fermer = conn is None
    conn = conn or db_module.ouvrir()
    try:
        quota.verifier(conn, "videos.list", plafonds=plafonds)
        quota.consommer(conn, "videos.list", channel_id=channel_id, plafonds=plafonds)
        yt = service or oauth.service(channel_id, racine=racine)
        return _verifier(yt, youtube_video_id)
    finally:
        if fermer:
            conn.close()


# --------------------------------------------------------------------------------------
# Programmation — `factory publish release`
# --------------------------------------------------------------------------------------


def _normaliser_date(valeur: str) -> str:
    """ISO-8601 UTC avec `Z`. Une date locale sans fuseau serait interprétée à tort."""
    texte = valeur.strip()
    try:
        quand = datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError as erreur:
        raise ErreurPublication(
            f"date illisible : « {valeur} » — attendu ISO-8601, par exemple "
            "2026-09-29T16:00:00Z"
        ) from erreur
    if quand.tzinfo is None:
        quand = quand.replace(tzinfo=UTC)
    return quand.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def programmer(youtube_video_id: str, *, channel_id: str | None = None,
               quand: str | None = None, annuler: bool = False,
               racine: Path | None = None, conn: sqlite3.Connection | None = None,
               service: Any = None, journal: Callable[[str], None] | None = None) -> dict[str, Any]:
    """`videos.update` : pose (ou retire) `status.publishAt` sur une vidéo privée.

    L'objet `status` est **relu** puis renvoyé en entier : `videos.update` écrase toute la
    partie qu'il vise, et un `status` partiel effacerait `containsSyntheticMedia` et
    `selfDeclaredMadeForKids`. C'est la mécanique la plus dangereuse de ce module.
    """
    from googleapiclient.errors import HttpError

    dire = journal or (lambda _m: None)
    racine = racine or racine_projet()
    cfg = config_module.charger(racine)
    plafonds = quota.Plafonds(cfg.orchestrator.publication.uploads_max_jour,
                              cfg.orchestrator.publication.unites_max_jour,
                              cfg.orchestrator.publication.gcp_project)
    fermer = conn is None
    conn = conn or db_module.ouvrir()
    try:
        ligne = conn.execute("SELECT * FROM publications WHERE youtube_video_id = ?",
                             (youtube_video_id,)).fetchone()
        if channel_id is None:
            if ligne is None:
                raise ErreurPublication(
                    f"vidéo inconnue de la base : {youtube_video_id} — précise --channel"
                )
            channel_id = ligne["channel_id"]
        channel = cfg.channels.get(channel_id)
        if channel is None:
            raise ErreurPublication(f"chaîne inconnue : {channel_id}")
        if not channel.youtube.audit_passed and not annuler:
            raise ErreurPublication(
                f"audit_passed est faux pour {channel_id} : YouTube n'honore pas publishAt "
                "sur un projet non audité. Programme la vidéo à la main dans Studio "
                "(`factory publish manual-list` donne la liste), ou passe "
                f"youtube.audit_passed à true dans config/channels/{channel_id}.yaml quand "
                "l'audit sera obtenu."
            )
        date = _normaliser_date(quand) if quand and not annuler else None
        if date and datetime.fromisoformat(date.replace("Z", "+00:00")) <= datetime.now(UTC):
            raise ErreurPublication(f"publishAt dans le passé : {date}")

        yt = service or oauth.service(channel_id, racine=racine)

        # Relecture obligatoire avant l'écrasement.
        quota.verifier(conn, "videos.list", plafonds=plafonds)
        quota.consommer(conn, "videos.list", channel_id=channel_id, plafonds=plafonds)
        avant = _verifier(yt, youtube_video_id)
        if not avant.get("trouve"):
            raise ErreurPublication(f"vidéo introuvable côté YouTube : {youtube_video_id}")
        if avant.get("privacyStatus") != "private":
            raise ErreurPublication(
                f"la vidéo est « {avant.get('privacyStatus')} » : publishAt « can be set only "
                "if the privacy status of the video is private » "
                "(developers.google.com/youtube/v3/docs/videos). Repasse-la en privé d'abord."
            )

        statut: dict[str, Any] = {"privacyStatus": "private"}
        for champ in ("selfDeclaredMadeForKids", "license", "embeddable",
                      "publicStatsViewable"):
            if avant.get(champ) is not None:
                statut[champ] = avant[champ]
        # `containsSyntheticMedia` n'est pas relisible : Google ne le renvoie pas. On le
        # rejoue depuis le manifeste du run (CONFORMITE § 3 : « rejoue-le à chaque update »).
        synthetique = _drapeau_synthetique(conn, youtube_video_id, racine)
        if synthetique is not None:
            statut["containsSyntheticMedia"] = synthetique
        statut["selfDeclaredMadeForKids"] = bool(avant.get("madeForKids", False))
        if date:
            statut["publishAt"] = date

        quota.verifier(conn, "videos.update", plafonds=plafonds)
        quota.consommer(conn, "videos.update", channel_id=channel_id, plafonds=plafonds)
        try:
            yt.videos().update(part="status",
                               body={"id": youtube_video_id, "status": statut}).execute()
        except HttpError as erreur:
            message = base._message_http(erreur)
            quota.noter_echec(conn, "videos.update", message)
            raise ErreurPublication(f"videos.update refusé : {message}") from erreur

        dire("videos.update accepté" + (f" — publishAt {date}" if date else " — sans publishAt"))
        quota.verifier(conn, "videos.list", plafonds=plafonds)
        quota.consommer(conn, "videos.list", channel_id=channel_id, plafonds=plafonds)
        apres = _verifier(yt, youtube_video_id)
        nouveau = "scheduled" if apres.get("publishAt") else "published_private"
        conn.execute(
            "UPDATE publications SET status = ?, publish_at = ?, updated_at = ? "
            "WHERE youtube_video_id = ?",
            (nouveau, apres.get("publishAt"), maintenant(), youtube_video_id),
        )
        return apres
    finally:
        if fermer:
            conn.close()


def _drapeau_synthetique(conn: sqlite3.Connection, youtube_video_id: str,
                         racine: Path) -> bool | None:
    """Relit `contains_synthetic_media` dans le `metadata.json` du run, seule source valable."""
    ligne = conn.execute("SELECT video_id FROM publications WHERE youtube_video_id = ?",
                         (youtube_video_id,)).fetchone()
    if ligne is None:
        return None
    chemins = RunPaths.depuis_video_id(ligne["video_id"], racine)
    if not chemins.metadata.is_file():
        return None
    return bool(json.loads(chemins.metadata.read_text(encoding="utf-8"))
                .get("contains_synthetic_media", False))


# --------------------------------------------------------------------------------------
# Base, publish.json, manifeste
# --------------------------------------------------------------------------------------


def _enregistrer(conn: sqlite3.Connection, resultat: Resultat,
                 erreur: str | None = None) -> None:
    """Écrit (ou met à jour) la ligne de `publications`. Idempotent sur `video_id`."""
    conn.execute(
        "INSERT INTO publications (video_id, channel_id, youtube_video_id, status, "
        "publish_at, uploaded_at, thumbnail_set, captions_set, playlist_added, units_used, "
        "last_error, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(video_id) DO UPDATE SET "
        "channel_id = excluded.channel_id, youtube_video_id = excluded.youtube_video_id, "
        "status = excluded.status, publish_at = excluded.publish_at, "
        "uploaded_at = excluded.uploaded_at, thumbnail_set = excluded.thumbnail_set, "
        "captions_set = excluded.captions_set, playlist_added = excluded.playlist_added, "
        "units_used = excluded.units_used, last_error = excluded.last_error, "
        "updated_at = excluded.updated_at",
        (resultat.video_id, resultat.channel, resultat.youtube_video_id, resultat.statut,
         resultat.publish_at, resultat.demarre_a, int(resultat.thumbnail_set),
         int(resultat.captions_set), int(resultat.playlist_added), resultat.unites,
         erreur, maintenant()),
    )
    conn.execute(
        "UPDATE runs SET youtube_video_id = ?, publish_state = ?, publish_path = ?, "
        "updated_at = ? WHERE video_id = ?",
        (resultat.youtube_video_id,
         "scheduled" if resultat.statut == "scheduled" else "uploaded_private",
         "api_scheduled" if resultat.statut == "scheduled" else "manual_studio",
         maintenant(), resultat.video_id),
    )


def _ecrire_publish(chemins: RunPaths, resultat: Resultat, channel: Channel) -> None:
    """`publish.json` au contrat de `INTERFACES.md`. Aucun jeton n'y figure."""
    gestes = [{"id": "schedule", "required": not channel.youtube.audit_passed,
               "done": False, "done_at": None}]
    if channel.paid_promotion:
        gestes.append({"id": "paid_promotion_box", "required": True,
                       "done": False, "done_at": None})
    etats = {"published_private": "uploaded_private", "scheduled": "scheduled",
             "public": "public", "failed": "draft"}
    charge = {
        "schema_version": "1.0",
        "publish_path": channel.publish_path,
        "publish_state": etats[resultat.statut],
        "checklist": [],   # rempli par `factory precheck` (étape 23.2)
        "youtube_video_id": resultat.youtube_video_id,
        "uploaded_at": resultat.demarre_a or None,
        "publish_at": resultat.publish_at,
        "published_at": None,   # personne ne peut l'écrire ici (INTERFACES § publish.json)
        "thumbnail_set": resultat.thumbnail_set,
        "caption_id": resultat.caption_id,
        "playlist_item_id": resultat.playlist_item_id,
        "quota_units_spent": resultat.unites,
        "quota_day": quota.aujourdhui(),
        "reporting_job_id": None,
        "manual_steps": gestes,
        "post_check": {
            "has_paid_product_placement": resultat.verification.get("hasPaidProductPlacement")
        },
        "retry_count": 0,
        "last_error": None,
        # Hors contrat, gardé parce qu'il porte la preuve : l'appel, son verdict, son coût.
        "steps": [{"call": e.nom, "ok": e.ok, "detail": e.message, "quota_units": e.unites}
                  for e in resultat.etapes],
        "warnings": resultat.avertissements,
        "verification": resultat.verification,
        "url": resultat.url,
        "studio_url": LIEN_STUDIO.format(id=resultat.youtube_video_id)
        if resultat.youtube_video_id else None,
    }
    chemins.publish.write_text(json.dumps(charge, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")


def _ecrire_pense_bete(chemins: RunPaths, resultat: Resultat, channel: Channel) -> None:
    """`publication.md` — les gestes que l'API ne sait pas faire (CONFORMITE § 2).

    Exigé par la conformité et écrit par personne jusqu'ici. Sans lui, l'opérateur oublie la
    case « promotion payante », qui n'a **aucun champ d'écriture dans l'API** et dont l'oubli
    met la vidéo en infraction (CONFORMITE § 3 couche 2).
    """
    if not resultat.youtube_video_id:
        return
    lien = LIEN_STUDIO.format(id=resultat.youtube_video_id)
    lignes = [
        f"# À faire dans Studio — {chemins.video_id}",
        "",
        f"- Vidéo : {resultat.url}",
        f"- Studio : {lien}",
        f"- Chaîne : {channel.name} (`{channel.id}`)",
        f"- Statut actuel : **{resultat.statut}**",
        "",
        "## Gestes",
        "",
    ]
    if not channel.youtube.audit_passed:
        quand = resultat.publish_at or "date non fixée (le calendrier arrive à l'étape 23.2)"
        lignes.append(f"1. **Passer en « Programmée »** pour le {quand}. L'audit de l'API "
                      "n'est pas obtenu : l'API ne peut pas le faire à notre place.")
    else:
        lignes.append("1. Programmation faite par l'API — rien à faire ici.")
    if channel.paid_promotion:
        lignes.append("2. **Cocher « La vidéo contient une promotion payante »**. L'API ne "
                      "l'expose qu'en lecture : ce geste est manuel pour toujours, même "
                      "après l'audit. Sans lui, la vidéo est en infraction.")
    if not resultat.thumbnail_set:
        lignes.append("3. **Poser la miniature** `thumbnail.png` : l'API l'a refusée ou ne "
                      "l'a pas tentée (compte non vérifié par téléphone).")
    if not resultat.captions_set:
        lignes.append("4. **Charger `subtitles.srt`** : les sous-titres n'ont pas été posés.")
    if resultat.avertissements:
        lignes += ["", "## Alertes de l'upload", ""]
        lignes += [f"- {a}" for a in resultat.avertissements]
    chemins.publication_md.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def _completer_manifeste(chemins: RunPaths, resultat: Resultat) -> None:
    """Inscrit l'identifiant YouTube au manifeste. `published_at` reste nul : rien n'est public."""
    if not chemins.manifest.is_file():
        return
    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    resultats = manifeste.setdefault("resultats", {})
    resultats["youtube_video_id"] = resultat.youtube_video_id
    resultats["published_at"] = None
    chemins.manifest.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")


# --------------------------------------------------------------------------------------
# Listes — état du jour et gestes manuels
# --------------------------------------------------------------------------------------


@dataclass
class LigneManuelle:
    """Une vidéo en ligne, privée, qu'un humain doit programmer dans Studio."""

    video_id: str
    channel_id: str
    youtube_video_id: str
    titre: str
    publish_at: str | None
    heure_locale: str
    studio_url: str


def liste_manuelle(conn: sqlite3.Connection,
                   racine: Path | None = None) -> list[LigneManuelle]:
    """Les vidéos `published_private` des chaînes dont l'audit n'est pas passé.

    C'est la seule liste qui compte tant que l'audit n'est pas obtenu : ce qui n'y figure pas
    n'est pas publié, et ce qui y figure attend deux minutes d'un humain dans Studio.
    """
    from zoneinfo import ZoneInfo

    racine = racine or racine_projet()
    cfg = config_module.charger(racine)
    lignes: list[LigneManuelle] = []
    for ligne in conn.execute(
        "SELECT * FROM publications WHERE status = 'published_private' "
        "ORDER BY publish_at IS NULL, publish_at, uploaded_at"
    ):
        channel = cfg.channels.get(ligne["channel_id"])
        if channel is not None and channel.youtube.audit_passed:
            continue   # celle-ci se programme toute seule
        titre = _titre(racine, ligne["video_id"])
        heure = "—"
        if ligne["publish_at"] and channel is not None:
            try:
                utc = datetime.fromisoformat(ligne["publish_at"].replace("Z", "+00:00"))
                local = utc.astimezone(ZoneInfo(channel.cadence.timezone))
                heure = local.strftime("%d/%m/%Y %H:%M ") + channel.cadence.timezone
            except (ValueError, KeyError):
                heure = ligne["publish_at"]
        lignes.append(LigneManuelle(
            video_id=ligne["video_id"], channel_id=ligne["channel_id"],
            youtube_video_id=ligne["youtube_video_id"] or "",
            titre=titre, publish_at=ligne["publish_at"], heure_locale=heure,
            studio_url=LIEN_STUDIO.format(id=ligne["youtube_video_id"])
            if ligne["youtube_video_id"] else "—",
        ))
    return lignes


def _titre(racine: Path, video_id: str) -> str:
    """Titre retenu, lu dans le `metadata.json` du run."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.metadata.is_file():
        return "(metadata.json absent)"
    try:
        return json.loads(chemins.metadata.read_text(encoding="utf-8")).get(
            "title_chosen", "(sans titre)")
    except json.JSONDecodeError:
        return "(metadata.json illisible)"


@dataclass
class Etat:
    """Ce que `factory publish status` affiche."""

    quota: quota.EtatQuota
    publications_possibles: int
    a_publier: list[LigneManuelle]
    programmees: list[dict[str, Any]]
    erreurs: list[dict[str, Any]]
    jobs_rapports: list[dict[str, Any]]


def etat_du_jour(conn: sqlite3.Connection, racine: Path | None = None) -> Etat:
    """Quota du jour, gestes en attente, programmations, erreurs, jobs de rapports."""
    racine = racine or racine_projet()
    plafonds = quota.Plafonds.depuis_config(racine)
    courant = quota.etat(conn, plafonds)
    programmees = [dict(l) for l in conn.execute(
        "SELECT * FROM publications WHERE status = 'scheduled' ORDER BY publish_at")]
    erreurs = [dict(l) for l in conn.execute(
        "SELECT * FROM publications WHERE status = 'failed' ORDER BY updated_at DESC LIMIT 10")]
    jobs = [dict(l) for l in conn.execute(
        "SELECT * FROM reporting_jobs WHERE state = 'active' ORDER BY channel_id, report_type")]
    return Etat(
        quota=courant,
        publications_possibles=quota.publications_possibles(courant),
        a_publier=liste_manuelle(conn, racine),
        programmees=programmees,
        erreurs=erreurs,
        jobs_rapports=jobs,
    )


def premiere_publication_sans_job(conn: sqlite3.Connection, channel_id: str) -> str | None:
    """Rend un motif de refus si la chaîne publie sans job de rapports, `None` sinon.

    Les rapports « reach » ne sont **pas rétroactifs** : une chaîne qui publie avant que ses
    jobs existent perd ses impressions et son CTR pour ces vidéos, définitivement. C'est la
    raison d'être de l'ordre imposé par l'étape : les jobs d'abord, l'upload ensuite.
    """
    ligne = conn.execute(
        "SELECT count(*) AS n FROM reporting_jobs WHERE channel_id = ? AND state = 'active' "
        "AND report_type = 'channel_reach_basic_a1'", (channel_id,)).fetchone()
    if ligne and ligne["n"]:
        return None
    return (
        f"aucun job « channel_reach_basic_a1 » pour {channel_id} : les impressions et le CTR "
        "ne sont pas rétroactifs, cette vidéo n'en aurait jamais. Lance "
        f"`factory publish reporting-jobs --channel {channel_id}` avant de publier."
    )


def date_prevue(conn: sqlite3.Connection, video_id: str, channel_id: str,
                racine: Path | None = None) -> str | None:
    """Date du calendrier de l'étape 23.2, quand elle existera. `None` aujourd'hui.

    L'appel est écrit ici pour que l'étape 23.2 n'ait qu'à remplir `calendar.py` : le point
    d'accroche existe, il ne rend rien tant que le module est absent.
    """
    try:
        from factory.publish import calendar as calendrier  # type: ignore[attr-defined]
    except ImportError:
        return None
    return calendrier.date_pour(conn, video_id, channel_id, racine=racine)


def precheck(video_id: str, channel_id: str, racine: Path | None = None) -> list[str]:
    """Checklist de conformité de l'étape 23.2. Liste vide tant qu'elle n'existe pas.

    Même intention que `date_prevue` : l'orchestrateur appelle déjà cette fonction avant tout
    upload, et le jour où `precheck.py` est écrit, le blocage devient effectif sans toucher à
    l'appelant.
    """
    try:
        from factory.publish import precheck as controles  # type: ignore[attr-defined]
    except ImportError:
        return []
    return controles.bloquants(video_id, channel_id, racine=racine)


def publier_run(video_id: str, channel_id: str, *, racine: Path | None = None,
                conn: sqlite3.Connection | None = None,
                journal: Callable[[str], None] | None = None) -> Resultat:
    """Point d'entrée de l'orchestrateur : precheck, calendrier, jobs de rapports, upload.

    C'est ici que l'ordre imposé par l'étape est tenu — et c'est la seule porte que le runner
    doit connaître. `televerser` reste accessible pour un upload décidé à la main.
    """
    racine = racine or racine_projet()
    fermer = conn is None
    conn = conn or db_module.ouvrir()
    try:
        bloquants = precheck(video_id, channel_id, racine)
        if bloquants:
            raise ErreurPublication(
                "precheck bloque la publication : " + " · ".join(bloquants))
        manque = premiere_publication_sans_job(conn, channel_id)
        if manque:
            raise ErreurPublication(manque)
        resultat = televerser(video_id, channel_id,
                              publish_at=date_prevue(conn, video_id, channel_id, racine),
                              racine=racine, conn=conn, journal=journal)
        # Étape 24 : déclinaisons enfilées après l'upload si `declencheur: publication`.
        cfg_orch = config_module.charger(racine, strict=False).orchestrator
        if resultat.youtube_video_id and cfg_orch is not None and cfg_orch.declinaison.actif \
                and cfg_orch.declinaison.declencheur == "publication":
            from factory.steps import localize as localize_module
            localize_module.enfiler_declinaisons(conn, video_id, racine)
        return resultat
    finally:
        if fermer:
            conn.close()


def fenetre_j7() -> str:
    """Date à J+7, arrondie à l'heure — la programmation d'essai de l'étape."""
    return (datetime.now(UTC) + timedelta(days=7)).replace(
        minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
