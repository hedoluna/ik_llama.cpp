#!/usr/bin/env python3
"""sweep_mode_ttft.py — measure TTFT (time-to-first-token) cold and warm.

Sends 5 streaming chat completions. Each request: measure (a) time to first
streaming chunk, (b) total time. The first sample reflects cold cache; later
samples are warm.
"""
from __future__ import annotations
import json
import time
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
PROMPT = "Scrivi una funzione Python che ritorna i numeri da 1 a 10."


def one_request(label: str) -> dict:
    payload = {
        "model": "ttft",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto."},
            {"role": "user", "content": PROMPT},
        ],
        "max_tokens": 64,
        "temperature": 0.0,
        "seed": 42,
        "stream": True,
    }
    t0 = time.time()
    first_chunk_t = None
    chunks = 0
    with requests.post(URL, json=payload, stream=True, timeout=60) as r:
        for line in r.iter_lines():
            if not line:
                continue
            if first_chunk_t is None and line.startswith(b"data:"):
                first_chunk_t = time.time() - t0
            chunks += 1
    total_t = time.time() - t0
    return {
        "label": label,
        "ttft_s": round(first_chunk_t, 4) if first_chunk_t else None,
        "total_s": round(total_t, 4),
        "chunks": chunks,
    }


def main():
    print("=== TTFT probe (5 samples) ===")
    results = []
    for i in range(5):
        r = one_request(f"sample{i+1}{'_cold' if i == 0 else '_warm'}")
        results.append(r)
        print(f"  {r['label']:14s} ttft={r['ttft_s']}s  total={r['total_s']}s  chunks={r['chunks']}")
    # summary
    warm = [r["ttft_s"] for r in results[1:] if r["ttft_s"] is not None]
    if warm:
        avg = sum(warm) / len(warm)
        print(f"\n  cold: {results[0]['ttft_s']}s")
        print(f"  warm avg ({len(warm)}): {avg:.4f}s")
    from pathlib import Path
    (Path(__file__).parent / "sweep_mode_ttft_result.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
