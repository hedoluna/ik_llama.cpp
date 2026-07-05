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

