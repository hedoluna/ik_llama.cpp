# Note di Sviluppo e Apprendimenti - Repository Llama & Benchmarks
*Ultimo aggiornamento: 2026-06-03*

Questo documento raccoglie la struttura dei repository, gli apprendimenti derivanti dagli aggiornamenti, lo stato dei benchmark e le impostazioni di sistema relative al marketing automatizzato per evitare perdite di tempo in futuro.

---

## 1. Struttura dei Repository & Git Worktrees
Tutti i repository legati a Llama si trovano in `D:\repos`.

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
