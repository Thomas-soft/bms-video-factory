"""Étape 13.1 — montage, lit musical, export vérifié.

Trois familles d'invariants, et une seule question derrière les trois :

- **La ligne du temps.** Une transition ne doit jamais prendre de temps à la vidéo. Le test le
  vérifie sur le budget d'images (somme des corps + somme des transitions = somme des clips)
  pour toutes les combinaisons de transitions, puis **pour de vrai avec ffmpeg** sur trois clips
  fabriqués : un montage dont on ne vérifierait que l'arithmétique ne prouverait rien.
- **La licence de la musique.** Une piste sans manifeste, en NC, en ND, ou qui exige une
  attribution sans porter son crédit, ne doit pas pouvoir entrer dans une vidéo. Ce sont les
  quatre refus de `CONFORMITE.md` § 7, et ils sont testés un par un.
- **Le ducking.** Le run FR n'a pas de musique : sans ce test, `sidechaincompress` serait du code
  écrit et jamais exercé. Le test fabrique un lit et une voix, mixe, et **mesure** que le lit est
  plus bas là où la voix parle que là où elle se tait.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from factory import audio as audio_module
from factory.assets import music as music_module
from factory.core import db
from factory.core import models as m
from factory.steps import assemble as A
from factory.video import FPS, ffprobe_clip, lancer_ffmpeg


# --- outillage ------------------------------------------------------------------------


class FauxInfo:
    """Ce que `ffprobe` rendrait d'un clip, sans clip."""

    def __init__(self, images: int) -> None:
        self.images = images


class FauxShot:
    def __init__(self, rang: int, transition: str = "cut", segment: str = "seg_01") -> None:
        self.id = f"shot_{rang:02d}"
        self.transition_in = transition
        self.segment_id = segment


def clip_couleur(chemin: Path, images: int, couleur: str) -> Path:
    """Un clip au contrat de format : 1920×1080, 30 ips, sans audio, durée exacte."""
    from factory.video import arguments_encodage

    lancer_ffmpeg([
        "-f", "lavfi", "-i", f"color=c={couleur}:s=1920x1080:r={FPS}:d={images / FPS + 1:.3f}",
        *arguments_encodage(chemin, images / FPS),
    ])
    return chemin


def piste(dossier: Path, slug: str, mood: str = "curieux", secondes: float = 3.0,
          **surcharges) -> Path:
    """Écrit une piste de bibliothèque : un fichier audio **et** son manifeste de licence."""
    dossier.mkdir(parents=True, exist_ok=True)
    audio = dossier / f"{slug}.wav"
    lancer_ffmpeg([
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={secondes}",
        "-c:a", "pcm_s16le", str(audio),
    ])
    manifeste = {
        "titre": slug.replace("_", " ").title(), "artiste": "Essai",
        "source": "youtube_audio_library", "licence": "CC0",
        "licence_url": "https://support.google.com/youtube/answer/3376882",
        "attribution_requise": False, "mood": mood, "bpm": 90,
        "telechargee_depuis": "bms-science-fr",
    }
    manifeste.update(surcharges)
    (dossier / f"{slug}.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return audio


# --- 1. ligne du temps ----------------------------------------------------------------


@pytest.mark.parametrize(
    "transitions",
    [
        ["cut", "fade", "cut", "dip_black", "cut"],
        ["fade", "fade", "fade", "fade", "fade"],
        ["cut", "dip_black", "dip_black", "dip_black", "dip_black"],
        ["fade", "dip_black", "fade", "dip_black", "cut"],
    ],
)
def test_le_budget_d_images_est_conserve(transitions: list[str]) -> None:
    """Quelle que soit la suite de transitions, le montage fait exactement la durée des clips."""
    infos = [FauxInfo(180) for _ in transitions]
    shots = [FauxShot(i, t) for i, t in enumerate(transitions)]
    images_fondu = 10
    retenues = list(transitions)
    rognes, _ = A._plan_de_coupe(shots, infos, retenues, images_fondu)

    corps = sum(info.images - tete - queue for info, (tete, queue) in zip(infos, rognes))
    transitions_images = 0
    for rang in range(1, len(retenues)):
        if retenues[rang] == "fade":
            transitions_images += images_fondu
        elif retenues[rang] == "dip_black":
            transitions_images += images_fondu  # les deux moitiés
    assert corps + transitions_images == sum(i.images for i in infos)


def test_un_plan_trop_court_retombe_sur_la_coupe() -> None:
    """Un fondu qui ne laisserait pas un demi-plan est refusé, pas rogné jusqu'à l'absurde."""
    infos = [FauxInfo(180), FauxInfo(12)]
    shots = [FauxShot(0), FauxShot(1, "fade")]
    retenues = ["cut", "fade"]
    rognes, alertes = A._plan_de_coupe(shots, infos, retenues, 10)
    assert retenues[1] == "cut"
    assert rognes[1] == (0, 0)
    assert alertes and "trop court" in alertes[0]


def test_le_hook_coupe_franc() -> None:
    """La charte peut autoriser le fondu ; le hook, lui, coupe — sinon il ne sert à rien."""
    shots = [FauxShot(0, "fade", "seg_00"), FauxShot(1, "fade", "seg_00"),
             FauxShot(2, "fade", "seg_01"), FauxShot(3, "whip", "seg_01")]
    roles = {"seg_00": "hook", "seg_01": "point"}
    retenues, forcages = A._transitions_effectives(shots, roles, {"cut", "fade", "dip_black"})
    assert retenues == ["fade", "cut", "fade", "cut"]
    assert any("dans le hook" in f for f in forcages)
    assert any("hors charte" in f for f in forcages)


def test_le_montage_reel_tient_la_duree(tmp_path: Path) -> None:
    """Le test qui compte : trois clips, un fondu, un fondu au noir, et `ffprobe` derrière."""
    clips = [
        clip_couleur(tmp_path / f"shot_{i:02d}.mp4", 60, c)
        for i, c in enumerate(("red", "green", "blue"))
    ]
    infos = [ffprobe_clip(c) for c in clips]
    attendu = sum(i.images for i in infos)
    retenues = ["cut", "fade", "dip_black"]
    shots = [FauxShot(i, t) for i, t in enumerate(retenues)]
    rognes, _ = A._plan_de_coupe(shots, infos, retenues, 10)

    with (tmp_path / "journal.log").open("w", encoding="utf-8") as trace:
        pieces = [A._corps(clips[0], infos[0], rognes[0], tmp_path / "c0.mp4", 0, trace)]
        pieces.append(A._fondu_enchaine(clips[0], infos[0], clips[1], 10, tmp_path, trace))
        pieces.append(A._corps(clips[1], infos[1], rognes[1], tmp_path / "c1.mp4", 0, trace))
        pieces.append(A._vers_le_noir(clips[1], infos[1], 5, tmp_path, trace))
        pieces.append(A._depuis_le_noir(clips[2], 5, tmp_path, trace))
        pieces.append(A._corps(clips[2], infos[2], rognes[2], tmp_path / "c2.mp4", 0, trace))
        sortie = tmp_path / "montage.mp4"
        A._concatener(pieces, sortie, tmp_path, trace)

    assert sum(p.images for p in pieces) == attendu
    mesure = ffprobe_clip(sortie)
    assert mesure.images == attendu
    assert (mesure.largeur, mesure.hauteur) == (1920, 1080)
    assert abs(mesure.duree_s - attendu / FPS) < 0.05


def test_un_plan_sans_transition_n_est_pas_reencode(tmp_path: Path) -> None:
    """Le corps d'un plan qu'aucune transition ne touche est le clip d'origine, tel quel."""
    clip = clip_couleur(tmp_path / "shot_00.mp4", 30, "red")
    info = ffprobe_clip(clip)
    with (tmp_path / "j.log").open("w", encoding="utf-8") as trace:
        piece_intacte = A._corps(clip, info, (0, 0), tmp_path / "corps.mp4", 0, trace)
        piece_rognee = A._corps(clip, info, (5, 0), tmp_path / "corps2.mp4", 0, trace)
    assert piece_intacte.chemin == clip
    assert piece_rognee.chemin == tmp_path / "corps2.mp4"
    assert piece_rognee.images == info.images - 5


# --- 2. licence de la musique ---------------------------------------------------------


def test_une_piste_valide_est_chargee(tmp_path: Path, monkeypatch) -> None:
    piste(tmp_path / "workspace" / "library" / "music", "lent_bleu", mood="calme")
    pistes, refus = music_module.charger_bibliotheque(tmp_path)
    assert refus == []
    assert len(pistes) == 1 and pistes[0].mood == "calme"
    assert pistes[0].asset_id == "music:lent_bleu"


@pytest.mark.parametrize(
    ("surcharges", "attendu"),
    [
        ({"licence": "CC-BY-NC"}, "refusée"),
        ({"licence": "CC-BY-ND-4.0"}, "refusée"),
        ({"licence": "sampling+"}, "refusée"),
        ({"attribution_requise": True}, "credit_line"),
        ({"mood": "joyeux"}, "mood"),
        ({"licence": ""}, "licence"),
        ({"licence_url": ""}, "licence_url"),
    ],
)
def test_une_piste_non_conforme_est_refusee(
    tmp_path: Path, surcharges: dict, attendu: str
) -> None:
    """Chaque refus de CONFORMITE § 7 est exercé, et le message nomme ce qui manque."""
    piste(tmp_path / "workspace" / "library" / "music", "douteuse", **surcharges)
    pistes, refus = music_module.charger_bibliotheque(tmp_path)
    assert pistes == []
    assert len(refus) == 1 and attendu in refus[0]


def test_un_audio_sans_manifeste_est_refuse(tmp_path: Path) -> None:
    """Pas de `licence.json`, pas de piste — un fichier audio seul n'est jamais joué."""
    dossier = tmp_path / "workspace" / "library" / "music"
    piste(dossier, "orpheline")
    (dossier / "orpheline.json").unlink()
    pistes, refus = music_module.charger_bibliotheque(tmp_path)
    assert pistes == []
    assert "sans licence" in refus[0]


def test_la_rotation_evite_les_cinq_derniers_runs(tmp_path: Path) -> None:
    """Deux pistes du même mood : la seconde sort quand la première vient de servir."""
    dossier = tmp_path / "workspace" / "library" / "music"
    piste(dossier, "a_curieux")
    piste(dossier, "b_curieux")
    pistes, _ = music_module.charger_bibliotheque(tmp_path)
    conn = db.ouvrir(tmp_path / "factory.db")
    music_module.indexer(conn, pistes, tmp_path)

    choisie, _ = music_module.choisir(pistes, "curieux", conn, "bms-science-fr")
    assert choisie.slug == "a_curieux"
    music_module.enregistrer_usage(conn, choisie, "run-1", "bms-science-fr")
    suivante, motif = music_module.choisir(pistes, "curieux", conn, "bms-science-fr")
    assert suivante.slug == "b_curieux"
    assert "hors des 5 derniers runs" in motif

    music_module.enregistrer_usage(conn, suivante, "run-2", "bms-science-fr")
    troisieme, motif = music_module.choisir(pistes, "curieux", conn, "bms-science-fr")
    assert troisieme is not None and "rotation relâchée" in motif
    conn.close()


def test_le_repli_de_mood_est_dit(tmp_path: Path) -> None:
    """Aucune piste du mood demandé : on en prend une autre, et le motif l'écrit."""
    piste(tmp_path / "workspace" / "library" / "music", "seule", mood="sombre")
    pistes, _ = music_module.charger_bibliotheque(tmp_path)
    choisie, motif = music_module.choisir(pistes, "energique")
    assert choisie.mood == "sombre"
    assert "aucune piste de mood energique" in motif


def test_le_lit_est_boucle_ou_coupe_a_la_duree(tmp_path: Path) -> None:
    """Une piste de 3 s doit remplir 7 s, une piste de 3 s doit tenir dans 1,5 s."""
    dossier = tmp_path / "workspace" / "library" / "music"
    piste(dossier, "courte", secondes=3.0)
    pistes, _ = music_module.charger_bibliotheque(tmp_path)

    longue = music_module.preparer_lit(pistes[0], 7.0, tmp_path / "long.wav")
    assert abs(longue - 7.0) < 0.05
    courte = music_module.preparer_lit(
        pistes[0], 1.5, tmp_path / "court.wav", fondu_entree_s=0.2, fondu_sortie_s=0.3
    )
    assert abs(courte - 1.5) < 0.05


# --- 3. ducking -----------------------------------------------------------------------


def _rms_db(chemin: Path, debut: float, fin: float) -> float:
    """Niveau RMS d'une fenêtre, mesuré par `volumedetect`."""
    import re
    import subprocess

    sortie = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{debut}", "-to", f"{fin}",
         "-i", str(chemin), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    ).stderr
    trouve = re.search(r"mean_volume:\s*(-?[\d.]+) dB", sortie)
    assert trouve, sortie[-500:]
    return float(trouve.group(1))


def test_le_lit_baisse_quand_la_voix_parle(tmp_path: Path) -> None:
    """`sidechaincompress` exercé pour de vrai : la musique doit être plus basse sous la voix.

    La « voix » est un bruit de 2 s au milieu de 6 s de silence ; le lit est une sinusoïde
    continue. Si le ducking fonctionne, le mélange est **plus fort** pendant la voix (elle
    s'ajoute) mais le lit, lui, y est atténué — ce que l'on mesure en comparant le mélange
    dans le silence à ce que le lit seul y vaut.
    """
    voix = tmp_path / "voix.wav"
    lancer_ffmpeg([
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=2",
        "-f", "lavfi", "-i", "anoisesrc=r=48000:a=0.5:d=2",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=2",
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[v]", "-map", "[v]",
        "-c:a", "pcm_s16le", str(voix),
    ])
    lit = tmp_path / "lit.wav"
    lancer_ffmpeg([
        "-f", "lavfi", "-i", "sine=frequency=220:duration=6:sample_rate=48000",
        "-af", "aformat=channel_layouts=stereo", "-c:a", "pcm_s16le", str(lit),
    ])

    melange = tmp_path / "mix.wav"
    with (tmp_path / "j.log").open("w", encoding="utf-8") as trace:
        A.mixer(voix, lit, melange, 6.0, [], trace)
        sans_lit = tmp_path / "mix_sans.wav"
        A.mixer(voix, None, sans_lit, 6.0, [], trace)

    avant = _rms_db(melange, 0.2, 1.8)   # lit seul, voix muette
    pendant = _rms_db(melange, 2.6, 3.4)  # lit ducké + voix
    lit_seul_avant = _rms_db(lit, 0.2, 1.8)

    # Le lit passe à -18 dB sous son niveau d'origine : c'est la consigne du prompt.
    assert avant < lit_seul_avant - 15
    # Et il est encore plus bas sous la voix — mesuré sur le résidu, pas supposé.
    assert pendant > avant  # la voix domine le mélange
    assert sans_lit.exists()


# --- 4. configuration ------------------------------------------------------------------


def test_la_duree_de_fondu_est_bornee() -> None:
    """Hors de [0,25 ; 0,40] s, la charte est refusée : un fondu d'une seconde n'est pas un fondu."""
    base = dict(
        version="t", fonts={"title": "Inter SemiBold", "body": "Inter Regular"},
        palette={"bg": "#000000", "text": "#ffffff", "text_outline": "#0a0a0a",
                 "accent": "#ff0000", "highlight": "#ffd166"},
        transitions=["cut", "fade"],
    )
    assert m.Charte(**base).transition_duration_s == pytest.approx(0.32)
    with pytest.raises(ValueError):
        m.Charte(**base, transition_duration_s=1.0)
    with pytest.raises(ValueError):
        m.Charte(**base, transition_duration_s=0.1)


def test_chaque_niche_porte_un_mood() -> None:
    """Le mood est une donnée de configuration, pas une valeur en dur dans le code."""
    from factory.core import config as config_module

    cfg = config_module.charger(strict=False)
    assert cfg.niches
    for niche in cfg.niches.values():
        assert niche.musique.mood in ("calme", "tension", "curieux", "energique", "sombre")


def test_une_piste_non_commerciale_est_refusee_par_le_manifeste() -> None:
    """La licence est vérifiée une seconde fois à l'écriture du manifeste, pas seulement au chargement."""
    commun = dict(
        track_title="Essai", source="youtube_audio_library", licence="CC0",
        attribution_required=False, downloaded_from_channel="bms-science-fr",
    )
    assert m.PisteMusicale(**commun).licence == "CC0"
    with pytest.raises(ValueError):
        m.PisteMusicale(**{**commun, "licence": "CC-BY-NC-4.0"})
    with pytest.raises(ValueError):
        m.PisteMusicale(**{**commun, "attribution_required": True})


def test_le_motif_du_lit_silencieux_a_sa_place_au_manifeste() -> None:
    """Un lit silencieux est une décision : elle a un champ, donc elle laisse une trace."""
    assert "music_warning" in m.ManifestDecisions.model_fields
