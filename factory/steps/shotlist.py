"""Étape `shotlist` — le rythme de coupe de la niche devient un découpage effectif.

**Le rythme de coupe est la cible chiffrée la plus directement exploitable du registre.** Cette
étape la transforme en `shots[]` et **refuse de livrer** une liste dont la médiane hors hook sort
de ± 10 % de la cible : une cible non vérifiée n'est pas une cible.

Comment la médiane tombe juste malgré le jitter :

1. **Fenêtres.** Chaque segment de `voice/timings.json` donne une fenêtre ; la respiration qui le
   précède lui est rattachée (un changement de plan pendant un silence est naturel, et sans cela
   les clips ne pavent pas la piste). Les fenêtres pavent donc `[0 ; total_duration_s]` sans trou.
2. **Ancres.** Une rupture (`segment.interrupt`) pose une coupe forcée à sa position ; elle découpe
   la fenêtre en sous-fenêtres traitées indépendamment.
3. **Nombre de plans.** `n = round(durée / cible_effective)`, corrigé tant que `durée/n` sort de
   `[0,7 ; 1,3] × cible`. C'est ce choix qui fixe la médiane : `durée/n` est proche de la cible par
   construction, et le jitter ne fait que la disperser sans la déplacer.
4. **Jitter.** Poids tirés dans `[0,7 ; 1,3]` puis **normalisés** sur la durée de la sous-fenêtre :
   la somme est exacte, donc aucune dérive cumulée, et la médiane reste centrée.
5. **Frontières de mots.** Chaque coupe interne glisse vers la frontière de mot la plus proche
   (`words.json`), dans une fenêtre de 0,6 s. Au-delà, il n'y a pas de mot à respecter : la coupe
   tombe dans un silence et reste où elle est.
6. **Hook.** Cible × 0,6, chaque plan plafonné à `hook_shots_max_s = cible × facteur_hook` (0,7).
   Les plans du hook sont **exclus de la médiane** : ils sont volontairement plus rapides.

Si la médiane sort de la tolérance, l'étape **rejoue** avec une autre graine puis un jitter réduit
(3 essais) avant d'échouer en code 2.
"""

from __future__ import annotations

import hashlib
import random
import re
import statistics
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from factory.core import config as config_module
from factory.core import db, referentiel, runs
from factory.core.models import (
    AssetRequest,
    Channel,
    Script,
    ScriptSegment,
    Shot,
    Shotlist,
    StatsShotlist,
    Style,
    Timings,
    Words,
)
from factory.core.paths import RunPaths, racine_projet

#: Bornes du jitter, en multiple de la cible effective (`[0,7 ; 1,3]`, prompt de l'étape 12.1).
JITTER_MIN, JITTER_MAX = 0.7, 1.3
#: Le hook vise des plans à 0,6 × cible, puis chaque plan y est plafonné à `hook_shots_max_s`.
FACTEUR_DUREE_HOOK = 0.6
#: Tolérance sur la médiane hors hook (`INTERFACES.md` → `stats.tolerance`).
TOLERANCE = 0.10
#: Nombre d'essais avant d'échouer : graine, puis jitter resserré, puis jitter nul.
ESSAIS_MAX = 3
#: Une coupe ne glisse pas plus loin que cela pour trouver une frontière de mot.
FENETRE_FRONTIERE_S = 0.6
#: Aucun plan sous cette durée : en dessous, l'œil ne voit pas le plan, il voit un clignotement.
DUREE_MIN_S = 1.0

#: Type d'asset demandé par plan selon le moteur, et type de remplacement sur une rupture.
#: Une rupture « force un changement de type d'asset » — quand le moteur en offre deux.
TYPES_PAR_MOTEUR: dict[str, tuple[str, str]] = {
    "cartes": ("card", "card"),
    "illustre_anime": ("image", "stock"),
    "documentaire": ("stock", "image"),
    "motion_design": ("card", "image"),
    "whiteboard": ("card", "image"),
    "avatar2d": ("avatar", "image"),
}

#: Gabarits du moteur « cartes », portés par `asset_request.prompt_or_keywords`.
TEMPLATES_CARTES: tuple[str, ...] = ("plein", "bandeau_bas", "carte_centrale")

#: Alternance de mouvement par défaut ; `config/styles/<id>.yaml` → `params.motion.alternance`
#: la surcharge. `parallax` exige une carte de profondeur : jamais ici.
ALTERNANCE_MOUVEMENT: tuple[str, ...] = ("zoom_in", "static", "zoom_out", "pan")

#: Précisions ajoutées à l'intention visuelle d'un segment pour les plans qui suivent le premier.
PRECISIONS: tuple[str, ...] = ("plan large", "détail", "variation de cadre", "contre-champ")


#: Mots qui font présumer **une silhouette ou un visage humain** dans l'image demandée.
#: `CONFORMITE.md` § 3 couche 3 (contrôle 27, **bloquant**) déclenche la mention « Images
#: virtuelles » sur « un visage ou une silhouette humaine, **réaliste ou non** » : une illustration
#: plate de bonhomme la déclenche autant qu'un portrait. Quatre langues, parce que l'intention est
#: écrite dans la langue de la chaîne (fr, en, es) et que le prompt part en anglais.
#:
#: **Ce que cette liste est, et ce qu'elle n'est pas.** C'est un **plancher**, volontairement
#: généreux : sur-déclencher ne coûte qu'une ligne de divulgation, sous-déclencher est un
#: manquement opposable. Elle ne remplace pas une détection sur l'image produite — seule celle-ci
#: verrait un corps qu'aucun mot n'annonçait (`STATE.md` § Bloqué, entrée É13.2).
VOCABULAIRE_PERSONNE: frozenset[str] = frozenset({
    # français
    "personne", "personnes", "gens", "humain", "humaine", "humains", "silhouette", "silhouettes",
    "visage", "visages", "corps", "main", "mains", "bras", "jambe", "jambes", "epaule", "epaules",
    "torse", "dos", "tete", "homme", "hommes", "femme", "femmes", "enfant", "enfants", "adulte",
    "adultes", "athlete", "athletes", "sportif", "sportive", "coureur", "coureuse", "patient",
    "patiente", "medecin", "silhouettes", "bonhomme", "personnage", "personnages", "foule",
    # anglais (le prompt est traduit avant génération)
    "person", "people", "human", "humans", "figure", "figures", "silhouette", "face", "faces",
    "body", "bodies", "hand", "hands", "arm", "arms", "leg", "legs", "shoulder", "shoulders",
    "torso", "back", "head", "man", "men", "woman", "women", "child", "children", "adult",
    "athlete", "athletes", "runner", "patient", "doctor", "nurse", "crowd", "character",
    # espagnol
    "persona", "personas", "gente", "humano", "humana", "silueta", "rostro", "cuerpo", "mano",
    "manos", "brazo", "brazos", "pierna", "piernas", "hombro", "cabeza", "hombre", "mujer",
    "nino", "nina", "adulto", "atleta", "corredor", "paciente", "medico", "multitud",
})


def figure_une_personne(intention: str) -> bool:
    """L'intention annonce-t-elle un corps humain à l'image ?

    Comparaison **mot à mot** sur la forme sans accents ni ponctuation : « mains » déclenche,
    « domaines » non — ce qu'une recherche de sous-chaîne ne saurait pas faire.

    Mesuré le 18/09/2026 : avant ce câblage, `AssetRequest.contains_person` était la **constante
    `False`** (`shotlist.py:434`). `virtual_images_mention` ne pouvait donc jamais valoir `True`,
    et le contrôle 27 de `CONFORMITE.md`, marqué « Bloquant », était du code mort. Le run
    `bms-science-fr-20260917-rtmk` déclarait ses 124 plans sans personne alors que son premier
    prompt est « Des mains saisissent une barre de fer » et que sa miniature montre deux bras.
    """
    sans_accent = unicodedata.normalize("NFKD", intention)
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    mots = re.split(r"[^a-z0-9]+", sans_accent.lower())
    return any(mot in VOCABULAIRE_PERSONNE for mot in mots)


class ContratNonSatisfait(RuntimeError):
    """Entrée manquante ou médiane hors tolérance : code de sortie 2 (`INTERFACES.md` § 4)."""


@dataclass
class Fenetre:
    """Une portion de piste attribuée à un segment de script."""

    segment: ScriptSegment
    debut_s: float
    fin_s: float

    @property
    def duree_s(self) -> float:
        return self.fin_s - self.debut_s


@dataclass
class PlanBrut:
    """Un plan avant mise au contrat : bornes, segment, et ce qui l'a déclenché."""

    segment: ScriptSegment
    debut_s: float
    fin_s: float
    premier_du_segment: bool
    rupture: bool

    @property
    def duree_s(self) -> float:
        return self.fin_s - self.debut_s


@dataclass
class ResultatShotlist:
    """Ce que l'étape a produit, pour l'affichage CLI."""

    shotlist: Shotlist
    essais: int
    graine: int
    jitter: float
    cible_s: float
    source_cible: str
    mediane_hook_s: float | None
    ecart_relatif: float
    secondes: float
    alertes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Cible de rythme
# --------------------------------------------------------------------------------------


def facteur_rythme_appris(niche_nom: str, racine: Path | None) -> float:
    """Facteur de `learned/weights.json → cut_rhythm.<niche>.factor`, borné à ±20 % ; 1,0 sinon.

    Ne s'applique qu'à une cible venue du référentiel : une surcharge de style ou de chaîne
    est une décision humaine, l'apprentissage ne la déplace pas.
    """
    from factory.analytics import weights as wmod

    bloc = ((wmod.charger(racine) or {}).get("cut_rhythm") or {}).get(niche_nom) or {}
    try:
        f = float(bloc.get("factor", 1.0))
    except (TypeError, ValueError):
        return 1.0
    return round(min(1.2, max(0.8, f)), 3) if f == f else 1.0


def cible_de_rythme(
    niche_nom: str, channel: Channel, style: Style | None, racine: Path | None,
    cible_spec: float | None,
) -> tuple[float, float, str]:
    """Cible de coupe, facteur de hook, et d'où ils viennent.

    Ordre : surcharge de `config/styles/<id>.yaml` → surcharge de la chaîne → niche
    (`cible_montage`, puis `cible`, puis `fallback_provisoire_s`) → `spec.cut_rhythm_target_s`.
    Une surcharge est une décision, elle doit donc être lisible dans le rapport de l'étape.
    """
    donnees = referentiel.niche(niche_nom, racine).get("rythme_coupe_s", {})
    facteur_hook = float(donnees.get("facteur_hook") or 0.7)

    if style is not None:
        surcharge = style.params.get("rythme_coupe_s") if style.params else None
        if isinstance(surcharge, (int, float)):
            return float(surcharge), facteur_hook, f"config/styles/{style.id}.yaml"
        if isinstance(surcharge, dict) and isinstance(surcharge.get("cible"), (int, float)):
            return float(surcharge["cible"]), facteur_hook, f"config/styles/{style.id}.yaml"

    for cle in ("cible_montage", "cible", "fallback_provisoire_s"):
        valeur = donnees.get(cle)
        if isinstance(valeur, (int, float)):
            source = f"registre/REFERENTIEL.json → {niche_nom}.{cle}"
            ajuste = facteur_rythme_appris(niche_nom, racine)
            if ajuste != 1.0:
                return float(valeur) * ajuste, facteur_hook, f"{source} × {ajuste} (learned/weights.json)"
            return float(valeur), facteur_hook, source

    if cible_spec:
        return float(cible_spec), facteur_hook, "spec.json → cut_rhythm_target_s"
    raise ContratNonSatisfait(
        f"niche {niche_nom} : aucune cible de rythme de coupe utilisable (REFERENTIEL.json)"
    )


# --------------------------------------------------------------------------------------
# Fenêtres et frontières de mots
# --------------------------------------------------------------------------------------


def construire_fenetres(script: Script, timings: Timings, words: Words) -> list[Fenetre]:
    """Pave `[0 ; total_duration_s]` d'une fenêtre par segment de script, sans trou ni recouvrement.

    La respiration qui précède un segment lui est rattachée. Une unité de voix fusionnée
    (`merged_from`) est repartagée entre ses segments d'origine au milieu du silence qui les sépare,
    d'après `words.json` — sinon le plan porterait un `segment_id` faux et la jointure au script
    serait rompue.
    """
    par_id = {segment.id: segment for segment in script.segments}
    debuts_mots: dict[str, float] = {}
    fins_mots: dict[str, float] = {}
    for mot in words.words:
        debuts_mots.setdefault(mot.seg, mot.start_s)
        fins_mots[mot.seg] = mot.end_s

    fenetres: list[Fenetre] = []
    curseur = 0.0
    for index, unite in enumerate(timings.segments):
        fin = unite.end_s if index < len(timings.segments) - 1 else timings.total_duration_s
        # `merged_from` porte DÉJÀ l'id de l'unité (mesuré le 18/09 sur le run EN :
        # seg_08 → ['seg_08', 'seg_09']). Sans déduplication, le segment est compté deux
        # fois : 31 fenêtres pour 28 segments, des bornes réparties sur un id fantôme, et
        # une fenêtre de 274 s qui recouvre tout son segment. Le défaut dormait tant
        # qu'aucun segment n'était assez court pour que la voix le fusionne.
        ids = list(dict.fromkeys([unite.id, *unite.merged_from]))
        ids = [identifiant for identifiant in ids if identifiant in par_id]
        if not ids:
            raise ContratNonSatisfait(
                f"timings : segment {unite.id} absent de script.json — jointure impossible"
            )
        if len(ids) == 1:
            fenetres.append(Fenetre(par_id[ids[0]], curseur, fin))
        else:
            ids.sort(key=lambda identifiant: debuts_mots.get(identifiant, 0.0))
            bornes = [curseur]
            for gauche, droite in zip(ids, ids[1:]):
                fin_gauche = fins_mots.get(gauche)
                debut_droite = debuts_mots.get(droite)
                if fin_gauche is None or debut_droite is None or debut_droite < fin_gauche:
                    bornes.append(curseur + (fin - curseur) * len(bornes) / len(ids))
                else:
                    bornes.append((fin_gauche + debut_droite) / 2)
            bornes.append(fin)
            for rang, identifiant in enumerate(ids):
                fenetres.append(Fenetre(par_id[identifiant], bornes[rang], bornes[rang + 1]))
        curseur = fin
    return fenetres


def frontieres_de_mots(words: Words) -> list[float]:
    """Instants où l'on peut couper sans traverser un mot, triés.

    Entre deux mots séparés par un silence, la frontière est au milieu du silence ; collés, c'est
    la fin du premier. Les bornes de la piste ne sont pas des frontières : elles sont imposées.
    """
    bornes: list[float] = []
    mots = words.words
    for gauche, droite in zip(mots, mots[1:]):
        if droite.start_s >= gauche.end_s:
            bornes.append((gauche.end_s + droite.start_s) / 2)
        else:
            bornes.append(gauche.end_s)
    return sorted(bornes)


def glisser_sur_frontiere(instant: float, frontieres: list[float], fenetre_s: float) -> float:
    """Déplace une coupe sur la frontière de mot la plus proche, si elle est à portée."""
    if not frontieres:
        return instant
    import bisect

    position = bisect.bisect_left(frontieres, instant)
    candidats = [c for c in frontieres[max(0, position - 1):position + 1]]
    if not candidats:
        return instant
    meilleure = min(candidats, key=lambda c: abs(c - instant))
    return meilleure if abs(meilleure - instant) <= fenetre_s else instant


# --------------------------------------------------------------------------------------
# Découpage
# --------------------------------------------------------------------------------------


def nombre_de_plans(duree_s: float, cible_s: float) -> int:
    """Nombre de plans qui rapproche le plus `durée/n` de la cible, dans la bande de jitter.

    C'est ici que se joue la médiane : la corriger après coup serait la truquer.
    """
    n = max(1, round(duree_s / cible_s))
    while n > 1 and duree_s / n < JITTER_MIN * cible_s:
        n -= 1
    while duree_s / n > JITTER_MAX * cible_s:
        n += 1
    return n


def decouper_sous_fenetre(
    debut_s: float, fin_s: float, cible_s: float, jitter: float, tirage: random.Random
) -> list[float]:
    """Durées d'une sous-fenêtre : jitter tiré puis **normalisé** sur la durée exacte."""
    duree = fin_s - debut_s
    if duree <= 0:
        return []
    n = nombre_de_plans(duree, cible_s)
    if n == 1:
        return [duree]
    poids = [tirage.uniform(1 - jitter, 1 + jitter) for _ in range(n)]
    somme = sum(poids)
    return [duree * poids_i / somme for poids_i in poids]


def plans_de_fenetre(
    fenetre: Fenetre, cible_s: float, cible_hook_s: float, plafond_hook_s: float,
    jitter: float, tirage: random.Random, frontieres: list[float],
) -> list[PlanBrut]:
    """Découpe une fenêtre : ancres de rupture, jitter, glissement sur frontières, fusion des trop courts."""
    est_hook = fenetre.segment.role == "hook"
    cible_effective = cible_hook_s if est_hook else cible_s

    ancres: list[float] = []
    rupture = fenetre.segment.interrupt
    if rupture is not None:
        instant = fenetre.debut_s + rupture.at_s_relative
        if fenetre.debut_s + DUREE_MIN_S < instant < fenetre.fin_s - DUREE_MIN_S:
            ancres.append(instant)

    bornes = [fenetre.debut_s, *ancres, fenetre.fin_s]
    coupes: list[float] = [fenetre.debut_s]
    est_ancre: set[int] = set()
    for gauche, droite in zip(bornes, bornes[1:]):
        if gauche in ancres:
            est_ancre.add(len(coupes) - 1)
        curseur = gauche
        durees = decouper_sous_fenetre(gauche, droite, cible_effective, jitter, tirage)
        for duree in durees[:-1]:
            curseur += duree
            coupes.append(curseur)
        coupes.append(droite)
    coupes = sorted(set(coupes))

    # Les bornes de fenêtre sont imposées (elles pavent la piste) ; seules les coupes internes
    # glissent vers une frontière de mot.
    glissees = [coupes[0]]
    for instant in coupes[1:-1]:
        glissees.append(glisser_sur_frontiere(instant, frontieres, FENETRE_FRONTIERE_S))
    glissees.append(coupes[-1])

    # Le glissement peut avoir rapproché deux coupes : on supprime celles qui créent un plan
    # sous le plancher, en gardant toujours les deux bornes.
    retenues = [glissees[0]]
    for instant in glissees[1:-1]:
        if instant - retenues[-1] >= DUREE_MIN_S:
            retenues.append(instant)
    if len(retenues) > 1 and glissees[-1] - retenues[-1] < DUREE_MIN_S:
        retenues.pop()
    retenues.append(glissees[-1])

    plans: list[PlanBrut] = []
    for rang, (debut, fin) in enumerate(zip(retenues, retenues[1:])):
        sur_ancre = any(abs(debut - ancre) <= FENETRE_FRONTIERE_S for ancre in ancres)
        plans.append(PlanBrut(
            segment=fenetre.segment, debut_s=debut, fin_s=fin,
            premier_du_segment=(rang == 0), rupture=sur_ancre,
        ))

    if est_hook:
        plans = _plafonner_hook(plans, plafond_hook_s)
    return plans


def _plafonner_hook(plans: list[PlanBrut], plafond_s: float) -> list[PlanBrut]:
    """Redécoupe les plans du hook qui dépassent le plafond — le hook coupe vite ou ne sert à rien."""
    sortie: list[PlanBrut] = []
    for plan in plans:
        if plan.duree_s <= plafond_s + 1e-6:
            sortie.append(plan)
            continue
        morceaux = max(2, int(plan.duree_s / plafond_s) + 1)
        pas = plan.duree_s / morceaux
        for index in range(morceaux):
            sortie.append(PlanBrut(
                segment=plan.segment,
                debut_s=plan.debut_s + index * pas,
                fin_s=plan.debut_s + (index + 1) * pas if index < morceaux - 1 else plan.fin_s,
                premier_du_segment=plan.premier_du_segment and index == 0,
                rupture=plan.rupture and index == 0,
            ))
    return sortie


# --------------------------------------------------------------------------------------
# Mise au contrat
# --------------------------------------------------------------------------------------


def graine_de_plan(video_id: str, shot_id: str) -> int:
    """`sha256(video_id + shot_id)` — déterminisme par plan (`INTERFACES.md`)."""
    empreinte = hashlib.sha256(f"{video_id}{shot_id}".encode("utf-8")).hexdigest()
    return int(empreinte[:16], 16)


def _intention(segment: ScriptSegment, rang: int, rupture: bool) -> str:
    """Intention visuelle du plan : celle du segment, précisée pour les plans qui suivent."""
    if rupture:
        return f"{segment.visual_intent} — rupture visuelle, cadre et fond changés"
    if rang == 0:
        return segment.visual_intent
    return f"{segment.visual_intent} — {PRECISIONS[(rang - 1) % len(PRECISIONS)]}"


def _transition(rang_global: int, plan: PlanBrut, transitions_charte: list[str]) -> str:
    """Transition d'entrée, restreinte à `charte.transitions[]`."""
    permises = set(transitions_charte)
    if rang_global == 0:
        voulue = "fade"
    elif plan.rupture:
        voulue = "dip_black"
    elif plan.premier_du_segment:
        voulue = "fade"
    else:
        voulue = "cut"
    return voulue if voulue in permises else "cut"


def _asset_request(
    plan: PlanBrut, rang_global: int, moteur: str, texte_ecran: str | None,
    template_precedent: str | None, rang_dans_segment: int,
) -> tuple[AssetRequest, str | None]:
    """Demande d'asset du plan, et le gabarit retenu s'il y en a un (moteur « cartes »).

    `rang_dans_segment` est le **même** que celui porté par `Shot.visual_intent` : c'est ce qui
    fait que les quatre `PRECISIONS` produisent quatre prompts, donc quatre clés de cache, donc
    quatre images. Mesuré le 18/09/2026 sur le run `bms-science-fr-20260917-rtmk` : tant que ce
    rang était figé à 0/1, les 124 plans ne portaient que **30 prompts distincts** et un seul
    servait **22 plans** — « — détail » était réécrit en « — plan large », « — rupture visuelle »
    jeté. La variété que le découpage écrit dans `visual_intent` n'atteignait jamais l'image.
    """
    base, rupture = TYPES_PAR_MOTEUR.get(moteur, ("image", "stock"))
    type_asset = rupture if plan.rupture else base
    template: str | None = None
    if type_asset == "card":
        rang = rang_global % len(TEMPLATES_CARTES)
        template = TEMPLATES_CARTES[rang]
        if plan.rupture and template == template_precedent:
            template = TEMPLATES_CARTES[(rang + 1) % len(TEMPLATES_CARTES)]
        mots_cles = template
    else:
        # `stock` comme `image` : même intention précisée. La branche `stock` servait l'intention
        # nue, donc les plans de rupture retombaient mot pour mot sur le premier plan de leur
        # segment — 27 collisions sur le run du 17/09.
        mots_cles = _intention(plan.segment, rang_dans_segment, plan.rupture)
    return (
        AssetRequest(
            type=type_asset,  # type: ignore[arg-type]
            prompt_or_keywords=mots_cles,
            # Un plan à texte incrusté n'est jamais réutilisable (validateur `Shot`), et une carte
            # porte toujours la charte d'une chaîne : elle ne franchit pas la frontière de chaîne.
            reuse_ok=False if (texte_ecran or type_asset == "card") else True,
            layer="background",
            contains_person=figure_une_personne(mots_cles),
            realistic=False,
        ),
        template,
    )


def mettre_au_contrat(
    plans: list[PlanBrut], video_id: str, channel: Channel, moteur: str,
    segments_sponsor: set[str], alternance: tuple[str, ...],
) -> list[Shot]:
    """Transforme les plans bruts en `Shot` conformes."""
    shots: list[Shot] = []
    template_precedent: str | None = None
    for rang, plan in enumerate(plans):
        shot_id = f"shot_{rang:02d}" if rang < 100 else f"shot_{rang:03d}"
        rang_dans_segment = sum(
            1 for precedent in plans[:rang] if precedent.segment.id == plan.segment.id
        )
        texte = plan.segment.on_screen_text if plan.premier_du_segment else None
        demande, template = _asset_request(
            plan, rang, moteur, texte, template_precedent, rang_dans_segment,
        )
        template_precedent = template or template_precedent
        mouvement = alternance[rang % len(alternance)]
        if plan.rupture:
            mouvement = alternance[(rang + 1) % len(alternance)]
        debut = round(plan.debut_s, 3)
        fin = round(plan.fin_s, 3)
        shots.append(Shot(
            id=shot_id,
            segment_id=plan.segment.id,
            start_s=debut,
            end_s=fin,
            duration_s=round(fin - debut, 3),
            visual_intent=_intention(plan.segment, rang_dans_segment, plan.rupture),
            on_screen_text=texte,
            asset_request=demande,
            motion=mouvement,  # type: ignore[arg-type]
            transition_in=_transition(rang, plan, list(channel.charte.transitions)),  # type: ignore[arg-type]
            is_sponsor=plan.segment.id in segments_sponsor,
            interrupt=plan.segment.interrupt if plan.rupture else None,
            seed=graine_de_plan(video_id, shot_id),
        ))
    return shots


def statistiques(shots: list[Shot], script: Script) -> tuple[float, float, float, float | None]:
    """Médiane hors hook, p10, p90, médiane du hook. Le hook est exclu : il coupe plus vite exprès."""
    roles = {segment.id: segment.role for segment in script.segments}
    hors_hook = [s.duration_s for s in shots if roles.get(s.segment_id) != "hook"]
    hook = [s.duration_s for s in shots if roles.get(s.segment_id) == "hook"]
    if not hors_hook:
        raise ContratNonSatisfait("shotlist : aucun plan hors hook, médiane non mesurable")
    triees = sorted(hors_hook)
    p10 = triees[max(0, min(len(triees) - 1, int(round(0.10 * (len(triees) - 1)))))]
    p90 = triees[max(0, min(len(triees) - 1, int(round(0.90 * (len(triees) - 1)))))]
    return (
        statistics.median(hors_hook), p10, p90,
        statistics.median(hook) if hook else None,
    )


# --------------------------------------------------------------------------------------
# Étape
# --------------------------------------------------------------------------------------


def executer(
    video_id: str, racine: Path | None = None, style_surcharge: str | None = None,
) -> ResultatShotlist:
    """Produit `shotlist.json` et inscrit le rythme planifié au manifeste."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    chemins = RunPaths.depuis_video_id(video_id, racine)

    for chemin, amont in ((chemins.script, "script"), (chemins.timings, "voice"),
                          (chemins.words, "subtitles")):
        if not chemin.exists():
            raise ContratNonSatisfait(
                f"{chemin.name} absent : lance `factory {amont} --run {video_id}`"
            )
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    timings = Timings.model_validate_json(chemins.timings.read_text(encoding="utf-8"))
    words = Words.model_validate_json(chemins.words.read_text(encoding="utf-8"))

    style_id = style_surcharge or spec.style or channel.style
    style = cfg.styles.get(style_id)
    if style is None:
        # Configuration invalide, pas contrat d'entrée : code 1 (`INTERFACES.md` § 4).
        raise ValueError(
            f"style inconnu : {style_id} (connus : {', '.join(sorted(cfg.styles)) or 'aucun'})"
        )
    moteur = style.engine
    if moteur not in TYPES_PAR_MOTEUR:
        alertes.append(f"moteur {moteur} inconnu du découpage : type d'asset `image` par défaut")

    cible_s, facteur_hook, source_cible = cible_de_rythme(
        spec.niche, channel, style, racine, spec.cut_rhythm_target_s
    )
    plafond_hook_s = cible_s * facteur_hook
    cible_hook_s = cible_s * FACTEUR_DUREE_HOOK

    fenetres = construire_fenetres(script, timings, words)
    frontieres = frontieres_de_mots(words)
    segments_sponsor = {
        segment.id for segment in script.segments
        if segment.disclosure_spoken or (segment.role == "cta" and channel.paid_promotion)
    }
    alternance_brute = None
    if style.params:
        alternance_brute = (style.params.get("motion") or {}).get("alternance")
    alternance = tuple(alternance_brute) if alternance_brute else ALTERNANCE_MOUVEMENT
    if "parallax" in alternance:
        raise ValueError(
            f"config/styles/{style.id}.yaml → motion.alternance : `parallax` exige une carte de "
            "profondeur, que le backend ffmpeg de l'étape 12.1 ne produit pas"
        )

    # Trois essais : graine seule, puis jitter resserré, puis jitter nul. On ne « corrige » jamais
    # la médiane après coup — on rejoue le tirage, et l'on échoue si elle reste hors tolérance.
    essai, dernier_ecart, shots, mesures = 0, 1.0, [], (0.0, 0.0, 0.0, None)
    jitter = (JITTER_MAX - JITTER_MIN) / 2
    graine = spec.seed % (2**32)
    for essai in range(1, ESSAIS_MAX + 1):
        jitter_essai = jitter * {1: 1.0, 2: 0.5, 3: 0.0}[essai]
        tirage = random.Random(graine + essai * 7919)
        bruts: list[PlanBrut] = []
        for fenetre in fenetres:
            bruts.extend(plans_de_fenetre(
                fenetre, cible_s, cible_hook_s, plafond_hook_s, jitter_essai, tirage, frontieres
            ))
        shots = mettre_au_contrat(bruts, video_id, channel, moteur, segments_sponsor, alternance)
        mesures = statistiques(shots, script)
        dernier_ecart = (mesures[0] - cible_s) / cible_s
        if abs(dernier_ecart) <= TOLERANCE:
            if essai > 1:
                alertes.append(
                    f"médiane obtenue au {essai}ᵉ essai (jitter ramené à ±{jitter_essai:.0%})"
                )
            break
    else:
        raise ContratNonSatisfait(
            f"rythme de coupe : médiane hors hook {mesures[0]:.2f} s contre une cible de "
            f"{cible_s:.2f} s, soit {dernier_ecart:+.1%} — hors tolérance de ±{TOLERANCE:.0%} "
            f"après {ESSAIS_MAX} essais (graine {graine}). Source de la cible : {source_cible}"
        )

    mediane, p10, p90, mediane_hook = mesures
    stats = StatsShotlist(
        median_shot_s=round(mediane, 3), target_s=round(cible_s, 3),
        hook_shots_max_s=round(plafond_hook_s, 3), tolerance=TOLERANCE,
        p10_shot_s=round(p10, 3), p90_shot_s=round(p90, 3), n_shots=len(shots),
        median_hook_s=round(mediane_hook, 3) if mediane_hook is not None else None,
    )
    shotlist = Shotlist(stats=stats, shots=shots)
    runs.ecrire_json(chemins.shotlist, shotlist)

    depassements = [s.id for s in shots
                    if script_role(script, s.segment_id) == "hook" and s.duration_s > plafond_hook_s + 0.05]
    if depassements:
        alertes.append(
            f"{len(depassements)} plan(s) du hook au-dessus de {plafond_hook_s:.2f} s : "
            + ", ".join(depassements[:3])
        )
    couverture = sum(s.duration_s for s in shots)
    if abs(couverture - timings.total_duration_s) > 0.1:
        alertes.append(
            f"les plans couvrent {couverture:.2f} s pour une piste de "
            f"{timings.total_duration_s:.2f} s"
        )
    if TYPES_PAR_MOTEUR.get(moteur, ("", ""))[0] == TYPES_PAR_MOTEUR.get(moteur, ("", ""))[1]:
        ruptures = sum(1 for s in shots if s.interrupt is not None)
        alertes.append(
            f"moteur {moteur} : un seul type d'asset (`{TYPES_PAR_MOTEUR[moteur][0]}`) — les "
            f"{ruptures} rupture(s) changent de gabarit et de mouvement, pas de type d'asset"
        )

    secondes = time.perf_counter() - t0
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.cut_rhythm_target_s = round(cible_s, 3)
    from factory.analytics import weights as wmod
    wmod.noter(manifest, wmod.charger(racine), "cut_rhythm", source_cible)
    manifest.decisions.cut_rhythm_planned_s = round(mediane, 3)
    manifest.decisions.interrupts = [s.interrupt for s in shots if s.interrupt is not None]
    manifest.execution.timings["shotlist"] = round(secondes, 3)
    manifest.execution.timings["shotlist_n_shots"] = len(shots)
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()

    return ResultatShotlist(
        shotlist=shotlist, essais=essai, graine=graine, jitter=jitter, cible_s=cible_s,
        source_cible=source_cible, mediane_hook_s=mediane_hook, ecart_relatif=dernier_ecart,
        secondes=secondes, alertes=alertes,
    )


def script_role(script: Script, segment_id: str) -> str:
    """Rôle d'un segment, par identifiant."""
    for segment in script.segments:
        if segment.id == segment_id:
            return segment.role
    return "point"
