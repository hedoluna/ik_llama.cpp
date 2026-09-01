# Cerebrum

> OpenWolf's learning memory. Updated automatically as the AI learns from interactions.
> Do not edit manually unless correcting an error.
> Last updated: 2026-07-28

## User Preferences

<!-- How the user likes things done. Code style, tools, patterns, communication. -->

## Key Learnings

- **Project:** llama-cpp-scripts
- **Description:** [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
- **Qwen3.8-Flash-Next / arch `qwen4exp`**: runs ONLY on the mainline PR build `D:\repos\llama-qwen38-flash-next` (PR #27742), NOT ik_llama.cpp. Model at `models\Qwen3.8-Flash-Next-UD-IQ3_XXS\`. Launch: `--jinja -fit off --cpu-moe -ngl 99 -t 12 -c <ctx>`. KV cache MUST be f16 (quantized KV = hard assert `qwen4exp.cpp:544`). Keep mmap ON (51B N-gram table pages from SSD). Memory-bandwidth bound → ~12-14 t/s tg ceiling on this box, no server flag improves it. Sampling for code: `temp 0.45 top_p 0.9 top_k 40 min_p 0.05 repeat_penalty 1.05 presence_penalty 0`.
- Optuna harnesses for this model: `D:\repos\ik-llama-bench\scripts\optuna_qwen38flashnext_2026_08_27.py` (server flags) + `optuna_sampling_qwen38fn_2026_08_27.py` (sampling).
- Bench methodology: Ralph `coding_benchmark.py` one-shot = raw capability + ambiguity detector; `orchestrator` (`D:\repos\orchestrator`) `--backend ralph-local` = success under realistic conditions (tests-as-spec + deterministic gate + repair). Keep both. orchestrator invocation + gotchas: see project_qwen38_flash_next memory.
- `coding_benchmark.py` has a spec-quality checklist above `CODING_TASKS` (added 2026-08-28 after `task3 nested_sum` turned out to be an ambiguous spec, not a model weakness — `task3b` is the disambiguated version).
- **2026-08-28: ik_llama merged native `qwen4exp` (upstream #2365).** The mainline PR worktree `D:\repos\llama-qwen38-flash-next` is now redundant. `-fit off` is a mainline-PR-only flag — ik_llama's binaries reject it (print help, exit 0). On the A2000 6GB always pass a small `-c` (8192) or the 262144-default KV (7.2GB) spills VRAM and tg drops from ~13 to ~6.6 t/s. Native speed/accuracy = same as PR build (memory-bandwidth bound, no IQK-GEMM win).
- **Ornith-1.5-35B-A3B (`qwen3_5_moe`)**: loads NATIVE in ik_llama, tg ~33 t/s on plain Q4_K_M, KV only 1.3 GB @ 64k (linear-attn hybrid). Coding 56/56, advanced 17/17+ML 4/4, tool-calling 3/3 no-fix, needle 41k PASS. **Daily-winner upgrade candidate.** Hard-logic recipe = **Mellum class**: `--reasoning off` + structural ordering hint v3 → **15/15 stable** on GildedRose-Conjured (thinking ON causes runaway, opposite of the Qwen3.6 daily-winner). Hint-wording rule: for double-penalty edges give the STRUCTURE ("same step applied twice"), never the total ("-4") — the total makes the model over-correct. Scripts: `scripts/test_gildedrose_ab.py` + `scripts/gildedrose_ornith_hint_v3_2026_08_28.py`. See [[project-ornith15-35b-bench]], [[project-hard-logic-recipe]].

## Do-Not-Repeat

<!-- Mistakes made and corrected. Each entry prevents the same mistake recurring. -->
<!-- Format: [YYYY-MM-DD] Description of what went wrong and what to do instead. -->
- [2026-08-27] Put `-ctk/-ctv` (KV quant) in an Optuna search space for `qwen4exp` → 7 trials wasted on a hard `GGML_ASSERT`. KV is f16-only for this arch; never search that axis.
- [2026-08-27] Applied the repo's standard `--no-mmap` speed trick to Qwen3.8-Flash-Next. Wrong: this arch needs mmap ON so the 51B N-gram hash table stays SSD-pageable. `--no-mmap`/`--load-mode none` defeats the memory strategy.
- [2026-08-27] Trusted the vendor `presence_penalty 1.5` (non-think preset) for exact-match code → -3/37 on katas vs presence 0. Vendor presets tune chat diversity, not pass-rate.
- [2026-08-27] Let a background Optuna run continue after the first ~5 trials already showed a systematic failure mode. Stop and fix the harness immediately instead.

## Decision Log

<!-- Significant technical decisions with rationale. Why X was chosen over Y. -->
