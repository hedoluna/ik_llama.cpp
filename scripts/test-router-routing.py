#!/usr/bin/env python
"""Offline unit tests for the opencode-router routing brain.

No network: the L2 classifier is monkeypatched. Run with:
    py D:\\repos\\ik_llama.cpp\\scripts\\test-router-routing.py
Exit code 0 = all pass.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "opencode_router", os.path.join(HERE, "opencode-router.py"))
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)

PASS, FAIL = 0, 0


def reset_sticky():
    with R._LOCK:
        R._STICKY.clear()


def body_of(text):
    return {"messages": [{"role": "user", "content": text}], "model": "auto"}


def check(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        print("  ok   %-32s -> %s" % (name, got))
    else:
        FAIL += 1
        print("  FAIL %-32s -> %s (want %s)" % (name, got, want))


def case(name, text, want_model, want_tier, session=None, mock_label=None):
    if mock_label is not None:
        R.classify = lambda u, _l=mock_label: (_l, 1.0)
    hint = {"session": session} if session else {}
    model, tier, reason, gate, ms = R.route(body_of(text), hint)
    check(name, (model, tier), (want_model, want_tier))


print("== L1 gate ==")
reset_sticky()
case("trivial-en", "hi there", "nemotron-fast", "L1")

reset_sticky()
case("trivial-ciao", "ciao", "nemotron-fast", "L1")

reset_sticky()
italian = ("Per favore spiegami nel dettaglio come funziona questa parte di codice "
           "e scrivimi un riassunto chiaro in italiano, grazie. Vorrei capire quindi "
           "perche viene usato questo approccio e cosa succede passo dopo passo nel "
           "flusso generale del programma cosi posso documentarlo meglio.")
case("italian-long", italian, "minerva-ita", "L1")

reset_sticky()
case("hard-short", "refactor this module to remove the deadlock and explain why",
     "ornith-35b-iq3-imat", "L1")

reset_sticky()
case("coder-kw", "apply patch: add error handling to each function",
     "mellum2-instruct", "L1")

reset_sticky()
bigctx = body_of("x " * 40000)   # ~80k chars -> ~20k tokens
m, t, _, _, _ = R.route(bigctx, {"session": "big"})
check("bigctx", (m, t), ("daily-Qwen3.6-35B-A3B-IQ3_K_R4", "L1"))

print("== overrides ==")
reset_sticky()
case("override-coder", "!coder write a parser", "mellum2-instruct", "L1")

print("== cloud tier (NVIDIA, opt-in) ==")
reset_sticky()
case("cloud-default", "!cloud summarize this whole repo", R.CLOUD_DEFAULT, "cloud")
reset_sticky()
case("cloud-kimi", "!kimi explain the architecture", "nvidia-kimi", "cloud")
reset_sticky()
case("cloud-inline", "please !deepseek review this design", "nvidia-deepseek", "cloud")
# resolve_target: cloud alias -> NVIDIA root + real catalog id + bearer header shape
b, real, hdr = R.resolve_target("nvidia-kimi")
check("resolve-cloud-base", b, R.NVIDIA_ROOT)
check("resolve-cloud-realid", real, R.CLOUD_MODELS["nvidia-kimi"])
check("resolve-cloud-no-double-v1", b.endswith("/v1"), False)
# local model -> swap base, id unchanged, no auth header
b2, real2, hdr2 = R.resolve_target("qwen36-iq3")
check("resolve-local-base", b2, R.SWAP_BASE)
check("resolve-local-realid", real2, "qwen36-iq3")
check("resolve-local-no-auth", hdr2, {})

print("== L2 classifier (mocked) ==")
ambiguous = ("I have a piece of logic that processes incoming records and updates "
             "several counters based on their category, then writes a summary to disk. "
             "Something seems off with how the totals are computed across batches and I "
             "want your opinion on the overall approach before I change anything here.")
reset_sticky()
case("l2-normal", ambiguous, "qwen36-iq3", "L2", session="a", mock_label="NORMAL")
reset_sticky()
case("l2-hard", ambiguous, "ornith-35b-iq3-imat", "L2", session="b", mock_label="HARD")
reset_sticky()
case("l2-trivial", ambiguous, "nemotron-fast", "L2", session="c", mock_label="TRIVIAL")

print("== sticky anti-thrash ==")
reset_sticky()
# First turn HARD -> ornith-35b-iq3-imat; second turn (same session) classifies NORMAL -> iq3,
# but sticky must KEEP ornith-35b-iq3-imat (BIG->BIG without escalation).
R.classify = lambda u: ("HARD", 1.0)
m1, _, _, _, _ = R.route(body_of("refactor the scheduler to fix the race condition"),
                         {"session": "S"})
check("sticky-turn1", m1, "ornith-35b-iq3-imat")
R.classify = lambda u: ("NORMAL", 1.0)
m2, _, r2, _, _ = R.route(body_of(ambiguous), {"session": "S"})
check("sticky-turn2-keepbig", m2, "ornith-35b-iq3-imat")

# Different session is independent.
reset_sticky()
R.classify = lambda u: ("NORMAL", 1.0)
m3, _, _, _, _ = R.route(body_of(ambiguous), {"session": "T"})
check("sticky-other-session", m3, "qwen36-iq3")

print("== nonstream SSE adapter ==")
completion = {
    "id": "chatcmpl-test",
    "created": 123,
    "model": "granite-fast",
    "choices": [{
        "message": {"role": "assistant", "content": "ciao"},
        "finish_reason": "stop",
    }],
    "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
}
chunks = [c.decode("utf-8") for c in R.chat_completion_to_sse_chunks(completion, "fallback")]
check("sse-start-role", '"role":"assistant"' in chunks[0], True)
check("sse-text", '"content":"ciao"' in "".join(chunks), True)
check("sse-usage", '"total_tokens":3' in "".join(chunks), True)
check("sse-done", chunks[-1], "data: [DONE]\n\n")

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
