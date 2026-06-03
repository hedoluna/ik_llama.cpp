#!/usr/bin/env python3
"""sweep_mode_kv_pressure.py — KV cache quality degradation @ long-ctx.

Prepend distractor tokens (N=0, 2k, 5k, 10k) prima del coding task.
Misura accuracy drop su nested_sum task (cluster-sensitive).

Indirizza Gemini gap #1 (KV cache pressure).
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

DISTRACTOR_PARA = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                   "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. ")  # ~25 tokens


def build_distractor(target_tokens: int) -> str:
    # rough estimate ~4 chars per token
    n_repeats = max(1, target_tokens * 4 // len(DISTRACTOR_PARA))
    return DISTRACTOR_PARA * n_repeats


def run_task(task: dict, distractor: str) -> dict:
    prefix = f"# Contesto irrilevante (ignora):\n{distractor}\n\n# Task:\n" if distractor else ""
    full_prompt = prefix + task["prompt"]
    t0 = time.time()
    r = requests.post(cb.LM_STUDIO_URL, json={
        "model": "kv",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
            {"role": "user", "content": full_prompt},
        ],
        "max_tokens": 2048, "temperature": 0.1, "seed": 42,
    }, timeout=600)
    dt = time.time() - t0
    text = r.json()["choices"][0]["message"]["content"]
    code = cb.extract_function(text, task["function_name"]) or text
    tr = cb.test_function(code, task)
    return {"passed": tr["passed"], "of": len(task["test_cases"]),
            "dt_s": round(dt, 2), "prefix_chars": len(prefix)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="kvpressure")
    ap.add_argument("--task", default="task3_nested_sum")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    target_task = next(t for t in cb.CODING_TASKS if t["id"] == a.task)
    print(f"=== KV PRESSURE bench (task={a.task}) ===")
    rows = []
    for tokens in [0, 2000, 5000, 10000]:
        distractor = build_distractor(tokens) if tokens > 0 else ""
        r = run_task(target_task, distractor)
        r["distractor_tokens"] = tokens
        rows.append(r)
        flag = "PASS" if r["passed"] == r["of"] else "FAIL"
        print(f"  distractor={tokens:6d} chars={r['prefix_chars']:6d}  {flag} {r['passed']}/{r['of']}  dt={r['dt_s']}s")
    Path(f"sweep_mode_kv_pressure_{a.label}.json").write_text(
        json.dumps({"args": vars(a), "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()
