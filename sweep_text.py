#!/usr/bin/env python3
"""sweep_text.py — esegue text_bench.py su 5 modelli, orchestrazione start/wait/kill."""
from __future__ import annotations
import json, re, subprocess, sys, time
from pathlib import Path
import sweep_small_models as ssm
import sweep_ts_ab as tsab  # reuse start_server_custom

LEADERBOARD = ssm.REPO / "sweep_text_leaderboard.json"
BENCH = Path(r"D:\repos\ik_llama.cpp\text_bench.py")

MODELS = tsab.MODELS + [tsab.DAILY_WINNER]


def run_text_bench(label: str) -> dict:
    save_path = ssm.REPO / f"text_bench_{label}.json"
    try:
        cp = subprocess.run(
            [ssm.PY_CMD, str(BENCH), "--label", label, "--save", str(save_path)],
            capture_output=True, text=True, timeout=900,
        )
        out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    (ssm.REPO / f"text_bench_log_{label}.txt").write_text(out, encoding="utf-8")
    if save_path.exists():
        data = json.loads(save_path.read_text())
        data["status"] = "ok"
        return data
    return {"status": "no_save", "stdout_tail": out[-500:]}


def run_one(entry) -> dict:
    label, path, rt, extra = entry
    ssm.kill_llama_server()
    t0 = time.time()
    proc = tsab.start_server_custom(label, path, rt, extra)
    if not proc:
        return {"label": label, "status": "skip_missing"}
    if not ssm.wait_server_ready(ssm.HOST, ssm.PORT, max_wait=240):
        proc.terminate(); ssm.kill_llama_server()
        return {"label": label, "status": "load_failed"}
    load_t = time.time() - t0
    print(f"  loaded in {load_t:.1f}s — running text_bench ...")
    r = run_text_bench(label)
    r["label"] = label
    r["load_time"] = round(load_t, 2)
    ssm.kill_llama_server()
    return r


def main():
    results = []
    if LEADERBOARD.exists():
        results = json.loads(LEADERBOARD.read_text())
    for entry in MODELS:
        print(f"\n=== TEXT: {entry[0]} ===")
        r = run_one(entry)
        r["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        results.append(r)
        LEADERBOARD.write_text(json.dumps(results, indent=2))
        print(f"  -> {r.get('total_score','?')}/{r.get('total_max','?')}  time={r.get('total_time_s','?')}s  status={r.get('status')}")
    print("\n=== TEXT SUMMARY ===")
    for r in results[-len(MODELS):]:
        print(f"  {r['label']:42s} -> {r.get('total_score','?')}/{r.get('total_max','?')}  "
              f"time={r.get('total_time_s','?')}s  status={r.get('status')}")


if __name__ == "__main__":
    main()
