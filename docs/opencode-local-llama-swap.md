# OpenCode locale con ik_llama.cpp

Questa installazione usa `llama-swap` come proxy OpenAI-compatible davanti a `llama-server.exe`.
OpenCode parla con un solo endpoint locale (`http://127.0.0.1:9292/v1`); `llama-swap` carica il modello richiesto dal campo `model` e scarica quello precedente.

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

- `ocl`: avvia `llama-swap` se serve e apre OpenCode.
- `ocl -Run "..."`: esecuzione non interattiva; in `auto` usa `qwen-small`.
- `ocl -Mode coding`: forza il default principale `qwen36-iq3`.
- `ocl -Mode quality`: prova `qwen36-opus-iq4`.
- `ocl -Mode max`: usa il Q8, piu lento e pesante.
- `ocl -Web`: apre direttamente la Web UI.
- `ocl -Tui`: ritenta la TUI nativa ignorando il marker di rottura.
- `ocl -Restart`: riavvia i processi locali `llama-swap` / `llama-server`.

Non lanciare due `opencode run` paralleli nella stessa directory: puo causare `database is locked`.

## Decisioni Correnti

- Default interattivo: `llama-swap/qwen36-iq3`.
- Default non interattivo (`ocl -Run` in `auto`): `llama-swap/qwen-small`, perche OpenCode invia circa 14k token anche per prompt brevi.
- Focus principale: Qwen3.6 35B A3B, soprattutto `qwen36-iq3`.
- Candidati qualita da misurare ancora: `qwen36-opus-iq4`, `qwen36-q5`, `qwen-opus-q8`.
- `granite-fast` e `gpt-oss-20b` non sono candidati principali in questa configurazione: i test iniziali sono stati lenti/non puliti.
- Workaround TUI: usare Web UI finche OpenCode/OpenTUI non risolve l'errore DLL 126.

Automaticita attuale:

- `llama-swap` cambia modello automaticamente quando OpenCode richiede un model id diverso.
- `ocl` sceglie automaticamente `qwen-small` per `-Run` in modalita `auto`.
- `ocl` sceglie automaticamente `qwen36-iq3` per uso interattivo in modalita `auto`.
- Non esiste ancora routing semantico vero basato sul contenuto del task; per quello servirebbe uno shim/router custom o LiteLLM.

Routing da chiarire:

- OpenCode sceglie il modello all'avvio, non per-request.
- Il routing semantico vero richiede uno shim/router persistente davanti a `llama-swap`.
- `small_model` serve per task leggeri, non come router semantico.
- I dettagli della policy e del flusso stanno in [docs/opencode-router-piano.md](D:/repos/ik_llama.cpp/docs/opencode-router-piano.md).

## File Configurati

| File | Scopo |
| --- | --- |
| `D:\repos\ik_llama.cpp\llama-swap.config.yaml` | Modelli locali e comandi `llama-server.exe`. |
| `C:\Users\orlan\.config\opencode\opencode.jsonc` | Provider `llama-swap`, default model, agenti OpenCode. |
| `D:\repos\ik_llama.cpp\scripts\start-opencode-local.ps1` | Avvia/riavvia `llama-swap` su `127.0.0.1:9292`. |
| `D:\repos\ik_llama.cpp\scripts\opencode-local.ps1` | Wrapper unico usato da `ocl`, `oclocal`, `opencode-local`. |
| `D:\repos\ik_llama.cpp\scripts\test-opencode-local.ps1` | Smoke test endpoint, modelli e chat completion. |
| `D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1` | Benchmark seriali OpenCode locali. |
| `D:\repos\ik_llama.cpp\scripts\fix-opencode-tui-vcredist.ps1` | Tentativo opzionale di fix VC++ per la TUI. |

Launcher in PATH utente:

```text
C:\Users\orlan\AppData\Roaming\npm\opencode-local.bat
C:\Users\orlan\AppData\Roaming\npm\ocl.bat
C:\Users\orlan\AppData\Roaming\npm\oclocal.bat
```

`C:\Users\orlan\AppData\Roaming\npm` e gia nel PATH utente.

## Modelli

| Profilo OpenCode | Modello llama-swap | File GGUF | Uso |
| --- | --- | --- | --- |
| `coding`, `review`, `auto` | `qwen36-iq3` | `Qwen3.6-35B-A3B-IQ3_K_R4.gguf` | Default principale. |
| `quality` | `qwen36-opus-iq4` | `Qwen3.6-35B-A3B-Opus-Distill-IQ4_K_R4.gguf` | Candidato qualita. |
| manuale | `qwen36-q5` | `Qwen3.6-35B-A3B-bartowski-Q5_K_M.gguf` | Candidato piu pesante da confrontare. |
| `max` | `qwen-opus-q8` | `Qwen3.6-35B-A3B-Opus-Distill-Q8_0.gguf` | Massima qualita locale, aspettarsi latenza alta. |
| `fast`, `auto` con `-Run` | `qwen-small` | `Qwen_Qwen3.5-4B-Q4_K_M.gguf` | Prompt rapidi e comandi non interattivi. |
| `qwen-coder-next` | `qwen-coder` | `Qwen3-Coder-Next-UD-Q3_K_XL.gguf` | Fallback/candidato coding. |
| `italian` | `cerbero-ita` | `cerbero-7b.Q4_K_M.gguf` | Italiano leggero. |
| `granite` | `granite-fast` | `ibm-granite_granite-4.1-8b-Q4_K_M.gguf` | Tenuto configurato, non preferito. |
| `oss` | `gpt-oss-20b` | `gpt-oss-20b-mxfp4.gguf` | Tenuto configurato, non preferito. |

Hardware rilevato durante la configurazione:

- GPU: NVIDIA RTX A2000 6GB.
- CPU: Ryzen 9 5950X, 16 core / 32 thread.
- RAM: circa 128GB.

## Test

Smoke test consigliato:

```powershell
D:\repos\ik_llama.cpp\scripts\test-opencode-local.ps1 -Chat
```

Controllo modelli lato OpenCode:

```powershell
opencode models llama-swap
```

Endpoint diretto:

```powershell
Invoke-RestMethod http://127.0.0.1:9292/v1/models
```

Ultima verifica rapida del 2026-06-07:

- `test-opencode-local.ps1 -Chat`: OK.
- `opencode models llama-swap`: vede tutti i 9 modelli configurati in OpenCode.
- `ocl -Run "Rispondi solo con OK."`: OK, auto-seleziona `fast` / `qwen-small`.
- API diretta `qwen36-iq3`: OK, risposta `OK` in circa 25.6s includendo lo switch/caricamento modello.

Avvio manuale di `llama-swap`, solo per debug:

```powershell
D:\repos\ik_llama.cpp\bin\llama-swap.exe -config D:\repos\ik_llama.cpp\llama-swap.config.yaml -listen 127.0.0.1:9292 -watch-config
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

Output:

- CSV: `D:\repos\ik_llama.cpp\bench-opencode-local\summary-*.csv`
- JSONL: `D:\repos\ik_llama.cpp\bench-opencode-local\details-*.jsonl`
- Note sintetiche: `D:\repos\ik_llama.cpp\bench-opencode-local\README.md`

Baseline utili del 2026-06-06:

| Profilo | Modello | Task | Durata osservata |
| --- | --- | --- | --- |
| `fast` | `qwen-small` | 3 task brevi | circa 7.8-11.8s |
| `coding` | `qwen36-iq3` | 3 task brevi | circa 64-97s |
| `granite,coding,oss` | misto | run parziale | utile solo come segnale negativo per `granite` / `oss` |

Smoke test API raw:

| Modello | Prompt tok/s | Gen tok/s | Stato |
| --- | ---: | ---: | --- |
| `qwen36-iq3` | 36.4 | 28.4 | OK |
| `qwen36-opus-iq4` | 34.7 | 28.8 | OK |
| `qwen36-q5` | 35.9 | 25.6 | OK |

## Cosa Funziona

- OpenCode `1.16.2` vede il provider locale `llama-swap`.
- `llama-swap` v223 risponde su `http://127.0.0.1:9292/v1`.
- `opencode run` funziona.
- `opencode web` funziona.
- `ocl`, `oclocal`, `opencode-local` funzionano da PowerShell e `cmd`.
- Il fallback automatico alla Web UI funziona quando la TUI fallisce.
- `test-opencode-local.ps1 -Chat` valida endpoint, modelli e completion breve.
- `bench-opencode-local.ps1` produce CSV/JSONL.

## Cosa Non Funziona

- TUI nativa OpenCode `1.16.2` su questa macchina:

```text
Failed to initialize OpenTUI render library: Failed to open library "B:/~BUN/root/opentui-*.dll": error code 126
```

- L'errore avviene da PowerShell 7, Windows PowerShell e `cmd`.
- VC++ Redistributable 2015-2022 x64/x86 e stato aggiornato a `14.51.36231.0`, ma non ha risolto.
- Poiche `opencode run` e `opencode web` funzionano, il problema non e nei modelli locali o in `llama-swap`.
- Esiste almeno un report pubblico con errore OpenCode/OpenTUI identico su Windows; probabile bug/compatibilita OpenTUI/Bun.

Marker TUI rotta:

```text
C:\Users\orlan\.local\state\opencode-local\opentui-broken.marker
```

Finche esiste, `ocl` apre direttamente la Web UI. Per ritentare:

```powershell
ocl -Tui
```

## Versioni Verificate

Aggiornato il 2026-06-07:

- OpenCode globale: `opencode-ai@1.16.2`
- Binario Windows globale: `opencode-windows-x64@1.16.2`
- Plugin config utente: `@opencode-ai/plugin@1.16.2`
- Provider OpenAI-compatible config utente: `@ai-sdk/openai-compatible@2.0.48`
- `llama-swap`: `223`, build `2026-06-04`
- VC++ Redistributable 2015-2022 x64/x86: `14.51.36231.0`

Comandi usati per aggiornare OpenCode:

```powershell
npm install -g opencode-ai@latest opencode-windows-x64@latest
cd C:\Users\orlan\.config\opencode
npm install @opencode-ai/plugin@latest @ai-sdk/openai-compatible@latest
```

Warning npm osservati ma non bloccanti:

- Install script non ancora approvati per `opencode-ai` e `msgpackr-extract`.
- `ini@7.0.0` richiede `node ^22.22.2 || ^24.15.0 || >=26.0.0`; il sistema aveva `node v22.22.0`.

Backup creati:

```text
C:\Users\orlan\.config\opencode\opencode.jsonc.bak-local-llama
D:\repos\ik_llama.cpp\llama-swap.config.yaml.bak-local-llama
```

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

Porta aperta ma non e `llama-swap`:

```powershell
Get-Process llama-swap,llama-server -ErrorAction SilentlyContinue
```

Poi riavviare con `-Restart` se i processi sono quelli locali sotto `D:\repos\ik_llama.cpp`.

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

## Memoria Operativa

Questa sezione e solo un indice di memoria. I dettagli operativi sono gia sopra in `Routing da chiarire`, `Cosa Funziona`, `Cosa Non Funziona`, `Classifica Modelli` e `Prossimi Passi`.

- Punto fermo: `llama-swap` centralizza i modelli locali.
- Punto fermo: `ocl` e il comando quotidiano.
- Punto fermo: `qwen36-iq3` resta il default interattivo.
- Punto fermo: `qwen-small` resta il filtro veloce per `-Run`.
- Punto fermo: la TUI nativa OpenCode su Windows resta rotta, quindi la Web UI e il fallback stabile.
- Piano routing separato: [docs/opencode-router-piano.md](D:/repos/ik_llama.cpp/docs/opencode-router-piano.md).

## Classifica Modelli

Questa e una classifica operativa, non un leaderboard assoluto. Tiene insieme:

- benchmark gia fatti
- tempi osservati
- qualita percepita sulle prove brevi
- ruolo del modello nel flusso OpenCode

### Tier 0 - Scrematura Rapida

1. `qwen-small`
   - Miglior scelta per `ocl -Run`.
   - Miglior compromesso velocita/affidabilita per task brevi, note, risposte immediate, prime bozza.
   - E il modello giusto per filtrare rapidamente richieste semplici prima di salire di livello.

### Tier 1 - Default Operativo

2. `qwen36-iq3`
   - Default principale per coding interattivo.
   - E il miglior punto di equilibrio attuale tra velocita e capacita generale.
   - E il candidato piu affidabile per la maggior parte dei task reali.

### Tier 2 - Qualita Maggiore

3. `qwen36-opus-iq4`
   - Candidato serio per sostituire il default se i benchmark reali mostrano un guadagno netto.
   - Da preferire quando vuoi piu accuratezza e un po' meno fretta.

4. `qwen36-q5`
   - Candidato intermedio tra default e massimo.
   - Utile se `qwen36-opus-iq4` non basta ma `qwen-opus-q8` e troppo lento.

### Tier 3 - Massima Qualita Locale

5. `qwen-opus-q8`
   - Da usare solo quando la qualita conta piu della latenza.
   - E il profilo da riserva per task difficili, analisi ampie, refactor importanti.

### Tier Specializzati

6. `qwen-coder`
   - Da tenere come candidato specializzato per coding.
   - Utile da confrontare, ma non ancora abbastanza validato per essere default.

7. `cerbero-ita`
   - Profilo utile per italiano e testo naturale in italiano.
   - Non e il modello principale per coding tecnico.

### Tier Non Preferiti

8. `granite-fast`
   - Tenuto configurato, ma i test iniziali non lo rendono una scelta primaria per OpenCode locale.

9. `gpt-oss-20b`
   - Tenuto configurato, ma non ancora convincente come scelta principale nel flusso attuale.

### Classifica Per Uso

Se vogliamo scegliere velocemente senza pensarci troppo:

- `fast`: `qwen-small`
- `coding`: `qwen36-iq3`
- `review`: `qwen36-iq3`
- `quality`: `qwen36-opus-iq4`
- `max`: `qwen-opus-q8`
- `italian`: `cerbero-ita`
- `qwen-coder-next`: `qwen-coder`
- `granite`: solo se vogliamo testarlo esplicitamente
- `oss`: solo se vogliamo testarlo esplicitamente

### Criterio Di Routing

Routing semantico vero, se lo implementiamo, dovrebbe fare solo questo:

- prima scrematura con `qwen-small`
- salire a `qwen36-iq3` per quasi tutto il coding
- passare a `qwen36-opus-iq4` o `qwen36-q5` quando il task sembra richiedere piu precisione
- usare `qwen-opus-q8` solo quando il costo di latenza e accettabile

La regola utile non e "scegli sempre il modello piu grande".
La regola utile e "scegli il modello minimo che ha probabilita alta di chiudere bene il task al primo colpo".

## Decision Log

2026-06-07:

- Confermato che TUI OpenCode fallisce ancora dopo aggiornamento VC++.
- Confermato che `opencode run` e `opencode web` funzionano: provider locale sano.
- Decisione: usare Web UI come workaround stabile.
- Deduplicata questa documentazione per tenerla come fonte operativa.

2026-06-06:

- OpenCode aggiornato da `1.4.3` a `1.16.2`.
- Installato `llama-swap` v223.
- Configurato provider OpenCode `llama-swap` con `@ai-sdk/openai-compatible`.
- Creati launcher `opencode-local`, `ocl`, `oclocal`.
- Configurato default locale `qwen36-iq3`.
- Eseguiti benchmark iniziali `fast/qwen-small` e `coding/qwen36-iq3`.

## Prossimi Passi

- Misurare latenza e qualita dei profili `fast`, `coding`, `quality`, `max` su task reali.
- Valutare se `qwen36-opus-iq4` migliora abbastanza da sostituire `qwen36-iq3`.
- Benchmarkare `qwen36-q5` e `qwen-opus-q8` solo se serve piu qualita e si accetta latenza maggiore.
- Rivedere `--ctx-size` e `-ngl` dopo benchmark reali su memoria e velocita.
- Riprovare `ocl -Tui` dopo un update OpenCode/OpenTUI successivo alla `1.16.2`.
- Valutare uno shim/router OpenAI-compatible custom solo se serve routing semantico vero.
- Sistemare LiteLLM solo se serve davvero routing avanzato.
