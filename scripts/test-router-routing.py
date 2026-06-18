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
case("trivial-en", "hi there", "qwen-small", "L1")

reset_sticky()
case("trivial-ciao", "ciao", "qwen-small", "L1")

reset_sticky()
italian = ("Per favore spiegami nel dettaglio come funziona questa parte di codice "
           "e scrivimi un riassunto chiaro in italiano, grazie. Vorrei capire quindi "
           "perche viene usato questo approccio e cosa succede passo dopo passo nel "
           "flusso generale del programma cosi posso documentarlo meglio.")
case("italian-long", italian, "cerbero-ita", "L1")

reset_sticky()
case("hard-short", "refactor this module to remove the deadlock and explain why",
     "qwen36-opus-iq4", "L1")

reset_sticky()
case("coder-kw", "apply patch: add error handling to each function",
     "qwen-coder", "L1")

reset_sticky()
bigctx = body_of("x " * 40000)   # ~80k chars -> ~20k tokens
m, t, _, _, _ = R.route(bigctx, {"session": "big"})
check("bigctx", (m, t), ("qwen36-iq3", "L1"))

print("== overrides ==")
reset_sticky()
case("override-max", "!max design a quick thing", "qwen-opus-q8", "L1")
reset_sticky()
case("override-coder", "!coder write a parser", "qwen-coder", "L1")

print("== L2 classifier (mocked) ==")
ambiguous = ("I have a piece of logic that processes incoming records and updates "
             "several counters based on their category, then writes a summary to disk. "
             "Something seems off with how the totals are computed across batches and I "
             "want your opinion on the overall approach before I change anything here.")
reset_sticky()
case("l2-normal", ambiguous, "qwen36-iq3", "L2", session="a", mock_label="NORMAL")
reset_sticky()
case("l2-hard", ambiguous, "qwen36-opus-iq4", "L2", session="b", mock_label="HARD")
reset_sticky()
case("l2-trivial", ambiguous, "qwen-small", "L2", session="c", mock_label="TRIVIAL")

print("== sticky anti-thrash ==")
reset_sticky()
# First turn HARD -> opus-iq4; second turn (same session) classifies NORMAL -> iq3,
# but sticky must KEEP opus-iq4 (BIG->BIG without escalation).
R.classify = lambda u: ("HARD", 1.0)
m1, _, _, _, _ = R.route(body_of("refactor the scheduler to fix the race condition"),
                         {"session": "S"})
check("sticky-turn1", m1, "qwen36-opus-iq4")
R.classify = lambda u: ("NORMAL", 1.0)
m2, _, r2, _, _ = R.route(body_of(ambiguous), {"session": "S"})
check("sticky-turn2-keepbig", m2, "qwen36-opus-iq4")

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
