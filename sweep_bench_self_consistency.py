#!/usr/bin/env python3
"""sweep_bench_self_consistency.py — Pass@5 wrapper for a single task.

Runs the same task N times at temp>0 with different seeds and reports
intersection rate (how often impl is correct AND identical across runs).
Default task: task3_nested_sum (the historically unstable one).
"""
from __future__ import annotations
import hashlib, json, re, subprocess, sys, tempfile, time
from pathlib import Path
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
RESULTS = Path(__file__).with_name("results_self_consistency.json")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "loaded"
N_RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
TEMP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6

TASK = {
    "id": "task3_nested_sum",
    "prompt": (
        "Scrivi una funzione Python `sum_nested_values(data, key)` che "
        "ritorna la somma di TUTTI i valori associati a `key` a QUALSIASI "
        "livello di annidamento dentro `data` (che può essere dict o list "
        "di dict). I valori NON numerici vanno ignorati. Esempio:\n"
        '`sum_nested_values({"a":{"x":1,"b":{"x":2}}, "c":[{"x":3}]}, "x")` -> 6.\n'
        "Rispondi SOLO con la funzione in un blocco ```python."
    ),
    "tests": [
        ('sum_nested_values({"x":5}, "x")', 5),
        ('sum_nested_values({"x":1,"y":{"x":2}}, "x")', 3),
        ('sum_nested_values({"x":1,"y":[{"x":2},{"x":3}]}, "x")', 6),
        ('sum_nested_values({"a":{"b":{"x":10}}}, "x")', 10),
        ('sum_nested_values({"x":"non-num","y":{"x":5}}, "x")', 5),
    ],
}

def call(prompt, seed):
    r = requests.post(URL, json={
        "model": MODEL, "messages":[{"role":"user","content":prompt}],
        "max_tokens": 1024, "temperature": TEMP, "seed": seed
    }, timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def extract(resp, fname):
    blocks = re.findall(r"```python\s*(.*?)\s*```", resp, re.DOTALL)
    if not blocks:
        blocks = re.findall(r"```\s*(.*?)\s*```", resp, re.DOTALL)
    for b in reversed(blocks):
        if f"def {fname}" in b:
            return b
    return blocks[-1] if blocks else resp

def run_tests(impl, tests):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.py"
        body = impl + "\n\n"
        for i,(expr,exp) in enumerate(tests):
            body += f"assert ({expr}) == ({exp!r}), 'T{i}'\n"
        p.write_text(body, encoding="utf-8")
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=15, cwd=d)
        return r.returncode == 0

def main():
    runs = []
    for i in range(N_RUNS):
        seed = 42 + i
        t0 = time.time()
        try:
            resp = call(TASK["prompt"], seed)
            impl = extract(resp, "sum_nested_values")
            ok = run_tests(impl, TASK["tests"])
        except Exception as e:
            impl, ok = f"ERR:{e}", False
        dt = round(time.time()-t0, 2)
        h = hashlib.sha256(impl.strip().encode("utf-8","ignore")).hexdigest()[:10]
        runs.append({"run":i, "seed":seed, "passed":ok, "impl_hash":h, "wall_s":dt})
        print(f"run {i} seed={seed}: {'PASS' if ok else 'FAIL'} hash={h} {dt}s")
    pass_count = sum(1 for r in runs if r["passed"])
    unique_impls = len({r["impl_hash"] for r in runs})
    unique_passing_impls = len({r["impl_hash"] for r in runs if r["passed"]})
    results = {
        "model": MODEL, "task": TASK["id"], "n_runs": N_RUNS, "temp": TEMP,
        "pass_at_n": pass_count, "unique_impls": unique_impls,
        "unique_passing_impls": unique_passing_impls,
        "pass_rate": round(pass_count/N_RUNS, 3),
        "runs": runs
    }
    print(f"\n== pass {pass_count}/{N_RUNS} unique_impls={unique_impls} unique_passing={unique_passing_impls} ==")
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
