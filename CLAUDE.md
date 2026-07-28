# OpenWolf

@.wolf/OPENWOLF.md

This project uses OpenWolf for context management. Read and follow .wolf/OPENWOLF.md every session. Check .wolf/cerebrum.md before generating code. Check .wolf/anatomy.md before reading files.


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Fork of `ggerganov/llama.cpp` (by ikawrakow) optimized for **CPU + hybrid CPU/GPU MoE inference**. Adds SOTA quantization types (IQ-K, R4 row-interleaved), MLA / FlashMLA for DeepSeek, fused MoE ops, Bitnet support, IQK quantized GEMM kernels. Only fully supported backends: **CPU (AVX2+ / ARM_NEON+) and CUDA (Turing+)**. ROCm/Vulkan/Metal/AVX/old-NVIDIA are not maintained — do not file issues for them.

## Build

```powershell
# CPU build (Linux/Mac/Windows)
cmake -B build -DGGML_NATIVE=ON
cmake --build build --config Release -j

# CUDA build (this machine: A2000 sm_86)
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DLLAMA_CURL=OFF
cmake --build build --config Release -j
```

Notes:
- On **AVX-512 CPUs** (Zen4 / Sapphire Rapids+) read `docs/build.md` section "CPU build flags for AVX-512". Without those extra flags a `Release` build silently falls back to AVX2 and the IQK GEMM kernels (`HAVE_FANCY_SIMD`) are disabled.
- This fork links CUDA **statically into `ggml.dll` / `llama.dll`** — there is no separate `ggml-cuda.dll` (unlike mainline). Do not look for one.
- Build artifacts on Windows live in `build\bin\Release\` (note `Release` capitalization differs from Linux).

## Run / test

```powershell
# Inference server (OpenAI-compatible API on :8080)
build\bin\Release\llama-server.exe -m <model.gguf> -ngl 99 -c 8192 --host 127.0.0.1 --port 8080

# Microbench (pp / tg for a given model + flags)
build\bin\Release\llama-bench.exe -m <model.gguf> -ngl 99

# Single CLI generation
build\bin\Release\llama-cli.exe -m <model.gguf> -p "..." -n 128

# Quantize / imatrix
build\bin\Release\llama-quantize.exe <in.gguf> <out.gguf> <type>
build\bin\Release\llama-imatrix.exe -m <model.gguf> -f <calibration.txt>
```

Test commands (per `CONTRIBUTING.md`):
- `./tests/test-backend-ops` — exercises GGML backend implementations (run after kernel changes)
- Full local CI: see `ci/README.md` before opening a PR

## Key directories

| Dir | Contains |
|---|---|
| `ggml/src/` | Tensor library: backends (`ggml-cuda/`, `ggml-cpu/`), IQK kernels, quant types, alloc, sched |
| `src/` | llama model layer: `llama-arch.*`, `llama-build-context.*`, `llama-delta-net.*`, expert IO, grammar, model loader |
| `examples/` | Binaries built into `build/bin/Release/`: server, llama-bench, llama-cli, llama-quantize, llama-imatrix, infill, embedding, lookup-*, llava-cli, gemma3-cli, qwen2vl-cli, parallel, batched-bench, perplexity, etc. |
| `common/` | Shared CLI argument parsing, sampling, log helpers used by all binaries in `examples/` |
| `tests/` | Standalone test binaries built into `build/bin/` (`test-backend-ops`, `test-grad0`, `test-tokenizer-*`, `test-chat-*`, `test-grammar-*`) |
| `docs/build.md`, `docs/parameters.md`, `docs/speculative.md`, `docs/backend/` | Operational docs |
| `gguf-py/` | Python package for reading/writing GGUF files (used by `convert_hf_to_gguf.py`) |
| `convert_*.py` | HuggingFace → GGUF converters at repo root (run with `py` on Windows; the MS Store `python`/`python3` stubs do not execute) |

Cross-repo local context lives in `DEVELOPMENT_NOTES.md`: it maps the related `D:\repos` checkouts (`llama`, `llama-zaya`, `llama_mtp`, `llama_indras`, `ik-llama-bench`, `ralph`, `trading-algo`) and records which ones are Git repos, worktrees, or plain local folders.

## Architecture in one paragraph

A `gguf` file is loaded by `llama-model-loader` → `llama_model` (arch-specific build via `src/llama-arch.cpp`) → `llama_build_context` constructs the compute graph node-by-node calling into `ggml` operators (`ggml_*` in `ggml/include/ggml.h`, implemented in `ggml/src/ggml-cuda/*` and `ggml/src/ggml-cpu/*`). The `ggml_backend` interface picks the executor per tensor; **for MoE models tensors can be split between GPU and CPU** via `--n-cpu-moe N` (partial, only experts on CPU) or `--cpu-moe` (all experts on CPU). The IQK matmul path (`ggml/src/iqk/`) is the CPU-side replacement that gives this fork its name; it requires AVX2 minimum and `HAVE_FANCY_SIMD` on AVX-512. Server frontend lives in `examples/server/` (HTTP + OpenAI-compat shim).

## Code style (from `CONTRIBUTING.md`)

- No new third-party deps; cross-compile-friendly (no GNU-only, no fancy STL, no templates if avoidable)
- 4-space indent, brackets on same line, `void * ptr`, `int & a`
- Common-prefix naming for tensors / functions (see GGML PR #302)
- Tensors are **row-major**: dim 0 = columns, 1 = rows, 2 = matrices. `ggml_mul_mat(A, B)` computes `C^T = A B^T` i.e. `C = B A^T` (counter-intuitive — read the diagram in `media/matmul.png`)

## Gotchas

- **`-rtr` (run-time repack) + hybrid CPU/GPU MoE = trap**: repacks tensors to row-interleaved format that has no CUDA path for k-quants (Q2_K…Q6_K) → matmul forced on CPU → catastrophic pp slowdown. Use only if you understand the consequence.
- **Unsloth `_XL` GGUFs** with `f16` tensors likely won't load — author warns explicitly in README.
- **Split mode `graph` + partial GPU offload** can produce gibberish; if so, add `-cuda graphs=0`.
- **IQ3_K_R4** (and other `_R4` quants) are ik_llama-only: mainline llama.cpp rejects them with `ggml type 138 invalid`. The R4 is row-interleaved repacking for CPU cache.
- **MTP-tail GGUFs** from various community quanters do not load with this build's MTP loader (mismatched tensor naming); not a build issue, an ecosystem one.
- Issue tracker: do not file ROCm / Vulkan / Metal / pre-Turing CUDA bugs unless you also bring a fix.
- **Windows reserved-port bind failure** (`ocl` / `scripts/start-opencode-local.ps1`): a bind error `An attempt was made to access a socket in a way forbidden by its access permissions` (WSAEACCES) with *no* process on the port means the port fell inside a Hyper-V/WSL/Docker dynamically reserved range. Diagnose with `netsh interface ipv4 show excludedportrange protocol=tcp`. These ranges re-roll on reboot/Docker restart, so a port that worked before can suddenly fail. The local stack was moved off the reserved block to **router 8291, llama-swap 8292** (classifier 9998 unchanged) — keep app ports **below 9211** (the reservation floor on this machine) to stay durable. Ports are set in three places that must agree: `scripts/start-opencode-local.ps1` (`$Listen`, `$RouterPort`), `scripts/opencode-router.py` (`LISTEN_PORT`, `SWAP_BASE`), and `~/.config/opencode/opencode.jsonc` (`baseURL` → router). Alternative (keeps 9291/9292, needs admin + restarts Docker net): `net stop winnat; netsh int ipv4 add excludedportrange protocol=tcp startport=9291 numberofports=2 store=persistent; net start winnat`.

## Local quant workflow expectations

Models for testing live in `models/` (already populated with several Qwen3.6-35B-A3B variants in this checkout). Sample model paths used during local benchmarking are in `models/*.gguf`; vocab-only `ggml-vocab-*.gguf` are not inferenceable.

## Progetti correlati
> Mappa completa: D:\repos\pdt\PROJECT_LINKS.md
- **pdt** — classifier :9998 (pipeline contatti)
- **ear2** — code-review locale 35B
- **06-marketing** — content-gen 35B
> Consumato via HTTP OpenAI-compat (classifier :9998, swap :8292, router :8291).

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->