#!/usr/bin/env python
"""End-to-end integration test for the router cloud tier.

Starts the real router Handler on an ephemeral port and drives a !cloud request
through the full path: _chat -> resolve_target -> _forward -> NVIDIA NIM.
Also asserts the no-key 400 guard. Local (llama-swap) path is NOT exercised here.

Requires a working NVIDIA_API_KEY (env or D:\\repos\\.env) and network.
Run:  py scripts/test-router-cloud-integration.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def load_key():
    k = os.environ.get("NVIDIA_API_KEY", "").strip()
    if k:
        return k
    envfile = r"D:\repos\.env"
    if os.path.exists(envfile):
        for line in open(envfile, encoding="utf-8", errors="ignore"):
            if line.strip().startswith("NVIDIA_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


def load_router(with_key):
    # Module reads NVIDIA_API_KEY at import time -> set env before loading.
    os.environ["NVIDIA_API_KEY"] = load_key() if with_key else ""
    spec = importlib.util.spec_from_file_location(
        "opencode_router_%s" % with_key, os.path.join(HERE, "opencode-router.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def serve(mod):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def post(port, body, timeout=120):
    req = urllib.request.Request(
        "http://127.0.0.1:%d/v1/chat/completions" % port,
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %-34s %s" % (name, detail))
    else:
        FAIL += 1
        print("  FAIL %-34s %s" % (name, detail))


if not load_key():
    print("SKIP: no NVIDIA_API_KEY available")
    raise SystemExit(0)

print("== cloud path WITH key ==")
mod = load_router(with_key=True)
srv, port = serve(mod)
try:
    code, resp = post(port, {
        "model": "auto",
        "messages": [{"role": "user", "content": "!kimi reply with exactly: PONG"}],
        "max_tokens": 16, "stream": False,
    })
    content = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content", "") if code == 200 else ""
    used_model = resp.get("model", "")
    check("cloud-200", code == 200, "http %s" % code)
    check("cloud-real-model-id", "kimi" in used_model.lower(), "model=%s" % used_model)
    check("cloud-got-content", bool(content.strip()), repr(content.strip()[:40]))
finally:
    srv.shutdown()

print("== no-key guard returns 400 ==")
mod0 = load_router(with_key=False)
srv0, port0 = serve(mod0)
try:
    code, resp = post(port0, {
        "model": "nvidia-kimi",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
    }, timeout=10)
    check("nokey-400", code == 400, "http %s" % code)
    check("nokey-msg", "NVIDIA_API_KEY" in json.dumps(resp), json.dumps(resp)[:60])
finally:
    srv0.shutdown()

print("\n%d passed, %d failed" % (PASS, FAIL))
raise SystemExit(1 if FAIL else 0)
