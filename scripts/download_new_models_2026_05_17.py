"""Download the 4 new candidate models for the 2026-05-17 sweep."""
from huggingface_hub import hf_hub_download
import sys, os, time

OUT = r"D:\repos\ik_llama.cpp\models"
TARGETS = [
    ("bartowski/ibm-granite_granite-4.1-8b-GGUF",          "ibm-granite_granite-4.1-8b-Q4_K_M.gguf"),
    ("bartowski/Qwen_Qwen3.5-4B-GGUF",                     "Qwen_Qwen3.5-4B-Q4_K_M.gguf"),
    ("bartowski/microsoft_Phi-4-mini-instruct-GGUF",       "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf"),
    ("TeichAI/Qwen3-8B-Claude-Sonnet-4.5-Reasoning-Distill-GGUF",
                                                            "qwen3-8b-claude-sonnet-4.5-reasoning-distill.q4_k_m.gguf"),
]

os.makedirs(OUT, exist_ok=True)
for repo, fname in TARGETS:
    print(f"==> {repo} :: {fname}", flush=True)
    t0 = time.time()
    try:
        path = hf_hub_download(
            repo_id=repo, filename=fname, local_dir=OUT, local_dir_use_symlinks=False
        )
        sz = os.path.getsize(path) / (1024**3)
        print(f"OK {sz:.2f} GB in {time.time()-t0:.0f}s -> {path}", flush=True)
    except Exception as e:
        print(f"FAIL {repo}/{fname}: {type(e).__name__}: {e}", flush=True)
print("DONE")
