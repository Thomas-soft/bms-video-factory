"""Étape 12.2 — prompt de charte, clés de bibliothèque, couches de parallaxe, moteur illustré.

Aucun test ne charge de modèle : ce qui se mesure ici est la **mécanique** (déterminisme des
graines, clés de cache, cumul des couches, règles de réutilisation). La qualité des pixels se
juge à l'œil et se consigne dans le manifeste, pas dans une assertion.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest
from PIL import Image

from factory.assets import images, parallax
from factory.core import config as config_module
from factory.core import db
from factory.core.models import Channel, Style
from factory.core.paths import racine_projet
from factory.styles import MOTEURS_PLANIFIES, STYLE_ENGINES
from factory.styles.illustre import IllustreEngine


@pytest.fixture(scope="module")
def configuration():
    """La configuration **réelle** du dépôt : la charte y est un livrable, pas un décor de test."""
    return config_module.charger(racine_projet(), strict=False)


@pytest.fixture(scope="module")
def channel_science_fr(configuration) -> Channel:
    return configuration.get_channel("bms-science-fr")


@pytest.fixture(scope="module")
def style_illustre(configuration) -> Style:
    return configuration.styles["illustre"]


# --------------------------------------------------------------------------------------
# Prompt de charte
# --------------------------------------------------------------------------------------

def test_prompt_encadre_intention(channel_science_fr: Channel) -> None:
    """Le prompt est préfixe + intention + cadrage + suffixe, dans cet ordre."""
    prompt = images.construire_prompt(channel_science_fr, "un cristal de sucre")
    assert prompt.startswith(channel_science_fr.charte.style_prefix.strip().rstrip(","))
    assert "un cristal de sucre" in prompt
    assert prompt.endswith(channel_science_fr.charte.style_suffix.strip().lstrip(","))
    assert channel_science_fr.charte.framing.background in prompt
    assert channel_science_fr.charte.framing.subject_scale in prompt


def test_prompt_rupture_change_le_cadre(channel_science_fr: Channel) -> None:
    """Une rupture ajoute un cadrage large : même style, autre cadre et autre fond."""
    normal = images.construire_prompt(channel_science_fr, "un cristal de sucre")
    rupture = images.construire_prompt(channel_science_fr, "un cristal de sucre", rupture=True)
    assert normal != rupture
    assert "wide establishing framing" in rupture


def test_charte_sans_style_refuse(channel_science_fr: Channel) -> None:
    """Un moteur qui génère des images ne choisit pas le style à la place de la charte."""
    nue = channel_science_fr.model_copy(deep=True)
    nue.charte.style_prefix = ""
    with pytest.raises(images.CharteIncomplete):
        images.construire_prompt(nue, "un cristal de sucre")


# --------------------------------------------------------------------------------------
# Clés et graines
# --------------------------------------------------------------------------------------

def test_graine_stable_entre_processus() -> None:
    """`sha256`, jamais `hash()` : la même paire rend la même graine à chaque exécution."""
    assert images.graine_de("video-42", "shot_07") == images.graine_de("video-42", "shot_07")
    assert images.graine_de("video-42", "shot_07") != images.graine_de("video-42", "shot_08")
    assert images.graine_mflux(images.graine_de("video-42", "shot_07")) < 2**32


def test_nouvel_essai_change_la_graine() -> None:
    """Une image inexploitable est rejouée avec un autre bruit, pas avec le même."""
    assert images.graine_de("v", "shot_00", 0) != images.graine_de("v", "shot_00", 1)


def test_normalisation_confond_ce_qui_doit_l_etre() -> None:
    """Accents, casse et ponctuation sortent de la clé ; les mots y restent."""
    assert images.normaliser("Un cristal de sucre…") == images.normaliser("un cristal de sucre")
    assert images.normaliser("a — b") == "a b"
    assert images.normaliser("plan large") != images.normaliser("plan serré")


def test_cle_depend_de_la_charte_et_du_format() -> None:
    """Changer de palette ou de format doit produire une image neuve, pas ressortir l'ancienne."""
    base = images.cle_bibliotheque("un chat", "illustre", "2026.09.1-fr", "1280x720")
    assert base != images.cle_bibliotheque("un chat", "illustre", "2026.10.1-fr", "1280x720")
    assert base != images.cle_bibliotheque("un chat", "illustre", "2026.09.1-fr", "1024x576")
    assert base == images.cle_bibliotheque("Un chat.", "illustre", "2026.09.1-fr", "1280x720")


# --------------------------------------------------------------------------------------
# Règles de réutilisation
# --------------------------------------------------------------------------------------

@pytest.fixture()
def base(tmp_path) -> sqlite3.Connection:
    conn = db.ouvrir(tmp_path / "factory.db")
    return conn


def test_rejeu_du_meme_run_reutilise_toujours(base, channel_science_fr: Channel) -> None:
    """Le cooldown ne compte que les **autres** runs — sinon « 2ᵉ exécution, 0 génération » est mort."""
    base.execute(
        "INSERT INTO library_uses VALUES ('abc', 'run-1', ?, '2026-09-16T10:00:00Z')",
        (channel_science_fr.id,),
    )
    libre, motif = images._reutilisable(base, "abc", channel_science_fr, "run-1")
    assert libre, motif


def test_cooldown_ecarte_un_run_recent(base, channel_science_fr: Channel) -> None:
    """Employé dans les `cooldown_videos` derniers runs de la chaîne, l'asset n'est pas resservi."""
    base.execute(
        "INSERT INTO library_uses VALUES ('abc', 'run-1', ?, '2026-09-16T10:00:00Z')",
        (channel_science_fr.id,),
    )
    libre, motif = images._reutilisable(base, "abc", channel_science_fr, "run-2")
    assert not libre
    assert "derniers runs" in motif


def test_plafond_d_emplois_par_chaine(base, channel_science_fr: Channel) -> None:
    """`max_uses_per_channel` est un plafond dur, indépendant du cooldown."""
    for numero in range(channel_science_fr.library.max_uses_per_channel):
        base.execute(
            "INSERT INTO library_uses VALUES ('abc', ?, ?, '2026-09-16T10:00:00Z')",
            (f"vieux-{numero}", channel_science_fr.id),
        )
    libre, motif = images._reutilisable(base, "abc", channel_science_fr, "run-neuf")
    assert not libre
    assert "max_uses_per_channel" in motif


# --------------------------------------------------------------------------------------
# Parallaxe
# --------------------------------------------------------------------------------------

def _image_et_profondeur(tmp_path):
    """Une image de test et une profondeur **inverse** (clair = proche), comme Depth Anything."""
    image = tmp_path / "img.png"
    Image.new("RGB", (320, 180), (40, 90, 140)).save(image)
    carte = np.zeros((180, 320), dtype=np.uint8)
    carte[:, 160:] = 255          # moitié droite au premier plan
    carte[:, 80:160] = 128
    profondeur = tmp_path / "depth.png"
    Image.fromarray(carte, mode="L").save(profondeur)
    return image, profondeur


def test_couches_cumulatives_sans_trou(tmp_path) -> None:
    """Le fond est plein et chaque couche porte tout ce qui est plus proche qu'elle."""
    image, profondeur = _image_et_profondeur(tmp_path)
    couches = parallax.couches(image, profondeur, tmp_path / "out", taille=(320, 180))
    assert len(couches) == 3
    # En `int`, pas en `uint8` : `0 - 1` y vaut 255 et le cumul semblerait rompu partout.
    alphas = [
        np.asarray(Image.open(c).convert("RGBA"))[..., 3].astype(int) for c in couches
    ]
    assert alphas[0].min() == 255, "le fond doit être opaque partout, sinon la parallaxe troue"
    # Cumulatif : ce que la couche 2 montre, la couche 1 le montre aussi.
    assert (alphas[1] >= alphas[2]).all()


def test_alpha_adouci_aux_bords(tmp_path) -> None:
    """Un seuil net crénèle : l'alpha doit passer par des valeurs intermédiaires."""
    image, profondeur = _image_et_profondeur(tmp_path)
    couches = parallax.couches(image, profondeur, tmp_path / "out", taille=(320, 180))
    alpha = np.asarray(Image.open(couches[2]).convert("RGBA"))[..., 3]
    assert ((alpha > 10) & (alpha < 245)).any(), "aucun pixel de transition : bord crénelé"


def test_derive_independante_de_la_duree(tmp_path) -> None:
    """Un plan long et un plan court parcourent la même distance, pas la même vitesse."""
    image, profondeur = _image_et_profondeur(tmp_path)
    couches = parallax.couches(image, profondeur, tmp_path / "out", taille=(320, 180))
    court = parallax.chaine_parallaxe(couches, 3.0, "parallax", 2)
    long = parallax.chaine_parallaxe(couches, 12.0, "parallax", 2)
    vitesse_courte = float(court.split("+")[-2].split("*t")[0].split("'")[-1])
    vitesse_longue = float(long.split("+")[-2].split("*t")[0].split("'")[-1])
    assert abs(vitesse_courte * 3.0 - vitesse_longue * 12.0) < 0.01


def test_plan_court_bascule_en_ken_burns(style_illustre) -> None:
    """Sous 2 s, un glissement de couches ne se lit pas : Ken Burns par construction."""
    moteur = IllustreEngine(style=style_illustre)
    court = _plan(duree=1.5)
    long = _plan(duree=6.0)
    assert not moteur._veut_parallaxe(court)
    assert moteur._veut_parallaxe(long)


def _plan(duree: float):
    from factory.core.models import AssetRequest, Shot

    return Shot(
        id="shot_00", segment_id="seg_00", start_s=0.0, end_s=duree, duration_s=duree,
        visual_intent="un cristal de sucre", on_screen_text=None,
        asset_request=AssetRequest(type="image", prompt_or_keywords="un cristal de sucre"),
        motion="parallax", transition_in="cut", seed=12345,
    )


# --------------------------------------------------------------------------------------
# Registre
# --------------------------------------------------------------------------------------

def test_moteur_illustre_est_livre() -> None:
    """Le moteur est au registre et n'est plus annoncé comme planifié."""
    assert STYLE_ENGINES["illustre_anime"] is IllustreEngine
    assert "illustre_anime" not in MOTEURS_PLANIFIES
