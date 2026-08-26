"""Download Qwen3.8-Flash-Next UD-IQ3_XXS GGUF (3 shards, ~83GB) for qwen4exp arch smoke test."""
from huggingface_hub import hf_hub_download
import sys, os, time

OUT = r"D:\repos\ik_llama.cpp\models\Qwen3.8-Flash-Next-UD-IQ3_XXS"
REPO = "unsloth/Qwen3.8-Flash-Next-GGUF"
FILES = [
    "UD-IQ3_XXS/Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf",
    "UD-IQ3_XXS/Qwen3.8-Flash-Next-UD-IQ3_XXS-00002-of-00003.gguf",
    "UD-IQ3_XXS/Qwen3.8-Flash-Next-UD-IQ3_XXS-00003-of-00003.gguf",
]

os.makedirs(OUT, exist_ok=True)
for fname in FILES:
    print(f"==> {fname}", flush=True)
    for attempt in range(5):
        t0 = time.time()
        try:
            path = hf_hub_download(
                repo_id=REPO, filename=fname, local_dir=OUT, local_dir_use_symlinks=False
            )
            sz = os.path.getsize(path) / (1024**3)
            print(f"OK {sz:.2f} GB in {time.time()-t0:.0f}s -> {path}", flush=True)
            break
        except Exception as e:
            print(f"attempt {attempt+1} FAIL {fname}: {type(e).__name__}: {e}", flush=True)
            time.sleep(5)
    else:
        print(f"GAVE UP on {fname}", flush=True)
        sys.exit(1)
print("DONE")
