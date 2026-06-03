#!/usr/bin/env python3
"""sweep_mode_temp_override.py — re-run coding bench with custom temperature.

Reuses cb.test_function for proper scoring (expected_set, input_data, etc).
Args: --temp <float> [--top_p <float>] [--top_k <int>] [--presence_penalty <float>]
Sends to whichever server is running on :1234.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys, io
import time
import requests
from pathlib import Path

BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
spec = importlib.util.spec_from_file_location("cb", BENCH)
cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)


def chat(prompt: str, args) -> tuple[str, float]:
    t0 = time.time()
    payload = {
        "model": "temp-override",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
        "temperature": args.temp,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "seed": 42,
    }
    if args.presence_penalty != 0.0:
        payload["presence_penalty"] = args.presence_penalty
    if args.frequency_penalty != 0.0:
        payload["frequency_penalty"] = args.frequency_penalty
    r = requests.post(cb.LM_STUDIO_URL, json=payload, timeout=300)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--top_p", type=float, default=0.95)
    ap.add_argument("--top_k", type=int, default=20)
    ap.add_argument("--presence_penalty", type=float, default=0.0)
    ap.add_argument("--frequency_penalty", type=float, default=0.0)
    ap.add_argument("--label", default="probe")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(f"=== TEMP-OVERRIDE bench (temp={a.temp} top_p={a.top_p} top_k={a.top_k} "
          f"pp={a.presence_penalty} fp={a.frequency_penalty}) ===")
    rows = []
    total_pass = 0
    total = 0
    t_start = time.time()
    for task in cb.CODING_TASKS:
        resp, dt = chat(task["prompt"], a)
        fn_code = cb.extract_function(resp, task["function_name"]) or resp
        tr = cb.test_function(fn_code, task)
        passed = tr["passed"]; n = len(task["test_cases"])
        verdict = "PASS" if passed == n else "FAIL"
        rows.append({"task": task["id"], "verdict": verdict, "passed": passed, "of": n,
                     "dt_s": round(dt, 2)})
        total_pass += passed; total += n
        print(f"  {task['id']:22s} {verdict:4s} {passed}/{n}  ({dt:.2f}s)")
    wall = time.time() - t_start
    print(f"\nTOTAL: {total_pass}/{total} in {wall:.2f}s")
    out_path = Path(f"sweep_mode_temp_override_{a.label}.json")
    out_path.write_text(json.dumps({
        "args": vars(a), "rows": rows, "total_pass": total_pass, "total": total,
        "wall_s": round(wall, 2)
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved -> {out_path}")


if __name__ == "__main__":
    main()
