"""Phase 1 de la preuve vidéo IA : encodeur de texte UMT5-XXL.

Le dépôt diffusers ne publie l'encodeur qu'en float32 (22,72 Go), ce qui ne
tient pas sous le plancher de 8 Go libres. On télécharge donc les fragments
un par un, on les recaste en bfloat16 et on supprime le float32 aussitôt.
L'encodeur sert une seule fois : on enregistre les embeddings puis on purge.
"""
import gc, json, os, resource, shutil, sys, time
from pathlib import Path
import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file, save_file

REPO = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
OUT = Path("benchmarks/videoproof")
ENC = OUT / "text_encoder_bf16"
SHARDS = 5

PROMPT = ("A slow aerial shot over a misty pine forest at sunrise, "
          "golden light between the trees, cinematic, photorealistic")
NEGATIVE = "blurry, distorted, low quality, watermark, text"


def free_gb():
    st = os.statvfs("/")
    return st.f_bavail * st.f_frsize / 1e9


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9


def stage_shards():
    ENC.mkdir(parents=True, exist_ok=True)
    for i in range(1, SHARDS + 1):
        name = f"model-{i:05d}-of-{SHARDS:05d}.safetensors"
        dst = ENC / name
        if dst.exists():
            print(f"[{i}/{SHARDS}] déjà converti", flush=True)
            continue
        t = time.time()
        src = hf_hub_download(REPO, f"text_encoder/{name}")
        dl = time.time() - t
        tens = {k: (v.to(torch.bfloat16) if v.is_floating_point() else v)
                for k, v in load_file(src).items()}
        save_file(tens, str(dst), metadata={"format": "pt"})
        del tens
        gc.collect()
        real = os.path.realpath(src)
        os.remove(real)                      # le blob du cache
        if os.path.islink(src):
            os.remove(src)
        print(f"[{i}/{SHARDS}] dl {dl:.0f}s -> bf16 {dst.stat().st_size/1e9:.2f} Go "
              f"| libre {free_gb():.1f} Go", flush=True)
        if free_gb() < 9.0:
            sys.exit(f"ARRET : plancher disque atteint ({free_gb():.1f} Go)")
    for f in ("config.json", "model.safetensors.index.json"):
        shutil.copy(hf_hub_download(REPO, f"text_encoder/{f}"), ENC / f)


def main():
    print(f"libre au départ : {free_gb():.1f} Go", flush=True)
    stage_shards()
    print(f"encodeur bf16 prêt | libre {free_gb():.1f} Go", flush=True)

    from transformers import AutoTokenizer, UMT5EncoderModel
    tok = AutoTokenizer.from_pretrained(REPO, subfolder="tokenizer")
    t = time.time()
    model = UMT5EncoderModel.from_pretrained(ENC, dtype=torch.bfloat16)
    model.eval()
    print(f"chargé en {time.time()-t:.0f}s | RSS {rss_gb():.1f} Go", flush=True)

    embeds = {}
    for key, text in (("prompt", PROMPT), ("negative", NEGATIVE)):
        batch = tok([text], padding="max_length", max_length=512,
                    truncation=True, return_tensors="pt")
        with torch.no_grad():
            out = model(batch.input_ids, attention_mask=batch.attention_mask)[0]
        n = int(batch.attention_mask.sum())
        embeds[key] = out[:, :n].to(torch.float32)
        print(f"{key}: {tuple(embeds[key].shape)} "
              f"nan={bool(embeds[key].isnan().any())}", flush=True)

    torch.save(embeds, OUT / "embeds.pt")
    print(f"RSS max {rss_gb():.1f} Go", flush=True)
    del model
    gc.collect()
    shutil.rmtree(ENC)
    print(f"encodeur purgé | libre {free_gb():.1f} Go", flush=True)
    (OUT / "encode_ok.json").write_text(json.dumps(
        {"prompt": PROMPT, "negative": NEGATIVE, "rss_gb": round(rss_gb(), 2)}))


if __name__ == "__main__":
    main()
