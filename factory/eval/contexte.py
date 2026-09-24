"""Tout ce qu'une mesure peut avoir besoin de lire, chargé une fois et partagé.

Les sondes coûteuses — détection de plans, silences, `ffprobe` — sont **mémoïsées** : neuf
familles de mesures les demandent, elles ne s'exécutent qu'une fois. C'est ce qui tient la
contrainte des trois minutes sur une vidéo de dix.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from factory.core import config as config_module
from factory.core import referentiel as ref_module
from factory.core import runs
from factory.core.models import Channel, QcConfig, Script, Shotlist, VideoSpec
from factory.core.paths import RunPaths, racine_projet
from factory.eval import base


@dataclass
class ContexteQc:
    """Un run, ses fichiers, sa niche et le barème qui s'y applique."""

    video_id: str
    racine: Path
    chemins: RunPaths
    spec: VideoSpec
    channel: Channel
    qc: QcConfig
    video: Path
    dossier_travail: Path
    #: Ce que le banc n'a pas pu lire, nommé plutôt que deviné.
    absents: list[str] = field(default_factory=list)

    @classmethod
    def charger(
        cls, video_id: str, racine: Path | None = None, video: Path | None = None
    ) -> ContexteQc:
        """Ouvre un run. `video` permet de noter un fichier autre que `final.mp4` (calibration)."""
        base_racine = racine or racine_projet()
        chemins = RunPaths.depuis_video_id(video_id, racine)
        spec = runs.charger_spec(video_id, racine)
        cfg = config_module.charger(racine, strict=False)
        qc = cfg.qc
        if qc is None:
            raise FileNotFoundError("config/qc.yaml absent : le banc n'a pas de barème")
        contexte = cls(
            video_id=video_id, racine=base_racine, chemins=chemins, spec=spec,
            channel=cfg.get_channel(spec.channel_id), qc=_avec_surcharges(qc, spec.niche),
            video=video or chemins.final,
            # Une mesure de calibration note un autre fichier : ses images vont dans un
            # sous-dossier à part, sinon elle écraserait les images du run qu'elle emprunte.
            dossier_travail=(
                chemins.racine / "qc" if video is None
                else chemins.racine / "qc" / f"calibration-{Path(video).stem}"
            ),
        )
        contexte.dossier_travail.mkdir(parents=True, exist_ok=True)
        return contexte

    # -- fichiers du run -----------------------------------------------------------------

    @cached_property
    def script(self) -> Script | None:
        """`script.json`. `None` si absent : les mesures concernées sortent `skipped`."""
        return self._modele(self.chemins.script, Script, "script.json")

    @cached_property
    def shotlist(self) -> Shotlist | None:
        """`shotlist.json` — les paramètres de rendu, donc les cibles de lisibilité."""
        return self._modele(self.chemins.shotlist, Shotlist, "shotlist.json")

    @cached_property
    def words(self) -> dict[str, Any] | None:
        """`words.json` — sans lui ni le débit ni la couverture des sous-titres ne se mesurent."""
        if not self.chemins.words.exists():
            self.absents.append("words.json")
            return None
        return json.loads(self.chemins.words.read_text(encoding="utf-8"))

    def _modele(self, chemin: Path, modele: type, nom: str):
        if not chemin.exists():
            self.absents.append(nom)
            return None
        return modele.model_validate_json(chemin.read_text(encoding="utf-8"))

    # -- cibles --------------------------------------------------------------------------

    @cached_property
    def manifest(self):
        """`manifest.json` du run. `None` s'il manque."""
        from factory.core import runs as runs_module

        try:
            return runs_module.charger_manifest(self.video_id, None if self.racine is None
                                                else self.racine)
        except (FileNotFoundError, ValueError):
            self.absents.append("manifest.json")
            return None

    @cached_property
    def niche(self) -> dict[str, Any]:
        """Bloc de la niche dans `REFERENTIEL.json`."""
        return ref_module.niche(self.spec.niche, self.racine)

    @cached_property
    def production(self) -> dict[str, Any]:
        """Bloc `production` du référentiel : les cibles qui ne viennent pas du registre."""
        return ref_module.charger(self.racine).get("production", {})

    def seuil(self, nom: str) -> dict[str, Any]:
        """Paramètres d'une mesure dans `config/qc.yaml`, en dictionnaire nu."""
        bloc = self.qc.seuils.get(nom)
        return {} if bloc is None else bloc.model_dump(exclude_none=True)

    def mesure_param(self, famille: str) -> dict[str, Any]:
        """Paramètres d'outillage d'une famille (seuils de détection, tailles d'échantillon)."""
        return dict(self.qc.mesure.get(famille, {}))

    # -- sondes mémoïsées ----------------------------------------------------------------

    @cached_property
    def sonde(self) -> dict[str, Any]:
        """`ffprobe` du fichier noté."""
        return base.sonde(self.video)

    @cached_property
    def duree_s(self) -> float:
        """Durée du fichier livré, en secondes."""
        return float(self.sonde["format"]["duration"])

    @cached_property
    def fps(self) -> float:
        """Cadence du flux vidéo, lue et non supposée."""
        flux = next(f for f in self.sonde["streams"] if f["codec_type"] == "video")
        num, _, den = str(flux.get("avg_frame_rate", "30/1")).partition("/")
        return float(num) / float(den) if float(den) else 30.0

    @cached_property
    def scenes(self) -> list[tuple[float, float]]:
        """Plans détectés sur le fichier livré — la seule vérité sur le rythme **perçu**."""
        params = self.mesure_param("coupes")
        return base.detecter_scenes(
            self.video,
            seuil=float(params.get("seuil_contentdetector", 27.0)),
            min_scene_s=float(params.get("min_scene_s", 0.5)),
            fps=self.fps,
        )

    @cached_property
    def silences(self) -> list[tuple[float, float]]:
        """Silences `(début, durée)` au seuil de `config/qc.yaml`."""
        params = self.mesure_param("audio")
        return base.detecter_silences(
            self.video,
            seuil_db=float(params.get("seuil_silence_db", -35.0)),
            duree_min_s=float(params.get("silence_min_s", 0.4)),
        )

    @cached_property
    def loudness(self):
        """`ebur128` : niveau intégré, crête réelle, plage de dynamique."""
        from factory import audio as audio_module

        return audio_module.measure_lufs(self.video)


def _avec_surcharges(qc: QcConfig, niche: str) -> QcConfig:
    """Applique `surcharges_par_niche[<niche>]` au barème. Fusion par clé, jamais remplacement.

    Une niche de plateau (`true_crime`) coupe toutes les 15 s : lui appliquer le barème de
    `home_hacks` ferait échouer une vidéo correcte. La surcharge n'existe que pour cela.
    """
    surcharge = qc.surcharges_par_niche.get(niche)
    if not surcharge:
        return qc
    brut = qc.model_dump()
    for cle, valeur in surcharge.items():
        if isinstance(valeur, dict) and isinstance(brut.get(cle), dict):
            for sous_cle, sous_valeur in valeur.items():
                if isinstance(sous_valeur, dict) and isinstance(brut[cle].get(sous_cle), dict):
                    brut[cle][sous_cle] = {**brut[cle][sous_cle], **sous_valeur}
                else:
                    brut[cle][sous_cle] = sous_valeur
        else:
            brut[cle] = valeur
    brut.pop("surcharges_par_niche", None)
    return QcConfig.model_validate({**brut, "surcharges_par_niche": {}})
