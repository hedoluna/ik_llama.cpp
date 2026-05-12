#!/usr/bin/env python3
"""sweep_mode_consistency.py — N runs same prompt, varying seed.

Misura quanti % delle N runs producono lo stesso output (per nested_sum
+ deep_merge — i task ai bordi della certezza). Gemini gap #4.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys, io
import time
from pathlib import Path
import requests

BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
spec = importlib.util.spec_from_file_location("cb", BENCH)
cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)


def chat(prompt: str, temp: float, top_k: int, seed: int) -> tuple[str, float]:
    t0 = time.time()
    r = requests.post(cb.LM_STUDIO_URL, json={
        "model": "cons",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
        "temperature": temp,
        "top_p": 0.95,
        "top_k": top_k,
        "seed": seed,
    }, timeout=600)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--top_k", type=int, default=64)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--task", default="task3_nested_sum")
    ap.add_argument("--label", default="cons")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    target = next(t for t in cb.CODING_TASKS if t["id"] == a.task)
    print(f"=== CONSISTENCY {a.n} runs (task={a.task} temp={a.temp}) ===")
    results = []
    seeds = list(range(1, a.n + 1))
    for s in seeds:
        resp, dt = chat(target["prompt"], a.temp, a.top_k, s)
        code = cb.extract_function(resp, target["function_name"]) or resp
        tr = cb.test_function(code, target)
        passed = tr["passed"] == len(target["test_cases"])
        results.append({"seed": s, "pass": passed,
                        "passed_count": tr["passed"], "of": len(target["test_cases"]),
                        "code_hash": hash(code.strip()) % 100000, "dt": round(dt, 2)})
        flag = "PASS" if passed else "FAIL"
        print(f"  seed={s:3d}  {flag}  {tr['passed']}/{len(target['test_cases'])}  hash={results[-1]['code_hash']}  dt={dt:.2f}s")
    pass_n = sum(1 for r in results if r["pass"])
    unique_hashes = len({r["code_hash"] for r in results})
    print(f"\n  pass rate: {pass_n}/{a.n} = {100*pass_n/a.n:.0f}%")
    print(f"  unique code variants: {unique_hashes}/{a.n} (lower=more stable)")
    Path(f"sweep_mode_consistency_{a.label}.json").write_text(
        json.dumps({"args": vars(a), "results": results,
                    "pass_rate": pass_n / a.n, "unique_variants": unique_hashes},
                   indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
