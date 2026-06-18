#!/usr/bin/env python3
"""Deterministic smoke + tool-use gate for local OpenAI-compatible profiles.

This is intentionally small and dependency-free. It verifies that a concrete
profile can:
  1. answer a deterministic smoke prompt with non-degenerate content;
  2. emit OpenAI `message.tool_calls` for a small set of function-calling cases.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_URL = "http://127.0.0.1:8292/v1/chat/completions"


@dataclass(frozen=True)
class ToolCase:
    id: str
    prompt: str
    want_fn: str
    want_args: dict[str, Any]


TOOLS: list[dict[str, Any]] = [
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
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a support ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["title", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_customer",
            "description": "Search a CRM customer by email.",
            "parameters": {
                "type": "object",
                "properties": {"email": {"type": "string"}},
                "required": ["email"],
            },
        },
    },
]


CASES: list[ToolCase] = [
    ToolCase("weather_milan", "Che tempo fa a Milano? Usa Celsius.", "get_weather",
             {"city": "Milano", "unit": "celsius"}),
    ToolCase("math_mul", "Quanto fa 47 moltiplicato per 13?", "calculator",
             {"op": "mul", "a": 47, "b": 13}),
    ToolCase("invoice_lookup", "Trova la fattura numero FT-2025-0042 dell'anno 2025.",
             "query_invoice", {"invoice_number": "FT-2025-0042", "year": 2025}),
    ToolCase("support_ticket", "Apri un ticket urgente: backup database fallito.",
             "create_ticket", {"priority": "high"}),
    ToolCase("customer_search", "Cerca il cliente con email mario.rossi@example.com.",
             "search_customer", {"email": "mario.rossi@example.com"}),
]


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read()
    return json.loads(body), time.time() - t0


def first_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    message = choices[0].get("message")
    return message if isinstance(message, dict) else {}


def normalize_scalar(value: Any) -> str:
    return str(value).strip().lower()


def evaluate_tool_response(case: ToolCase, message: dict[str, Any], elapsed_s: float) -> dict[str, Any]:
    tool_calls = message.get("tool_calls")
    if not tool_calls:
        text = message.get("content")
        return {
            "id": case.id,
            "pass": False,
            "verdict": "FAIL_NO_TOOLCALL",
            "want_fn": case.want_fn,
            "got_fn": None,
            "got_text": text,
            "elapsed_s": round(elapsed_s, 2),
        }

    call = tool_calls[0] if isinstance(tool_calls, list) else {}
    function = call.get("function", {}) if isinstance(call, dict) else {}
    fn_name = function.get("name")
    raw_args = function.get("arguments", "")

    try:
        got_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except (TypeError, json.JSONDecodeError):
        return {
            "id": case.id,
            "pass": False,
            "verdict": "FAIL_BAD_ARGS_JSON",
            "want_fn": case.want_fn,
            "got_fn": fn_name,
            "raw_args": raw_args,
            "elapsed_s": round(elapsed_s, 2),
        }

    if fn_name != case.want_fn:
        return {
            "id": case.id,
            "pass": False,
            "verdict": "FAIL_NAME",
            "want_fn": case.want_fn,
            "got_fn": fn_name,
            "got_args": got_args,
            "elapsed_s": round(elapsed_s, 2),
        }

    if not isinstance(got_args, dict):
        got_args = {}

    wrong = [
        key for key, want in case.want_args.items()
        if normalize_scalar(got_args.get(key)) != normalize_scalar(want)
    ]
    verdict = "PASS" if not wrong else "FAIL_ARGS"
    return {
        "id": case.id,
        "pass": not wrong,
        "verdict": verdict,
        "want_fn": case.want_fn,
        "got_fn": fn_name,
        "want_args": case.want_args,
        "got_args": got_args,
        "missing_or_wrong": wrong,
        "elapsed_s": round(elapsed_s, 2),
    }


def run_smoke(url: str, model: str, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Rispondi solo con OK, senza spiegazioni."}],
        "max_tokens": 32,
        "temperature": 0,
        "min_p": 0,
        "top_p": 1,
        "seed": 42,
        "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        response, elapsed = post_json(url, payload, timeout)
        message = first_message(response)
        content = str(message.get("content") or "").strip()
        ok = content in {"OK", "OK."}
        return {
            "pass": ok,
            "verdict": "PASS" if ok else "FAIL_CONTENT",
            "content": content,
            "elapsed_s": round(elapsed, 2),
            "usage": response.get("usage"),
        }
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"pass": False, "verdict": "FAIL_REQUEST", "error": str(exc)}


def run_tool_case(url: str, model: str, case: ToolCase, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Sei un assistente. Usa le funzioni quando rilevanti."},
            {"role": "user", "content": case.prompt},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": 256,
        "temperature": 0,
        "seed": 42,
    }
    try:
        response, elapsed = post_json(url, payload, timeout)
        return evaluate_tool_response(case, first_message(response), elapsed)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "id": case.id,
            "pass": False,
            "verdict": "FAIL_REQUEST",
            "want_fn": case.want_fn,
            "error": str(exc),
        }


def run_gate(url: str, model: str, timeout: int) -> dict[str, Any]:
    smoke = run_smoke(url, model, timeout)
    tool_results = [run_tool_case(url, model, case, timeout) for case in CASES]
    tool_pass = sum(1 for item in tool_results if item["pass"])
    passed = smoke["pass"] and tool_pass == len(tool_results)
    return {
        "model": model,
        "url": url,
        "status": "pass" if passed else "fail",
        "smoke": smoke,
        "tool_use": {
            "passed": tool_pass,
            "total": len(tool_results),
            "results": tool_results,
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_gate(args.url, args.model, args.timeout)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "model": result["model"],
        "status": result["status"],
        "smoke": result["smoke"]["verdict"],
        "tool_use": f"{result['tool_use']['passed']}/{result['tool_use']['total']}",
    }, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
