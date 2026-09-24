"""Lit musical : choix d'une piste de la bibliothèque, rotation, mise à la durée.

Trois règles de conformité sont **codées** ici, pas seulement documentées (`CONFORMITE.md` § 7) :

1. **Aucune piste sans licence.** Une piste est un couple `<slug>.mp3` + `<slug>.json` frère.
   Un fichier audio sans manifeste n'est pas ignoré en silence : il est refusé et signalé.
2. **Licence commerciale obligatoire.** `licence_commerciale()` filtre CC-BY-NC, CC-BY-ND et
   les licences « sampling » ; une piste refusée ne peut pas entrer dans une vidéo.
3. **Crédit automatique.** `attribution_requise` vraie sans `credit_line` est une erreur de
   manifeste : le crédit doit exister avant le montage, il sera recopié en description.

Et une règle de production : **rotation**. Une chaîne qui repasse la même piste toutes les
semaines s'entend ; les pistes employées par les **5 derniers runs** de la chaîne sont écartées
tant qu'il reste un candidat, puis la contrainte se relâche plutôt que d'échouer.

**Freesound est écarté depuis le 15/09/2026** : les CGU de son API ne couvrent pas l'usage
commercial. Le repli n'est donc pas une autre source, c'est le **lit silencieux** — la vidéo se
monte, le manifeste porte l'avertissement, et `music_track` reste vide, ce qui suffit à empêcher
la publication (`RunManifest.champs_conformite_manquants`).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.core.models import Mood, PisteMusicale, licence_commerciale
from factory.core.paths import LibraryPaths
from factory.core.runs import maintenant

#: Extensions acceptées pour un fichier de piste.
EXTENSIONS = (".mp3", ".m4a", ".wav", ".ogg", ".flac")
#: Nombre de runs récents d'une chaîne sur lesquels une piste ne doit pas se répéter.
ROTATION_RUNS = 5
#: Fondu de sortie du lit, en secondes.
FONDU_SORTIE_S = 2.5
#: Fondu d'entrée du lit, en secondes — un lit qui démarre à plein niveau se remarque.
FONDU_ENTREE_S = 1.5


class PisteInvalide(RuntimeError):
    """Une piste de la bibliothèque n'est pas exploitable ; le message dit laquelle et pourquoi."""


@dataclass(frozen=True)
class Piste:
    """Une piste de `workspace/library/music/`, manifeste lu et licence vérifiée."""

    slug: str
    fichier: Path
    mood: Mood
    titre: str
    artiste: str | None
    source: str
    licence: str
    licence_url: str | None
    attribution_requise: bool
    credit_line: str | None
    bpm: int | None
    telechargee_depuis: str | None

    @property
    def asset_id(self) -> str:
        """Identifiant en base : préfixé pour ne pas entrer en collision avec une image."""
        return f"music:{self.slug}"

    def vers_manifeste(self, channel_id: str) -> PisteMusicale:
        """Bloc `decisions.music_track` du manifeste (`INTERFACES.md`, `CONFORMITE.md` § 10)."""
        return PisteMusicale(
            track_title=self.titre,
            source=self.source,
            author=self.artiste,
            licence=self.licence,
            licence_url=self.licence_url,
            attribution_required=self.attribution_requise,
            credit_line=self.credit_line,
            downloaded_from_channel=self.telechargee_depuis or channel_id,
        )


def _licence_refusee(licence: str) -> bool:
    """« ND » et « sampling » sont éliminatoires en plus de « NC » (`CONFORMITE.md` § 7).

    `licence_commerciale()` ne connaît que « NC » : elle laisserait passer un CC-BY-ND, qui
    interdit pourtant l'œuvre dérivée qu'est un montage.
    """
    normalisee = licence.upper().replace("_", "-").replace(" ", "-")
    jetons = {j for j in normalisee.split("-") if j}
    return "ND" in jetons or "NODERIVS" in jetons or "SAMPLING" in normalisee


def _lire_manifeste(manifeste: Path) -> dict:
    try:
        return json.loads(manifeste.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erreur:
        raise PisteInvalide(f"{manifeste.name} : manifeste illisible — {erreur}") from erreur


def charger_bibliotheque(racine: Path | None = None) -> tuple[list[Piste], list[str]]:
    """Lit `workspace/library/music/`. Rend les pistes valides **et** les refus, en clair.

    Un refus n'interrompt pas le chargement : une bibliothèque de dix pistes dont une est mal
    déclarée doit rendre les neuf autres, et dire laquelle manque.
    """
    dossier = LibraryPaths.depuis_racine(racine).music
    pistes: list[Piste] = []
    refus: list[str] = []
    if not dossier.is_dir():
        return pistes, refus

    audios = sorted(f for f in dossier.iterdir() if f.suffix.lower() in EXTENSIONS)
    for audio in audios:
        manifeste = audio.with_suffix(".json")
        if not manifeste.exists():
            refus.append(f"{audio.name} : aucun {manifeste.name} — piste sans licence, écartée")
            continue
        try:
            donnees = _lire_manifeste(manifeste)
            licence = str(donnees.get("licence", "")).strip()
            if not licence:
                raise PisteInvalide(f"{manifeste.name} : champ `licence` vide")
            if not licence_commerciale(licence) or _licence_refusee(licence):
                raise PisteInvalide(
                    f"{manifeste.name} : licence {licence} refusée par CONFORMITE.md § 7"
                )
            attribution = bool(donnees.get("attribution_requise", donnees.get("attribution_required")))
            credit = donnees.get("credit_line") or donnees.get("attribution_line")
            if attribution and not credit:
                raise PisteInvalide(f"{manifeste.name} : attribution exigée sans `credit_line`")
            url = str(donnees.get("licence_url", "") or "").strip()
            if not url:
                # `library_assets.licence_url` est NOT NULL, et `CONFORMITE.md` § 7 exige
                # « URL de licence » par piste : une licence sans source vérifiable ne se
                # défend pas en cas de réclamation.
                raise PisteInvalide(f"{manifeste.name} : `licence_url` vide")
            mood = str(donnees.get("mood", "")).strip()
            if mood not in ("calme", "tension", "curieux", "energique", "sombre"):
                raise PisteInvalide(f"{manifeste.name} : mood {mood!r} inconnu")
            pistes.append(
                Piste(
                    slug=audio.stem,
                    fichier=audio,
                    mood=mood,  # type: ignore[arg-type]
                    titre=str(donnees.get("titre") or donnees.get("title") or audio.stem),
                    artiste=donnees.get("artiste") or donnees.get("artist"),
                    source=str(donnees.get("source", "inconnue")),
                    licence=licence,
                    licence_url=url,
                    attribution_requise=attribution,
                    credit_line=credit,
                    bpm=int(donnees["bpm"]) if donnees.get("bpm") else None,
                    telechargee_depuis=donnees.get("telechargee_depuis")
                    or donnees.get("downloaded_from_channel"),
                )
            )
        except PisteInvalide as erreur:
            refus.append(str(erreur))
    return pistes, refus


def indexer(conn: sqlite3.Connection, pistes: list[Piste], racine: Path | None = None) -> int:
    """Inscrit les pistes dans `library_assets` (`kind = "music"`). Idempotent."""
    from factory.core.paths import racine_projet

    base = racine or racine_projet()
    horodatage = maintenant()
    for piste in pistes:
        try:
            chemin = str(piste.fichier.resolve().relative_to(base))
        except ValueError:
            chemin = str(piste.fichier)
        conn.execute(
            """
            INSERT INTO library_assets (
                asset_id, kind, layer, path, provider, licence, licence_url,
                attribution_line, has_text, lang, keywords, created_at
            ) VALUES (?, 'music', 'background', ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                path = excluded.path, licence = excluded.licence,
                licence_url = excluded.licence_url,
                attribution_line = excluded.attribution_line,
                keywords = excluded.keywords
            """,
            (
                piste.asset_id, chemin, piste.source, piste.licence, piste.licence_url,
                piste.credit_line, piste.mood, horodatage,
            ),
        )
    conn.commit()
    return len(pistes)


def _pistes_recentes(conn: sqlite3.Connection, channel_id: str) -> set[str]:
    """Pistes employées par les `ROTATION_RUNS` derniers runs de la chaîne."""
    lignes = conn.execute(
        """
        SELECT asset_id FROM library_uses
        WHERE channel_id = ? AND video_id IN (
            SELECT video_id FROM library_uses WHERE channel_id = ?
            GROUP BY video_id ORDER BY MAX(used_at) DESC LIMIT ?
        ) AND asset_id LIKE 'music:%'
        """,
        (channel_id, channel_id, ROTATION_RUNS),
    ).fetchall()
    return {ligne[0] for ligne in lignes}


def choisir(
    pistes: list[Piste], mood: Mood, conn: sqlite3.Connection | None = None,
    channel_id: str | None = None,
) -> tuple[Piste | None, str]:
    """Choisit une piste pour ce mood, hors des `ROTATION_RUNS` derniers runs de la chaîne.

    Rend la piste **et le motif du choix**, parce qu'un repli silencieux sur un autre mood est
    exactement le genre de décision qu'on ne retrouve plus trois semaines après.
    """
    if not pistes:
        return None, "bibliothèque vide"
    recentes = _pistes_recentes(conn, channel_id) if conn is not None and channel_id else set()

    du_mood = [p for p in pistes if p.mood == mood]
    if du_mood:
        libres = [p for p in du_mood if p.asset_id not in recentes]
        if libres:
            return libres[0], f"mood {mood}, hors des {ROTATION_RUNS} derniers runs"
        return du_mood[0], (
            f"mood {mood} ; les {len(du_mood)} piste(s) de ce mood ont toutes servi "
            f"dans les {ROTATION_RUNS} derniers runs — rotation relâchée"
        )

    libres = [p for p in pistes if p.asset_id not in recentes]
    repli = libres or pistes
    return repli[0], f"aucune piste de mood {mood} — repli sur {repli[0].mood}"


def enregistrer_usage(
    conn: sqlite3.Connection, piste: Piste, video_id: str, channel_id: str
) -> None:
    """Inscrit l'emploi de la piste dans `library_uses` et incrémente son compteur."""
    conn.execute(
        "INSERT OR REPLACE INTO library_uses (asset_id, video_id, channel_id, used_at) "
        "VALUES (?, ?, ?, ?)",
        (piste.asset_id, video_id, channel_id, maintenant()),
    )
    conn.execute(
        "UPDATE library_assets SET uses = uses + 1, last_used_at = ? WHERE asset_id = ?",
        (maintenant(), piste.asset_id),
    )
    conn.commit()


# --------------------------------------------------------------------------------------
# Mise à la durée
# --------------------------------------------------------------------------------------


def preparer_lit(
    piste: Piste, duree_s: float, sortie: Path, sample_rate: int = 48000,
    fondu_entree_s: float = FONDU_ENTREE_S, fondu_sortie_s: float = FONDU_SORTIE_S,
    journal=None,
) -> float:
    """Met la piste à `duree_s` — bouclée si trop courte, coupée si trop longue — avec fondus.

    `aloop=loop=-1:size=...` boucle l'intégralité du fichier : `size` se compte en **échantillons**
    et doit donc être calculé après le rééchantillonnage, sinon une piste à 44,1 kHz bouclée à
    48 kHz se répète avant sa fin. `atrim` coupe ensuite à la durée exacte.
    """
    from factory.audio import duree as duree_audio
    from factory.video import lancer_ffmpeg

    longueur = duree_audio(piste.fichier)
    echantillons = max(1, int(round(longueur * sample_rate)))
    debut_fondu = max(0.0, duree_s - fondu_sortie_s)
    filtre = (
        f"aresample={sample_rate},"
        + (f"aloop=loop=-1:size={echantillons}," if longueur < duree_s else "")
        + f"atrim=0:{duree_s:.3f},asetpts=N/SR/TB,"
        f"afade=t=in:st=0:d={fondu_entree_s:.3f},"
        f"afade=t=out:st={debut_fondu:.3f}:d={fondu_sortie_s:.3f},"
        "aformat=sample_fmts=s16:channel_layouts=stereo"
    )
    lancer_ffmpeg(
        ["-i", str(piste.fichier), "-af", filtre, "-c:a", "pcm_s16le", str(sortie)],
        journal=journal,
    )
    return duree_audio(sortie)


def lit_silencieux(duree_s: float, sortie: Path, sample_rate: int = 48000, journal=None) -> float:
    """Lit muet à la durée voulue — le repli quand aucune piste sous licence n'est disponible."""
    from factory.audio import duree as duree_audio
    from factory.video import lancer_ffmpeg

    lancer_ffmpeg(
        [
            "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=stereo",
            "-t", f"{duree_s:.3f}", "-c:a", "pcm_s16le", str(sortie),
        ],
        journal=journal,
    )
    return duree_audio(sortie)
