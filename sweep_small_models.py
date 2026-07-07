#!/usr/bin/env python3
"""sweep_small_models.py — bottom-up sweep of small LM Studio models on coding bench.

Usage:
  py sweep_small_models.py --tier 0   # ultra-small only
  py sweep_small_models.py --models <path1> <path2> ...

For each model:
  1. Start ik_llama llama-server.exe on :1234 with full GPU offload (-ngl 999)
  2. Poll /v1/models until ready
  3. Run coding_benchmark.py against it
  4. Parse "X/51" + total_time from output
  5. Kill server, wait port release
  6. Append row to sweep_leaderboard.json
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(r"D:\repos\ik_llama.cpp")
IK_SERVER = REPO / "build" / "bin" / "Release" / "llama-server.exe"
MAIN_SERVER = Path(r"D:\repos\llama_mtp\build\bin\Release\llama-server.exe")
BENCH = Path(r"D:\repos\ralph\local_ralph\coding_benchmark.py")
BENCH_ADV = Path(r"D:\repos\ralph\local_ralph\advanced_benchmark.py")
EXEC_TRACE = Path(r"D:\repos\ik-llama-bench\sweep_bench_exec_trace.py")
LEADERBOARD = REPO / "sweep_leaderboard.json"
PORT = 1234
HOST = "127.0.0.1"

MODELS_CACHE = Path(r"F:\01_Modelli_AI\LLM_Models\lm-studio\models")  # moved 2026-06 from F:\LLM_Models\...

# Tier 0..3 candidates. Format: (label, gguf_path, runtime, extra_flags)
TIERS = {
    0: [  # ultra-small 0.5-0.6B
        ("Qwen2.5-Coder-0.5B-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "Qwen2.5-Coder-0.5B-Instruct-GGUF" / "Qwen2.5-Coder-0.5B-Instruct-Q4_K_M.gguf",
         "ik", []),
        ("Qwen3-0.6B-Q8_0",
         MODELS_CACHE / "lmstudio-community" / "Qwen3-0.6B-GGUF" / "Qwen3-0.6B-Q8_0.gguf",
         "ik", []),
    ],
    1: [  # small coder 1.3-1.5B
        ("deepseek-coder-1.3B-kexer-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "deepseek-coder-1.3B-kexer-GGUF" / "deepseek-coder-1.3B-kexer-Q4_K_M.gguf",
         "ik", []),
        ("Yi-Coder-1.5B-Chat-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "Yi-Coder-1.5B-Chat-GGUF" / "Yi-Coder-1.5B-Chat-Q4_K_M.gguf",
         "ik", []),
        ("Qwen2.5-Coder-1.5B-Q4_K_M",
         MODELS_CACHE / "migarcoes" / "Qwen-Qwen2.5-Coder-1.5B-Instruct" / "Qwen-Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf",
         "ik", []),
        ("Qwen2.5-Coder-1.5B-bartowski-Q4_K_M",
         MODELS_CACHE / "bartowski" / "Qwen2.5-Coder-1.5B-Instruct-GGUF" / "Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf",
         "ik", []),
        ("DeepCoder-1.5B-Preview-Q8_0",
         MODELS_CACHE / "lmstudio-community" / "DeepCoder-1.5B-Preview-GGUF" / "DeepCoder-1.5B-Preview-Q8_0.gguf",
         "ik", []),
    ],
    2: [  # small general 1-2B
        ("gemma-3-1B-it-qat-Q4_0",
         MODELS_CACHE / "lmstudio-community" / "gemma-3-1B-it-qat-GGUF" / "gemma-3-1B-it-QAT-Q4_0.gguf",
         "ik", []),
        ("SmolLM2-1.7B-Instruct-Q8_0",
         MODELS_CACHE / "RichardErkhov" / "HuggingFaceTB_-_SmolLM2-1.7B-Instruct-gguf" / "SmolLM2-1.7B-Instruct.Q8_0.gguf",
         "ik", []),
        ("gemma-2-2b-it-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "gemma-2-2b-it-GGUF" / "gemma-2-2b-it-Q4_K_M.gguf",
         "ik", []),
        ("granite-3.3-2b-instruct-Q6_K",
         MODELS_CACHE / "lmstudio-community" / "granite-3.3-2b-instruct-GGUF" / "granite-3.3-2b-instruct-Q6_K.gguf",
         "main", []),  # granite bug on ik_llama (memory lesson)
    ],
    3: [  # mid 3-4B
        ("Qwen2.5-Coder-3B-Q4_0",
         MODELS_CACHE / "Qwen" / "Qwen2.5-Coder-3B-Instruct-GGUF" / "qwen2.5-coder-3b-instruct-q4_0.gguf",
         "ik", []),
        ("stable-code-instruct-3B-Q6_K",
         MODELS_CACHE / "bartowski" / "stable-code-instruct-3b-GGUF" / "stable-code-instruct-3b-Q6_K.gguf",
         "ik", []),
        ("granite-4.1-3B-Q4_K_S",
         MODELS_CACHE / "unsloth" / "granite-4.1-3b-GGUF" / "granite-4.1-3b-Q4_K_S.gguf",
         "main", []),
        ("Phi-3.5-mini-Q4_K_S",
         MODELS_CACHE / "bartowski" / "Phi-3.5-mini-instruct-GGUF" / "Phi-3.5-mini-instruct-Q4_K_S.gguf",
         "ik", []),
        ("Phi-4-mini-reasoning-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "Phi-4-mini-reasoning-GGUF" / "Phi-4-mini-reasoning-Q4_K_M.gguf",
         "main", []),
        ("Ministral-3-3B-2512-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "Ministral-3-3B-Instruct-2512-GGUF" / "Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
         "ik", []),
        ("Hermes-3-Llama-3.2-3B-Q4_K_M",
         MODELS_CACHE / "NousResearch" / "Hermes-3-Llama-3.2-3B-GGUF" / "Hermes-3-Llama-3.2-3B.Q4_K_M.gguf",
         "ik", []),
    ],
    4: [  # 7-9B (advanced bench challengers — Granite 4.1 8B, Qwen3.5 family)
        ("Qwen3.5-0.8B-Q8_0",
         MODELS_CACHE / "lmstudio-community" / "Qwen3.5-0.8B-GGUF" / "Qwen3.5-0.8B-Q8_0.gguf",
         "ik", []),
        ("granite-4.0-h-tiny-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "granite-4.0-h-tiny-GGUF" / "granite-4.0-h-tiny-Q4_K_M.gguf",
         "main", []),
        ("granite-4.1-8B-Q4_K_S",
         MODELS_CACHE / "unsloth" / "granite-4.1-8b-GGUF" / "granite-4.1-8b-Q4_K_S.gguf",
         "main", []),
        ("Qwen3.5-9B-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "Qwen3.5-9B-GGUF" / "Qwen3.5-9B-Q4_K_M.gguf",
         "ik", []),
    ],
    6: [  # Qwen3-Coder-Next 80B-A3B MoE (massive download, --cpu-moe required)
        ("Qwen3-Coder-Next-UD-Q2_K_XL",
         MODELS_CACHE / "unsloth" / "Qwen3-Coder-Next-GGUF" / "Qwen3-Coder-Next-UD-Q2_K_XL.gguf",
         "ik", ["--cpu-moe"]),
    ],
    5: [  # Gemma 4 family
        ("gemma-4-E2B-it-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "gemma-4-E2B-it-GGUF" / "gemma-4-E2B-it-Q4_K_M.gguf",
         "ik", []),
        ("gemma-4-E4B-it-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "gemma-4-E4B-it-GGUF" / "gemma-4-E4B-it-Q4_K_M.gguf",
         "ik", []),
        ("gemma-4-26B-A4B-it-Q4_K_M",
         MODELS_CACHE / "lmstudio-community" / "gemma-4-26B-A4B-it-GGUF" / "gemma-4-26B-A4B-it-Q4_K_M.gguf",
         "ik", ["--cpu-moe"]),
        ("gemma-4-26B-A4B-it-qat-UD-Q4_K_XL",
         MODELS_CACHE / "gemma" / "gemma-4-26b-it" / "gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf",
         "ik", ["--cpu-moe", "--reasoning", "off", "-ctk", "q8_0", "-ctv", "q8_0"]),
    ],
    7: [  # Ornith-1.0 (deepreinforce, qwen3_5 RL) vs daily winner — identical flags, 2026-06-29
        ("daily-Qwen3.6-35B-A3B-IQ3_K_R4",
         Path(r"D:\repos\ik_llama.cpp\models\Qwen3.6-35B-A3B-IQ3_K_R4.gguf"),
         "ik", ["-ngl", "95", "--n-cpu-moe", "30", "--reasoning", "off",
                "-ctk", "q4_0", "-ctv", "q8_0", "-b", "1024", "-ub", "256"]),
        ("Ornith-1.0-35B-A3B-Q4_K_M",
         Path(r"F:\01_Modelli_AI\LLM_Models\Ornith\ornith-1.0-35b-Q4_K_M.gguf"),
         "ik", ["-ngl", "80", "--n-cpu-moe", "30", "--reasoning", "off",
                "-ctk", "q4_0", "-ctv", "q8_0", "-b", "1024", "-ub", "256"]),
        ("Ornith-1.0-9B-Q4_K_M",
         Path(r"D:\repos\ik_llama.cpp\models\ornith-1.0-9b-Q4_K_M.gguf"),
         "ik", ["--reasoning", "off", "-ctk", "q4_0", "-ctv", "q8_0"]),
        ("Ornith-1.0-35B-A3B-IQ3_K_R4",
         Path(r"D:\repos\ik_llama.cpp\models\ornith-1.0-35b-IQ3_K_R4.gguf"),
         "ik", ["-ngl", "95", "--n-cpu-moe", "30", "--reasoning", "off",
                "-ctk", "q4_0", "-ctv", "q8_0", "-b", "1024", "-ub", "256"]),
        ("Ornith-1.0-35B-A3B-IQ3_K_R4-imat",
         Path(r"D:\repos\ik_llama.cpp\models\ornith-1.0-35b-IQ3_K_R4-imat.gguf"),
         "ik", ["-ngl", "95", "--n-cpu-moe", "30", "--reasoning", "off",
                "-ctk", "q4_0", "-ctv", "q8_0", "-b", "1024", "-ub", "256"]),
        # Qwen2.5-Coder-32B-Instruct-IQ3_M removed 2026-07-07: dense 32B forces
        # -ngl 15 (only 15 layers fit 6 GiB VRAM) — 23+ min for the 17-task
        # advanced bench alone. Confirms the known hardware ceiling: dense >12B
        # impractical on this rig. Re-add only for a dedicated quality run.
        # DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M removed 2026-07-07: "drop coding"
        # verdict in reference_model_matrix_consolidated (A33 11/33, no patch-format
        # training) + repeated 900s+ timeouts with zero score, twice historically and
        # again mid-run this session. Pure time cost, no signal — do not re-add
        # without a specific reason to re-evaluate it.
        ("Mellum2-12B-A2.5B-Instruct-Q4_K_M",
         Path(r"D:\repos\ik_llama.cpp\models\Mellum2-12B-A2.5B-Instruct-Q4_K_M.gguf"),
         "ik", ["-ngl", "99", "--n-cpu-moe", "12", "--reasoning", "off"]),
    ],
}

PY_CMD = next((p for p in [
    r"D:\repos\trading-algo\.venv-py312\Scripts\python.exe",
    r"C:\Python313\python.exe",
    r"C:\Python312\python.exe",
    r"C:\Python39\python.exe",
] if Path(p).exists()), sys.executable)


def run_preflight() -> None:
    """Fail-fast if coding_benchmark's scorer misjudges known-good solutions.

    Session 2026-05-12 found the scorer itself wrong more than once
    (antiglaze/vision_invoice/extract_function bugs), producing false model
    fails. Gate every sweep run on it instead of trusting single-sample output.
    """
    sys.path.insert(0, str(REPO))
    from sweep_lib_sanity import preflight_scorer
    spec = importlib.util.spec_from_file_location("cb", BENCH)
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)
    preflight_scorer(cb)


def port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def wait_port_free(host: str, port: int, max_wait: int = 30) -> bool:
    """Wait until port is no longer accepting connections."""
    t0 = time.time()
    while time.time() - t0 < max_wait:
        if not port_open(host, port, 0.3):
            return True
        time.sleep(0.5)
    return False


def wait_server_ready(host: str, port: int, max_wait: int = 120) -> bool:
    """Poll /v1/models until 200 OK or timeout."""
    url = f"http://{host}:{port}/v1/models"
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def kill_llama_server() -> None:
    """Kill any llama-server.exe process."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe"],
                       capture_output=True, timeout=10)
    except Exception:
        pass
    wait_port_free(HOST, PORT, max_wait=20)


def start_server(label: str, model_path: Path, runtime: str, extra: list[str]) -> subprocess.Popen | None:
    if not model_path.exists():
        print(f"  [SKIP] missing model: {model_path}")
        return None
    bin_path = IK_SERVER if runtime == "ik" else MAIN_SERVER
    if not bin_path.exists():
        print(f"  [SKIP] missing server bin: {bin_path}")
        return None
    cmd = [
        str(bin_path),
        "--model", str(model_path),
        "--host", HOST, "--port", str(PORT),
        "--jinja",
        "-c", "16384",
        "-fa", "on",
        "-t", "8",
        "--no-mmap",
    ]
    if not any(arg in ["-ngl", "--n-gpu-layers"] for arg in extra):
        cmd += ["-ngl", "999"]
    cmd += extra
    log_path = REPO / f"sweep_log_{label}.txt"
    log_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    return proc


def parse_bench_output(output: str) -> dict:
    """Extract pass/total + total_time + valid from coding_benchmark.py stdout."""
    # Format: "Test totali: X/Y" and "Tempo totale: Zs" and "RISULTATO: [OK] VALIDO" / "[X] SCARTATO"
    tot_m = re.search(r"Test totali:\s*(\d+)/(\d+)", output)
    time_m = re.search(r"Tempo totale:\s*([\d.]+)s", output)
    risultato = re.search(r"RISULTATO:\s*\[(OK|X)\]\s*(\w+)", output)
    # Per-task pass counts (PASS lines like "[PASS] - 8/8 test")
    pass_lines = re.findall(r"\[(PASS|FAIL)\]\s*-\s*(\d+)/(\d+)\s*test\s*\(([\d.]+)s\)", output)
    per_task = [{"verdict": v, "passed": int(p), "total": int(t), "time_s": float(s)}
                for v, p, t, s in pass_lines]
    # Compute true totals from per-task (fixes denominator bug when "Nessun codice generato")
    true_passed = sum(t["passed"] for t in per_task) if per_task else None
    true_total = sum(t["total"] for t in per_task) if per_task else None  # bench-reported denom
    # Expected max if every task had all test cases attempted = 8+6+5+6+6+6+8+6 = 51
    EXPECTED_MAX = 51
    return {
        "passed": int(tot_m.group(1)) if tot_m else true_passed,
        "total": int(tot_m.group(2)) if tot_m else true_total,
        "passed_of_51": true_passed,
        "total_time_s": float(time_m.group(1)) if time_m else None,
        "valid_for_coding": bool(risultato and risultato.group(1) == "OK"),
        "per_task": per_task,
    }


def parse_exec_trace_output(output: str) -> dict | None:
    """Parse '== exec_trace: X/N ==' summary line. None if the script errored."""
    m = re.search(r"==\s*exec_trace:\s*(\d+)/(\d+)\s*==", output)
    if not m:
        return None
    return {"exec_trace_passed": int(m.group(1)), "exec_trace_total": int(m.group(2))}


def run_exec_trace(label: str) -> dict:
    """Run the exec_trace 'easy' tier against the already-running server on :1234.

    Coding-bench accuracy saturates at 51/51 for most viable models (see
    reference_model_matrix_consolidated), so it stopped discriminating between
    top candidates. exec_trace (predict exact stdout, don't generate) is the
    one axis that still separates them — worth a cheap 6-item add-on per model.
    """
    if not EXEC_TRACE.exists():
        return {"exec_trace_status": "skip_missing_script"}
    try:
        cp = subprocess.run([PY_CMD, str(EXEC_TRACE)], capture_output=True, text=True, timeout=180)
        out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    except subprocess.TimeoutExpired:
        return {"exec_trace_status": "timeout_180s"}
    parsed = parse_exec_trace_output(out)
    if parsed is None:
        return {"exec_trace_status": "parse_failed", "exec_trace_raw": out[-500:]}
    parsed["exec_trace_status"] = "ok"
    return parsed


def run_one(label: str, model_path: Path, runtime: str, extra: list[str],
            with_exec_trace: bool = False) -> dict:
    kill_llama_server()  # ensure clean state
    t_load_start = time.time()
    proc = start_server(label, model_path, runtime, extra)
    if proc is None:
        return {"label": label, "status": "skip_missing"}
    ready = wait_server_ready(HOST, PORT, max_wait=180)
    load_time = time.time() - t_load_start
    if not ready:
        proc.terminate()
        kill_llama_server()
        return {"label": label, "status": "load_failed", "load_time": load_time}
    print(f"  ready in {load_time:.1f}s — running bench...")
    bench_t0 = time.time()
    try:
        cp = subprocess.run(
            [PY_CMD, str(BENCH), "--models", label],
            capture_output=True, text=True, timeout=900,
        )
        out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    except subprocess.TimeoutExpired:
        out = "<<<TIMEOUT 900s>>>"
    bench_time = time.time() - bench_t0
    parsed = parse_bench_output(out)
    log_dump = REPO / f"sweep_bench_{label}.txt"
    log_dump.write_text(out, encoding="utf-8", errors="replace")
    exec_trace_result = run_exec_trace(label) if with_exec_trace else {}
    kill_llama_server()
    result = {
        "label": label,
        "model_path": str(model_path),
        "runtime": runtime,
        "load_time": round(load_time, 2),
        "bench_time": round(bench_time, 2),
        "passed": parsed["passed"],
        "total": parsed["total"],
        "passed_of_51": parsed["passed_of_51"],
        "total_time_s": parsed["total_time_s"],
        "valid": parsed["valid_for_coding"],
        "per_task": parsed["per_task"],
        "status": "ok",
    }
    result.update(exec_trace_result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, choices=[0, 1, 2, 3, 4, 5, 6, 7], help="Run a tier")
    ap.add_argument("--single", help="Run a single label from any tier")
    ap.add_argument("--skip-preflight", action="store_true",
                     help="Skip the scorer sanity gate (not recommended)")
    ap.add_argument("--exec-trace", action="store_true",
                     help="Also run the exec_trace 'easy' 6-item add-on per model "
                          "(discriminates the 51/51 coding-bench ceiling cluster)")
    args = ap.parse_args()

    if not args.skip_preflight:
        run_preflight()

    if args.single:
        for tier in TIERS.values():
            for label, path, rt, extra in tier:
                if label == args.single:
                    print(f"\n=== {label} ===")
                    r = run_one(label, path, rt, extra, with_exec_trace=args.exec_trace)
                    print(json.dumps(r, indent=2))
                    return
        print(f"Label '{args.single}' not found"); sys.exit(1)

    if args.tier is None:
        ap.print_help(); sys.exit(1)

    results = []
    if LEADERBOARD.exists():
        results = json.loads(LEADERBOARD.read_text())

    for label, path, rt, extra in TIERS[args.tier]:
        print(f"\n=== {label} ===")
        r = run_one(label, path, rt, extra, with_exec_trace=args.exec_trace)
        r["tier"] = args.tier
        r["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        keys = ("label", "load_time", "bench_time", "passed", "valid", "status")
        print(json.dumps({k: r.get(k) for k in keys}, indent=2))
        results.append(r)
        LEADERBOARD.write_text(json.dumps(results, indent=2))

    print("\n=== SUMMARY ===")
    for r in results[-len(TIERS[args.tier]):]:
        print(f"  {r['label']:50s} -> {r.get('passed_of_51', r.get('passed', '?'))}/51  "
              f"bench={r.get('bench_time', '?')}s  total={r.get('total_time_s', '?')}s  valid={r.get('valid')}")


if __name__ == "__main__":
    main()
