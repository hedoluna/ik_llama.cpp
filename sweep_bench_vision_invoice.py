#!/usr/bin/env python3
"""sweep_bench_vision_invoice.py — vision-OCR bench for Italian invoices.

Riusa pipeline apcore (D:\\repos\\apcore):
- Prompt: packages/api/src/prompts/extraction.txt
- Fixtures: packages/api/test-fixtures/benchmark-{sgam,fiorucci}.jpg
- Ground truth: estratto da packages/web/public/benchmark.html
- Schema: types.ts InvoiceDataSchema (9 campi)
- Scorer: match esatto + math consistency net+tax=total ±0.01

Target server: già-running llama-server con `--mmproj` flag. Script invia
image via OpenAI content array. Scarta lineItems (out of scope MVP).
"""
from __future__ import annotations
import base64
import json
import re
import sys, io
import time
from pathlib import Path
import requests

APCORE = Path(r"D:\repos\apcore\packages\api")
# Sanitized prompt (no SGAM/Fiorucci literals — prevents prompt-leak hallucination)
SANITIZED_PROMPT = Path(r"D:\repos\ik_llama.cpp\bench_vision\extraction_sanitized.txt")
PROMPT_PATH = SANITIZED_PROMPT if SANITIZED_PROMPT.exists() else APCORE / "src" / "prompts" / "extraction.txt"
FIXTURES = {
    "sgam": APCORE / "test-fixtures" / "benchmark-sgam.jpg",
    "fiorucci": APCORE / "test-fixtures" / "benchmark-fiorucci.jpg",
}

GROUND_TRUTH = {
    "sgam": {
        "supplierName": "SGAM SpA",
        "supplierVat": "IT01315810612",
        "invoiceNumber": "128.969/2025",
        "invoiceDate": "2025-08-11",
        "totalAmount": "3554.17",
        "taxAmount": "640.92",
        "netAmount": "2913.25",
        "currency": "EUR",
    },
    "fiorucci": {
        "supplierName": "Fiorucci S.p.A.",
        "supplierVat": "IT11980969",
        "invoiceNumber": "3511054052",
        "invoiceDate": "2025-08-11",
        "totalAmount": "996.19",
        "taxAmount": "90.56",
        "netAmount": "905.63",
        "currency": "EUR",
    },
}

URL = "http://127.0.0.1:1234/v1/chat/completions"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def image_to_dataurl(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def extract_json(text: str) -> dict | None:
    if not text:
        return None
    # try ```json fenced
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = m.group(1) if m else None
    if not candidate:
        # find first { ... } balanced
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    break
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _normalize_amount(s: str) -> str | None:
    """Try to normalize italian/intl amount format.
    "3.554,17" -> "3554.17"; "3554.17" -> "3554.17"; "3554,17" -> "3554.17"
    """
    s = s.strip().replace(" ", "")
    if not s:
        return None
    # If contains both . and , : the rightmost separator is decimal
    if "." in s and "," in s:
        if s.rindex(",") > s.rindex("."):
            # italian: dots=thousands, comma=decimal
            s = s.replace(".", "").replace(",", ".")
        else:
            # intl: commas=thousands, dot=decimal
            s = s.replace(",", "")
    elif "," in s:
        # only comma → assume decimal
        s = s.replace(",", ".")
    # else only dot or none → leave
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return None


def score_field(got: str | None, expected: str, field: str = "") -> tuple[bool, str]:
    if got is None:
        return False, "missing"
    g = str(got).strip()
    e = expected.strip()
    if g == e:
        return True, "exact"
    if g.lower() == e.lower():
        return True, "case-insens"
    # Amount normalization for numeric fields
    if field in ("totalAmount", "taxAmount", "netAmount"):
        gn = _normalize_amount(g)
        en = _normalize_amount(e)
        if gn is not None and en is not None and gn == en:
            return True, f"normalized {g!r}->{gn}"
    return False, f"got={g!r}"


def math_consistent(got: dict) -> bool:
    try:
        n = float(got.get("netAmount", "0"))
        t = float(got.get("taxAmount", "0"))
        T = float(got.get("totalAmount", "0"))
        return abs((n + t) - T) <= 0.01
    except Exception:
        return False


def run_one(fixture_name: str, model_label: str) -> dict:
    prompt = load_prompt()
    image_path = FIXTURES[fixture_name]
    data_url = image_to_dataurl(image_path)
    payload = {
        "model": model_label,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        "max_tokens": 2048,
        "temperature": 0.1,
        "seed": 42,
    }
    t0 = time.time()
    try:
        r = requests.post(URL, json=payload, timeout=600)
        dt = time.time() - t0
        data = r.json()
    except Exception as e:
        return {"fixture": fixture_name, "error": str(e), "dt_s": round(time.time()-t0, 2)}
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = extract_json(text)
    gt = GROUND_TRUTH[fixture_name]
    if parsed is None:
        return {"fixture": fixture_name, "dt_s": round(dt, 2),
                "score": 0, "of": len(gt), "math_ok": False,
                "verdict": "JSON_PARSE_FAIL", "raw_preview": text[:300]}
    scores = {}
    correct = 0
    for k, expected in gt.items():
        ok, note = score_field(parsed.get(k), expected, field=k)
        scores[k] = {"ok": ok, "note": note, "expected": expected}
        if ok:
            correct += 1
    return {
        "fixture": fixture_name, "dt_s": round(dt, 2),
        "score": correct, "of": len(gt),
        "math_ok": math_consistent(parsed),
        "scores": scores,
        "raw_json": parsed,
    }


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    label = sys.argv[1] if len(sys.argv) > 1 else "vision"
    print(f"=== VISION INVOICE BENCH ({label}) ===")
    results = []
    for fname in FIXTURES:
        r = run_one(fname, label)
        results.append(r)
        if "error" in r:
            print(f"  {fname:10s} ERROR ({r['dt_s']}s): {r['error']}")
            continue
        if r.get("verdict") == "JSON_PARSE_FAIL":
            print(f"  {fname:10s} JSON_PARSE_FAIL ({r['dt_s']}s)")
            print(f"     preview: {r['raw_preview'][:200]}")
            continue
        print(f"  {fname:10s} {r['score']}/{r['of']} math={r['math_ok']} ({r['dt_s']}s)")
        for k, s in r["scores"].items():
            mark = "✓" if s["ok"] else "✗"
            note = "" if s["ok"] else f" expected={s['expected']!r} {s['note']}"
            print(f"     {mark} {k}{note}")
    total_correct = sum(r.get("score", 0) for r in results)
    total = sum(r.get("of", 0) for r in results)
    print(f"\nTOTAL: {total_correct}/{total}")
    out = Path(f"sweep_bench_vision_invoice_{label}.json")
    out.write_text(json.dumps({"label": label, "results": results,
                                "total_correct": total_correct, "total": total},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
