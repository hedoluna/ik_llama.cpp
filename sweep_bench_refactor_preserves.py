#!/usr/bin/env python3
"""sweep_bench_refactor_preserves.py — refactor without breaking behavior.

Input: working impl + its passing tests + refactor instruction.
Output: refactored impl. Tests MUST still pass.
Scoring: pytest exit code on refactored code + given tests.
"""
from __future__ import annotations
import json, re, subprocess, sys, tempfile, time
from pathlib import Path
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"
RESULTS = Path(__file__).with_name("results_refactor_preserves.json")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "loaded"

CASES = [
    {
        "id": "extract_constant",
        "impl": '''def shipping(weight_kg, dest):
    if dest == "EU":
        if weight_kg <= 1: return 5
        if weight_kg <= 5: return 12
        return 25
    if dest == "US":
        if weight_kg <= 1: return 8
        if weight_kg <= 5: return 18
        return 35
    return 50''',
        "test": '''
def test():
    assert shipping(0.5, "EU") == 5
    assert shipping(3, "EU") == 12
    assert shipping(10, "EU") == 25
    assert shipping(0.5, "US") == 8
    assert shipping(3, "US") == 18
    assert shipping(10, "US") == 35
    assert shipping(1, "JP") == 50
''',
        "instruction": "Refactor: estrai la tabella dei prezzi in una struttura dati (dict di tuple-list) e implementa una sola funzione di lookup."
    },
    {
        "id": "remove_dup",
        "impl": '''def validate_user(u):
    if not u: return False
    if not u.get("email"): return False
    if "@" not in u["email"]: return False
    return True

def validate_admin(u):
    if not u: return False
    if not u.get("email"): return False
    if "@" not in u["email"]: return False
    if not u.get("admin"): return False
    return True''',
        "test": '''
def test():
    assert validate_user({"email":"a@b"}) is True
    assert validate_user({}) is False
    assert validate_user(None) is False
    assert validate_user({"email":"plain"}) is False
    assert validate_admin({"email":"a@b","admin":True}) is True
    assert validate_admin({"email":"a@b"}) is False
    assert validate_admin({"email":"a@b","admin":False}) is False
''',
        "instruction": "Refactor: rimuovi duplicazione tra validate_user e validate_admin. Mantieni le stesse due funzioni pubbliche."
    },
    {
        "id": "early_return",
        "impl": '''def process(items):
    result = []
    for item in items:
        if item is not None:
            if hasattr(item, "value"):
                if item.value > 0:
                    result.append(item.value * 2)
    return result''',
        "test": '''
class Obj:
    def __init__(self,v): self.value = v
def test():
    assert process([Obj(1), Obj(2), None, Obj(-1)]) == [2, 4]
    assert process([]) == []
    assert process([None, None]) == []
    assert process([Obj(0), Obj(3)]) == [6]
''',
        "instruction": "Refactor: appiattisci la nested-if con guard clauses (continue) per leggibilità. Comportamento invariato."
    },
    {
        "id": "to_comprehension",
        "impl": '''def even_squares(nums):
    out = []
    for n in nums:
        if n % 2 == 0:
            out.append(n * n)
    return out''',
        "test": '''
def test():
    assert even_squares([1,2,3,4,5]) == [4, 16]
    assert even_squares([]) == []
    assert even_squares([1,3,5]) == []
    assert even_squares([0]) == [0]
''',
        "instruction": "Refactor: usa una list comprehension single-line."
    },
    {
        "id": "split_function",
        "impl": '''def process_order(order):
    total = 0
    for item in order["items"]:
        price = item["price"] * item["qty"]
        if item.get("discount"):
            price *= (1 - item["discount"])
        total += price
    if order.get("coupon") == "VIP10":
        total *= 0.9
    tax = total * 0.22
    return {"subtotal": round(total, 2), "tax": round(tax, 2), "total": round(total + tax, 2)}''',
        "test": '''
def test():
    o = {"items":[{"price":10,"qty":2}]}
    r = process_order(o)
    assert r["subtotal"] == 20.0
    assert r["tax"] == 4.4
    assert r["total"] == 24.4
    o = {"items":[{"price":100,"qty":1,"discount":0.5}], "coupon":"VIP10"}
    r = process_order(o)
    assert r["subtotal"] == 45.0
    assert r["total"] == 54.9
''',
        "instruction": "Refactor: dividi in 3 funzioni pure - _calc_items_total, _apply_coupon, _add_tax. process_order le orchestra. Stesse signatures pubbliche."
    },
    {
        "id": "param_object",
        "impl": '''def create_user(name, email, age, role, active, country, signup_source):
    return {"name":name,"email":email,"age":age,"role":role,"active":active,"country":country,"source":signup_source}''',
        "test": '''
def test():
    u = create_user("Ana","a@b",30,"admin",True,"IT","web")
    assert u["name"] == "Ana"
    assert u["role"] == "admin"
    assert u["country"] == "IT"
    assert u["source"] == "web"
    assert u["active"] is True
''',
        "instruction": "Refactor: introduci un dataclass UserSpec per i parametri. La firma create_user(spec: UserSpec) deve accettare il dataclass. Mantieni le keys del dict di output uguali."
    },
]

PROMPT = (
    "Sei un esperto refactoring Python. Riceverai impl + test + istruzione. "
    "Riscrivi l'impl secondo l'istruzione, mantenendo TUTTI i test passanti. "
    "Output: SOLO il codice Python refactored in un singolo blocco ```python. "
    "Nessuna spiegazione, niente test (i test esistono già).\n\n"
    "IMPL ORIGINALE:\n```python\n{impl}\n```\n\n"
    "TEST DEVONO PASSARE INVARIATI:\n```python\n{test}\n```\n\n"
    "ISTRUZIONE: {instruction}\n"
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
        prompt = PROMPT.format(**c)
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
