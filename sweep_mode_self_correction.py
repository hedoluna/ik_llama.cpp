#!/usr/bin/env python3
"""sweep_mode_self_correction.py — Pass@1+1 con error feedback.

Per ogni task: gen → test. Se FAIL → re-prompt con error message → test again.
Misura: Pass@1 (no feedback), Pass@1+1 (1 retry con feedback), delta.

Indirizza Gemini gap #3 (self-correction agentic loop).
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

from sweep_lib_sanity import preflight_scorer
preflight_scorer(cb)


def chat(messages: list, temp: float = 0.1) -> tuple[str, float]:
    t0 = time.time()
    r = requests.post(cb.LM_STUDIO_URL, json={
        "model": "selfcorr",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": temp,
        "seed": 42,
    }, timeout=600)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def feedback_for(tr: dict, task: dict) -> str:
    """Build error message from test_function result."""
    details = tr.get("details", [])
    failing = [d for d in details if not d.get("passed")]
    if not failing:
        # generic feedback
        return f"Il codice non passa i test. Errori: {tr.get('errors', [])}"
    examples = "\n".join(
        f"  test{d.get('test',i+1)}: expected={d.get('expected')!r} got={d.get('got', d.get('error'))!r}"
        for i, d in enumerate(failing[:3])
    )
    return (f"Il codice precedente ha fallito {len(failing)} test:\n{examples}\n"
            f"Correggi la funzione `{task['function_name']}`. Output: solo codice Python.")


def run_task(task: dict, temp: float) -> dict:
    # Pass 1: standard
    msgs = [
        {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
        {"role": "user", "content": task["prompt"]},
    ]
    resp1, dt1 = chat(msgs, temp)
    code1 = cb.extract_function(resp1, task["function_name"]) or resp1
    tr1 = cb.test_function(code1, task)
    pass1 = tr1["passed"] == len(task["test_cases"])
    # If pass, no retry
    if pass1:
        return {"task": task["id"], "pass1": True, "pass1_plus_1": True,
                "passed_initial": tr1["passed"], "of": len(task["test_cases"]),
                "dt_first": round(dt1, 2), "dt_retry": 0}
    # Pass 1+1: provide feedback
    msgs.append({"role": "assistant", "content": resp1})
    msgs.append({"role": "user", "content": feedback_for(tr1, task)})
    resp2, dt2 = chat(msgs, temp)
    code2 = cb.extract_function(resp2, task["function_name"]) or resp2
    tr2 = cb.test_function(code2, task)
    pass2 = tr2["passed"] == len(task["test_cases"])
    return {"task": task["id"], "pass1": False, "pass1_plus_1": pass2,
            "passed_initial": tr1["passed"], "passed_retry": tr2["passed"],
            "of": len(task["test_cases"]),
            "dt_first": round(dt1, 2), "dt_retry": round(dt2, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temp", type=float, default=0.1)
    ap.add_argument("--label", default="selfcorr")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(f"=== Self-correction Pass@1+1 (temp={a.temp}) ===")
    rows = []
    pass1_n = pass2_n = 0
    for task in cb.CODING_TASKS:
        r = run_task(task, a.temp)
        rows.append(r)
        flag = "PASS@1" if r["pass1"] else ("RECOVER" if r["pass1_plus_1"] else "STILL_FAIL")
        print(f"  {r['task']:22s} {flag:11s} init={r['passed_initial']}/{r['of']}"
              f"{' retry='+str(r.get('passed_retry','-'))+'/'+str(r['of']) if not r['pass1'] else ''}"
              f"  dt={r['dt_first']}+{r['dt_retry']}s")
        if r["pass1"]: pass1_n += 1
        if r["pass1_plus_1"]: pass2_n += 1
    delta = pass2_n - pass1_n
    print(f"\n  Pass@1:   {pass1_n}/{len(rows)}")
    print(f"  Pass@1+1: {pass2_n}/{len(rows)}  (Δ +{delta})")
    Path(f"sweep_mode_self_correction_{a.label}.json").write_text(
        json.dumps({"args": vars(a), "rows": rows, "pass1": pass1_n, "pass1_plus_1": pass2_n},
                   indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
