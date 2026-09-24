"""Famille « durée » — la vidéo livrée face à ce qu'elle visait, et face à sa niche.

Deux cibles, parce qu'elles ne disent pas la même chose :

- `duree_vs_run` compare à `spec.target_duration_s`, la durée décidée pour **cette** vidéo à
  l'étape 10. C'est elle qui bloque : une vidéo qui sort à 45 % de ce qu'elle visait est
  tronquée, pas « courte ».
- `duree_vs_niche` compare à la médiane de la niche. Elle n'est **jamais bloquante** et sort
  en `warn` au pire : `REFERENTIEL.md` § 2 mesure `p75/p25 = 12,9` sur `science_pop`, où la
  médiane n'est pas un mode. Punir l'écart à une médiane qui mélange des formats serait punir
  un choix éditorial légitime.
"""

from __future__ import annotations

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def mesurer(contexte: ContexteQc) -> Famille:
    """Durée livrée contre la cible du run et contre la médiane de la niche."""
    famille = Famille("duree", poids=contexte.qc.poids.get("duree", 10))
    duree = contexte.duree_s
    seuil = contexte.seuil("duration")
    tolerance = float(seuil.get("tolerance", 0.15))
    plage = float(seuil.get("plage", 0.50))

    cible_run = float(contexte.spec.target_duration_s)
    part = duree / cible_run if cible_run else 0.0
    score = base.score_cible(duree, cible_run, tolerance, plage)
    bas = float(seuil.get("min", 0.60))
    haut = float(seuil.get("max", 1.50))
    hors_bornes = not (bas <= part <= haut)
    famille.mesures.append(Mesure(
        nom="duree_vs_run", valeur=round(duree, 1), unite="s", cible=round(cible_run, 1),
        source="ffprobe format.duration", origine_cible="spec.json (target_duration_s)",
        score=score, poids=2, bloquant=True,
        statut="fail" if hors_bornes else base.statut_depuis(score),
        note=f"{part:.0%} de la cible du run ; bornes bloquantes {bas:.0%}–{haut:.0%}",
    ))

    bloc = contexte.niche.get("duree_s", {})
    cible_niche = bloc.get("cible")
    if cible_niche is None or bloc.get("a_mesurer"):
        famille.mesures.append(Mesure(
            nom="duree_vs_niche", valeur=round(duree, 1), unite="s", cible=None,
            source="ffprobe format.duration",
            origine_cible=f"{base.REGISTRE} — cible absente ou a_mesurer",
            score=None, poids=1, statut="skipped", note="aucune cible de durée pour cette niche",
        ))
        return famille

    large = bool(bloc.get("distribution_large"))
    # Objection C5, retenue : quand `spec.target_duration_s` a été dimensionnée sur la médiane
    # de la niche — c'est le cas par défaut — les deux mesures portent la même cible et la
    # famille note deux fois le même écart, avec un poids total de 3. La seconde sort alors.
    if abs(float(cible_niche) - cible_run) <= 0.01 * cible_run or large:
        famille.mesures.append(Mesure(
            nom="duree_vs_niche", valeur=round(duree, 1), unite="s", cible=float(cible_niche),
            source="ffprobe format.duration",
            origine_cible=f"{base.REGISTRE} — niches.{contexte.spec.niche}.duree_s.cible",
            score=None, poids=1, statut="skipped",
            note=(
                "cible identique à celle du run : la noter deux fois compterait deux fois le "
                "même écart" if not large else
                f"distribution large (p75/p25 = {bloc.get('dispersion_p75_p25')}) : "
                "la médiane n'est pas un mode, l'écart n'est pas un défaut"
            ),
        ))
        return famille

    score_niche = base.score_cible(duree, float(cible_niche), tolerance, plage)
    famille.mesures.append(Mesure(
        nom="duree_vs_niche", valeur=round(duree, 1), unite="s", cible=float(cible_niche),
        source="ffprobe format.duration",
        origine_cible=f"{base.REGISTRE} — niches.{contexte.spec.niche}.duree_s.cible",
        score=score_niche, poids=1, bloquant=False,
        statut="warn" if score_niche < 85 else "pass",
        note=(
            f"p25 {bloc.get('p25')} s – p75 {bloc.get('p75')} s"
            + (" ; distribution large (p75/p25 > 4), écart non pénalisant" if large else "")
        ),
    ))
    return famille
