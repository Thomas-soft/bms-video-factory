"""`factory qc` — le banc, et le portillon.

Il mesure `final.mp4` face aux cibles de sa niche, écrit `qc.json`, note le manifeste et la
table `runs`. Rien ne se publie sans lui (`ROADMAP.md` étape 15).

**Trois choix qui font la valeur du score, et qu'il faut connaître avant de le lire :**

1. *Le score est une moyenne pondérée des familles notées, jamais une somme.* Une famille
   entièrement `skipped` — faute de cible mesurée — sort du numérateur **et** du dénominateur.
   Un run n'est donc pas puni pour une niche que le registre n'a pas mesurée, et le score reste
   comparable d'une vidéo à l'autre. Le nombre de familles notées est publié à côté du score.
2. *Un contrôle bloquant ne note pas, il refuse.* Les six bloquants du prompt de l'étape 15
   donnent un `FAIL` quel que soit le score : une vidéo à 92 dont le niveau sonore est hors
   norme ne se publie pas.
3. *Le score n'est pas une prédiction de rétention.* Il mesure la conformité aux cibles du
   registre. Sa valeur prédictive sera établie — ou infirmée — à l'étape 26, en corrélant
   `qc_score` aux vues réelles. D'ici là, `docs/QC.md` § recalibration dit comment.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factory.core import db, runs
from factory.core.paths import RunPaths, chemin_base
from factory.eval.base import Famille
from factory.eval.contexte import ContexteQc
from factory.eval.metrics import FAMILLES

#: Version du banc. Toute modification du barème ou d'une formule l'incrémente : sans elle,
#: l'étape 26 corrélerait des scores calculés par deux bancs différents.
#: `1.1.0` à l'étape 16 : cinq mesures ajoutées (hook_pattern_score,
#: hook_forbidden_wording, open_loops_verified, interrupt_gap, density_vs_target) et
#: poids de `structure` porté de 5 à 10. Les scores d'avant ne sont pas comparables.
VERSION = "qc/1.1.0"

#: Étape du pipeline à rejouer pour corriger chaque mesure (`regenerate_steps` d'INTERFACES.md).
ETAPE_CORRECTRICE = {
    "cut_rhythm": "shotlist", "cut_dispersion": "shotlist", "cut_long_shots": "shotlist",
    "cut_rhythm_hook": "shotlist", "duree_vs_run": "script", "duree_vs_niche": "script",
    "loudness": "assemble", "true_peak": "assemble", "loudness_range": "voice",
    "silence_long": "voice", "music_bed_attenuation": "assemble",
    "speech_rate": "voice", "respiration": "script",
    "hook_visual_change": "shotlist", "hook_text_present": "shotlist",
    "hook_length": "script", "hook_type_rules": "script",
    "text_size": "render", "text_contrast": "render", "on_screen_words": "script",
    "visual_variety": "render", "visual_redundancy": "shotlist",
    "visual_distinct_ratio": "shotlist", "speech_rate_p90": "voice",
    "cut_redundancy": "shotlist", "cut_rhythm_by_minute": "shotlist",
    "hook_first_word": "voice", "subtitle_track": "assemble",
    "subtitle_coverage": "subtitles", "subtitle_line_length": "subtitles",
    "sponsor_position": "script", "open_loops_paid": "script", "open_loop_position": "script",
}


@dataclass
class ResultatQc:
    """Ce que le banc a mesuré, et ce qu'il en conclut."""

    video_id: str
    familles: list[Famille]
    score: float
    verdict: str
    raisons: list[str]
    verdict_pipeline: str
    etapes_a_rejouer: list[str]
    secondes: float
    absents: list[str] = field(default_factory=list)
    non_couvert: list[str] = field(default_factory=list)
    temps_par_famille: dict[str, float] = field(default_factory=dict)
    chemin: Path | None = None

    @property
    def mesures(self) -> dict[str, Any]:
        """Toutes les mesures, à plat, indexées par nom."""
        return {m.nom: m for famille in self.familles for m in famille.mesures}

    def plus_faibles(self, combien: int = 3) -> list[tuple[str, float]]:
        """Les mesures notées les plus basses, dans l'ordre croissant."""
        notees = [(m.nom, m.score) for m in self.mesures.values() if m.score is not None]
        return sorted(notees, key=lambda couple: couple[1])[:combien]

    def json(self) -> dict[str, Any]:
        """Contenu de `qc.json`.

        Deux vues du même résultat cohabitent : `metrics` (le contrat de l'étape 15) et
        `checks` (le contrat d'`INTERFACES.md` § qc.json, que l'étape 22.2 consomme). Elles
        sont calculées à partir des mêmes objets, jamais saisies deux fois.
        """
        mesures = self.mesures
        return {
            "schema_version": "1.0",
            "version": VERSION,
            "run": self.video_id,
            "score": round(self.score, 1),
            "verdict": self.verdict,
            "reasons": self.raisons,
            "families": {
                f.nom: {
                    "weight": f.poids,
                    "score": None if f.score is None else round(f.score, 1),
                    "metrics": [m.nom for m in f.mesures],
                }
                for f in self.familles
            },
            "metrics": {nom: mesure.json() for nom, mesure in mesures.items()},
            "checks": [
                {
                    "id": nom, "measured": mesure.valeur, "target": mesure.cible,
                    "tolerance": None, "status": mesure.statut, "source": mesure.source,
                }
                for nom, mesure in mesures.items()
            ],
            "verdict_pipeline": self.verdict_pipeline,
            "regenerate_steps": self.etapes_a_rejouer,
            "missing_inputs": self.absents,
            "not_covered": self.non_couvert,
            "bench_seconds": round(self.secondes, 1),
            "bench_seconds_by_family": self.temps_par_famille,
        }


def executer(
    video_id: str, racine: Path | None = None, video: Path | None = None, ecrire: bool = True
) -> ResultatQc:
    """Mesure un run et rend son verdict. `video` note un autre fichier que `final.mp4`."""
    t0 = time.perf_counter()
    contexte = ContexteQc.charger(video_id, racine, video)
    if not contexte.video.exists():
        raise FileNotFoundError(
            f"{contexte.video} absent : `factory export --run {video_id}` d'abord"
        )
    familles, temps = [], {}
    for module in FAMILLES:
        depart = time.perf_counter()
        familles.append(module.mesurer(contexte))
        temps[familles[-1].nom] = round(time.perf_counter() - depart, 1)
    resultat = _conclure(contexte, familles, time.perf_counter() - t0)
    resultat.temps_par_famille = temps
    if ecrire:
        _ecrire(contexte, resultat, racine)
    return resultat


def noter_fixture(chemin: Path, racine: Path | None = None) -> ResultatQc:
    """Note un jeu de valeurs idéales (`tests/fixtures/qc_cible.json`).

    La calibration a besoin de savoir ce que vaut une vidéo **exactement aux cibles**, et une
    telle vidéo n'existe pas : la fabriquer coûterait des heures de rendu pour vérifier une
    arithmétique. La fixture ne porte que des **valeurs mesurées** ; les seuils, les poids et
    les fonctions de score sont ceux de `config/qc.yaml` et de `factory/eval/base.py`, lus au
    moment du calcul. Ce qui est calibré, c'est donc le barème déployé — pas une copie.
    """
    from factory.core import config as config_module
    from factory.eval.base import Mesure

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    cfg = config_module.charger(racine, strict=False)
    if cfg.qc is None:
        raise FileNotFoundError("config/qc.yaml absent")
    familles = []
    for nom, bloc in donnees["familles"].items():
        famille = Famille(nom, poids=cfg.qc.poids.get(nom, 0))
        for brut in bloc["mesures"]:
            score = _score_de_fixture(brut, cfg.qc)
            famille.mesures.append(Mesure(
                nom=brut["nom"], valeur=brut["valeur"], unite=brut.get("unite", ""),
                cible=brut.get("cible"), source="fixture de calibration",
                origine_cible=brut.get("origine_cible", "fixture"), score=score,
                poids=brut.get("poids", 1), bloquant=brut.get("bloquant", False),
                statut="skipped" if score is None else _statut(score),
                note=brut.get("note", ""),
            ))
        familles.append(famille)
    score, _ = _score_global(familles)
    raisons, verdict_pipeline, etapes = _verdicts(familles, score, cfg.qc, [])
    return ResultatQc(
        video_id=donnees.get("run", chemin.stem), familles=familles, score=score,
        verdict="PASS" if not raisons else "FAIL", raisons=raisons,
        verdict_pipeline=verdict_pipeline, etapes_a_rejouer=etapes, secondes=0.0,
    )


def _score_de_fixture(brut: dict[str, Any], qc) -> float | None:
    """Applique à une valeur de fixture la fonction de score et les seuils du barème déployé."""
    from factory.eval import base as socle

    forme = brut.get("forme")
    if forme is None:
        return None
    params = dict(brut.get("params", {}))
    nom_seuil = brut.get("seuil")
    if nom_seuil and nom_seuil in qc.seuils:
        params = {**qc.seuils[nom_seuil].model_dump(exclude_none=True), **params}
    # « @cut_rhythm.dispersion_max » renvoie au barème déployé : la fixture ne recopie jamais un
    # seuil, sans quoi elle validerait une arithmétique périmée le jour où le seuil bouge.
    params = {
        cle: _resoudre(valeur_param, qc) for cle, valeur_param in params.items()
    }
    valeur = brut["valeur"]
    if forme == "part":
        return 100.0 * float(valeur)
    if forme == "booleen":
        return socle.score_booleen(bool(valeur))
    if forme == "cible":
        return socle.score_cible(
            float(valeur), float(brut["cible"]),
            float(params["tolerance"]), float(params["plage"]),
        )
    if forme == "min":
        return socle.score_min(float(valeur), float(params["min"]), float(params["zero"]))
    if forme == "max":
        return socle.score_max(float(valeur), float(params["max"]), float(params["zero"]))
    if forme == "intervalle":
        return socle.score_intervalle(
            float(valeur), float(params["min"]), float(params["max"]),
            float(params.get("marge", 10.0)),
        )
    raise ValueError(f"forme de score inconnue dans la fixture : {forme}")


def _resoudre(valeur: Any, qc) -> Any:
    """Résout une référence « @<seuil>.<champ> » vers `config/qc.yaml`."""
    if not isinstance(valeur, str) or not valeur.startswith("@"):
        return valeur
    nom, _, champ = valeur[1:].partition(".")
    seuil = qc.seuils.get(nom)
    if seuil is None or getattr(seuil, champ, None) is None:
        raise ValueError(f"fixture : référence introuvable {valeur}")
    return getattr(seuil, champ)


def _statut(score: float) -> str:
    from factory.eval import base as socle

    return socle.statut_depuis(score)


def _score_global(familles: list[Famille]) -> tuple[float, int]:
    """Moyenne pondérée des familles notées, et leur nombre."""
    notees = [f for f in familles if f.score is not None and f.poids > 0]
    total = sum(f.poids for f in notees)
    if not total:
        return 0.0, 0
    return sum(f.score * f.poids for f in notees) / total, len(notees)


def _verdicts(
    familles: list[Famille], score: float, qc, absents: list[str]
) -> tuple[list[str], str, list[str]]:
    """Raisons d'échec, verdict de pipeline et étapes à rejouer."""
    raisons: list[str] = []
    etapes: list[str] = []
    bloque = False
    for famille in familles:
        for mesure in famille.mesures:
            if mesure.statut != "fail":
                continue
            etape = ETAPE_CORRECTRICE.get(mesure.nom)
            if etape and etape not in etapes:
                etapes.append(etape)
            if mesure.bloquant:
                raisons.append(
                    f"[bloquant] {mesure.nom} = {mesure.valeur} {mesure.unite} "
                    f"(cible {mesure.cible}) — {mesure.note}"
                )
                if (qc.seuils.get(mesure.nom) and
                        qc.seuils[mesure.nom].verdict_fail == "blocked"):
                    bloque = True
    # Objection A1, retenue : sur le run rtmk, la famille `coupes` valait 9,8/100 et le score
    # global 73,9 — les cinq familles à 100 la portaient. Une moyenne pondérée compense par
    # construction ; un plancher par famille refuse la compensation. Le portillon ne tient plus
    # aux seuls contrôles bloquants.
    plancher = qc.plancher_par_famille
    if plancher:
        for famille in familles:
            if famille.score is not None and famille.poids > 0 and famille.score < plancher:
                raisons.append(
                    f"famille {famille.nom} à {famille.score:.1f}/100, sous le plancher "
                    f"{plancher} — une moyenne pondérée ne rachète pas une famille effondrée"
                )
    seuil = qc.score_minimal_pour_publier
    if score < seuil:
        raisons.append(f"score {score:.1f} sous le seuil de publication {seuil}")
    for manquant in absents:
        raisons.append(f"entrée absente : {manquant} — mesures concernées non notées")
    if bloque:
        return raisons, "blocked", etapes
    return raisons, ("regenerate" if raisons else "pass"), etapes


def _conclure(contexte: ContexteQc, familles: list[Famille], secondes: float) -> ResultatQc:
    """Assemble le score, le verdict et les raisons."""
    score, _ = _score_global(familles)
    # Un fichier d'entrée manquant rend des mesures `skipped`, ce qui **monte** mécaniquement le
    # score en retirant du dénominateur. Il est donc porté en raison d'échec, jamais ignoré.
    bloquantes = [a for a in contexte.absents if a in ("words.json", "script.json", "shotlist.json")]
    raisons, verdict_pipeline, etapes = _verdicts(familles, score, contexte.qc, bloquantes)
    return ResultatQc(
        video_id=contexte.video_id, familles=familles, score=score,
        verdict="PASS" if not raisons else "FAIL", raisons=raisons,
        verdict_pipeline=verdict_pipeline, etapes_a_rejouer=etapes, secondes=secondes,
        absents=list(contexte.absents), non_couvert=list(contexte.qc.non_couvert),
    )


def _ecrire(contexte: ContexteQc, resultat: ResultatQc, racine: Path | None) -> None:
    """Écrit `qc.json`, porte la note au manifeste et à la table `runs`."""
    chemins = RunPaths.depuis_video_id(contexte.video_id, racine)
    chemins.qc.write_text(
        json.dumps(resultat.json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    resultat.chemin = chemins.qc

    manifest = runs.charger_manifest(contexte.video_id, racine)
    manifest.decisions.qc_score = round(resultat.score, 1)
    manifest.decisions.qc_verdict = resultat.verdict
    manifest.decisions.qc_version = VERSION
    mesures = resultat.mesures
    rythme = mesures.get("cut_rhythm")
    if rythme is not None and rythme.valeur is not None:
        manifest.decisions.cut_rhythm_measured_s = float(rythme.valeur)
    couverture = mesures.get("subtitle_coverage")
    if couverture is not None and couverture.valeur is not None:
        manifest.decisions.subtitle_coverage = float(couverture.valeur)
    manifest.execution.timings["qc"] = round(resultat.secondes, 2)
    runs.ecrire_json(chemins.manifest, manifest)

    conn = db.ouvrir(chemin_base(racine))
    runs.enregistrer(conn, contexte.spec, manifest, racine)
    # `runs.enregistrer` ne connaît pas la note du banc : elle est écrite ici, avec la version
    # du barème, sans quoi l'étape 26 corrélerait des scores calculés par deux bancs différents.
    conn.execute(
        "UPDATE runs SET score_qc = ?, qc_verdict = ?, qc_version = ?, "
        "cut_rhythm_measured_s = ?, updated_at = ? WHERE video_id = ?",
        (
            round(resultat.score, 1), resultat.verdict, VERSION,
            manifest.decisions.cut_rhythm_measured_s, runs.maintenant(), contexte.video_id,
        ),
    )
    conn.commit()
    conn.close()
