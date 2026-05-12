#!/usr/bin/env python3
"""sweep_ts_ab.py — A/B 4 TS scripts su 5 modelli (4 51/51 nuovi + daily winner).

Each model: start server, run vanilla+recipe variants of each script, parse score X/Y, kill.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import sweep_small_models as ssm

TS_SCRIPTS = [
    ("tanstack", Path(r"D:\repos\ik_llama.cpp\test_tanstack_ab.py"), ["vanilla", "recipe"]),
    ("useinvoices", Path(r"D:\repos\ik_llama.cpp\test_useinvoices_ab.py"), ["vanilla", "recipe"]),
    ("zod", Path(r"D:\repos\ik_llama.cpp\test_zod_ab.py"), ["vanilla"]),  # zod uses extra_checks, single variant
    ("asynciter", Path(r"D:\repos\ik_llama.cpp\test_asynciter_ab.py"), ["vanilla"]),
]

# Models: 4 nuovi 51/51 + ex champion Qwen3-4B + daily winner Qwen3.6
MODELS = [
    ("Qwen2.5-Coder-1.5B-Q4_K_M",
     ssm.MODELS_CACHE / "migarcoes" / "Qwen-Qwen2.5-Coder-1.5B-Instruct" / "Qwen-Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf",
     "ik", []),
    ("Qwen2.5-Coder-3B-Q4_0",
     ssm.MODELS_CACHE / "Qwen" / "Qwen2.5-Coder-3B-Instruct-GGUF" / "qwen2.5-coder-3b-instruct-q4_0.gguf",
     "ik", []),
    ("granite-4.1-3B-Q4_K_S",
     ssm.MODELS_CACHE / "unsloth" / "granite-4.1-3b-GGUF" / "granite-4.1-3b-Q4_K_S.gguf",
     "main", []),
    ("Qwen3-4B-Instruct-2507-Q4_K_M",
     ssm.MODELS_CACHE / "lmstudio-community" / "Qwen3-4B-Instruct-2507-GGUF" / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
     "ik", []),
]

# Daily winner has dedicated config (partial offload, different model path)
DAILY_WINNER = (
    "Qwen3.6-35B-A3B-IQ3_K_R4",
    Path(r"D:\repos\ik_llama.cpp\models\Qwen3.6-35B-A3B-IQ3_K_R4.gguf"),
    "ik",
    ["--reasoning", "off", "-c", "24000", "-ngl", "95", "--n-cpu-moe", "30",
     "-b", "2048", "-ub", "2048", "-ctk", "q4_0", "-ctv", "q8_0"],
)

LEADERBOARD = ssm.REPO / "sweep_ts_ab_leaderboard.json"


def start_server_custom(label: str, path: Path, runtime: str, extra: list[str]) -> subprocess.Popen | None:
    """Variant of ssm.start_server that lets extra override base flags for daily winner."""
    if not path.exists():
        return None
    bin_path = ssm.IK_SERVER if runtime == "ik" else ssm.MAIN_SERVER
    if not bin_path.exists():
        return None
    # If extra contains -c/-ngl flags, use them directly (daily winner case); else use defaults
    has_c = any(f == "-c" for f in extra)
    base = [str(bin_path), "--model", str(path),
            "--host", ssm.HOST, "--port", str(ssm.PORT),
            "--jinja",
            "-fa", "on", "-t", "8", "--no-mmap"]
    if not has_c:
        base += ["-c", "16384", "-ngl", "999"]
    cmd = base + extra
    log = ssm.REPO / f"sweep_ts_log_{label}.txt"
    log_f = open(log, "w", encoding="utf-8")
    return subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)


def parse_score(output: str) -> dict:
    m = re.search(r"score:\s*(\d+)/(\d+)", output)
    t = re.search(r"elapsed:\s*([\d.]+)s", output)
    miss = re.search(r"missing:\s*\[(.*?)\]", output)
    return {
        "score": int(m.group(1)) if m else None,
        "total": int(m.group(2)) if m else None,
        "elapsed": float(t.group(1)) if t else None,
        "missing": miss.group(1) if miss else "",
    }


def run_script(script_path: Path, label: str, variant: str) -> dict:
    cp = subprocess.run(
        [ssm.PY_CMD, str(script_path), "--label", label, "--variant", variant,
         "--url", f"http://{ssm.HOST}:{ssm.PORT}"],
        capture_output=True, text=True, timeout=600,
    )
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    return parse_score(out), out


def run_one_model(label: str, path: Path, runtime: str, extra: list[str]) -> dict:
    ssm.kill_llama_server()
    t0 = time.time()
    proc = start_server_custom(label, path, runtime, extra)
    if not proc:
        return {"label": label, "status": "skip_missing"}
    if not ssm.wait_server_ready(ssm.HOST, ssm.PORT, max_wait=240):
        proc.terminate(); ssm.kill_llama_server()
        return {"label": label, "status": "load_failed", "load_time": time.time() - t0}
    load_t = time.time() - t0
    print(f"  loaded in {load_t:.1f}s — running {sum(len(v) for _,_,v in TS_SCRIPTS)} script-variants ...")
    results = []
    for name, script, variants in TS_SCRIPTS:
        for variant in variants:
            try:
                parsed, out = run_script(script, label, variant)
                key = f"{name}_{variant}"
                results.append({"task": key, **parsed})
                print(f"    {key:30s} -> {parsed.get('score','?')}/{parsed.get('total','?')} ({parsed.get('elapsed','?')}s)")
            except subprocess.TimeoutExpired:
                results.append({"task": f"{name}_{variant}", "score": None, "status": "timeout"})
    ssm.kill_llama_server()
    total_score = sum(r.get("score") or 0 for r in results)
    total_max = sum(r.get("total") or 0 for r in results)
    total_time = sum(r.get("elapsed") or 0 for r in results)
    return {
        "label": label, "status": "ok",
        "load_time": round(load_t, 2),
        "total_score": total_score, "total_max": total_max,
        "total_time_s": round(total_time, 2),
        "per_task": results,
    }


def main():
    results = []
    if LEADERBOARD.exists():
        results = json.loads(LEADERBOARD.read_text())

    all_models = MODELS + [DAILY_WINNER]
    for entry in all_models:
        label, path, rt, extra = entry
        print(f"\n=== TS A/B: {label} ===")
        r = run_one_model(label, path, rt, extra)
        r["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        results.append(r)
        LEADERBOARD.write_text(json.dumps(results, indent=2))

    print("\n=== SUMMARY ===")
    for r in results[-len(all_models):]:
        print(f"  {r['label']:42s} -> {r.get('total_score','?')}/{r.get('total_max','?')}  time={r.get('total_time_s','?')}s  status={r.get('status')}")


if __name__ == "__main__":
    main()
