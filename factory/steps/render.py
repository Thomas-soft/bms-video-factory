"""Étape `render` — `prepare_assets` puis `render_shot` pour chaque plan, et rien de spécifique.

Cette étape ne sait pas ce qu'est une carte, une image ou un avatar. Elle résout un style en
moteur, lui demande ses assets, lui demande un clip par plan, **mesure chaque clip par `ffprobe`**
et inscrit les temps au manifeste. Tout ce qui change d'un style à l'autre est derrière
`StyleEngine` (`ARCHITECTURE.md` § 5) : c'est la raison d'être de l'interface.

Un clip hors tolérance fait échouer **ce plan**, pas le run (`INTERFACES.md` § clips) : les écarts
sont collectés, rapportés, et l'étape sort en code 1 s'il en reste un.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from factory.core import config as config_module
from factory.core import db, runs
from factory.core.models import Asset, ReutilisationBibliotheque, Shotlist
from factory.core.paths import RunPaths, racine_projet
from factory.styles import moteur_de_chaine

#: Journal de l'étape : toute la sortie ffmpeg y va (`CLAUDE.md` § 2).
JOURNAL = "workspace/logs/etape12_1.log"


class RenduIncomplet(RuntimeError):
    """Au moins un clip n'est pas au contrat de format ; le message liste les écarts.

    Porte le résultat complet : l'appelant doit pouvoir montrer ce qui a été rendu **et** ce qui
    manque, pas seulement le premier message d'erreur.
    """

    def __init__(self, message: str, resultat: "ResultatRendu | None" = None) -> None:
        super().__init__(message)
        self.resultat = resultat


@dataclass
class ResultatRendu:
    """Ce que le rendu a produit et ce qu'il a coûté."""

    clips: int
    style_id: str
    moteur: str
    secondes_total: float
    secondes_assets: float
    secondes_par_plan: dict[str, float]
    ecarts: list[str] = field(default_factory=list)
    alertes: list[str] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    #: Ce que le moteur a mesuré pendant `prepare_assets` — générations, reprises de
    #: bibliothèque, temps par image, pic mémoire. Vide pour un moteur qui ne mesure rien.
    mesures_moteur: dict = field(default_factory=dict)

    @property
    def secondes_median_par_plan(self) -> float:
        import statistics

        return statistics.median(self.secondes_par_plan.values()) if self.secondes_par_plan else 0.0


def executer(
    video_id: str, racine: Path | None = None, style_surcharge: str | None = None,
    force: bool = False,
) -> ResultatRendu:
    """Rend tous les plans de `shotlist.json` en `clips/shot_XX.mp4`."""
    t0 = time.perf_counter()
    base = racine or racine_projet()
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.shotlist.exists():
        raise FileNotFoundError(
            f"shotlist.json absent : lance `factory shotlist --run {video_id}`"
        )
    shotlist = Shotlist.model_validate_json(chemins.shotlist.read_text(encoding="utf-8"))

    journal = base / JOURNAL
    journal.parent.mkdir(parents=True, exist_ok=True)
    alertes: list[str] = []
    ecarts: list[str] = []
    secondes_par_plan: dict[str, float] = {}

    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n===== render {video_id} — {runs.maintenant()} =====\n")
        langue = cfg.languages.get(channel.lang)
        divulgation = langue.disclosure.overlay_generic if langue else None
        if divulgation is None:
            alertes.append(
                f"config/languages/{channel.lang}.yaml : `disclosure.overlay_generic` absent — "
                "le bandeau de divulgation tomberait sur un repli en dur"
            )
        moteur = moteur_de_chaine(
            channel, cfg.styles, racine=base, journal=trace, surcharge=style_surcharge
        )
        moteur.texte_divulgation = divulgation
        style_id = style_surcharge or channel.style
        trace.write(
            f"style={style_id} moteur={moteur.name} backend={moteur.backend} "
            f"plans={len(shotlist.shots)}\n"
        )

        t_assets = time.perf_counter()
        assets = moteur.prepare_assets(shotlist, channel, chemins)
        secondes_assets = time.perf_counter() - t_assets
        trace.write(f"prepare_assets : {len(assets)} asset(s) en {secondes_assets:.2f} s\n")

        par_plan = {asset.path.split("/")[1]: asset for asset in assets if "/" in asset.path}
        for shot in shotlist.shots:
            clip = chemins.clip(shot.id)
            if clip.exists() and not force and not moteur.verify_clip(clip, shot.duration_s):
                secondes_par_plan[shot.id] = 0.0
                trace.write(f"{shot.id} : clip conforme déjà présent, réemployé\n")
                continue
            debut = time.perf_counter()
            try:
                produit = moteur.render_shot(
                    shot, [par_plan[shot.id]] if shot.id in par_plan else [], channel, chemins
                )
            except Exception as erreur:  # le plan échoue, pas le run
                ecarts.append(f"{shot.id} : {erreur}")
                trace.write(f"{shot.id} : ÉCHEC — {erreur}\n")
                continue
            secondes_par_plan[shot.id] = time.perf_counter() - debut
            defauts = moteur.verify_clip(produit, shot.duration_s)
            ecarts.extend(defauts)
            trace.write(
                f"{shot.id} : {shot.duration_s:.3f} s · {shot.motion} · "
                f"{shot.asset_request.prompt_or_keywords} · {secondes_par_plan[shot.id]:.2f} s"
                + (" · ÉCARTS : " + " ; ".join(defauts) if defauts else " · conforme") + "\n"
            )

    mesures = dict(getattr(moteur, "mesures", {}) or {})

    secondes = time.perf_counter() - t0
    manifest = runs.charger_manifest(video_id, racine)
    manifest.execution.timings["render"] = round(secondes, 2)
    manifest.execution.timings["render_assets"] = round(secondes_assets, 2)
    manifest.execution.timings["render_par_plan_median"] = round(
        _mediane(list(secondes_par_plan.values())), 3
    )
    manifest.execution.timings["render_n_clips"] = len(
        [s for s in shotlist.shots if chemins.clip(s.id).exists()]
    )
    manifest.decisions.assets = assets
    # La réutilisation est **la** mesure de cette brique : elle doit confirmer ou infirmer que la
    # bibliothèque fait tomber le coût par plan (`INTERFACES.md` § manifeste).
    if "assets_generated" in mesures:
        manifest.decisions.library_reuse = ReutilisationBibliotheque(
            assets_reused=int(mesures.get("assets_reused", 0)),
            assets_generated=int(mesures.get("assets_generated", 0)),
            reuse_ratio=float(mesures.get("reuse_ratio", 0.0)),
        )
    temps_images = [float(x) for x in mesures.get("image_seconds", [])]
    if temps_images:
        manifest.execution.timings["render_image_median"] = round(_mediane(temps_images), 2)
        manifest.execution.timings["render_image_total"] = round(sum(temps_images), 2)
        manifest.execution.timings["render_image_n"] = len(temps_images)
    if mesures.get("image_peak_mlx_gb") is not None:
        manifest.execution.timings["render_image_peak_mlx_gb"] = float(
            mesures["image_peak_mlx_gb"]
        )
    if mesures.get("depth_seconds"):
        manifest.execution.timings["render_depth"] = float(mesures["depth_seconds"])
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()

    resultat = ResultatRendu(
        clips=len([s for s in shotlist.shots if chemins.clip(s.id).exists()]),
        style_id=style_id, moteur=moteur.name, secondes_total=secondes,
        secondes_assets=secondes_assets, secondes_par_plan=secondes_par_plan,
        ecarts=ecarts, alertes=alertes, assets=assets, mesures_moteur=mesures,
    )
    if ecarts:
        raise RenduIncomplet(
            f"{len(ecarts)} écart(s) au contrat de format sur {len(shotlist.shots)} plan(s) — "
            + " ; ".join(ecarts[:5]),
            resultat,
        )
    return resultat


def _mediane(valeurs: list[float]) -> float:
    import statistics

    return statistics.median(valeurs) if valeurs else 0.0
