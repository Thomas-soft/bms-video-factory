"""Étape 12.1 — découpage en plans, interface `StyleEngine`, moteur « cartes ».

Deux familles d'invariants :

- **Le découpage**, testé sans ffmpeg : pavage sans trou, médiane dans la tolérance, plafond du
  hook, coupes sur frontières de mots, rupture qui change de gabarit, segment sponsor marqué.
- **Le rendu**, qui appelle ffmpeg pour de vrai sur **un** plan court : un moteur de style dont on
  ne vérifierait que la chaîne de filtres en chaîne de caractères ne prouverait rien. Le contrat
  de format est mesuré par `ffprobe`, comme en production.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from factory import video
from factory.core import models as m
from factory.core.paths import RunPaths
from factory.steps import shotlist as sl
from factory.styles import MoteurIndisponible, get_engine
from factory.styles.cartes import CartesEngine


# --- outillage ------------------------------------------------------------------------


def segment(identifiant: str, role: str = "point", texte: str | None = "TEXTE",
            rupture: m.Interrupt | None = None, sponsor: bool = False,
            boucle: str = "none") -> m.ScriptSegment:
    return m.ScriptSegment(
        id=identifiant, role=role, narration="Une phrase de narration qui tient lieu de texte.",
        on_screen_text=texte, visual_intent="un objet sur fond neutre", interrupt=rupture,
        disclosure_spoken=sponsor, open_loop=boucle,
    )


def mots(debut: float, fin: float, seg: str, pas: float = 0.4) -> list[m.WordTiming]:
    """Une suite de mots jointifs, pour que les frontières existent."""
    sortie, curseur, index = [], debut, 0
    while curseur + pas <= fin:
        sortie.append(m.WordTiming(w=f"mot{index}", start_s=round(curseur, 3),
                                   end_s=round(curseur + pas * 0.8, 3), seg=seg))
        curseur += pas
        index += 1
    return sortie


def script_de(segments: list[m.ScriptSegment]) -> m.Script:
    """Un `Script` valide : le modèle exige 2 boucles plantées et autant de résolues, que les
    segments de complément fournissent sans peser sur ce que le test mesure."""
    complement = [segment("seg_90", boucle="plant"), segment("seg_91", boucle="plant"),
                  segment("seg_92", boucle="payoff"), segment("seg_93", boucle="payoff")]
    return m.Script(
        lang="fr", hook=m.Hook(type="adresse_directe", text="Bonjour"),
        segments=[*segments, *complement],
        editorial_signature=m.SignatureEditoriale(angle="donnee_proprietaire",
                                                  elements_proprietaires=["x"]),
        word_count=30, estimated_duration_s=40.0,
    )


def charte() -> m.Charte:
    return m.Charte(
        version="test-1", fonts=m.Polices(title="Inter SemiBold", body="Inter Regular"),
        palette=m.Palette(bg="#101820", text="#ffffff", text_outline="#0a0a0a",
                          accent="#2f9e8f", highlight="#ffd166"),
        transitions=["cut", "fade", "dip_black"],
    )


def chaine() -> m.Channel:
    return m.Channel(
        id="bms-test", name="BMS Test", lang="fr", niche="science_pop", style="cartes",
        templates=["a", "b", "c"], charte=charte(), voice_id="serena_fr",
        cadence=m.Cadence(per_week_max=1, days=["tuesday"], hours_local=["18:00"],
                          jitter_min=180, timezone="Europe/Paris"),
        google_account=m.CompteGoogle(alias="bms-test", brand_account="BMS Test", owner="BMS",
                                      gcp_project="p", token_ref="secrets/tokens/bms-test.json"),
    )


def style_cartes() -> m.Style:
    return m.Style(id="cartes", engine="cartes", backend="ffmpeg", statut="retenu_v1",
                   templates=["carte-plein"], params={"card": {"marge_px": 96}})


# --- découpage -------------------------------------------------------------------------


def test_le_pavage_ne_laisse_ni_trou_ni_recouvrement() -> None:
    """Les fenêtres couvrent la piste entière : sinon les clips ne se recollent pas."""
    script = script_de([segment("seg_00", "hook"), segment("seg_01"), segment("seg_02"),
                        segment("seg_03")])
    timings = m.Timings(
        voice_id="v", engine="qwen3_tts", loudness_lufs=-14.0, true_peak_dbtp=-1.4,
        total_duration_s=40.0, segments=[
            m.SegmentVoix(id="seg_00", file="a.wav", start_s=0.0, end_s=6.0, duration_s=6.0,
                          text="a"),
            m.SegmentVoix(id="seg_01", file="b.wav", start_s=6.6, end_s=24.0, duration_s=17.4,
                          text="b"),
            m.SegmentVoix(id="seg_02", file="c.wav", start_s=24.5, end_s=33.0, duration_s=8.5,
                          text="c"),
            m.SegmentVoix(id="seg_03", file="d.wav", start_s=33.4, end_s=39.5, duration_s=6.1,
                          text="d"),
        ])
    words = m.Words(engine="whisper", fallback_reason="coverage_below_threshold", coverage=1.0,
                    wer_vs_script=0.02, wer_threshold=0.08,
                    words=mots(0, 6, "seg_00") + mots(6.6, 24, "seg_01")
                          + mots(24.5, 33, "seg_02") + mots(33.4, 39.5, "seg_03"))
    fenetres = sl.construire_fenetres(script, timings, words)
    assert [f.segment.id for f in fenetres] == ["seg_00", "seg_01", "seg_02", "seg_03"]
    assert fenetres[0].debut_s == 0.0
    assert fenetres[-1].fin_s == pytest.approx(40.0)
    for gauche, droite in zip(fenetres, fenetres[1:]):
        assert gauche.fin_s == pytest.approx(droite.debut_s)


def test_le_nombre_de_plans_rapproche_la_duree_de_la_cible() -> None:
    """C'est `nombre_de_plans` qui fixe la médiane ; la corriger après coup serait la truquer.

    Une fenêtre de 8 s pour une cible de 5,85 s n'a **aucune** découpe dans la bande (8 s est trop
    long, 2 × 4 s trop court) : la règle n'est donc pas « toujours dans la bande » mais « le plus
    près possible de la cible », et la bande est tenue dès qu'elle est tenable.
    """
    cible = 5.85
    for duree in (3.0, 8.0, 12.3, 41.0, 60.0):
        n = sl.nombre_de_plans(duree, cible)
        assert n >= 1
        meilleur = min(range(1, 40), key=lambda k: abs(duree / k - cible))
        assert abs(duree / n - cible) == pytest.approx(abs(duree / meilleur - cible), abs=1e-9)
        if any(sl.JITTER_MIN * cible <= duree / k <= sl.JITTER_MAX * cible for k in range(1, 40)):
            assert sl.JITTER_MIN * cible <= duree / n <= sl.JITTER_MAX * cible


def test_une_coupe_glisse_sur_la_frontiere_de_mot_la_plus_proche() -> None:
    frontieres = [1.0, 5.2, 9.8]
    assert sl.glisser_sur_frontiere(5.4, frontieres, 0.6) == 5.2
    # Au-delà de la fenêtre, la coupe reste où elle est : il n'y a pas de mot à respecter.
    assert sl.glisser_sur_frontiere(7.5, frontieres, 0.6) == 7.5


def test_le_jitter_est_normalise_donc_la_somme_est_exacte() -> None:
    durees = sl.decouper_sous_fenetre(10.0, 40.0, 5.85, 0.3, random.Random(7))
    assert sum(durees) == pytest.approx(30.0)
    assert len(durees) == sl.nombre_de_plans(30.0, 5.85)


def test_les_plans_du_hook_sont_plafonnes() -> None:
    plan = sl.PlanBrut(segment("seg_00", "hook"), 0.0, 9.0, True, False)
    plafonnes = sl._plafonner_hook([plan], 4.1)
    assert len(plafonnes) == 3
    assert all(p.duree_s <= 4.1 + 1e-6 for p in plafonnes)
    assert plafonnes[-1].fin_s == pytest.approx(9.0)


def test_une_rupture_pose_une_ancre_et_change_de_gabarit() -> None:
    fenetre = sl.Fenetre(segment("seg_01", rupture=m.Interrupt(type="chiffre", at_s_relative=9.0)),
                         0.0, 20.0)
    plans = sl.plans_de_fenetre(fenetre, 5.85, 3.51, 4.1, 0.0, random.Random(1), [])
    ruptures = [p for p in plans if p.rupture]
    assert len(ruptures) == 1
    assert ruptures[0].debut_s == pytest.approx(9.0, abs=0.01)
    shots = sl.mettre_au_contrat(plans, "vid", chaine(), "cartes", set(), sl.ALTERNANCE_MOUVEMENT)
    rang = next(i for i, p in enumerate(plans) if p.rupture)
    assert shots[rang].interrupt is not None
    assert shots[rang].transition_in == "dip_black"
    assert (shots[rang].asset_request.prompt_or_keywords
            != shots[rang - 1].asset_request.prompt_or_keywords)


def test_le_texte_a_l_ecran_ne_vit_que_sur_le_premier_plan_du_segment() -> None:
    plans = [sl.PlanBrut(segment("seg_01"), 0.0, 5.0, True, False),
             sl.PlanBrut(segment("seg_01"), 5.0, 10.0, False, False)]
    shots = sl.mettre_au_contrat(plans, "vid", chaine(), "cartes", set(), sl.ALTERNANCE_MOUVEMENT)
    assert shots[0].on_screen_text == "TEXTE"
    assert shots[1].on_screen_text is None
    # Un plan à texte incrusté n'est jamais réutilisable (validateur `Shot`).
    assert shots[0].asset_request.reuse_ok is False


def test_un_segment_sponsor_porte_le_drapeau_sur_tous_ses_plans() -> None:
    plans = [sl.PlanBrut(segment("seg_09", sponsor=True), 0.0, 5.0, True, False)]
    shots = sl.mettre_au_contrat(plans, "vid", chaine(), "cartes", {"seg_09"},
                                 sl.ALTERNANCE_MOUVEMENT)
    assert shots[0].is_sponsor is True


def test_la_graine_d_un_plan_est_deterministe() -> None:
    assert sl.graine_de_plan("vid", "shot_00") == sl.graine_de_plan("vid", "shot_00")
    assert sl.graine_de_plan("vid", "shot_00") != sl.graine_de_plan("vid", "shot_01")


def test_la_mediane_exclut_le_hook() -> None:
    script = script_de([segment("seg_00", "hook"), segment("seg_01")])
    plans = [sl.PlanBrut(segment("seg_00", "hook"), 0.0, 2.0, True, False),
             sl.PlanBrut(segment("seg_01"), 2.0, 8.0, True, False),
             sl.PlanBrut(segment("seg_01"), 8.0, 14.0, False, False)]
    shots = sl.mettre_au_contrat(plans, "vid", chaine(), "cartes", set(), sl.ALTERNANCE_MOUVEMENT)
    mediane, _, _, mediane_hook = sl.statistiques(shots, script)
    assert mediane == pytest.approx(6.0)
    assert mediane_hook == pytest.approx(2.0)


def test_parallax_est_refuse_sans_carte_de_profondeur() -> None:
    with pytest.raises(ValueError, match="profondeur"):
        video.filtre_zoompan("parallax", 5.0)


# --- registre des moteurs ---------------------------------------------------------------


def test_un_style_planifie_nomme_l_etape_qui_le_livrera() -> None:
    # `illustre_anime` a été livré par l'étape 12.2 : le témoin est désormais `documentaire`.
    planifie = m.Style(id="documentaire", engine="documentaire", backend="ffmpeg",
                       statut="planifie")
    with pytest.raises(MoteurIndisponible, match="17"):
        get_engine(planifie)


def test_le_moteur_cartes_est_livre_et_satisfait_le_protocole() -> None:
    moteur = get_engine(style_cartes())
    assert isinstance(moteur, CartesEngine)
    assert moteur.name == "cartes" and moteur.backend == "ffmpeg"
    assert callable(moteur.prepare_assets) and callable(moteur.render_shot)


# --- polices et calques -------------------------------------------------------------------


def test_la_police_de_charte_se_resout_en_fichier_ofl() -> None:
    police = video.resoudre_police("Inter SemiBold")
    assert police.fichier.exists() and police.graisse == "SemiBold"
    assert video.resoudre_police("Inter Regular").graisse == "Regular"


def test_une_police_absente_arrete_le_rendu_au_lieu_de_se_replier() -> None:
    with pytest.raises(FileNotFoundError, match="inconnue"):
        video.resoudre_police("Helvetica Bold")


def test_le_texte_tient_en_trois_lignes_et_dans_la_largeur() -> None:
    police = video.resoudre_police("Inter SemiBold")
    long = "UNE ACCROCHE VOLONTAIREMENT TRÈS LONGUE QUI NE TIENDRAIT JAMAIS SUR UNE SEULE LIGNE"
    fonte, lignes = video.ajuster_taille(long, police, 1200, 88, 3)
    assert len(lignes) <= 3
    assert all(fonte.getlength(ligne) <= 1200 for ligne in lignes)


# --- rendu réel --------------------------------------------------------------------------


def test_un_plan_rendu_tient_le_contrat_de_format(tmp_path: Path) -> None:
    """Un plan court, rendu par ffmpeg puis **mesuré** : 1920×1080, 30 ips, durée à ± 0,05 s."""
    chemins = RunPaths(video_id="run-test", racine=tmp_path).creer()
    shot = m.Shot(
        id="shot_00", segment_id="seg_00", start_s=0.0, end_s=1.2, duration_s=1.2,
        visual_intent="un objet", on_screen_text="TEXTE DE TEST",
        asset_request=m.AssetRequest(type="card", prompt_or_keywords="carte_centrale",
                                     reuse_ok=False),
        motion="zoom_in", transition_in="fade", seed=1234,
    )
    liste = m.Shotlist(
        stats=m.StatsShotlist(median_shot_s=1.2, target_s=1.2, hook_shots_max_s=0.9),
        shots=[shot],
    )
    moteur = CartesEngine(style=style_cartes(), racine=Path.cwd())
    assets = moteur.prepare_assets(liste, chaine(), chemins)
    assert len(assets) == 1 and assets[0].provider == "charte"
    assert chemins.licence("shot_00").exists()
    clip = moteur.render_shot(shot, assets, chaine(), chemins)
    assert moteur.verify_clip(clip, 1.2) == []
    info = video.ffprobe_clip(clip)
    assert (info.largeur, info.hauteur) == (1920, 1080)
    assert info.images == round(1.2 * video.FPS)
    assert info.audio is False


def test_un_plan_sponsor_porte_le_bandeau_de_divulgation(tmp_path: Path) -> None:
    """Le bandeau « Publicité » vient de la langue et couvre **tout** le plan (loi 2023-451)."""
    from PIL import Image

    chemins = RunPaths(video_id="run-sponsor", racine=tmp_path).creer()
    shot = m.Shot(
        id="shot_00", segment_id="seg_00", start_s=0.0, end_s=1.0, duration_s=1.0,
        visual_intent="un objet", on_screen_text=None,
        asset_request=m.AssetRequest(type="card", prompt_or_keywords="plein", reuse_ok=False),
        is_sponsor=True, seed=99,
    )
    liste = m.Shotlist(
        stats=m.StatsShotlist(median_shot_s=1.0, target_s=1.0, hook_shots_max_s=0.7),
        shots=[shot],
    )
    moteur = CartesEngine(style=style_cartes(), racine=Path.cwd(),
                          texte_divulgation="Publicité")
    moteur.prepare_assets(liste, chaine(), chemins)
    carte = Image.open(chemins.asset_dir("shot_00") / "card.png").convert("RGBA")
    # Le bandeau est posé dans la marge haute gauche, en couleur `highlight` opaque.
    fenetre = carte.crop((96, 96, 500, 200))
    assert any(pixel[3] > 200 for pixel in fenetre.get_flattened_data()), "bandeau absent"
