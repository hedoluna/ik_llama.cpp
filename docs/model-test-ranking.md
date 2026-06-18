# Graduatoria modelli testati

Ultimo aggiornamento: 2026-06-18.

Questa e l'unica graduatoria locale da aggiornare. I file JSON/CSV restano dati raw; README e guide operative devono linkare questa pagina invece di duplicare classifiche. La memoria di cosa abbiamo imparato e cosa evitare sta in [docs/benchmark-memory.md](D:/repos/ik_llama.cpp/docs/benchmark-memory.md).

Non e un benchmark assoluto: i test hanno prompt, tempi e hardware diversi. Usarla come indice operativo per scegliere cosa ritestare e quale modello mettere nelle caselle OpenCode.

Hardware locale rilevante: Ryzen 9 5950X, 128GB RAM, RTX A2000 6GB VRAM.

## Fonti

| File | Cosa misura | Affidabilita |
| --- | --- | --- |
| `sweep_leaderboard.json` | coding sweep piccolo/incompleto | Media-bassa: molte righe sono parziali. |
| `sweep_advanced_leaderboard.json` | coding avanzato | Media: utile per confronto tra piccoli/3B. |
| `sweep_text_leaderboard.json` | text/estrazione/traduzione | Alta per task testuali brevi. |
| `sweep_ts_ab_leaderboard.json` | TypeScript/coding web | Media: punteggio e tempi aggiornati 2026-06-18. |
| `bench-opencode-local/summary-*.csv` | OpenCode end-to-end | Alta per flusso reale, ma pochi task. |
| `D:\repos\ralph\local_ralph\BENCHMARK_v4_v5_LEADERBOARD.md` | coding realistico su pattern TS/Python reali | Alta per qualita: GildedRose, Drizzle, TanStack, Zod, Vitest, fiscal/crypto/state machine. |
| `D:\repos\ralph\local_ralph\coding_benchmark_v4_realworld.py` + `coding_benchmark_v5_ts_focus.py` | harness rieseguibile contro endpoint OpenAI-compatible | Alta per confronto A/B; usare `BENCH_URL` e `BENCH_MODEL`. |
| Smoke API manuali | caricamento, compatibilita e tok/s su prompt breve | Alta per sanity check, non per qualita. |

## Classifica sintetica

| Modello | Qualita migliore osservata | Velocita osservata | Fonte | Nota operativa |
| --- | ---: | ---: | --- | --- |
| `Qwen3.6-35B-A3B-IQ3_K_R4` | Text `29/31`, TS `55/58` | Text `18.29s`; TS `53.34s`; OpenCode `64-97s/task` | `sweep_text_leaderboard.json`, `sweep_ts_ab_leaderboard.json`, OpenCode CSV | Default robusto attuale (`qwen36-iq3`). |
| `Qwen3.6-35B-A3B-IQ4_XS` / cluster Qwen3.6 Q4-Q6 | Ralph v4+v5 `14/17` | Ralph: ~`25-36` tok/s decode secondo config storica | `D:\repos\ralph\local_ralph\BENCHMARK_v4_v5_LEADERBOARD.md` | Miglior segnale realistico storico per TS/Python; da riallineare agli attuali profili `qwen36-mtp`/`quality-iq3`. |
| `phi-4 14B Q4_K_M` | Ralph v4 `9/9`, v5 `4/8`, totale `13/17` | ~`5` tok/s storico | Ralph v4+v5 | Unico storico a passare GildedRose+Conjured; utile come confronto quality lento, se disponibile/caricabile. |
| `Qwen3-4B-Instruct-2507-Q4_K_M` | TS `55/58`, Text `23/31` | Text `8.25s`; TS `30.07s` | text/TS leaderboard | Buon candidato leggero se disponibile/configurato; `asynciter` recuperato con repair runtime. |
| `Qwen2.5-Coder-3B-Q4_0` | Text `29/31`, Advanced `15/17`, TS `48/58` | Text `5.97s`, Advanced `21.67s`, TS `30.12s` | text/advanced/TS | Vecchio ma forte nei test piccoli. |
| `Qwen2.5-Coder-1.5B-Q4_K_M` | Advanced `16/17`, TS `50/58`, Text `25/31` | Text `4.92s`, Advanced `13.71s`, TS `29.27s` | text/advanced/TS | Molto efficiente nei bench storici. |
| `granite-4.1-3B-Q4_K_S` | Advanced `15/17`, TS `46/58`, Text `23/31` | Text `6.25s`, Advanced `20.25s`, TS `25.45s` | text/advanced/TS | Buon baseline Granite piccolo. |
| `Qwen2.5-Coder-0.5B-Q4_K_M` | Coding sweep `32/45` | `6.49s` | `sweep_leaderboard.json` | Veloce, ma test parziale e qualita limitata. |
| `Qwen3-0.6B-Q8_0` | Coding sweep `30/38` | `59.11s` | `sweep_leaderboard.json` | Parziale; non competitivo. |
| `deepseek-coder-1.3B-kexer-Q4_K_M` | Coding sweep `5/13` | `134.55s` | `sweep_leaderboard.json` | Segnale negativo. |
| `Qwen3.5-0.8B-Q8_0` | Coding sweep `0/51` | `143.10s` | `sweep_leaderboard.json` | Segnale negativo. |

## Caselle OpenCode top 5

| Casella | Profilo/OpenCode | Modello | Segnale migliore | Stato | Nota |
| --- | --- | --- | --- | --- | --- |
| Quality reale | `quality-iq3` | `llama-swap/qwen36-opus-iq3` | Ralph v4 `8/9`, v5 `8/8`, totale `16/17` | Piena | Migliore candidato locale misurato con regole generali; GildedRose resta aperto. |
| Default / contesto lungo | `coding` / `review` | `llama-swap/qwen36-iq3` | Text `29/31`, TS `55/58`, OpenCode OK `3/3` | Piena per text/TS/OpenCode, debole su Ralph v4 | Resta default pragmatico per 32k e stabilita, non per qualita massima. |
| Fast / classifier | `fast` | `llama-swap/qwen-small` | OpenCode OK `3/3`, `7.77-11.85s` | Piena per smoke/OpenCode breve | Usare per prompt corti, classificazione e comandi banali. |
| MTP sperimentale | `qwen36-mtp` | `llama-swap/qwen36-mtp` | Ralph v4 `8/9`, v5 `8/8`, totale `16/17` | Piena | Ora competitivo con prompt generali; resta aperto GildedRose. |
| Hard refactor storico | non configurata | `phi-4 14B Q4_K_M` | Ralph v4 `9/9`, v5 `4/8`, totale `13/17` | Piena storica, manca profilo OpenCode locale | Miglior segnale su refactor/rule reasoning; lenta e da aggiungere a `llama-swap` solo se serve. |

## Caselle verificate 2026-06-18

| Fonte | Campo verificato | Esito | Azione |
| --- | --- | --- | --- |
| `sweep_ts_ab_leaderboard.json` | `per_task[].elapsed` per tutti i 5 modelli | Riempito | Parser corretto: accetta `latency:` oltre a `elapsed:`. |
| `sweep_ts_ab_leaderboard.json` | `Qwen3-4B-Instruct-2507-Q4_K_M` su `asynciter_vanilla` | `4/4`, totale TS `55/58` | Recuperato con prompt esplicito + repair runtime. |
| `quality-iq3` | Ralph v5 | `8/8` | `react_query` recuperato con prompt checklist `useState/useEffect`. |
| `quality-iq3` | Ralph v4 | `8/9` | Drizzle recuperato; GildedRose fallisce ancora con rubrica generale. |
| `qwen36-mtp` | Ralph v4/v5 | v4 `2/9`, v5 `7/8` | Non promuovere a quality: passa TS-focus ma non il gate reale v4. |
| `qwen36-mtp` | Ralph v4/v5 dopo prompt generali | v4 `8/9`, v5 `8/8` | Recuperati Drizzle/AppError/React Query e vari task v4; resta GildedRose. |
| `qwen36-iq3` | Ralph v4/v5 dopo prompt generali | v4 `7/9`, v5 `8/8` | Migliora molto il baseline; falliscono GildedRose e P.IVA output fence. |
| `qwopus9-mtp` | Smoke/Ralph con smoke `160` | smoke OK, v4 `0/9`, v5 `2/8` | Rimane fuori routing: produce formato inadatto al checker. |

## OpenCode end-to-end

| Profilo | Modello | Esito | Durata osservata | Fonte | Nota |
| --- | --- | --- | ---: | --- | --- |
| `fast` | `llama-swap/qwen-small` | OK 3/3 | `7.77-11.85s` | `summary-20260606-231739.csv` | Migliore per prompt brevi e classifier. |
| `coding` | `llama-swap/qwen36-iq3` | OK 3/3 | `64.49-96.64s` | `summary-20260606-233248.csv` | Default principale, lento ma affidabile. |
| `qwen-coder` | `llama-swap/qwen-coder` | FAIL recente | crash avvio API 2026-06-18 | API smoke, `summary-20260606-232234.csv` | Vecchio run parziale OK 2/3, ma ora `upstream command exited prematurely`. |
| `granite` | `llama-swap/granite-fast` | FAIL 3/3 | `12.32-325.01s` | `summary-20260606-232234.csv` | Segnale negativo vecchio; ritestare dopo update. |
| `oss` | `llama-swap/gpt-oss-20b` | FAIL 3/3 | `1.03-19.88s` | `summary-20260606-232234.csv` | Segnale negativo vecchio; ritestare dopo update. |

## Smoke nuovi profili 2026-06-17

| Profilo | Esito | Velocita/metriche | Nota |
| --- | --- | --- | --- |
| `quality-iq3` | OK OpenCode + API | API: ~`32.4` tok/s prompt, ~`26.1` tok/s gen | Candidato quality pragmatico. |
| `qwen36-mtp` | OK OpenCode + API | API: ~`20.6` tok/s gen, `draft_n=1`, `draft_n_accepted=1` | MTP attivo. |
| `qwopus9` | Parziale | API: ~`13.9` tok/s gen, `draft_n=20`, `draft_n_accepted=17` | Produce reasoning prima del contenuto; serve budget/tuning. |
| `mellum` | API OK, OpenCode problematico | API: ~`60.6` tok/s prompt, ~`53.4` tok/s gen | In OpenCode genera blocchi stato ripetuti. |
| `mellum-thinking` | API OK | API: ~`68.2` tok/s prompt, ~`55.0` tok/s gen | Smoke pulito via API. |
| `gpt-oss-20b` | API OK | API: ~`72.3` tok/s prompt, ~`16.8` tok/s gen | Produce reasoning ma contenuto finale `OK`; da ritestare OpenCode. |
| `granite-fast` | API negativo | API: ~`53.7` tok/s prompt, ~`12.7` tok/s gen | Carica, ma genera solo spazi invisibili sul prompt breve. |
| `qwen-coder` | API negativo | n/d | `llama-swap`: `upstream command exited prematurely`; probabile config/offload da rivedere. |

## Ralph real-world 2026-06-18

| Profilo | Suite | Esito | Note |
| --- | --- | --- | --- |
| `qwen36-iq3` | v4 | `1/9` | Solo `apperror_pattern` passato; baseline debole su task reali. |
| `quality-iq3` | v4 | `8/9` | Fallisce solo GildedRose con rubrica generale. |
| `quality-iq3` | v5 | `8/8` | React Query offline recuperato con prompt checklist. |
| `qwen36-mtp` | v4 | `2/9` | Passano solo Advisory Lock e Vitest 4; debole su task reali. |
| `qwen36-mtp` | v5 | `7/8` | Fallisce solo React Query offline; buon TS-focus ma non basta per routing quality. |
| `qwen36-mtp` | v4 aggiornato | `8/9` | Fallisce solo GildedRose. |
| `qwen36-mtp` | v5 aggiornato | `8/8` | Tutti i task passano. |
| `qwen36-iq3` | v4 aggiornato | `7/9` | Falliscono GildedRose e P.IVA per output fence. |
| `qwen36-iq3` | v5 aggiornato | `8/8` | Tutti i task passano. |
| `qwopus9-mtp` | v4/v5 aggiornato | `0/9`, `2/8` | Smoke OK con 160 token, ma formato/ragionamento non adatti. |

## Lettura rapida

- Miglior candidato reale misurato: `quality-iq3` (`16/17` Ralph v4+v5 con prompt migliorati ma generali).
- Miglior default stabile/contesto: `qwen36-iq3`.
- Miglior candidato quality da promuovere: `quality-iq3`.
- Miglior candidato MTP: `qwen36-mtp` e ora competitivo (`16/17`); `qwopus9` resta fuori nonostante smoke OK.
- Miglior fast path: `qwen-small`.
- Da non mettere in routing automatico per ora: `mellum`, `granite-fast`, `qwen-coder`, `Qwen3-Coder-Next` pesante.
- `gpt-oss-20b` e tornato API-OK nello smoke 2026-06-18, ma resta fuori dal routing finche non passa un test OpenCode vero.

## Prossimi test modello

- Usare Ralph come gate realistico principale: da `D:\repos\ralph\local_ralph`, eseguire `coding_benchmark_v4_realworld.py` e `coding_benchmark_v5_ts_focus.py` contro `llama-swap`/router con `BENCH_URL` e `BENCH_MODEL`.
- Tenere `quality-iq3` come candidato quality principale e non promuovere `qwen36-mtp` oltre l'uso sperimentale senza migliorare Ralph v4.
- GildedRose richiede ulteriore lavoro: una rubrica generale su stato originale/soglie/strategie esclusive non basta; lo scaffold algoritmico specifico porta a `17/17` ma non e un benchmark fair.
- Sistemare reasoning/budget di `qwopus9-mtp` prima di qualunque altro benchmark realistico.
- Benchmarkare `qwen36-q5` e `qwen-opus-q8` solo se serve piu qualita e si accetta latenza maggiore.
- Validare DFlash con `dflash-draft-3.6-q4_k_m.gguf` prima di aggiungerlo come profilo stabile.
- Rivedere `qwen-coder` con offload/`--cpu-moe` diversi: lo smoke 2026-06-18 crasha all'avvio.
