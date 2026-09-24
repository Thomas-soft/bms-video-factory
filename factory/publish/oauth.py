"""Flux OAuth 2.0 « installed app » pour les services API de YouTube.

Trois points méritent d'être lus avant d'y toucher.

- **Le jeton est un secret de fichier, jamais une valeur de configuration.** Il est écrit
  dans `secrets/tokens/<channel>.json` en mode 600, référencé par `google_account.token_ref`
  dans `config/channels/<channel>.yaml`, et jamais journalisé ni affiché — seule sa présence
  et sa date d'expiration le sont.
- **Le projet doit être « En production », pas « Testing ».** En mode Testing, Google fait
  expirer l'autorisation — et le jeton de rafraîchissement avec elle — **sept jours** après le
  consentement ; le démon de la phase 4 s'arrêterait chaque semaine. En production non
  vérifiée, l'écran d'avertissement reste, le plafond est de 100 utilisateurs au total, et les
  jetons ne sont plus limités dans le temps.
- **`prompt="consent"` est obligatoire au premier consentement.** Sans lui, Google ne renvoie
  un `refresh_token` que la toute première fois qu'un compte autorise le client : une
  ré-autorisation ultérieure produirait un jeton qui meurt en une heure.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from factory.core import secrets as secrets_module
from factory.core.paths import racine_projet

#: Scopes demandés par l'usine, dans l'ordre du dossier d'audit (`docs/AUDIT-API.md` § 3).
#: Chacun est justifié un par un devant Google ; n'en ajoute aucun sans l'y ajouter aussi.
SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
)

#: Référence du client OAuth téléchargé depuis la console Google Cloud (« Application de bureau »).
REF_CLIENT_SECRET = "secrets/client_secret.json"


class ErreurOAuth(RuntimeError):
    """Consentement impossible, jeton absent ou irrécupérable."""


@dataclass(frozen=True)
class Chaine:
    """Une chaîne détenue par le compte connecté, telle que `channels.list?mine=true` la rend."""

    channel_id: str
    titre: str
    playlist_uploads: str | None


def chemin_client_secret(racine: Path | None = None) -> Path:
    """Chemin du client OAuth. Ne lit pas le fichier."""
    return secrets_module.chemin_reference(REF_CLIENT_SECRET, racine)


def chemin_jeton(channel: str, racine: Path | None = None) -> Path:
    """Chemin du jeton d'une chaîne : `secrets/tokens/<channel>.json`."""
    return secrets_module.chemin_reference(f"secrets/tokens/{channel}.json", racine)


def _ecrire_jeton(chemin: Path, identifiants) -> None:
    """Écrit le jeton en mode 600. Rien de son contenu ne sort de cette fonction."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ancien = os.umask(0o077)
    try:
        chemin.write_text(identifiants.to_json(), encoding="utf-8")
    finally:
        os.umask(ancien)
    chemin.chmod(0o600)


def autoriser(channel: str, racine: Path | None = None, port: int = 0):
    """Ouvre le consentement dans le navigateur de l'opérateur et enregistre le jeton.

    L'opérateur se connecte lui-même : aucun identifiant ne transite par le code, aucune page
    n'est pilotée. Le serveur local n'écoute que le temps de la redirection.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    client = chemin_client_secret(racine)
    if not client.is_file():
        raise ErreurOAuth(
            f"client OAuth absent : {REF_CLIENT_SECRET} — télécharge le JSON « Application de "
            "bureau » depuis la console Google Cloud (Google Auth Platform > Clients)"
        )
    flux = InstalledAppFlow.from_client_secrets_file(str(client), list(SCOPES))
    identifiants = flux.run_local_server(
        port=port,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message=(
            "Connecte-toi avec le compte Google de la chaîne, puis choisis la chaîne.\n"
            "Ouvre cette adresse si le navigateur ne s'ouvre pas : {url}"
        ),
        success_message=(
            "Consentement enregistré. Tu peux fermer cet onglet et revenir au terminal."
        ),
        open_browser=True,
    )
    if not identifiants.refresh_token:
        raise ErreurOAuth(
            "aucun jeton de rafraîchissement renvoyé : révoque l'accès sur "
            "https://myaccount.google.com/permissions puis recommence"
        )
    destination = chemin_jeton(channel, racine)
    _ecrire_jeton(destination, identifiants)
    return identifiants


def charger_identifiants(channel: str, racine: Path | None = None):
    """Charge le jeton d'une chaîne et le rafraîchit s'il a expiré. Jamais de consentement ici."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    chemin = chemin_jeton(channel, racine)
    if not chemin.is_file():
        raise ErreurOAuth(
            f"aucun jeton pour « {channel} » : lance `factory publish auth --channel {channel}`"
        )
    if not secrets_module.permissions_sures(chemin):
        raise ErreurOAuth(f"permissions trop ouvertes sur le jeton de « {channel} » : chmod 600")
    identifiants = Credentials.from_authorized_user_file(str(chemin), list(SCOPES))
    if identifiants.valid:
        return identifiants
    if not identifiants.refresh_token:
        raise ErreurOAuth(
            f"jeton de « {channel} » expiré et non rafraîchissable : relance `factory publish "
            f"auth --channel {channel}`"
        )
    try:
        identifiants.refresh(Request())
    except RefreshError as erreur:  # jeton révoqué, ou projet repassé en « Testing »
        raise ErreurOAuth(
            f"rafraîchissement refusé pour « {channel} » ({type(erreur).__name__}) : le jeton a "
            "été révoqué, ou le projet OAuth n'est plus « En production » (les autorisations de "
            f"test expirent en 7 jours). Relance `factory publish auth --channel {channel}`."
        ) from erreur
    _ecrire_jeton(chemin, identifiants)
    return identifiants


def service(channel: str, api: str = "youtube", version: str = "v3", racine: Path | None = None):
    """Client d'API authentifié pour une chaîne. `api` : `youtube`, `youtubeAnalytics`…"""
    from googleapiclient.discovery import build

    identifiants = charger_identifiants(channel, racine)
    return build(api, version, credentials=identifiants, cache_discovery=False)


def chaines_du_compte(channel: str, racine: Path | None = None) -> list[Chaine]:
    """`channels.list?mine=true` — 1 unité de quota. Rend les chaînes détenues par le compte."""
    reponse = (
        service(channel, racine=racine)
        .channels()
        .list(part="id,snippet,contentDetails", mine=True)
        .execute()
    )
    chaines: list[Chaine] = []
    for item in reponse.get("items", []):
        lies = item.get("contentDetails", {}).get("relatedPlaylists", {})
        chaines.append(
            Chaine(
                channel_id=item["id"],
                titre=item.get("snippet", {}).get("title", ""),
                playlist_uploads=lies.get("uploads"),
            )
        )
    return chaines


def etat_jeton(channel: str, racine: Path | None = None) -> dict[str, object]:
    """Ce qu'on peut dire d'un jeton sans en révéler la valeur : présence, scopes, expiration."""
    chemin = chemin_jeton(channel, racine)
    if not chemin.is_file():
        return {"present": False}
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    return {
        "present": True,
        "chemin": str(chemin.relative_to(racine or racine_projet())),
        "mode_600": secrets_module.permissions_sures(chemin),
        "scopes": brut.get("scopes", []),
        "refresh_token": "présent" if brut.get("refresh_token") else "absent",
        "expiry": brut.get("expiry"),
    }
