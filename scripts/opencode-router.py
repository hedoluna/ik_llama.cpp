#!/usr/bin/env python
"""OpenCode local router shim.

OpenAI-compatible reverse proxy that sits in FRONT of llama-swap and, when the
incoming request asks for the synthetic model id ``auto`` (or ``llama-swap/auto``),
picks a concrete local model with a hybrid policy:

  L1  fast deterministic gate  (override / big-ctx / trivial / italian / hard / coder)
  L2  classifier fallback      (an always-hot qwen-small instance on its own port)

A per-session sticky policy avoids thrashing between the 35B variants (each big
swap relaunches a llama-server process even when the GGUF is warm in page cache).

Stdlib only. Launch with:  py D:\\repos\\ik_llama.cpp\\scripts\\opencode-router.py

The routing brain (``route`` / ``classify`` / helpers and the CONFIG block) is
importable without starting the server, so it can be unit-tested offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ===================== CONFIG (tune AFTER real data) =====================
LISTEN_HOST, LISTEN_PORT = "127.0.0.1", 8291
SWAP_BASE = "http://127.0.0.1:8292"
CLASSIFIER_BASE = "http://127.0.0.1:9998"
CLASSIFIER_MODEL = "qwen-small"
LOG_DIR = r"D:\repos\ik_llama.cpp\bench-opencode-local"

AUTO_IDS = {"auto", "llama-swap/auto"}
SWAP_PREFIX = "llama-swap/"
CHARS_PER_TOKEN = 4

# Input-context budget per model (tokens). Used by the context guard.
MODEL_CTX = {
    "qwen-small": 32768, "qwen36-iq3": 32768, "qwen-coder": 32768,
    "qwen36-opus-iq4": 24576, "qwen36-q5": 24576, "qwen-opus-q8": 24576,
    "cerbero-ita": 16384, "granite-fast": 16384, "gpt-oss-20b": 24576,
}
CTX_SAFETY_FRAC = 0.75
TRIVIAL_TOKENS = 60
BIG_CONTEXT_TOKENS = 18000
AMBIGUOUS_LOW = 60
AMBIGUOUS_HIGH = 400

LABEL_MODEL = {
    "TRIVIAL": "qwen-small", "NORMAL": "qwen36-iq3", "HARD": "qwen36-opus-iq4",
    "CODER": "qwen-coder", "ITALIAN": "cerbero-ita",
}
DEFAULT_MODEL = "qwen36-iq3"
BIG_CAPABLE_MODEL = "qwen36-iq3"   # 32k window, used when context is huge
SMALL_MODEL = "qwen-small"

HARD_KEYWORDS = [
    "refactor", "redesign", "architecture", "architettura", "design pattern",
    "race condition", "deadlock", "concurrency", "concorrenza", "optimi", "profil",
    "benchmark", "rewrite", "migrate", "migrazione", "root cause", "thread-safe",
    "memory leak", "complessit", "big-o", "prove that", "dimostra", "why is this slow",
]
CODER_KEYWORDS = [
    "diff", "apply patch", "unified diff", "write the full file", "full file",
    "implement", "codegen", "generate code", "scaffold", "boilerplate",
]
OVERRIDE_TOKENS = {
    "!small": "qwen-small", "!fast": "qwen-small", "!coding": "qwen36-iq3",
    "!normal": "qwen36-iq3", "!quality": "qwen36-opus-iq4", "!hard": "qwen36-opus-iq4",
    "!max": "qwen-opus-q8", "!coder": "qwen-coder", "!ita": "cerbero-ita",
    "!italian": "cerbero-ita",
}

CLASSIFY_TIMEOUT_S = 4.0
# Single socket timeout for the upstream forward. urllib applies one timeout to
# the whole operation, and a NON-streaming llama-server sends nothing until the
# full completion is ready -> this must cover cold model load (llama-swap
# relaunches a llama-server, ~20-40s) PLUS the entire generation. A dead PORT
# still fails instantly (connection refused), so a generous value is safe locally.
UPSTREAM_TIMEOUT = 900.0

BIG_MODELS = {
    "qwen36-iq3", "qwen36-opus-iq4", "qwen36-q5", "qwen-opus-q8",
    "qwen-coder", "gpt-oss-20b",
}
STICKY_TURNS_TTL_S = 1800
# ========================================================================

_LOCK = threading.Lock()
_STICKY = {}        # session -> {"model": str, "ts": float}
_MODELS_CACHE = {"ts": 0.0, "body": None}
_LOGPATH = None     # set on server start; None => stdout only (e.g. unit tests)


# ----------------------------- helpers ----------------------------------

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _join_parts(content):
    """Flatten OpenAI message content that may be a string or a list of parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict):
                out.append(part.get("text") or part.get("content") or "")
            elif isinstance(part, str):
                out.append(part)
        return "\n".join(out)
    return ""


def gather_text(body):
    """All text in the request (system+user+assistant) for token estimation."""
    msgs = body.get("messages")
    if isinstance(msgs, list):
        return "\n".join(_join_parts(m.get("content")) for m in msgs if isinstance(m, dict))
    return _join_parts(body.get("prompt", ""))


def last_user_text(body):
    msgs = body.get("messages")
    if isinstance(msgs, list):
        for m in reversed(msgs):
            if isinstance(m, dict) and m.get("role") == "user":
                return _join_parts(m.get("content"))
    return _join_parts(body.get("prompt", ""))


def count_file_parts(body):
    n = 0
    msgs = body.get("messages")
    if isinstance(msgs, list):
        for m in msgs:
            content = m.get("content") if isinstance(m, dict) else None
            if isinstance(content, list):
                n += sum(1 for p in content if isinstance(p, dict) and p.get("type") == "file")
    return n


def estimate_tokens(text):
    return max(1, len(text) // CHARS_PER_TOKEN)


def has_code_fence(text):
    return "```" in text or bool(re.search(r"\b(def |class |function |=>)|;\s*$", text))


def looks_italian(text):
    markers = (
        "perché", "perche", "ciao", "grazie", "quindi", "funzione", "spiega",
        "scrivi", "codice", "errore", "come posso", "vorrei", "dammi", "puoi",
        "traduci", "riassumi", "spiegami",
    )
    low = text.lower()
    return sum(1 for w in markers if w in low) >= 2 and not has_code_fence(text)


# --------------------------- L2 classifier ------------------------------

CLASSIFY_SYS = (
    "You are a router. Output EXACTLY ONE label, nothing else, from: "
    "TRIVIAL NORMAL HARD CODER ITALIAN. "
    "TRIVIAL=greeting/tiny. NORMAL=ordinary coding/Q&A. "
    "HARD=deep reasoning/refactor/architecture/tricky debug. "
    "CODER=bulk code/diffs/full-file. ITALIAN=request written in Italian."
)
FEWSHOT = [
    ("hi there", "TRIVIAL"),
    ("what does ^\\d+$ do", "NORMAL"),
    ("refactor this module to remove the race condition and explain why", "HARD"),
    ("write the full LRU cache implementation as a unified diff", "CODER"),
    ("scrivimi una funzione fattoriale e spiega come funziona", "ITALIAN"),
]
VALID_LABELS = {"TRIVIAL", "NORMAL", "HARD", "CODER", "ITALIAN"}


def classify(user_text):
    """Return (label, elapsed_ms). On any error/slowness return ('NORMAL', ms)."""
    msgs = [{"role": "system", "content": CLASSIFY_SYS}]
    for u, a in FEWSHOT:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": user_text[:2000]})
    payload = json.dumps({
        "model": CLASSIFIER_MODEL, "messages": msgs,
        "temperature": 0, "max_tokens": 5, "stream": False,
    }).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(
            CLASSIFIER_BASE + "/v1/chat/completions", data=payload, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=CLASSIFY_TIMEOUT_S) as r:
            out = json.loads(r.read())
        raw = (out["choices"][0]["message"]["content"] or "").strip().upper()
        label = next((v for v in VALID_LABELS if v in raw), "NORMAL")
        return label, (time.time() - t0) * 1000.0
    except Exception:
        return "NORMAL", (time.time() - t0) * 1000.0


# ----------------------------- routing ----------------------------------

def _commit(hint, toks, model, tier, reason, gate, ms,
            allow_small=False, escalate=False):
    """Apply per-session sticky anti-thrash, then the context guard."""
    sess = (hint or {}).get("session") or "anon"
    now = time.time()
    with _LOCK:
        st = _STICKY.get(sess)
        if st and now - st["ts"] > STICKY_TURNS_TTL_S:
            st = None
        prev = st["model"] if st else None
        if (prev in BIG_MODELS and model in BIG_MODELS
                and model != prev and not escalate and not allow_small):
            model = prev
            reason += "|sticky->%s" % prev
        elif prev in BIG_MODELS and model == SMALL_MODEL and not allow_small:
            model = prev
            reason += "|sticky-keepbig"
        # Remember the active BIG model for the session.
        remember = model if model in BIG_MODELS else (prev or model)
        _STICKY[sess] = {"model": remember, "ts": now}
    # Context guard: never send more than the model can hold.
    if (toks > MODEL_CTX.get(model, 32768) * CTX_SAFETY_FRAC
            and MODEL_CTX[BIG_CAPABLE_MODEL] > MODEL_CTX.get(model, 32768)):
        model = BIG_CAPABLE_MODEL
        reason += "|ctx-bump"
    return model, tier, reason, gate, ms


def route(body, hint=None):
    """Pure routing decision. Returns (model, tier, reason, gate, classify_ms)."""
    hint = hint or {}
    full = gather_text(body)
    user = last_user_text(body)
    toks = estimate_tokens(full)
    low = user.lower().strip()

    # Explicit manual override anywhere in the user text.
    for tok, m in OVERRIDE_TOKENS.items():
        if low.startswith(tok) or (" " + tok) in low:
            return _commit(hint, toks, m, "L1", "override %s" % tok, "gate", 0.0,
                           allow_small=(m == SMALL_MODEL), escalate=(m in BIG_MODELS))
    # Huge context must go to a 32k-capable model.
    if toks >= BIG_CONTEXT_TOKENS:
        return _commit(hint, toks, BIG_CAPABLE_MODEL, "L1", "bigctx~%d" % toks,
                       "gate", 0.0, escalate=True)
    # Hard coding/reasoning keywords -> escalate to quality.
    # NOTE: checked BEFORE the trivial-by-length rule because a SHORT prompt can
    # still be hard ("refactor to remove the deadlock" is ~14 tokens).
    if any(k in low for k in HARD_KEYWORDS):
        return _commit(hint, toks, LABEL_MODEL["HARD"], "L1", "hard-kw", "gate", 0.0,
                       escalate=True)
    # Bulk-code keywords -> coder specialist (also before trivial).
    if any(k in low for k in CODER_KEYWORDS):
        return _commit(hint, toks, LABEL_MODEL["CODER"], "L1", "coder-kw", "gate", 0.0)
    # Trivial short prompt with no code.
    if toks <= TRIVIAL_TOKENS and not has_code_fence(user):
        return _commit(hint, toks, SMALL_MODEL, "L1", "trivial", "gate", 0.0,
                       allow_small=True)
    # Italian natural-language request.
    if looks_italian(user):
        return _commit(hint, toks, LABEL_MODEL["ITALIAN"], "L1", "italian", "gate", 0.0)
    # Ambiguous mid-length prompt -> ask the classifier.
    if AMBIGUOUS_LOW < toks < AMBIGUOUS_HIGH:
        label, ms = classify(user)
        m = LABEL_MODEL.get(label, DEFAULT_MODEL)
        return _commit(hint, toks, m, "L2", "label=%s" % label, "classifier", ms,
                       allow_small=(label == "TRIVIAL"), escalate=(label == "HARD"))
    return _commit(hint, toks, DEFAULT_MODEL, "L1", "default-normal", "gate", 0.0)


def session_key(body, hint):
    if hint and hint.get("session"):
        return hint["session"]
    first = ""
    msgs = body.get("messages")
    if isinstance(msgs, list):
        for m in msgs:
            if isinstance(m, dict) and m.get("role") == "user":
                first = _join_parts(m.get("content"))
                break
    agent = (hint or {}).get("agent") or ""
    return hashlib.sha1((first + "|" + agent).encode("utf-8", "ignore")).hexdigest()[:8]


# ------------------------------ logging ---------------------------------

def log_decision(record):
    line = json.dumps(record, ensure_ascii=False)
    if _LOGPATH:
        with _LOCK:
            try:
                with open(_LOGPATH, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass
    else:
        print(line)


# ------------------------------ server ----------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"   # keep-alive + chunked streaming

    def log_message(self, *args):   # silence default stderr access log
        pass

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/v1/models", "/models"):
            return self._models()
        if path == "/healthz":
            return self._send_json(200, {"ok": True})
        return self._send_json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path in ("/v1/chat/completions", "/v1/completions"):
            return self._chat(path)
        return self._send_json(404, {"error": "not found"})

    def _models(self):
        now = time.time()
        with _LOCK:
            fresh = _MODELS_CACHE["body"] if now - _MODELS_CACHE["ts"] < 5 else None
        if fresh is None:
            try:
                with urllib.request.urlopen(SWAP_BASE + "/v1/models", timeout=5) as r:
                    data = json.loads(r.read())
            except Exception:
                data = {"object": "list", "data": []}
            data.setdefault("data", [])
            if not any(m.get("id") == "auto" for m in data["data"]):
                data["data"].insert(0, {
                    "id": "auto", "object": "model",
                    "owned_by": "router", "created": int(now),
                })
            fresh = json.dumps(data).encode()
            with _LOCK:
                _MODELS_CACHE["ts"] = now
                _MODELS_CACHE["body"] = fresh
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(fresh)))
        self.end_headers()
        try:
            self.wfile.write(fresh)
        except Exception:
            pass

    def _chat(self, path):
        n = _safe_int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw)
        except Exception:
            return self._send_json(400, {"error": "bad json"})

        req = (body.get("model") or "").strip()
        bare = req[len(SWAP_PREFIX):] if req.startswith(SWAP_PREFIX) else req
        t0 = time.time()

        if req in AUTO_IDS or bare == "auto":
            hint = {
                "agent": self.headers.get("x-route-agent"),
                "files": _safe_int(self.headers.get("x-route-files")),
                "session": self.headers.get("x-route-session"),
            }
            hint["session"] = session_key(body, hint)
            chosen, tier, reason, gate, cms = route(body, hint)
            body["model"] = chosen
            self._emit_log(hint, body, chosen, tier, reason, gate, cms, t0)
        else:
            chosen = bare
            body["model"] = bare
            self._emit_log({"session": None}, body, chosen, "bypass",
                           "explicit", "-", 0.0, t0)

        self._forward(path, json.dumps(body).encode(), bool(body.get("stream")))

    def _emit_log(self, hint, body, chosen, tier, reason, gate, cms, t0):
        log_decision({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "session": hint.get("session"),
            "model_chosen": chosen,
            "tier": tier,
            "reason": reason,
            "gate_or_classifier": gate,
            "prompt_tokens_est": estimate_tokens(gather_text(body)),
            "classify_ms": round(cms, 1),
            "total_ms": round((time.time() - t0) * 1000.0, 1),
        })

    def _forward(self, path, raw, stream):
        req = urllib.request.Request(
            SWAP_BASE + path, data=raw, method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json",
            })
        try:
            resp = urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT)
        except urllib.error.HTTPError as e:
            b = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            try:
                self.wfile.write(b)
            except Exception:
                pass
            return
        except Exception as e:
            return self._send_json(502, {"error": "upstream: %s" % e})

        ctype = resp.headers.get(
            "Content-Type", "text/event-stream" if stream else "application/json")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if stream:
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    self.wfile.write(b"%X\r\n" % len(chunk) + chunk + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # client aborted -> stop the upstream generation
            finally:
                resp.close()
        else:
            try:
                d = resp.read()
            except Exception as e:
                resp.close()
                return self._send_json(504, {"error": "upstream read: %s" % e})
            resp.close()
            self.send_header("Content-Length", str(len(d)))
            self.end_headers()
            try:
                self.wfile.write(d)
            except Exception:
                pass


def main():
    global _LOGPATH
    os.makedirs(LOG_DIR, exist_ok=True)
    _LOGPATH = os.path.join(LOG_DIR, "router-%s.jsonl" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print("opencode-router listening on http://%s:%d  (auto -> %s upstream)"
          % (LISTEN_HOST, LISTEN_PORT, SWAP_BASE))
    print("log: %s" % _LOGPATH)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
