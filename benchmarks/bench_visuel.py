#!/usr/bin/env python3
"""Banc de mesure des briques visuelles — étape 5.2.

Un sous-processus par brique (`python bench_visuel.py <brique>`), pour qu'un
seul modèle soit résident à la fois. Chaque brique écrit une ligne JSON dans
benchmarks/results_visuel.jsonl et ne renvoie que des valeurs mesurées.
"""
import json, os, re, resource, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmarks" / "samples" / "visuel"
RESULTS = ROOT / "benchmarks" / "results_visuel.jsonl"
VENV = ROOT / ".venv" / "bin" / "python"

IMAGE_MODEL = "mlx-community/FLUX.2-Klein-4B-4bit"   # figé par STATE.md, Apache-2.0
SEED = 42
STEPS = 4                                            # FLUX.2-klein est un modèle turbo

STYLES = {
    "cartoon": "flat cartoon illustration, bold outlines, simple shapes, "
               "limited flat color palette, a woman watering plants on a balcony",
    "documentaire": "detailed documentary illustration, realistic textures, "
                    "natural lighting, an ancient library with tall wooden shelves",
    "photo": "photorealistic photograph of a misty pine forest at sunrise, "
             "golden light between the trees, shallow depth of field",
    "whiteboard": "simple black line drawing on plain white background, "
                  "hand-drawn marker sketch, no shading, no color, a human brain "
                  "connected to three gears",
    "motion": "abstract motion design background, smooth gradient shapes, "
              "geometric waves, deep blue and orange, no text, no characters",
}
RESOLUTIONS = [(1280, 720), (1024, 1024)]
PERSONNAGE = ("flat cartoon illustration of the same character: a bearded man "
              "in his forties wearing a green flannel shirt and round glasses, "
              "neutral background, upper body, bold outlines")


# ---------------------------------------------------------------- utilitaires
def log(msg):
    print(msg, flush=True)


def record(row):
    with RESULTS.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log(json.dumps(row, ensure_ascii=False))


def child_peak_gb():
    """Pic de RSS de tous les sous-processus terminés, en Go."""
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e9


def self_peak_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9


def run(cmd, **kw):
    """Exécute et renvoie (code, secondes, sortie fusionnée)."""
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return p.returncode, time.time() - t, (p.stdout or "") + (p.stderr or "")


def pic_mlx(sortie):
    """mflux annonce lui-même son pic : « Peak MLX memory: 4.83 GB »."""
    m = re.findall(r"Peak MLX memory:\s*([\d.]+)\s*GB", sortie)
    return max((float(x) for x in m), default=None)


def dir_gb(path):
    p = Path(path)
    if not p.exists():
        return 0.0
    out = subprocess.run(["du", "-sk", str(p)], capture_output=True, text=True)
    return int(out.stdout.split()[0]) / 1e6


def ffprobe(path, entries):
    code, _, out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", entries, "-of", "json", str(path)])
    return json.loads(out) if code == 0 else {}


# -------------------------------------------------------------------- images
def brique_image():
    OUT.mkdir(parents=True, exist_ok=True)
    mflux = shutil.which("mflux-generate-flux2") or str(ROOT / ".venv/bin/mflux-generate-flux2")
    for style, prompt in STYLES.items():
        for w, h in RESOLUTIONS:
            dest = OUT / f"img_{style}_{w}x{h}.png"
            if dest.exists():
                continue
            before = child_peak_gb()
            code, secs, out = run([
                mflux, "--model", IMAGE_MODEL, "--prompt", prompt,
                "--width", str(w), "--height", str(h), "--steps", str(STEPS),
                "--seed", str(SEED), "--low-ram", "--vae-tiling",
                "--output", str(dest)])
            record({"brique": "image", "outil": "mflux FLUX.2-klein-4B 4-bit",
                    "style": style, "resolution": f"{w}x{h}",
                    "secondes": round(secs, 1),
                    "pic_mlx_go": pic_mlx(out),
                    "pic_rss_go": round(max(child_peak_gb(), before), 2),
                    "ok": dest.exists(),
                    "erreur": "" if dest.exists() else out.strip()[-400:]})
            if not dest.exists():
                return

    # Cohérence : même personnage, trois graines différentes.
    for i, seed in enumerate((11, 22, 33), start=1):
        dest = OUT / f"coherence_perso_{i}_seed{seed}.png"
        if dest.exists():
            continue
        code, secs, out = run([
            mflux, "--model", IMAGE_MODEL, "--prompt", PERSONNAGE,
            "--width", "1024", "--height", "1024", "--steps", str(STEPS),
            "--seed", str(seed), "--low-ram", "--vae-tiling",
            "--output", str(dest)])
        record({"brique": "image_coherence", "outil": "mflux FLUX.2-klein-4B 4-bit",
                "graine": seed, "secondes": round(secs, 1),
                "pic_mlx_go": pic_mlx(out),
                "pic_rss_go": round(child_peak_gb(), 2), "ok": dest.exists(),
                "erreur": "" if dest.exists() else out.strip()[-400:]})


# ------------------------------------------------------------------- profondeur
def brique_depth():
    import torch
    from PIL import Image
    from transformers import pipeline
    # Les trois styles qui iront en parallaxe : une photo, une illustration
    # détaillée, un cartoon. Le fond abstrait n'a pas de profondeur à extraire.
    voulus = ["img_photo_1280x720.png", "img_documentaire_1280x720.png",
              "img_cartoon_1280x720.png"]
    srcs = [OUT / n for n in voulus if (OUT / n).exists()]
    if not srcs:
        record({"brique": "depth", "ok": False, "erreur": "aucune image source"})
        return
    t = time.time()
    pipe = pipeline("depth-estimation",
                    model="depth-anything/Depth-Anything-V2-Small-hf", device="mps")
    charge = time.time() - t
    for src in srcs:
        t = time.time()
        depth = pipe(Image.open(src))["depth"]
        secs = time.time() - t
        dest = OUT / f"depth_{src.stem}.png"
        depth.save(dest)
        record({"brique": "depth", "outil": "Depth Anything V2 Small (MPS)",
                "image": src.name, "chargement_s": round(charge, 1),
                "secondes": round(secs, 2), "pic_go": round(self_peak_gb(), 2),
                "ok": dest.exists()})
        charge = 0.0


# -------------------------------------------------------------------- parallaxe
def brique_parallax():
    import numpy as np
    from PIL import Image, ImageFilter
    src = next(iter(sorted(OUT.glob("img_photo_1280x720.png"))), None)
    if src is None:
        src = next(iter(sorted(OUT.glob("img_*_1280x720.png"))), None)
    depth_p = OUT / f"depth_{src.stem}.png"
    if not depth_p.exists():
        record({"brique": "parallax", "ok": False, "erreur": "carte de profondeur absente"})
        return

    t = time.time()
    img = Image.open(src).convert("RGBA").resize((1920, 1080))
    dep = np.asarray(Image.open(depth_p).convert("L").resize((1920, 1080)), dtype=float)
    dep = (dep - dep.min()) / max(dep.max() - dep.min(), 1e-6)
    layers = []
    # Depth Anything sort une profondeur INVERSE : clair = proche. Vérifié sur
    # l'image forêt — végétation du premier plan à 122, ciel lointain à 40.
    #
    # Trois pièges, tous payés une fois :
    #   1. Les rôles étaient inversés — la tranche sombre (72 % des pixels, le
    #      fond) servait d'avant-plan et glissait le plus vite.
    #   2. Des masques binaires mutuellement exclusifs laissent des trous : dès
    #      qu'une couche glisse, on voit à travers. Les masques sont donc
    #      CUMULATIFS — chaque couche contient tout ce qui est plus proche
    #      qu'elle, et le fond est l'image entière, sans masque.
    #   3. Un seuil net crénèle les contours. L'alpha suit une rampe autour du
    #      seuil, puis un flou gaussien lisse ce qu'il reste.
    BANDE = 0.06        # largeur de la rampe de fondu, en unités de profondeur
    FLOU = 3            # rayon du flou de bord, en pixels
    for i, seuil in enumerate((0.0, 0.34, 0.67)):
        rgba = np.asarray(img).copy()
        if i == 0:
            rgba[..., 3] = 255                      # le fond est plein
        else:
            a = np.clip((dep - (seuil - BANDE / 2)) / BANDE, 0.0, 1.0)
            rgba[..., 3] = (a * 255).astype(np.uint8)
        couche = Image.fromarray(rgba)
        if i > 0:
            couche.putalpha(Image.fromarray(rgba[..., 3])
                            .filter(ImageFilter.GaussianBlur(FLOU)))
        p = OUT / f"layer_{i}.png"
        couche.save(p)
        layers.append(p)
    decoupe = time.time() - t

    dest = OUT / "clip_parallaxe_1080p.mp4"
    # layers[0] = fond (le plus loin, glisse le moins), layers[2] = premier plan.
    # Les couches sont agrandies de 20 % pour que le glissement ne découvre
    # jamais le bord : dérive maximale 26 x 5 = 130 px pour 192 px de marge.
    def chaine(canvas):
        return ("[1:v]scale=2304:1296,setsar=1[bg];"
                "[2:v]scale=2304:1296,setsar=1[mid];"
                "[3:v]scale=2304:1296,setsar=1[fg];"
                f"[0:v][bg]overlay=x='-192-2*t':y=-108[a];"
                "[a][mid]overlay=x='-192-10*t':y=-108[b];"
                "[b][fg]overlay=x='-192-26*t':y=-108[c];"
                "[c]fps=30,format=yuv420p[v]")

    def cmd_parallaxe(couleur, duree, sortie, extra):
        return (["ffmpeg", "-y", "-f", "lavfi",
                 "-i", f"color=c={couleur}:s=1920x1080:r=30:d={duree}"]
                + [arg for lay in layers
                   for arg in ("-loop", "1", "-t", str(duree), "-i", str(lay))]
                + ["-filter_complex", chaine(couleur), "-map", "[v]"]
                + extra + [str(sortie)])

    code, secs, out = run(cmd_parallaxe("black", 5, dest,
                                        ["-c:v", "libx264", "-preset", "medium",
                                         "-crf", "20"]))

    # Vérification des trous : on rejoue la dernière image sur un fond magenta,
    # en PNG (sans compression). Tout pixel magenta est un trou.
    temoin = OUT / "parallaxe_controle_trous.png"
    run(cmd_parallaxe("magenta", 5, temoin,
                      ["-ss", "4.9", "-frames:v", "1"]))
    trous = 0
    if temoin.exists():
        a = np.asarray(Image.open(temoin).convert("RGB"))
        trous = int(((a[..., 0] > 240) & (a[..., 1] < 15) & (a[..., 2] > 240)).sum())
        temoin.unlink()

    record({"brique": "parallax", "outil": "Depth Anything + ffmpeg overlay",
            "decoupe_couches_s": round(decoupe, 1), "secondes": round(secs, 1),
            "trous_px_a_4s9": trous, "ok": dest.exists() and trous == 0,
            "erreur": "" if code == 0 else out.strip()[-400:]})

    dest2 = OUT / "clip_kenburns_1080p.mp4"
    # Suréchantillonnage x4 avant zoompan : sans lui le zoom saute d'un pixel.
    # Piège mesuré : avec « -loop 1 -t 5 » en entrée, zoompan produit d images
    # PAR image d'entrée, soit 18 750 au lieu de 150. L'entrée doit être une
    # image unique, sans -loop.
    code, secs, out = run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", "scale=7680:4320,zoompan=z='min(zoom+0.0009,1.35)':d=150:"
               "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
               "format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(dest2)])
    record({"brique": "kenburns", "outil": "ffmpeg zoompan (suréchantillon x4)",
            "secondes": round(secs, 1), "ok": dest2.exists(),
            "erreur": "" if code == 0 else out.strip()[-400:]})


# ----------------------------------------------------------------- composition
def brique_revideo():
    proj = ROOT / "benchmarks" / "revideo_test"
    dest = proj / "output" / "out.mp4"
    env = dict(os.environ, DISABLE_TELEMETRY="true",
               PUPPETEER_CACHE_DIR=str(ROOT / "models" / "puppeteer"))
    code, secs, out = run(["node", "render.mjs"], cwd=proj, env=env)
    info = ffprobe(dest, "stream=nb_frames,width,height") if dest.exists() else {}
    frames = 0
    try:
        frames = int(info["streams"][0]["nb_frames"])
    except Exception:
        pass
    record({"brique": "composition", "outil": "Revideo (rendu headless)",
            "secondes": round(secs, 1), "frames": frames,
            "fps_rendu": round(frames / secs, 2) if secs and frames else None,
            "node_modules_go": round(dir_gb(proj / "node_modules"), 2),
            "chromium_go": round(dir_gb(ROOT / "models" / "puppeteer"), 2),
            "ok": dest.exists(), "erreur": "" if code == 0 else out.strip()[-600:]})


# ------------------------------------------------------------------ whiteboard
def brique_whiteboard():
    src = OUT / "img_whiteboard_1280x720.png"
    if not src.exists():
        record({"brique": "whiteboard", "ok": False, "erreur": "image trait absente"})
        return
    import vtracer
    dest = OUT / "whiteboard.svg"
    t = time.time()
    vtracer.convert_image_to_svg_py(str(src), str(dest), colormode="binary",
                                    mode="spline", filter_speckle=4)
    secs = time.time() - t
    chemins = dest.read_text().count("<path") if dest.exists() else 0
    record({"brique": "whiteboard_vectorisation", "outil": "vtracer",
            "secondes": round(secs, 2), "chemins": chemins,
            "svg_ko": round(dest.stat().st_size / 1e3, 1) if dest.exists() else 0,
            "ok": dest.exists()})
    if not dest.exists():
        return

    # Animation du tracé : stroke-dashoffset, capturée image par image.
    page = ROOT / "benchmarks" / "whiteboard.html"
    svg = dest.read_text().split("?>", 1)[-1]
    page.write_text(f"""<!doctype html><meta charset="utf-8">
<style>html,body{{margin:0;background:#fff;width:1280px;height:720px;overflow:hidden}}
svg{{width:1280px;height:720px}}
path{{fill:none;stroke:#111;stroke-width:2;
stroke-dasharray:var(--l);stroke-dashoffset:calc(var(--l) * (1 - var(--p)))}}</style>
{svg}
<script>
const ps=[...document.querySelectorAll('path')];
ps.forEach(p=>p.style.setProperty('--l', p.getTotalLength()||1));
window.setProgress=(t)=>{{const n=ps.length;ps.forEach((p,i)=>{{
  const a=i/n,b=(i+1)/n;p.style.setProperty('--p',Math.max(0,Math.min(1,(t-a)/(b-a))));}});}};
window.setProgress(0);
</script>""")
    frames_dir = ROOT / "benchmarks" / "wb_frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir()
    t = time.time()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(page.as_uri())
        for i in range(150):                      # 5 s a 30 ips
            pg.evaluate(f"window.setProgress({i / 149:.4f})")
            pg.screenshot(path=str(frames_dir / f"f{i:04d}.png"))
        b.close()
    capture = time.time() - t
    clip = OUT / "clip_whiteboard_720p.mp4"
    code, enc, out = run(["ffmpeg", "-y", "-framerate", "30", "-i",
                          str(frames_dir / "f%04d.png"), "-c:v", "libx264",
                          "-pix_fmt", "yuv420p", "-crf", "20", str(clip)])
    shutil.rmtree(frames_dir, ignore_errors=True)
    record({"brique": "whiteboard_animation", "outil": "Playwright + ffmpeg",
            "capture_s": round(capture, 1), "encodage_s": round(enc, 1),
            "secondes": round(capture + enc, 1), "ok": clip.exists(),
            "erreur": "" if code == 0 else out.strip()[-300:]})


# --------------------------------------------------------------------- lipsync
def brique_lipsync():
    wav = next(iter(sorted((ROOT / "benchmarks" / "samples" / "audio").glob("*fr*.wav"))), None)
    rhubarb = ROOT / "outils" / "rhubarb" / "rhubarb"
    if wav is None or not rhubarb.exists():
        record({"brique": "lipsync", "ok": False,
                "erreur": f"wav={wav} rhubarb={rhubarb.exists()}"})
        return
    mono = ROOT / "benchmarks" / "samples" / "visuel" / "lipsync_src.wav"
    run(["ffmpeg", "-y", "-i", str(wav), "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(mono)])
    duree = float(ffprobe(mono, "format=duration").get("format", {}).get("duration", 0) or 0)
    if not duree:
        code, _, out = run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", str(mono)])
        duree = float(out.strip() or 0)
    for mode in ("phonetic", "pocketSphinx"):
        dest = OUT / f"visemes_{mode}.json"
        code, secs, out = run([str(rhubarb), "-f", "json", "-r", mode,
                               "--extendedShapes", "GHX", "-o", str(dest), str(mono)])
        n = 0
        if dest.exists():
            try:
                n = len(json.loads(dest.read_text()).get("mouthCues", []))
            except Exception:
                pass
        record({"brique": "lipsync", "outil": f"Rhubarb -r {mode}",
                "audio_s": round(duree, 1), "secondes": round(secs, 1),
                "visemes": n, "ok": code == 0 and n > 0,
                "erreur": "" if code == 0 else out.strip()[-300:]})


# ------------------------------------------------------------------- miniature
def brique_miniature():
    fond = OUT / "img_photo_1280x720.png"
    if not fond.exists():
        fond = next(iter(sorted(OUT.glob("img_*_1280x720.png"))), None)
    page = ROOT / "benchmarks" / "miniature.html"
    page.write_text(f"""<!doctype html><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:720px;position:relative;overflow:hidden;
 font-family:'Helvetica Neue',Arial,sans-serif}}
.bg{{position:absolute;inset:0;background:url('{fond.as_uri()}') center/cover;
 filter:brightness(.55) saturate(1.2)}}
.titre{{position:absolute;inset:0;display:flex;flex-direction:column;
 justify-content:center;align-items:center;gap:6px;text-align:center}}
.titre span{{font-size:150px;font-weight:900;color:#fff;letter-spacing:-4px;
 text-shadow:0 8px 28px rgba(0,0,0,.85);line-height:.95}}
.titre span.accent{{color:#ffcc00}}
.bandeau{{position:absolute;left:0;right:0;bottom:0;height:96px;
 background:#d40000;display:flex;align-items:center;padding:0 48px}}
.bandeau b{{color:#fff;font-size:44px;letter-spacing:2px;text-transform:uppercase}}
</style>
<div class="bg"></div>
<div class="titre"><span>LA FORÊT</span><span class="accent">QUI RESPIRE</span></div>
<div class="bandeau"><b>Épisode 1 · Documentaire</b></div>""")
    dest = OUT / "miniature_1280x720.png"
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        lancement = time.time() - t0
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        t = time.time()
        pg.goto(page.as_uri())
        pg.wait_for_function("document.fonts.ready")
        pg.screenshot(path=str(dest))
        rendu = time.time() - t
        b.close()
    record({"brique": "miniature", "outil": "Playwright HTML->PNG",
            "lancement_s": round(lancement, 2), "secondes": round(rendu, 2),
            "png_ko": round(dest.stat().st_size / 1e3, 1) if dest.exists() else 0,
            "ok": dest.exists()})


BRIQUES = {"image": brique_image, "depth": brique_depth, "parallax": brique_parallax,
           "revideo": brique_revideo, "whiteboard": brique_whiteboard,
           "lipsync": brique_lipsync, "miniature": brique_miniature}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in BRIQUES:
        sys.exit(f"usage: bench_visuel.py [{'|'.join(BRIQUES)}]")
    BRIQUES[sys.argv[1]]()
