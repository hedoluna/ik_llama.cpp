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
| `untested_characteristics_leaderboard.json` | ambiguita, literal preservation, toolcall, self-correction | Media: utile per caratteristiche isolate; non sostituisce Ralph/OpenCode reale. |
| `bench-opencode-local/summary-*.csv` | OpenCode end-to-end | Alta per flusso reale, ma pochi task. |
| `D:\repos\ralph\local_ralph\BENCHMARK_v4_v5_LEADERBOARD.md` | coding realistico su pattern TS/Python reali | Alta per qualita: GildedRose, Drizzle, TanStack, Zod, Vitest, fiscal/crypto/state machine. |
| `D:\repos\ralph\local_ralph\coding_benchmark_v4_realworld.py` + `coding_benchmark_v5_ts_focus.py` | harness rieseguibile contro endpoint OpenAI-compatible | Alta per confronto A/B; usare `BENCH_URL` e `BENCH_MODEL`. |
| Smoke API manuali | caricamento, compatibilita e tok/s su prompt breve | Alta per sanity check, non per qualita. |

## Leaderboard operativa

Questa e la tabella da usare per decidere routing, ritest e priorita. Ordine scelto pesando: qualita su task realistici, affidabilita OpenCode, velocita osservata e rischio operativo. Le righe con solo smoke o benchmark parziali non devono superare profili che hanno gia passato OpenCode/Ralph realistico.

| Rank | Modello / profilo | Qualita osservata | Velocita osservata | Caso d'uso consigliato | Stato operativo |
| ---: | --- | --- | --- | --- | --- |
| 1 | `quality-iq3` / `llama-swap/qwen36-opus-iq3` | Ralph v4 `8/9`, v5 `8/8`, totale `16/17` | API ~`32.4 tok/s` prompt, ~`26.1 tok/s` gen | Quality locale, refactor, TS/Python realistico, task dove conta il primo colpo | Miglior candidato quality; promuovere solo dopo gate OpenCode breve dedicato |
| 2 | `qwen36-mtp` / `llama-swap/qwen36-mtp` | Con prompt generali: Ralph v4 `8/9`, v5 `8/8`, totale `16/17` | API ~`20.6 tok/s` gen; MTP `draft_n=1`, `draft_n_accepted=1` | Quality sperimentale, coding medio-difficile, confronto MTP | Competitivo ma sperimentale; non sostituire il default senza OpenCode gate |
| 3 | `qwen36-iq3` / `coding`, `review` | Text `29/31`, TS `55/58`, OpenCode `3/3`; Ralph aggiornato `15/17` | OpenCode `64-97s/task`; Text `18.29s`; TS `53.34s` | Default quotidiano, review, contesto lungo 32k, workflow OpenCode stabile | Default robusto attuale |
| 4 | `qwen-small` / `fast` | OpenCode `3/3` sui task brevi | `7.77-11.85s/task` | Classifier, prompt corti, comandi banali, titoli, routing helper | Fast path consigliato |
| 5 | `phi-4 14B Q4_K_M` | Ralph storico v4 `9/9`, v5 `4/8`, totale `13/17`; unico a passare GildedRose+Conjured | ~`5 tok/s` storico | Hard refactor, rule reasoning, confronto quality lento | Forte ma non configurato come profilo OpenCode locale |
| 6 | `Qwen3-4B-Instruct-2507-Q4_K_M` | TS `55/58`, Text `23/31`; `asynciter` recuperato a `4/4` | Text `8.25s`; TS `30.07s` | Modello leggero per TS e repair piccoli | Buon candidato leggero, da configurare se serve |
| 7 | `Qwen2.5-Coder-1.5B-Q4_K_M` | Advanced `16/17`, TS `50/58`, Text `25/31`; literal `5/5`, hard literal `6/7` | Text `4.92s`; Advanced `13.71s`; TS `29.27s` | Small coding economico, batch rapidi, test locali piccoli | Efficiente nei bench storici, non ancora OpenCode-top |
| 8 | `Qwen2.5-Coder-3B-Q4_0` | Text `29/31`, Advanced `15/17`, TS `48/58`; literal `5/5`, hard literal `6/7` | Text `5.97s`; Advanced `21.67s`; TS `30.12s` | Coding leggero/medio e task testuali brevi | Buono nei bench piccoli, non routing principale |
| 9 | `granite-4.1-3B-Q4_K_S` | Advanced `15/17`, TS `46/58`, Text `23/31`; toolcall isolato `3/3` | Text `6.25s`; Advanced `20.25s`; TS `25.45s` | Candidato Granite piccolo per tool/API e sweep mirati | Interessante ma non trasferire i risultati al profilo `granite-fast` 8B |
| 10 | `mellum2-instruct` / `llama-swap/mellum2-instruct` | Smoke API OK su runtime IK | Smoke `2.98s`; API ~`53.4 tok/s` gen | Solo investigazione su runtime IK; possibile coding specialist | Fuori routing finche non passa OpenCode/Ralph |
| 11 | `qwen-coder` corretto / Qwen3-Coder-Next Q2 Unsloth | Smoke OK dopo fix GGUF + `--cpu-moe` | Smoke `13.89s` | Da ritestare su OpenCode/Ralph leggero; possibile coder specialist | Recuperato tecnicamente, non promosso |
| 12 | `granite-fast` corretto 8B Unsloth | API smoke PASS, tool-use `5/5`; OpenCode breve `0/3` con output vuoto | Gate API ~`11s`; smoke `4.68s`; toolcall `2.4-3.8s/case`; OpenCode vuoto `11.9-15s/task` | Tool specialist API isolato, non coding agent | Non promuovere OpenCode; problema streaming OpenCode/AI SDK isolato |
| 13 | `gpt-oss-20b` | API OK, vecchio OpenCode `0/3` | API ~`72.3 tok/s` prompt, ~`16.8 tok/s` gen; vecchio OpenCode `1.03-19.88s` | Da ritestare se serve modello reasoning/OSS | Fuori routing finche non passa OpenCode |
| 14 | `qwopus9-mtp` | Smoke OK; Ralph v4 `0/9`, v5 `2/8` | API ~`13.9 tok/s` gen; `draft_n=20`, `draft_n_accepted=17` | Nessun uso automatico; solo debug reasoning/budget | Bocciato dai gate realistici |
| 15 | vecchio `granite-fast` 8B bartowski+IK | Ralph `0/17`, toolcall API `0/3`, output degenerato | Ralph `40-127s/task`; toolcall ~`21s/case` | Nessuno | Bocciato; non riusare |
| 16 | `Qwen2.5-Coder-0.5B-Q4_K_M` | Coding sweep parziale `32/45` | `6.49s` | Esperimenti tiny/latency | Qualita limitata e test parziale |
| 17 | `Qwen3-0.6B-Q8_0` | Coding sweep parziale `30/38` | `59.11s` | Nessun uso prioritario | Non competitivo |
| 18 | `deepseek-coder-1.3B-kexer-Q4_K_M` | Coding sweep `5/13` | `134.55s` | Nessuno | Segnale negativo |
| 19 | `Qwen3.5-0.8B-Q8_0` | Coding sweep `0/51` | `143.10s` | Nessuno | Segnale negativo |

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
| `granite-fast` | Ralph v4/v5 ritest 2026-06-18 | v4 `0/9`, v5 `0/8` | Non promuovere: fallisce import/funzioni/strutture su task reali e resta lento. |
| `granite-fast` | Toolcall API diretto 2026-06-18 | `0/3` | Non usare per toolcall nel router: non emette `tool_calls`, genera testo degenerato. |
| `granite-4.1-3B-Q4_K_S` | caratteristiche isolate 2026-06-18 | toolcall `3/3`, literal `5/5`, hard literal `6/7`, spec `3/4` | Segnale interessante ma non applicabile automaticamente a `granite-fast` 8B/router. |
| `granite-fast` corretto | Gate atomico 2026-06-18 | smoke `PASS`, tool-use `5/5` | Fix: Unsloth 8B Q4_K_S + runtime mainline + `--jinja`, senza `--merge-qkv`; OpenCode/Ralph da ritestare. |
| `granite-fast` corretto | Gate OpenCode breve 2026-06-18 | `0/3` | `opencode` exit code `0`, ma output vuoto e token `0` su tutti i task; non promuovere a coding. |
| `qwen-coder` corretto | Smoke 2026-06-18 | smoke `OK` via `llama-swap` | Fix: Qwen3-Coder-Next Q2 Unsloth + `--cpu-moe`; il Q3 locale e corrotto/incompleto. |
| `mellum2-instruct` | Smoke 2026-06-18 | smoke `OK` via `llama-swap` | Funziona su IK; mainline fallisce con `unknown model architecture: mellum`. |

## OpenCode end-to-end

| Profilo | Modello | Esito | Durata osservata | Fonte | Nota |
| --- | --- | --- | ---: | --- | --- |
| `fast` | `llama-swap/qwen-small` | OK 3/3 | `7.77-11.85s` | `summary-20260606-231739.csv` | Migliore per prompt brevi e classifier. |
| `coding` | `llama-swap/qwen36-iq3` | OK 3/3 | `64.49-96.64s` | `summary-20260606-233248.csv` | Default principale, lento ma affidabile. |
| `qwen-coder` | `llama-swap/qwen-coder` | FAIL recente | crash avvio API 2026-06-18 | API smoke, `summary-20260606-232234.csv` | Vecchio run parziale OK 2/3, ma ora `upstream command exited prematurely`. |
| `granite` | `llama-swap/granite-fast` | FAIL 3/3 | `12.32-325.01s` | `summary-20260606-232234.csv` | Segnale negativo vecchio; ritestare dopo update. |
| `granite` | `llama-swap/granite-fast` | FAIL Ralph `0/17`, toolcall `0/3` | Ralph `40-127s/task`; toolcall ~`21s/case` | `bench-ralph-realworld/20260618-214438`, `sweep_mode_toolcall_result.json` | Ritest 2026-06-18 conferma: fuori dal routing automatico. |
| `granite` | `llama-swap/granite-fast` corretto | Smoke OK, tool-use `5/5` | gate completo ~`11s`; smoke `4.68s`; toolcall `2.4-3.8s/case` | `bench-opencode-local/model-gate-granite-fast-20260618-224916.json` | Il vecchio profilo era rotto; candidato toolcall, ma ritestare OpenCode/Ralph prima del coding. |
| `granite` | `llama-swap/granite-fast` corretto | OpenCode breve FAIL `0/3` | `11.9-15.0s/task`, output vuoto | `bench-opencode-local/opencode-gate-granite-fast-20260618-225533.json` | Non promuovere a coding/OpenCode; investigare output vuoto se serve. |
| `granite` | `llama-swap/granite-fast` corretto | Diagnosi output vuoto | non-stream adapter: primo testo dopo ~`16s` su 16k; 32k non chiude entro `90s` | `raw-granite-routerfix-*`, `raw-granite-ctxfix-*` | Causa probabile: stream OpenAI-compatible non digerito da OpenCode/AI SDK. Workaround non-stream sblocca `text`/token, ma e troppo lento/instabile come default. |
| `qwen-coder` | `llama-swap/qwen-coder` corretto | Smoke OK | `13.89s` | smoke manuale 2026-06-18 | Q2 Unsloth + `--cpu-moe`; ritestare OpenCode/Ralph leggero. |
| `mellum` | `llama-swap/mellum2-instruct` | Smoke OK | `2.98s` | smoke manuale 2026-06-18 | IK supporta `mellum`; mainline no. Ritestare OpenCode. |
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
| `granite-fast` | v4/v5 aggiornato | `0/9`, `0/8` | Smoke OK, ma fallisce tutti i task reali; non aggiungere regole router verso Granite. |

## Lettura rapida

- Miglior candidato reale misurato: `quality-iq3` (`16/17` Ralph v4+v5 con prompt migliorati ma generali).
- Miglior default stabile/contesto: `qwen36-iq3`.
- Miglior candidato quality da promuovere: `quality-iq3`.
- Miglior candidato MTP: `qwen36-mtp` e ora competitivo (`16/17`); `qwopus9` resta fuori nonostante smoke OK.
- Miglior fast path: `qwen-small`.
- Da non mettere in routing coding automatico per ora: `mellum`, `granite-fast`, `qwen-coder`, `Qwen3-Coder-Next` pesante, finche non passano un gate OpenCode/Ralph.
- Il vecchio `tools` -> `granite-fast` era sbagliato; il profilo corretto passa il gate atomico tool-use `5/5`, ma fallisce OpenCode breve `0/3`. Eventuale routing solo come tool specialist, non coding.
- `gpt-oss-20b` e tornato API-OK nello smoke 2026-06-18, ma resta fuori dal routing finche non passa un test OpenCode vero.

## Piano progressivo

Obiettivo: promuovere solo profili che migliorano davvero il routing locale senza introdurre regressioni, loop OpenCode o falsi positivi da smoke test.

### Fase 0 - Baseline bloccata

- Tenere `qwen36-iq3` come default `coding`/`review`.
- Tenere `qwen-small` come `fast` e classifier.
- Tenere `quality-iq3` e `qwen36-mtp` come override manuali quality/sperimentali.
- Non aggiungere `granite-fast`, `qwen-coder`, `mellum`, `gpt-oss-20b`, `qwopus9-mtp` al routing coding automatico.

### Fase 1 - Gate atomico obbligatorio

- Per ogni candidato eseguire prima `scripts/model_profile_gate.py`: smoke + tool-use breve, JSON persistente, exit code non ambiguo.
- Se fallisce smoke, template, caricamento o `message.tool_calls`, fermarsi: niente Ralph, niente OpenCode, niente Optuna.
- Candidati immediati: `quality-iq3`, `qwen36-mtp`, `qwen-coder` corretto, `mellum2-instruct`.

### Fase 2 - Gate OpenCode breve

- Eseguire `scripts/opencode_profile_gate.py` su un candidato alla volta.
- Promuovere a esperimento OpenCode solo con `3/3` e output non vuoto.
- Se si vede output vuoto/token 0, seguire la diagnosi streaming: API `stream:false`, API `stream:true`, poi eventuale `OPENCODE_ROUTER_NONSTREAM_MODELS=<modello>` solo per conferma.

### Fase 3 - Ralph leggero

- Da `D:\repos\ralph\local_ralph`, usare v4/v5 solo dopo OpenCode breve passato.
- Prima run leggera: v5 TS-focus o subset mirato, poi v4 real-world.
- Gate minimo per promozione quality: almeno `15/17` complessivo senza trucchi specifici del task.

### Fase 4 - Promozione controllata

- `quality-iq3`: candidato principale per diventare `quality` stabile se passa OpenCode breve.
- `qwen36-mtp`: mantenere sperimentale finche non conferma OpenCode breve e non mostra regressioni di formato.
- `qwen-coder`: ritestare solo col Q2 Unsloth + `--cpu-moe`; non usare il Q3 locale corrotto.
- `mellum2-instruct`: testare solo su IK o runtime con supporto `mellum`; mainline generico e escluso.

### Fase 5 - Tuning solo dopo stabilita

- Usare Optuna o sweep sampling solo su profili che gia caricano, rispondono, rispettano template e passano i gate brevi.
- Parametri candidati: `temperature`, `top_p`, `min_p`, `repeat_penalty`, budget output.
- Non usare tuning per correggere file GGUF corrotti, runtime incompatibili, stream non digeriti da OpenCode o chat template errati.

### Stop conditions

- Stop immediato se un profilo produce output vuoto su OpenCode.
- Stop immediato se supera il contesto reale di OpenCode o innesca compaction loop.
- Stop immediato se la qualita reale scende sotto il default `qwen36-iq3`.
- Nessuna promozione senza velocita osservata e caso d'uso scritto nella leaderboard.
