# Task Status - Qwen3 7B Testing (2026-07-14)

## Task 1: Download & Validate GGUF ✅ COMPLETE
- Downloaded: `Qwen3-7B-Q4_K_M.gguf` from Ygz-08123/Qwen3-7B-Instruct-Q4_K_M-GGUF
- File size: 4.36 GB (Q4_K_M variant)
- Smoke test: PASSED (loaded on CUDA, generated output without OOM)
- Commit: `704c83fd` - chore: add Qwen3-7B-Q4_K_M GGUF for testing

## Task 2: Benchmark Qwen3 7B - Coding (51 task) 🔄 IN PROGRESS
- Script: `sweep_small_models.py --single "Qwen3-7B-Q4_K_M" --exec-trace`
- Started: 2026-07-14 after fresh server initialization
- Timeout: Extended from 900s to 7200s (2 hours) to prevent premature timeout
- Status: Server log shows model loaded, first task processing
- Commits:
  - `c5f5626b` - fix: increase benchmark timeout from 900s to 7200s (2 hours)
  - `704c83fd` - chore: add Qwen3-7B-Q4_K_M GGUF for testing

## Task 3: Benchmark Qwen3 7B - Advanced (17 task) ⏳ WAITING FOR TASK 2
- Script: `sweep_advanced.py` (runs independently, starts own server)
- Qwen3-7B added to WINNERS list
- Status: Waiting for Task 2 coding benchmark to complete
- Commit: `67f93216` - chore: add Qwen3-7B-Q4_K_M to advanced benchmark WINNERS list

## Task 4: Golden Hash Check ⏳ WAITING FOR TASK 2
- Script: `D:\repos\ik-llama-bench\golden_hash.py check <label>`
- Status: Waiting for Task 2 to complete and leave server running
- Will use semantic validation (checking answer correctness vs byte-identical match)

## Notes
- Monitor running (task: bdglfy4x0) - will notify when coding benchmark completes
- Model is Qwen2.5 7B (merged: Qwen2.5-Coder + Qwen2.5 + Qwen2.5-Math)
- Architecture: qwen2, non-MoE dense
- Previous timeout at 15 minutes due to script timeout (900s), not model hang
