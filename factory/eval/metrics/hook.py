"""Famille « hook » — les trois premières secondes, et la forme de l'accroche écrite.

Quatre mesures, dont une bloquante :

1. `hook_visual_change` (**bloquant**) — dans les 3 premières secondes, au moins une coupe
   détectée **ou** du mouvement mesuré entre images. Une accroche sur image fixe et muette est
   le défaut de rétention le mieux établi du registre ; c'est le seul contrôle visuel du banc
   qui refuse de laisser passer.
2. `hook_text_present` — un texte à l'écran dans la fenêtre, lu dans `shotlist.json`
   (paramètre de rendu) et non deviné par OCR.
3. `hook_length` — première phrase du script ≤ `hooks.longueur_mots.mediane` de la niche.
4. `hook_type_rules` — la part **mécaniquement vérifiable** des règles du type de hook tiré.
   Les règles de sens (« verbe d'action conjugué décrivant un événement en cours ») ne sont pas
   vérifiables sans modèle : elles sont comptées comme non vérifiées et nommées dans la note,
   jamais comptées comme réussies.
"""

from __future__ import annotations

import re

from factory.core import referentiel as ref_module
from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def mesurer(contexte: ContexteQc) -> Famille:
    """Changement visuel, texte, longueur et conformité de forme du hook."""
    famille = Famille("hook", poids=contexte.qc.poids.get("hook", 20))
    params = contexte.mesure_param("hook")
    fenetre = float(params.get("fenetre_s", 3.0))

    famille.mesures.append(_changement_visuel(contexte, fenetre, params))
    famille.mesures.append(_texte_present(contexte, fenetre))
    famille.mesures.append(_delai_premier_mot(contexte))
    famille.mesures.extend(_forme_du_hook(contexte))
    famille.mesures.extend(_conformite_au_type(contexte))
    return famille


def _conformite_au_type(contexte: ContexteQc) -> list[Mesure]:
    """Étape 16 : note par règles du hook retenu, et formulations proscrites.

    `hook_type_rules` (ci-dessus) mesure la part des règles de la **taxonomie** qui tiennent ;
    ces deux mesures-ci notent le hook contre les **patrons mesurés** de `patterns_<lang>.yaml` :
    élément clé du type présent, longueur dans la fourchette, aucune formulation d'ouverture
    proscrite. Les deux ne font pas double emploi — la première vient du référentiel, la
    seconde du corpus des 60 vidéos les plus vues.
    """
    script = contexte.script
    if script is None:
        return []
    try:
        from factory.retention import hooks as hooks_module
        from factory.retention import patterns as patterns_module
        patrons = patterns_module.charger(contexte.spec.lang, contexte.racine)
    except (FileNotFoundError, ImportError) as erreur:
        return [Mesure(
            nom="hook_pattern_score", valeur=None, unite="note", cible=100.0,
            source="factory/retention/patterns_<lang>.yaml", origine_cible=base.REGISTRE,
            score=None, poids=2, statut="skipped", note=f"patrons indisponibles : {erreur}")]

    bloc = contexte.niche.get("hooks", {}).get("longueur_mots", {})
    plafond = int(round(float(bloc.get("mediane") or 0))) or 40
    plancher = int(round(float(bloc.get("p25") or plafond * 0.6)))
    candidat = hooks_module.noter(script.hook.text, script.hook.type, plafond, patrons,
                                  plancher_mots=plancher)
    element = patrons.elements_cles.get(script.hook.type, "—")
    mesures = [Mesure(
        nom="hook_pattern_score", valeur=round(candidat.score, 1), unite="note",
        cible=100.0, source=f"règles de rétention du type {script.hook.type}",
        origine_cible=(f"{base.REGISTRE} — patrons mesurés sur les 60 vidéos les plus vues "
                       f"(élément clé : {element})"),
        score=candidat.score, poids=2, statut=base.statut_depuis(candidat.score),
        note=" ; ".join(candidat.infractions) or "aucune infraction de forme",
    )]

    proscrites = patrons.proscrites_trouvees(script.hook.text)
    mesures.append(Mesure(
        nom="hook_forbidden_wording", valeur=not proscrites, unite="booléen", cible=True,
        source="patterns_<lang>.yaml — formulations_proscrites",
        origine_cible=(f"{base.REGISTRE} — {len(patrons.formulations_proscrites)} formulations "
                       "relevées comme absentes des hooks les plus vus"),
        score=base.score_booleen(not proscrites), poids=2,
        statut="pass" if not proscrites else "fail",
        note=("aucune" if not proscrites
              else "trouvées : " + ", ".join(f"« {f} »" for f in proscrites)),
    ))
    return mesures


def _delai_premier_mot(contexte: ContexteQc) -> Mesure:
    """Silence d'ouverture avant le premier mot prononcé.

    Objection D3 du contradicteur, retenue : l'abandon des trois premières secondes était
    mesuré à l'image et jamais au son. Une vidéo qui commence par deux secondes de rien perd
    son spectateur avant d'avoir parlé. Aucune valeur de registre — l'audio des chaînes tierces
    n'est jamais téléchargé — le seuil est une décision de production.
    """
    seuil = contexte.seuil("hook_first_word")
    maximum = float(seuil.get("max", 1.5))
    donnees = contexte.words
    if not donnees or not donnees.get("words"):
        return Mesure(
            nom="hook_first_word", valeur=None, unite="s", cible=maximum,
            source="words.json", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="words.json absent",
        )
    delai = min(float(m["start_s"]) for m in donnees["words"])
    score = base.score_max(delai, maximum, float(seuil.get("zero", 5.0)))
    return Mesure(
        nom="hook_first_word", valeur=round(delai, 2), unite="s", cible=maximum,
        source="words.json — premier mot prononcé",
        origine_cible=f"{base.DECISION} — aucune mesure de registre (audio non téléchargé)",
        score=score, poids=1, statut=base.statut_depuis(score),
        note="silence d'ouverture : ce que le spectateur entend avant qu'on lui parle",
    )


def _changement_visuel(contexte: ContexteQc, fenetre: float, params: dict) -> Mesure:
    """Coupes détectées dans la fenêtre, sinon mouvement mesuré entre images extraites."""
    coupes = sum(1 for debut, _ in contexte.scenes if 0.0 < debut < fenetre)
    seuil_mouvement = float(params.get("seuil_mouvement", 0.5))
    mouvement = base.mouvement_moyen(contexte.video, fenetre)
    bouge = coupes >= 1 or (mouvement is not None and mouvement >= seuil_mouvement)
    detail = (
        f"{coupes} coupe(s) avant {fenetre:g} s · mouvement moyen "
        + (f"{mouvement:.2f}" if mouvement is not None else "NON MESURÉ")
        + f" YAVG (seuil {seuil_mouvement:g} ; plan figé ≈ 0, Ken Burns lent ≈ 0,7)"
    )
    return Mesure(
        nom="hook_visual_change", valeur=bouge, unite="booléen", cible=True,
        source="PySceneDetect + ffmpeg tblend=difference,signalstats (YAVG)",
        origine_cible=f"{base.DECISION} — bloquant imposé par le prompt de l'étape 15",
        score=base.score_booleen(bouge), poids=3, bloquant=True,
        statut="pass" if bouge else "fail", note=detail,
    )


def _texte_present(contexte: ContexteQc, fenetre: float) -> Mesure:
    """Texte à l'écran dans la fenêtre du hook, lu dans les paramètres de rendu."""
    shotlist = contexte.shotlist
    if shotlist is None:
        return Mesure(
            nom="hook_text_present", valeur=None, unite="booléen", cible=True,
            source="shotlist.json", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="shotlist.json absent",
        )
    dans_fenetre = [s for s in shotlist.shots if s.start_s < fenetre]
    avec_texte = [s for s in dans_fenetre if (s.on_screen_text or "").strip()]
    present = bool(avec_texte)
    return Mesure(
        nom="hook_text_present", valeur=present, unite="booléen", cible=True,
        source="shotlist.json — on_screen_text (paramètre de rendu, pas d'OCR)",
        origine_cible=f"{base.DECISION} — décision de production",
        score=base.score_booleen(present), poids=1, bloquant=False,
        statut="pass" if present else "fail",
        note=(
            f"{len(avec_texte)}/{len(dans_fenetre)} plan(s) à texte dans les {fenetre:g} s"
            + (f" — « {avec_texte[0].on_screen_text} »" if avec_texte else "")
        ),
    )


_FIN_DE_PHRASE = re.compile(r"[.!?…]+")


def _forme_du_hook(contexte: ContexteQc) -> list[Mesure]:
    """Longueur de la première phrase et règles vérifiables du type de hook enregistré."""
    script = contexte.script
    bloc = contexte.niche.get("hooks", {}).get("longueur_mots", {})
    cible = bloc.get("mediane")
    if script is None:
        return [Mesure(
            nom="hook_length", valeur=None, unite="mots", cible=cible, source="script.json",
            origine_cible=base.REGISTRE, score=None, poids=2, statut="skipped",
            note="script.json absent",
        )]

    texte = script.hook.text.strip()
    premiere = next((p.strip() for p in _FIN_DE_PHRASE.split(texte) if p.strip()), texte)
    mots = len(premiere.split())
    mesures: list[Mesure] = []
    if cible is None:
        mesures.append(Mesure(
            nom="hook_length", valeur=mots, unite="mots", cible=None, source="script.json",
            origine_cible=base.REGISTRE, score=None, poids=2, statut="skipped",
            note="pas de longueur de hook mesurée pour cette niche",
        ))
    else:
        # Objection B4, retenue : plafonner à la médiane donnait 100 à un hook de deux mots,
        # qui n'accroche rien. Le corpus mesure aussi un p25 : la note vaut 100 entre p25 et
        # médiane, et tombe de part et d'autre. Le plafond exigé par le prompt de l'étape 15
        # (≤ médiane) est conservé, un plancher lui est ajouté.
        cible = float(cible)
        plancher = float(bloc.get("p25") or cible * 0.6)
        score = base.score_intervalle(mots, plancher, cible, marge=cible)
        mesures.append(Mesure(
            nom="hook_length", valeur=mots, unite="mots", cible=f"{plancher:.0f}–{cible:.0f}",
            source="script.json — première phrase de hook.text",
            origine_cible=(
                f"{base.REGISTRE} — hooks.longueur_mots p25 à mediane "
                f"(n={bloc.get('n')}, n_faible={bloc.get('n_faible')})"
            ),
            score=score, poids=2, statut=base.statut_depuis(score),
            note=(
                f"« {premiere[:70]}{'…' if len(premiere) > 70 else ''} » — trop court accroche "
                "aussi mal que trop long"
            ),
        ))

    mesures.append(_regles_de_type(contexte, script.hook.type, texte))
    return mesures


def _regles_de_type(contexte: ContexteQc, type_hook: str, texte: str) -> Mesure:
    """Part des règles mécaniques du type de hook qui sont tenues.

    Les règles vivent dans `config/qc.yaml` (`hooks.regles_par_type`), pas dans le code :
    la taxonomie du référentiel les écrit en prose, et traduire une prose en code est une
    décision qui doit se relire.
    """
    config = contexte.qc.hooks
    regles = dict(config.get("regles_par_type", {})).get(type_hook)
    taxonomie = ref_module.taxonomie_hooks(contexte.racine).get(type_hook, {})
    n_prose = len(taxonomie.get("regles", []))
    if not regles:
        return Mesure(
            nom="hook_type_rules", valeur=None, unite="part", cible=1.0,
            source="config/qc.yaml — hooks.regles_par_type", origine_cible=base.REGISTRE,
            score=None, poids=2, statut="skipped",
            note=f"aucune règle mécanique écrite pour le type {type_hook}",
        )
    lang = contexte.spec.lang
    lexiques = dict(config.get("lexiques", {})).get(lang, {})
    fenetre = int(config.get("fenetre_mots", 15))
    tenues, echouees = [], []
    for nom in regles:
        verdict = _VERIFICATEURS[nom](texte, lexiques, fenetre) if nom in _VERIFICATEURS else None
        if verdict is None:
            continue
        (tenues if verdict else echouees).append(nom)
    total = len(tenues) + len(echouees)
    if total == 0:
        return Mesure(
            nom="hook_type_rules", valeur=None, unite="part", cible=1.0,
            source="config/qc.yaml — hooks.regles_par_type", origine_cible=base.REGISTRE,
            score=None, poids=2, statut="skipped",
            note=f"aucune règle de {type_hook} n'est vérifiable sans modèle",
        )
    part = len(tenues) / total
    # Objection A3, retenue autrement : le contradicteur proposait de diviser par le nombre de
    # règles écrites au référentiel, ce qui aurait plafonné la note d'un script irréprochable
    # au seul motif que *nous* ne savons pas vérifier les autres — punir la vidéo pour notre
    # limite. Le score reste la part des règles tenues ; c'est le **poids** qui suit la part de
    # règles vérifiables. Un type dont une seule règle sur quatre est mécanisable pèse le quart.
    poids = max(1, round(2 * total / n_prose)) if n_prose else 1
    return Mesure(
        nom="hook_type_rules", valeur=round(part, 3), unite="part",
        cible=1.0, source=f"règles mécaniques de {type_hook} sur hook.text",
        origine_cible=f"{base.REGISTRE} — hooks_taxonomie.{type_hook}.regles",
        score=100.0 * part, poids=poids, statut=base.statut_depuis(100.0 * part),
        note=(
            f"{len(tenues)}/{total} règle(s) mécanique(s) tenue(s) sur {n_prose} écrite(s) "
            f"au référentiel ; non vérifiables sans modèle : {n_prose - total}"
            + (f" ; échec : {', '.join(echouees)}" if echouees else "")
        ),
    )


# -- vérificateurs de règles ----------------------------------------------------------------
# Chacun rend True (tenue), False (violée) ou None (non vérifiable sur ce lexique).

def _sans_deuxieme_personne(texte: str, lexiques: dict, fenetre: int) -> bool | None:
    pronoms = [p.lower() for p in lexiques.get("deuxieme_personne", [])]
    if not pronoms:
        return None
    debut = " ".join(texte.split()[:fenetre]).lower()
    return not any(re.search(rf"\b{re.escape(p)}\b", debut) for p in pronoms)


def _avec_deuxieme_personne(texte: str, lexiques: dict, fenetre: int) -> bool | None:
    verdict = _sans_deuxieme_personne(texte, lexiques, fenetre)
    return None if verdict is None else not verdict


def _sans_question(texte: str, _lexiques: dict, _fenetre: int) -> bool:
    return "?" not in texte


def _avec_question(texte: str, _lexiques: dict, _fenetre: int) -> bool:
    return "?" in texte


def _avec_chiffre(texte: str, _lexiques: dict, _fenetre: int) -> bool:
    return bool(re.search(r"\d", texte))


def _sans_chiffre_en_tete(texte: str, _lexiques: dict, fenetre: int) -> bool:
    return not bool(re.search(r"\d", " ".join(texte.split()[:fenetre])))


def _sans_salutation(texte: str, lexiques: dict, _fenetre: int) -> bool | None:
    formules = [f.lower() for f in lexiques.get("salutations", [])]
    if not formules:
        return None
    debut = texte.lower()[:120]
    return not any(f in debut for f in formules)


def _avec_negation(texte: str, lexiques: dict, _fenetre: int) -> bool | None:
    marqueurs = [m.lower() for m in lexiques.get("negation", [])]
    if not marqueurs:
        return None
    return any(re.search(rf"\b{re.escape(m)}\b", texte.lower()) for m in marqueurs)


_VERIFICATEURS = {
    "sans_deuxieme_personne": _sans_deuxieme_personne,
    "avec_deuxieme_personne": _avec_deuxieme_personne,
    "sans_question": _sans_question,
    "avec_question": _avec_question,
    "avec_chiffre": _avec_chiffre,
    "sans_chiffre_en_tete": _sans_chiffre_en_tete,
    "sans_salutation": _sans_salutation,
    "avec_negation": _avec_negation,
}
