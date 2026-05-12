#!/usr/bin/env python3
"""sweep_advanced.py — run advanced_benchmark.py on the new 51/51 winners.

Reuses sweep_small_models infrastructure (start/wait/kill).
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import sweep_small_models as ssm

ADV_LEADERBOARD = ssm.REPO / "sweep_advanced_leaderboard.json"
WINNERS = [
    "Qwen2.5-Coder-1.5B-Q4_K_M",
    "granite-3.3-2b-instruct-Q6_K",
    "granite-4.1-3B-Q4_K_S",
    "Qwen2.5-Coder-3B-Q4_0",
]


def parse_advanced(output: str) -> dict:
    """Parse advanced_benchmark.py stdout — Score X/Y + category bars."""
    score_m = re.search(r"Score:\s*(\d+)/(\d+)", output)
    time_m = re.search(r"Tempo:\s*([\d.]+)s", output)
    profile_m = re.search(r"Specializzazioni:\s*(.+)", output)
    cat_lines = re.findall(r"^\s+([\w ]+?):\s*\[[#-]+\]\s*(\d+)/(\d+)", output, re.M)
    return {
        "score": int(score_m.group(1)) if score_m else None,
        "total": int(score_m.group(2)) if score_m else None,
        "time_s": float(time_m.group(1)) if time_m else None,
        "profile": (profile_m.group(1).strip() if profile_m else None),
        "by_category": [{"cat": c.strip(), "passed": int(p), "total": int(t)}
                        for c, p, t in cat_lines],
    }


def run_one_advanced(label: str) -> dict:
    # Find model entry in TIERS
    entry = None
    for tier in ssm.TIERS.values():
        for lab, path, rt, extra in tier:
            if lab == label:
                entry = (lab, path, rt, extra)
                break
        if entry: break
    if not entry:
        return {"label": label, "status": "not_found"}

    lab, path, rt, extra = entry
    ssm.kill_llama_server()
    t0 = time.time()
    proc = ssm.start_server(lab, path, rt, extra)
    if proc is None:
        return {"label": label, "status": "skip_missing"}
    if not ssm.wait_server_ready(ssm.HOST, ssm.PORT, max_wait=180):
        proc.terminate(); ssm.kill_llama_server()
        return {"label": label, "status": "load_failed"}
    load_t = time.time() - t0
    print(f"  ready in {load_t:.1f}s — running advanced bench (17 task) ...")
    t1 = time.time()
    try:
        cp = subprocess.run(
            [ssm.PY_CMD, str(ssm.BENCH_ADV), "--models", label],
            capture_output=True, text=True, timeout=1800,
        )
        out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    except subprocess.TimeoutExpired:
        out = "<<<TIMEOUT 1800s>>>"
    bench_t = time.time() - t1
    parsed = parse_advanced(out)
    (ssm.REPO / f"sweep_adv_{label}.txt").write_text(out, encoding="utf-8", errors="replace")
    ssm.kill_llama_server()
    return {
        "label": label, "status": "ok",
        "load_time": round(load_t, 2),
        "bench_time": round(bench_t, 2),
        **parsed,
    }


def main():
    results = []
    if ADV_LEADERBOARD.exists():
        results = json.loads(ADV_LEADERBOARD.read_text())
    for label in WINNERS:
        print(f"\n=== ADVANCED: {label} ===")
        r = run_one_advanced(label)
        r["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(json.dumps({k: r.get(k) for k in ("label", "score", "total", "time_s",
                                                 "profile", "load_time", "bench_time", "status")}, indent=2))
        results.append(r)
        ADV_LEADERBOARD.write_text(json.dumps(results, indent=2))

    print("\n=== ADVANCED SUMMARY ===")
    for r in results[-len(WINNERS):]:
        print(f"  {r['label']:50s} -> {r.get('score','?')}/{r.get('total','?')}  "
              f"time={r.get('time_s','?')}s  profile={r.get('profile')}")


if __name__ == "__main__":
    main()
