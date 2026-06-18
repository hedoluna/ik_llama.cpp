# Router Locale OpenCode

Stato: **IMPLEMENTATO** (v1). Scegliere il modello giusto per ogni prompt senza riavviare OpenCode, scegliendo il modello minimo con alta probabilita di chiudere bene il task al primo colpo.

## Architettura

```
OpenCode -> shim 127.0.0.1:8291 -> llama-swap :8292 -> llama-server :9999 (uno per volta, GPU)
              |
              +-> classifier llama-server :9998 (qwen-small, -ngl 0, CPU, mai scaricato, fuori da llama-swap)
```

- **Shim** (`scripts/opencode-router.py`, Python stdlib): proxy OpenAI-compatible. Se `model` = `auto` (o `llama-swap/auto`) sceglie un modello concreto e inoltra a llama-swap; ogni altro id passa invariato (bypass = override manuale). Streaming SSE passthrough di default. Log decisioni in `bench-opencode-local/router-*.jsonl`.
- **Classifier**: istanza qwen-small dedicata su :9998, CPU (`-ngl 0`), sempre accesa, FUORI da llama-swap cosi L2 non sfratta mai il modello GPU principale. Sfrutta i 128 GB di RAM (zero VRAM).
- **Plugin** OpenCode (`~/.config/opencode/plugin/router-hints.ts`): solo stub best-effort (gli hook stabili non danno header per-turno). Il sistema funziona senza.

## Policy di routing

L1 = gate euristico deterministico (in ordine, primo match vince). L2 = classifier solo sugli ambigui. Stima token = `len(testo)//4`.

| Ordine | Regola | Condizione | Modello | Tier |
| --- | --- | --- | --- | --- |
| 1 | Override | testo contiene `!small/!fast/!coding/!quality/!hard/!max/!coder/!ita` | mappato | L1 |
| 2 | Big ctx | tokens >= 18000 | qwen36-iq3 (32k) | L1 |
| 3 | Hard | keyword (refactor, architettura, race condition, deadlock, optimize, ...) | qwen36-opus-iq4 | L1 |
| 4 | Coder | keyword (diff, apply patch, full file, implement, scaffold, ...) | qwen-coder | L1 |
| 5 | Trivial | tokens <= 60 e no code-fence | qwen-small | L1 |
| 6 | Italian | >=2 marker IT e no code-fence | cerbero-ita | L1 |
| 7 | Ambiguo | 60 < tokens < 400, nessun segnale | classify() -> mappa | L2 |
| 8 | Default | altro | qwen36-iq3 | L1 |

- **Hard/Coder prima di Trivial**: un prompt corto puo essere difficile ("refactor to remove the deadlock" e ~14 token ma va su opus, non su small).
- **Context guard**: se `tokens > ctx_modello * 0.75` -> bump a qwen36-iq3 (evita troncamento su opus/q5/q8/cerbero, ctx piu piccolo).
- **L2 classifier**: qwen-small (:9998), few-shot, `temp=0 max_tokens=5`, label in {TRIVIAL, NORMAL, HARD, CODER, ITALIAN}. Timeout 4s -> fallback qwen36-iq3.
- **Anti-thrash sticky** (per sessione, TTL 30 min): memorizza l'ultimo modello BIG; se prev BIG e nuova scelta BIG-diversa -> resta, salvo escalation HARD o de-escalation TRIVIAL. Lo swap big<->big rilancia il processo llama-server (caldo grazie ai 128 GB di page-cache, ma non gratis). `qwen-opus-q8` e solo override-only (mai auto).

Soglie e keyword sono nel blocco CONFIG in testa a `scripts/opencode-router.py`. Ritoccarle solo dopo dati reali.

## Uso

```powershell
# avvia tutto (llama-swap + classifier + router) e apre OpenCode in auto
ocl

# il routing e attivo in modalita auto (default). Modi espliciti = override manuale:
ocl -Mode quality     # forza qwen36-opus-iq4 (bypassa il router)
ocl -Mode max         # forza qwen-opus-q8
ocl -Run "..."        # non interattivo, anch'esso instradato dal router
```

Override inline dentro il prompt: iniziare con `!max`, `!quality`, `!coder`, `!ita`, `!small`, ecc.

Diagnostica streaming: `OPENCODE_ROUTER_NONSTREAM_MODELS=granite-fast` forza solo i modelli indicati a chiamare llama-swap in non-streaming e riconfezionare la risposta come SSE. Usarlo solo per debug di output vuoto/token 0: sblocca il parsing OpenCode in alcuni casi, ma puo aumentare molto la latenza e non e default operativo.

## Verifica

- Unit offline (no rete): `py scripts/test-router-routing.py` (gate L1, override, L2 mockato, sticky, adapter SSE diagnostico).
- Integrazione: `Invoke-RestMethod http://127.0.0.1:8291/v1/models` deve mostrare `auto`; POST `model=auto` sui 4 archetipi e controllare l'ultimo `bench-opencode-local/router-*.jsonl`.
- Latenza warm/cold swap e run 20-40 prompt reali: da eseguire nel tempo, log nel bench dir.

## Stato dettagliato

Configurazione operativa, classifica modelli, versioni e troubleshooting in [docs/opencode-local-llama-swap.md](D:/repos/ik_llama.cpp/docs/opencode-local-llama-swap.md).
