#!/usr/bin/env python3
"""sweep_untested_characteristics.py — sweeps the top 3 models on untested features.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

# Reuse sweep_small_models logic for starting/killing server
import sweep_small_models as ssm

MODELS = [
    ("Qwen2.5-Coder-3B-Q4_0",
     ssm.MODELS_CACHE / "Qwen" / "Qwen2.5-Coder-3B-Instruct-GGUF" / "qwen2.5-coder-3b-instruct-q4_0.gguf",
     "ik", []),
    ("Qwen2.5-Coder-1.5B-Q4_K_M",
     ssm.MODELS_CACHE / "migarcoes" / "Qwen-Qwen2.5-Coder-1.5B-Instruct" / "Qwen-Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf",
     "ik", []),
    ("granite-4.1-3B-Q4_K_S",
     ssm.MODELS_CACHE / "unsloth" / "granite-4.1-3b-GGUF" / "granite-4.1-3b-Q4_K_S.gguf",
     "main", []),
]

LEADERBOARD = ssm.REPO / "untested_characteristics_leaderboard.json"

def run_script(script_path: Path, args: list[str] = []) -> str:
    cp = subprocess.run(
        [ssm.PY_CMD, str(script_path)] + args,
        capture_output=True, text=True, timeout=600
    )
    return (cp.stdout or "") + "\n" + (cp.stderr or "")

def run_one_model(label: str, path: Path, runtime: str, extra: list[str]) -> dict:
    print(f"\n=== Starting server for: {label} ===")
    ssm.kill_llama_server()
    t0 = time.time()
    proc = ssm.start_server(label, path, runtime, extra)
    if not proc:
        return {"label": label, "status": "skip_missing"}
    
    # Wait for server
    if not ssm.wait_server_ready(ssm.HOST, ssm.PORT, max_wait=180):
        proc.terminate()
        ssm.kill_llama_server()
        return {"label": label, "status": "load_failed"}
    
    load_time = time.time() - t0
    print(f"  ready in {load_time:.1f}s — running benchmarks ...")
    
    model_results = {
        "label": label,
        "load_time_s": round(load_time, 2),
        "status": "ok",
        "benchmarks": {}
    }
    
    # 1. Spec Ambiguity
    print("  Running Spec Ambiguity ...")
    run_script(ssm.REPO / "sweep_bench_spec_ambiguity.py")
    res_spec_path = ssm.REPO / "sweep_bench_spec_ambiguity_result.json"
    if res_spec_path.exists():
        spec_data = json.loads(res_spec_path.read_text())
        honest_n = sum(1 for r in spec_data if r["class"] in ("ASKS", "HEDGES", "FABRICATES_WITH_HEDGE"))
        model_results["benchmarks"]["spec_ambiguity"] = {
            "honest_score": f"{honest_n}/{len(spec_data)}",
            "results": spec_data
        }
        
    # 2. Literal Preservation (with hint)
    print("  Running Literal Preservation ...")
    run_script(ssm.REPO / "sweep_bench_literal_preservation.py")
    res_lit_path = ssm.REPO / "sweep_bench_literal_preservation_result.json"
    if res_lit_path.exists():
        lit_data = json.loads(res_lit_path.read_text())
        pass_n = sum(1 for r in lit_data if r["verdict"] == "PASS")
        model_results["benchmarks"]["literal_preservation"] = {
            "pass_score": f"{pass_n}/{len(lit_data)}",
            "results": lit_data
        }
        
    # 3. Literal Preservation Hard (without hint)
    print("  Running Literal Preservation Hard ...")
    run_script(ssm.REPO / "sweep_bench_literal_preservation_hard.py")
    res_lit_hard_path = ssm.REPO / "sweep_bench_literal_preservation_hard_result.json"
    if res_lit_hard_path.exists():
        lit_hard_data = json.loads(res_lit_hard_path.read_text())
        pass_n = sum(1 for r in lit_hard_data if r["verdict"] == "PASS")
        part_n = sum(1 for r in lit_hard_data if r["verdict"] == "PARTIAL")
        model_results["benchmarks"]["literal_preservation_hard"] = {
            "pass_score": f"{pass_n}/{len(lit_hard_data)}",
            "partial_score": f"{part_n}/{len(lit_hard_data)}",
            "results": lit_hard_data
        }
        
    # 4. Tool Call
    print("  Running Tool Call ...")
    run_script(ssm.REPO / "sweep_mode_toolcall.py")
    res_tool_path = ssm.REPO / "sweep_mode_toolcall_result.json"
    if res_tool_path.exists():
        tool_data = json.loads(res_tool_path.read_text())
        pass_n = sum(1 for r in tool_data if r["verdict"] == "PASS")
        model_results["benchmarks"]["toolcall"] = {
            "pass_score": f"{pass_n}/{len(tool_data)}",
            "results": tool_data
        }
        
    # 5. Self-Correction
    print("  Running Self-Correction ...")
    # Clean old self-correction JSON if any
    sc_json_path = ssm.REPO / f"sweep_mode_self_correction_{label}.json"
    if sc_json_path.exists():
        sc_json_path.unlink()
    run_script(ssm.REPO / "sweep_mode_self_correction.py", ["--label", label])
    if sc_json_path.exists():
        sc_data = json.loads(sc_json_path.read_text())
        model_results["benchmarks"]["self_correction"] = {
            "pass1": sc_data["pass1"],
            "pass1_plus_1": sc_data["pass1_plus_1"],
            "rows": sc_data["rows"]
        }
        
    ssm.kill_llama_server()
    return model_results

def main():
    print("Starting untested characteristics sweep ...")
    results = []
    if LEADERBOARD.exists():
        try:
            results = json.loads(LEADERBOARD.read_text())
        except Exception:
            pass
            
    for label, path, runtime, extra in MODELS:
        res = run_one_model(label, path, runtime, extra)
        res["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # update or append
        idx = next((i for i, x in enumerate(results) if x.get("label") == label), -1)
        if idx != -1:
            results[idx] = res
        else:
            results.append(res)
            
        LEADERBOARD.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        
    print("\n=== SWEEP COMPLETED ===")
    for r in results:
        print(f"\nModel: {r['label']}")
        if r["status"] != "ok":
            print(f"  Status: {r['status']}")
            continue
        bench = r.get("benchmarks", {})
        if "spec_ambiguity" in bench:
            print(f"  Spec Ambiguity: {bench['spec_ambiguity']['honest_score']}")
        if "literal_preservation" in bench:
            print(f"  Literal Preservation: {bench['literal_preservation']['pass_score']}")
        if "literal_preservation_hard" in bench:
            print(f"  Literal Pres. Hard: {bench['literal_preservation_hard']['pass_score']}")
        if "toolcall" in bench:
            print(f"  Toolcall: {bench['toolcall']['pass_score']}")
        if "self_correction" in bench:
            print(f"  Self-Correction: Pass@1={bench['self_correction']['pass1']} -> Pass@1+1={bench['self_correction']['pass1_plus_1']}")

if __name__ == "__main__":
    main()
