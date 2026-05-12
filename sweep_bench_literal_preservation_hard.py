#!/usr/bin/env python3
"""sweep_bench_literal_preservation_hard.py — slug-rewrite trap HARD variant.

Variante hard del literal_preservation: NO istruzione esplicita "preserve
exactly". Vediamo se il modello rispetta autonomamente i token literal
quando gli si chiede traduzione/parafrasi.

Discrimina: modello consapevole della preservazione semantica vs modello
che "migliora" autonomamente (slug-rewrite trap dell'articolo glukhov).
"""
from __future__ import annotations
import json
import sys, io
import time
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"

CASES = [
    {
        "id": "invoice_id_translation_NO_HINT",
        "system": "Sei un traduttore. Traduci dall'italiano all'inglese.",
        "user": "Per favore invia la fattura FT-2025-0042 entro venerdì.",
        "must_contain_exact": ["FT-2025-0042"],
    },
    {
        "id": "url_path_summary_NO_HINT",
        "system": "Sei un technical writer. Riassumi in una frase.",
        "user": "L'endpoint /api/v2/users/{id}/invoices?format=json ritorna una lista.",
        "must_contain_exact": ["/api/v2/users/{id}/invoices", "format=json"],
    },
    {
        "id": "placeholder_rewrite_NO_HINT",
        "system": "Riscrivi la frase in modo più formale.",
        "user": "Ehi, il tuo codice <<<TOKEN_ABC>>> scade alle {{ts}}.",
        "must_contain_exact": ["<<<TOKEN_ABC>>>", "{{ts}}"],
    },
    {
        "id": "version_string_explain_NO_HINT",
        "system": "Spiega in italiano cosa significa questo.",
        "user": "Update to nginx-1.27.3-alpine3.20 deprecates SSLv3.",
        "must_contain_exact": ["nginx-1.27.3-alpine3.20", "SSLv3"],
    },
    {
        "id": "regex_translation_NO_HINT",
        "system": "Traduci la descrizione in tedesco.",
        "user": "The regex ^[A-Z]{2}\\d{4}$ matches our format.",
        "must_contain_exact": ["^[A-Z]{2}\\d{4}$"],
    },
    {
        "id": "sku_in_marketing_NO_HINT",
        "system": "Riscrivi questa descrizione prodotto in modo più accattivante.",
        "user": "Maglietta SKU-RC-44231-XL, 100% cotone.",
        "must_contain_exact": ["SKU-RC-44231-XL"],
    },
    {
        "id": "commit_hash_summary_NO_HINT",
        "system": "Riassumi questo cambio in una frase.",
        "user": "Il commit 7a3f9e2bc ha refactorato la classe DatabasePool.",
        "must_contain_exact": ["7a3f9e2bc", "DatabasePool"],
    },
]


def run_case(c: dict) -> dict:
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "lit-hard",
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
    print("=== LITERAL PRESERVATION HARD bench (no explicit hint) ===")
    results = []
    for c in CASES:
        r = run_case(c)
        results.append(r)
        print(f"  {r['id']:40s} {r['verdict']:7s} {r['pass']}  ({r['dt_s']}s)")
        if r["missing"]:
            print(f"     MISSING: {r['missing']}")
            print(f"     OUTPUT:  {r['output'][:140]}")
    p = sum(1 for r in results if r["verdict"] == "PASS")
    part = sum(1 for r in results if r["verdict"] == "PARTIAL")
    print(f"\nTOTAL PASS: {p}/{len(results)}  PARTIAL: {part}  FAIL: {len(results)-p-part}")
    from pathlib import Path
    Path("sweep_bench_literal_preservation_hard_result.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
