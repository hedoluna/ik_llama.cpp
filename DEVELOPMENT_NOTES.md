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
| `D:\repos\ralph` | Cartella locale non-Git (top-level) | nessun `.git` rilevato al top-level | Contiene `local_ralph\coding_benchmark.py`, usato da `sweep_small_models.py`. | ⚠️ **`D:\repos\ralph\local_ralph` è invece un repo Git nested proprio** (commit indipendenti dal parent) — comandi Git funzionano lì, non nel top-level `ralph\`. |
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

---

## 5. Aggiornamento Codice, Conflitti CUDA e Stress Test (02 Luglio 2026)

### Modifiche e Aggiornamenti Eseguiti
* **Git Sync**: Eseguito il merge di `origin/main` in `ik_llama.cpp` portando le modifiche dal 16 Giugno al 02 Luglio 2026.
* **Correzione Errore di Compilazione**:
  * **Cosa non ha funzionato**: La build di MSBuild/NVCC falliva su `oaidl.h(812)` del Windows SDK con `error: expected an identifier`. Il motivo risiedeva nella macro `#define CC_PASCAL 600` definita in `ggml-cuda/common.cuh` per denotare l'architettura Pascal GPU, la quale collideva con il tipo di convenzione di chiamata `CC_PASCAL` usata internamente negli header Windows (espansa a `600 = CC_MSCPASCAL`).
  * **Cosa ha funzionato**: La macro è stata rinominata in `GGML_CUDA_CC_PASCAL` in `common.cuh` e `convert.cu`, risolvendo definitivamente l'errore di preprocessore.
* **Aggiornamento Script**: Copiate le versioni sincronizzate di `sweep_small_models.py` e `sweep_advanced.py` da `ik-llama-bench`.

### Introduzione Stress Test Personalizzati
* Implementata una nuova suite in [sweep_stress_tests.py](file:///D:/repos/ik_llama.cpp/sweep_stress_tests.py) per valutare i modelli su 4 criteri critici reali:
  1. **Concurrency**: Scrittura di una coda thread-safe MPSC ed esecuzione con 10 thread produttori contemporanei per catturare deadlock e race condition.
  2. **Self-Correction**: Iterazione di debug su bug logico (mutamento liste durante ciclo), fornendo l'errore al modello per misurarne i tentativi di fix.
  3. **Tool-Calling**: Scelta intelligente di sequenze di chiamate API in situazioni di informazioni parziali/ambigue.
  4. **KV-Cache Pressure**: Estrazione di istruzioni nascoste in contesti lunghi (16K token commentati).

### Apprendimenti sui Modelli e Ottimizzazione Hardware
* **Ornith-1.0-9B-Q4_K_M** si conferma il miglior modello in assoluto per correttezza logica: **51/51** Base, **17/17** Advanced, e **4/4** Stress Test superati senza allucinazioni o rallentamenti.
* **Ornith-1.0-35B-A3B-IQ3_K_R4-imat** chiude a **17/17** Advanced, **50/51** Base e **4/4** Stress Test. Supera brillantemente la variante non-imatrix (`Ornith-1.0-35B-A3B-IQ3_K_R4`), la quale fallisce il test di Tool-Calling (allucina sequenze API incomplete), provando l'efficacia del calcolo basato su matrice d'influenza per agenti.
* **Qwen2.5-Coder-1.5B-Q4_K_M**: Si rivela un modello compatto straordinario. Totalizza **16/17** nell'Advanced, **51/51** nel Base e supera **4/4** Stress Test con tempi fulminei (es. Auto-Correzione in 0.4s).
* **Limiti VRAM (OOM)**: Il modello `Ornith-1.0-35B-A3B-Q4_K_M` (20 GB) fallisce per OOM in presenza di elevato carico grafico in background (con ~870MB VRAM occupati), in quanto richiede circa 6.1 GB di buffer CUDA sul lato GPU da 6GB. I modelli `IQ3_K_R4` (15 GB) risolvono questo limite senza swap lento.
* **SSD Optimization (30x Speedup)**: Spostando i tre modelli migliori (`Ornith-1.0-9B-Q4_K_M`, `Ornith-1.0-35B-A3B-IQ3_K_R4` e `Ornith-1.0-35B-A3B-IQ3_K_R4-imat`) dal disco lento `F:` (HDD/SATA) al disco principale NVMe `D:\repos\ik_llama.cpp\models`, il tempo di caricamento è crollato da **~160 secondi** a **5.4 secondi** per il modello 35B.

---

## 6. Ottimizzazione VRAM e Risoluzione Crash 35B (04 Luglio 2026)

### Cosa abbiamo fatto
* **Risolto crash in sweep**: Corretto il caricamento di `daily-Qwen3.6-35B-A3B-IQ3_K_R4` in `sweep_small_models.py`, eliminando il default `-ngl 999` e il batch eccessivo `-b 2048 -ub 2048`. Il modello è stato validato ottenendo **51/51** coding in **24.26s** senza crash.
* **Validato Ornith Imatrix**: Testato `Ornith-1.0-35B-A3B-IQ3_K_R4-imat` con gli stessi parametri ottenendo **50/51** coding (punteggio nominale previsto).
* **Allineamento Configurazione Stack**: Aggiornata la configurazione reale in `llama-swap.config.yaml` per `qwen36-iq3` e introdotto il nuovo modello `ornith-35b-iq3-imat` mappando i parametri del *Global Winner*.
* **Fix Script Stack**: Corretti errori di sintassi in `opencode-local.ps1` (blocco `agentByMode` parzialmente corrotto) e definito `SMALL_MODEL = "qwen-small"` mancante in `opencode-router.py`.
* **Creazione Wrapper OMP Locale (`oml`)**: Creati gli script `omp-local.ps1`, `omp-local.bat` e `oml.bat` per eseguire l'agente OMP in locale sfruttando lo stack OpenCode. Il wrapper intercetta e imposta `LM_STUDIO_BASE_URL` indirizzandolo a `llama-swap` (porta 8292) o al router (porta 8291), esponendo i modelli locali tramite il provider integrato `lm-studio` (con caching pre-popolato). Inoltre, supporta l'inoltro trasparente di qualsiasi flag o prompt non intercettato (es. `--continue`, `--auto-approve`, etc.).
* **Allineamento Limiti Context e Error Rewriting**: Allineato il limite di contesto per `qwen36-iq3` e `ornith-35b-iq3-imat` a **24000** in `opencode-router.py` per rispecchiare la configurazione reale di `llama-swap.config.yaml`. Aggiunto un intercettatore HTTP nel router che cattura gli errori 500 generati da `llama-server.exe` relativi al superamento del contesto e li riscrive nel formato standard OpenAI (`400 context_length_exceeded`), forzando l'agente OMP ad avviare la compattazione automatica invece di interrompere l'esecuzione.


### Apprendimenti e Successi
* **L'importanza dei micro-batch**: `-ub 256` mantiene il buffer temporaneo di calcolo CUDA a circa **800 MiB** (invece di ~1.9 GB con `-ub 2048`), permettendo di alloggiare i modelli MoE 35B nella VRAM limitata da 6 GB della RTX A2000.
* **Il ruolo di imatrix**: Come da stress test, l'influenza della matrice per quantizzazioni spinte (`IQ3`) rende `Ornith-imat` robusto per il tool-calling degli agenti locali rispetto alla versione base.

### Errori da non ripetere
* **Mai assumere che l'offload parziale MoE gestisca batch massivi su GPU ridotte**: Un batch di `2048` forza allocazioni CUDA non negoziabili che superano la memoria fisica della scheda, portando a crash silenziosi e successivi fallimenti di rete (*Connection Refused*).
* **Verificare sempre il rilascio VRAM**: Test paralleli o esecuzioni successive possono risentire di processi orfani `llama-server.exe` attivi. Usare sempre `opencode-local.ps1 -Stop` per pulire la VRAM.

---

## 7. Procedura standard "aggiorna i repo collegati" (06 Luglio 2026)

### Regole generali (valide per tutto il cluster `D:\repos`)
1. **Mai `reset --hard` / `pull` distruttivo senza controllare prima** `git status` e `git log` — specialmente su `ik_llama.cpp` che ha sempre lavoro locale non pulito e diverge da `origin/main`.
2. **Fetch prima di ogni decisione**: `git fetch origin` su ogni repo per vedere lo stato reale prima di scegliere l'azione (ff-only, merge, o nessuna azione).
3. **Repo puliti e semplicemente indietro → fast-forward diretto** (`git pull --ff-only origin <branch>`): sicuro, nessuna conferma necessaria. Vale per `llama` e `llama_mtp` (mirror upstream, nessun commit locale).
4. **Repo con worktree sporco ma già allineato a origin (`0 0` su `rev-list --left-right --count`) → non toccare**: il lavoro locale (`ik-llama-bench`: script/risultati; `trading-algo`: `.wolf`, `state/`) è dato prezioso, non stash/reset automatico.
5. **`ik_llama.cpp` (repo principale, ha commit locali + diverge da origin) → chiedere conferma esplicita all'utente prima del merge**, poi:
   - `git stash push -u -m "<descrizione>" -- <file modificati>` per i file sporchi non legati al merge (es. `sweep_leaderboard.json`, dati benchmark)
   - `git merge origin/main --no-edit` (mai rebase: preserva la history locale con 50+ commit propri)
   - `git stash pop` per ripristinare i file locali
   - Se il merge tocca file CUDA/kernel critici, **ricompilare e rilanciare uno smoke test** prima di considerare l'aggiornamento concluso (non fatto sistematicamente finora — vedi nota sotto).
6. **`llama-zaya` condivide il DB Git con `llama`** (stesso worktree): aggiornare `llama/master` aggiorna automaticamente il ref, ma `zaya-pr` (28 commit locali, unica copia di Zaya-1) **non va mai toccato/riallineato automaticamente** — merge di `master` in `zaya-pr` genera conflitti noti (vedi sezione 2), va fatto solo manualmente e offline.
7. **`ralph`** non è un repo Git: nessuna azione di aggiornamento possibile o necessaria.

### Comando di verifica divergenza (usato per ogni repo)
```bash
git fetch origin
git rev-list --left-right --count origin/<branch>...HEAD
# output "<dietro> <avanti>": primo numero = commit solo in origin (behind), secondo = commit solo in HEAD (ahead)
```

### Log aggiornamento 06 Luglio 2026
| Repo | Prima | Azione | Dopo |
|---|---|---|---|
| `llama` | 18 dietro | `pull --ff-only` | `ee445f93d` |
| `llama_mtp` | 32 dietro | `pull --ff-only` | `ee445f93d` |
| `llama-zaya` | — | nessuna (ref aggiornato via worktree condiviso con `llama`) | `zaya-pr` invariato |
| `llama_indras` | allineato | nessuna | invariato |
| `ik-llama-bench` | allineato, worktree sporco | nessuna | invariato |
| `trading-algo` | allineato, worktree sporco | nessuna | invariato |
| `ik_llama.cpp` | 9 dietro / 54 avanti, `sweep_leaderboard.json` modificato | stash → `merge origin/main --no-edit` → stash pop | `656c39f2`, 0 dietro / 55 avanti |

Il merge in `ik_llama.cpp` ha toccato kernel CUDA critici (flash-attention tile f16/f32, MLA decode Pascal, `iqk_flash_attn`).

### Rebuild + golden-check + re-bench top-5 (07 Luglio 2026, stesso giro)

* **1° rebuild FALSO POSITIVO**: `cmake --build | tail -60` ha riportato exit 0 ma il link falliva davvero (`LNK2019`/`LNK1120`, 2 unresolved `ggml_cuda_flash_attn_ext_vec_f32_case<576,512,...>`). Causa: il merge ha aggiunto 2 nuovi `.cu` in `ggml-cuda/template-instances/` (`fattn-vec-f32-instance-hs576-{f16-f16,q8_0-q8_0}.cu`) e il `file(GLOB ...)` in `ggml/src/CMakeLists.txt:276` non ha `CONFIGURE_DEPENDS` → serve reconfigure esplicito (`cmake -B build -S . -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DLLAMA_CURL=OFF -DGGML_NATIVE=ON`) prima del rebuild. Fix applicato, 2° build (senza pipe, redirect diretto su file) exit 0 reale, binari freschi.
* **Golden-check** (`golden_hash.py check`, solo i 2 job ik-affetti dal merge — i job mainline sono invariati): `qwen36-iq3kr4-daily` e `qwen36-opus-distill-r4` → **3/3 gate pass ciascuno** (prime/arith/json), zero regressione.
* **Re-bench top-5** (`sweep_small_models.py --single`, upsert manuale in `sweep_leaderboard.json` perché `--single` NON salva da solo — vedi codice `main()`, la nota "salvataggio automatico" di questo file sez.3 è superata):

| Modello | Score | Load | Bench |
|---|---:|---:|---:|
| daily-Qwen3.6-35B-A3B-IQ3_K_R4 | 51/51 | 6.6s | 24.9s |
| Ornith-1.0-9B-Q4_K_M | 51/51 | 3.6s | 43.4s |
| Ornith-1.0-35B-A3B-IQ3_K_R4-imat | 50/51 | 10.2s | 24.5s |
| Qwen2.5-Coder-1.5B-Q4_K_M | 51/51 | 13.1s | 5.0s |
| Mellum2-12B-A2.5B-Instruct-Q4_K_M | 51/51 | 4.6s | 22.2s |

Zero regressioni rispetto ai baseline storici (Ornith-imat 50/51 = fail task3 già noto, non nuovo). Aggiunta entry `Mellum2-12B-A2.5B-Instruct-Q4_K_M` a `TIERS[7]` in `sweep_small_models.py` (mancava, recipe da `reference_winner_configs.md`).

### Preflight-scorer gate + `--exec-trace` + roster cleanup (07 Luglio 2026, stessa giornata)

* `sweep_small_models.py` ora esegue `run_preflight()` (gate su `sweep_lib_sanity.preflight_scorer`) prima di ogni `--single`/`--tier` — prima non era mai invocato dal runner principale, solo da 2 script di nicchia. `--skip-preflight` per bypasso.
* Flag `--exec-trace`: esegue il tier "easy" (6 item) di `ik-llama-bench/sweep_bench_exec_trace.py` sullo stesso server già caricato, prima del teardown. Applicato subito sul top-5 (`sweep_leaderboard.json`): **daily-winner 4/6, Ornith-imat 5/6** vs **1-2/6** per Ornith-9B/Coder-1.5B/Mellum-Instruct — conferma che discrimina dove il coding-bench satura.
* `sweep_advanced.py` (17-task) rieseguito su 7 modelli: Ornith-1.0-35B-A3B (entrambi i quant) e Mellum2-12B **17/17**; Coder-1.5B/Ornith-9B 16/17; Yi-Coder-1.5B 14/17; **daily-winner 16/17** (era 17/17 storico — single-sample, da riverificare prima di chiamarla regressione).
* **Roster ripulito**: `Qwen2.5-Coder-32B-Instruct-IQ3_M` (dense 32B, `-ngl 15`, 23+ min per il solo advanced bench — 6 GiB VRAM non basta, hardware ceiling confermato) e `DeepSeek-Coder-V2-Lite-Instruct` (già "drop coding", 2 timeout storici da 900s) rimossi da `WINNERS`/`TIERS[7]` — commentati con motivazione, non cancellati.

