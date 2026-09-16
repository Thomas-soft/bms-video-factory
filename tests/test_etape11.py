"""Étape 11 — audio, fusion des segments, alignement souple, découpage et rendu des sous-titres.

Aucun test ne charge de modèle : le TTS et l'ASR sont mesurés par `factory doctor` et par les
exécutions réelles, pas par pytest. Ce qui est testé ici, ce sont les invariants que le pipeline
doit tenir quelles que soient les valeurs rendues par les deux briques.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from factory import asr, audio
from factory.core import models as m
from factory.steps import subtitles as st
from factory.steps import voice as vo


# --- outillage ------------------------------------------------------------------------

def sinus(chemin: Path, duree: float, silence_avant: float = 0.0, gain_db: float = -18.0) -> Path:
    """Écrit un WAV de test au format de travail, précédé d'un silence si demandé."""
    filtres = [f"volume={gain_db}dB"]
    if silence_avant:
        filtres.insert(0, f"adelay={int(silence_avant * 1000)}")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", f"sine=frequency=220:duration={duree}:sample_rate={audio.SAMPLE_RATE}",
         "-af", ",".join(filtres), "-ac", "1", "-c:a", "pcm_s16le", str(chemin)],
        check=True,
    )
    return chemin


def segment(identifiant: str, role: str, narration: str,
            boucle: str | None = None) -> m.ScriptSegment:
    return m.ScriptSegment(id=identifiant, role=role, narration=narration,
                           visual_intent="un objet sur fond de charte", open_loop=boucle)


def script_de(segments: list[m.ScriptSegment]) -> m.Script:
    """Script minimal pour exercer la fusion.

    `model_construct` court-circuite les règles de boucles ouvertes du contrat de script :
    elles sont testées à l'étape 10 et n'ont rien à voir avec le découpage de la synthèse.
    """
    mots = sum(len(s.narration.split()) for s in segments)
    return m.Script.model_construct(
        schema_version="1.0", lang="fr",
        hook=m.Hook(type="question_contrarienne", text=segments[0].narration),
        segments=segments,
        editorial_signature=m.SignatureEditoriale(angle="opinion", elements_proprietaires=["essai"]),
        word_count=mots, estimated_duration_s=max(1.0, mots / 134.9 * 60),
    )


def mot_asr(mot: str, debut: float, fin: float, conf: float | None = 0.9) -> dict:
    return {"w": mot, "start_s": debut, "end_s": fin, "conf": conf}


# --- audio ----------------------------------------------------------------------------

def test_silence_trim_retire_le_silence_de_tete(tmp_path: Path) -> None:
    source = sinus(tmp_path / "a.wav", duree=2.0, silence_avant=1.0)
    avant, apres = audio.silence_trim(source, tmp_path / "a_t.wav")
    assert avant == pytest.approx(3.0, abs=0.05)
    assert apres < avant - 0.7  # le silence d'une seconde est parti, la garde reste


def test_concat_pose_les_pauses_et_rend_les_positions(tmp_path: Path) -> None:
    a = sinus(tmp_path / "a.wav", duree=1.0)
    b = sinus(tmp_path / "b.wav", duree=2.0)
    positions = audio.concat([a, b], [0.0, 0.35], tmp_path / "c.wav")
    assert positions[0][0] == pytest.approx(0.0, abs=0.01)
    assert positions[1][0] == pytest.approx(1.35, abs=0.02)
    assert audio.duree(tmp_path / "c.wav") == pytest.approx(3.35, abs=0.02)


def test_concat_refuse_un_nombre_de_pauses_incoherent(tmp_path: Path) -> None:
    a = sinus(tmp_path / "a.wav", duree=0.5)
    with pytest.raises(audio.ErreurAudio):
        audio.concat([a, a], [0.0], tmp_path / "c.wav")


def test_loudnorm_deux_passes_rend_ce_qui_a_ete_mesure(tmp_path: Path) -> None:
    """La cible est -14 LUFS ; ce qui compte, c'est que les valeurs rendues soient des mesures."""
    source = sinus(tmp_path / "a.wav", duree=6.0, gain_db=-24.0)
    resultat = audio.loudnorm_two_pass(source, tmp_path / "n.wav")
    assert resultat.mesure_i < 0
    assert resultat.apres.lufs is not None and resultat.apres.true_peak_dbtp is not None
    # La normalisation est un gain : elle ne déplace pas le temps.
    assert audio.duree(tmp_path / "n.wav") == pytest.approx(audio.duree(source), abs=0.02)


def test_measure_lufs_prend_la_derniere_valeur_et_non_la_premiere(tmp_path: Path) -> None:
    source = sinus(tmp_path / "a.wav", duree=4.0, gain_db=-30.0)
    mesure = audio.measure_lufs(source)
    assert mesure.lufs is not None and -60 < mesure.lufs < 0
    assert "Integrated loudness" in mesure.resume


def test_atempo_raccourcit_sans_chainer_au_dela_des_bornes(tmp_path: Path) -> None:
    source = sinus(tmp_path / "a.wav", duree=4.0)
    assert audio.atempo(source, tmp_path / "f.wav", 1.25) == pytest.approx(3.2, abs=0.05)
    with pytest.raises(audio.ErreurAudio):
        audio.atempo(source, tmp_path / "g.wav", 3.0)


# --- fusion des segments --------------------------------------------------------------

def test_les_segments_courts_de_meme_role_fusionnent(tmp_path: Path) -> None:
    script = script_de([
        segment("seg_00", "point", "un deux trois quatre cinq", boucle="plant"),
        segment("seg_01", "point", "six sept huit neuf dix", boucle="plant"),
        segment("seg_02", "point", " ".join(["mot"] * 60), boucle="payoff"),
    ])
    unites = vo.construire_unites(script, mots_par_minute=134.9, min_segment_s=15.0)
    assert [u.segments for u in unites] == [["seg_00", "seg_01", "seg_02"]]


def test_la_fusion_ne_traverse_jamais_un_changement_de_role(tmp_path: Path) -> None:
    """Fusionner le hook avec la suite supprimerait la respiration de 600 ms qui le suit."""
    script = script_de([
        segment("seg_00", "hook", "un deux trois quatre cinq", boucle="plant"),
        segment("seg_01", "contexte", " ".join(["mot"] * 60), boucle="plant"),
    ])
    unites = vo.construire_unites(script, mots_par_minute=134.9, min_segment_s=15.0)
    assert [u.identifiant for u in unites] == ["seg_00", "seg_01"]
    assert unites[0].duree_estimee_s < 15.0  # court, et signalé par l'étape


def test_les_pauses_suivent_la_charte() -> None:
    unites = [
        vo.Unite("seg_00", "hook", ["seg_00"], "a", 1, 8.0),
        vo.Unite("seg_01", "point", ["seg_01"], "b", 1, 20.0),
        vo.Unite("seg_02", "sponsor", ["seg_02"], "c", 1, 20.0),
        vo.Unite("seg_03", "cta", ["seg_03"], "d", 1, 20.0),
    ]
    pauses = vo.pauses_de(unites, m.PausesTts())
    assert pauses == [0.0, 0.600, 0.250, 0.350]


# --- alignement -----------------------------------------------------------------------

MOTS = [st.MotScript(mot=m_, segment="seg_00") for m_ in "le sucre change tout".split()]


def test_alignement_parfait_reprend_les_timings_de_l_asr() -> None:
    asr_mots = [mot_asr("Le", 0.0, 0.2), mot_asr("sucre", 0.2, 0.6),
                mot_asr("change", 0.6, 1.0), mot_asr("tout", 1.0, 1.3)]
    apparies = st.aligner(MOTS, asr_mots)
    assert apparies == {0: 0, 1: 1, 2: 2, 3: 3}
    horodatages = st.horodater(MOTS, asr_mots, apparies, 1.5)
    assert horodatages[1] == (0.2, 0.6)


def test_un_mot_non_entendu_est_interpole_entre_ses_ancres() -> None:
    asr_mots = [mot_asr("le", 0.0, 0.2), mot_asr("change", 0.8, 1.0), mot_asr("tout", 1.0, 1.3)]
    apparies = st.aligner(MOTS, asr_mots)
    assert 1 not in apparies  # « sucre » n'a pas été entendu
    horodatages = st.horodater(MOTS, asr_mots, apparies, 1.5)
    assert 0.2 <= horodatages[1][0] < horodatages[1][1] <= 0.8


def test_le_texte_du_script_fait_foi_meme_quand_l_asr_se_trompe() -> None:
    """Un mot mal entendu garde le mot du script et emprunte seulement son timing."""
    asr_mots = [mot_asr("le", 0.0, 0.2), mot_asr("sucres", 0.2, 0.6),
                mot_asr("changent", 0.6, 1.0), mot_asr("tout", 1.0, 1.3)]
    apparies = st.aligner(MOTS, asr_mots)
    assert apparies[1] == 1 and apparies[2] == 2  # appariés par similarité
    horodatages = st.horodater(MOTS, asr_mots, apparies, 1.5)
    mots = [
        m.WordTiming(w=mot.mot, start_s=d, end_s=f, seg=mot.segment)
        for mot, (d, f) in zip(MOTS, horodatages, strict=True)
    ]
    assert [w.w for w in mots] == ["le", "sucre", "change", "tout"]


def test_un_bloc_remplace_sans_ressemblance_n_est_pas_apparie() -> None:
    asr_mots = [mot_asr("le", 0.0, 0.2), mot_asr("brouhaha", 0.2, 0.6),
                mot_asr("xyz", 0.6, 1.0), mot_asr("tout", 1.0, 1.3)]
    apparies = st.aligner(MOTS, asr_mots)
    assert 1 not in apparies and 2 not in apparies


def test_les_horodatages_restent_croissants_et_dans_la_piste() -> None:
    asr_mots = [mot_asr("le", 0.0, 0.2), mot_asr("sucre", 0.1, 0.1), mot_asr("tout", 9.0, 12.0)]
    apparies = st.aligner(MOTS, asr_mots)
    horodatages = st.horodater(MOTS, asr_mots, apparies, 2.0)
    debuts = [d for d, _ in horodatages]
    assert debuts == sorted(debuts)
    assert all(0.0 <= d <= f <= 2.0 for d, f in horodatages)


# --- découpage et rendu ---------------------------------------------------------------

def horodatages_reguliers(nombre: int, pas: float = 0.3) -> list[tuple[float, float]]:
    return [(i * pas, i * pas + pas * 0.9) for i in range(nombre)]


def test_un_groupe_ne_depasse_jamais_cinq_mots_ni_deux_lignes() -> None:
    mots = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
    cues = st.grouper(mots, horodatages_reguliers(len(mots)), largeur=38, lignes_max=2)
    assert all(1 <= len(c.indices) <= st.MOTS_MAX for c in cues)
    assert all(len(c.lignes) <= 2 for c in cues)
    assert all(len(ligne) <= 38 for c in cues for ligne in c.lignes)
    assert [i for c in cues for i in c.indices] == list(range(len(mots)))


def test_un_groupe_ne_traverse_pas_une_respiration() -> None:
    mots = ["un", "deux", "trois", "quatre"]
    horodatages = [(0.0, 0.3), (0.3, 0.6), (2.0, 2.3), (2.3, 2.6)]
    cues = st.grouper(mots, horodatages, largeur=38, lignes_max=2)
    assert len(cues) == 2 and cues[0].indices == [0, 1]


def test_la_duree_d_un_groupe_reste_dans_les_bornes() -> None:
    mots = [f"m{i}" for i in range(20)]
    cues = st.grouper(mots, horodatages_reguliers(20, pas=0.9), largeur=38, lignes_max=2)
    assert all(c.fin_s - c.debut_s <= st.DUREE_MAX_S + 1e-6 for c in cues)
    assert all(c.fin_s - c.debut_s >= st.DUREE_MIN_S - 1e-6 for c in cues)


def test_le_srt_est_horodate_au_format_attendu(tmp_path: Path) -> None:
    mots = ["alpha", "beta", "gamma"]
    cues = st.grouper(mots, horodatages_reguliers(3), largeur=38, lignes_max=2)
    st.ecrire_srt(cues, tmp_path / "s.srt")
    contenu = (tmp_path / "s.srt").read_text(encoding="utf-8")
    assert contenu.startswith("1\n00:00:00,000 --> ")
    assert "alpha" in contenu


def test_la_couleur_ass_inverse_bien_les_octets() -> None:
    assert st._couleur_ass("#ffd166") == "&H0066D1FF"
    assert st._couleur_ass("#000000") == "&H00000000"


def test_le_style_ass_vient_de_la_charte_et_de_rien_d_autre(tmp_path: Path) -> None:
    charte = m.Charte(
        version="test", fonts=m.Polices(title="Inter SemiBold", body="Inter Regular"),
        palette=m.Palette(bg="#101820", text="#ffffff", text_outline="#0a0a0a",
                          accent="#2f9e8f", highlight="#ffd166"),
        transitions=["cut"],
        subtitles=m.SousTitresCharte(align="middle_center", size_px=72, margin_v_px=120,
                                     max_chars_per_line=38, karaoke=True),
    )
    mots = ["alpha", "beta", "gamma"]
    horodatages = horodatages_reguliers(3)
    cues = st.grouper(mots, horodatages, largeur=38, lignes_max=2)
    st.ecrire_ass(cues, mots, horodatages, tmp_path / "s.ass", charte)
    contenu = (tmp_path / "s.ass").read_text(encoding="utf-8")
    assert "Inter SemiBold,72" in contenu
    assert contenu.count("\nDialogue: ") == len(cues)
    # karaoké : la primaire est la couleur de surlignage, la secondaire celle du texte
    assert "&H0066D1FF,&H00FFFFFF" in contenu
    assert ",5,80,80,120,1" in contenu  # alignement milieu-centre et marge de la charte
    assert "{\\k" in contenu


def test_sans_karaoke_la_couleur_primaire_est_celle_du_texte(tmp_path: Path) -> None:
    charte = m.Charte(
        version="test", fonts=m.Polices(title="Inter SemiBold", body="Inter Regular"),
        palette=m.Palette(bg="#101820", text="#ffffff", text_outline="#0a0a0a",
                          accent="#2f9e8f", highlight="#ffd166"),
        transitions=["cut"], subtitles=m.SousTitresCharte(karaoke=False),
    )
    mots = ["alpha", "beta"]
    horodatages = horodatages_reguliers(2)
    cues = st.grouper(mots, horodatages, largeur=38, lignes_max=2)
    st.ecrire_ass(cues, mots, horodatages, tmp_path / "s.ass", charte)
    contenu = (tmp_path / "s.ass").read_text(encoding="utf-8")
    assert "&H00FFFFFF,&H00FFFFFF" in contenu
    assert "{\\k" not in contenu


# --- mesure ---------------------------------------------------------------------------

def test_le_wer_hors_nombres_neutralise_la_convention_d_ecriture() -> None:
    assert asr.wer("trente jours sans sucre", "30 jours sans sucre") == pytest.approx(0.25)
    assert asr.wer("trente jours sans sucre", "30 jours sans sucre", ignorer_nombres=True) == 0.0


def test_le_seuil_de_wer_depend_de_la_longueur_du_segment() -> None:
    config = m.ConfigAsr(primary="parakeet", fallback="whisper",
                         wer_thresholds={"5": 0.20, "20": 0.15, "999": 0.08})
    assert config.seuil(4) == 0.20
    assert config.seuil(12) == 0.15
    assert config.seuil(60) == 0.08


# --- contrats -------------------------------------------------------------------------

def timings_valides(**surcharges) -> dict:
    base = dict(
        schema_version="1.0", voice_id="serena_fr", engine="qwen3_tts",
        loudness_lufs=-14.1, true_peak_dbtp=-1.0, total_duration_s=40.0,
        segments=[
            dict(id="seg_00", file="voice/segment_00.wav", start_s=0.0, end_s=20.0,
                 duration_s=20.0, text="a"),
            dict(id="seg_01", file="voice/segment_01.wav", start_s=20.35, end_s=40.0,
                 duration_s=19.65, text="b"),
        ],
    )
    base.update(surcharges)
    return base


def test_timings_accepte_un_run_normal() -> None:
    timings = m.Timings.model_validate(timings_valides())
    assert timings.segments[1].start_s == 20.35


def test_timings_refuse_un_segment_qui_deborde_de_la_piste() -> None:
    with pytest.raises(ValidationError):
        m.Timings.model_validate(timings_valides(total_duration_s=30.0))


def test_timings_refuse_une_duree_incoherente() -> None:
    donnees = timings_valides()
    donnees["segments"][0]["duration_s"] = 5.0
    with pytest.raises(ValidationError):
        m.Timings.model_validate(donnees)


def test_words_refuse_un_repli_sans_motif() -> None:
    with pytest.raises(ValidationError):
        m.Words(schema_version="1.0", engine="whisper", coverage=1.0,
                wer_vs_script=0.02, wer_threshold=0.08)


def test_la_langue_porte_des_pauses_par_defaut_conformes_a_la_charte() -> None:
    config = m.ConfigTts()
    assert (config.pauses_ms.entre_segments_ms, config.pauses_ms.apres_hook_ms,
            config.pauses_ms.avant_sponsor_ms) == (350, 600, 250)
    assert config.min_segment_s == 15.0


def test_le_saut_de_ligne_ass_suit_le_repli_du_srt(tmp_path: Path) -> None:
    """Le `\\N` est posé d'après le nombre de mots de la première ligne, pas par recherche."""
    charte = m.Charte(
        version="test", fonts=m.Polices(title="Inter SemiBold", body="Inter Regular"),
        palette=m.Palette(bg="#101820", text="#ffffff", text_outline="#0a0a0a",
                          accent="#2f9e8f", highlight="#ffd166"),
        transitions=["cut"],
        subtitles=m.SousTitresCharte(max_chars_per_line=12, max_lines=2, karaoke=False),
    )
    mots = ["alpha", "beta", "alpha", "gamma"]
    horodatages = horodatages_reguliers(4)
    cues = st.grouper(mots, horodatages, largeur=12, lignes_max=2)
    assert len(cues) == 1 and len(cues[0].lignes) == 2
    st.ecrire_ass(cues, mots, horodatages, tmp_path / "s.ass", charte)
    ligne = [l for l in (tmp_path / "s.ass").read_text(encoding="utf-8").splitlines()
             if l.startswith("Dialogue:")][0]
    # Le mot « alpha » apparaît deux fois : la coupure doit tomber sur la bonne occurrence.
    assert ligne.endswith("alpha beta\\Nalpha gamma")


def test_un_groupe_trop_court_est_absorbe_par_le_precedent() -> None:
    """La seule correction qui ne fabrique pas de temps : fusionner, pas étirer."""
    mots = ["un", "deux", "trois"]
    horodatages = [(0.0, 1.0), (1.0, 2.0), (2.0, 2.1)]
    cues = st.grouper(mots, horodatages, largeur=38, lignes_max=2)
    assert len(cues) == 1 and cues[0].indices == [0, 1, 2]


def test_un_groupe_trop_long_voit_son_affichage_coupe() -> None:
    """Un mot interpolé sur une longue respiration ne reste pas dix secondes à l'écran."""
    mots = ["interminable"]
    cues = st.grouper(mots, [(0.0, 10.0)], largeur=38, lignes_max=2)
    assert cues[0].fin_s - cues[0].debut_s == pytest.approx(st.DUREE_MAX_S)


def test_deux_sous_titres_ne_sont_jamais_a_l_ecran_en_meme_temps() -> None:
    """Les ASR rendent des mots dont la fin déborde sur le début du suivant."""
    mots = ["un", "deux", "trois", "quatre", "cinq", "six"]
    horodatages = [(0.0, 1.2), (0.5, 1.6), (1.0, 2.4), (2.0, 3.0), (2.5, 3.4), (3.0, 4.0)]
    cues = st.grouper(mots, horodatages, largeur=12, lignes_max=2)
    assert all(cues[i].fin_s <= cues[i + 1].debut_s + 1e-9 for i in range(len(cues) - 1))
