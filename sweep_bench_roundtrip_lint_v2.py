#!/usr/bin/env python3
"""sweep_bench_roundtrip_lint_v2.py — ruff --fix safety.

Re-generates code on current server, runs:
  1. functional test (cb.test_function)
  2. ruff check → count issues
  3. ruff check --fix → auto-fix the file
  4. functional test AGAIN on fixed code

Reports: (a) pre-fix pass, (b) post-fix pass, (c) fix-broke-functionality?
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
RUFF_IGNORE = "D,ANN,COM812,ISC001,T201,N999,INP001,Q000,PT,RUF002,UP032,EM101,EM102,TRY003"


def chat(prompt: str) -> tuple[str, float]:
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "rtv2",
        "messages": [
            {"role": "system", "content": "Sei un programmatore Python esperto. Rispondi SOLO con codice Python, senza spiegazioni."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048, "temperature": 0.1, "seed": 42,
    }, timeout=120)
    return r.json()["choices"][0]["message"]["content"], time.time() - t0


def lint(code: str, fix: bool = False) -> tuple[int, str]:
    """Return (issues_count, fixed_code if fix else code_unchanged)."""
    if not code:
        return -1, code
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tf:
        tf.write(code); path = tf.name
    try:
        if fix:
            subprocess.run([sys.executable, "-m", "ruff", "check", "--select", "ALL",
                            "--ignore", RUFF_IGNORE, "--fix", "--unsafe-fixes", path],
                           capture_output=True, timeout=30)
            fixed = Path(path).read_text(encoding="utf-8")
        else:
            fixed = code
        cp = subprocess.run([sys.executable, "-m", "ruff", "check", "--select", "ALL",
                             "--ignore", RUFF_IGNORE, "--output-format", "concise", path],
                            capture_output=True, text=True, timeout=30)
        lines = [ln for ln in (cp.stdout or "").splitlines()
                 if ln.strip() and "Found " not in ln and "All checks" not in ln]
        return len(lines), fixed
    finally:
        Path(path).unlink(missing_ok=True)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("=== ROUND-TRIP LINT v2: ruff --fix safety ===")
    rows = []
    for task in cb.CODING_TASKS:
        resp, dt = chat(task["prompt"])
        fn_code = cb.extract_function(resp, task["function_name"]) or resp
        # functional pre-fix
        tr0 = cb.test_function(fn_code, task)
        pre_pass = tr0["passed"] == len(task["test_cases"])
        n_issues_pre, _ = lint(fn_code, fix=False)
        # apply fix
        n_issues_post, fixed_code = lint(fn_code, fix=True)
        # functional post-fix
        tr1 = cb.test_function(fixed_code, task)
        post_pass = tr1["passed"] == len(task["test_cases"])
        broke = (pre_pass and not post_pass)
        rows.append({
            "task": task["id"],
            "pre_pass": pre_pass, "post_pass": post_pass,
            "pre_issues": n_issues_pre, "post_issues": n_issues_post,
            "fix_broke_functionality": broke,
            "dt_s": round(dt, 2),
        })
        flag = "BROKE!" if broke else ("ok" if post_pass else ("never-passed" if not pre_pass else "?"))
        print(f"  {task['id']:22s} pre={'PASS' if pre_pass else 'FAIL':4s}->{'PASS' if post_pass else 'FAIL':4s}  "
              f"issues={n_issues_pre}->{n_issues_post}  {flag}")
    broke_n = sum(1 for r in rows if r["fix_broke_functionality"])
    clean_after = sum(1 for r in rows if r["post_pass"] and r["post_issues"] == 0)
    print(f"\n  fix BROKE functionality: {broke_n}/{len(rows)}")
    print(f"  CLEAN after fix:         {clean_after}/{len(rows)}")
    Path("sweep_bench_roundtrip_lint_v2_result.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
