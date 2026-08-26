"""Robust urllib+Range downloader for Qwen3.8-Flash-Next GGUF shards (huggingface_hub stalled silently).
Resumes from existing .part files. Pattern from memory: Range header, retry loop, per-chunk timeout.
"""
import os, sys, time, urllib.request, urllib.error

REPO = "unsloth/Qwen3.8-Flash-Next-GGUF"
OUT = r"D:\repos\ik_llama.cpp\models\Qwen3.8-Flash-Next-UD-IQ3_XXS\UD-IQ3_XXS"
FILES = [
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf",
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00002-of-00003.gguf",
    "Qwen3.8-Flash-Next-UD-IQ3_XXS-00003-of-00003.gguf",
]
BASE_URL = f"https://huggingface.co/{REPO}/resolve/main/UD-IQ3_XXS/"

MAX_RETRIES = 100
RETRY_DELAY = 5
CHUNK_TIMEOUT = 30
CHUNK_SIZE = 1024 * 1024

os.makedirs(OUT, exist_ok=True)

def get_remote_size(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=CHUNK_TIMEOUT) as r:
        return int(r.headers.get("Content-Length", 0))

def download(fname):
    url = BASE_URL + fname
    final_path = os.path.join(OUT, fname)
    part_path = final_path + ".part"

    if os.path.exists(final_path):
        print(f"SKIP {fname} (already complete)", flush=True)
        return

    total = get_remote_size(url)
    downloaded = os.path.getsize(part_path) if os.path.exists(part_path) else 0
    print(f"==> {fname}: {downloaded}/{total} bytes ({100*downloaded/total:.1f}%)", flush=True)

    if downloaded >= total and total > 0:
        os.rename(part_path, final_path)
        print(f"OK {fname} (already fully downloaded, renamed)", flush=True)
        return

    t_start = time.time()
    bytes_start = downloaded
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url)
            if downloaded > 0:
                req.add_header("Range", f"bytes={downloaded}-")
            with urllib.request.urlopen(req, timeout=CHUNK_TIMEOUT) as r, open(part_path, "ab") as f:
                last_report = time.time()
                while True:
                    chunk = r.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_report > 10:
                        rate = (downloaded - bytes_start) / max(now - t_start, 1) / (1024*1024)
                        pct = 100*downloaded/total if total else 0
                        print(f"  {fname}: {downloaded/(1024**3):.2f}/{total/(1024**3):.2f} GB ({pct:.1f}%) @ {rate:.1f} MB/s", flush=True)
                        last_report = now
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            print(f"  attempt {attempt+1}/{MAX_RETRIES} FAIL at {downloaded} bytes: {type(e).__name__}: {e}", flush=True)
            time.sleep(RETRY_DELAY)
    else:
        print(f"GAVE UP on {fname} after {MAX_RETRIES} retries", flush=True)
        sys.exit(1)

    final_size = os.path.getsize(part_path)
    if total and final_size != total:
        print(f"SIZE MISMATCH {fname}: got {final_size}, expected {total}", flush=True)
        sys.exit(1)
    os.rename(part_path, final_path)
    print(f"OK {fname} complete ({final_size/(1024**3):.2f} GB)", flush=True)

for f in FILES:
    download(f)
print("DONE")
