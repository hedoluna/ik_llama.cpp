#!/usr/bin/env python3
"""sweep_mode_toolcall.py — mini tool-use bench.

3 function specs sent via OpenAI tools API. Verify the model:
  1. Emits a tool_calls array (not plain text)
  2. Uses the correct function name
  3. Provides valid JSON arguments parseable + matching expected keys
"""
from __future__ import annotations
import json
import time
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform arithmetic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["add", "sub", "mul", "div"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["op", "a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_invoice",
            "description": "Fetch an invoice from the database by number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "year": {"type": "integer"},
                },
                "required": ["invoice_number"],
            },
        },
    },
]

CASES = [
    ("Che tempo fa a Milano? Usa Celsius.", "get_weather",
     {"city": "Milano", "unit": "celsius"}),
    ("Quanto fa 47 moltiplicato per 13?", "calculator",
     {"op": "mul", "a": 47, "b": 13}),
    ("Trova la fattura numero FT-2025-0042 dell'anno 2025.", "query_invoice",
     {"invoice_number": "FT-2025-0042", "year": 2025}),
]


def run_case(text: str, want_fn: str, want_args: dict) -> dict:
    payload = {
        "model": "toolcall",
        "messages": [
            {"role": "system", "content": "Sei un assistente. Usa le funzioni quando rilevanti."},
            {"role": "user", "content": text},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": 256,
        "temperature": 0.0,
        "seed": 42,
    }
    t0 = time.time()
    r = requests.post(URL, json=payload, timeout=60)
    dt = time.time() - t0
    try:
        data = r.json()
    except Exception as e:
        return {"text": text, "err": str(e), "dt": dt}
    msg = data["choices"][0]["message"]
    tc = msg.get("tool_calls")
    if not tc:
        return {"text": text, "got_text": msg.get("content"), "verdict": "FAIL_NO_TOOLCALL", "dt": round(dt, 2)}
    call = tc[0]
    fn_name = call.get("function", {}).get("name")
    raw_args = call.get("function", {}).get("arguments", "")
    try:
        got_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except Exception:
        got_args = None
    name_ok = (fn_name == want_fn)
    args_ok = isinstance(got_args, dict) and all(
        str(got_args.get(k)).lower() == str(v).lower() for k, v in want_args.items()
    )
    verdict = "PASS" if (name_ok and args_ok) else ("FAIL_ARGS" if name_ok else "FAIL_NAME")
    return {
        "text": text, "want_fn": want_fn, "got_fn": fn_name,
        "want_args": want_args, "got_args": got_args,
        "verdict": verdict, "dt": round(dt, 2),
    }


def main():
    print("=== TOOL-USE mini-bench (3 cases) ===")
    results = []
    for text, want_fn, want_args in CASES:
        r = run_case(text, want_fn, want_args)
        results.append(r)
        print(f"  {r['verdict']:18s} {r['dt']}s  want={want_fn}  got={r.get('got_fn')}")
        print(f"    want_args: {r.get('want_args')}")
        print(f"    got_args:  {r.get('got_args')}")
    pass_n = sum(1 for r in results if r["verdict"] == "PASS")
    print(f"\nTOTAL: {pass_n}/{len(results)} PASS")
    from pathlib import Path
    (Path(__file__).parent / "sweep_mode_toolcall_result.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
