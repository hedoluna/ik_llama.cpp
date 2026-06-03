#!/usr/bin/env python3
"""sweep_bench_roundtrip_lint.py — round-trip "clean first attempt" gate.

Inspired by glukhov article: "clean first attempt, not requiring to fix any
typos" — a quality metric beyond functional pass/fail. A function may pass
its tests but emit dead code, unused imports, or shadowed builtins.

Re-generates the 8 coding tasks once with the current server, then runs
`ruff check --select ALL --ignore D,ANN,COM812,ISC001` on each extracted
function. Reports first-try-clean rate per task.
"""
from __future__ import annotations
import importlib.util
import json
import subprocess
import sys, io
import tempfile
import time
import requests
from pathlib import Path

BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
spec = importlib.util.spec_from_file_location("cb", BENCH)
cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)

URL = cb.LM_STUDIO_URL
RUFF_IGNORE = "D,ANN,COM812,ISC001,T201,N999,INP001,Q000,PT,RUF002,UP032,EM101,EM102,TRY003,W291,W293"


def chat(prompt: str) -> tuple[str, float]:
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "rt",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048, "temperature": 0.1, "seed": 42,
    }, timeout=120)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def lint(code: str) -> dict:
    if not code:
        return {"clean": False, "n_issues": -1, "issues": ["no code"]}
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tf:
        tf.write(code)
        path = tf.name
    try:
        cp = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "ALL",
             "--ignore", RUFF_IGNORE, "--output-format", "concise", path],
            capture_output=True, text=True, timeout=30,
        )
        lines = [ln for ln in (cp.stdout or "").splitlines() if ln.strip() and "Found " not in ln and "All checks" not in ln]
        # ruff output: path:line:col: CODE message — strip the temp path noise
        issues = [ln.split(":", 3)[-1].strip() if path in ln else ln for ln in lines]
        return {"clean": len(issues) == 0, "n_issues": len(issues), "issues": issues[:5]}
    finally:
        Path(path).unlink(missing_ok=True)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("=== ROUND-TRIP LINT bench (ruff) ===")
    rows = []
    for task in cb.CODING_TASKS:
        resp, dt = chat(task["prompt"])
        fn_code = cb.extract_function(resp, task["function_name"]) or resp
        # also test functional correctness
        tr = cb.test_function(fn_code, task)
        func_pass = tr["passed"] == len(task["test_cases"])
        # then lint
        lr = lint(fn_code)
        rows.append({
            "task": task["id"], "func_pass": func_pass,
            "clean": lr["clean"], "n_issues": lr["n_issues"],
            "issues_preview": lr["issues"][:3],
            "dt_s": round(dt, 2),
        })
        status = "PASS+CLEAN" if (func_pass and lr["clean"]) else \
                 ("PASS+DIRTY" if func_pass else "FAIL")
        print(f"  {task['id']:22s} {status:12s} issues={lr['n_issues']:3d}  ({dt:.2f}s)")
        for iss in lr["issues"][:2]:
            print(f"     ↳ {iss}")
    pass_clean = sum(1 for r in rows if r["func_pass"] and r["clean"])
    pass_dirty = sum(1 for r in rows if r["func_pass"] and not r["clean"])
    fail = sum(1 for r in rows if not r["func_pass"])
    print(f"\n  PASS+CLEAN: {pass_clean}/8")
    print(f"  PASS+DIRTY: {pass_dirty}/8")
    print(f"  FAIL:       {fail}/8")
    Path("sweep_bench_roundtrip_lint_result.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
