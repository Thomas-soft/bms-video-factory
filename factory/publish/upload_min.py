"""`factory publish upload` — `videos.insert` résumable, miniature, sous-titres, vérification.

Uploader minimal de la phase 1 : il porte **toutes** les métadonnées dès l'insertion, parce
que le geste humain restant dans Studio doit se limiter au basculement de confidentialité
(CONFORMITE § 2). Trois points méritent d'être lus avant d'y toucher.

- **La vidéo sort privée, et ce n'est pas un choix.** Tout upload d'un projet API non audité
  est forcé en privé par YouTube ; l'écrire explicitement (`privacyStatus="private"`) évite de
  croire à une programmation qui n'existe pas. Tant que `youtube.audit_passed` est faux, le
  module refuse toute autre valeur.
- **`containsSyntheticMedia` est recopié du manifeste, jamais recalculé ici.** Le drapeau est
  posé plan par plan au moment de la génération (CONFORMITE § 3 couche 1) ; un drapeau
  reconstitué à l'upload serait un drapeau faux.
- **La case « promotion payante » n'a pas de champ d'écriture dans l'API.** Si le run la
  réclame, le module lève une alerte et l'inscrit dans `publish.json` : elle se coche à la
  main dans Studio, même après l'audit.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from factory.core import config as config_module
from factory.core.models import Channel
from factory.core.paths import RunPaths, racine_projet
from factory.publish import oauth

#: Coût en unités de quota, documenté par Google. Le compteur de `publish.json` en dépend :
#: 6 uploads/jour saturent le quota de 10 000 unités avant le compteur de 100 inserts.
COUT_QUOTA = {
    "videos.insert": 1600,
    "thumbnails.set": 50,
    "captions.insert": 400,
    "videos.list": 1,
    "channels.list": 1,
}

#: Taille de fragment de l'upload résumable : 8 Mio, un compromis entre reprises et appels.
FRAGMENT_OCTETS = 8 * 1024 * 1024


class ErreurUpload(RuntimeError):
    """Run inutilisable, configuration incohérente ou refus de l'API."""


@dataclass
class Etape:
    """Un appel d'API, son verdict et son coût."""

    nom: str
    ok: bool
    message: str
    unites: int = 0


@dataclass
class Resultat:
    """Ce que `publish.json` enregistre."""

    video_id: str
    channel: str
    youtube_video_id: str | None = None
    url: str | None = None
    etapes: list[Etape] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    demarre_a: str = ""
    termine_a: str = ""

    @property
    def quota_units(self) -> int:
        """Somme des unités réellement dépensées."""
        return sum(e.unites for e in self.etapes)


def _maintenant() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _lire_metadata(chemins: RunPaths) -> dict[str, Any]:
    if not chemins.metadata.is_file():
        raise ErreurUpload(
            f"metadata.json absent pour {chemins.video_id} : lance `factory metadata --run "
            f"{chemins.video_id}` avant de publier"
        )
    return json.loads(chemins.metadata.read_text(encoding="utf-8"))


def _controles_prealables(chemins: RunPaths, meta: dict[str, Any], channel: Channel) -> list[str]:
    """Refus bloquants avant toute dépense de quota. Rend la liste des alertes non bloquantes."""
    if not chemins.final.is_file():
        raise ErreurUpload(
            f"final.mp4 absent pour {chemins.video_id} : le run n'est pas exporté"
        )
    if meta.get("default_language") != channel.lang:
        raise ErreurUpload(
            f"langue incohérente : le run est en « {meta.get('default_language')} », la chaîne "
            f"{channel.id} publie en « {channel.lang} ». Un run n'est jamais publié sur une "
            "chaîne d'une autre langue."
        )
    if "contains_synthetic_media" not in meta:
        raise ErreurUpload(
            "contains_synthetic_media absent de metadata.json : le drapeau se pose à la "
            "génération (CONFORMITE § 3), il ne se devine pas à l'upload"
        )
    alertes: list[str] = []
    if meta.get("paid_promotion"):
        alertes.append(
            "promotion payante : l'API n'expose aucun champ d'écriture — coche la case dans "
            "YouTube Studio (CONFORMITE § 3 couche 2), sans quoi la vidéo est en infraction"
        )
    if not channel.google_account.phone_verified:
        alertes.append(
            f"compte « {channel.google_account.alias} » non vérifié par téléphone : miniature "
            "personnalisée et vidéo de plus de 15 minutes refusées par YouTube"
        )
    return alertes


def _corps_insert(meta: dict[str, Any], channel: Channel) -> dict[str, Any]:
    """Le corps de `videos.insert`, composé du seul `metadata.json` et de la configuration."""
    tags = list(meta.get("tags") or [])
    return {
        "snippet": {
            "title": meta["title_chosen"],
            "description": meta["description"],
            "tags": tags,
            "categoryId": meta.get("category_id") or channel.youtube.category_id,
            "defaultLanguage": meta["default_language"],
            "defaultAudioLanguage": meta.get("default_audio_language", meta["default_language"]),
        },
        "status": {
            # Forcé en privé tant que l'audit n'est pas obtenu — et écrit explicitement.
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(meta["contains_synthetic_media"]),
            "license": "youtube",
            "embeddable": True,
        },
    }


def televerser(
    video_id: str,
    channel_id: str,
    racine: Path | None = None,
    journal: Callable[[str], None] | None = None,
    dry_run: bool = False,
) -> Resultat:
    """Téléverse un run sur une chaîne, en privé, avec miniature et sous-titres."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    dire = journal or (lambda _m: None)
    racine = racine or racine_projet()
    cfg = config_module.charger(racine)
    channel = cfg.channels.get(channel_id)
    if channel is None:
        connues = ", ".join(sorted(cfg.channels)) or "aucune"
        raise ErreurUpload(f"chaîne inconnue : {channel_id} (connues : {connues})")

    chemins = RunPaths.depuis_video_id(video_id, racine)
    meta = _lire_metadata(chemins)
    resultat = Resultat(video_id=video_id, channel=channel_id, demarre_a=_maintenant())
    resultat.avertissements.extend(_controles_prealables(chemins, meta, channel))

    if channel.youtube.audit_passed:
        resultat.avertissements.append(
            "audit_passed est vrai : cet uploader minimal publie tout de même en privé ; la "
            "programmation relève de l'étape 23"
        )

    if dry_run:
        resultat.etapes.append(
            Etape("dry-run", True, f"corps prêt, {chemins.final.stat().st_size / 1e6:.1f} Mo", 0)
        )
        resultat.termine_a = _maintenant()
        return resultat

    yt = oauth.service(channel_id, racine=racine)

    # --- videos.insert, résumable -------------------------------------------------------
    corps = _corps_insert(meta, channel)
    support = MediaFileUpload(
        str(chemins.final), chunksize=FRAGMENT_OCTETS, resumable=True, mimetype="video/mp4"
    )
    requete = yt.videos().insert(
        part="snippet,status",
        body=corps,
        media_body=support,
        notifySubscribers=False,  # étape 14 : aucune notification, la vidéo reste privée
    )
    reponse = None
    dernier_pourcent = -10
    try:
        while reponse is None:
            etat, reponse = requete.next_chunk()
            if etat and int(etat.progress() * 100) >= dernier_pourcent + 10:
                dernier_pourcent = int(etat.progress() * 100)
                dire(f"upload {dernier_pourcent} %")
    except HttpError as erreur:
        resultat.etapes.append(
            Etape("videos.insert", False, _message_http(erreur), COUT_QUOTA["videos.insert"])
        )
        resultat.termine_a = _maintenant()
        _ecrire_publish(chemins, resultat)
        raise ErreurUpload(f"videos.insert refusé : {_message_http(erreur)}") from erreur

    resultat.youtube_video_id = reponse["id"]
    resultat.url = f"https://www.youtube.com/watch?v={reponse['id']}"
    resultat.etapes.append(
        Etape("videos.insert", True, reponse["id"], COUT_QUOTA["videos.insert"])
    )
    dire(f"vidéo créée : {reponse['id']}")

    # --- thumbnails.set ------------------------------------------------------------------
    if chemins.thumbnail.is_file():
        try:
            _reessayer(
                lambda: yt.thumbnails()
                .set(
                    videoId=resultat.youtube_video_id,
                    media_body=MediaFileUpload(str(chemins.thumbnail), mimetype="image/png"),
                )
                .execute()
            )
            resultat.etapes.append(
                Etape("thumbnails.set", True, chemins.thumbnail.name, COUT_QUOTA["thumbnails.set"])
            )
        except HttpError as erreur:
            message = _message_http(erreur)
            resultat.etapes.append(
                Etape("thumbnails.set", False, message, COUT_QUOTA["thumbnails.set"])
            )
            resultat.avertissements.append(
                f"miniature refusée ({message}) — la miniature personnalisée exige un compte "
                "vérifié par téléphone (support.google.com/youtube/answer/171664)"
            )
    else:
        resultat.avertissements.append("aucune thumbnail.png dans le run : miniature non posée")

    # --- captions.insert -----------------------------------------------------------------
    if channel.youtube.captions_upload and chemins.subtitles_srt.is_file():
        try:
            _reessayer(lambda: yt.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": resultat.youtube_video_id,
                        "language": meta["default_language"],
                        "name": "",  # piste par défaut de la langue
                        "isDraft": False,
                    }
                },
                media_body=MediaFileUpload(
                    str(chemins.subtitles_srt), mimetype="application/octet-stream"
                ),
            ).execute())
            resultat.etapes.append(
                Etape("captions.insert", True, "subtitles.srt", COUT_QUOTA["captions.insert"])
            )
        except HttpError as erreur:
            message = _message_http(erreur)
            resultat.etapes.append(
                Etape("captions.insert", False, message, COUT_QUOTA["captions.insert"])
            )
            resultat.avertissements.append(f"sous-titres refusés ({message})")
    elif not channel.youtube.captions_upload:
        resultat.avertissements.append(
            "captions_upload est faux pour cette chaîne : sous-titres non envoyés"
        )

    # --- vérification --------------------------------------------------------------------
    resultat.verification = verifier(channel_id, resultat.youtube_video_id, racine=racine)
    resultat.etapes.append(
        Etape("videos.list", True, "vérification", COUT_QUOTA["videos.list"])
    )
    resultat.termine_a = _maintenant()

    _ecrire_publish(chemins, resultat)
    _completer_manifeste(chemins, resultat)
    return resultat


def verifier(channel_id: str, youtube_video_id: str, racine: Path | None = None) -> dict[str, Any]:
    """`videos.list` — ce que YouTube dit de la vidéo, pas ce que l'uploader croit avoir envoyé."""
    yt = oauth.service(channel_id, racine=racine)
    reponse = (
        yt.videos()
        .list(part="snippet,status,processingDetails,paidProductPlacementDetails",
              id=youtube_video_id)
        .execute()
    )
    items = reponse.get("items", [])
    if not items:
        return {"trouve": False}
    item = items[0]
    statut = item.get("status", {})
    snippet = item.get("snippet", {})
    traitement = item.get("processingDetails", {})
    return {
        "trouve": True,
        "id": item["id"],
        "title": snippet.get("title"),
        "privacyStatus": statut.get("privacyStatus"),
        # Champ en écriture seule chez Google : absent de la réponse ne veut pas dire « faux ».
        "containsSyntheticMedia": statut.get("containsSyntheticMedia", "non renvoyé par l'API"),
        "madeForKids": statut.get("madeForKids"),
        "uploadStatus": statut.get("uploadStatus"),
        "processingStatus": traitement.get("processingStatus"),
        "defaultLanguage": snippet.get("defaultLanguage"),
        "categoryId": snippet.get("categoryId"),
        "hasPaidProductPlacement": item.get("paidProductPlacementDetails", {}).get(
            "hasPaidProductPlacement"
        ),
    }


def _reessayer(appel: Callable[[], Any], tentatives: int = 4, attente_s: float = 15.0):
    """Rejoue un appel tant que YouTube répond « vidéo introuvable ».

    Juste après `videos.insert`, la vidéo existe pour l'API d'upload mais pas encore pour
    `thumbnails.set` ni `captions.insert` : les deux répondent 404 pendant quelques secondes.
    Un échec coûte son quota entier (400 unités pour les sous-titres) ; il vaut mieux attendre.
    """
    from googleapiclient.errors import HttpError

    for essai in range(tentatives):
        try:
            return appel()
        except HttpError as erreur:
            transitoire = erreur.resp.status in (404, 409, 500, 503)
            if not transitoire or essai == tentatives - 1:
                raise
            time.sleep(attente_s)
    raise RuntimeError("inatteignable")


def _message_http(erreur) -> str:
    """Message d'erreur de l'API, court et sans jeton."""
    try:
        contenu = json.loads(erreur.content.decode("utf-8"))
        detail = contenu.get("error", {})
        motifs = ", ".join(e.get("reason", "") for e in detail.get("errors", []) if e.get("reason"))
        return f"{erreur.resp.status} {detail.get('message', '')}".strip() + (
            f" [{motifs}]" if motifs else ""
        )
    except Exception:  # noqa: BLE001 — une erreur d'API illisible ne doit pas masquer l'échec
        return f"{getattr(erreur, 'resp', None) and erreur.resp.status} {erreur}"


def _ecrire_publish(chemins: RunPaths, resultat: Resultat) -> None:
    """`publish.json` — la trace de l'appel, quota compris. Aucun jeton n'y figure."""
    charge = {
        "schema_version": "1.0",
        "video_id": resultat.video_id,
        "channel": resultat.channel,
        "youtube_video_id": resultat.youtube_video_id,
        "url": resultat.url,
        "quota_units": resultat.quota_units,
        "started_at": resultat.demarre_a,
        "finished_at": resultat.termine_a,
        "steps": [
            {"call": e.nom, "ok": e.ok, "detail": e.message, "quota_units": e.unites}
            for e in resultat.etapes
        ],
        "warnings": resultat.avertissements,
        "verification": resultat.verification,
    }
    chemins.publish.write_text(
        json.dumps(charge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _completer_manifeste(chemins: RunPaths, resultat: Resultat) -> None:
    """Inscrit l'identifiant YouTube au manifeste.

    `conformite.publish_state` n'est **pas** touché : il ne passe à `uploaded_private` qu'une
    fois la relecture humaine enregistrée (CONFORMITE § 10.1, vérifié par `RunManifest`). Une
    vidéo privée non relue n'est pas une vidéo publiable.
    """
    if not chemins.manifest.is_file():
        return
    manifeste = json.loads(chemins.manifest.read_text(encoding="utf-8"))
    resultats = manifeste.setdefault("resultats", {})
    resultats["youtube_video_id"] = resultat.youtube_video_id
    resultats["published_at"] = None  # privée : rien n'est publié
    chemins.manifest.write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
