#!/usr/bin/env python3
"""sweep_lib_sanity.py — preflight scorer sanity check.

Importa coding_benchmark e verifica che `test_function()` ritorni
passed==total per ogni task quando alimentato con una soluzione corretta
known-good. Se fallisce, fail-fast: il scorer è rotto, NON eseguire il bench.

Lezione meta dalla session 2026-05-12 (bug sweep_mode_antiglaze):
mai eseguire un bench senza prima verificare che lo scorer riconosce
soluzioni note come corrette.

Usage:
    from sweep_lib_sanity import preflight_scorer
    preflight_scorer(cb)  # raises AssertionError se scorer rotto
"""
from __future__ import annotations

KNOWN_GOOD: dict[str, str] = {
    "task1_fizzbuzz": '''
def fizzbuzz(n):
    if n % 15 == 0: return "FizzBuzz"
    if n % 3 == 0: return "Fizz"
    if n % 5 == 0: return "Buzz"
    return str(n)
''',
    "task2_duplicates": '''
def find_duplicates(lst):
    from collections import Counter
    return [x for x, c in Counter(lst).items() if c > 1]
''',
    "task3_nested_sum": '''
def sum_nested_values(data, key):
    # NB: bench test cases attendono che liste NON siano walked
    # (test 2: {"z": [{"x": 15}]} con key="x" expected=15 not 30).
    # Spec ambiguous, codifico de-facto behavior.
    total = 0
    if not isinstance(data, dict):
        return 0
    for k, v in data.items():
        if isinstance(v, dict):
            total += sum_nested_values(v, key)
        elif k == key and isinstance(v, (int, float)):
            total += v
    return total
''',
    "task4_flatten": '''
def flatten(nested):
    result = []
    for x in nested:
        if isinstance(x, list):
            result.extend(flatten(x))
        else:
            result.append(x)
    return result
''',
    "task5_parse_config": '''
def parse_config(text):
    result = {}
    for line in text.split("\\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result
''',
    "task6_merge_intervals": '''
def merge_intervals(intervals):
    if not intervals: return []
    intervals = sorted(intervals)
    out = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= out[-1][1]:
            out[-1] = [out[-1][0], max(out[-1][1], end)]
        else:
            out.append([start, end])
    return out
''',
    "task7_balanced_brackets": '''
def balanced_brackets(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for c in s:
        if c in "([{":
            stack.append(c)
        else:
            if not stack or stack[-1] != pairs[c]:
                return False
            stack.pop()
    return not stack
''',
    "task8_deep_merge": '''
def deep_merge(d1, d2):
    out = dict(d1)
    for k, v in d2.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
''',
}


def preflight_scorer(cb_module) -> None:
    """Raise AssertionError if scorer fails to recognize known-good code."""
    failures = []
    for task in cb_module.CODING_TASKS:
        known = KNOWN_GOOD.get(task["id"])
        if not known:
            failures.append(f"{task['id']}: NO KNOWN_GOOD defined")
            continue
        tr = cb_module.test_function(known.strip(), task)
        n = len(task["test_cases"])
        if tr["passed"] != n:
            failures.append(
                f"{task['id']}: scorer flagged known-good as {tr['passed']}/{n} "
                f"(errors: {tr.get('errors', [])[:2]})"
            )
    if failures:
        raise AssertionError(
            "SCORER PREFLIGHT FAILED — refusing to run bench:\n  " +
            "\n  ".join(failures)
        )
    print(f"[preflight] scorer OK on {len(cb_module.CODING_TASKS)} tasks")


if __name__ == "__main__":
    import importlib.util
    from pathlib import Path
    BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
    spec = importlib.util.spec_from_file_location("cb", BENCH)
    cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)
    preflight_scorer(cb)
