# OpenCode locale con ik_llama.cpp

Entrypoint operativo per usare OpenCode con i modelli locali di `ik_llama.cpp`.

Fonti canoniche:

- Stack, comandi quotidiani e troubleshooting: questo file.
- Policy di routing: [docs/opencode-router-piano.md](D:/repos/ik_llama.cpp/docs/opencode-router-piano.md).
- Elenco completo modelli e flag `llama-server`: [llama-swap.config.yaml](D:/repos/ik_llama.cpp/llama-swap.config.yaml).
- Graduatoria qualita/velocita locale: [docs/model-test-ranking.md](D:/repos/ik_llama.cpp/docs/model-test-ranking.md).
- Memoria operativa dei successi/fallimenti: [docs/benchmark-memory.md](D:/repos/ik_llama.cpp/docs/benchmark-memory.md).
- Benchmark e output prodotti: [bench-opencode-local/README.md](D:/repos/ik_llama.cpp/bench-opencode-local/README.md).
- Gotcha globali della repo: [CLAUDE.md](D:/repos/ik_llama.cpp/CLAUDE.md).

## Architettura

```text
OpenCode -> router 127.0.0.1:8291 -> llama-swap 127.0.0.1:8292 -> llama-server 127.0.0.1:9999
                                      |
                                      +-> classifier 127.0.0.1:9998
```

- OpenCode deve puntare a `http://127.0.0.1:8291/v1` e usare `auto` per il routing.
- Il router inoltra i model id concreti a `llama-swap`.
- `llama-swap` carica un solo modello GPU per volta su `127.0.0.1:9999`.
- Il classifier `qwen-small` resta separato su `127.0.0.1:9998` e non sfratta il modello GPU.

## Quick Start

Comando quotidiano da PowerShell o `cmd`:

```powershell
ocl
```

Con lo stato attuale la TUI nativa OpenCode e marcata rotta su Windows per errore OpenTUI DLL 126, quindi `ocl` apre direttamente la Web UI:

```text
http://127.0.0.1:4097/
```

Comandi utili:

```powershell
ocl -Run "Rispondi solo con OK."
ocl -Mode coding
ocl -Mode quality
ocl -Mode max
ocl -Web
ocl -Tui
ocl -Restart
```

Significato:

- `ocl`: avvia `llama-swap`, classifier e router se serve, poi apre OpenCode.
- `ocl -Run "..."`: esecuzione non interattiva; in `auto` passa dal router.
- `ocl -Mode coding`: forza `qwen36-iq3`.
- `ocl -Mode quality`: forza `qwen36-opus-iq4`.
- `ocl -Mode max`: forza `qwen-opus-q8`, piu lento e pesante.
- `ocl -Web`: apre direttamente la Web UI.
- `ocl -Tui`: ritenta la TUI nativa ignorando il marker di rottura.
- `ocl -Restart`: riavvia i processi locali.

Non lanciare due `opencode run` paralleli nella stessa directory: puo causare `database is locked`.

## Stato Operativo

Decisioni correnti:

- Default interattivo: routing `auto`, che normalmente finisce su `qwen36-iq3`.
- Default rapido: `qwen-small` per prompt semplici e `ocl -Run` quando il router lo ritiene sufficiente.
- Modello principale: Qwen3.6 35B A3B, soprattutto `qwen36-iq3`.
- Candidati, esclusioni e benchmark sono tracciati solo in [docs/model-test-ranking.md](D:/repos/ik_llama.cpp/docs/model-test-ranking.md).
- Workaround TUI: usare Web UI finche OpenCode/OpenTUI non risolve l'errore DLL 126.

Hardware rilevato durante la configurazione:

- GPU: NVIDIA RTX A2000 6GB.
- CPU: Ryzen 9 5950X, 16 core / 32 thread.
- RAM: circa 128GB.

Versioni verificate il 2026-06-07:

- OpenCode globale: `opencode-ai@1.16.2`.
- Binario Windows globale: `opencode-windows-x64@1.16.2`.
- Plugin config utente: `@opencode-ai/plugin@1.16.2`.
- Provider OpenAI-compatible config utente: `@ai-sdk/openai-compatible@2.0.48`.
- `llama-swap`: `223`, build `2026-06-04`.
- VC++ Redistributable 2015-2022 x64/x86: `14.51.36231.0`.

## File Configurati

| File | Scopo |
| --- | --- |
| `D:\repos\ik_llama.cpp\llama-swap.config.yaml` | Modelli locali e comandi `llama-server.exe`. |
| `C:\Users\orlan\.config\opencode\opencode.jsonc` | Provider locale e base URL verso il router. |
| `D:\repos\ik_llama.cpp\scripts\start-opencode-local.ps1` | Avvia/riavvia `llama-swap`, classifier e router. |
| `D:\repos\ik_llama.cpp\scripts\opencode-local.ps1` | Wrapper unico usato da `ocl`, `oclocal`, `opencode-local`. |
| `D:\repos\ik_llama.cpp\scripts\opencode-router.py` | Router OpenAI-compatible con policy `auto`. |
| `D:\repos\ik_llama.cpp\scripts\test-opencode-local.ps1` | Smoke test endpoint, modelli e chat completion. |
| `D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1` | Benchmark seriali OpenCode locali. |
| `D:\repos\ik_llama.cpp\scripts\fix-opencode-tui-vcredist.ps1` | Tentativo opzionale di fix VC++ per la TUI. |

Launcher in PATH utente:

```text
C:\Users\orlan\AppData\Roaming\npm\opencode-local.bat
C:\Users\orlan\AppData\Roaming\npm\ocl.bat
C:\Users\orlan\AppData\Roaming\npm\oclocal.bat
```

## Modelli Operativi

La configurazione completa vive in [llama-swap.config.yaml](D:/repos/ik_llama.cpp/llama-swap.config.yaml). Graduatoria, qualita, velocita e stato benchmark vivono solo in [docs/model-test-ranking.md](D:/repos/ik_llama.cpp/docs/model-test-ranking.md).

Profili principali disponibili:

- `auto`, `fast`, `coding`, `review`
- `quality-iq3`, `quality`, `max`
- `qwen36-mtp`, `qwopus9`, `qwen-coder-next`
- `mellum`, `mellum-thinking`
- `italian`, `granite`, `oss`

## Test

Smoke test consigliato:

```powershell
D:\repos\ik_llama.cpp\scripts\test-opencode-local.ps1 -Chat
```

Controlli manuali:

```powershell
opencode models llama-swap
Invoke-RestMethod http://127.0.0.1:8291/v1/models
Invoke-RestMethod http://127.0.0.1:8292/v1/models
```

Avvio manuale di `llama-swap`, solo per debug:

```powershell
D:\repos\ik_llama.cpp\bin\llama-swap.exe -config D:\repos\ik_llama.cpp\llama-swap.config.yaml -listen 127.0.0.1:8292 -watch-config
```

Nota: `llama-swap` usa `-config`, non `--config`. Con l'argomento sbagliato puo partire sulla porta default `:8080`, che OpenCode non usa.

## Benchmark

Script:

```powershell
D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1
```

Run consigliati:

```powershell
D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1 -Modes fast
D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1 -Modes fast,coding,quality
D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1 -Modes fast,coding,quality -IncludeMax
```

Run manuali rapidi:

```powershell
ocl -Mode quality-iq3 -Run "Rispondi solo con OK."
ocl -Mode qwen36-mtp -Run "Rispondi solo con OK."
ocl -Mode qwopus9 -Run "Rispondi solo con OK."
ocl -Mode mellum -Run "Rispondi solo con OK."
ocl -Mode mellum-thinking -Run "Rispondi solo con OK."
```

Output e baseline sono documentati in [bench-opencode-local/README.md](D:/repos/ik_llama.cpp/bench-opencode-local/README.md).
Graduatoria unica e conclusioni sui modelli sono in [docs/model-test-ranking.md](D:/repos/ik_llama.cpp/docs/model-test-ranking.md).

## Troubleshooting

OpenCode non vede `llama-swap/*`:

```powershell
D:\repos\ik_llama.cpp\scripts\test-opencode-local.ps1
opencode models llama-swap
```

Endpoint non risponde:

```powershell
D:\repos\ik_llama.cpp\scripts\start-opencode-local.ps1 -Restart
```

Porta aperta ma endpoint sbagliato:

```powershell
Get-Process llama-swap,llama-server,python -ErrorAction SilentlyContinue
```

Riavviare con `-Restart` se i processi sono quelli locali sotto `D:\repos\ik_llama.cpp`.

Risposte vuote con Qwen:

- Verificare che nel comando `llama-server.exe` ci siano `--jinja` e `--reasoning off`.
- Controllare `D:\repos\ik_llama.cpp\logs\llama-swap.err.log`.

Modello troppo lento o memoria insufficiente:

- Usare `ocl -Mode fast` o `ocl -Run "..."`.
- Ridurre `--ctx-size` o `-ngl` nel modello in `llama-swap.config.yaml`.
- Riavviare con `ocl -Restart`.

Provider custom non carica il pacchetto npm:

```powershell
cd C:\Users\orlan\.config\opencode
npm install
```

TUI nativa OpenCode rotta:

```text
Failed to initialize OpenTUI render library: Failed to open library "B:/~BUN/root/opentui-*.dll": error code 126
```

Il marker che forza il fallback Web UI e:

```text
C:\Users\orlan\.local\state\opencode-local\opentui-broken.marker
```

Per ritentare:

```powershell
ocl -Tui
```

Errore Windows `WSAEACCES` su porte locali:

- Vedere il gotcha in [CLAUDE.md](D:/repos/ik_llama.cpp/CLAUDE.md).
- Le porte operative attuali sono sotto la reservation floor osservata: router `8291`, llama-swap `8292`, classifier `9998`.

## Prossimi Passi

- Aggiornare solo [docs/model-test-ranking.md](D:/repos/ik_llama.cpp/docs/model-test-ranking.md) quando cambiano qualita, velocita o decisioni sui modelli.
- Misurare il router su 20-40 prompt reali e ritoccare soglie/keyword solo con dati.
- Rivedere `--ctx-size` e `-ngl` dopo benchmark reali su memoria e velocita.
- Riprovare `ocl -Tui` dopo un update OpenCode/OpenTUI successivo alla `1.16.2`.
