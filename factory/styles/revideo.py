"""Socle commun aux moteurs à backend Revideo : lancer `render.mjs`, redécouper le lot.

Extrait de `motion.py` à l'étape 30.2, quand un second moteur (`whiteboard`) a eu besoin des
mêmes gestes. Rien n'y est propre à un style : le fichier de lot, le lancement de Chromium, la
vérification du compte d'images et la découpe à l'image près valent pour **toute** scène Revideo.
Ce qui change d'un style à l'autre — quelles scènes, quelles props, quelle palette — reste dans
le moteur.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from factory import video
from factory.core.paths import RunPaths
from factory.styles.base import MoteurBase

#: Plans par lancement de Chromium, à défaut de `params.revideo.lot`.
LOT_DEFAUT = 20

#: Nom de fichier de police → famille CSS déclarée par `render/src/styles.css`. Une police de
#: charte absente de cette table ne peut pas être servie par le navigateur : le moteur le dit
#: plutôt que de laisser Chromium retomber sur une police système non redistribuable.
FAMILLES_CSS: dict[str, str] = {
    "Inter[opsz,wght].ttf": "BMSInter",
    "PlayfairDisplay[wght].ttf": "BMSPlayfair",
    "SourceSerif4[opsz,wght].ttf": "BMSSourceSerif",
    "Caveat[wght].ttf": "BMSCaveat",
}

#: Graisse de charte → graisse CSS.
POIDS_CSS: dict[str, int] = {
    "Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400, "Medium": 500,
    "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900,
}


class RenduRevideoEchoue(RuntimeError):
    """`render.mjs` n'a pas rendu un lot ; le message porte la fin du journal."""


@dataclass
class MoteurRevideo(MoteurBase):
    """Ce qu'un moteur Revideo répète : paramètres du projet, lancement, découpe."""

    #: Ce que le rendu a coûté : rempli par `prepare_assets`, lu par l'étape `render`.
    mesures: dict = field(default_factory=dict)

    # -- paramètres ----------------------------------------------------------------------

    @property
    def dossier_render(self) -> Path:
        # Résolu en absolu : `render.mjs` tourne avec `cwd=render/`, un chemin relatif ne s'y
        # relit pas. Le pipeline passe une racine absolue, un test peut passer `Path(".")`.
        return (self.racine / "render").resolve()

    @property
    def taille_lot(self) -> int:
        return int(self.param("revideo.lot", LOT_DEFAUT) or LOT_DEFAUT)

    @property
    def echelle(self) -> float:
        """Échelle de rendu. 1,0 = 1080p ; 0,667 = 720p suivi d'un agrandissement ffmpeg."""
        return float(self.param("scene.resolution_scale", 1.0) or 1.0)

    def famille_css(self, police: video.Police) -> dict:
        """Une police de charte → la famille CSS déclarée par `render/src/styles.css`."""
        famille = FAMILLES_CSS.get(police.fichier.name)
        if famille is None:
            raise FileNotFoundError(
                f"police « {police.nom_charte} » ({police.fichier.name}) : aucune règle @font-face "
                f"dans render/src/styles.css — ajoute-la et copie le fichier dans render/src/fonts/"
            )
        return {"family": famille, "weight": POIDS_CSS.get(police.graisse, 400)}

    def verifier_render(self) -> None:
        """Node et les dépendances du projet Revideo, avant toute promesse de rendu."""
        import shutil

        if shutil.which("node") is None:
            raise RenduRevideoEchoue(f"node introuvable — le moteur {self.name} en dépend")
        if not (self.dossier_render / "node_modules" / "@revideo" / "renderer").exists():
            raise RenduRevideoEchoue(
                f"dépendances absentes : lance `npm install` dans {self.dossier_render}"
            )

    # -- rendu ---------------------------------------------------------------------------

    def lancer_render(self, spec: dict, video_id: str, lot: str | None = None) -> list[dict]:
        """Lance `node render.mjs` et rend les manifestes de lot produits.

        Toute la sortie de Node va au journal de l'étape, jamais à l'écran (`CLAUDE.md` § 2).
        """
        fichier = self.dossier_render / "specs" / video_id / "batch.json"
        commande = ["node", "render.mjs", str(fichier)]
        if lot:
            commande += ["--lot", lot]
        environnement = dict(os.environ)
        environnement["DISABLE_TELEMETRY"] = "true"
        debut = time.perf_counter()
        produit = subprocess.run(
            commande, cwd=self.dossier_render, capture_output=True, text=True,
            env=environnement,
        )
        self.tracer(
            f"render.mjs {' '.join(commande[1:])} — code {produit.returncode} en "
            f"{time.perf_counter() - debut:.2f} s"
        )
        for ligne in (produit.stdout or "").splitlines():
            self.tracer(f"  node: {ligne}")
        if produit.returncode != 0:
            queue = "\n".join((produit.stderr or "").splitlines()[-12:])
            for ligne in (produit.stderr or "").splitlines():
                self.tracer(f"  node!: {ligne}")
            raise RenduRevideoEchoue(f"render.mjs code {produit.returncode} :\n{queue}")

        manifestes: list[dict] = []
        dossier = Path(spec["out_dir"])
        for entree in spec["lots"]:
            if lot and entree["name"] != lot:
                continue
            chemin = dossier / f"{entree['name']}.json"
            if not chemin.exists():
                raise RenduRevideoEchoue(f"manifeste de lot absent : {chemin}")
            manifestes.append(json.loads(chemin.read_text(encoding="utf-8")))
        return manifestes

    def decouper(self, manifeste: dict, run: RunPaths, durees: dict[str, float]) -> dict[str, float]:
        """Redécoupe la vidéo d'un lot en un clip par plan, à l'image près.

        Le manifeste donne la frontière en images ; `ffprobe` vérifie que la vidéo rendue porte
        bien le nombre d'images attendu **avant** toute découpe. Un écart signifie que Revideo
        n'a pas rendu ce qui était demandé : mieux vaut le dire que découper de travers.
        """
        source = Path(manifeste["fichier"])
        info = video.ffprobe_clip(source)
        images = int(round(info.duree_s * info.fps))
        attendues = int(manifeste["frames_attendues"])
        if abs(images - attendues) > 1:
            raise RenduRevideoEchoue(
                f"{source.name} : {images} images rendues pour {attendues} attendues — "
                f"la frontière de découpe des plans n'est pas fiable"
            )
        run.clips_dir.mkdir(parents=True, exist_ok=True)
        temps: dict[str, float] = {}
        for plan in manifeste["shots"]:
            debut = time.perf_counter()
            sortie = run.clip(plan["id"])
            # Le décalage d'une demi-image évite qu'un arrondi flottant fasse tomber la recherche
            # sur l'image précédente : à 30 ips, une demi-image vaut 16,7 ms.
            depart = (plan["frame_debut"] + 0.5) / manifeste["fps"]
            duree = durees.get(plan["id"], plan["frames"] / manifeste["fps"])
            arguments = [
                "-ss", f"{depart:.6f}", "-i", str(source),
                *video.arguments_encodage(sortie, duree),
            ]
            self.encoder(arguments)
            temps[plan["id"]] = time.perf_counter() - debut
        return temps

    def ecrire_specs(self, spec: dict, video_id: str) -> Path:
        """Écrit `render/specs/<video_id>/batch.json` et un fichier par lot ; rend le dossier."""
        dossier = self.dossier_render / "specs" / video_id
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "batch.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        for lot in spec["lots"]:
            (dossier / f"{lot['name']}.json").write_text(
                json.dumps(lot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
        return dossier
