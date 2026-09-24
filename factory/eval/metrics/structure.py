"""Famille « structure » — où sont placés le sponsor et les boucles ouvertes.

Deux contrôles seulement, mais l'un des deux est bloquant : **un segment sponsor dans la
première minute** est le motif le mieux documenté d'abandon précoce, et c'est aussi celui qui
transforme une vidéo en publicité aux yeux du spectateur avant qu'il ait reçu quoi que ce soit.

Les boucles ouvertes se lisent dans `script.json` (`open_loop: plant | payoff`) et sont datées
par `shotlist.json` : une boucle plantée qui n'est jamais payée est le défaut que l'étape 16
devra corriger, et le banc doit savoir le voir avant elle.
"""

from __future__ import annotations

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def mesurer(contexte: ContexteQc) -> Famille:
    """Position du sponsor, comptage et datation des boucles ouvertes."""
    famille = Famille("structure", poids=contexte.qc.poids.get("structure", 5))
    famille.mesures.append(_sponsor(contexte))
    famille.mesures.extend(_boucles(contexte))
    famille.mesures.extend(_boucles_verifiees(contexte))
    famille.mesures.append(_cadence_des_ruptures(contexte))
    famille.mesures.append(_densite(contexte))
    return famille


def _bloc_retention(contexte: ContexteQc):
    """Bloc `decisions.retention` du manifeste, ou `None` s'il date d'avant l'étape 16."""
    manifest = contexte.manifest
    return None if manifest is None else getattr(manifest.decisions, "retention", None)


def _boucles_verifiees(contexte: ContexteQc) -> list[Mesure]:
    """Boucles **réellement** payées : marqueur de promesse, marqueur de paiement, juge.

    `open_loops_paid` ci-dessus compte les étiquettes `plant`/`payoff` de `script.json` — que
    le code pose lui-même avant toute génération. Cette mesure-ci compte ce que
    `factory/retention/verify.py` a vérifié dans le **texte** : c'est la différence entre une
    boucle écrite et une boucle déclarée.
    """
    seuil = contexte.seuil("open_loops")
    minimum = int(seuil.get("min", 2))
    bloc = _bloc_retention(contexte)
    if bloc is None:
        return [Mesure(
            nom="open_loops_verified", valeur=None, unite="boucles", cible=minimum,
            source="manifest.decisions.retention", origine_cible=base.REGISTRE, score=None,
            poids=2, statut="skipped",
            note="run antérieur à l'étape 16 : aucune vérification de rétention au manifeste")]
    payees = int(bloc.loops_paid_verified)
    part = min(1.0, payees / max(1, minimum))
    note = (f"{bloc.loops_planted_marked} promesse(s) écrite(s), {payees} tenue(s) sur "
            f"{minimum} exigées")
    if bloc.loops_unjudged:
        note += f" ; {bloc.loops_unjudged} non jugée(s) par le modèle — non vérifiée(s)"
    return [Mesure(
        nom="open_loops_verified", valeur=payees, unite="boucles", cible=minimum,
        source="manifest.decisions.retention — marqueurs mesurés + juge LLM",
        origine_cible=f"{base.REGISTRE} — hooks.boucles_minimum {minimum}",
        score=100.0 * part, poids=2, statut=base.statut_depuis(100.0 * part), note=note)]


def _cadence_des_ruptures(contexte: ContexteQc) -> Mesure:
    """Plus grand intervalle sans rupture, contre la cadence visée de la niche."""
    bloc = _bloc_retention(contexte)
    if bloc is None or bloc.interrupt_cadence_s is None:
        return Mesure(
            nom="interrupt_gap", valeur=None, unite="s", cible=None,
            source="manifest.decisions.retention", origine_cible=base.DECISION, score=None,
            poids=2, statut="skipped", note="aucune planification de rupture au manifeste")
    cadence = float(bloc.interrupt_cadence_s)
    ecart = bloc.interrupt_max_gap_s
    if ecart is None:
        return Mesure(
            nom="interrupt_gap", valeur=None, unite="s", cible=cadence,
            source="manifest.decisions.retention", origine_cible=base.DECISION, score=None,
            poids=2, statut="skipped", note="écart non mesuré")
    # Poser une rupture plus tôt que la cadence n'est pas un défaut ; l'espacement l'est.
    score = base.score_max(float(ecart), cadence, cadence * 2.0)
    return Mesure(
        nom="interrupt_gap", valeur=round(float(ecart), 1), unite="s", cible=round(cadence, 1),
        source="manifest.decisions.retention — script.json, ruptures datées",
        origine_cible=(f"{base.DECISION} — 4 × rythme de coupe de la niche, borné à [20, 45] s "
                       "(étape 16)"),
        score=score, poids=2, statut=base.statut_depuis(score),
        note=f"{bloc.interrupts_planned} rupture(s) posée(s) ; plus long silence de rupture")


def _densite(contexte: ContexteQc) -> Mesure:
    """Densité d'information du script, telle que le manifeste l'a enregistrée.

    **Ce que cette note ne dit pas.** Le sous-agent B de l'étape 16 a mesuré la densité sur
    263 transcriptions du registre : elle **ne sépare pas** les vidéos les plus vues des
    autres (Spearman +0,057 sur l'ensemble, non significatif dans 9 niches sur 10). C'est donc
    un garde-fou de rédaction, pas un prédicteur de performance — la note reste au barème
    parce qu'un script sans aucun fait est mauvais, pas parce qu'un script dense percera.
    """
    manifest = contexte.manifest
    bloc = None if manifest is None else getattr(manifest.decisions, "density", None)
    if bloc is None or bloc.target is None:
        return Mesure(
            nom="density_vs_target", valeur=None if bloc is None else bloc.facts_per_min,
            unite="faits/min", cible=None if bloc is None else bloc.target,
            source="manifest.decisions.density", origine_cible=base.REGISTRE, score=None,
            poids=2, statut="skipped",
            note=("aucune densité au manifeste (run antérieur à l'étape 16)" if bloc is None
                  else "aucune cible de densité pour cette niche"))
    score = base.score_min(bloc.facts_per_min, float(bloc.target),
                           float(bloc.floor or bloc.target * 0.4))
    return Mesure(
        nom="density_vs_target", valeur=bloc.facts_per_min, unite="faits/min",
        cible=bloc.target, source="manifest.decisions.density — règles de density.py",
        origine_cible=(f"{base.REGISTRE} — médiane des transcriptions EN de la niche "
                       "(étape 16) ; NON validée comme prédicteur de vues"),
        score=score, poids=2, statut=base.statut_depuis(score),
        note=(f"{bloc.count} fait(s) comptés, dont {bloc.entity_share:.0%} de noms propres"
              + (f" ; plancher de refus {bloc.floor}" if bloc.floor else "")
              + (f" ; juge LLM {bloc.judge_facts_per_min:.1f} fait/min"
                 if bloc.judge_facts_per_min is not None else " ; juge LLM non consulté")))


def _debuts_de_segment(contexte: ContexteQc) -> dict[str, float]:
    """Instant du premier plan de chaque segment, depuis `shotlist.json`."""
    shotlist = contexte.shotlist
    if shotlist is None:
        return {}
    debuts: dict[str, float] = {}
    for shot in shotlist.shots:
        debuts.setdefault(shot.segment_id, shot.start_s)
        debuts[shot.segment_id] = min(debuts[shot.segment_id], shot.start_s)
    return debuts


def _sponsor(contexte: ContexteQc) -> Mesure:
    """Instant du premier plan sponsorisé. Aucun sponsor = contrôle tenu."""
    seuil = contexte.seuil("sponsor_position")
    plancher = float(seuil.get("min", 60.0))
    shotlist = contexte.shotlist
    if shotlist is None:
        return Mesure(
            nom="sponsor_position", valeur=None, unite="s", cible=plancher,
            source="shotlist.json", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="shotlist.json absent",
        )
    sponsors = [s for s in shotlist.shots if s.is_sponsor]
    if not sponsors:
        # Objection A4, retenue : rendre 100 pour un contrôle qui n'a rien contrôlé offrait
        # cinq points de barème à toute vidéo sans sponsor — c'est-à-dire à toutes les nôtres.
        return Mesure(
            nom="sponsor_position", valeur=None, unite="s", cible=plancher,
            source="shotlist.json — is_sponsor", origine_cible=base.DECISION,
            score=None, poids=1, bloquant=False, statut="skipped",
            note="aucun segment sponsorisé : rien à placer, donc rien à noter",
        )
    premier = min(s.start_s for s in sponsors)
    tenu = premier >= plancher
    return Mesure(
        nom="sponsor_position", valeur=round(premier, 1), unite="s", cible=plancher,
        source="shotlist.json — premier plan is_sponsor",
        origine_cible=f"{base.DECISION} — bloquant imposé par le prompt de l'étape 15",
        score=base.score_booleen(tenu), poids=1, bloquant=True,
        statut="pass" if tenu else "fail",
        note=f"{len(sponsors)} plan(s) sponsorisé(s) ; plancher {plancher:g} s",
    )


def _boucles(contexte: ContexteQc) -> list[Mesure]:
    """Boucles plantées, boucles payées, et date de la première par rapport au référentiel."""
    script = contexte.script
    seuil = contexte.seuil("open_loops")
    minimum = int(seuil.get("min", 2))
    if script is None:
        return [Mesure(
            nom="open_loops_paid", valeur=None, unite="part", cible=1.0, source="script.json",
            origine_cible=base.REGISTRE, score=None, poids=2, statut="skipped",
            note="script.json absent",
        )]

    ordre = {segment.id: index for index, segment in enumerate(script.segments)}
    plants = [s.id for s in script.segments if s.open_loop == "plant"]
    payoffs = [s.id for s in script.segments if s.open_loop == "payoff"]
    # Une boucle n'est payée que si son paiement vient **après** : un payoff placé avant tous
    # les plants est une erreur de script que le compte brut ne verrait pas.
    payees = min(
        len(plants),
        sum(1 for p in payoffs if any(ordre[p] > ordre[plant] for plant in plants)),
    )
    # Objection A4, retenue : `boucles_minimum` ne servait que dans la note. Une seule boucle
    # plantée et payée rendait 100 alors que le référentiel en exige deux — le dénominateur est
    # donc le plus grand des deux, et une boucle manquante coûte.
    part = payees / max(len(plants), minimum)
    score = 100.0 * part if plants else 0.0
    mesures = [Mesure(
        nom="open_loops_paid", valeur=round(part, 3), unite="part des boucles plantées",
        cible=1.0, source="script.json — open_loop plant/payoff",
        origine_cible=(
            f"{base.REGISTRE} — hooks.boucles_minimum {minimum} "
            "(décision de production, au-delà de l'usage observé)"
        ),
        score=score, poids=2, statut=base.statut_depuis(score),
        note=f"{len(plants)} plantée(s), {payees} payée(s) après leur plant",
    )]

    debuts = _debuts_de_segment(contexte)
    instants = [debuts[p] for p in plants if p in debuts]
    bloc = contexte.niche.get("hooks", {}).get("boucle_ouverte", {})
    cible = bloc.get("position_s_mediane") or bloc.get("position_s_repli")
    if not instants or cible is None:
        mesures.append(Mesure(
            nom="open_loop_position", valeur=None, unite="s", cible=cible,
            source="shotlist.json + script.json", origine_cible=base.REGISTRE, score=None,
            poids=1, statut="skipped", note="position de la première boucle non datable",
        ))
        return mesures
    premiere = min(instants)
    cible = float(cible)
    plafond = cible * float(seuil.get("plage_position", 2.0))
    score_p = base.score_max(premiere, cible, plafond)
    mesures.append(Mesure(
        nom="open_loop_position", valeur=round(premiere, 1), unite="s", cible=round(cible, 1),
        source="première boucle plantée, datée par shotlist.json",
        origine_cible=(
            f"{base.REGISTRE} — hooks.boucle_ouverte.position_s"
            + (" (repli inter-niches 47,9 s)" if bloc.get("position_s_mediane") is None else "")
            + f" ; n={bloc.get('n')}, n_faible={bloc.get('n_faible')}"
        ),
        score=score_p, poids=1, statut=base.statut_depuis(score_p),
        note="plafond : planter plus tôt que la médiane n'est pas pénalisé",
    ))
    return mesures
