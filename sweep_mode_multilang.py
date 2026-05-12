#!/usr/bin/env python3
"""sweep_mode_multilang.py — translation probe outside Italian.

Tests Coder-1.5B on:
  - EN→DE (mainstream EU)
  - EN→ZH (cross-script, Qwen training)
  - EN→IT (control, expected to pass)

3 prompts each. Scorer: lightweight keyword presence check (each target
language has 2-3 anchor terms expected in the translation).
"""
from __future__ import annotations
import json
import time
import requests

URL = "http://127.0.0.1:1234/v1/chat/completions"

CASES = [
    # (source_en, target_lang, anchor_terms_lowercase)
    ("The quick brown fox jumps over the lazy dog.", "German",
     [["fuchs"], ["springt", "spring"], ["hund"]]),
    ("Please send the invoice by Friday at noon.", "German",
     [["rechnung"], ["freitag"], ["mittag", "12"]]),
    ("Machine learning models require labeled data.", "German",
     [["maschinell", "machine"], ["modell"], ["daten"]]),

    ("The quick brown fox jumps over the lazy dog.", "Chinese (Simplified)",
     [["狐"], ["跳"], ["狗"]]),
    ("Please send the invoice by Friday at noon.", "Chinese (Simplified)",
     [["发票"], ["星期五", "周五"], ["中午", "12"]]),
    ("Machine learning models require labeled data.", "Chinese (Simplified)",
     [["机器学习", "机器"], ["模型"], ["数据"]]),

    ("The quick brown fox jumps over the lazy dog.", "Italian",
     [["volpe"], ["salta"], ["cane"]]),
    ("Please send the invoice by Friday at noon.", "Italian",
     [["fattura"], ["venerd"], ["mezzogiorno", "12"]]),
    ("Machine learning models require labeled data.", "Italian",
     [["apprendimento", "machine"], ["modell"], ["dati"]]),
]


def run_case(src: str, target: str, anchors: list[list[str]]) -> dict:
    payload = {
        "model": "ml",
        "messages": [
            {"role": "system", "content": f"You are a translator. Translate to {target}. Output ONLY the translation, no commentary."},
            {"role": "user", "content": src},
        ],
        "max_tokens": 128,
        "temperature": 0.1,
        "seed": 42,
    }
    t0 = time.time()
    r = requests.post(URL, json=payload, timeout=60)
    dt = time.time() - t0
    text = r.json()["choices"][0]["message"]["content"].lower()
    hits = sum(1 for grp in anchors if any(a in text for a in grp))
    verdict = "PASS" if hits == len(anchors) else ("PARTIAL" if hits > 0 else "FAIL")
    return {
        "src": src, "target": target, "got": text[:120],
        "anchors_hit": f"{hits}/{len(anchors)}",
        "verdict": verdict, "dt": round(dt, 2),
    }


def main():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("=== MULTILINGUAL probe ===")
    results = []
    for src, target, anchors in CASES:
        r = run_case(src, target, anchors)
        results.append(r)
        print(f"  [{r['target'][:10]:10s}] {r['verdict']:7s} {r['anchors_hit']}  ({r['dt']}s)")
        print(f"     got: {r['got']}")
    # summary by language
    print("\n=== SUMMARY ===")
    for tgt in ["German", "Chinese (Simplified)", "Italian"]:
        cases = [r for r in results if r["target"] == tgt]
        p = sum(1 for r in cases if r["verdict"] == "PASS")
        part = sum(1 for r in cases if r["verdict"] == "PARTIAL")
        print(f"  {tgt:25s} PASS {p}/{len(cases)}  partial={part}")
    from pathlib import Path
    (Path(__file__).parent / "sweep_mode_multilang_result.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
