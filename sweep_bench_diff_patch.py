#!/usr/bin/env python3
"""sweep_bench_diff_patch.py — apply unified diff to source.

Input: source file + a unified diff to apply.
Output: model must return the FULL modified file content.
Scoring: byte-exact match to expected result.
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
RESULTS = Path(__file__).with_name("results_diff_patch.json")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "loaded"

# Each case: source, diff, expected_result (post-patch)
CASES = [
    {
        "id": "simple_rename",
        "source": '''def greet(name):
    return "Hello " + name

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
''',
        "diff": '''@@ -1,2 +1,2 @@
-def greet(name):
-    return "Hello " + name
+def greet(name, greeting="Hello"):
+    return greeting + " " + name
''',
        "expected": '''def greet(name, greeting="Hello"):
    return greeting + " " + name

def main():
    print(greet("World"))

if __name__ == "__main__":
    main()
'''
    },
    {
        "id": "add_imports",
        "source": '''def compute(data):
    return sum(data)
''',
        "diff": '''@@ -1,2 +1,5 @@
+from math import sqrt
+
 def compute(data):
-    return sum(data)
+    return sqrt(sum(data))
''',
        "expected": '''from math import sqrt

def compute(data):
    return sqrt(sum(data))
'''
    },
    {
        "id": "delete_block",
        "source": '''def foo():
    print("a")
    print("b")
    print("c")
    print("d")
    return 1
''',
        "diff": '''@@ -2,3 +2,1 @@
     print("a")
-    print("b")
-    print("c")
     print("d")
''',
        "expected": '''def foo():
    print("a")
    print("d")
    return 1
'''
    },
    {
        "id": "two_hunks",
        "source": '''def f():
    x = 1
    return x

def g():
    y = 2
    return y
''',
        "diff": '''@@ -1,3 +1,3 @@
 def f():
-    x = 1
+    x = 10
     return x
@@ -5,3 +5,3 @@
 def g():
-    y = 2
+    y = 20
     return y
''',
        "expected": '''def f():
    x = 10
    return x

def g():
    y = 20
    return y
'''
    },
    {
        "id": "context_only_block_move",
        "source": '''class Counter:
    def __init__(self):
        self.n = 0
    def incr(self):
        self.n += 1
    def value(self):
        return self.n
''',
        "diff": '''@@ -4,2 +4,4 @@
     def incr(self):
+        if self.n >= 100:
+            raise ValueError("max reached")
         self.n += 1
''',
        "expected": '''class Counter:
    def __init__(self):
        self.n = 0
    def incr(self):
        if self.n >= 100:
            raise ValueError("max reached")
        self.n += 1
    def value(self):
        return self.n
'''
    },
]

PROMPT = (
    "Applica il diff unificato al file. Rispondi SOLO con il contenuto "
    "completo del file dopo l'applicazione del diff, in un singolo blocco "
    "```. Niente prosa, niente spiegazioni.\n\n"
    "FILE ORIGINALE:\n```\n{source}```\n\n"
    "DIFF:\n```diff\n{diff}```\n"
)

def call(model, prompt):
    r = requests.post(URL, json={
        "model": model, "messages": [{"role":"user","content":prompt}],
        "max_tokens": 2048, "temperature": 0.0, "seed": 42
    }, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def extract(resp):
    blocks = re.findall(r"```(?:python|diff|text|)?\s*\n?(.*?)```", resp, re.DOTALL)
    return blocks[-1] if blocks else resp

def norm(s):
    # tolerate trailing newline + windows CRLF
    return s.replace("\r\n", "\n").rstrip() + "\n"

def main():
    results = {"model": MODEL, "cases": [], "passed": 0, "total": len(CASES)}
    for c in CASES:
        prompt = PROMPT.format(source=c["source"], diff=c["diff"])
        t0 = time.time()
        try:
            resp = call(MODEL, prompt)
            got = extract(resp)
            ok = norm(got) == norm(c["expected"])
        except Exception as e:
            ok, got = False, f"ERR:{e}"
        dt = round(time.time() - t0, 2)
        if ok: results["passed"] += 1
        results["cases"].append({
            "id": c["id"], "passed": ok, "wall_s": dt,
            "diff_chars": abs(len(norm(got)) - len(norm(c["expected"])))
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {c['id']}  {dt}s")
    print(f"\n== {results['passed']}/{results['total']} ==")
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
