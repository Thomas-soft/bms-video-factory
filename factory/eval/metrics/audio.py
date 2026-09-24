"""Famille « audio » — niveau, crête, silences et lit musical, mesurés sur le fichier livré.

Aucune de ces cibles ne vient du registre : l'audio des chaînes tierces n'est jamais téléchargé
(`docs/CONFORMITE.md`). Le référentiel le dit lui-même dans son bloc `production`, et chaque
mesure recopie ici l'origine exacte — norme YouTube, pratique de diffusion ou décision de
production. C'est la réponse à l'objection 15 du contradicteur de l'étape 3.

Le rapport musique/voix est **estimé**, pas mesuré : sans piste séparée dans `final.mp4`, on
compare le niveau moyen d'une fenêtre sans parole (le lit seul) à celui d'une fenêtre parlée
(voix + lit). L'écart approche l'atténuation du lit. Le mot « estimé » est dans la note.
"""

from __future__ import annotations

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def mesurer(contexte: ContexteQc) -> Famille:
    """LUFS, crête réelle, silences trop longs et atténuation estimée du lit musical."""
    famille = Famille("audio", poids=contexte.qc.poids.get("audio", 15))
    niveau = contexte.loudness
    production = contexte.production

    # -- niveau intégré (bloquant) --------------------------------------------------------
    bloc_l = production.get("loudness_lufs", {})
    cible_l = float(bloc_l.get("cible", -14.0))
    seuil_l = contexte.seuil("loudness")
    tolerance_l = float(seuil_l.get("tolerance", bloc_l.get("tolerance", 1.0)))
    bas = float(seuil_l.get("min", -16.0))
    haut = float(seuil_l.get("max", -12.0))
    if niveau.lufs is None:
        famille.mesures.append(Mesure(
            nom="loudness", valeur=None, unite="LUFS", cible=cible_l, source="ffmpeg ebur128",
            origine_cible=f"{base.REGISTRE} — production.loudness_lufs", score=None,
            poids=3, bloquant=True, statut="fail", note="ebur128 n'a rien rendu : NON MESURÉ",
        ))
    else:
        hors = not (bas <= niveau.lufs <= haut)
        score_l = base.score_intervalle(
            niveau.lufs, cible_l - tolerance_l, cible_l + tolerance_l, marge=4.0
        )
        famille.mesures.append(Mesure(
            nom="loudness", valeur=round(niveau.lufs, 2), unite="LUFS", cible=cible_l,
            source="ffmpeg ebur128 (peak=true)",
            origine_cible=(
                f"{base.REGISTRE} — production.loudness_lufs "
                f"({bloc_l.get('origine', 'norme YouTube')})"
            ),
            score=score_l, poids=3, bloquant=True,
            statut="fail" if hors else base.statut_depuis(score_l),
            note=f"bornes bloquantes [{bas:g}, {haut:g}] LUFS · LRA {niveau.lra} LU",
        ))

    # -- crête réelle ----------------------------------------------------------------------
    bloc_tp = production.get("true_peak_dbtp", {})
    cible_tp = float(bloc_tp.get("cible", -1.0))
    if niveau.true_peak_dbtp is None:
        famille.mesures.append(Mesure(
            nom="true_peak", valeur=None, unite="dBTP", cible=cible_tp,
            source="ffmpeg ebur128", origine_cible=f"{base.REGISTRE} — production.true_peak_dbtp",
            score=None, poids=1, statut="skipped", note="crête réelle NON MESURÉE",
        ))
    else:
        score_tp = base.score_max(niveau.true_peak_dbtp, cible_tp, cible_tp + 2.0)
        famille.mesures.append(Mesure(
            nom="true_peak", valeur=round(niveau.true_peak_dbtp, 2), unite="dBTP",
            cible=cible_tp, source="ffmpeg ebur128 (peak=true)",
            origine_cible=(
                f"{base.REGISTRE} — production.true_peak_dbtp "
                f"({bloc_tp.get('origine', 'pratique de diffusion')})"
            ),
            score=score_tp, poids=1, statut=base.statut_depuis(score_tp),
            note="plafond, jamais une cible à atteindre",
        ))

    # -- plage de dynamique ------------------------------------------------------------------
    seuil_lra = contexte.seuil("loudness_range")
    if niveau.lra is not None:
        minimum = float(seuil_lra.get("min", 5.0))
        score_lra = base.score_min(niveau.lra, minimum, float(seuil_lra.get("zero", 1.0)))
        famille.mesures.append(Mesure(
            nom="loudness_range", valeur=round(niveau.lra, 2), unite="LU", cible=minimum,
            source="ffmpeg ebur128", origine_cible=f"{base.DECISION} — défaut n° 2 de l'étape 13.2",
            score=score_lra, poids=1, statut=base.statut_depuis(score_lra),
            note="LRA 3,3 LU mesurée sur le run rtmk : la narration n'a aucun relief",
        ))

    # -- silences trop longs ------------------------------------------------------------------
    params = contexte.mesure_param("audio")
    plancher_long = float(params.get("silence_long_s", 1.5))
    longs = [(d, duree) for d, duree in contexte.silences if duree >= plancher_long]
    seuil_s = contexte.seuil("silence")
    maximum = float(seuil_s.get("max", 2.0))
    score_s = base.score_max(len(longs), maximum, float(seuil_s.get("zero", 8.0)))
    famille.mesures.append(Mesure(
        nom="silence_long", valeur=len(longs), unite=f"silences ≥ {plancher_long:g} s",
        cible=maximum,
        source=f"ffmpeg silencedetect noise={params.get('seuil_silence_db', -35.0)}dB",
        origine_cible=(
            f"{base.DECISION} — production.silence_max_s du registre porte a_mesurer, "
            "la valeur est une décision de production"
        ),
        score=score_s, poids=1, statut=base.statut_depuis(score_s),
        note=(
            "aucun trou" if not longs
            else f"le plus long : {max(d for _, d in longs):.1f} s"
        ),
    ))

    # -- lit musical : atténuation estimée ------------------------------------------------------
    famille.mesures.append(_lit_musical(contexte))
    return famille


def _lit_musical(contexte: ContexteQc) -> Mesure:
    """Écart estimé entre le lit musical seul et la voix, en dB.

    La fenêtre « sans voix » est le plus long **blanc entre deux mots** de `words.json`, et non
    un silence repéré par `silencedetect`. C'est l'objection A5 du contradicteur, retenue mais
    corrigée autrement : il proposait de noter 0 quand la mesure est impossible, ce qui aurait
    puni deux fois le même défaut (l'absence de respiration est déjà notée dans la famille
    parole). La vraie cause était ailleurs — `silencedetect` ne voit **aucun** silence quand un
    lit musical maintient le niveau au-dessus du seuil, c'est-à-dire exactement dans le cas où
    cette mesure a un sens. Les blancs de `words.json`, eux, existent toujours.

    Sans piste isolée, cela reste une estimation : la note en porte le mot, et la mesure n'est
    jamais bloquante.
    """
    seuil = contexte.seuil("music_bed")
    params = contexte.mesure_param("audio")
    fenetre_min = float(params.get("fenetre_musique_s", 0.8))
    origine = f"{base.DECISION} — atténuation du lit sous la voix (décision de production)"

    # Un lit absent est un lit absent, pas un lit bien mixé. Sans ce contrôle, les deux runs de
    # la phase 1 — qui n'ont aucune musique, la bibliothèque étant vide et Freesound écarté —
    # obtenaient 97/100 sur cette mesure : l'écart voix/blanc y vaut 30 dB parce qu'il n'y a
    # rien sous la voix. Le manifeste sait, lui, si une piste a été posée.
    manifest = contexte.manifest
    if manifest is not None and manifest.decisions.music_track is None:
        motif = manifest.decisions.music_warning or "aucun motif consigné"
        return Mesure(
            nom="music_bed_attenuation", valeur=None, unite="dB", cible=seuil.get("min"),
            source="manifest.decisions.music_track",
            origine_cible=origine, score=0.0, poids=1, statut="fail",
            note=f"aucun lit musical dans cette vidéo — motif au manifeste : {motif}",
        )

    candidats = _blancs_de_narration(contexte, fenetre_min)
    if not candidats:
        return Mesure(
            nom="music_bed_attenuation", valeur=None, unite="dB", cible=seuil.get("min"),
            source="ffmpeg volumedetect", origine_cible=origine, score=None, poids=1,
            statut="skipped",
            note=(
                f"aucun blanc de narration ≥ {fenetre_min:g} s : le lit musical n'est pas "
                "isolable — l'absence de respiration est notée par `respiration`"
            ),
        )
    debut, duree = max(candidats, key=lambda c: c[1])
    marge = 0.15
    niveau_lit = base.volume_moyen(
        contexte.video, debut + marge, max(0.2, duree - 2 * marge)
    )
    niveau_voix = base.volume_moyen(contexte.video, contexte.duree_s * 0.5, 10.0)
    if niveau_lit is None or niveau_voix is None:
        return Mesure(
            nom="music_bed_attenuation", valeur=None, unite="dB", cible=seuil.get("min"),
            source="ffmpeg volumedetect", origine_cible=origine, score=None, poids=1,
            statut="skipped", note="volumedetect n'a rien rendu",
        )
    ecart = niveau_voix - niveau_lit
    minimum = float(seuil.get("min", 10.0))
    maximum = float(seuil.get("max", 30.0))
    score = base.score_intervalle(ecart, minimum, maximum, marge=10.0)
    return Mesure(
        nom="music_bed_attenuation", valeur=round(ecart, 1), unite="dB",
        cible=f"{minimum:g}–{maximum:g}", source="ffmpeg volumedetect, deux fenêtres",
        origine_cible=origine, score=score, poids=1, statut=base.statut_depuis(score),
        note=(
            f"estimation : blanc de narration {debut:.1f}–{debut + duree:.1f} s à "
            f"{niveau_lit:.1f} dBFS contre {niveau_voix:.1f} dBFS sur 10 s de narration. "
            "Un écart très grand signale l'absence de lit musical, pas un bon mixage."
        ),
    )


def _blancs_de_narration(contexte: ContexteQc, plancher_s: float) -> list[tuple[float, float]]:
    """Blancs `(début, durée)` entre deux mots consécutifs de `words.json`.

    Repli sur `silencedetect` quand `words.json` manque : sans transcription mot à mot, le
    silence du fichier mixé est la seule fenêtre disponible.
    """
    donnees = contexte.words
    if not donnees or not donnees.get("words"):
        return [(d, duree) for d, duree in contexte.silences if duree >= plancher_s]
    mots = sorted(donnees["words"], key=lambda m: float(m["start_s"]))
    blancs = []
    for precedent, suivant in zip(mots, mots[1:]):
        debut, fin = float(precedent["end_s"]), float(suivant["start_s"])
        if fin - debut >= plancher_s:
            blancs.append((debut, fin - debut))
    return blancs
