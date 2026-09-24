"""Vérification complète d'un script, avant la synthèse vocale.

Le module ne réécrit rien : il **liste des infractions**. Chacune porte son message en français
(pour le journal, `SUIVI.md` et Thomas) et sa consigne en anglais (pour le modèle, qui écrit en
anglais). C'est `factory/steps/script.py` qui décide quoi en faire : régénérer les segments
nommés, trois fois au plus, puis faire échouer le run.

**Ce qui est vérifié, et sur quoi.**

| Contrôle | Source de la règle |
|---|---|
| type, longueur et formulation du hook | `hooks.longueur_mots` du registre + `patterns_<lang>.yaml` |
| boucles plantées et payées | marqueurs mesurés + juge LLM court |
| cadence des ruptures | `4 × rythme_coupe_s.cible_montage`, borné [20, 45] s |
| densité d'information | `config/niches/<niche>.yaml → densite_faits_par_minute.cible` |
| formulations proscrites | `patterns_<lang>.yaml` |
| sponsor pas avant 60 s | `config/qc.yaml → seuils.sponsor_position` (contrôle bloquant du banc) |
| texte à l'écran ≤ 6 mots | `factory/steps/script.py → MOTS_ECRAN_MAX` |
| durée estimée ± 15 % | `config/niches/<niche>.yaml → duree_s.tolerance` |

**Une infraction non vérifiable n'est jamais un succès.** Quand le juge LLM est indisponible,
la boucle concernée est rapportée en `avertissement`, pas en `pass` silencieux.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factory.core.models import Research, Script
from factory.retention import density as density_module
from factory.retention import hooks as hooks_module
from factory.retention import interrupts as interrupts_module
from factory.retention import loops as loops_module
from factory.retention.patterns import Patterns

#: Plafond de mots du texte à l'écran, aligné sur `factory/steps/script.py`.
MOTS_ECRAN_MAX = 6
#: Le sponsor ne parle pas avant cette seconde (contrôle bloquant du banc, `qc.yaml`).
SPONSOR_MIN_S = 60.0
#: Au-delà de ce multiple de la cadence, le rythme est considéré comme rompu.
ECART_RUPTURE_TOLERE = 1.6


@dataclass
class Infraction:
    """Une règle violée, nommée en français et corrigible en anglais."""

    code: str
    message: str
    consigne: str = ""
    segments: list[str] = field(default_factory=list)
    bloquante: bool = True

    def __str__(self) -> str:
        cible = f" [{', '.join(self.segments)}]" if self.segments else ""
        return f"{self.code}{cible} : {self.message}"

    def json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "segments": list(self.segments),
                "blocking": self.bloquante}


@dataclass
class Rapport:
    """Le résultat d'une vérification : ce qui cloche, et ce qui a été mesuré au passage."""

    infractions: list[Infraction] = field(default_factory=list)
    densite: density_module.Comptage | None = None
    densite_cible: float | None = None
    boucles: list[loops_module.Boucle] = field(default_factory=list)
    ruptures_posees: int = 0
    cadence_s: float = 0.0
    ecart_rupture_max_s: float | None = None

    @property
    def conforme(self) -> bool:
        """Aucune infraction bloquante. Les avertissements n'empêchent pas le run."""
        return not any(i.bloquante for i in self.infractions)

    @property
    def bloquantes(self) -> list[Infraction]:
        return [i for i in self.infractions if i.bloquante]

    def segments_a_reecrire(self) -> list[str]:
        """Segments nommés par au moins une infraction bloquante, sans doublon."""
        vus: list[str] = []
        for infraction in self.bloquantes:
            for identifiant in infraction.segments:
                if identifiant not in vus:
                    vus.append(identifiant)
        return vus

    def consignes(self) -> str:
        """Les infractions bloquantes, en anglais, telles qu'elles repartent au modèle."""
        return "\n".join(f"- {i.consigne or i.message}" for i in self.bloquantes)

    def json(self) -> dict[str, Any]:
        return {
            "conforme": self.conforme,
            "violations": [i.json() for i in self.infractions],
            "density": None if self.densite is None else self.densite.json(),
            "density_target": self.densite_cible,
            "open_loops": [{"plant": b.plant_id, "payoff": b.payoff_id,
                            "planted": b.plantee, "paid": b.payee,
                            "judge": b.coherente, "why": b.motif} for b in self.boucles],
            "interrupts": {"count": self.ruptures_posees, "cadence_s": self.cadence_s,
                           "max_gap_s": self.ecart_rupture_max_s},
        }


def verifier(
    script: Script,
    *,
    niche: str,
    lang: str,
    mots_par_minute: float,
    plafond_hook_mots: int,
    plancher_hook_mots: int | None,
    boucles_minimum: int,
    cut_rhythm_target_s: float,
    duree_cible_s: float,
    tolerance_duree: float,
    patterns: Patterns,
    densite_cible: float | None,
    recherche: Research | None = None,
    juge_boucles: bool = True,
    seed: int = 0,
    racine: Path | None = None,
    trace: Any | None = None,
) -> Rapport:
    """Vérifie un script écrit et rend la liste de ses infractions.

    Tous les seuils sont **passés en paramètre** : aucun n'est lu ici, pour que la fonction
    soit testable sans configuration et que l'origine de chaque valeur reste celle de son
    fichier (registre, `config/niches`, `config/qc.yaml`).
    """
    rapport = Rapport(densite_cible=densite_cible)
    rapport.infractions.extend(_hook(script, patterns, plafond_hook_mots, plancher_hook_mots))
    rapport.infractions.extend(_proscrites(script, patterns))
    rapport.infractions.extend(
        _boucles(script, patterns, boucles_minimum, rapport, juge_boucles, seed, racine, trace))
    rapport.infractions.extend(
        _ruptures(script, mots_par_minute, cut_rhythm_target_s, rapport))
    rapport.infractions.extend(
        _densite(script, mots_par_minute, densite_cible, rapport, recherche))
    rapport.infractions.extend(_sponsor(script, mots_par_minute))
    rapport.infractions.extend(_texte_ecran(script))
    rapport.infractions.extend(_duree(script, duree_cible_s, tolerance_duree))
    return rapport


# --------------------------------------------------------------------------------------
# Contrôles
# --------------------------------------------------------------------------------------

def _hook(
    script: Script, patterns: Patterns, plafond: int, plancher: int | None,
) -> list[Infraction]:
    """Longueur, formulation et élément clé du type tiré."""
    candidat = hooks_module.noter(script.hook.text, script.hook.type, plafond, patterns,
                                  plancher_mots=plancher)
    if not candidat.infractions:
        return []
    element = patterns.elements_cles.get(script.hook.type, "")
    return [Infraction(
        code="hook",
        message=" ; ".join(candidat.infractions) + f" (note {candidat.score:.0f}/100)",
        consigne=(
            f"The hook breaks its own type. Rewrite it as a {script.hook.type} hook of at most "
            f"{plafond} words, carrying a clear {element or 'opening'}, with none of the "
            "forbidden openings."
        ),
        segments=["seg_00"],
        bloquante=candidat.score < hooks_module.SCORE_ACCEPTABLE,
    )]


def _proscrites(script: Script, patterns: Patterns) -> list[Infraction]:
    """Formulations proscrites, où qu'elles soient dans le script."""
    infractions: list[Infraction] = []
    for segment in script.segments:
        trouvees = patterns.proscrites_trouvees(segment.narration)
        if trouvees:
            infractions.append(Infraction(
                code="formulation_proscrite",
                message=f"{segment.id} : " + ", ".join(f"« {t} »" for t in trouvees),
                consigne=(
                    f"Segment {segment.id} uses banned wording: "
                    + ", ".join(f'"{t}"' for t in trouvees)
                    + ". Say the same thing without it."
                ),
                segments=[segment.id],
            ))
    return infractions


def _boucles(
    script: Script, patterns: Patterns, minimum: int, rapport: Rapport, juge: bool,
    seed: int, racine: Path | None, trace: Any | None,
) -> list[Infraction]:
    """Plantation et paiement, par marqueurs puis par juge sémantique."""
    boucles = loops_module.apparier(script, patterns)
    if juge and boucles:
        boucles = loops_module.juger(script, boucles, seed=seed, racine=racine, trace=trace)
    rapport.boucles = boucles
    plantees, payees = loops_module.resume(boucles)
    infractions: list[Infraction] = []

    exemples = ", ".join(f'"{m}"' for m in patterns.marqueurs_plantation[:4])
    for boucle in boucles:
        if not boucle.plantee:
            infractions.append(Infraction(
                code="boucle_non_plantee",
                message=(f"{boucle.plant_id} est étiqueté `plant` mais ne promet rien : aucun "
                         "marqueur de promesse dans ses deux dernières phrases"),
                consigne=(f"Segment {boucle.plant_id} must end on an explicit promise of "
                          f"something revealed later, in the manner of {exemples}."),
                segments=[boucle.plant_id],
            ))
        if boucle.payoff_id is None:
            infractions.append(Infraction(
                code="boucle_sans_paiement",
                message=f"{boucle.plant_id} : aucun segment `payoff` ne vient après",
                consigne=(f"The promise made in {boucle.plant_id} is never answered. Answer it "
                          "before the conclusion."),
                segments=[boucle.plant_id],
            ))
        elif not boucle.marqueurs_payoff:
            infractions.append(Infraction(
                code="boucle_non_payee",
                message=(f"{boucle.payoff_id} est étiqueté `payoff` mais ne renvoie à aucune "
                         "promesse : aucun marqueur de paiement dans ses deux premières phrases"),
                consigne=(f"Segment {boucle.payoff_id} must open by answering, in so many words, "
                          f"the promise made in {boucle.plant_id}."),
                segments=[boucle.payoff_id],
            ))
        elif boucle.coherente is False:
            infractions.append(Infraction(
                code="boucle_incoherente",
                message=(f"{boucle.payoff_id} ne répond pas à la promesse de {boucle.plant_id} "
                         f"— juge : « {boucle.motif} »"),
                consigne=(f"Segment {boucle.payoff_id} does not deliver what {boucle.plant_id} "
                          f"promised ({boucle.motif}). Deliver it in the first sentence."),
                segments=[boucle.payoff_id],
            ))
        elif boucle.coherente is None and juge:
            infractions.append(Infraction(
                code="boucle_non_jugee",
                message=(f"{boucle.plant_id} → {boucle.payoff_id} : cohérence non jugée "
                         f"({boucle.motif or 'juge indisponible'}) — non vérifié, pas réussi"),
                bloquante=False,
            ))

    if payees < minimum:
        infractions.append(Infraction(
            code="boucles_insuffisantes",
            message=(f"{payees} boucle(s) réellement payée(s) pour {minimum} exigées "
                     f"({plantees} plantée(s))"),
            consigne=(f"The video must carry {minimum} open loops that are actually promised "
                      "and actually answered."),
            segments=[b.plant_id for b in boucles if not b.payee],
        ))
    return infractions


def _ruptures(
    script: Script, mots_par_minute: float, cut_rhythm_target_s: float, rapport: Rapport,
) -> list[Infraction]:
    """Une rupture par tranche de N secondes, N = 4 × rythme de coupe, borné [20, 45]."""
    cadence = interrupts_module.intervalle_s(cut_rhythm_target_s)
    rapport.cadence_s = round(cadence, 1)
    horloge = 0.0
    instants: list[float] = []
    # `interrupts.py` **refuse par construction** de poser une rupture sur un `hook`, un
    # `sponsor` ou une `conclusion` (`ROLES_SANS_RUPTURE`). Mesurer l'écart jusqu'aux bords de
    # la vidéo revenait donc à reprocher au script une décision du planificateur : sur `avwf`
    # le 18/09/2026, la conclusion de 21 s en fin de vidéo produisait 46 s d'écart, infraction
    # **qu'aucune régénération ne pouvait corriger** — les trois essais y passaient. L'écart se
    # mesure sur le **corps** de la vidéo : du premier segment éligible au dernier.
    debut_corps: float | None = None
    fin_corps = 0.0
    for segment in script.segments:
        duree = segment.word_count / (mots_par_minute / 60) if mots_par_minute else 0.0
        if segment.role not in interrupts_module.ROLES_SANS_RUPTURE:
            if debut_corps is None:
                debut_corps = horloge
            fin_corps = horloge + duree
        if segment.interrupt is not None:
            instants.append(horloge + segment.interrupt.at_s_relative)
        horloge += duree
    if debut_corps is None:          # aucun segment éligible : le corps est vide
        debut_corps, fin_corps = 0.0, horloge
    rapport.ruptures_posees = len(instants)
    if not instants:
        rapport.ecart_rupture_max_s = round(horloge, 1)
        return [Infraction(
            code="ruptures_absentes",
            message=f"aucune rupture de rythme sur {horloge:.0f} s (cadence visée {cadence:.0f} s)",
            consigne="", bloquante=True,
        )]
    bornes = [debut_corps, *sorted(instants), fin_corps]
    paires = list(zip(bornes, bornes[1:]))
    debut_pire, fin_pire = max(paires, key=lambda ab: ab[1] - ab[0])
    ecart = fin_pire - debut_pire
    rapport.ecart_rupture_max_s = round(ecart, 1)
    if ecart > cadence * ECART_RUPTURE_TOLERE:
        # Un segment ne porte **qu'une** rupture (`ScriptSegment.interrupt`). Un écart trop
        # large vient donc d'un segment plus long que la cadence, jamais du texte lui-même :
        # sur `avwf` le 18/09/2026, `seg_25` durait 39,4 s pour une cadence de 23,4 s. Tant
        # que l'infraction ne **nommait** pas ce segment, la passe de réparation n'avait rien
        # à réécrire et les trois essais se perdaient sur « non corrigible ». On le nomme, et
        # la consigne demande de le raccourcir — ce qui libère une tranche de cadence.
        # **Seulement** les segments qui chevauchent le pire écart. Nommer tous ceux plus
        # longs que la cadence revenait à demander de raccourcir presque tout le script :
        # mesuré le 18/09/2026, il perdait 38 % de sa durée et tombait en
        # `duree_hors_tolerance`, l'infraction suivante. Une réparation ne corrige qu'un point.
        trop_longs: list[str] = []
        horloge_seg = 0.0
        for segment, duree in _durees(script, mots_par_minute):
            fin_seg = horloge_seg + duree
            chevauche = horloge_seg < fin_pire and fin_seg > debut_pire
            if (chevauche and duree > cadence
                    and segment.role not in interrupts_module.ROLES_SANS_RUPTURE):
                trop_longs.append(segment.id)
            horloge_seg = fin_seg
        return [Infraction(
            code="rupture_trop_espacee",
            message=(f"{ecart:.0f} s sans rupture pour une cadence de {cadence:.0f} s "
                     f"({len(instants)} rupture(s) posée(s))"
                     + (f" — segment(s) plus long(s) que la cadence : {', '.join(trop_longs)}"
                        if trop_longs else "")),
            consigne=(
                f"These segments last longer than the {cadence:.0f} s rhythm target and can "
                "carry only one rhythm break each. Shorten each of them to about "
                f"{cadence:.0f} s of speech, cutting asides and repetitions, never a fact."
            ) if trop_longs else "",
            segments=trop_longs, bloquante=True,
        )]
    return []


def _durees(script: Script, mots_par_minute: float):
    """`(segment, durée parlée estimée)` pour chaque segment, au débit de la niche."""
    for segment in script.segments:
        yield segment, (segment.word_count / (mots_par_minute / 60) if mots_par_minute else 0.0)


def _densite(
    script: Script, mots_par_minute: float, cible: float | None, rapport: Rapport,
    recherche: Research | None,
) -> list[Infraction]:
    """Faits par minute, par règles, contre la cible de la niche."""
    comptage = density_module.mesurer_script(script, mots_par_minute)
    rapport.densite = comptage
    if cible is None:
        return [Infraction(
            code="densite_sans_cible",
            message=("aucune cible de densité pour cette niche "
                     "(`config/niches/<niche>.yaml → densite_faits_par_minute.cible`)"),
            bloquante=False,
        )]
    if comptage.faits_par_minute >= cible:
        return []
    ids = ""
    if recherche is not None:
        ids = " Use only these fact ids: " + ", ".join(f.id for f in recherche.facts) + "."
    return [Infraction(
        code="densite_sous_cible",
        message=(f"{comptage.faits_par_minute:.2f} fait(s)/min pour une cible de {cible:.2f} "
                 f"({comptage.mots} mots, {comptage.duree_min:.1f} min)"),
        consigne=("The narration is too thin: it carries "
                  f"{comptage.faits_par_minute:.1f} verifiable facts per minute against a target "
                  f"of {cible:.1f}. Add facts taken from the fact list, never invented."
                  + ids),
        segments=density_module.segments_a_enrichir(script),
    )]


def _sponsor(script: Script, mots_par_minute: float) -> list[Infraction]:
    """Le segment sponsorisé ne commence pas avant la 60ᵉ seconde."""
    horloge = 0.0
    for segment in script.segments:
        duree = segment.word_count / (mots_par_minute / 60) if mots_par_minute else 0.0
        if segment.role == "sponsor" and horloge < SPONSOR_MIN_S:
            return [Infraction(
                code="sponsor_trop_tot",
                message=(f"{segment.id} : segment sponsorisé à {horloge:.0f} s, "
                         f"plancher {SPONSOR_MIN_S:.0f} s (contrôle bloquant du banc)"),
                consigne="", segments=[segment.id],
            )]
        horloge += duree
    return []


def _texte_ecran(script: Script) -> list[Infraction]:
    """Texte à l'écran : six mots au maximum, plafond du rendu."""
    fautifs = [(s.id, s.on_screen_text) for s in script.segments
               if s.on_screen_text and len(s.on_screen_text.split()) > MOTS_ECRAN_MAX]
    if not fautifs:
        return []
    return [Infraction(
        code="texte_ecran_trop_long",
        message="; ".join(f"{i} : {len(t.split())} mots (« {t} »)" for i, t in fautifs),
        consigne=(f"On-screen text is capped at {MOTS_ECRAN_MAX} words: "
                  + ", ".join(i for i, _ in fautifs)),
        segments=[i for i, _ in fautifs],
    )]


def _duree(script: Script, cible_s: float, tolerance: float) -> list[Infraction]:
    """Durée estimée à ± `tolerance` de la cible du run."""
    if cible_s <= 0:
        return []
    ecart = (script.estimated_duration_s - cible_s) / cible_s
    if abs(ecart) <= tolerance:
        return []
    return [Infraction(
        code="duree_hors_tolerance",
        message=(f"{script.estimated_duration_s:.0f} s estimées pour une cible de {cible_s:.0f} s "
                 f"({ecart * 100:+.1f} %, tolérance ± {tolerance * 100:.0f} %)"),
        consigne=("The script is " + ("too long" if ecart > 0 else "too short")
                  + f" by {abs(ecart) * 100:.0f} %."),
        # La durée se corrige par la boucle de calage de `script.py`, pas par une réécriture
        # éditoriale : l'infraction est rapportée, elle ne déclenche pas de régénération.
        bloquante=False,
    )]
