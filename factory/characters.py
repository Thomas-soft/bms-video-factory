"""Personnages récurrents : base générée, détourage, calques de bouche et d'yeux (étape 29).

`workspace/library/characters/<id>/character.yaml` fige la description **mot pour mot**, tenue
comprise : le visage tient d'une graine à l'autre, la tenue non (étape 5.2). La construction :

1. **Base** : une image par graine candidate (mflux FLUX.2 klein, Apache-2.0), repères du visage
   par Apple Vision (`outils/vision/reperes_visage`, système) ; la première graine dont le visage,
   les lèvres et les deux yeux sont détectés est retenue.
2. **Détourage** : rembg + `birefnet-general-lite` (MIT) dans un sous-processus qui se termine.
3. **Calques** : trois essais d'édition par référence (`mflux-generate-flux2-edit`, même
   description, même graine, seule la bouche ou les yeux changent). Chaque essai est **recalé sur
   les yeux de la base** puis mesuré : SSIM hors de la zone modifiée, décalage des yeux. Si les
   trois essais passent, les 9 bouches et les yeux fermés viennent de l'édition, découpés en
   patch à bord adouci ; sinon, ils sont **dessinés** par Pillow sur les repères de la base.

Chaque calque est une image RGBA de la taille de la base, transparente hors de sa zone : le
compositing se réduit à trois `alpha_composite` (base, yeux, bouche).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter

from factory.core.paths import racine_projet

VISEMES = ("A", "B", "C", "D", "E", "F", "G", "H", "X")
#: Consigne d'édition par visème — formes de la documentation de Rhubarb Lip Sync.
CONSIGNES = {
    "A": "lips pressed firmly together, mouth closed, as when saying 'm' or 'b'",
    "B": "mouth slightly open with clenched teeth visible, as when saying 'ee' or 's'",
    "C": "mouth open showing upper teeth, as when saying 'eh'",
    "D": "mouth wide open with jaw dropped, as when saying 'ah'",
    "E": "mouth slightly open and slightly rounded, as when saying 'er'",
    "F": "lips puckered and pushed forward into a small round opening, as when saying 'oo'",
    "G": "upper teeth resting on the lower lip, as when saying 'f' or 'v'",
    "H": "mouth open with the tongue tip raised behind the upper teeth, as when saying 'l'",
    "eyes_closed": "both eyes fully closed, relaxed eyelids, mouth unchanged",
}
ESSAIS = ("D", "F", "eyes_closed")
SEUIL_SSIM = 0.90
#: Écart moyen minimal (niveaux de gris, 0-255) dans la zone éditée pour qu'un visème se voie.
SEUIL_ECART = 6.0
MODELE = "mlx-community/FLUX.2-Klein-4B-4bit"
REMBG_MODELE = "birefnet-general-lite"
LICENCE = "Apache-2.0 (poids FLUX.2 klein 4B) ; calques dérivés : BMS"
LICENCE_URL = "https://www.apache.org/licenses/LICENSE-2.0"


def dossier(personnage: str, racine: Path | None = None) -> Path:
    return (racine or racine_projet()) / "workspace" / "library" / "characters" / personnage


def environnement(racine: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update({"HF_HOME": str(racine / "models/hf"), "MFLUX_CACHE_DIR": str(racine / "models/mflux"),
                "U2NET_HOME": str(racine / "models/rembg")})
    return env


def binaire(nom: str) -> str:
    return str(Path.home() / ".local" / "bin" / nom)


# --------------------------------------------------------------------------------------
# Repères
# --------------------------------------------------------------------------------------


@dataclass
class Reperes:
    levres: np.ndarray
    oeil_g: np.ndarray
    oeil_d: np.ndarray
    boite: list[float]

    @classmethod
    def mesurer(cls, image: Path, racine: Path) -> Reperes | None:
        binaire_vision = racine / "outils/vision/reperes_visage"
        if not binaire_vision.exists():  # compilé à la demande, non versionné
            subprocess.run(["swiftc", "-O", str(binaire_vision.with_suffix(".swift")), "-o",
                            str(binaire_vision)], check=True, capture_output=True)
        sortie = subprocess.run([str(binaire_vision), str(image)],
                                capture_output=True, text=True, timeout=60)
        try:
            d = json.loads(sortie.stdout)
        except ValueError:
            return None
        if not d.get("visages") or not d.get("levres") or not d.get("oeil_g") or not d.get("oeil_d"):
            return None
        return cls(np.array(d["levres"]), np.array(d["oeil_g"]), np.array(d["oeil_d"]), d["boite"])

    @property
    def yeux(self) -> np.ndarray:
        return np.array([self.oeil_g.mean(0), self.oeil_d.mean(0)])

    def zone_bouche(self, marge: float = 0.45) -> tuple[int, int, int, int]:
        x0, y0 = self.levres.min(0)
        x1, y1 = self.levres.max(0)
        l, h = x1 - x0, y1 - y0
        # la mâchoire descend sur D : la zone s'étend surtout vers le bas
        return (int(x0 - l * marge), int(y0 - h * 0.8), int(x1 + l * marge), int(y1 + h * 2.2))

    def zone_yeux(self) -> tuple[int, int, int, int]:
        pts = np.vstack([self.oeil_g, self.oeil_d])
        x0, y0 = pts.min(0)
        x1, y1 = pts.max(0)
        h = max(y1 - y0, 8)
        return (int(x0 - h * 1.2), int(y0 - h * 1.4), int(x1 + h * 1.2), int(y1 + h * 1.2))

    def en_dict(self) -> dict[str, Any]:
        return {"levres": self.levres.round(1).tolist(), "oeil_g": self.oeil_g.round(1).tolist(),
                "oeil_d": self.oeil_d.round(1).tolist(), "boite": [round(v, 1) for v in self.boite],
                "zone_bouche": list(self.zone_bouche()), "zone_yeux": list(self.zone_yeux())}


# --------------------------------------------------------------------------------------
# Génération, édition, détourage
# --------------------------------------------------------------------------------------


def generer(prompt: str, graine: int, sortie: Path, taille: str, racine: Path,
            reference: Path | None = None) -> float:
    l, h = taille.lower().split("x")
    if reference is None:
        commande = [binaire("mflux-generate-flux2"), "--model", MODELE]
    else:
        commande = [binaire("mflux-generate-flux2-edit"), "--model", MODELE,
                    "--image-paths", str(reference), "--guidance", "1.0"]
    commande += ["--prompt", prompt, "--width", l, "--height", h, "--steps", "4",
                 "--seed", str(graine), "--low-ram", "--vae-tiling", "--output", str(sortie)]
    depart = time.perf_counter()
    journal = sortie.with_suffix(".log")
    with journal.open("w") as f:
        code = subprocess.run(commande, stdout=f, stderr=subprocess.STDOUT,
                              env=environnement(racine)).returncode
    if code != 0 or not sortie.exists():
        raise RuntimeError(f"mflux en code {code} — {journal}")
    return time.perf_counter() - depart


def detourer(source: Path, sortie: Path, racine: Path) -> None:
    """rembg dans un sous-processus qui se termine (un seul modèle résident)."""
    code = subprocess.run([sys.executable, "-m", "factory.characters", "detourer", str(source),
                           str(sortie)], env=environnement(racine), capture_output=True, text=True)
    if code.returncode != 0:
        raise RuntimeError(f"rembg : {code.stderr.strip()[-300:]}")


def _detourer_ici(source: Path, sortie: Path) -> None:
    from rembg import new_session, remove

    session = new_session(REMBG_MODELE)
    with Image.open(source) as image:
        remove(image.convert("RGB"), session=session).save(sortie)


# --------------------------------------------------------------------------------------
# Recalage, mesure, découpe
# --------------------------------------------------------------------------------------


def recaler(image: Image.Image, depuis: Reperes, vers: Reperes) -> Image.Image:
    """Similitude (échelle + translation) qui pose les yeux de `depuis` sur ceux de `vers`."""
    a, b = depuis.yeux, vers.yeux
    echelle = np.linalg.norm(b[1] - b[0]) / max(np.linalg.norm(a[1] - a[0]), 1e-6)
    centre_a, centre_b = a.mean(0), b.mean(0)
    # PIL attend l'inverse : pour chaque pixel de sortie, le pixel source
    inv = 1 / echelle
    tx = centre_a[0] - inv * centre_b[0]
    ty = centre_a[1] - inv * centre_b[1]
    return image.transform(image.size, Image.Transform.AFFINE, (inv, 0, tx, 0, inv, ty),
                           resample=Image.Resampling.BICUBIC)


def aligner(edition: Image.Image, r_edit: Reperes | None, base: Image.Image, r_base: Reperes,
            zone: tuple[int, int, int, int]) -> tuple[Image.Image, float, bool]:
    """L'édition telle quelle ou recalée sur les yeux, selon le SSIM hors zone le plus haut.

    Mesuré sur l'essai D : 0,984 sans recalage, 0,914 recalée (1,8 px de décalage seulement,
    le rééchantillonnage bicubique coûte plus qu'il ne rapporte).
    """
    brute = ssim_hors_zone(base, edition, zone)
    if r_edit is None:
        return edition, brute, False
    recalee = recaler(edition, r_edit, r_base)
    s = ssim_hors_zone(base, recalee, zone)
    return (recalee, s, True) if s > brute else (edition, brute, False)


def ssim_hors_zone(a: Image.Image, b: Image.Image, zone: tuple[int, int, int, int]) -> float:
    from skimage.metrics import structural_similarity

    ga = np.asarray(a.convert("L"), dtype=np.float32)
    gb = np.asarray(b.convert("L"), dtype=np.float32)
    _, carte = structural_similarity(ga, gb, data_range=255, full=True)
    masque = np.ones_like(carte, dtype=bool)
    x0, y0, x1, y1 = zone
    masque[max(y0, 0):y1, max(x0, 0):x1] = False
    return float(carte[masque].mean())


def masque_ellipse(taille: tuple[int, int], zone: tuple[int, int, int, int], flou: int = 10) -> Image.Image:
    m = Image.new("L", taille, 0)
    ImageDraw.Draw(m).ellipse(zone, fill=255)
    return m.filter(ImageFilter.GaussianBlur(flou))


def patch(source: Image.Image, zone: tuple[int, int, int, int]) -> Image.Image:
    """Calque RGBA pleine taille : `source` dans l'ellipse de `zone`, transparent ailleurs."""
    calque = source.convert("RGBA").copy()
    calque.putalpha(masque_ellipse(source.size, zone))
    return calque


# --------------------------------------------------------------------------------------
# Repli : bouches et paupières dessinées
# --------------------------------------------------------------------------------------


def _couleur(image: Image.Image, x: float, y: float) -> tuple[int, int, int]:
    px = np.asarray(image.convert("RGB"))[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3]
    return tuple(int(v) for v in px.reshape(-1, 3).mean(0))


def bouche_dessinee(base: Image.Image, r: Reperes, viseme: str) -> Image.Image:
    """Forme de bouche Rhubarb dessinée sur une plaque de peau prélevée sous la lèvre."""
    x0, y0 = r.levres.min(0)
    x1, y1 = r.levres.max(0)
    cx, cy, l = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0
    peau = _couleur(base, cx, y1 + (y1 - y0) * 1.2)
    levre = _couleur(base, cx, y0 + (y1 - y0) * 0.25)
    sombre = tuple(int(c * 0.35) for c in levre)
    zone = r.zone_bouche(0.25)
    calque = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    d.ellipse(zone, fill=peau + (255,))
    ouverture = {"A": 0.0, "B": 0.12, "C": 0.35, "D": 0.6, "E": 0.28, "F": 0.3, "G": 0.1,
                 "H": 0.4, "X": 0.0}[viseme]
    largeur = l * {"E": 0.8, "F": 0.45}.get(viseme, 1.0) / 2
    hauteur = l * ouverture / 2
    if hauteur < 1:
        d.line([(cx - largeur, cy), (cx + largeur, cy)], fill=sombre + (255,),
               width=max(3, int(l * (0.06 if viseme == "A" else 0.04))))
    else:
        d.ellipse((cx - largeur, cy - hauteur, cx + largeur, cy + hauteur), fill=sombre + (255,),
                  outline=levre + (255,), width=max(3, int(l * 0.07)))
        if viseme in ("B", "C", "G"):
            d.rectangle((cx - largeur * 0.7, cy - hauteur, cx + largeur * 0.7, cy - hauteur * 0.3),
                        fill=(245, 245, 240, 255))
        if viseme == "H":
            d.ellipse((cx - largeur * 0.4, cy - hauteur * 0.6, cx + largeur * 0.4, cy + hauteur * 0.2),
                      fill=(200, 90, 100, 255))
    alpha = masque_ellipse(base.size, zone, 6)
    calque.putalpha(Image.fromarray(np.minimum(np.asarray(calque.getchannel("A")),
                                               np.asarray(alpha))))
    return calque


def paupieres_dessinees(base: Image.Image, r: Reperes) -> Image.Image:
    calque = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    for oeil in (r.oeil_g, r.oeil_d):
        x0, y0 = oeil.min(0)
        x1, y1 = oeil.max(0)
        peau = _couleur(base, (x0 + x1) / 2, y0 - (y1 - y0) * 0.9)
        h = y1 - y0
        d.ellipse((x0 - h * 0.4, y0 - h * 0.5, x1 + h * 0.4, y1 + h * 0.5), fill=peau + (255,))
        d.arc((x0, y0 - h * 0.2, x1, y1 + h * 0.6), 10, 170, fill=(40, 30, 30, 255),
              width=max(3, int(h * 0.25)))
    return calque


# --------------------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------------------


def construire(personnage: str, racine: Path | None = None, echo=print) -> dict[str, Any]:
    racine = racine or racine_projet()
    d = dossier(personnage, racine)
    fiche = d / "character.yaml"
    conf = yaml.safe_load(fiche.read_text(encoding="utf-8"))
    description = " ".join(str(conf["description"]).split())
    style = " ".join(str(conf["style"]).split())
    taille = conf.get("resolution", "1024x1024")
    essais_dir = d / "essais"
    essais_dir.mkdir(exist_ok=True)
    secondes: dict[str, float] = {}
    expressivite: dict[str, dict] = {}

    # 1. base
    graine, reperes = None, None
    for g in conf["seeds"]:
        brut = essais_dir / f"base_{g}.png"
        if not brut.exists():
            secondes[f"base_{g}"] = round(generer(f"{description}, {style}", g, brut, taille, racine), 1)
        reperes = Reperes.mesurer(brut, racine)
        echo(f"base graine {g} : visage {'détecté' if reperes else 'absent'}")
        if reperes is not None:
            graine = g
            break
    if graine is None:
        raise RuntimeError("aucune graine ne donne un visage détectable")
    base_brute = Image.open(essais_dir / f"base_{graine}.png").convert("RGB")
    base_brute.save(d / "base_raw.png")
    if not (d / "base.png").exists():
        detourer(d / "base_raw.png", d / "base.png", racine)
    base = Image.open(d / "base.png").convert("RGBA")

    # 2. trois essais d'édition
    def editer(cle: str, relance: bool = False) -> Path:
        sortie = essais_dir / f"edit_{cle}{'_bis' if relance else ''}.png"
        if not sortie.exists():
            appui = "clearly visible, exaggerated cartoon mouth shape: " if relance else ""
            consigne = (f"{description}, {style}. Keep exactly the same person, face, hair, "
                        f"clothes, pose, framing and background; only change: {appui}"
                        f"{CONSIGNES[cle]}")
            secondes[sortie.stem] = round(generer(
                consigne, graine + (1 if relance else 0), sortie, taille, racine,
                reference=d / "base_raw.png"), 1)
        return sortie

    def meilleure_edition(cle: str, zone: tuple[int, int, int, int]) -> Image.Image:
        """L'édition du visème, relancée une fois si elle marque trop peu la zone."""
        retenue, ecart_retenu = None, -1.0
        for relance in (False, True):
            fichier = editer(cle, relance)
            aligne, s_, _ = aligner(Image.open(fichier).convert("RGB"),
                                    Reperes.mesurer(fichier, racine), base_brute, reperes, zone)
            ecart = float(np.abs(np.asarray(base_brute.crop(zone), np.float32)
                                 - np.asarray(aligne.crop(zone), np.float32)).mean())
            expressivite[cle] = {"ecart_zone": round(ecart, 1), "ssim": round(s_, 3),
                                 "relance": relance}
            if s_ >= SEUIL_SSIM and ecart > ecart_retenu:
                retenue, ecart_retenu = aligne, ecart
            if ecart >= SEUIL_ECART and s_ >= SEUIL_SSIM:
                break
        return retenue if retenue is not None else aligne

    mesures = []
    for cle in ESSAIS:
        fichier = editer(cle)
        r_edit = Reperes.mesurer(fichier, racine)
        decalage = float(np.abs(r_edit.yeux - reperes.yeux).max()) if r_edit else -1.0
        zone = reperes.zone_yeux() if cle == "eyes_closed" else reperes.zone_bouche()
        recale, s, recalee = aligner(Image.open(fichier).convert("RGB"), r_edit, base_brute,
                                     reperes, zone)
        # l'édition a-t-elle changé la zone visée ? (sinon elle n'a servi à rien)
        a = np.asarray(base_brute.crop(zone), dtype=np.float32)
        b = np.asarray(recale.crop(zone), dtype=np.float32)
        change = float(np.abs(a - b).mean())
        # La décision porte sur la COHÉRENCE (SSIM hors zone) ; l'expressivité (écart dans la
        # zone) est mesurée à part : un visème trop peu marqué est relancé, pas dessiné.
        ok = s >= SEUIL_SSIM
        mesures.append({"essai": cle, "visage": r_edit is not None, "ssim_hors_zone": round(s, 3),
                        "decalage_yeux_px": round(decalage, 1), "recale": recalee,
                        "ecart_zone": round(change, 1), "expressif": change >= SEUIL_ECART,
                        "ok": ok})
        echo(f"essai {cle} : SSIM hors zone {s:.3f}, décalage yeux {decalage:.1f} px, "
             f"écart dans la zone {change:.1f} → {'OK' if ok else 'insuffisant'}")
    methode = "edition" if all(m["ok"] for m in mesures if m["essai"] != "eyes_closed") else "dessin"
    methode_yeux = "edition" if all(m["ok"] for m in mesures if m["essai"] == "eyes_closed") \
        else "dessin"
    echo(f"décision : bouches par {methode}, yeux fermés par {methode_yeux}")

    # 3. calques
    (d / "mouths").mkdir(exist_ok=True)
    for v in VISEMES:
        if v == "X":
            calque = patch(base_brute, reperes.zone_bouche())
        elif methode == "edition":
            calque = patch(meilleure_edition(v, reperes.zone_bouche()), reperes.zone_bouche())
        else:
            calque = bouche_dessinee(base_brute, reperes, v)
        calque.save(d / "mouths" / f"{v}.png")
    patch(base_brute, reperes.zone_yeux()).save(d / "eyes_open.png")
    if methode_yeux == "edition":
        patch(meilleure_edition("eyes_closed", reperes.zone_yeux()),
              reperes.zone_yeux()).save(d / "eyes_closed.png")
    else:
        paupieres_dessinees(base_brute, reperes).save(d / "eyes_closed.png")
    (d / "reperes.json").write_text(json.dumps(reperes.en_dict(), indent=1), encoding="utf-8")

    conf.update({
        "seed": graine, "model": MODELE, "detourage": f"rembg {REMBG_MODELE} (MIT)",
        "licence": LICENCE, "licence_url": LICENCE_URL,
        "layers": {"base": "base.png", "mouths": {v: f"mouths/{v}.png" for v in VISEMES},
                   "eyes_open": "eyes_open.png", "eyes_closed": "eyes_closed.png",
                   "landmarks": "reperes.json"},
        "derivation": {"methode": methode, "methode_yeux": methode_yeux, "seuil_ssim": SEUIL_SSIM, "essais": mesures,
                       "expressivite": expressivite, "secondes": secondes},
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    fiche.write_text(yaml.safe_dump(conf, allow_unicode=True, sort_keys=False, width=100),
                     encoding="utf-8")
    return conf


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "detourer":
        _detourer_ici(Path(sys.argv[2]), Path(sys.argv[3]))
    elif len(sys.argv) == 3 and sys.argv[1] == "construire":
        construire(sys.argv[2])
    else:
        sys.exit("usage : python -m factory.characters construire <id> | detourer <src> <dst>")
