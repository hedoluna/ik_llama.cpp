#!/usr/bin/env python3
"""sweep_bench_test_first.py — TDD red->green bench.

Input: a failing pytest test. Output: implementation that makes it pass.
Scoring: deterministic — run pytest against generated impl + given test,
check exit code + 'passed' count.

Use case: tests cap 'leggere intent dei test e produrre impl minima'.
Different from coding_benchmark.py which gives prose spec; here only the
test exists.
"""
from __future__ import annotations
import json, re, subprocess, sys, tempfile, time, os
from pathlib import Path
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
RESULTS = Path(__file__).with_name("results_test_first.json")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "loaded"

CASES = [
    {
        "id": "stack_pop_empty",
        "test": '''
def test_stack():
    s = Stack()
    assert s.is_empty() is True
    s.push(1); s.push(2)
    assert s.pop() == 2
    assert s.peek() == 1
    assert len(s) == 1
    import pytest
    s2 = Stack()
    with pytest.raises(IndexError):
        s2.pop()
'''
    },
    {
        "id": "lru_cache",
        "test": '''
def test_lru():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)  # evict b (LRU)
    assert c.get("b") is None
    assert c.get("c") == 3
    assert c.get("a") == 1
    c.put("d", 4)  # evict c (LRU now)
    assert c.get("c") is None
'''
    },
    {
        "id": "parse_duration",
        "test": '''
def test_parse_duration():
    assert parse_duration("1h") == 3600
    assert parse_duration("30m") == 1800
    assert parse_duration("45s") == 45
    assert parse_duration("1h30m") == 5400
    assert parse_duration("2h15m30s") == 8130
    import pytest
    with pytest.raises(ValueError):
        parse_duration("garbage")
'''
    },
    {
        "id": "rate_limiter_window",
        "test": '''
import time
def test_rate_limiter():
    rl = RateLimiter(max_calls=3, window_seconds=1.0)
    assert rl.allow("user1") is True
    assert rl.allow("user1") is True
    assert rl.allow("user1") is True
    assert rl.allow("user1") is False  # 4th call in window denied
    assert rl.allow("user2") is True   # different user OK
    time.sleep(1.05)
    assert rl.allow("user1") is True   # window slid
'''
    },
    {
        "id": "topo_sort",
        "test": '''
def test_toposort():
    deps = {"a": [], "b": ["a"], "c": ["a", "b"], "d": ["c"]}
    order = topo_sort(deps)
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")
    assert order.index("c") < order.index("d")
    import pytest
    with pytest.raises(ValueError):
        topo_sort({"a": ["b"], "b": ["a"]})  # cycle
'''
    },
    {
        "id": "url_parse",
        "test": '''
def test_url():
    u = parse_url("https://user:pass@example.com:8080/a/b?x=1&y=2#frag")
    assert u.scheme == "https"
    assert u.host == "example.com"
    assert u.port == 8080
    assert u.user == "user"
    assert u.password == "pass"
    assert u.path == "/a/b"
    assert u.query == {"x": "1", "y": "2"}
    assert u.fragment == "frag"
'''
    },
    {
        "id": "retry_decorator",
        "test": '''
def test_retry():
    calls = []
    @retry(max_attempts=3, on=(ValueError,))
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("nope")
        return "ok"
    assert flaky() == "ok"
    assert len(calls) == 3
    calls.clear()
    @retry(max_attempts=2, on=(ValueError,))
    def always_fail():
        calls.append(1)
        raise ValueError("nope")
    import pytest
    with pytest.raises(ValueError):
        always_fail()
    assert len(calls) == 2
'''
    },
]

PROMPT = (
    "Sei un programmatore Python esperto. Ti viene fornito un test pytest. "
    "Scrivi SOLO la classe/funzione che fa passare il test. "
    "Non scrivere il test, non scrivere import inutili, niente prosa.\n\n"
    "TEST:\n```python\n{test}\n```\n\n"
    "Scrivi l'implementazione qui sotto in un singolo blocco ```python.\n"
)

def call(model, prompt):
    r = requests.post(URL, json={
        "model": model, "messages": [{"role":"user","content":prompt}],
        "max_tokens": 2048, "temperature": 0.1, "seed": 42
    }, timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def extract(resp):
    blocks = re.findall(r"```python\s*(.*?)\s*```", resp, re.DOTALL)
    if not blocks:
        blocks = re.findall(r"```\s*(.*?)\s*```", resp, re.DOTALL)
    return blocks[-1] if blocks else resp

def run_test(impl, test):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "test_x.py"
        p.write_text(impl + "\n\n" + test, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "--tb=short", str(p)],
            capture_output=True, text=True, timeout=30, cwd=d
        )
        return r.returncode == 0, (r.stdout + r.stderr)[-400:]

def main():
    results = {"model": MODEL, "cases": [], "passed": 0, "total": len(CASES)}
    for c in CASES:
        prompt = PROMPT.format(test=c["test"])
        t0 = time.time()
        try:
            resp = call(MODEL, prompt)
            impl = extract(resp)
            ok, tail = run_test(impl, c["test"])
        except subprocess.TimeoutExpired:
            ok, tail = False, "TIMEOUT"
            impl = ""
        except Exception as e:
            ok, tail = False, f"ERR: {type(e).__name__}: {e}"
            impl = ""
        dt = round(time.time() - t0, 2)
        if ok: results["passed"] += 1
        results["cases"].append({
            "id": c["id"], "passed": ok, "wall_s": dt,
            "impl_chars": len(impl), "tail": tail
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {c['id']}  {dt}s")
    print(f"\n== {results['passed']}/{results['total']} ==")
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
