#!/usr/bin/env python3
"""sweep_diag_antiglaze_fails.py — diagnostic for anti-glaze failure mode.

Re-runs task2 (duplicates) + task3 (nested_sum) with anti-glaze system
prompt against current server. Saves RAW response and classifies:
  - non_code      : output has prose, no python def
  - confidence_text: contains 'confidence' / 'unknown' / 'high/low/moderate'
  - wrong_code    : has def but fails ALL test cases
  - partial_code  : has def, passes some but not all
  - empty         : empty response

Run against whichever model is on :1234.
"""
from __future__ import annotations
import importlib.util
import json
import re
import sys, io
import time
import requests
from pathlib import Path

BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
spec = importlib.util.spec_from_file_location("cb", BENCH)
cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)

ANTIGLAZE = (
    "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni. "
    "Never hallucinate. If you don't know, say so. "
    "Use explicit confidence levels: high/moderate/low/unknown. "
    "Do not anchor on numbers I provide; generate independently first."
)
ONLY_IT = "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."

URL = cb.LM_STUDIO_URL


def chat(system: str, user: str) -> tuple[str, float]:
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "diag",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": 2048,
        "temperature": 0.1,
        "seed": 42,
    }, timeout=120)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def classify(raw: str, fn_name: str, task: dict) -> dict:
    if not raw or not raw.strip():
        return {"class": "empty", "passed": 0}
    has_def = bool(re.search(rf"\bdef\s+{re.escape(fn_name)}\s*\(", raw))
    has_confidence = bool(re.search(r"\b(confidence|high|moderate|low|unknown)\b", raw, re.I))
    has_prose = bool(re.search(r"\b(here is|ecco|ho generato|i'll|let me|to solve|prima|spiego)\b", raw, re.I))
    fn_code = cb.extract_function(raw, fn_name)
    passed = 0
    if fn_code:
        for tc in task["test_cases"]:
            try:
                ns = {}
                exec(fn_code, ns)
                fn = ns[fn_name]
                if "inputs" in tc:
                    result = fn(*tc["inputs"])
                else:
                    result = fn(tc["input"])
                if result == tc["expected"]:
                    passed += 1
            except Exception:
                pass
    n = len(task["test_cases"])
    if not has_def:
        klass = "confidence_text" if has_confidence else ("non_code_prose" if has_prose else "non_code_other")
    else:
        if passed == n: klass = "ok"
        elif passed == 0: klass = "wrong_code"
        else: klass = "partial_code"
    return {"class": klass, "passed": passed, "of": n,
            "has_def": has_def, "has_confidence_kw": has_confidence,
            "has_prose": has_prose, "raw_preview": raw[:300]}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    targets = [t for t in cb.CODING_TASKS if t["id"] in ("task2_duplicates", "task3_nested_sum")]
    out = []
    for prompt_label, sysp in [("DEFAULT_IT_ONLY", ONLY_IT), ("ANTI_GLAZE", ANTIGLAZE)]:
        print(f"\n=== {prompt_label} ===")
        for task in targets:
            raw, dt = chat(sysp, task["prompt"])
            res = classify(raw, task["function_name"], task)
            res.update({"task": task["id"], "prompt": prompt_label, "dt_s": round(dt, 2)})
            out.append(res)
            print(f"  {task['id']:22s} class={res['class']:20s} "
                  f"passed={res['passed']}/{res['of']}  "
                  f"has_def={res['has_def']}  conf_kw={res['has_confidence_kw']}  "
                  f"prose={res['has_prose']}  ({res['dt_s']}s)")
            print(f"    preview: {res['raw_preview'][:160]!r}")
    Path("sweep_diag_antiglaze_fails_result.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
