"""Preuve vidéo IA, phase 1 : encodeur de texte T5-XXL en GGUF, sur CPU.

L'encodeur de texte de LTX-Video n'est publié qu'en float32 (19,05 Go) : hors
budget. Première tentative par GGUF Q5_K_M (3,39 Go) : transformers déquantifie
en float32 avant de caster, la machine est partie en 15,7 Go de swap. Seconde
tentative : un dépôt déjà en bfloat16 (9,53 Go), chargé tel quel sur CPU.
Processus séparé : l'encodeur sort de la mémoire avant que le transformer
n'y entre.
"""
import gc, os, resource, time
from pathlib import Path
import torch

OUT = Path("benchmarks/videoproof")
ENC_REPO = "city96/t5-v1_1-xxl-encoder-bf16"   # 9,53 Go, deja en bf16
PROMPT = ("A slow aerial shot flying over a misty pine forest at sunrise, "
          "golden light between the trees, birds flying, cinematic, photorealistic")
NEGATIVE = "worst quality, inconsistent motion, blurry, jittery, distorted"


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9


def main():
    from transformers import AutoTokenizer, T5EncoderModel
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained("Lightricks/LTX-Video", subfolder="tokenizer")
    enc = T5EncoderModel.from_pretrained(ENC_REPO, dtype=torch.bfloat16,
                                         low_cpu_mem_usage=True)
    enc.eval()
    print(f"encodeur chargé en {time.time()-t0:.0f}s | RSS {rss():.1f} Go", flush=True)

    out = {}
    for key, text in (("prompt", PROMPT), ("negative", NEGATIVE)):
        b = tok([text], padding="max_length", max_length=128, truncation=True,
                add_special_tokens=True, return_tensors="pt")
        with torch.no_grad():
            e = enc(b.input_ids, attention_mask=b.attention_mask)[0]
        out[key] = e.to(torch.float32)
        out[key + "_mask"] = b.attention_mask
        print(f"{key}: {tuple(e.shape)} nan={bool(e.isnan().any())}", flush=True)

    torch.save(out, OUT / "ltx_embeds.pt")
    del enc
    gc.collect()
    print(f"RSS max {rss():.1f} Go | embeddings écrits", flush=True)


if __name__ == "__main__":
    main()
