#!/usr/bin/env python3
"""sweep_mode_latency_p99.py — tail latency distribution.

100 chat turns, 1 prompt fisso, max_tokens=32. Misura latency/turn,
plot p50/p90/p99/max.

Indirizza Gemini gap #2 (latency tail).
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys, io
import time
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
PROMPT = "Rispondi con 'ok'."


def one_request() -> float:
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "lat",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 32,
        "temperature": 0.0,
        "seed": 42,
    }, timeout=60)
    r.raise_for_status()
    return time.time() - t0


def percentile(values: list[float], p: float) -> float:
    if not values: return 0.0
    s = sorted(values)
    k = int(len(s) * p)
    k = max(0, min(k, len(s) - 1))
    return s[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--label", default="lat")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(f"=== LATENCY p99 ({a.n} turns) ===")
    # warmup 3
    for _ in range(3):
        one_request()
    durs = []
    for i in range(a.n):
        durs.append(one_request())
    durs_ms = [d * 1000 for d in durs]
    print(f"  avg:  {statistics.mean(durs_ms):.1f}ms")
    print(f"  p50:  {percentile(durs_ms, 0.50):.1f}ms")
    print(f"  p90:  {percentile(durs_ms, 0.90):.1f}ms")
    print(f"  p99:  {percentile(durs_ms, 0.99):.1f}ms")
    print(f"  max:  {max(durs_ms):.1f}ms")
    print(f"  min:  {min(durs_ms):.1f}ms")
    print(f"  stdev: {statistics.stdev(durs_ms):.1f}ms")
    from pathlib import Path
    Path(f"sweep_mode_latency_p99_{a.label}.json").write_text(
        json.dumps({"n": a.n, "durations_ms": durs_ms,
                    "avg_ms": statistics.mean(durs_ms),
                    "p50_ms": percentile(durs_ms, 0.50),
                    "p90_ms": percentile(durs_ms, 0.90),
                    "p99_ms": percentile(durs_ms, 0.99),
                    "max_ms": max(durs_ms), "min_ms": min(durs_ms)},
                   indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
