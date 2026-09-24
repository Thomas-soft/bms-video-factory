"""Étape 17 — banques libres et moteur documentaire.

Aucun test ne touche le réseau : les réponses d'API sont posées à la main. Ce qui est vérifié
ici, ce sont les **règles de tri et de conformité**, c'est-à-dire ce qui décide si un fichier
entre ou non dans une vidéo publiée — pas la disponibilité d'une banque un jour donné.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.assets import stock
from factory.core.models import AssetRequest, Shot


def candidat(**surcharges: object) -> stock.Candidat:
    """Un candidat recevable par défaut ; chaque test ne change que ce qu'il éprouve."""
    champs: dict[str, object] = dict(
        provider="openverse", identifiant="abc", url_fichier="https://example.org/a.jpg",
        source_url="https://example.org/a", author="Anon", licence="CC0-1.0",
        licence_url="https://creativecommons.org/publicdomain/zero/1.0/",
        titre="Ruines", largeur=1920, hauteur=1080, duree_s=0.0, extension="jpg",
    )
    champs.update(surcharges)
    return stock.Candidat(**champs)  # type: ignore[arg-type]


def banque_seche(chaine: tuple[str, ...] = stock.CHAINE_DEFAUT) -> stock.BanqueStock:
    """Une banque sans disque ni réseau : seule la logique de tri est sollicitée."""
    return stock.BanqueStock(
        conn=sqlite3.connect(":memory:"), racine=Path("/tmp"), chaine=chaine,
        compteur=stock.CompteurQuota(chemin=Path("/tmp/quotas-de-test.json")),
    )


# -- ordre des fournisseurs --------------------------------------------------------------


def test_sans_cle_le_metrage_passe_devant_les_images(monkeypatch: pytest.MonkeyPatch) -> None:
    """C'est la règle qui empêche le style documentaire d'être un diaporama.

    Sans `PEXELS_KEY` ni `PIXABAY_KEY`, l'ordre nominal laisse Openverse — qui n'indexe que des
    images — devant les deux seules banques de vidéo restantes. Openverse répond presque
    toujours : il servirait donc **tous** les plans, et le style sortirait en photographies
    animées, doublon visuel du style illustré (`STATE.md`, 18/09/2026).
    """
    monkeypatch.delenv("PEXELS_KEY", raising=False)
    monkeypatch.delenv("PIXABAY_KEY", raising=False)
    actifs = banque_seche().fournisseurs_actifs()
    assert actifs == ["internet_archive", "nasa", "openverse"]


def test_avec_une_cle_video_l_ordre_nominal_est_respecte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le jour où Thomas pose `PEXELS_KEY`, le reclassement s'efface : Pexels est meilleur."""
    monkeypatch.setenv("PEXELS_KEY", "xxx")
    monkeypatch.delenv("PIXABAY_KEY", raising=False)
    actifs = banque_seche().fournisseurs_actifs()
    assert actifs == ["pexels", "openverse", "internet_archive", "nasa"]


# -- licences ----------------------------------------------------------------------------


@pytest.mark.parametrize("licence", ["CC-BY-NC-4.0", "CC-BY-ND-2.0", "CC-BY-SA-4.0"])
def test_les_licences_contaminantes_sont_refusees(licence: str) -> None:
    """NC et ND sont éliminatoires par définition, SA par décision de projet."""
    assert not stock._licence_ok(licence)


@pytest.mark.parametrize("licence", ["CC0-1.0", "PDM-1.0", "CC-BY-4.0", "domaine-public-US"])
def test_les_licences_employables_passent(licence: str) -> None:
    assert stock._licence_ok(licence)


def test_cc0_et_pdm_ne_sont_pas_etiquetes_comme_des_licences_cc() -> None:
    """`CC-CC0-1.0` n'existe pas. Un registre de licences ne porte pas de libellé inventé."""
    assert stock._etiquette_licence_cc("cc0", "1.0") == "CC0-1.0"
    assert stock._etiquette_licence_cc("pdm", "1.0") == "PDM-1.0"
    assert stock._etiquette_licence_cc("by", "4.0") == "CC-BY-4.0"


# -- droit à l'image ---------------------------------------------------------------------


def test_une_personne_annoncee_par_le_titre_est_ecartee() -> None:
    assert stock._annonce_une_personne(candidat(titre="Portrait of a young woman"))


def test_un_mot_qui_contient_un_mot_de_personne_ne_declenche_pas() -> None:
    """Comparaison mot à mot : « Roman » contient « man » et doit passer."""
    assert not stock._annonce_une_personne(candidat(titre="Roman aqueduct at dawn"))


# -- critères de montage -----------------------------------------------------------------


def test_une_video_plus_courte_que_son_plan_est_refusee() -> None:
    recevable, motif = banque_seche()._recevable(
        candidat(extension="mp4", duree_s=4.0, largeur=1920, hauteur=1080), duree_min_s=7.0
    )
    assert not recevable and "4.0 s" in motif


def test_une_image_en_4_3_est_acceptee_mais_pas_une_video() -> None:
    """Une image 4:3 se recadre en 16:9 avec la marge du Ken Burns ; une vidéo, non."""
    image = candidat(largeur=4000, hauteur=3000)
    video = candidat(largeur=4000, hauteur=3000, extension="mp4", duree_s=30.0)
    assert banque_seche()._recevable(image, 7.0)[0]
    assert not banque_seche()._recevable(video, 7.0)[0]


def test_le_sous_1080p_est_refuse() -> None:
    recevable, motif = banque_seche()._recevable(candidat(largeur=1280, hauteur=720), 7.0)
    assert not recevable and "sous 1080p" in motif


# -- attribution -------------------------------------------------------------------------


def test_la_ligne_composee_par_la_banque_prime_sur_le_gabarit_local() -> None:
    """Openverse compose le texte que CC exige, version de licence comprise."""
    officiel = '"Forêt" by barnyz is licensed under CC BY 4.0.'
    assert stock._ligne_attribution(candidat(attribution=officiel)) == officiel


def test_pixabay_n_exige_aucune_attribution() -> None:
    assert stock._ligne_attribution(candidat(provider="pixabay")) is None


def test_la_nasa_est_creditee_nommement() -> None:
    ligne = stock._ligne_attribution(candidat(provider="nasa", source_url="https://n.gov/x"))
    assert ligne == "Crédit : NASA — https://n.gov/x"


# -- quotas ------------------------------------------------------------------------------


def test_le_seau_journalier_ferme_openverse_avant_le_seau_horaire() -> None:
    """200/jour en anonyme : c'est ce plafond-là qui mord sur un run de 110 plans."""
    compteur = stock.CompteurQuota(chemin=Path("/tmp/quotas-de-test.json"))
    for _ in range(stock.QUOTAS["openverse"]["jour"] or 0):
        compteur.enregistrer("openverse")
    assert not compteur.disponible("openverse")
    assert compteur.resume()["openverse"]["heure"] < (stock.QUOTAS["openverse"]["heure"] or 0)


# -- moteur documentaire -------------------------------------------------------------------


def test_la_course_du_pan_est_exprimee_dans_le_repere_surechantillonne() -> None:
    """Le défaut mesuré à l'étape 16 sur `illustre.py`, qui ne doit pas être recopié ici.

    `zoompan` travaille sur l'image suréchantillonnée ×4 : une course calculée en pixels de
    l'image finale y vaut le quart de ce qu'elle annonce — 115 px deviennent 29 px, soit
    7,5 px/s, invisibles. Le moteur documentaire la reporte donc dans le grand repère.
    """
    from factory import video
    from factory.core.config import charger
    from factory.styles.documentaire import DocumentaireEngine

    commandes: list[list[str]] = []
    style = charger(Path.cwd()).styles["documentaire"]
    moteur = DocumentaireEngine(style=style, racine=Path.cwd())
    moteur.encoder = commandes.append  # type: ignore[method-assign]
    moteur.etalonnage = lambda: "null"  # type: ignore[method-assign]
    shot = Shot(
        id="shot_00", segment_id="seg_00", start_s=0.0, end_s=6.0, duration_s=6.0,
        visual_intent="ruines", motion="pan", seed=0,
        asset_request=AssetRequest(type="stock", prompt_or_keywords="ruines"),
    )
    moteur._rendre_ken_burns(shot, Path("/tmp/a.png"), Path("/tmp/absent.png"), Path("/tmp/o.mp4"))

    filtre = next(a for a in commandes[0] if "zoompan" in a)
    course_attendue = moteur.course_ratio * video.LARGEUR * moteur.surechantillonnage * 1.6
    assert f"+{course_attendue:.1f}*on/" in filtre, filtre
    # Et la vérification qui compte vraiment : la course dépasse largement le seuil de
    # visibilité. En deçà de ~100 px de sortie sur un plan, le banc mesure un plan figé.
    assert course_attendue / 4 > 100


# -- attribution : le plafond de description --------------------------------------------


def test_cent_credits_cc_by_ne_sont_jamais_coupes_au_milieu_d_un_nom() -> None:
    """Cas que seul le style documentaire produit, et qui ne pouvait pas exister avant.

    Cent images générées partagent **une** ligne de crédit ; cent photographies CC-BY en
    portent cent. Le `[:5000]` d'origine tranchait alors dans le bloc de crédits, donc dans le
    nom d'un auteur — et une attribution CC-BY coupée en deux n'est pas une imperfection de
    mise en page, c'est un manquement à la licence.
    """
    from factory.editorial import seo as M

    credits = [
        f'"Photographie numéro {n}" par Auteur Numéro {n} est sous licence CC BY 4.0. '
        f"Pour lire la licence, voir https://creativecommons.org/licenses/by/4.0/ — "
        f"https://exemple.org/oeuvre/{n}"
        for n in range(100)
    ]
    blocs = M.BlocsDescription(
        hook="Une accroche.", sources=[f"Source {n} — https://exemple.org/s{n}" for n in range(20)],
        attribution=credits,
    )
    texte = M.composer_description(blocs)

    assert len(texte.encode("utf-8")) <= M.DESCRIPTION_MAX_OCTETS
    lignes = [l[2:] for l in texte.splitlines() if l.startswith("— ")]
    gardees = [l for l in lignes if l in credits]
    assert gardees, "aucun crédit n'a survécu"
    # Le point qui compte : chaque crédit affiché est **entier**, aucun n'est coupé.
    for ligne in gardees:
        assert ligne in credits
    assert M.credits_omis, "des crédits ont dû être écartés et n'ont pas été comptés"
    assert len(gardees) + len(M.credits_omis) == len(credits)
    assert "autres crédits" in texte


def test_une_description_qui_tient_n_est_pas_degraissee() -> None:
    from factory.editorial import seo as M

    blocs = M.BlocsDescription(hook="Accroche.", attribution=["Crédit : NASA — https://n.gov/x"])
    texte = M.composer_description(blocs)
    assert "Crédit : NASA" in texte and "autres crédits" not in texte
