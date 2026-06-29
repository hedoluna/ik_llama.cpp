#!/usr/bin/env python
"""Live bench for the NVIDIA NIM cloud tier used by the OpenCode router.

Reads NVIDIA_API_KEY from env or D:\\repos\\.env, confirms the catalog id of each
CLOUD_MODELS alias actually serves, then measures latency + tokens/s on a small
chat completion. No third-party deps. Run:  py scripts/bench-nvidia-cloud.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "opencode_router", os.path.join(HERE, "opencode-router.py"))
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


def load_key():
    k = os.environ.get("NVIDIA_API_KEY", "").strip()
    if k:
        return k, "env"
    envfile = r"D:\repos\.env"
    if os.path.exists(envfile):
        for line in open(envfile, encoding="utf-8", errors="ignore"):
            if line.strip().startswith("NVIDIA_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"'), envfile
    return "", None


def get_models(root, key):
    req = urllib.request.Request(
        root + "/v1/models", headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return {m.get("id") for m in json.loads(r.read()).get("data", [])}


def bench_one(root, key, real_id, prompt, max_tokens=64):
    payload = json.dumps({
        "model": real_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.2, "stream": False,
    }).encode()
    req = urllib.request.Request(
        root + "/v1/chat/completions", data=payload, method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "err": "HTTP %s: %s" % (e.code, e.read()[:200].decode("utf-8", "ignore"))}
    except Exception as e:
        return {"ok": False, "err": str(e)[:200]}
    dt = time.time() - t0
    usage = out.get("usage") or {}
    ctoks = usage.get("completion_tokens") or 0
    content = ((out.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return {
        "ok": True, "latency_s": round(dt, 2),
        "completion_tokens": ctoks,
        "tok_per_s": round(ctoks / dt, 1) if dt > 0 and ctoks else None,
        "snippet": content.strip().replace("\n", " ")[:60],
    }


def main():
    key, src = load_key()
    root = R.NVIDIA_ROOT
    print("root: %s" % root)
    if not key:
        print("NO KEY: set NVIDIA_API_KEY or add it to D:\\repos\\.env")
        return 1
    print("key:  ...%s (from %s)" % (key[-6:], src))

    try:
        catalog = get_models(root, key)
        print("catalog models served: %d" % len(catalog))
    except Exception as e:
        print("FAILED to list models: %s" % e)
        catalog = set()

    print("\n%-16s %-42s %-7s %-8s %-7s %-7s" %
          ("alias", "real_id", "served", "lat_s", "ctoks", "tok/s"))
    print("-" * 96)
    results = []
    for alias, real in R.CLOUD_MODELS.items():
        served = "yes" if real in catalog else ("?" if not catalog else "NO")
        b = bench_one(root, key, real, "Reply with exactly: OK then count 1 to 5.")
        if b["ok"]:
            print("%-16s %-42s %-7s %-8s %-7s %-7s | %s" % (
                alias, real, served, b["latency_s"], b["completion_tokens"],
                b["tok_per_s"], b["snippet"]))
        else:
            print("%-16s %-42s %-7s ERROR: %s" % (alias, real, served, b["err"]))
        results.append((alias, real, served, b))

    # Tool-use probe on the default model (agentic OpenCode needs function calling).
    print("\n-- tool-use probe (default %s) --" % R.CLOUD_DEFAULT)
    tool_real = R.CLOUD_MODELS[R.CLOUD_DEFAULT]
    tool_payload = json.dumps({
        "model": tool_real,
        "messages": [{"role": "user", "content": "What is the weather in Rome? Use the tool."}],
        "tools": [{"type": "function", "function": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {"type": "object", "properties": {
                "city": {"type": "string"}}, "required": ["city"]}}}],
        "tool_choice": "auto", "max_tokens": 64, "stream": False,
    }).encode()
    req = urllib.request.Request(
        root + "/v1/chat/completions", data=tool_payload, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
        msg = ((out.get("choices") or [{}])[0].get("message") or {})
        tc = msg.get("tool_calls")
        print("tool_calls returned: %s" % (
            "YES -> " + tc[0]["function"]["name"] if tc else "no (model answered in text)"))
    except urllib.error.HTTPError as e:
        print("tool probe HTTP %s: %s" % (e.code, e.read()[:200].decode("utf-8", "ignore")))
    except Exception as e:
        print("tool probe error: %s" % str(e)[:200])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
