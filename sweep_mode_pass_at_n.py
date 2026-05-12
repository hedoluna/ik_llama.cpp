#!/usr/bin/env python3
"""sweep_mode_pass_at_n.py — Pass@N statistical bench.

N runs con random seed per stesso config, report avg/min/max + per-run.
Indirizza HIGH concern di review Gemini: N=1+seed=42 = no varianza.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import random
import statistics
import sys, io
import time
from pathlib import Path
import requests

BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
spec = importlib.util.spec_from_file_location("cb", BENCH)
cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)

from sweep_lib_sanity import preflight_scorer
preflight_scorer(cb)


def chat(prompt: str, args, seed: int) -> tuple[str, float]:
    t0 = time.time()
    payload = {
        "model": "passN",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
        "temperature": args.temp,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "seed": seed,
    }
    r = requests.post(cb.LM_STUDIO_URL, json=payload, timeout=600)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def run_once(args, seed: int) -> dict:
    total_pass = 0; total = 0
    t_start = time.time()
    per_task = []
    for task in cb.CODING_TASKS:
        resp, dt = chat(task["prompt"], args, seed)
        fn_code = cb.extract_function(resp, task["function_name"]) or resp
        tr = cb.test_function(fn_code, task)
        passed = tr["passed"]; n = len(task["test_cases"])
        total_pass += passed; total += n
        per_task.append({"task": task["id"], "passed": passed, "of": n, "dt": round(dt, 2)})
    return {"seed": seed, "score": total_pass, "total": total,
            "wall_s": round(time.time() - t_start, 2), "per_task": per_task}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--top_p", type=float, default=0.95)
    ap.add_argument("--top_k", type=int, default=64)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--label", default="passN")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(f"=== Pass@{a.n} (temp={a.temp} top_p={a.top_p} top_k={a.top_k}) ===")
    runs = []
    seeds = [42, 123, 7777, 2026, 31415][:a.n]
    for s in seeds:
        r = run_once(a, s)
        runs.append(r)
        print(f"  seed={s:5d}  {r['score']}/{r['total']}  wall={r['wall_s']}s")
    scores = [r["score"] for r in runs]
    walls = [r["wall_s"] for r in runs]
    print(f"\n  avg score: {statistics.mean(scores):.2f}  min={min(scores)}  max={max(scores)}  "
          f"stdev={statistics.stdev(scores):.2f}" if len(scores) > 1 else
          f"\n  score: {scores[0]}")
    print(f"  avg wall:  {statistics.mean(walls):.2f}s  range=[{min(walls)},{max(walls)}]")
    # task-level variance
    print("\n  per-task pass variance:")
    by_task: dict[str, list[int]] = {}
    for r in runs:
        for t in r["per_task"]:
            by_task.setdefault(t["task"], []).append(t["passed"])
    for tname, passes in by_task.items():
        if len(set(passes)) > 1:
            print(f"    {tname}: {passes}  <-- UNSTABLE")
        else:
            pass  # silent if stable
    Path(f"sweep_mode_pass_at_n_{a.label}.json").write_text(
        json.dumps({"args": vars(a), "runs": runs}, indent=2, ensure_ascii=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()
