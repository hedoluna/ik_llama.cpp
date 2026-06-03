#!/usr/bin/env python3
"""sweep_mode_antiglaze.py — test anti-glaze 3-line excerpt as system prompt.

Monkey-patches coding_benchmark.chat_completion to inject the anti-glaze
system prompt instead of the default. Runs against an already-started
Coder-1.5B migarcoes server on :1234.
"""
from __future__ import annotations
import importlib.util
import json
import sys
import time
from pathlib import Path

BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
spec = importlib.util.spec_from_file_location("cb", BENCH)
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

ANTIGLAZE = (
    "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni. "
    "Never hallucinate. If you don't know, say so. "
    "Use explicit confidence levels: high/moderate/low/unknown. "
    "Do not anchor on numbers I provide; generate independently first."
)

import requests
_session = requests.Session()


def chat_completion_antiglaze(model, prompt):
    start = time.time()
    try:
        r = _session.post(
            cb.LM_STUDIO_URL,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": ANTIGLAZE},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 2048,
                "temperature": 0.1,
                "seed": 42,
            },
            timeout=cb.TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"], time.time() - start
    except Exception:
        return None, time.time() - start


cb.chat_completion = chat_completion_antiglaze


def main():
    # mirror coding_benchmark.benchmark_model() but smaller surface
    model = "antiglaze-test"
    print(f"[ANTI-GLAZE] testing {model}")
    t0 = time.time()
    per_task = []
    total_pass = total = 0
    for task in cb.CODING_TASKS:
        resp, dt = cb.chat_completion(model, task["prompt"])
        if resp is None:
            per_task.append({"id": task["id"], "verdict": "FAIL", "passed": 0,
                              "total": len(task["test_cases"]), "time_s": round(dt, 2)})
            total += len(task["test_cases"])
            continue
        fn_code = cb.extract_function(resp, task["function_name"])
        # Use the bench's own test_function() so expected_set/input_data are honored
        tr = cb.test_function(fn_code, task)
        passed = tr["passed"]
        verdict = "PASS" if passed == len(task["test_cases"]) else "FAIL"
        per_task.append({"id": task["id"], "verdict": verdict, "passed": passed,
                         "total": len(task["test_cases"]), "time_s": round(dt, 2)})
        total_pass += passed
        total += len(task["test_cases"])
        print(f"  {task['id']:30s} {verdict} {passed}/{len(task['test_cases'])} ({dt:.2f}s)")
    total_t = time.time() - t0
    print(f"\nTOTAL: {total_pass}/{total} in {total_t:.2f}s")
    out = {
        "label": "Qwen2.5-Coder-1.5B-migarcoes + anti-glaze system prompt",
        "passed": total_pass, "total": total, "wall_s": round(total_t, 2),
        "per_task": per_task,
    }
    (Path(__file__).parent / "sweep_mode_antiglaze_result.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
