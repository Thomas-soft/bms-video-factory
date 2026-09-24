"""Moteur « avatar2d » : personnage en calques animé par les visèmes de Rhubarb (étape 29).

Deux modes, choisis par `config/styles/avatar2d.yaml → params.mode` :

- **overlay** : le style hôte de la chaîne (`channel.style`) rend tous les plans ; sur les plans
  des segments `params.segments` (hook, cta), le personnage est incrusté à la position et à
  l'échelle du gabarit du run (`charte.layouts[template_id]`) ;
- **presenter** : sur ces mêmes plans, le personnage est seul, en grand, sur le fond de charte.

Chaîne de rendu d'un plan incrusté :

1. **Rhubarb Lip Sync** (MIT, binaire x86_64 sous Rosetta 2) en sous-processus sur
   `voice/segment_XX.wav` → `avatar/visemes_seg_XX.json`. `pocketSphinx` + texte du segment pour
   l'anglais, `phonetic` pour les autres langues.
2. **Timeline d'états** (visème, yeux) au pas de 1/30 s sur le temps global de la voix ;
   clignement tiré de la graine du run toutes les 2,5 à 5 s, 4 images.
3. **Pillow ne compose qu'un sprite par état distinct** (≤ 9 × 2), jamais 30 images identiques
   par seconde ; ffmpeg lit la liste des changements (concat) et applique le balancement de
   tête sinusoïdal → **ProRes 4444 avec alpha** (`avatar/shot_XX.mov`).
4. ffmpeg compose ce clip sur celui du style hôte ; `verify_clip` vérifie le résultat.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from factory import video
from factory.core.models import Asset, Channel, Generateur, Shot, Shotlist
from factory.core.paths import RunPaths
from factory.styles.base import MoteurBase

RHUBARB = "outils/rhubarb/rhubarb"
FPS = video.FPS


@dataclass
class Avatar2dEngine(MoteurBase):
    """Incrustation ou présentateur, au-dessus d'un moteur hôte."""

    name: str = "avatar2d"
    backend: str = "ffmpeg"
    hote: object | None = None
    mesures: dict = field(default_factory=dict)
    _timelines: dict[str, list[tuple[float, float, str]]] = field(default_factory=dict)
    _segments: dict[str, dict] = field(default_factory=dict)
    _sprites: dict[tuple[str, bool], Path] = field(default_factory=dict)
    _clignements: list[tuple[float, float]] = field(default_factory=list)

    # -- paramètres ----------------------------------------------------------------------

    @property
    def mode(self) -> str:
        return str(self.param("mode", "overlay"))

    @property
    def roles(self) -> set[str]:
        return set(self.param("segments", ["hook", "cta"]))

    def _hote(self, channel: Channel):
        if self.hote is None:
            from factory.core import config
            from factory.styles import get_engine

            styles = config.charger(self.racine, strict=False).styles
            hote_id = self.param("host_style") or channel.style
            if hote_id == self.style.id:
                raise ValueError("avatar2d ne peut pas être son propre style hôte")
            self.hote = get_engine(styles[hote_id], racine=self.racine, journal=self.journal)
            self.hote.texte_divulgation = self.texte_divulgation
        return self.hote

    def personnage(self, channel: Channel) -> Path:
        """Dossier du personnage de la chaîne : `params.character`, sinon le premier déclaré."""
        racine = self.racine / "workspace" / "library" / "characters"
        voulu = self.param("character")
        for fiche in sorted(racine.glob("*/character.yaml")):
            conf = yaml.safe_load(fiche.read_text(encoding="utf-8")) or {}
            if (voulu and conf.get("id") == voulu) or (not voulu and conf.get("channel") == channel.id):
                if not (fiche.parent / "mouths" / "X.png").exists():
                    raise FileNotFoundError(f"{fiche.parent.name} : calques absents (factory character build)")
                return fiche.parent
        raise FileNotFoundError(f"aucun personnage pour {channel.id} dans workspace/library/characters/")

    def _plans(self, shotlist: Shotlist) -> list[Shot]:
        """Plans des segments où le personnage apparaît."""
        return [s for s in shotlist.shots if s.segment_id in self._segments]

    # -- contrat -------------------------------------------------------------------------

    def prepare_assets(self, shotlist: Shotlist, channel: Channel, run: RunPaths) -> list[Asset]:
        hote = self._hote(channel)
        assets = hote.prepare_assets(shotlist, channel, run)
        self.mesures = dict(getattr(hote, "mesures", {}) or {})

        timings = json.loads((run.voice_dir / "timings.json").read_text(encoding="utf-8"))
        script = json.loads(run.script.read_text(encoding="utf-8"))
        roles = {s["id"]: s["role"] for s in script["segments"]}
        self._segments = {s["id"]: s for s in timings["segments"] if roles.get(s["id"]) in self.roles}
        dossier = run.racine / "avatar"
        dossier.mkdir(exist_ok=True)

        # Un plan incrusté dont le clip hôte existe déjà est rendu à nouveau : sans marqueur
        # d'incrustation, le rendu le prendrait pour conforme et le garderait tel quel.
        for shot in self._plans(shotlist):
            marque = dossier / f"{shot.id}.done"
            if not marque.exists():
                run.clip(shot.id).unlink(missing_ok=True)

        depart = time.perf_counter()
        for seg_id, seg in self._segments.items():
            self._timelines[seg_id] = self._rhubarb(run, seg, channel.lang, dossier)
        self.mesures["avatar_rhubarb_s"] = round(time.perf_counter() - depart, 2)
        self.mesures["avatar_segments"] = sorted(self._segments)
        self.mesures["avatar_shots"] = [s.id for s in self._plans(shotlist)]
        self.mesures.setdefault("avatar_compose_s", 0.0)
        self.mesures.setdefault("avatar_overlay_s", 0.0)
        self.mesures.setdefault("avatar_host_render_s", 0.0)
        self._clignements = self._tirer_clignements(run.video_id, float(timings["total_duration_s"]))
        (dossier / "timeline.json").write_text(json.dumps(
            {"segments": {k: [list(e) for e in v] for k, v in self._timelines.items()},
             "blinks": self._clignements, "mode": self.mode}, indent=1), encoding="utf-8")

        perso = self.personnage(channel)
        conf = yaml.safe_load((perso / "character.yaml").read_text(encoding="utf-8"))
        assets.append(Asset(
            asset_id=self.identifiant_asset(perso / "base.png"), path=str((perso / "base.png").relative_to(self.racine)),
            provider="flux", source_url=None, author="BMS (généré)", licence="Apache-2.0",
            licence_url=conf.get("licence_url", "https://www.apache.org/licenses/LICENSE-2.0"),
            attribution_line=None, downloaded_at=self.maintenant(), person_release=None,
            generator=Generateur(
                model=conf.get("model", "mlx-community/FLUX.2-Klein-4B-4bit"),
                prompt_hash=hashlib.sha256(" ".join(str(conf["description"]).split()).encode()).hexdigest(),
                seed=int(conf["seed"]), steps=4, resolution=conf.get("resolution", "1024x1024")),
            realistic=False, has_text=False, c2pa_present=False,
        ))
        self._inscrire_emploi(assets[-1], run.video_id, channel.id)
        return assets

    def _inscrire_emploi(self, asset: Asset, video_id: str, channel_id: str) -> None:
        """Emploi du personnage dans `library_uses` : il compte dans le réemploi de la chaîne."""
        from factory.core import db

        conn = db.ouvrir(self.racine / "workspace" / "factory.db")
        try:
            conn.execute("INSERT INTO library_uses (asset_id, video_id, channel_id, used_at)"
                         " VALUES (?,?,?,?) ON CONFLICT(asset_id, video_id) DO NOTHING",
                         (asset.asset_id, video_id, channel_id, self.maintenant()))
            conn.execute("UPDATE library_assets SET uses = (SELECT count(*) FROM library_uses"
                         " WHERE asset_id = ?), last_used_at = ? WHERE asset_id = ?",
                         (asset.asset_id, self.maintenant(), asset.asset_id))
        finally:
            conn.close()

    def render_shot(self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths) -> Path:
        hote = self._hote(channel)
        seg = self._segments.get(shot.segment_id)
        if seg is None:
            return hote.render_shot(shot, assets, channel, run)

        depart = time.perf_counter()
        sortie = run.clip(shot.id)
        if self.mode == "presenter":
            fond = run.racine / "avatar" / f"{shot.id}_fond.mp4"
            self.encoder(["-f", "lavfi", "-i",
                          f"color=c={channel.charte.palette.bg}:s={video.LARGEUR}x{video.HAUTEUR}:r={FPS}",
                          *video.arguments_encodage(fond, shot.duration_s)])
            hote_clip = fond
        else:
            hote_clip = hote.render_shot(shot, assets, channel, run)
        self.mesures["avatar_host_render_s"] += time.perf_counter() - depart

        gabarit = self.gabarit(channel, run)
        echelle = 0.85 if self.mode == "presenter" else gabarit.avatar_scale
        hauteur = int(video.HAUTEUR * echelle) // 2 * 2
        t0 = time.perf_counter()
        mov = self._clip_alpha(shot, seg, run, channel, hauteur)
        self.mesures["avatar_compose_s"] += time.perf_counter() - t0

        t1 = time.perf_counter()
        ancre = "bottom_center" if self.mode == "presenter" else gabarit.avatar_anchor
        marge = 24
        x = {"left": str(marge), "right": f"W-w-{marge}", "center": "(W-w)/2"}[ancre.split("_")[1]]
        y = f"{marge}" if ancre.startswith("top") else "H-h"
        # respiration : ±2 px vertical, période 4 s ; le bas du buste reste hors cadre
        bob = f"{y}+2*sin(2*PI*t/4)+2" if not ancre.startswith("top") else f"{y}+2*sin(2*PI*t/4)"
        temporaire = sortie.with_name(f"{shot.id}.avatar.mp4")
        self.encoder(["-i", str(hote_clip), "-i", str(mov), "-filter_complex",
                      f"[0:v][1:v]overlay=x={x}:y={bob}:eval=frame:shortest=1:format=auto",
                      *video.arguments_encodage(temporaire, shot.duration_s)])
        temporaire.replace(sortie)
        (run.racine / "avatar" / f"{shot.id}.done").write_text(self.maintenant() + "\n")
        self.mesures["avatar_overlay_s"] += time.perf_counter() - t1
        for cle in ("avatar_compose_s", "avatar_overlay_s", "avatar_host_render_s"):
            self.mesures[cle] = round(self.mesures[cle], 2)
        return sortie

    # -- Rhubarb -------------------------------------------------------------------------

    def _rhubarb(self, run: RunPaths, seg: dict, lang: str, dossier: Path) -> list[tuple[float, float, str]]:
        """Visèmes du segment en temps **global** : (début, fin, forme)."""
        cible = dossier / f"visemes_{seg['id']}.json"
        wav = run.racine / seg["file"]
        if not cible.exists():
            commande = [str(self.racine / RHUBARB), "-f", "json", "--extendedShapes", "GHX",
                        "-o", str(cible)]
            if lang == "en":
                texte = dossier / f"{seg['id']}.txt"
                texte.write_text(seg.get("text", ""), encoding="utf-8")
                commande += ["-r", "pocketSphinx", "-d", str(texte)]
            else:
                commande += ["-r", "phonetic"]
            resultat = subprocess.run(commande + [str(wav)], capture_output=True, text=True,
                                      timeout=600)
            self.tracer(f"rhubarb {seg['id']} : code {resultat.returncode} "
                        f"{resultat.stderr.strip()[-200:]}")
            if resultat.returncode != 0 or not cible.exists():
                raise RuntimeError(f"rhubarb {seg['id']} en code {resultat.returncode}")
        donnees = json.loads(cible.read_text(encoding="utf-8"))
        debut = float(seg["start_s"])
        return [(round(debut + c["start"], 3), round(debut + c["end"], 3), c["value"])
                for c in donnees["mouthCues"]]

    def visemes_a(self, seg_id: str, t: float) -> str:
        for a, b, forme in self._timelines.get(seg_id, []):
            if a <= t < b:
                return forme
        return "X"

    # -- clignements, sprites, clip alpha ------------------------------------------------

    @staticmethod
    def _tirer_clignements(video_id: str, duree: float) -> list[tuple[float, float]]:
        graine = int(hashlib.sha256(video_id.encode()).hexdigest()[:8], 16)
        hasard = random.Random(graine)
        t, sortie = hasard.uniform(1.0, 3.0), []
        while t < duree:
            sortie.append((round(t, 3), round(t + 4 / FPS, 3)))
            t += hasard.uniform(2.5, 5.0)
        return sortie

    def _yeux_fermes(self, t: float) -> bool:
        return any(a <= t < b for a, b in self._clignements)

    def _sprite(self, perso: Path, forme: str, fermes: bool, hauteur: int, dossier: Path) -> Path:
        cle = (forme, fermes)
        if cle in self._sprites:
            return self._sprites[cle]
        base = Image.open(perso / "base.png").convert("RGBA")
        boite = base.getchannel("A").getbbox()
        image = base.copy()
        image.alpha_composite(Image.open(perso / ("eyes_closed.png" if fermes else "eyes_open.png")).convert("RGBA"))
        bouche = Image.open(perso / "mouths" / f"{forme}.png").convert("RGBA")
        # la bouche ne déborde jamais du détourage (fond gris sous le patch)
        alpha = Image.fromarray(np.minimum(np.asarray(bouche.getchannel("A")),
                                           np.asarray(base.getchannel("A"))))
        bouche.putalpha(alpha)
        image.alpha_composite(bouche)
        image = image.crop(boite)
        largeur = round(image.width * hauteur / image.height) // 2 * 2
        image = image.resize((largeur, hauteur), Image.Resampling.LANCZOS)
        chemin = dossier / f"sprite_{hauteur}_{forme}_{'f' if fermes else 'o'}.png"
        image.save(chemin)
        self._sprites[cle] = chemin
        return chemin

    def _clip_alpha(self, shot: Shot, seg: dict, run: RunPaths, channel: Channel, hauteur: int) -> Path:
        """ProRes 4444 alpha du personnage sur la fenêtre du plan ; sprites aux changements seuls."""
        dossier = run.racine / "avatar"
        perso = self.personnage(channel)
        n = max(1, round(shot.duration_s * FPS))
        etats: list[tuple[tuple[str, bool], int]] = []
        for i in range(n):
            t = shot.start_s + i / FPS
            etat = (self.visemes_a(seg["id"], t), self._yeux_fermes(t))
            if etats and etats[-1][0] == etat:
                etats[-1] = (etat, etats[-1][1] + 1)
            else:
                etats.append((etat, 1))
        liste = dossier / f"{shot.id}.ffconcat"
        lignes = ["ffconcat version 1.0"]
        for (forme, fermes), images in etats:
            sprite = self._sprite(perso, forme, fermes, hauteur, dossier)
            lignes += [f"file '{sprite.name}'", f"duration {images / FPS:.5f}"]
        lignes.append(f"file '{self._sprite(perso, etats[-1][0][0], etats[-1][0][1], hauteur, dossier).name}'")
        liste.write_text("\n".join(lignes) + "\n", encoding="utf-8")
        (dossier / f"{shot.id}.etats.json").write_text(json.dumps(
            [[f, int(o), k] for (f, o), k in etats]), encoding="utf-8")

        amplitude = float(self.param("sway.amplitude_deg", 0.8)) * 3.14159 / 180
        periode = float(self.param("sway.period_s", 5.5))
        mov = dossier / f"{shot.id}.mov"
        # temps global dans l'expression : le balancement se poursuit d'un plan à l'autre
        self.encoder([
            "-f", "concat", "-safe", "0", "-i", str(liste),
            "-vf", f"fps={FPS},format=rgba,pad=iw+40:ih+20:20:20:color=0x00000000,"
                   f"rotate=a='{amplitude:.5f}*sin(2*PI*(t+{shot.start_s:.3f})/{periode})'"
                   f":c=none:ow=iw:oh=ih",
            "-frames:v", str(n), "-c:v", "prores_ks", "-profile:v", "4444",
            "-pix_fmt", "yuva444p10le", "-an", str(mov),
        ])
        self.mesures["avatar_changements"] = self.mesures.get("avatar_changements", 0) + len(etats)
        self.mesures["avatar_images"] = self.mesures.get("avatar_images", 0) + n
        self.mesures["avatar_sprites"] = len(self._sprites)
        return mov


def rhubarb_disponible(racine: Path) -> bool:
    return (racine / RHUBARB).exists() and shutil.which("arch") is not None
