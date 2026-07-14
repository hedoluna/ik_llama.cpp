# Test & Benchmark Modelli Luglio 2026 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Testare sistematicamente 4 modelli nuovi luglio 2026 su hw A2000 6GB, determinare quali aggiungere al roster coding/advanced.

**Architecture:** 
Ordine razionale per viabilità VRAM (densità prima, MoE dopo). TDD: fallimento atteso per modelli ad alto rischio (Phi-4-mini base, Llama 3.3 dopo Llama 3.1 fail). Commit dopo ogni benchmark per tracciabilità. Golden hash check per regressioni cross-build ik_llama vs mainline. Leaderboard snapshot finale + memory update.

**Tech Stack:** Python 3.12 (trading-algo venv), ik_llama.cpp build CUDA, sweep_small_models.py harness, sweep_advanced.py, golden_hash.py.

---

### Task 1: Download & validate GGUF Qwen3 7B

**Files:**
- Check: `D:\repos\ik_llama.cpp\models\` (inventory)
- Script: `scripts\bench_new_models_2026_05_17.ps1` (template)
- Verify: `D:\repos\ik_llama.cpp\build\bin\Release\llama-cli.exe`

**Step 1: Locate Qwen3 7B GGUF on HuggingFace**

Run: `curl -s "https://huggingface.co/api/models?search=qwen3%207b&library=gguf&sort=downloads" | jq '.[] | select(.id) | .id' | head -5`

Expected: Output list of Qwen3 7B GGUF candidates (e.g., `bartowski/Qwen3-7B-Q4_K_M-GGUF`, `migarcoes/Qwen3-7B-Q4_K_M`)

**Step 2: Download smallest viable GGUF variant (Q4_K_M)**

Estimate: ~4.7 GB for 7B Q4_K_M. If not in `models/`, download:

```powershell
$url = "https://huggingface.co/bartowski/Qwen3-7B-Q4_K_M-GGUF/resolve/main/Qwen3-7B-Q4_K_M.gguf"
$dest = "D:\repos\ik_llama.cpp\models\Qwen3-7B-Q4_K_M.gguf"
if (-not (Test-Path $dest)) {
  curl -L -C - -o $dest $url
}
Write-Host "Downloaded: $(Get-Item $dest | % { "$($_.Length/1GB)GB" })"
```

Expected: File ~4.7 GB at $dest, curl exit 0

**Step 3: Quick smoke test (10s inference)**

```powershell
& "D:\repos\ik_llama.cpp\build\bin\Release\llama-cli.exe" `
  -m "D:\repos\ik_llama.cpp\models\Qwen3-7B-Q4_K_M.gguf" `
  -p "def fibonacci" -n 32 -ngl 99 -c 2048
```

Expected: Output coherent Python code snippet, no OOM, exit 0

**Step 4: Commit**

```bash
git add -A  # (if models/ tracked)
git commit -m "chore: add Qwen3-7B-Q4_K_M GGUF for testing"
```

---

### Task 2: Benchmark Qwen3 7B — Coding (51 task)

**Files:**
- Script: `D:\repos\ik_llama.cpp\sweep_small_models.py`
- Harness: `D:\repos\ik-llama-bench\sweep_lib.py`, `coding_benchmark.py`
- Config: `D:\repos\ik_llama.cpp\llama-swap.config.yaml` (reference params)
- Output: `D:\repos\ik_llama.cpp\sweep_leaderboard.json` (upsert result)

**Step 1: Prepare benchmark environment**

Verify: `D:\repos\trading-algo\.venv-py312\Scripts\python.exe` exists
Verify: `D:\repos\ik_llama.cpp\build\bin\Release\llama-server.exe` exists

Expected: Both files present

**Step 2: Run coding benchmark (Qwen3 7B)**

```powershell
$env:PYTHONPATH = "D:\repos\ik-llama-bench;D:\repos\ik_llama.cpp"
$python = "D:\repos\trading-algo\.venv-py312\Scripts\python.exe"

& $python D:\repos\ik_llama.cpp\sweep_small_models.py `
  --single "Qwen3-7B-Q4_K_M" `
  --tier CANDIDATES `
  --exec-trace
```

Expected: Completes in ~30-45 min, output JSON with score (target: >=50/51, ideally 51/51)

**Step 3: Manually record result in leaderboard**

If `--single` does NOT auto-save (known issue from memory), upsert `sweep_leaderboard.json`:

```json
{
  "label": "Qwen3-7B-Q4_K_M",
  "model": "Qwen3-7B-Q4_K_M",
  "score": <N/51>,
  "load_time_s": <T>,
  "bench_time_s": <T>,
  "timestamp": "2026-07-14",
  "tier": "CANDIDATES",
  "valid": true,
  "notes": "Qwen3 7B test"
}
```

**Step 4: Commit**

```bash
git add sweep_leaderboard.json
git commit -m "test(qwen3-7b): coding benchmark 51 task — <SCORE>/51 in <TIME>s"
```

---

### Task 3: Benchmark Qwen3 7B — Advanced (17 task)

**Files:**
- Script: `D:\repos\ik_llama.cpp\sweep_advanced.py`
- Harness: `D:\repos\ik-llama-bench\sweep_lib.py`
- Same llama-server from Task 2 (reuse loaded model)

**Step 1: Run advanced benchmark**

```powershell
$env:PYTHONPATH = "D:\repos\ik-llama-bench;D:\repos\ik_llama.cpp"
$python = "D:\repos\trading-algo\.venv-py312\Scripts\python.exe"

& $python D:\repos\ik_llama.cpp\sweep_advanced.py `
  --model "Qwen3-7B-Q4_K_M" `
  --load-from-server "http://127.0.0.1:8080" `
  --timeout 300
```

Expected: Completes in ~5-10 min (reuses loaded model), output score (target: >=15/17, ideally 17/17)

**Step 2: Record advanced score**

Append to leaderboard record from Task 3:

```json
"advanced_score": <N/17>,
"advanced_time_s": <T>
```

**Step 3: Commit**

```bash
git add sweep_leaderboard.json
git commit -m "test(qwen3-7b): advanced benchmark — <SCORE>/17"
```

---

### Task 4: Golden Hash Check (Qwen3 7B, ik_llama vs mainline)

**Files:**
- Script: `D:\repos\ik_llama.cpp\golden_hash.py`
- Ref configs: `D:\repos\ik_llama.cpp\reference_winner_configs.md`

**Step 1: Check ik_llama build hash**

```powershell
& "D:\repos\ik_llama.cpp\golden_hash.py" check `
  --model "Qwen3-7B-Q4_K_M" `
  --binary "ik_llama" `
  --prompt-tokens 128 `
  --gen-tokens 64
```

Expected: Output hash (e.g., `prime=abc123`, `arith=def456`, `json=ghi789`)

**Step 2: Compare vs mainline**

```powershell
& "D:\repos\llama\build\bin\Release\llama-bench.exe" `
  -m "D:\repos\ik_llama.cpp\models\Qwen3-7B-Q4_K_M.gguf" `
  -p 128 -n 64 -ngl 99 -r 3
```

Capture output (pp, tg), compare hashes.

Expected: Either MATCH (no regression) or DIVERGE (ik_llama-specific, acceptable if speed gain)

**Step 3: Record result**

```bash
git add -A
git commit -m "test(qwen3-7b): golden hash check — <STATUS> vs mainline"
```

---

### Task 5: Test Llama 3.3 8B (same workflow as Qwen3 7B, Tasks 1-4)

**Caveat:** Llama 3.1-8B failed with 19-25/51. Llama 3.3 8B is newer release; may have fix or same gap. **Accept 20-45/51 as "candidate for future watchlist" (low priority).**

**Files:** Same as Tasks 1-4, swap model name

**Step 1-4:** Repeat Task 1-4 with `Llama-3.3-8B-Q4_K_M` (estimate download ~4.8 GB)

Expected (generous): 30-40/51 coding, 12-15/17 advanced (below Qwen3 7B)

**Step 5: Commit**

```bash
git commit -m "test(llama-3.3-8b): coding <SCORE>/51, advanced <SCORE>/17 — CANDIDATE"
```

---

### Task 6: Assess Phi-4-mini 3.8B viability (VRAM + fail risk)

**Files:**
- Variant check: HuggingFace search `phi-4-mini 3.8B` (NOT `-reasoning`)
- VRAM estimate: ~2.5 GB

**Step 1: Confirm Phi-4-mini 3.8B base (non-reasoning) GGUF exists**

Run: `curl -s "https://huggingface.co/api/models?search=phi-4-mini%203.8b&library=gguf" | grep -v reasoning | head -1`

Expected: Output repo URL (e.g., `bartowski/Phi-4-mini-3.8B-Q4_K_M-GGUF`)

**Step 2: Download & smoke test (2 min)**

```powershell
# Download ~2.5 GB
$url = "https://huggingface.co/bartowski/Phi-4-mini-3.8B-Q4_K_M-GGUF/resolve/main/Phi-4-mini-3.8B-Q4_K_M.gguf"
$dest = "D:\repos\ik_llama.cpp\models\Phi-4-mini-3.8B-Q4_K_M.gguf"
curl -L -C - -o $dest $url

# Quick test
& "D:\repos\ik_llama.cpp\build\bin\Release\llama-cli.exe" `
  -m $dest -p "def factorial" -n 32 -ngl 99 -t 60
```

Expected: Completes <60s, outputs Python code (NOT infinite CoT like Phi-4-mini-reasoning)

**Step 3: Decision gate**

- If completes cleanly: proceed to Task 7 (full benchmark)
- If hangs >60s or loop detected: SKIP (risk same as Phi-4-mini-reasoning), commit decision

```bash
git commit -m "test(phi-4-mini-3.8b): smoke test PASS — proceed to coding benchmark" 
# OR
git commit -m "test(phi-4-mini-3.8b): smoke test FAIL (timeout/loop) — SKIP this model"
```

---

### Task 7: Benchmark Phi-4-mini 3.8B — Coding (51 task, IF Task 6 passes)

**Scope:** Same as Task 2 (coding 51 + advanced 17)

**Step 1-3:** Run sweep_small_models.py (expect ~20-30 min)

Expected: 40-50/51 (Microsoft-grade, but unproven coding specialty)

**Step 4: Commit**

```bash
git commit -m "test(phi-4-mini-3.8b): coding <SCORE>/51, advanced <SCORE>/17"
```

---

### Task 8: Skip Mistral Small 3 7B (low priority)

**Rationale:** From memory, Mistral Small 3 7B est. 15-20 t/s on A2000 (slower than daily winner 50 t/s). Qwen3 7B already tests the "new 7B dense" tier. Skip unless time permits.

**Step 1: Document decision**

```bash
git commit -m "docs: note Mistral Small 3 7B skipped (low priority, estimated slower than Qwen3 7B)"
```

---

### Task 9: Update Leaderboard & Memory

**Files:**
- `D:\repos\ik_llama.cpp\sweep_leaderboard.json` (finalize)
- `C:\Users\orlan\.claude\projects\D--repos-ik-llama-cpp\memory\MEMORY.md`
- `C:\Users\orlan\.claude\projects\D--repos-ik-llama-cpp\memory\LEARNED.md`

**Step 1: Summarize results in leaderboard**

Consolidate all test results into `sweep_leaderboard.json` with complete records:

```json
{
  "date": "2026-07-14",
  "tests": [
    { "model": "Qwen3-7B-Q4_K_M", "coding": XX/51, "advanced": XX/17, "status": "CANDIDATE|PASS|FAIL" },
    { "model": "Llama-3.3-8B-Q4_K_M", "coding": XX/51, "advanced": XX/17, "status": "CANDIDATE|FAIL" },
    { "model": "Phi-4-mini-3.8B-Q4_K_M", "coding": XX/51, "advanced": XX/17, "status": "SKIP|FAIL" }
  ]
}
```

**Step 2: Create memory file summarizing test session**

File: `C:\Users\orlan\.claude\projects\D--repos-ik-llama-cpp\memory\project_test_new_models_2026_07_14.md`

```markdown
---
name: project_test_new_models_2026_07_14
description: Test session luglio 2026 — Qwen3 7B, Llama 3.3 8B, Phi-4-mini 3.8B base
metadata:
  type: project
---

## Test Session 14 Luglio 2026

### Modelli Testati

| Modello | Coding | Advanced | Status | Note |
|---|---:|---:|---|---|
| Qwen3-7B-Q4_K_M | XX/51 | XX/17 | PASS/CANDIDATE | HE 76.0, <5GB VRAM |
| Llama-3.3-8B-Q4_K_M | XX/51 | XX/17 | CANDIDATE/FAIL | Vs Llama 3.1 (19-25/51) |
| Phi-4-mini-3.8B-Q4_K_M | XX/51 | XX/17 | PASS/FAIL/SKIP | Smoke test: PASS/FAIL |

### Roster Decision

- **KEEP** (add to sweep_small_models.py TIERS): [list modelli con >=50/51 coding + >=16/17 advanced]
- **WATCH** (futuri upgrade): [list modelli 40-49/51]
- **DROP**: [list modelli <40/51]

### Lezioni

[Specifiche osservazioni tecniche per ogni modello — VRAM, speed, failures]

### Prossimi Step

[Eventual future testing, known gaps, architetture da rivisitare]
```

**Step 3: Update MEMORY.md index**

Add line:

```markdown
- [**✅ Test modelli luglio 2026 2026-07-14**](project_test_new_models_2026_07_14.md) — Qwen3 7B (nuovo, HE 76.0), Llama 3.3 8B (post-3.1 fail), Phi-4-mini 3.8B base (MS, non-reasoning); roster update
```

**Step 4: Update LEARNED.md (if applicable)**

If Qwen3 7B passes >=50/51: add to ✓ COSA FUNZIONA table.

**Step 5: Commit final changes**

```bash
git add sweep_leaderboard.json LEARNED.md
git commit -m "docs: update leaderboard and learned from test session 2026-07-14"
```

---

### Task 10: Final Review & Roster Update

**Files:**
- `D:\repos\ik_llama.cpp\sweep_small_models.py` (TIERS array, if new model qualifies)
- `reference_model_selection_matrix.md` (update if new daily winner)

**Step 1: Decide roster changes**

Criteria:
- **Add to WINNERS/TIERS[7]**: >=51/51 coding + >=17/17 advanced + speed competitive (20-50 t/s target)
- **Add to TIERS[X] (candidate tier)**: 45-50/51 coding, useful specialty
- **Skip**: <40/51

**Step 2: Update sweep_small_models.py**

If Qwen3 7B passes, add to TIERS array:

```python
# TIERS[3] — Qwen tier
{
    "label": "Qwen3-7B-Q4_K_M",
    "model_path": "Qwen3-7B-Q4_K_M.gguf",
    "params": ["-ngl", "99", "-c", "8192", "-fa", "1"],
    "tier": "CANDIDATES"
}
```

**Step 3: Commit**

```bash
git add sweep_small_models.py
git commit -m "chore: add new models to sweep roster (2026-07-14 test results)"
```

---

## Execution Handoff

**Plan complete and saved to `docs/plans/2026-07-14-test-new-models.md`.**

Two execution options:

**1. Subagent-Driven (this session)** — Fresh subagent per task (1-4 tasks per wakeup), code review between, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

**Which approach?**

(If Subagent-Driven: I'll use @superpowers:subagent-driven-development. If Parallel: guide you to new session using @superpowers:executing-plans.)
