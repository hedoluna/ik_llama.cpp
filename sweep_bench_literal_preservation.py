#!/usr/bin/env python3
"""sweep_bench_literal_preservation.py — slug-rewrite-trap bench.

Tests whether the model preserves EXACT tokens (invoice IDs, URL paths,
placeholders) when asked to perform a transformation (translate / rephrase /
explain). Inspired by glukhov.org article: models that score 5-7% error on
migration mapping vs 98-100% when they "improve" slugs to be SEO-friendly.

5 cases: each gives source text + transformation instruction + required-
verbatim tokens. Scored by literal substring presence post-transform.
"""
from __future__ import annotations
import json
import sys, io
import time
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"

CASES = [
    {
        "id": "invoice_id_in_translation",
        "system": "You are a translator. Translate to English. Preserve all identifiers and codes EXACTLY as given.",
        "user": "Traduci: 'Per favore invia la fattura FT-2025-0042 entro venerdì.'",
        "must_contain_exact": ["FT-2025-0042"],
    },
    {
        "id": "url_path_in_summary",
        "system": "You are a technical writer. Summarize in one sentence. Preserve URL paths exactly.",
        "user": "Endpoint /api/v2/users/{id}/invoices?format=json returns list.",
        "must_contain_exact": ["/api/v2/users/{id}/invoices", "format=json"],
    },
    {
        "id": "placeholder_in_rewrite",
        "system": "Rewrite the sentence more formally. Keep all placeholders unchanged.",
        "user": "Hey, your code <<<TOKEN_ABC>>> expires at {{ts}}.",
        "must_contain_exact": ["<<<TOKEN_ABC>>>", "{{ts}}"],
    },
    {
        "id": "version_string_in_explanation",
        "system": "Explain in Italian what this means. Preserve version strings exactly.",
        "user": "Update to nginx-1.27.3-alpine3.20 deprecates SSLv3.",
        "must_contain_exact": ["nginx-1.27.3-alpine3.20", "SSLv3"],
    },
    {
        "id": "regex_in_translation",
        "system": "Translate the description to German. Preserve regex and code literally.",
        "user": "The regex ^[A-Z]{2}\\d{4}$ matches our format.",
        "must_contain_exact": ["^[A-Z]{2}\\d{4}$"],
    },
]


def run_case(c: dict) -> dict:
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "lit",
        "messages": [
            {"role": "system", "content": c["system"]},
            {"role": "user", "content": c["user"]},
        ],
        "max_tokens": 256,
        "temperature": 0.1,
        "seed": 42,
    }, timeout=120)
    dt = time.time() - t0
    text = r.json()["choices"][0]["message"]["content"]
    hits = [t in text for t in c["must_contain_exact"]]
    pass_n = sum(hits)
    n = len(hits)
    verdict = "PASS" if pass_n == n else ("PARTIAL" if pass_n > 0 else "FAIL")
    return {
        "id": c["id"], "verdict": verdict, "pass": f"{pass_n}/{n}",
        "missing": [t for t, h in zip(c["must_contain_exact"], hits) if not h],
        "output": text[:200],
        "dt_s": round(dt, 2),
    }


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("=== LITERAL PRESERVATION bench ===")
    results = []
    for c in CASES:
        r = run_case(c)
        results.append(r)
        print(f"  {r['id']:38s} {r['verdict']:7s} {r['pass']}  ({r['dt_s']}s)")
        if r["missing"]:
            print(f"     MISSING: {r['missing']}")
    p = sum(1 for r in results if r["verdict"] == "PASS")
    print(f"\nTOTAL PASS: {p}/{len(results)}")
    from pathlib import Path
    Path("sweep_bench_literal_preservation_result.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
