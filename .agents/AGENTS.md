# Project-Scoped Rules & Knowledge - ik_llama.cpp

Questo file memorizza le regole locali e gli apprendimenti critici relativi a questo workspace, utili per le future istanze di agenti che lavoreranno qui.

---

## 1. Linee Guida di Compilazione CUDA su Windows

### Collisione Nomi Preprocessore (CC_PASCAL)
* **Problema**: L'SDK di Windows (in particolare `oaidl.h`) definisce un valore enum denominato `CC_PASCAL`. Se includiamo gli header di `ggml` o CUDA prima o dopo, la definizione `#define CC_PASCAL 600` contenuta in `common.cuh` genera un errore di compilazione `error: expected an identifier` su MSVC/NVCC.
* **Regola**: **NON utilizzare `CC_PASCAL`**. Utilizzare sempre **`GGML_CUDA_CC_PASCAL`** sia in `common.cuh` sia in `convert.cu` o altri moduli CUDA del repository.

### Comando di Build Consigliato per questa Macchina
```powershell
# Configurazione CMake per CUDA Compute Capability 86 (RTX A2000)
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DLLAMA_CURL=OFF

# Compilazione incrementale Release
cmake --build build --config Release -j
```

---

## 2. Archiviazione Modelli & Vincoli Hardware

* **CPU**: AMD Ryzen 9 5950X (16 core, 32 thread) -> Ottimo per offloading MoE.
* **RAM**: 128 GB -> Spazio abbondante per ospitare gli esperti dei modelli MoE.
* **GPU**: NVIDIA RTX A2000 (6 GB VRAM).
  * **Limite di memoria**: I modelli MoE da 35B in formato `Q4_K_M` (~20 GB) causano frequentemente **OOM (Out Of Memory)** o fortissimi rallentamenti di paging WDDM su questa GPU quando vi sono altre risorse grafiche allocate in background (~800MB usati).
  * **Regola**: Preferire sempre e configurare modelli MoE in formato **`IQ3_K_R4`** o inferiori (circa 15 GB), come ad esempio `Ornith-1.0-35B-A3B-IQ3_K_R4-imat` o `daily-Qwen3.6-35B-A3B-IQ3_K_R4`.
  * **Parametri per evitare crash (OOM) su 35B**:
    * **Batch/Ubatch limitati**: Impostare sempre `-b 1024` e `-ub 256` (o inferiori). Valori come `2048` aumentano a dismisura il buffer di calcolo CUDA (~1.9 GB) causando crash OOM immediati.
    * **Offload esperti (`--n-cpu-moe 30` e `-ngl 95`)**: Per far entrare i modelli MoE 35B in 6 GB di VRAM, non utilizzare mai `-ngl 999` e limitare gli esperti attivi su GPU. A contesti lunghi (>24k), utilizzare `--cpu-moe` (tutti gli esperti su CPU).
    * **KV Cache asimmetrica**: Quantizzare la cache con `-ctk q4_0` e `-ctv q8_0` per dimezzare l'uso di memoria KV.

* **Storage**:
  * I modelli migliori sono memorizzati localmente sul percorso veloce NVMe **D:**:
    `D:\repos\ik_llama.cpp\models\`
  * Non spostare o referenziare questi modelli da unità HDD lente (come `F:`), in quanto il caricamento passerebbe da **5.4 secondi** (SSD) a **160 secondi** (HDD).

---

## 3. Suite di Test e Benchmark Locali

* **Benchmark Base (51 task)**: [sweep_small_models.py](file:///D:/repos/ik_llama.cpp/sweep_small_models.py)
* **Benchmark Avanzato (17 task)**: [sweep_advanced.py](file:///D:/repos/ik_llama.cpp/sweep_advanced.py)
* **Stress Test (Concorrenza, Auto-Correzione, Tool-Calling, KV-Cache)**: [sweep_stress_tests.py](file:///D:/repos/ik_llama.cpp/sweep_stress_tests.py)
* **Interprete Python da utilizzare**: `D:\repos\trading-algo\.venv-py312\Scripts\python.exe`

---

## 4. Evidenze Critiche dai Test Logici e di Stress

* **Importanza del tuning Imatrix**: La quantizzazione con calcolo imatrix (`Ornith-1.0-35B-A3B-IQ3_K_R4-imat`) supera tutti e 4 gli stress test, mentre la versione base non-imatrix (`Ornith-1.0-35B-A3B-IQ3_K_R4`) fallisce sistematicamente il test di Tool-Calling (allucinando chiamate API parziali). Il tuning imatrix è **essenziale** per compiti di agenti ed esecuzioni complesse.
* **Scelta del Co-Pilota Leggero (1.5B)**: Il modello `Qwen2.5-Coder-1.5B-Q4_K_M` si dimostra incredibilmente solido, ottenendo **16/17** nel test avanzato e **4/4** negli stress test con i tempi di risposta più veloci. Da preferire per il coding veloce locale.
* **Limiti dei Modelli Minori sotto Pressione Context**: Modelli come `Yi-Coder-1.5B-Chat` tendono a fallire l'estrazione di istruzioni complesse da ampi contesti (16K commenti), denotando problemi di "needle-in-a-haystack" tipici dei pesi inferiori a 3B.
* **Wrapper OMP locale (`oml`)**: Creato il wrapper `oml.bat` per usare l'agente `omp` con modelli locali. Mappa gli stessi alias di OpenCode (`big`, `ornith`, `fast`, etc.) ed inoltra qualsiasi argomento aggiuntivo o flag (es. `--continue`, `--auto-approve`, `--thinking` o prompt diretti) direttamente all'agente `omp` (esposto tramite il provider locale `lm-studio` a 8292/8291).
---

## 5. Delega ad Ralph (Agente Autonomo locale)

### Avvio dello Stack LLM Locale
* **Prerequisito**: Lo stack LLM locale NON è attivo di default. Avviarlo con:
  ```powershell
  powershell -ExecutionPolicy Bypass -File D:/repos/ik_llama.cpp/scripts/start-opencode-local.ps1 -Restart
  ```
  Avvia: llama-swap su `http://127.0.0.1:8292/v1`, classifier su `9998`, router su `8291`.
* **Verifica**: fetch `http://127.0.0.1:8292/v1/models` → JSON con ~50 modelli (alias llama-swap).
* **Path PowerShell da bash**: Usare SEMPRE forward slash (`D:/repos/...`) mai backslash singoli (vengono strippati dal shell embedding).

### Workflow TDD con Ralph
* **Pattern collaudato**: Scrittura test (spec vincolante) → PRD JSON → Ralph implementa → fix manuale se stall.
* **Struttura PRD** (`.ralph/prd.json` nel target project):
  * `test_cwd`, `test_command` (es. `npm test`), `target_file`, `context_files`
  * `obiettivo`: descrizione testuale del task
  * Regole specifiche (es. `progression_rules`, `combat_rules`) con formule esatte
  * `architecture`: hints per domain/application/ui layers
  * `tasks[].acceptance_criteria[]` e `definition_of_done[]`
* **Esecuzione**: `powershell -File D:/repos/<project>/.ralph/ralph.ps1 -Reset` (async, timeout=0)
* **Modello**: `quality-iq3` (= Ornith-1.0-35B-A3B-IQ3_K_R4-imat) via `.model_config`

### Root Cause e Guardrail Implementati (2026-07)
* **⚠️ ROOT CAUSE PRIMARIO (risolto)**: Il system prompt di `brain_manager.py` **contraddiceva** il `prompt_powershell.md`. Il system prompt diceva "usa here-string `@'<a capo>...'@` e scrivi il file INTERO", mentre il prompt utente diceva "usa blocchi `<edit>` mirati, NON here-string". Il system prompt ha precedenza → il modello usava here-string + `<a capo>` + riscritture integrali, causando tutti i sintomi downstream.
* **Fix system prompt**: Riscritto `default_system` in `brain_manager.py` per allinearsi con l'approccio edit-based: "usa `<edit>` SEARCH/REPLACE, NON here-string, NON `<a capo>`".
* **Fix temperature**: Ridotta da 0.7 → 0.1 (default, configurable via `RALPH_TEMPERATURE`). Coding deterministico richiede bassa temperatura.
* **Guardrail SYNTAX GATE (implementato)**: L'harness ora esegue `node --check` dopo ogni `<edit>` su file `.js`/`.mjs`/`.cjs`. Se l'edit produce un SyntaxError, **l'harness reverte automaticamente** il file allo stato precedente e logga `EDIT REVERTITO` + `ERRORE_SINTASSI` + `SUGGERIMENTO` in memoria. Il modello vede sempre l'ultimo stato valido.
* **Backup automatico**: Ogni edit viene preceduto da backup `.ralph_bak`. Revert garantito su syntax error.
* **Multi-edit cumulativo**: Più `<edit>` nello stesso file nella stessa risposta vengono applicati sequenzialmente in memoria, non richiedendo re-read da disco.
* **Prompt aggiornato**: Regola esplicita "un edit per metodo/funzione" + "bilancia le parentesi graffe" aggiunta a `prompt_powershell.md`.
* **Regola pratica residua**: Per modifiche complesse al application layer (classi multi-metodo), Ralph ora ha il syntax gate come rete di sicurezza. Se il modello produce 3+ revert di fila, intervenire manualmente.
* **Guard A — npm test interception (implementato)**: Se il modello lancia `npm test`, l'harness lo intercetta con `SALTATO: npm test vietato al modello` e risparmia l'iterazione. Il test lo esegue sempre l'harness dopo ogni edit.
* **Guard B — `<a capo>` sanitization (implementato)**: I modelli italiani emettono `<a capo>` invece di newline nelle here-string, corrompendo PowerShell. L'harness sanitizza `<a capo>` → `` `n `` prima dell'esecuzione.
* **Guard C — PEGGIORATO auto-revert (implementato)**: Se i test peggiorano dopo un edit (più failure di prima), l'harness reverte automaticamente tutti i file editati allo stato pre-edit. Il modello vede sempre l'ultimo stato non-peggiornato.
* **Guard D — Context injection dei moduli dipendenti (implementato)**: `Get-ModuleSignatures` in `Build-Prompt` scansiona gli `import` del file target, risolve i moduli relativi, ed inietta le signature delle funzioni/classi/const esportate. Il modello vede l'API reale → zero allucinazioni.

### Progetti Collegati in D:\repos
* **text-rpg-online** (`D:\repos\text-rpg-online`, repo: `hedoluna/text-rpg-online`): RPG testuale "Cronache di Asteria". Stack: Node 22+, ESM, `node --test`. 31 test (world + items + combat + progression + training). UI: HTML+JS vanilla, persistenza via here.now Site Data. **Pubblicato su: https://stormy-cairn-esr7.here.now/**. Deploy: `node publish.mjs` (jq-free, puro Node.js). **Workflow post-modifica**: dopo ogni fix/feature → sync `src/` → `site/` → `npm test` → `node publish.mjs` → commit+push.
* **ralph** (`D:\repos\ralph`): Harness agente autonomo. `local_ralph/ralph.ps1` + `brain_manager.py`. Benchmark codici in `local_ralph/coding_benchmark_*.py`.
* **remotica2** (`D:\repos\remotica2`): Progetto primario (piattaforma coworking). Pattern: Single File API, monorepo.

