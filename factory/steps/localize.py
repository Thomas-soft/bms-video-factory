"""`factory localize` — déclinaison d'un run exporté vers une chaîne d'une autre langue (étape 24).

Une déclinaison est une **adaptation**, jamais un clone (`CONFORMITE` § 5, `ARCHITECTURE` § 6) :

1. **Ce qui est repris** : le sujet, l'angle, la structure des segments (ids, rôles, boucles,
   ruptures) et les `visual_intent` — donc les images. C'est là que se fait l'économie :
   `heritage.json` sert au moteur les images du parent, par demande d'asset puis par segment,
   et aucune image n'est générée tant que le parent en a une.
2. **Ce qui est réécrit** : la narration (adaptée par le LLM avec glossaire et consignes de la
   langue cible : unités, nombres, références), le hook (trois candidats notés par
   `retention/hooks.py`), le texte à l'écran (≤ 6 mots), la divulgation sponsor.
3. **Ce qui est propre à la cible** : voix, charte, template (≠ celui du parent), miniature
   (gabarit ≠ celui du parent), titres et description.

Le run enfant est un run ordinaire : `plan` et `research` sont marqués faits, `script` appelle
`adapter_script` parce que `spec.parent_id` est posé, et le reste du DAG tourne tel quel — la
relecture humaine comprise, qui voit qu'il s'agit d'une déclinaison.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factory import llm
from factory.core import config as config_module
from factory.core import db, referentiel, runs
from factory.core.models import (
    AngleEditorialManifeste, CandidatHook, Declinaison, EnfantDeclinaison, ErreurRun, Hook, ManifestDecisions,
    ManifestIdentite, Research, RunManifest, Script, ScriptSegment, VerificationRetention,
    VideoSpec,
)
from factory.core.paths import RunPaths, racine_projet
from factory.retention import density as density_module
from factory.retention import loops as loops_module
from factory.retention import patterns as patterns_module

#: Segments adaptés par appel : au-delà, un 9B perd des ids ou fusionne des segments.
LOT = 5
#: Reprises d'adaptation sur infraction de `retention/verify`.
REPRISES_MAX = 2
#: Part maximale de mots-outils de la langue source tolérée dans un segment adapté.
DERIVE_MAX = 0.08
#: Mots-outils par langue — détecteur de dérive (un 9B recopie parfois la source).
MOTS_OUTILS = {
    "fr": {"le", "la", "les", "des", "une", "est", "et", "que", "pour", "dans", "qui", "sur",
           "pas", "avec", "sont", "du", "au", "ce", "cette", "mais"},
    "en": {"the", "and", "is", "of", "to", "that", "with", "for", "are", "this", "but", "it"},
    "es": {"el", "los", "las", "una", "es", "y", "que", "para", "con", "por", "pero", "del"},
    "it": {"il", "gli", "una", "è", "e", "che", "per", "con", "sono", "ma", "del", "della"},
}

SCHEMA_ADAPTATION = {
    "type": "object",
    "properties": {"segments": {"type": "array", "minItems": 1, "items": {
        "type": "object", "properties": {
            "id": {"type": "string"}, "narration": {"type": "string"},
            "on_screen_text": {"type": "string"}},
        "required": ["id", "narration", "on_screen_text"]}}},
    "required": ["segments"],
}

SYSTEME = (
    "You are a senior localization editor for a YouTube science channel. You ADAPT scripts for a "
    "new market; you never translate word for word. You write for the ear in {langue}: short "
    "sentences, one idea per sentence, natural idioms of {langue}. You keep every fact and every "
    "number of the source, converted to local conventions, and you invent none. You answer with "
    "a valid JSON object only."
)

GABARIT = """Adapt these segments of a video script from {source} into {langue}.
Topic: {sujet}
Editorial angle: {angle}
The hook, spoken just before segment seg_01, is: "{hook}"
Never repeat or paraphrase the hook in these segments.
{precedent}
Localization rules for {langue}:
{consignes}
{glossaire}
Retention rules:
- A segment marked PLANT must end on an unanswered question or teaser (for example: {plantation}).
- A segment marked PAYOFF must explicitly answer the teaser quoted in its "answers" field (for example: {paiement}).
- Keep each segment about its target word count (±10 %).
- Do not mirror the source sentence by sentence: merge or split sentences, vary the rhythm, and
  where the source is generic, give one concrete everyday example familiar to a {langue}-speaking
  viewer. Facts, numbers and meaning may not change.
- on_screen_text: at most 6 words in {langue}, no final punctuation (empty string if the source has none).
{consignes_supp}
Return {{"segments": [{{"id", "narration", "on_screen_text"}}]}} with exactly these ids, in order.

Segments:
{segments}
"""


class DeclinaisonImpossible(RuntimeError):
    """Le parent ou la cible ne permet pas de décliner — message lisible par Alek."""


@dataclass
class ResultatDeclinaison:
    video_id: str
    parent_id: str
    etat: str
    declinaison: Declinaison | None = None
    alertes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# 1 — le run enfant
# --------------------------------------------------------------------------------------

def _template_miniature_parent(parent: RunPaths) -> str | None:
    fichier = parent.racine / "thumbnails" / "thumbnails.json"
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8")).get("template")
    return None


def heritage(parent_shotlist: dict[str, Any], parent_id: str) -> dict[str, Any]:
    """Images du parent par demande d'asset, puis par segment (ordre des plans)."""
    par_prompt: dict[str, str] = {}
    par_segment: dict[str, list[str]] = {}
    for shot in parent_shotlist["shots"]:
        demande = shot["asset_request"]["prompt_or_keywords"].strip()
        par_prompt.setdefault(demande, shot["id"])
        if not shot["asset_request"].get("type") == "card":
            par_segment.setdefault(shot["segment_id"], []).append(shot["id"])
    return {"parent_id": parent_id, "par_prompt": par_prompt, "par_segment": par_segment}


def creer_enfant(parent_id: str, cible: str, racine: Path | None = None) -> tuple[str, list[str]]:
    """Crée le squelette du run enfant (aucun modèle) et l'inscrit au parent. Idempotent."""
    racine = racine or racine_projet()
    alertes: list[str] = []
    cfg = config_module.charger(racine, strict=False)
    parent = RunPaths.depuis_video_id(parent_id, racine)
    for requis in (parent.spec, parent.manifest, parent.script, parent.shotlist, parent.research):
        if not requis.exists():
            raise DeclinaisonImpossible(f"{parent_id} : {requis.name} absent — le parent doit "
                                        "être produit jusqu'à l'export")
    if not parent.done("export").exists():
        raise DeclinaisonImpossible(f"{parent_id} n'est pas exporté : on ne décline qu'une "
                                    "vidéo finie")
    spec_p = runs.charger_spec(parent_id, racine)
    manifest_p = runs.charger_manifest(parent_id, racine)
    if spec_p.parent_id:
        raise DeclinaisonImpossible(f"{parent_id} est lui-même une déclinaison : la parenté est "
                                    "d'un seul niveau")
    channel = cfg.get_channel(cible)
    if channel.lang == spec_p.lang:
        raise DeclinaisonImpossible(
            f"{cible} parle {channel.lang}, comme le parent : même langue = clone, interdit "
            "(CONFORMITE § 5)")
    if channel.derive_from != spec_p.channel_id:
        alertes.append(f"{cible}.derive_from = {channel.derive_from}, pas {spec_p.channel_id} : "
                       "déclinaison manuelle hors configuration")
    deja = next((e for e in manifest_p.children if e.channel_id == cible), None)
    if deja is not None and RunPaths.depuis_video_id(deja.video_id, racine).spec.exists():
        return deja.video_id, alertes + [f"déclinaison déjà créée : {deja.video_id}"]

    miniature_p = _template_miniature_parent(parent)
    gabarits_mini = list(channel.charte.thumbnail.templates)
    # Graine tirée jusqu'à ce que template **et** gabarit de miniature diffèrent du parent :
    # `plan` et `thumbnail` les tirent tous deux de `spec.seed`.
    for _ in range(200):
        seed = config_module.nouvelle_graine()
        template = channel.templates[seed % len(channel.templates)]
        mini = gabarits_mini[seed % len(gabarits_mini)]
        if template != manifest_p.identite.template_id and (miniature_p is None or mini != miniature_p):
            break
    else:
        raise DeclinaisonImpossible(f"{cible} : aucun template distinct de "
                                    f"{manifest_p.identite.template_id} dans {channel.templates}")

    niche_cfg = cfg.niches[channel.niche]
    produit = spec_p.product_id if spec_p.product_id in channel.products else (
        channel.products[0] if channel.products else None)
    conn = db.ouvrir(racine / "workspace" / "factory.db")
    db.migrer(conn)
    video_id = config_module.attribuer_video_id(channel.id, seed, racine=racine, conn=conn)
    spec = VideoSpec(
        video_id=video_id, parent_id=parent_id, channel_id=channel.id, lang=channel.lang,
        niche=channel.niche, style=channel.style, topic=spec_p.topic,
        target_duration_s=int(round(niche_cfg.duree_s.cible)),
        cut_rhythm_target_s=cfg.cible_rythme(channel), seed=seed, product_id=produit,
        created_at=runs.maintenant(),
    )
    bloquants = [p for p in config_module.verifier_spec(spec, cfg) if p.niveau == "erreur"]
    if bloquants:
        raise DeclinaisonImpossible("spec.json refusé : " + " ; ".join(p.message for p in bloquants))
    script_p = Script.model_validate_json(parent.script.read_text(encoding="utf-8"))
    manifest = RunManifest(
        identite=ManifestIdentite(
            video_id=video_id, parent_id=parent_id, channel_id=channel.id, lang=channel.lang,
            niche=channel.niche, style=channel.style, template_id=template,
            charte_version=channel.charte.version),
        decisions=ManifestDecisions(topic=spec_p.topic, hook_type=script_p.hook.type,
                                    cut_rhythm_target_s=spec.cut_rhythm_target_s,
                                    voice_id=channel.voice_id),
        declinaison=Declinaison(
            parent_id=parent_id, parent_lang=spec_p.lang,
            parent_template_id=manifest_p.identite.template_id,
            parent_thumbnail_template=miniature_p,
            segments_conserves=len(script_p.segments),
            parent_compute_min=manifest_p.execution.cost.compute_min),
    )
    manifest.conformite.paid_promotion = bool(produit)
    manifest.conformite.publish_path = channel.publish_path  # type: ignore[assignment]
    manifest.execution.run_state = "running"

    chemins = RunPaths.depuis_video_id(video_id, racine).creer()
    runs.ecrire_json(chemins.spec, spec)
    shutil.copyfile(parent.research, chemins.research)
    (chemins.racine / "heritage.json").write_text(json.dumps(
        heritage(json.loads(parent.shotlist.read_text(encoding="utf-8")), parent_id),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runs.ecrire_json(chemins.manifest, manifest)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()

    from factory import run as run_module
    for etape in ("plan", "research"):
        run_module.marquer(chemins, etape, runs.maintenant(), 0.0, 0)

    manifest_p.children = [e for e in manifest_p.children if e.channel_id != cible]
    manifest_p.children.append(EnfantDeclinaison(
        video_id=video_id, channel_id=cible, lang=channel.lang, created_at=runs.maintenant()))
    runs.ecrire_json(parent.manifest, manifest_p)
    return video_id, alertes


# --------------------------------------------------------------------------------------
# 2 — l'adaptation du script (appelée par `factory script` quand `spec.parent_id` est posé)
# --------------------------------------------------------------------------------------

def _derive(texte: str, lang_source: str) -> float:
    """Part de mots-outils de la langue source dans un texte adapté."""
    mots = re.findall(r"[a-zà-ÿ']+", texte.lower())
    if not mots:
        return 0.0
    return sum(1 for m in mots if m in MOTS_OUTILS.get(lang_source, set())) / len(mots)


def _nombres(texte: str) -> set[str]:
    return {n.replace(",", "").replace(" ", "") for n in re.findall(r"\d[\d  ,]*", texte)}


def _glossaire(langue: Any, niche: str, source: str) -> str:
    termes = [*langue.localisation.glossaire.get(niche, []),
              *langue.localisation.glossaire.get("_defaut", [])]
    presents = [t for t in termes if t.source.lower() in source.lower()]
    if not presents:
        return ""
    lignes = [f'- "{t.source}" -> ' + (f'"{t.cible}"' if t.cible else "keep as is")
              + (f" ({t.note})" if t.note else "") for t in presents]
    return "Glossary (mandatory):\n" + "\n".join(lignes)


def adapter_script(video_id: str, racine: Path | None = None) -> Any:
    """Écrit le `script.json` de l'enfant par adaptation du parent. Rend un `ResultatScript`."""
    from factory.steps import script as script_module

    t0 = time.perf_counter()
    racine_eff = racine or racine_projet()
    alertes: list[str] = []
    spec = runs.charger_spec(video_id, racine)
    if not spec.parent_id:
        raise DeclinaisonImpossible(f"{video_id} n'a pas de parent_id")
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    langue = cfg.langue_de(channel)
    chemins = RunPaths.depuis_video_id(video_id, racine_eff)
    parent = RunPaths.depuis_video_id(spec.parent_id, racine_eff)
    source = Script.model_validate_json(parent.script.read_text(encoding="utf-8"))
    recherche = Research.model_validate_json(
        chemins.research.read_text(encoding="utf-8"))
    nom_langue = {"en": "English", "fr": "French", "es": "Spanish", "it": "Italian"}
    cible_nom, source_nom = nom_langue.get(spec.lang, spec.lang), nom_langue.get(source.lang, source.lang)

    mpm = referentiel.mots_par_minute(spec.niche, racine)
    mots_cibles = int(round(spec.target_duration_s * mpm / 60))
    tolerance = float(cfg.niches[spec.niche].duree_s.tolerance)
    mots_hook_max = referentiel.longueur_hook_max(spec.niche, racine)
    bloc_hook = referentiel.niche(spec.niche, racine)["hooks"]["longueur_mots"]
    mots_hook_min = int(round(float(bloc_hook.get("p25") or mots_hook_max * 0.6)))
    patterns = patterns_module.charger(spec.lang, racine)
    densite_cible = density_module.cible(spec.niche, racine)
    densite_plancher = density_module.plancher(spec.niche, racine)
    trace = llm.TraceLLM()

    # --- hook : régénéré dans la langue cible, même type que le parent ---
    gabarits = script_module.charger_gabarits(spec.lang, racine)
    taxonomie = referentiel.taxonomie_hooks(racine)[source.hook.type]
    from factory.steps.research import persona as _persona
    commun = {
        "sujet": spec.topic.sujet, "angle": recherche.angle,
        "elements_proprietaires": " ; ".join(recherche.elements_proprietaires) or "—",
        "persona": _persona(channel, cfg),
        "faits": "\n".join(f"- {f.id} : {f.claim}" for f in recherche.facts),
        "cadrage": f"Prefer {', '.join(channel.charte.framing.prefer)}; no full-body characters.",
        "mots_cibles": mots_cibles, "duree_cible_s": spec.target_duration_s,
        "mots_par_minute": mpm,
        "marqueurs_plantation": ", ".join(f'"{m}"' for m in patterns.marqueurs_plantation[:8]),
        "marqueurs_paiement": ", ".join(f'"{m}"' for m in patterns.marqueurs_paiement[:8]),
    }
    choix = script_module._accroche(  # noqa: SLF001 — même générateur que `script`
        gabarits, commun, gabarits["systeme"], source.hook.type, taxonomie, patterns, spec,
        mots_hook_max, mots_hook_min, trace, racine, alertes, decalage=0)
    tirages = 1
    while not choix.choisi.acceptable and tirages < script_module.ESSAIS_RETENTION:
        tirages += 1
        choix = script_module._accroche(  # noqa: SLF001
            gabarits, commun, gabarits["systeme"], source.hook.type, taxonomie, patterns, spec,
            mots_hook_max, mots_hook_min, trace, racine, alertes, decalage=tirages - 1)
    hook_text = choix.choisi.texte

    # --- budgets : la part de chaque segment dans le parent, rapportée à la cible ---
    corps = [s for s in source.segments if s.role != "hook"]
    mots_source = sum(s.word_count for s in corps) or 1
    budget_corps = max(1, mots_cibles - len(hook_text.split()))
    budgets = {s.id: max(12, round(s.word_count * budget_corps / mots_source)) for s in corps}
    consignes = "\n".join(f"- {c}" for c in langue.localisation.consignes) or "- (none)"
    produit = cfg.products.get(spec.product_id) if spec.product_id else None
    lignes = script_module._lignes_divulgation(produit, cfg, spec.lang) if produit else None  # noqa: SLF001

    adaptes: dict[str, dict[str, str]] = {}
    plants = [s for s in source.segments if s.open_loop == "plant"]
    payoffs = [s for s in source.segments if s.open_loop == "payoff"]
    reponses = {pay.id: plant.id for plant, pay in zip(plants, payoffs)}

    def _promesse(segment_id: str) -> str:
        plant_id = reponses.get(segment_id)
        if plant_id is None:
            return ""
        if plant_id == source.segments[0].id:
            return hook_text
        return adaptes.get(plant_id, {}).get("narration") or next(
            s.narration for s in source.segments if s.id == plant_id)

    def _adapter(segments: list[ScriptSegment], supplement: str, etiquette: str) -> None:
        for debut in range(0, len(segments), LOT):
            lot = segments[debut:debut + LOT]
            precedent_id = next((s.id for s in reversed(source.segments)
                                 if s.id < lot[0].id and s.id in adaptes), None)
            precedent = ("Previous adapted segment ends with: \""
                         + adaptes[precedent_id]["narration"][-200:] + "\"") if precedent_id else ""
            texte_lot = "\n".join(
                json.dumps({"id": s.id, "role": s.role,
                            "loop": {"plant": "PLANT", "payoff": "PAYOFF"}.get(s.open_loop, ""),
                            "answers": _promesse(s.id)[-240:],
                            "target_words": budgets[s.id], "source": s.narration,
                            "on_screen_text_source": s.on_screen_text or ""}, ensure_ascii=False)
                for s in lot)
            sponsor = ""
            if lignes and any(s.role == "sponsor" for s in lot):
                sponsor = f'- The sponsor segment must contain this sentence verbatim: "{lignes.spoken_line}"'
            prompt = GABARIT.format(
                source=source_nom, langue=cible_nom, sujet=spec.topic.sujet,
                angle=recherche.angle, hook=hook_text, precedent=precedent,
                consignes=consignes,
                glossaire=_glossaire(langue, spec.niche, " ".join(s.narration for s in lot)),
                plantation=commun["marqueurs_plantation"], paiement=commun["marqueurs_paiement"],
                consignes_supp="\n".join(x for x in (sponsor, supplement) if x),
                segments=texte_lot)
            donnees, _ = llm.generate_json(
                prompt, system=SYSTEME.format(langue=cible_nom), json_schema=SCHEMA_ADAPTATION,
                max_tokens=int(sum(budgets[s.id] for s in lot) * 2.2) + 300,
                temperature=0.5, seed=(spec.seed + debut) % 100000,
                etiquette=f"localize:{etiquette}", trace=trace, racine=racine)
            rendus = {str(e.get("id", "")).strip(): e for e in donnees.get("segments") or []}
            for s in lot:
                entree = rendus.get(s.id)
                if entree is None or not str(entree.get("narration", "")).strip():
                    alertes.append(f"{s.id} : absent de la réponse du modèle ({etiquette})")
                    continue
                adaptes[s.id] = {"narration": re.sub(r"\s+", " ", str(entree["narration"])).strip(),
                                 "on_screen_text": str(entree.get("on_screen_text") or "")}

    _adapter(corps, "", "adaptation")
    manquants = [s for s in corps if s.id not in adaptes]
    if manquants:
        _adapter(manquants, "", "adaptation-reprise")
    # Dérive de langue : un segment qui a gardé la source est réadapté une fois.
    derives = [s for s in corps if s.id in adaptes
               and _derive(adaptes[s.id]["narration"], source.lang) > DERIVE_MAX]
    if derives:
        alertes.append(f"dérive de langue sur {len(derives)} segment(s), réadaptés")
        _adapter(derives, f"- Write ONLY in {cible_nom}. No {source_nom} word may remain.",
                 "derive")
    manquants = [s.id for s in corps if s.id not in adaptes]
    if manquants:
        raise RuntimeError(f"adaptation incomplète : {', '.join(manquants)}")

    def _assembler() -> Script:
        segments: list[ScriptSegment] = []
        for s in source.segments:
            if s.role == "hook":
                narration, ecran = hook_text, script_module._texte_ecran(  # noqa: SLF001
                    choix.choisi.on_screen_text)
            else:
                narration = script_module._retailler(  # noqa: SLF001
                    adaptes[s.id]["narration"], round(budgets[s.id] * 1.2))
                ecran = script_module._texte_ecran(adaptes[s.id]["on_screen_text"]) \
                    if s.on_screen_text else None  # noqa: SLF001
            segments.append(s.model_copy(update={
                "narration": narration, "on_screen_text": ecran}))
        mots = sum(s.word_count for s in segments)
        return Script(lang=spec.lang, hook=Hook(type=source.hook.type, text=hook_text),
                      segments=segments, editorial_signature=source.editorial_signature,
                      music_mood=source.music_mood, word_count=mots,
                      estimated_duration_s=round(mots / (mpm / 60), 1), disclosure_lines=lignes)

    script = _assembler()
    boucles_minimum = referentiel.boucles_minimum(spec.niche, racine)
    rapport = script_module._verifier(  # noqa: SLF001
        script, patterns=patterns, niche=spec.niche, spec=spec, mpm=mpm,
        mots_hook_max=mots_hook_max, mots_hook_min=mots_hook_min,
        boucles_minimum=boucles_minimum, tolerance=tolerance, densite_cible=densite_cible,
        recherche=recherche, racine=racine, trace=trace)
    historique: list[str] = []
    reprises = 0
    while not rapport.conforme and reprises < REPRISES_MAX:
        cibles = [s for s in corps if s.id in rapport.segments_a_reecrire()]
        historique.append("; ".join(str(i) for i in rapport.bloquantes)[:300])
        if not cibles:
            break
        reprises += 1
        _adapter(cibles, "Fix these problems:\n" + rapport.consignes(), f"reprise{reprises}")
        script = _assembler()
        rapport = script_module._verifier(  # noqa: SLF001
            script, patterns=patterns, niche=spec.niche, spec=spec, mpm=mpm,
            mots_hook_max=mots_hook_max, mots_hook_min=mots_hook_min,
            boucles_minimum=boucles_minimum, tolerance=tolerance, densite_cible=densite_cible,
            recherche=recherche, racine=racine, trace=trace)
    runs.ecrire_json(chemins.script, script)

    # Nombres perdus : signalés au relecteur, jamais corrigés en silence.
    for s_src, s_ad in zip(source.segments, script.segments):
        perdus = {n for n in _nombres(s_src.narration) if len(n) > 1} - _nombres(s_ad.narration)
        if perdus and s_src.role != "hook":
            alertes.append(f"{s_src.id} : nombre(s) {', '.join(sorted(perdus))} absent(s) de "
                           "l'adaptation — à vérifier en relecture (conversion d'unité ?)")

    secondes = time.perf_counter() - t0
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.hook_type = source.hook.type
    manifest.decisions.hook_candidates = [
        CandidatHook(text=c.texte, words=c.mots, score=round(min(100.0, c.score), 1),
                     violations=list(c.infractions)) for c in choix.candidats]
    manifest.decisions.hook_chosen = hook_text
    manifest.decisions.hook_choice_reason = choix.motif
    manifest.decisions.duration_s = script.estimated_duration_s
    comptage = rapport.densite or density_module.mesurer_script(script, mpm)
    manifest.decisions.density_facts_per_min = comptage.faits_par_minute
    plantees, payees = loops_module.resume(rapport.boucles)
    manifest.decisions.retention = VerificationRetention(
        regenerations=reprises, violations=[str(i) for i in rapport.infractions],
        historique=historique, interrupts_planned=rapport.ruptures_posees,
        interrupt_cadence_s=rapport.cadence_s, interrupt_max_gap_s=rapport.ecart_rupture_max_s,
        loops_planted_marked=plantees, loops_paid_verified=payees,
        loops_unjudged=sum(1 for b in rapport.boucles if b.coherente is None),
        seconds=round(secondes, 2))
    manifest.decisions.open_loops.planted = sum(1 for s in script.segments if s.open_loop == "plant")
    manifest.decisions.open_loops.paid = sum(1 for s in script.segments if s.open_loop == "payoff")
    manifest.execution.timings["script"] = round(secondes, 2)
    manifest.execution.timings["script_llm"] = round(trace.secondes, 2)
    manifest.execution.timings["script_appels"] = len(trace.appels)
    if manifest.declinaison is not None:
        manifest.declinaison.adaptation_s = round(secondes, 1)
    # L'angle est celui du parent : c'est le même sujet, adapté (contrôle 17 du precheck).
    manifest.conformite.editorial_angle = AngleEditorialManifeste(
        type=source.editorial_signature.angle, resume=recherche.angle[:300] or spec.topic.sujet)
    motifs = [str(i) for i in rapport.bloquantes if i.code != "densite_sous_cible"]
    if densite_plancher is not None and comptage.faits_par_minute < densite_plancher:
        motifs.append(f"densite_sous_plancher : {comptage.faits_par_minute:.2f} fait(s)/min")
    if motifs:
        manifest.execution.run_state = "failed"
        manifest.execution.blocked_reason = ("adaptation refusée par la vérification de "
                                             "rétention : " + " ; ".join(motifs))
        manifest.execution.errors.append(ErreurRun(step="script", ts=runs.maintenant(), code=4,
                                                   message=" ; ".join(motifs)[:500], retry=reprises))
    else:
        manifest.execution.run_state = "awaiting_review"
        manifest.execution.blocked_reason = None
    runs.ecrire_json(chemins.manifest, manifest)
    alertes.insert(0, f"déclinaison de {spec.parent_id} ({source.lang} → {spec.lang}) : "
                      "script adapté, pas écrit")
    return script_module.ResultatScript(
        script, source.hook.type, 0.0, mots_cibles, secondes, 0, alertes, trace,
        rapport=rapport, regenerations=reprises,
        echec=manifest.execution.blocked_reason if motifs else None)


# --------------------------------------------------------------------------------------
# 3 — mesures, parent, orchestrateur
# --------------------------------------------------------------------------------------

def distance_miniatures(a: Path, b: Path) -> int | None:
    """Distance de Hamming entre les pHash de deux miniatures (imagehash)."""
    if not a.exists() or not b.exists():
        return None
    import imagehash
    from PIL import Image
    return int(imagehash.phash(Image.open(a)) - imagehash.phash(Image.open(b)))


def mesurer(video_id: str, racine: Path | None = None) -> Declinaison:
    """Réutilisation, coût relatif, distance des miniatures ; parent mis à jour."""
    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    if manifest.declinaison is None:
        raise DeclinaisonImpossible(f"{video_id} n'est pas une déclinaison")
    d = manifest.declinaison
    parent = RunPaths.depuis_video_id(d.parent_id, racine)
    stats_f = chemins.racine / "heritage_stats.json"
    if stats_f.exists():
        stats = json.loads(stats_f.read_text(encoding="utf-8"))
        d.assets_reused = int(stats.get("prompt", 0))
        d.assets_reused_same_segment = int(stats.get("segment", 0))
        d.assets_generated = int(stats.get("generees", 0))
        total = d.assets_reused + d.assets_reused_same_segment + d.assets_generated
        d.assets_reused_ratio = round((total - d.assets_generated) / total, 3) if total else None
    manifest_p = runs.charger_manifest(d.parent_id, racine)
    d.parent_compute_min = manifest_p.execution.cost.compute_min
    if manifest.execution.cost.compute_min and d.parent_compute_min:
        d.compute_ratio = round(manifest.execution.cost.compute_min / d.parent_compute_min, 3)
    d.thumbnail_phash_distance = distance_miniatures(chemins.thumbnail, parent.thumbnail)
    runs.ecrire_json(chemins.manifest, manifest)

    for enfant in manifest_p.children:
        if enfant.video_id == video_id:
            enfant.compute_ratio = d.compute_ratio
    runs.ecrire_json(parent.manifest, manifest_p)

    # Localisations du parent : titre et description de l'enfant, relus avec lui.
    meta_e, meta_p = chemins.racine / "metadata.json", parent.racine / "metadata.json"
    if meta_e.exists() and meta_p.exists():
        e, p = (json.loads(f.read_text(encoding="utf-8")) for f in (meta_e, meta_p))
        loc = p.setdefault("localizations", {})
        loc[manifest.identite.lang] = {"title": e["title_chosen"][:100],
                                       "description": e["description"]}
        loc.setdefault(manifest_p.identite.lang, {"title": p["title_chosen"][:100],
                                                  "description": p["description"]})
        meta_p.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return d


def executer(parent_id: str, cible: str, racine: Path | None = None) -> ResultatDeclinaison:
    """`factory localize` : squelette, puis le DAG normal à partir de `script`, puis mesures."""
    from factory import run as run_module

    racine = racine or racine_projet()
    video_id, alertes = creer_enfant(parent_id, cible, racine)
    resultat = run_module.executer(video_id=video_id, racine=racine)
    alertes += resultat.alertes
    declinaison = mesurer(video_id, racine) if resultat.etat != "failed" else None
    return ResultatDeclinaison(video_id, parent_id, resultat.etat, declinaison, alertes)


def chaines_derivees(channel_id: str, racine: Path | None = None) -> list[str]:
    """Chaînes dont `derive_from` vaut `channel_id`."""
    cfg = config_module.charger(racine, strict=False)
    return sorted(c.id for c in cfg.channels.values() if c.derive_from == channel_id)


def enfiler_declinaisons(conn: sqlite3.Connection, parent_id: str,
                         racine: Path | None = None) -> list[tuple[str, int]]:
    """Orchestrateur : un job par chaîne `derive_from`, enfilé à l'étape `script`."""
    from factory.orchestrator import queue as queue_module

    racine = racine or racine_projet()
    spec = runs.charger_spec(parent_id, racine)
    if spec.parent_id:
        return []  # une déclinaison ne se décline pas
    sortie: list[tuple[str, int]] = []
    for cible in chaines_derivees(spec.channel_id, racine):
        video_id, _ = creer_enfant(parent_id, cible, racine)
        if conn.execute("SELECT 1 FROM jobs WHERE video_id = ?", (video_id,)).fetchone():
            continue
        job = queue_module.enfiler(conn, video_id, cible, stage="script")
        sortie.append((video_id, job.id))
    return sortie
