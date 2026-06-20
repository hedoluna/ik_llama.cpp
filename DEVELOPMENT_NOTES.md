# Note di Sviluppo e Apprendimenti - Repository Llama & Benchmarks
*Ultimo aggiornamento: 2026-06-20*

Questo documento raccoglie la struttura dei repository, gli apprendimenti derivanti dagli aggiornamenti, lo stato dei benchmark e le impostazioni di sistema relative al marketing automatizzato per evitare perdite di tempo in futuro.

---

## 1. Struttura dei Repository & Git Worktrees
Tutti i repository legati a Llama e ai benchmark locali si trovano in `D:\repos`.

### Mappa locale canonica

| Path | Tipo | Remoto / Branch | Scopo | Note operative |
| --- | --- | --- | --- | --- |
| `D:\repos\ik_llama.cpp` | Git repo | `origin=https://github.com/ikawrakow/ik_llama.cpp`, `main`; `bench=https://github.com/hedoluna/ik-llama-bench.git` | Fork operativo corrente di `ik_llama.cpp`, build locale, OpenCode/llama-swap/router, modelli e script benchmark. | Repo attuale. Al 2026-06-16, dopo `fetch`, `main` e avanti di 16 commit e indietro di 41 rispetto a `origin/main`, con lavoro locale non pulito. Non fare reset/pull/merge distruttivi senza controllare. |
| `D:\repos\ik-llama-bench` | Git repo | `origin=https://github.com/hedoluna/ik-llama-bench-data.git`, `master` | Archivio/working tree dati benchmark separato. | Contiene risultati modificati e nuovi script di benchmark; trattare come dati locali importanti. |
| `D:\repos\llama` | Git worktree/repo | `origin=https://github.com/ggerganov/llama.cpp.git`, `master` | Checkout upstream ufficiale `llama.cpp`. | Usato come riferimento upstream. Ha artefatti build non tracciati sotto `cmake/`. |
| `D:\repos\llama-zaya` | Git worktree | `origin=https://github.com/ggerganov/llama.cpp.git`, `zaya-pr` | Branch locale Zaya-1 su base `llama.cpp`. | Branch critico: unica copia locale nota dell'implementazione Zaya-1. Non eliminare. |
| `D:\repos\llama_mtp` | Git repo | `origin=https://github.com/ggml-org/llama.cpp.git`, `master` | Checkout mainline/ggml-org per confronto MTP. | Usato come riferimento pulito rispetto alle feature MTP upstream. |
| `D:\repos\llama_indras` | Git repo | `origin=https://github.com/Indras-Mirror/llama.cpp-mtp.git`, `master` | Mirror/variante Indras con MTP. | Usato per confronto delle implementazioni MTP. |
| `D:\repos\ralph` | Cartella locale non-Git | nessun `.git` rilevato | Contiene `local_ralph\coding_benchmark.py`, usato da `sweep_small_models.py`. | Non aspettarsi comandi Git funzionanti qui. |
| `D:\repos\trading-algo` | Git repo | `origin=https://github.com/hedoluna/trading-algo.git`, `master` | Fornisce l'ambiente Python funzionante per alcuni benchmark. | Interprete usato: `D:\repos\trading-algo\.venv-py312\Scripts\python.exe`. |

Questa tabella e la fonte canonica per i riferimenti cross-repo locali. I documenti specifici (`CLAUDE.md`, `docs/opencode-local-llama-swap.md`, `bench-opencode-local/README.md`) devono rimandare qui invece di duplicare tutta la mappa.

### Documentazione cross-repo (linkata a vicenda)

Questo file (`DEVELOPMENT_NOTES.md`) e la **single source of truth** della mappa.
Ogni repo del cluster contiene un puntatore di ritorno qui (cosi i link sono
reciproci) senza duplicare la mappa. Aggiornare SOLO questo file quando cambiano
ruoli, remoti o stato.

| Repo | File puntatore | Tracciato in Git? | Cosa documenta in proprio |
| --- | --- | --- | --- |
| `ik_llama.cpp` | *questo file* + `docs/opencode-*.md` | si (branch `main`) | Mappa canonica, build, stack OpenCode/llama-swap/router, cloud tier NVIDIA, modelli, benchmark |
| `ik-llama-bench` | `README.md` (sez. "Stack locale & cross-repo") | si (branch `master`) | Harness e dati benchmark; `LESSONS_LEARNED_2026-05-31.md` |
| `llama` | `LOCAL_NOTES.md` | no (`.git/info/exclude` — mirror upstream) | Checkout pulito `llama.cpp` (ggerganov) di riferimento |
| `llama_mtp` | `LOCAL_NOTES.md` | no (mirror upstream) | Mainline ggml-org per confronto MTP |
| `llama_indras` | `LOCAL_NOTES.md` | no (mirror upstream) | Variante Indras-Mirror con MTP |
| `llama-zaya` | `LOCAL_NOTES.md` | no (worktree `zaya-pr`) | Unica copia locale di Zaya-1 — non eliminare |
| `ralph` | `LOCAL_NOTES.md` | n/a (cartella non-Git) | `local_ralph/coding_benchmark.py`, code-review LLM locale |
| `trading-algo` | `README.md` (sez. "Related local repositories") | si | Consuma lo stack locale (Local Ralph/PAL); SSOT retrospettiva = `LEARNINGS.md` |

I `LOCAL_NOTES.md` dei mirror upstream sono **local-only** (aggiunti a
`.git/info/exclude`) per mantenere i checkout fast-forwardabili da `origin`.

### Stack OpenCode locale + cloud tier (riferimenti)

- `docs/opencode-local-llama-swap.md` — stack locale (OpenCode -> router 8291 -> llama-swap 8292 -> llama-server 9999; classifier 9998).
- `docs/opencode-router-piano.md` — policy di routing `auto` + **cloud tier NVIDIA NIM** opt-in (`!cloud`/`!kimi`/`ocl -Mode kimi`); solo `nvidia-kimi` ha tool-calling verificato. Test/bench: `scripts/test-router-routing.py`, `scripts/test-router-cloud-integration.py`, `scripts/bench-nvidia-cloud.py`.
- `docs/model-test-ranking.md` — graduatoria qualita/velocita modelli locali.

### Stato aggiornamento remoti 2026-06-16

- `D:\repos\llama`: aggiornato in fast-forward a `origin/master` commit `74ade5274` (`vendor : update BoringSSL to 0.20260616.0 (#24693)`). Restano solo artefatti build non tracciati.
- `D:\repos\llama_mtp`: aggiornato in fast-forward a `origin/master` commit `74ade5274`.
- `D:\repos\ik_llama.cpp`: solo fetch. Non aggiornato/mergiato perche il branch locale diverge (`ahead 16, behind 41`) e il worktree contiene modifiche locali.
- `D:\repos\ik-llama-bench`: fetch eseguito; branch gia allineato a `origin/master`, ma worktree sporco con risultati/script locali.
- `D:\repos\llama_indras`: fetch eseguito; branch gia allineato a `origin/master`.
- `D:\repos\trading-algo`: fetch eseguito; non modificato perche `master` e avanti di 2 commit e il worktree contiene modifiche locali `.wolf`.
- `D:\repos\llama-zaya`: fetch eseguito tramite repo condiviso con `llama`; `zaya-pr` non ha upstream configurato e non e stato toccato.
- `D:\repos\ralph`: cartella non-Git, nessun aggiornamento remoto applicabile.

### Verifica nuovi commit `ik_llama.cpp` origin/main 2026-06-16

Per evitare merge distruttivi sul repo principale sporco/divergente, `origin/main` e stato provato in un worktree isolato:

- Worktree: `D:\repos\ik_llama.cpp-origin-main-test`
- Commit testato: `064d23a6` (`Codex CLI Responses Compatibility (#1964)`)
- Build: `cmake --build ... --config Release -j 12`, CUDA ON, arch `86`, `LLAMA_CURL=OFF`
- Risultato build: successo; prodotti `llama-server.exe` e `llama-bench.exe` in `build-cuda-test\bin\Release`.
- Warning osservati: molti warning MSVC/NVCC gia non bloccanti (`C4244`, `C4267`, `#177-D`, `LNK4098`, duplicati `reasoning-budget` in `common.lib`). Nessun errore bloccante.

Benchmark rapido su `D:\repos\ik_llama.cpp\models\Qwen_Qwen3.5-4B-Q4_K_M.gguf`, `-p 128 -n 64 -ngl 999 -fa 1 -r 3`:

| Build | Commit | pp128 | tg64 | Note |
| --- | --- | ---: | ---: | --- |
| corrente locale | `0c55f51f` | `1315.12 +/- 567.29 t/s` | `55.98 +/- 0.39 t/s` | Build esistente in `D:\repos\ik_llama.cpp\build\bin\Release`. |
| `origin/main` isolato | `064d23a6` | `1393.58 +/- 499.29 t/s` | `55.83 +/- 0.21 t/s` | Prestazioni equivalenti sul modello piccolo; nessun vantaggio misurabile in TG. |

Smoke API su server isolato `127.0.0.1:18391`, modello Qwen3.5 4B:

- `/v1/chat/completions`: OK, risposta `ok`, schema `chat.completion` valido.
- `/v1/responses`: OK, risposta `ok`, schema `response` valido con `output[].content[].type = output_text`.

Conclusione pratica: vale la pena portare o cherry-pickare la compatibilità Responses API solo se serve davvero a OpenCode/Codex. I commit CUDA recenti non mostrano beneficio immediato sul Qwen3.5 4B piccolo; i possibili vantaggi per Qwen3.6/GQA 16 vanno misurati separatamente sui modelli grandi con i profili `llama-swap.config.yaml`. Non fare merge diretto di `origin/main` nel repo principale senza prima risolvere divergenza e modifiche locali.

### Condivisione del database Git (Worktree)
* `D:\repos\llama` e `D:\repos\llama-zaya` condividono lo stesso database Git sottostante tramite **Git Worktree**.
  * `D:\repos\llama` è associato al branch `master` (allineato all'upstream ufficiale `ggerganov/llama.cpp`).
  * `D:\repos\llama-zaya` è associato al branch locale di sviluppo `zaya-pr`.
  * **Cosa significa:** Aggiornare il branch `master` in `llama` (es. tramite `git pull`) aggiorna automaticamente anche il riferimento di `master` in `llama-zaya`. Non è possibile fare checkout di `master` direttamente nella cartella `llama-zaya` perché è già attivo nel worktree di `llama`.

---

## 2. Branch di Sviluppo Zaya (`zaya-pr`)
Il branch `zaya-pr` in `D:\repos\llama-zaya` contiene **28 commit locali** che implementano l'architettura **Zaya-1** (modello MoE con *Compressed Convolutional Attention* o CCA).

### Importanza
* **Non eliminare questo branch:** Questa è l'unica copia esistente di questa implementazione. Non è presente nell'upstream ufficiale `ggerganov/llama.cpp` né in `ikawrakow/ik_llama.cpp`.
* **Stato di allineamento:** Il tentativo di fare il merge dell'ultimo `master` (aggiornato al commit `94a220cd6`) in `zaya-pr` genera conflitti nei seguenti file:
  * `convert_hf_to_gguf.py`
  * `ggml/src/ggml-cuda/ssm-conv.cu`
  * `gguf-py/gguf/constants.py`
  * `gguf-py/gguf/tensor_mapping.py`
  * `src/llama-arch.cpp` / `src/llama-arch.h`
  * `src/llama-model.cpp` / `src/llama-model.h`
* **Cosa fare in futuro:** Se si desidera allineare lo sviluppo, i conflitti vanno risolti manualmente ed esclusivamente offline (tutte le operazioni Git sono locali e non caricano codice sui server remoti ufficiali).

---

## 3. Modello di Benchmarking (`sweep_small_models.py`)
Lo script `sweep_small_models.py` effettua il benchmark dei modelli tramite `D:\repos\ralph\local_ralph\coding_benchmark.py`.

### Configurazione Funzionante
* **Path dei modelli (Modificato):** Il percorso dei modelli in formato GGUF sul disco `F:` era originariamente configurato su `F:\LLM_Models\lm-studio\models`. È stato corretto nel percorso reale:
  ```python
  MODELS_CACHE = Path(r"F:\01_Modelli_AI\LLM_Models\lm-studio\models")
  ```
* **Interprete Python funzionante:** L'ambiente virtuale funzionante per avviare i benchmark è:
  `D:\repos\trading-algo\.venv-py312\Scripts\python.exe`
  *(Nota: In zsh/bash, usare gli slash in avanti `/` per evitare problemi di escape).*
* **Miglioramento dello script:** Abbiamo modificato la funzione `main()` di `sweep_small_models.py` in modo che:
  1. I risultati delle esecuzioni singole (`--single <model>`) vengano salvati automaticamente nel leaderboard `sweep_leaderboard.json` (prima venivano solo stampati a schermo).
  2. Gli aggiornamenti sovrascrivano i record esistenti identificati dallo stesso `label` evitando duplicati.

### Risultati degli Ultimi Test eseguiti sui 5 Modelli Incompleti:
* **`Qwen2.5-Coder-0.5B-Q4_K_M`**: **32/45** passati (`valid: false`).
* **`Qwen3-0.6B-Q8_0`**: **30/38** passati (`valid: false`).
* **`deepseek-coder-1.3B-kexer-Q4_K_M`**: **5/13** passati (`valid: false`).
* **`stable-code-instruct-3B-Q6_K`**: **8/8** passati (`valid: false` - eseguiti solo 8 task).
* **`Qwen3.5-0.8B-Q8_0`**: **0/0** passati (`valid: false` - falliti tutti i task tentati).

---

## 4. Attività Pianificate di Windows (Marketing)
Le attività pianificate di Windows legate al marketing e all'automazione (situate in `D:\projects\06-marketing`) sono state disabilitate con successo:
* `\OpenWolfOrchestrator` -> **Disabilitata** (Gestiva il posting programmato).
* `\StudioSmart-Email-Followup` -> **Disabilitata** (Gestiva i follow-up email giornalieri).
* `\StudioSmart-Email-Review` -> **Disabilitata** (Gestiva le richieste di recensioni giornaliere).

Tutte le attività mostrano ora lo stato `Disabilitato` in Task Scheduler e non verranno avviate automaticamente.
