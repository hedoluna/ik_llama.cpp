#!/usr/bin/env python3
"""sweep_bench_bug_hunt.py — bug classifier bench.

Input: code snippet 20-60 lines with 0-2 seeded bugs from a known taxonomy.
Output: model must list bug categories present (or 'NONE').
Scoring: precision/recall vs ground truth.

Bug taxonomy:
  OFF_BY_ONE, NULL_DEREF, RESOURCE_LEAK, RACE, SQL_INJECTION,
  PATH_TRAVERSAL, INTEGER_OVERFLOW, INFINITE_LOOP, TYPE_ERROR,
  WRONG_OPERATOR, MISSING_RETURN, UNHANDLED_EXC
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
RESULTS = Path(__file__).with_name("results_bug_hunt.json")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "loaded"

CASES = [
    {
        "id": "off_by_one_window",
        "code": '''def moving_avg(values, window):
    out = []
    for i in range(len(values) - window):
        s = sum(values[i:i+window])
        out.append(s / window)
    return out''',
        "bugs": ["OFF_BY_ONE"]  # should be len(values) - window + 1
    },
    {
        "id": "sql_injection",
        "code": '''def find_user(conn, name):
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM users WHERE name = '{name}'")
    return cur.fetchone()''',
        "bugs": ["SQL_INJECTION"]
    },
    {
        "id": "path_traversal",
        "code": '''def serve_file(req_path, root):
    full = root + "/" + req_path
    with open(full, "rb") as f:
        return f.read()''',
        "bugs": ["PATH_TRAVERSAL"]
    },
    {
        "id": "resource_leak",
        "code": '''def count_lines(path):
    f = open(path)
    n = 0
    for _ in f:
        n += 1
    return n''',
        "bugs": ["RESOURCE_LEAK"]
    },
    {
        "id": "null_deref",
        "code": '''def email_domain(user):
    parts = user.email.split("@")
    return parts[1].lower()''',
        "bugs": ["NULL_DEREF"]  # user.email could be None
    },
    {
        "id": "race_condition",
        "code": '''class Counter:
    def __init__(self):
        self.n = 0
    def incr(self):
        v = self.n
        v += 1
        self.n = v''',
        "bugs": ["RACE"]  # check-then-set without lock
    },
    {
        "id": "wrong_operator",
        "code": '''def is_adult(age):
    if age = 18:
        return True
    return False''',
        "bugs": ["TYPE_ERROR", "WRONG_OPERATOR"]  # = vs ==, parse error counts as either
    },
    {
        "id": "clean_correct",
        "code": '''def fib(n):
    if n < 2:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b''',
        "bugs": []
    },
    {
        "id": "infinite_loop",
        "code": '''def find_zero(arr):
    i = 0
    while arr[i] != 0:
        if arr[i] < 0:
            i += 1
        elif arr[i] > 10:
            i -= 1
    return i''',
        "bugs": ["INFINITE_LOOP"]  # neither branch advances if 0 < arr[i] <= 10
    },
    {
        "id": "missing_return",
        "code": '''def find_max(arr):
    if not arr:
        return None
    m = arr[0]
    for x in arr[1:]:
        if x > m:
            m = x
    # missing return''',
        "bugs": ["MISSING_RETURN"]
    },
]

TAXONOMY = ["OFF_BY_ONE","NULL_DEREF","RESOURCE_LEAK","RACE","SQL_INJECTION",
            "PATH_TRAVERSAL","INTEGER_OVERFLOW","INFINITE_LOOP","TYPE_ERROR",
            "WRONG_OPERATOR","MISSING_RETURN","UNHANDLED_EXC"]

PROMPT = (
    "Analizza il seguente codice e identifica bug PRESENTI. "
    f"Categorie ammesse: {', '.join(TAXONOMY)}. "
    "Se il codice è corretto, rispondi 'NONE'. "
    "Rispondi SOLO con la lista CSV delle categorie (es. 'OFF_BY_ONE,NULL_DEREF') oppure 'NONE'. "
    "Nessuna spiegazione, niente prosa.\n\n```python\n{code}\n```"
)

def call(model, prompt):
    r = requests.post(URL, json={
        "model": model, "messages": [{"role":"user","content":prompt}],
        "max_tokens": 128, "temperature": 0.1, "seed": 42
    }, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def parse(resp):
    # find first line that looks like CSV or NONE
    line = resp.strip().splitlines()[-1] if resp.strip() else ""
    line = line.strip().strip("`").strip()
    if "NONE" in line.upper():
        return set()
    found = set()
    for tok in re.split(r"[,\s]+", line.upper()):
        if tok in TAXONOMY:
            found.add(tok)
    return found

def main():
    results = {"model": MODEL, "cases": [], "tp":0,"fp":0,"fn":0,"tn":0}
    for c in CASES:
        prompt = PROMPT.format(code=c["code"])
        t0 = time.time()
        try:
            resp = call(MODEL, prompt)
        except Exception as e:
            resp = f"ERR:{e}"
        pred = parse(resp)
        gt = set(c["bugs"])
        tp = len(pred & gt); fp = len(pred - gt); fn = len(gt - pred)
        tn = 1 if (not pred and not gt) else 0
        results["tp"]+=tp; results["fp"]+=fp; results["fn"]+=fn; results["tn"]+=tn
        dt = round(time.time()-t0, 2)
        results["cases"].append({
            "id": c["id"], "gt": sorted(gt), "pred": sorted(pred),
            "tp":tp,"fp":fp,"fn":fn, "wall_s": dt, "resp_short": resp[:120]
        })
        print(f"[{c['id']}] gt={sorted(gt)} pred={sorted(pred)} tp={tp} fp={fp} fn={fn}")
    tp, fp, fn = results["tp"], results["fp"], results["fn"]
    prec = tp/(tp+fp) if (tp+fp) else 0
    rec  = tp/(tp+fn) if (tp+fn) else 0
    f1   = 2*prec*rec/(prec+rec) if (prec+rec) else 0
    results["precision"] = round(prec,3); results["recall"] = round(rec,3); results["f1"] = round(f1,3)
    print(f"\n== precision={prec:.2f} recall={rec:.2f} f1={f1:.2f} ==")
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
