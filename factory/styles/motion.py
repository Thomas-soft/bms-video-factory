"""Moteur « motion design » — scènes Revideo paramétrées par JSON, **aucun pixel généré par IA**.

C'est le style le plus fort réalisable localement (`docs/STYLES.md` : 5/5) et celui de la chaîne
de référence du registre. Il ne coûte ni image de diffusion ni carte de profondeur : tout est
vectoriel, composé par un navigateur sans interface, puis encodé.

Le moteur tient en trois gestes.

1. **Choisir une scène par plan.** Des règles lisent `visual_intent`, le rôle du segment, le texte
   incrusté et les chiffres du script ; le LLM n'est appelé que sur les plans qu'aucune règle ne
   tranche, et par **lots**, jamais un appel par plan — un 9B quantifié coûte une seconde par
   appel, cent appels coûteraient plus cher que le rendu entier.
2. **Rendre par lots.** `render.mjs` rend un lot de plans en **une seule vidéo continue** et un
   seul lancement de Chromium ; le moteur redécoupe ensuite à l'image près. Un lancement coûte
   une dizaine de secondes : le payer une fois pour vingt plans est le premier levier de vitesse.
3. **Alterner.** Deux plans voisins ne portent jamais la même scène : c'est la contrainte que le
   verdict du 16/09 sur la preuve de l'étape 5.2 a imposée (« aucun contraste d'échelle, aucune
   composition hors-centre » — un seul dispositif répété n'est pas du motion design).

Ce que le moteur **ne fait pas** : il ne connaît ni la langue, ni la conformité, ni le montage.
La phrase de divulgation lui est passée (`texte_divulgation`), la palette vient de la charte, les
horodatages viennent de `words.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from factory import video
from factory.core.models import Asset, Channel, Shot, Shotlist
from factory.core.paths import RunPaths
from factory.styles.revideo import (
    MoteurRevideo, RenduRevideoEchoue,
)

#: Scènes **construites** : un objet se fabrique, se transforme ou se disloque à l'écran.
#: Verdict de Thomas du 16/09/2026, qui est le critère de ce moteur et pas une préférence : « ce
#: qui est perçu comme animation n'est pas le déplacement, c'est la construction et la
#: transformation ». Et sur la typographie cinétique, essayée puis écartée : « y'a trop trop de
#: texte pour presque aucune image, aucune animation, que du texte quasiment ».
SCENES_CONSTRUITES: tuple[str, ...] = (
    # Dispositifs d'explication : un objet se fabrique, s'ouvre, se transforme, se compte.
    "assemble", "echelle", "systeme", "coupe", "flux", "transformation",
    "quantite", "chronologie",
    # Dispositifs **joués** : un être occupe le cadre et agit. C'est la grammaire de la chaîne de
    # référence, relevée le 19/09/2026 — une sitcom animée à personnages, « presque aucun texte à
    # l'écran », organes et objets anthropomorphes, plan moyen sous 3 s.
    "tete_parlante", "duo", "groupe", "personnage",
)

#: Scènes de texte. Elles restent au jeu, mais **en ponctuation** : jamais la substance d'un plan.
SCENES_TEXTE: tuple[str, ...] = (
    "kinetic_text", "title_card", "quote", "transition_stinger", "lower_third",
    "list_reveal", "icon_grid",
)

#: Scènes dont le sens repose sur des étiquettes écrites : sans dispositif, elles sont vides.
SCENES_A_ETIQUETTES: frozenset[str] = frozenset({
    "assemble", "systeme", "coupe", "flux", "groupe", "chronologie", "echelle", "quantite",
})

#: Scènes qui affirment un chiffre. Elles ne se choisissent jamais par rotation.
SCENES_CHIFFRE: tuple[str, ...] = ("chart", "stat_counter")

#: Toutes les scènes livrées par `render/src/scenes/`.
SCENES: tuple[str, ...] = SCENES_CONSTRUITES + SCENES_TEXTE + SCENES_CHIFFRE

#: Remplissage quand rien n'a tranché : **que des scènes construites**.
#: Un dispositif joué sur deux : sans cela, la vidéo redevient une infographie narrée, et ce
#: n'est pas ce que fait la chaîne de référence.
ROTATION: tuple[str, ...] = (
    "tete_parlante", "assemble", "duo", "systeme", "personnage", "flux",
    "groupe", "coupe", "tete_parlante", "transformation",
)

#: Ordre des teintes de fond. Pas 0-1-2-3 : dans cet ordre, deux frontières sur quatre séparent
#: deux teintes voisines et la coupe reste invisible (87 plans détectés sur 114 le 19/09). Cet
#: ordre-ci met la plus grande distance possible à chaque frontière.
ORDRE_FONDS: tuple[int, ...] = (0, 2, 1, 3)

#: Plans de moins de 2,6 s : le temps d'une apparition et d'une sortie, pas d'une construction.
ROTATION_COURTE: tuple[str, ...] = ("tete_parlante", "transformation", "kinetic_text")

#: Repli des plans que le metteur en scène n'a pas servis. **Aucune de ces scènes n'a besoin
#: d'étiquettes** : elles se jouent avec la voix et rien d'autre. Sans cette règle, le repli
#: découpait la phrase prononcée et posait « LOOK AT THE » sur une boîte de schéma — mesuré sur
#: l'extrait réel du 19/09.
ROTATION_SANS_ETIQUETTE: tuple[str, ...] = ("tete_parlante", "personnage", "transformation")

#: Part maximale de plans en scène de texte. Un plan sur quatre au plus — au-delà, la vidéo
#: redevient ce que Thomas a refusé le 16/09 puis le 19/09 : « des textes et un peu du motion
#: design très léger ».
PART_TEXTE_MAX = 0.25

#: Icônes disponibles dans `render/src/icons.ts` (Tabler 3.36.0, MIT).
ICONES: tuple[str, ...] = (
    "brain", "heart", "dna", "atom", "microscope", "flask", "bolt", "battery", "clock",
    "calendar", "chart-bar", "trending-up", "trending-down", "scale", "eye", "bulb", "shield",
    "alert-triangle", "check", "x", "moon", "sun", "droplet", "flame", "leaf", "world", "users",
    "user", "book", "search", "target", "tree", "pill", "stethoscope", "activity", "apple",
    "coin", "building-bank", "plant", "wind", "temperature", "hourglass",
)

#: Mot-clé du plan → icône. Le premier mot trouvé gagne ; rien trouvé, l'icône vient de la graine.
INDICES_ICONES: tuple[tuple[str, str], ...] = (
    ("brain", "brain"), ("neuro", "brain"), ("memory", "brain"), ("mind", "brain"),
    ("heart", "heart"), ("cardiac", "heart"), ("blood", "droplet"), ("dna", "dna"),
    ("gene", "dna"), ("cell", "atom"), ("atom", "atom"), ("molecul", "atom"),
    ("microscop", "microscope"), ("lab", "flask"), ("chemi", "flask"), ("experiment", "flask"),
    ("energy", "bolt"), ("power", "bolt"), ("electric", "bolt"), ("batter", "battery"),
    ("time", "clock"), ("hour", "hourglass"), ("year", "calendar"), ("day", "calendar"),
    ("chart", "chart-bar"), ("data", "chart-bar"), ("rise", "trending-up"),
    ("increase", "trending-up"), ("growth", "trending-up"), ("fall", "trending-down"),
    ("drop", "trending-down"), ("decline", "trending-down"), ("balance", "scale"),
    ("compar", "scale"), ("see", "eye"), ("vision", "eye"), ("observ", "eye"),
    ("idea", "bulb"), ("insight", "bulb"), ("discover", "search"), ("protect", "shield"),
    ("risk", "alert-triangle"), ("danger", "alert-triangle"), ("warning", "alert-triangle"),
    ("night", "moon"), ("sleep", "moon"), ("sun", "sun"), ("star", "sun"), ("light", "sun"),
    ("water", "droplet"), ("fire", "flame"), ("heat", "flame"), ("temperatur", "temperature"),
    ("plant", "plant"), ("leaf", "leaf"), ("tree", "tree"), ("forest", "tree"),
    ("earth", "world"), ("planet", "world"), ("global", "world"), ("climate", "wind"),
    ("air", "wind"), ("people", "users"), ("popula", "users"), ("patient", "user"),
    ("doctor", "stethoscope"), ("health", "stethoscope"), ("drug", "pill"), ("pill", "pill"),
    ("study", "book"), ("research", "book"), ("book", "book"), ("target", "target"),
    ("goal", "target"), ("money", "coin"), ("cost", "coin"), ("bank", "building-bank"),
    ("food", "apple"), ("eat", "apple"), ("exercise", "activity"), ("muscle", "activity"),
)

#: Un chiffre porteur : nombre, éventuellement décimal, suivi d'une unité courte ou d'un mot.
NOMBRE = re.compile(r"(?<![\w.])(\d{1,3}(?:[ ,]\d{3})*(?:\.\d+)?)\s*(%|x|×|°C|°F)?", re.IGNORECASE)

#: Mots qui commencent une phrase par une majuscule sans nommer personne. Ils ne signent rien.
PRONOMS: frozenset[str] = frozenset({
    "he", "she", "they", "it", "we", "you", "i", "this", "that", "there", "these", "those",
    "but", "and", "the", "a", "an", "his", "her", "their", "its", "our", "your", "one",
})

#: Marqueurs d'énumération dans une intention visuelle ou une narration.
MOTS_LISTE = ("list", "three ", "four ", "five ", "steps", "stages", "ways", "reasons",
              "factors", "rules", "types", "kinds", "first,", "second,", "finally")
MOTS_COMPARAISON = ("versus", " vs ", "compared", "comparison", "against", "difference between")
MOTS_CITATION = ("quote", "said", "wrote", "according to", "in his words")
MOTS_PERSONNE = ("scientist", "researcher", "professor", "doctor", "author", "physicist",
                 "biologist", "astronomer", "engineer")


@dataclass
class MotionEngine(MoteurRevideo):
    """Moteur de style « motion design » (`STYLE_ENGINES["motion_design"]`)."""

    name: str = "motion_design"
    backend: str = "revideo"

    # -- choix de scène ------------------------------------------------------------------

    @staticmethod
    def graine(*parties: str) -> int:
        """Graine stable d'un appel LLM.

        `hash()` de Python est **randomisé à chaque processus** : la même vidéo rejouée donnait un
        montage différent, et le cache d'appels ne servait jamais. Un sha256 tronqué ne bouge pas.
        """
        brut = "|".join(parties).encode("utf-8")
        return int.from_bytes(hashlib.sha256(brut).digest()[:4], "big") % 10**6

    @staticmethod
    def chiffres(texte: str) -> list[tuple[float, str]]:
        """Les nombres d'un texte, avec leur unité quand elle suit immédiatement."""
        trouves: list[tuple[float, str]] = []
        for brut, unite in NOMBRE.findall(texte or ""):
            try:
                trouves.append((float(brut.replace(",", "").replace(" ", "")), unite or ""))
            except ValueError:
                continue
        return trouves

    @staticmethod
    def icone_pour(texte: str, graine: int) -> str:
        """Icône d'un mot-clé, ou une icône stable tirée de la graine du plan."""
        bas = (texte or "").lower()
        for indice, icone in INDICES_ICONES:
            if indice in bas:
                return icone
        return ICONES[graine % len(ICONES)]

    def scene_par_regle(
        self, shot: Shot, role: str, dit: str, a_un_graphique: bool
    ) -> str | None:
        """La scène qu'une règle tranche seule, ou `None` — et alors le metteur en scène décide.

        Les règles ne gardent que ce qu'elles savent décider **sans se tromper** : un graphique
        vérifié, un chiffre isolé dans le texte incrusté, une rupture courte. Tout le reste est
        une question de contenu visuel, et une règle de mots-clés n'a rien à y dire — c'est ce
        qui produisait 58 plans de texte pur sur 114.
        """
        duree = shot.duration_s

        # Une rupture courte fait sentir la coupure ; longue, elle deviendrait un plan vide.
        if (shot.interrupt is not None or role == "rupture") and duree <= 3.0:
            return "transition_stinger"
        if a_un_graphique and duree >= 3.5:
            return "chart"
        # Un texte incrusté court qui porte un nombre : c'est un compteur, pas un titre.
        if shot.on_screen_text and duree >= 2.2:
            if self.chiffres(shot.on_screen_text) and len(shot.on_screen_text.split()) <= 6:
                return "stat_counter"
        return None

    #: Schéma de sortie du metteur en scène — **une seule forme, entièrement obligatoire**.
    #:
    #: La première version décrivait un champ par dispositif et ne rendait obligatoires que `id`
    #: et `scene`. La grammaire GBNF autorisait donc l'objet minimal, et un 9B quantifié le prend
    #: toujours : mesuré le 19/09 sur l'extrait réel, **0 dispositif paramétré sur 10**, rien que
    #: des `{"id": …, "scene": …}`. Une forme unique dont tous les champs sont exigés retire ce
    #: chemin de moindre effort.
    SCHEMA_PLANS = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "scene": {
                            "type": "string",
                            "enum": list(SCENES_CONSTRUITES) + ["kinetic_text"],
                        },
                        "title": {"type": "string"},
                        "items": {"type": "array", "items": {"type": "string"}},
                        "number": {"type": "number"},
                    },
                    "required": ["id", "scene", "title", "items", "number"],
                },
            },
        },
        "required": ["shots"],
    }

    CONSIGNE_METTEUR_EN_SCENE = (
        "You are the art director of an animated explainer channel. Its videos have almost no "
        "text on screen: things are SHOWN being built, opened, transformed, or acted out by "
        "characters. For each shot below, choose ONE device and fill ALL four fields.\n\n"
        "Fields, always present:\n"
        "  title  — 1 to 5 words, taken from the shot text.\n"
        "  items  — 2 to 4 labels of 1-3 words each, taken from the shot text. [] if unused.\n"
        "  number — a number that APPEARS IN THE SHOT TEXT, or 0 if there is none.\n\n"
        "Devices, and what each field means for them:\n"
        "- tete_parlante: title = WHAT speaks (a star, your brain). items []. number 0.\n"
        "- duo: title = the second character's reaction, 2-4 words. items []. number 0.\n"
        "- personnage: title = what someone blurts out, 2-4 words. items []. number 0.\n"
        "- assemble: items = the parts that make up one thing. title = the whole.\n"
        "- systeme: title = the centre. items = what orbits it.\n"
        "- coupe: title = the object. items = its layers, outside to inside.\n"
        "- flux: title = the process. items = its steps, in order.\n"
        "- groupe: items = 3 to 5 named things that take turns speaking.\n"
        "- chronologie: items = 2 to 4 events in time order. title = the span.\n"
        "- transformation: items = exactly two, what it was and what it becomes.\n"
        "- echelle: items = exactly two, the small one and the big one. number = the ratio.\n"
        "- quantite: number = a percentage from the text. title = what it is a share of.\n"
        "- kinetic_text: only if the shot has no object, process, quantity or contrast at all.\n\n"
        "Never invent a number. Never write a sentence in a label. Prefer characters "
        "(tete_parlante, duo, groupe, personnage) for anything that is an idea rather than an "
        "object. Answer with JSON only.\n"
    )

    def mettre_en_scene(
        self, plans: list[tuple[Shot, str, str]], video_id: str
    ) -> dict[str, dict]:
        """Demande au LLM **un dispositif et ses paramètres** par plan, par lots de six.

        Ce n'est plus un choix de mise en page : c'est une note d'intention visuelle. Le LLM
        fournit ce que le code ne peut pas deviner — quelles sont les pièces, quelles sont les
        étapes, ce qui devient quoi — et **rien d'autre** : la géométrie, le rythme et les
        couleurs restent au code et à la charte.

        Un lot qui échoue ne fait pas échouer le run : ses plans retombent sur une scène qui n'a
        besoin d'aucune étiquette.
        """
        if not plans:
            return {}
        from factory import llm

        sorties: dict[str, dict] = {}
        for depart in range(0, len(plans), 6):
            paquet = plans[depart : depart + 6]
            lignes = "\n".join(
                f"- {shot.id} | on screen: {shot.on_screen_text or '-'} | intent: "
                f"{shot.visual_intent} | spoken: {dit[:220]}"
                for shot, dit, _ in paquet
            )
            try:
                donnees, _ = llm.generate_json(
                    self.CONSIGNE_METTEUR_EN_SCENE + "\n" + lignes,
                    json_schema=self.SCHEMA_PLANS, max_tokens=1100, temperature=0.35,
                    seed=self.graine(video_id, f"mise{depart}"),
                    etiquette="motion_mise_en_scene", racine=self.racine,
                )
            except Exception as erreur:
                self.tracer(f"LLM mise en scène lot {depart} : {erreur} — repli sans étiquette")
                continue
            contextes = {shot.id: (dit, narration) for shot, dit, narration in paquet}
            for entree in (donnees or {}).get("shots", []):
                identifiant = str(entree.get("id", ""))
                if identifiant not in contextes:
                    continue
                retenu = self._valider_dispositif(entree, *contextes[identifiant])
                if retenu is not None:
                    sorties[identifiant] = retenu
            self.tracer(
                f"mise en scène lot {depart} : {len(sorties)} dispositif(s) retenus sur "
                f"{len(paquet)} plan(s)"
            )
        return sorties

    def _valider_dispositif(self, entree: dict, dit: str, narration: str) -> dict | None:
        """Traduit la forme unique du metteur en scène en props de scène, et refuse le reste.

        Deux refus, et ils ne se négocient pas : un dispositif à étiquettes qui n'en a pas assez,
        et **un chiffre qui ne figure pas dans ce qui est dit**. Une vidéo publiée n'affirme que
        ce que son script affirme.
        """
        scene = str(entree.get("scene", ""))
        if scene not in SCENES_CONSTRUITES and scene != "kinetic_text":
            return None
        texte = f"{dit} {narration}"
        titre = str(entree.get("title") or "").strip()[:48]
        items = [
            " ".join(str(x).split())[:32]
            for x in (entree.get("items") or []) if str(x or "").strip()
        ]
        nombre = entree.get("number")

        if scene in {"tete_parlante", "duo", "personnage"}:
            cle = "who" if scene == "tete_parlante" else "label"
            return {"scene": scene, cle: titre}
        # Trois pièces au minimum : à deux, l'assemblage ne se lit pas comme un tout mais comme
        # deux formes côte à côte (extrait réel du 19/09). Même raison pour la coupe et la
        # chronologie : deux couches font un camembert, deux jalons font une ligne vide.
        if scene == "assemble":
            return {"scene": scene, "parts": items[:5], "heading": titre} if len(items) >= 3 else None
        if scene == "systeme":
            return ({"scene": scene, "centre": titre, "satellites": items[:4]}
                    if len(items) >= 2 else None)
        if scene == "coupe":
            return {"scene": scene, "heading": titre, "layers": items[:4]} if len(items) >= 3 else None
        if scene == "flux":
            return {"scene": scene, "heading": titre, "steps": items[:4]} if len(items) >= 2 else None
        if scene == "groupe":
            return {"scene": scene, "parts": items[:5]} if len(items) >= 3 else None
        if scene == "chronologie":
            return ({"scene": scene, "events": [{"label": x, "when": ""} for x in items[:4]]}
                    if len(items) >= 3 else None)
        if scene == "transformation":
            return ({"scene": scene, "avant": items[0], "apres": items[1]}
                    if len(items) >= 2 else None)
        if scene == "echelle":
            if len(items) < 2 or not self._valeur_dans_le_texte(nombre, texte):
                return None
            rapport = float(nombre)  # type: ignore[arg-type]
            return ({"scene": scene, "small": items[0], "big": items[1], "ratio": rapport}
                    if rapport >= 2 else None)
        if scene == "quantite":
            if not self._valeur_dans_le_texte(nombre, texte):
                return None
            valeur = float(nombre)  # type: ignore[arg-type]
            return ({"scene": scene, "value": valeur, "label": titre}
                    if 1 <= valeur <= 99 else None)
        return {"scene": "kinetic_text"}

    def donnees_graphique(
        self, segments_chiffres: list[tuple[str, str]], video_id: str
    ) -> dict[str, dict]:
        """Extrait par le LLM les séries comparables d'un segment qui porte plusieurs chiffres.

        Un graphique n'est produit que si le LLM rend **au moins deux** points nommés et que
        chaque valeur apparaît dans la narration : le contraire serait un chiffre inventé sur une
        vidéo publiée.
        """
        if not segments_chiffres:
            return {}
        from factory import llm

        schema = {
            "type": "object",
            "properties": {
                "heading": {"type": "string"},
                "unit": {"type": "string"},
                "kind": {"type": "string", "enum": ["bar", "line"]},
                "series": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "number"},
                        },
                        "required": ["label", "value"],
                    },
                },
            },
            "required": ["heading", "unit", "kind", "series"],
        }
        sorties: dict[str, dict] = {}
        for segment_id, narration in segments_chiffres:
            prompt = (
                "Extract the comparable figures from this narration as a small chart.\n"
                "Rules: only numbers that appear literally in the text; two to five points; "
                "each label at most three words; use \"line\" only for a progression over time, "
                "otherwise \"bar\". If the figures are not comparable, answer with an empty "
                "series.\nAnswer with JSON only.\n\n"
                f"{narration[:900]}"
            )
            try:
                donnees, _ = llm.generate_json(
                    prompt, json_schema=schema, max_tokens=380, temperature=0.1,
                    seed=self.graine(video_id, segment_id),
                    etiquette="motion_chart", racine=self.racine,
                )
            except Exception as erreur:
                self.tracer(f"LLM graphique {segment_id} : {erreur}")
                continue
            serie = [
                point for point in (donnees or {}).get("series", [])
                if str(point.get("label", "")).strip()
                and self._valeur_dans_le_texte(point.get("value"), narration)
            ][:5]
            if len(serie) < 2:
                self.tracer(f"{segment_id} : série rejetée ({len(serie)} point(s) vérifié(s))")
                continue
            sorties[segment_id] = {
                "kind": donnees.get("kind") if donnees.get("kind") in {"bar", "line"} else "bar",
                "unit": str(donnees.get("unit") or "")[:4],
                "heading": str(donnees.get("heading") or "")[:60],
                "series": [{"label": str(p["label"])[:22], "value": p["value"]} for p in serie],
            }
        return sorties

    @staticmethod
    def _valeur_dans_le_texte(valeur: object, narration: str) -> bool:
        """Vrai si la valeur figure littéralement dans la narration — la seule preuve acceptable."""
        try:
            nombre = float(valeur)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
        formes = {f"{nombre:g}", f"{int(nombre)}" if nombre == int(nombre) else f"{nombre:g}"}
        nu = narration.replace(",", "")
        return any(forme in nu or forme in narration for forme in formes)

    # -- props -------------------------------------------------------------------------

    @staticmethod
    def mots_du_plan(mots: list[dict], shot: Shot) -> list[dict]:
        """Les mots de `words.json` qui tombent dans le plan, réexprimés depuis son début."""
        dedans = [
            m for m in mots
            if float(m.get("start_s", -1)) >= shot.start_s - 0.02
            and float(m.get("start_s", -1)) < shot.end_s
        ]
        return [
            {
                "w": str(m.get("w", "")),
                "t": round(float(m["start_s"]) - shot.start_s, 3),
                "e": round(min(float(m["end_s"]), shot.end_s) - shot.start_s, 3),
            }
            for m in dedans
            if str(m.get("w", "")).strip()
        ]

    @classmethod
    def texte_du_plan(cls, mots: list[dict], shot: Shot) -> str:
        """Ce qui est prononcé pendant le plan, reconstruit depuis `words.json`."""
        return " ".join(m["w"] for m in cls.mots_du_plan(mots, shot))

    def props_du_plan(
        self, shot: Shot, scene: str, dit: str, mots: list[dict], graphique: dict | None,
        titre_segment: str = "", variante_fond: int = 0, dispositif: dict | None = None,
    ) -> dict:
        """Les propriétés que la scène lit. Tout vient du plan, de la charte ou du script.

        `dit` est ce qui est prononcé **pendant ce plan**. Les phrases posées à l'écran sont donc
        celles que la voix dit au même moment, jamais celles du segment entier : c'est la seule
        façon qu'un point de liste apparaisse quand il est prononcé.
        """
        props: dict = {
            "seed": shot.seed % (2**31),
            # Sur-titre : le texte incrusté **du segment**, qui fait office de titre de chapitre
            # sur tous ses plans ; à défaut, deux mots de l'intention visuelle. Le rôle du segment
            # (« hook », « point ») n'est pas un mot de la vidéo : l'écrire à l'écran serait une
            # fuite de vocabulaire interne dans un plan publié.
            "title": titre_segment or self._mots_cles(shot.visual_intent, 2),
            "on_screen_text": shot.on_screen_text,
            # Teinte de fond du plan, en rotation sur quatre : deux plans voisins n'ont jamais la
            # même. C'est ce qui rend une coupe visible — sans elle, 27 plans sur 114 seulement
            # étaient détectés au montage du 19/09, soit les seuls `dip_black`.
            "bg_variant": variante_fond,
            "is_sponsor": shot.is_sponsor,
            "disclosure": self.texte_divulgation if shot.is_sponsor else None,
        }
        if scene == "kinetic_text":
            props["words"] = mots
            return props

        # Les scènes construites reçoivent **les paramètres du metteur en scène**, validés plus
        # haut — et **rien d'autre**. Faute de dispositif, aucune étiquette n'est fabriquée : le
        # plan a déjà été renvoyé par `construire_specs` vers une scène qui n'en a pas besoin.
        # Le repli par découpage de phrase, lui, posait « LOOK AT THE » sur une boîte de schéma.
        if scene in SCENES_CONSTRUITES:
            props.update({k: v for k, v in (dispositif or {}).items() if k != "scene"})
            props.setdefault("heading", shot.on_screen_text or "")
            # Les deux scènes jouées qui parlent reçoivent les mots du plan : c'est ce qui ouvre
            # et ferme la bouche du personnage au bon moment.
            if scene in {"tete_parlante", "duo"}:
                props["words"] = mots
                # Sans nom donné par le metteur en scène, **pas de cartouche** : l'intention
                # visuelle d'un plan (« split screen… ») n'est pas le nom de ce qui parle.
                props.setdefault("who", "")
                props.setdefault("label", "")
                return props
            if scene == "transformation":
                props.setdefault("avant", "")
                props.setdefault("apres", "")
            elif scene == "personnage":
                props.setdefault("label", "")
            return props

        phrases = [p.strip() for p in re.split(r"(?<=[.!?,;:])\s+", dit) if len(p.strip()) > 3]
        # Les temps d'apparition suivent la voix : chaque silence de plus de 0,28 s ouvre un point.
        debuts = [mots[0]["t"]] if mots else [0.2]
        debuts += [
            mots[i]["t"] for i in range(1, len(mots))
            if mots[i]["t"] - mots[i - 1]["e"] > 0.28
        ]

        if scene == "list_reveal":
            points = [p for p in phrases if len(p) > 10][:3] or [shot.on_screen_text or dit[:90]]
            props["items"] = [p[:100] for p in points]
            props["heading"] = shot.on_screen_text or ""
            props["beats"] = debuts[: len(points)]
        elif scene == "stat_counter":
            chiffres = self.chiffres(shot.on_screen_text or "") or self.chiffres(dit)
            valeur, unite = chiffres[0] if chiffres else (0.0, "")
            reste = NOMBRE.sub("", shot.on_screen_text or "").strip(" -—:·")
            props["value"] = valeur
            props["unit"] = unite
            # Le libellé, c'est ce que le texte incrusté dit d'autre que le nombre — « 93 BILLION
            # LIGHT YEARS » donne 93 et « BILLION LIGHT YEARS ». Faute de quoi, la phrase dite.
            props["label"] = (reste or (phrases[0] if phrases else dit))[:100]
        elif scene == "icon_grid":
            noms = [p for p in phrases if len(p) > 8][:3] or [shot.on_screen_text or shot.visual_intent]
            # Deux fois la même icône dans une grille de trois, c'est une grille qui ne dit rien :
            # la deuxième occurrence descend sur le mot suivant, puis sur la graine.
            grille: list[dict] = []
            prises: set[str] = set()
            for i, nom in enumerate(noms):
                choix = self.icone_pour(f"{nom} {shot.visual_intent}", shot.seed + i)
                if choix in prises:
                    choix = ICONES[(shot.seed + i * 7 + len(prises)) % len(ICONES)]
                    while choix in prises:
                        choix = ICONES[(ICONES.index(choix) + 1) % len(ICONES)]
                prises.add(choix)
                grille.append({"icon": choix, "label": self._mots_cles(nom, 2, mots_seuls=True)})
            props["icons"] = grille
            props["heading"] = shot.on_screen_text or ""
            props["beats"] = debuts[: len(noms)]
        elif scene == "chart":
            props["data"] = graphique or {}
            props["heading"] = shot.on_screen_text or ""
        elif scene == "lower_third":
            props["heading"] = shot.on_screen_text or self._mots_cles(dit, 4)
            props["label"] = (phrases[0] if phrases else "")[:64]
            props["watermark"] = self._mots_cles(shot.visual_intent, 1)
        elif scene == "quote":
            props["quote"] = (phrases[0] if phrases else dit)[:200]
            # L'auteur n'est posé que si le texte le nomme. Inventer une attribution sur une
            # vidéo publiée est une faute, pas un défaut de mise en page.
            nomme = re.search(
                r"(?:according to|as)\s+([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,2})"
                r"|([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,2})\s+(?:said|wrote|put it)",
                dit,
            )
            candidat = ((nomme.group(1) or nomme.group(2)) if nomme else "").strip()[:40]
            # « He said gravity changes space geometry. » attribuait la citation à « He » (rendu
            # du 19/09). Un pronom n'est pas un auteur : sans nom propre, pas de signature.
            props["author"] = "" if candidat.lower() in PRONOMS else candidat
        elif scene == "transition_stinger":
            props["on_screen_text"] = (
                shot.on_screen_text or self._mots_cles(dit, 4) or self._mots_cles(shot.visual_intent, 3)
            )
        elif scene == "title_card":
            props["heading"] = shot.on_screen_text or (phrases[0][:90] if phrases else
                                                        self._mots_cles(shot.visual_intent, 6))
            props["label"] = (phrases[1][:70] if len(phrases) > 1 else "")
        # Le sur-titre ne redit jamais ce que la scène affiche déjà en grand : sur le premier plan
        # d'un segment, le titre de chapitre et l'en-tête de scène sont le même texte.
        for cle in ("heading", "quote", "on_screen_text"):
            valeur = props.get(cle)
            if valeur and str(valeur).strip().lower() == str(props["title"]).strip().lower():
                props["title"] = ""
                break
        return props

    @staticmethod
    def _groupes_de_mots(texte: str, combien: int) -> list[str]:
        """Découpe ce qui est dit en groupes courts.

        **N'est plus employé comme repli d'étiquette** : posé sur une pièce de schéma, il donnait
        « LOOK AT THE » et « THE MATH OF » (extrait réel du 19/09). Un plan sans dispositif part
        désormais sur une scène qui n'a pas d'étiquette. La fonction reste pour les listes, où
        des groupes de mots prononcés sont exactement ce qu'il faut.
        """
        morceaux = [
            m.strip() for m in re.split(r"[,;:.!?]|\band\b|\bthen\b|\bbut\b", texte or "")
            if len(m.strip()) > 3
        ]
        sortie = [" ".join(m.split()[:3]) for m in morceaux][:combien]
        return [s for s in sortie if s]

    @staticmethod
    def _mots_cles(texte: str, combien: int = 3, mots_seuls: bool = False) -> str:
        """Les premiers mots signifiants d'un texte — jamais un texte inventé, juste raccourci.

        `mots_seuls` écarte les nombres. Sur un libellé d'icône, « 13.8 » se découpe en « 13 » et
        « 8 » et donne « universe 13 8 », lu à l'écran comme une erreur (rendu du 19/09).
        """
        vides = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "is", "are",
                 "that", "this", "it", "with", "as", "at", "by", "from", "but", "not"}
        motif = r"[A-Za-z'-]+" if mots_seuls else r"[A-Za-z0-9'%-]+"
        mots = [m for m in re.findall(motif, texte or "") if m.lower() not in vides]
        return " ".join(mots[:combien])

    # -- spécifications ------------------------------------------------------------------

    def construire_specs(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> tuple[dict, dict[str, str]]:
        """Écrit `render/specs/<video_id>/batch.json` et rend la spec plus le plan des scènes."""
        script = json.loads(run.script.read_text(encoding="utf-8")) if run.script.exists() else {}
        narrations = {s["id"]: s.get("narration", "") for s in script.get("segments", [])}
        roles = {s["id"]: s.get("role", "point") for s in script.get("segments", [])}
        titres = {
            s["id"]: (s.get("on_screen_text") or "") for s in script.get("segments", [])
        }
        mots = (
            json.loads(run.words.read_text(encoding="utf-8")).get("words", [])
            if run.words.exists() else []
        )

        # 1. graphiques — un segment qui porte au moins deux chiffres comparables, et un seul
        #    graphique par segment. Le LLM ne voit que ces segments-là.
        candidats = [
            (segment_id, narration) for segment_id, narration in narrations.items()
            if len(self.chiffres(narration)) >= 2
        ]
        t_chart = time.perf_counter()
        graphiques = self.donnees_graphique(candidats[:6], run.video_id)
        secondes_chart = time.perf_counter() - t_chart
        deja_trace: set[str] = set()

        # 2. règles — elles ne gardent que ce qu'elles savent décider sans se tromper
        dits = {shot.id: self.texte_du_plan(mots, shot) for shot in shotlist.shots}
        decisions: dict[str, str] = {}
        a_mettre_en_scene: list[tuple[Shot, str, str]] = []
        for shot in shotlist.shots:
            libre = shot.segment_id in graphiques and shot.segment_id not in deja_trace
            choix = self.scene_par_regle(
                shot, roles.get(shot.segment_id, "point"), dits[shot.id], libre
            )
            if choix == "chart":
                deja_trace.add(shot.segment_id)
            if choix is None:
                a_mettre_en_scene.append(
                    (shot, dits[shot.id], narrations.get(shot.segment_id, ""))
                )
            else:
                decisions[shot.id] = choix

        # 3. mise en scène : un dispositif **et ses paramètres** par plan
        t_llm = time.perf_counter()
        dispositifs = self.mettre_en_scene(a_mettre_en_scene, run.video_id)
        secondes_llm = time.perf_counter() - t_llm
        for identifiant, dispositif in dispositifs.items():
            decisions[identifiant] = dispositif["scene"]

        # 4. rotation, variété, et **plafond de texte**
        plan_final: dict[str, str] = {}
        recents: list[str] = ["", ""]
        textes_poses = 0
        plafond_texte = max(1, int(len(shotlist.shots) * PART_TEXTE_MAX))
        for rang, shot in enumerate(shotlist.shots):
            court = shot.duration_s < 2.6
            rotation = ROTATION_COURTE if court else ROTATION
            scene = decisions.get(shot.id, "")
            if scene not in SCENES:
                scene = rotation[rang % len(rotation)]
            # Une scène à étiquettes sans dispositif n'a rien à écrire dessus.
            if scene in SCENES_A_ETIQUETTES and shot.id not in dispositifs:
                scene = ROTATION_SANS_ETIQUETTE[rang % len(ROTATION_SANS_ETIQUETTE)]
            # Le plafond de texte est une contrainte dure : au-delà, la vidéo redevient ce qui a
            # été refusé deux fois — « des textes et un peu du motion design très léger ».
            if scene in SCENES_TEXTE:
                if textes_poses >= plafond_texte and scene != "transition_stinger":
                    scene = rotation[rang % len(rotation)]
                    dispositifs.pop(shot.id, None)
                else:
                    textes_poses += 1
            # Variété sur une fenêtre de deux plans. `chart` et `stat_counter` en sont exemptées :
            # elles portent un chiffre du script, et ce chiffre ne se déplace pas pour faire joli.
            if scene in recents and scene not in SCENES_CHIFFRE:
                permis = [
                    s for s in rotation
                    if s not in SCENES_A_ETIQUETTES or shot.id in dispositifs
                ] or list(ROTATION_SANS_ETIQUETTE)
                rechange = [s for s in permis if s not in recents] or permis
                remplacant = rechange[rang % len(rechange)]
                if scene != remplacant:
                    dispositifs.pop(shot.id, None)
                scene = remplacant
            plan_final[shot.id] = scene
            recents = [scene, recents[0]]

        # 5. spec
        charte = channel.charte
        titre = self.police_titre(channel)
        corps = self.police_corps(channel)
        lots: list[dict] = []
        taille = max(1, self.taille_lot)
        for depart in range(0, len(shotlist.shots), taille):
            paquet = shotlist.shots[depart : depart + taille]
            lots.append({
                "name": f"lot_{depart // taille:03d}",
                "shots": [
                    {
                        "id": shot.id,
                        "scene": plan_final[shot.id],
                        "duration_s": round(shot.duration_s, 3),
                        "props": self.props_du_plan(
                            shot, plan_final[shot.id], dits[shot.id],
                            self.mots_du_plan(mots, shot),
                            graphiques.get(shot.segment_id),
                            titres.get(shot.segment_id, ""),
                            ORDRE_FONDS[(depart + index) % len(ORDRE_FONDS)],
                            dispositifs.get(shot.id),
                        ),
                    }
                    for index, shot in enumerate(paquet)
                ],
            })

        spec = {
            "video_id": run.video_id,
            "fps": video.FPS,
            "width": video.LARGEUR,
            "height": video.HAUTEUR,
            "resolution_scale": self.echelle,
            "workers": int(self.param("revideo.workers", 1) or 1),
            "out_dir": str(self.dossier_render / "out" / run.video_id),
            "charte": {
                "bg": charte.palette.bg,
                "text": charte.palette.text,
                "text_outline": charte.palette.text_outline,
                "accent": charte.palette.accent,
                "highlight": charte.palette.highlight,
                "font_title": self.famille_css(titre),
                "font_body": self.famille_css(corps),
                "marge_px": int(self.param("scene.marge_px", 96) or 96),
            },
            "lots": lots,
        }
        self.ecrire_specs(spec, run.video_id)
        self.mesures["scene_llm_seconds"] = round(secondes_llm, 2)
        self.mesures["part_texte"] = round(
            sum(1 for s in plan_final.values() if s in SCENES_TEXTE)
            / max(1, len(plan_final)), 3
        )
        self.mesures["chart_llm_seconds"] = round(secondes_chart, 2)
        self.mesures["scene_counts"] = {
            scene: sum(1 for s in plan_final.values() if s == scene)
            for scene in sorted(set(plan_final.values()))
        }
        self.mesures["scene_mises_en_scene"] = len(dispositifs)
        self.mesures["scene_a_mettre_en_scene"] = len(a_mettre_en_scene)
        self.mesures["charts"] = len(graphiques)
        return spec, plan_final

    # -- rendu ---------------------------------------------------------------------------

    # -- contrat StyleEngine -------------------------------------------------------------

    def prepare_assets(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> list[Asset]:
        """Écrit les spécifications de scène, rend tous les lots, découpe, inscrit les licences.

        C'est ici que **tout** le rendu a lieu : `render_shot` ne fait plus que constater. La
        raison est le coût de lancement de Chromium — un plan à la fois coûterait dix secondes
        par plan, soit plus cher que les images elles-mêmes.
        """
        self.verifier_render()

        spec, plan_final = self.construire_specs(shotlist, channel, run)
        durees = {shot.id: shot.duration_s for shot in shotlist.shots}

        t0 = time.perf_counter()
        manifestes = self.lancer_render(spec, run.video_id)
        secondes_revideo = sum(float(m["secondes_rendu"]) for m in manifestes)
        images = sum(int(m["frames_utiles"]) for m in manifestes)

        t_decoupe = time.perf_counter()
        temps_par_plan: dict[str, float] = {}
        for manifeste in manifestes:
            temps_par_plan.update(self.decouper(manifeste, run, durees))
        secondes_decoupe = time.perf_counter() - t_decoupe
        secondes_total = time.perf_counter() - t0

        secondes_video = sum(durees.values())
        self.mesures.update({
            "revideo_seconds": round(secondes_revideo, 2),
            "decoupe_seconds": round(secondes_decoupe, 2),
            "render_seconds": round(secondes_total, 2),
            "frames": images,
            "revideo_fps": round(images / secondes_revideo, 1) if secondes_revideo else 0.0,
            "pipeline_fps": round(images / secondes_total, 1) if secondes_total else 0.0,
            "seconds_per_video_minute": round(secondes_total / (secondes_video / 60), 1)
            if secondes_video else 0.0,
            "realtime_ratio": round(secondes_total / secondes_video, 3) if secondes_video else 0.0,
            "resolution_scale": self.echelle,
            "shot_seconds": {k: round(v, 3) for k, v in temps_par_plan.items()},
        })

        self.tracer(
            "mesures motion : "
            + json.dumps({k: v for k, v in self.mesures.items() if k != "shot_seconds"},
                         ensure_ascii=False)
        )

        assets: list[Asset] = []
        for shot in shotlist.shots:
            dossier = run.asset_dir(shot.id)
            dossier.mkdir(parents=True, exist_ok=True)
            spec_plan = dossier / "scene.json"
            contenu = next(
                (
                    plan for lot in spec["lots"] for plan in lot["shots"]
                    if plan["id"] == shot.id
                ),
                {},
            )
            spec_plan.write_text(
                json.dumps(contenu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
            asset = Asset(
                asset_id=self.identifiant_asset(spec_plan),
                path=f"assets/{shot.id}/scene.json",
                provider="charte",
                # Une scène de motion design n'est faite que de la charte, d'une police OFL et
                # d'icônes MIT. La source est donc le dépôt, et c'est vérifiable.
                source_url=(
                    f"config/channels/{channel.id}.yaml#charte@{channel.charte.version}"
                    f"+render/src/scenes/{plan_final[shot.id].replace('_', '-')}.tsx"
                ),
                author=f"BMS ({channel.name})",
                licence="OFL-1.1 AND MIT",
                licence_url="https://openfontlicense.org/open-font-license-official-text/",
                attribution_line="Icons: Tabler Icons 3.36.0 (MIT) — Paweł Kuna",
                downloaded_at=self.maintenant(),
                person_release=None,
                generator=None,
                realistic=False,
                has_text=True,
                c2pa_present=False,
            )
            run.licence(shot.id).write_text(
                json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            assets.append(asset)
        return assets

    def render_shot(
        self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths
    ) -> Path:
        """Rend `clips/<shot>.mp4`. Le lot l'a normalement déjà produit ; sinon, il est rejoué seul.

        Rejouer un plan seul relance Chromium pour lui tout seul : c'est lent, et c'est voulu — le
        cas normal est le lot, celui-ci est la réparation d'un plan manquant.
        """
        sortie = run.clip(shot.id)
        if sortie.exists() and not self.verify_clip(sortie, shot.duration_s):
            return sortie
        fichier = self.dossier_render / "specs" / run.video_id / "batch.json"
        if not fichier.exists():
            raise RenduRevideoEchoue(
                f"{shot.id} : spécification absente ({fichier}) — `prepare_assets` n'a pas tourné"
            )
        spec = json.loads(fichier.read_text(encoding="utf-8"))
        lot = next(
            (l["name"] for l in spec["lots"] if any(p["id"] == shot.id for p in l["shots"])),
            None,
        )
        if lot is None:
            raise RenduRevideoEchoue(f"{shot.id} : absent de {fichier}")
        manifestes = self.lancer_render(spec, run.video_id, lot=lot)
        self.decouper(manifestes[0], run, {shot.id: shot.duration_s})
        return sortie
