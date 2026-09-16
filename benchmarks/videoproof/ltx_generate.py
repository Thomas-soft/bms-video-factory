"""Preuve vidéo IA, phase 2 : génération LTX-Video 2B, 512x288, ~4 s.

Transformer en GGUF Q6_K (1,72 Go), VAE du dépôt officiel (1,68 Go), encodeur
de texte absent : on réinjecte les embeddings calculés en phase 1. Objectif de
la mesure : le temps et le pic mémoire, pas la beauté du plan.
"""
import gc, json, os, resource, threading, time
from pathlib import Path
import torch

OUT = Path("benchmarks/videoproof")
BASE = "Lightricks/LTX-Video"
GGUF_REPO = "city96/LTX-Video-gguf"
GGUF_FILE = "ltx-video-2b-v0.9-Q6_K.gguf"
W, H, FRAMES, FPS, STEPS = 512, 288, 97, 24, 25   # 97 frames a 24 ips = 4,04 s

peak = {"rss": 0.0, "mps": 0.0, "swap": 0.0}
stop = threading.Event()


def swap_gb():
    out = os.popen("sysctl -n vm.swapusage").read()
    for tok in out.split():
        if tok.endswith("M") and "used" in out.split(tok)[0][-8:]:
            pass
    try:
        used = out.split("used =")[1].split()[0]
        return float(used.rstrip("M")) / 1024 if used.endswith("M") else 0.0
    except Exception:
        return 0.0


def sampler():
    while not stop.is_set():
        peak["rss"] = max(peak["rss"],
                          resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9)
        try:
            peak["mps"] = max(peak["mps"], torch.mps.driver_allocated_memory() / 1e9)
        except Exception:
            pass
        peak["swap"] = max(peak["swap"], swap_gb())
        stop.wait(5)


def main():
    from diffusers import LTXPipeline, AutoencoderKLLTXVideo, LTXVideoTransformer3DModel
    from diffusers import GGUFQuantizationConfig, FlowMatchEulerDiscreteScheduler
    from diffusers.utils import export_to_video

    emb = torch.load(OUT / "ltx_embeds.pt")
    t0 = time.time()
    tr = LTXVideoTransformer3DModel.from_single_file(
        f"https://huggingface.co/{GGUF_REPO}/blob/main/{GGUF_FILE}",
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16)
    vae = AutoencoderKLLTXVideo.from_pretrained(BASE, subfolder="vae",
                                                torch_dtype=torch.bfloat16)
    sched = FlowMatchEulerDiscreteScheduler.from_pretrained(BASE, subfolder="scheduler")
    pipe = LTXPipeline(vae=vae, transformer=tr, scheduler=sched,
                       text_encoder=None, tokenizer=None)
    pipe.to("mps")
    pipe.vae.enable_tiling()
    load_s = time.time() - t0
    print(f"pipeline chargé en {load_s:.0f}s", flush=True)

    threading.Thread(target=sampler, daemon=True).start()
    t = time.time()
    frames = pipe(
        prompt_embeds=emb["prompt"].to("mps", torch.bfloat16),
        prompt_attention_mask=emb["prompt_mask"].to("mps"),
        negative_prompt_embeds=emb["negative"].to("mps", torch.bfloat16),
        negative_prompt_attention_mask=emb["negative_mask"].to("mps"),
        width=W, height=H, num_frames=FRAMES, num_inference_steps=STEPS,
        generator=torch.Generator().manual_seed(42),
    ).frames[0]
    gen_s = time.time() - t
    stop.set()

    mp4 = OUT / "ltx_512x288_4s.mp4"
    export_to_video(frames, str(mp4), fps=FPS)
    res = {"outil": "LTX-Video 2B v0.9 Q6_K", "largeur": W, "hauteur": H,
           "frames": FRAMES, "fps": FPS, "steps": STEPS,
           "chargement_s": round(load_s, 1), "generation_s": round(gen_s, 1),
           "s_par_seconde_video": round(gen_s / (FRAMES / FPS), 1),
           "pic_rss_go": round(peak["rss"], 2), "pic_mps_go": round(peak["mps"], 2),
           "swap_go": round(peak["swap"], 2), "mp4": str(mp4)}
    print(json.dumps(res, ensure_ascii=False), flush=True)
    (OUT / "ltx_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
