# Benchmark Memory

Ultimo aggiornamento: 2026-06-18.

Questa nota memorizza gli apprendimenti più utili emersi durante il lavoro sui modelli locali, su `ik_llama.cpp` e su `D:\repos\ralph\local_ralph`.
E' una memoria operativa, non una classifica.

## Cosa abbiamo fatto

- Consolidato una sola graduatoria canonica in [docs/model-test-ranking.md](D:/repos/ik_llama.cpp/docs/model-test-ranking.md).
- Separato i dati raw dei benchmark dalle conclusioni operative.
- Aggiornato i profili OpenCode locali per includere i candidati nuovi e i fallback.
- Verificato che `D:\repos\ralph\local_ralph` sia il gate realistico per task di coding veri.
- Creato un wrapper non distruttivo per eseguire Ralph contro `llama-swap` senza sovrascrivere i risultati storici.
- Eseguito un primo giro reale su Ralph v4 con `qwen36-iq3` e `quality-iq3`.
- Riempite le caselle mancanti 2026-06-18: timing TS, `Qwen3-4B` async iterator, Ralph v5 `quality-iq3`, Ralph v4/v5 `qwen36-mtp`, smoke `qwopus9-mtp`.
- Migliorati gli zero 2026-06-18: prompt checklist + parametri deterministici portano `quality-iq3` a Ralph v4 `8/9`, v5 `8/8`; repair runtime porta `Qwen3-4B` async iterator a `4/4`.
- Aggiornati i repo collegati sotto `D:\repos` con `fetch --all --prune` e `pull --ff-only --autostash`, lasciando intatti i worktree divergenti o con conflitti.
- Eseguito `sweep_untested_characteristics.py` sui tre modelli piccoli candidati per caratteristiche non ancora coperte: `Qwen2.5-Coder-3B-Q4_0`, `Qwen2.5-Coder-1.5B-Q4_K_M`, `granite-4.1-3B-Q4_K_S`.
- Eseguito un confronto reale end-to-end su `granite-fast` via `scripts/run-ralph-realworld-bench.ps1 -Model granite-fast -Suite both -Restart -StopAfter`.
- Verificato `granite-fast` anche sul mini-bench toolcall API diretto con server `llama-server` su `127.0.0.1:1234`.
- Aggiornata la graduatoria canonica con qualita, velocita osservata e caso d'uso consigliato; non e stata modificata la logica del router perche i dati non lo giustificano.

## Ultimi run reali

### Baseline `qwen36-iq3`

- Esito: `1/9` su Ralph v4.
- Passato: solo `apperror_pattern`.
- Falliti: `gilded_rose_refactor_with_conjured`, `drizzle_multitenant`, `advisory_lock`, `monetary_rounding`, `crypto_aes_gcm`, `state_machine`, `piva_validator`, `vitest4_integration`.
- Lettura pratica: baseline utile come controllo, ma troppo debole per essere candidato reale su questa batteria.

### Candidato `quality-iq3`

- Esito fair: `8/9` su Ralph v4, `8/8` su Ralph v5, totale `16/17`.
- Passati: `apperror_pattern`, `advisory_lock`, `monetary_rounding`, `crypto_aes_gcm`, `state_machine`, `piva_validator`, `vitest4_integration`.
- Recuperati: `drizzle_multitenant` con prompt checklist, `react_query_use_invoices_with_offline` con requisiti espliciti `useState/useEffect`.
- Non recuperato con rubrica generale: `gilded_rose_refactor_with_conjured`.
- Esperimento non-fair: con scaffold algoritmico specifico GildedRose passa e il totale diventa `17/17`, ma non va usato come ranking principale.
- Lettura pratica: miglioramento netto rispetto a `qwen36-iq3`; al momento e il candidato locale piu convincente su questa batteria.

### Candidato `qwen36-mtp`

- Esito: `2/9` su Ralph v4, `7/8` su Ralph v5, totale `9/17`.
- v4 passati: `advisory_lock`, `vitest4_integration`.
- v5 fallito: solo `react_query_use_invoices_with_offline` per `missing useState`.
- Dopo prompt generali: `8/9` su Ralph v4, `8/8` su Ralph v5, totale `16/17`.
- Lettura pratica: ora competitivo come MTP sperimentale; resta aperto GildedRose.

### Baseline aggiornato `qwen36-iq3`

- Esito dopo prompt generali: `7/9` su Ralph v4, `8/8` su Ralph v5, totale `15/17`.
- Falliti v4: `gilded_rose_refactor_with_conjured`, `piva_validator_italian` per output fence/sintassi.
- Lettura pratica: molto meglio del vecchio `1/9`; resta meno forte di `quality-iq3`/`qwen36-mtp`.

### Candidato `qwopus9-mtp`

- Esito smoke Ralph: FAIL.
- Dettaglio: content vuoto, `reasoning_chars=148`, `completion_tokens=32`.
- Dopo smoke `160`: smoke OK, ma Ralph v4 `0/9`, v5 `2/8`.
- Lettura pratica: non adatto al gate corrente; il problema non e solo il budget di smoke.

### Sweep caratteristiche non ancora coperte

- Script: `sweep_untested_characteristics.py`.
- Output: `untested_characteristics_leaderboard.json`.
- `Qwen2.5-Coder-3B-Q4_0`: spec ambiguity `2/4`, literal `5/5`, literal hard `6/7`, toolcall `0/3`, self-correction `8 -> 8`.
- `Qwen2.5-Coder-1.5B-Q4_K_M`: spec ambiguity `2/4`, literal `5/5`, literal hard `6/7`, toolcall `0/3`, self-correction `8 -> 8`.
- `granite-4.1-3B-Q4_K_S`: spec ambiguity `3/4`, literal `5/5`, literal hard `6/7`, toolcall `3/3`, self-correction `7 -> 7`.
- Lettura pratica: il Granite 3B ha un segnale interessante su toolcall isolato, ma questo dato non va trasferito automaticamente al profilo `granite-fast` 8B usato nel router.

### Ritest `granite-fast`

- Harness reale: `scripts/run-ralph-realworld-bench.ps1 -Model granite-fast -Suite both -Restart -StopAfter`.
- Output: `bench-ralph-realworld/20260618-214438`.
- Profilo vecchio: `D:\repos\ik_llama.cpp\models\ibm-granite_granite-4.1-8b-Q4_K_M.gguf` con runtime IK e flag `--merge-qkv`.
- Smoke vecchio: tecnicamente OK, ma contenuto degenerato con spazi invisibili e sequenze `](`; quindi smoke OK non significa qualita OK.
- Ralph v4: `0/9`.
- Ralph v5: `0/8`.
- Tempi Ralph: circa `40-127s/task`, quindi lento e qualitativamente insufficiente.
- Toolcall API diretto sul profilo vecchio: `0/3`; non emette `tool_calls` e produce testo degenerato (`maduras`, `cigaret`, ripetizioni).
- Ricerca online: la pagina Unsloth `granite-4.1-8b-GGUF` indica esplicitamente chat template fixes e uso `--jinja` con llama.cpp.
- Fix provato: usare `F:\01_Modelli_AI\LLM_Models\lm-studio\models\unsloth\granite-4.1-8b-GGUF\granite-4.1-8b-Q4_K_S.gguf` con runtime mainline `D:\repos\llama_mtp\build\bin\Release\llama-server.exe`, `--jinja`, senza `--merge-qkv`, senza `-ctk/-ctv`.
- Smoke corretto via `llama-swap`: `OK` in `4.68s`.
- Toolcall corretto via `llama-swap`: `3/3` (`get_weather`, `calculator`, `query_invoice`) in circa `2.4-3.8s/case`.
- Gate atomico implementato: `scripts/model_profile_gate.py`, coperto da `tests/test_model_profile_gate.py`.
- Gate reale `granite-fast` corretto: smoke `PASS`, tool-use `5/5`, output `bench-opencode-local/model-gate-granite-fast-20260618-224916.json`.
- Gate OpenCode breve implementato: `scripts/opencode_profile_gate.py`, coperto da `tests/test_opencode_profile_gate.py`.
- Gate OpenCode breve `granite-fast` corretto: `0/3`, output `bench-opencode-local/opencode-gate-granite-fast-20260618-225533.json`.
- Dettaglio OpenCode: `opencode` termina con exit code `0`, ma produce output vuoto e token `0` su `explain-bug`, `write-patch`, `review`.
- Lettura pratica: il fallimento iniziale era profilo/runtime/quantizzazione, non Granite in generale. Il profilo corretto e candidato toolcall API, ma non va promosso a OpenCode/coding: il gate breve fallisce con output vuoto.

### Fix `qwen-coder`

- Profilo vecchio: `D:\repos\ik_llama.cpp\models\Qwen3-Coder-Next-UD-Q3_K_XL.gguf`.
- Fallimento: loader IK segnala `model is corrupted or incomplete`, tensor `blk.45.ffn_up_exps.weight` fuori dai bounds del file.
- Ricerca online: le pagine Unsloth Qwen3-Coder-Next indicano GGUF aggiornati e `llama.cpp` aggiornato per evitare looping/output scadente; per MoE serve attenzione a CPU/offload.
- Fix provato: usare `F:\01_Modelli_AI\LLM_Models\lm-studio\models\unsloth\Qwen3-Coder-Next-GGUF\Qwen3-Coder-Next-UD-Q2_K_XL.gguf` con `--cpu-moe`.
- Smoke manuale: `OK`.
- Smoke via `llama-swap`: `OK` in `13.89s`.
- Lettura pratica: non era un problema di sampling o Optuna; era un file GGUF locale corrotto/incompleto piu mancanza di `--cpu-moe`.

### Fix/diagnosi `mellum2-instruct`

- Profilo IK: `Mellum2-12B-A2.5B-Instruct-Q4_K_M.gguf` con runtime IK.
- Smoke via `llama-swap`: `OK` in `2.98s`.
- Runtime mainline `D:\repos\llama_mtp` fallisce: `unknown model architecture: 'mellum'`.
- Ricerca online: Mellum2 e un MoE 64 esperti / 8 attivi; il supporto llama.cpp per architettura `mellum` e recente/non sempre presente nelle build.
- Lettura pratica: Mellum va tenuto su IK o su build che supporta esplicitamente `mellum`; non va provato su runtime mainline generico.

### TS A/B locale

- Corretto `sweep_ts_ab.py`: il parser ora legge `latency:` oltre a `elapsed:`.
- `sweep_ts_ab_leaderboard.json` ora ha tempi per-task per tutti i 5 modelli.
- `Qwen3-4B-Instruct-2507-Q4_K_M` e passato da TS `51/54` a `55/58`: `asynciter_vanilla` e recuperato da `0/4` a `4/4` con repair che usa l'errore Node.

### Lezioni sul wrapper

- Il primo wrapper Ralph falliva sui warning Python stampati su stderr.
- La correzione giusta e stata separare stdout/stderr e poi consolidare i log.
- `smoke OK` non basta: serve il report completo della suite per parlare di qualita.

## Cosa ha avuto successo

- `qwen36-iq3` resta un baseline affidabile per uso quotidiano.
- `qwen36-mtp` si carica e passa gli smoke API/OpenCode di base, ma Ralph v4 lo boccia.
- Con i prompt generali, `qwen36-mtp` sale a `16/17` e diventa il migliore candidato MTP.
- `quality-iq3` è un candidato pragmatico da tenere sotto osservazione.
- Prompt checklist per TS strutturale: recupera `React Query`, `Drizzle`, `AppError`.
- Repair runtime con errore concreto: recupera `asynciter`.
- Ralph v4/v5 è la fonte migliore per distinguere qualità reale da semplice capacità di rispondere a `OK`.
- La documentazione è stata deduplicata: routing, benchmark e ranking ora puntano a fonti canoniche distinte.
- `quality-iq3` ha dimostrato di superare nettamente `qwen36-iq3` sul gate reale Ralph v4.
- Lo sweep caratteristiche ha chiarito che i due Qwen piccoli sono affidabili su preservazione letterale ma non su toolcall.
- `granite-4.1-3B-Q4_K_S` e promettente su toolcall isolato (`3/3`).
- Il confronto reale ha evitato una promozione sbagliata del vecchio `granite-fast`: il profilo era rotto. Il profilo corretto Unsloth+mainline passa smoke e toolcall, ma va ritestato su Ralph prima del coding routing.
- Il nuovo gate `scripts/model_profile_gate.py` mette un punto ripetibile: smoke + 5 casi tool-use, JSON persistente ed exit code.
- Il nuovo gate `scripts/opencode_profile_gate.py` mette un secondo punto: OpenCode breve con 3 task e checker deterministici. Su `granite-fast` corretto fallisce `0/3`, quindi blocca la promozione coding.
- La scelta migliore per il router resta conservativa: `qwen36-iq3` default, `quality-iq3`/`qwen36-mtp` per quality, `qwen-small` per fast/classifier.
- `qwen-coder` e recuperabile sostituendo il GGUF corrotto con il Q2 Unsloth e aggiungendo `--cpu-moe`.
- `mellum2-instruct` non e morto: su IK risponde correttamente; il fallimento mainline e supporto architettura mancante.
- Diagnosi `granite-fast` OpenCode output vuoto: il modello e l'API non-streaming funzionano; il vuoto/token 0 nasce nel percorso streaming OpenCode/AI SDK. Un adapter router non-streaming->SSE ha sbloccato eventi `text` e token, quindi la causa non e "modello muto".

## Cosa non ha avuto successo

- `qwen36-iq3` e risultato troppo debole su Ralph v4 per essere un candidato serio.
- `mellum` in OpenCode ha mostrato comportamento instabile, con output ripetitivo e poco utile.
- `granite-fast` ha caricato ma ha prodotto output inutilizzabile su smoke brevi.
- Il vecchio profilo `granite-fast` e stato ritestato dopo update e conferma il segnale negativo: Ralph `0/17`, toolcall API `0/3`, output degenerato.
- `qwen-coder` ha iniziato a crashare con `upstream command exited prematurely`; causa trovata: GGUF Q3 locale corrotto/incompleto.
- `qwopus9` ha richiesto tuning ulteriore: reasoning content e budget non erano ancora allineati.
- `qwopus9-mtp` passa lo smoke con piu token, ma fallisce quasi tutto Ralph (`0/9`, `2/8`).
- GildedRose resta il discriminator: la rubrica generale su stato originale, soglie e strategie esclusive non basta; lo scaffold specifico sconfina nel dare la soluzione.
- Il primo tentativo di wrapper Ralph ha sofferto per gestione stderr/warning Python troppo aggressiva.
- Il dato positivo `granite-4.1-3B-Q4_K_S` toolcall `3/3` non si trasferisce al vecchio `granite-fast`; serve correggere il profilo esatto.
- Fare un benchmark monolitico senza output progressivo puo sembrare bloccato: meglio loggare per repo/modello/task o controllare i log lato `llama-swap`.
- Optuna/sampling non risolve problemi di file corrotto, runtime incompatibile, chat template errato o flag non supportati.
- Workaround non-streaming per `granite-fast` non promosso a default: su 16k produce testo ma poi OpenCode va in context overflow (`26202 > 16384`); portando Granite a 32k non chiude entro `90s` perche perde lo streaming reale e aspetta la risposta completa.

## Errori da non ripetere

- Non usare uno smoke `OK` come sostituto di un benchmark realistico.
- Non sovrascrivere i file storici di Ralph quando si prova un nuovo modello.
- Non lanciare benchmark paralleli sulla stessa macchina locale.
- Non inferire che un modello sia buono solo perché risponde velocemente.
- Non lasciare che warning Python o stderr innocui interrompano il processo di benchmark.
- Non fare routing automatico su modelli che non hanno passato almeno un gate realistico.
- Non promuovere il baseline storico senza passarlo prima su Ralph reale.
- Non rieseguire suite complete su profili che falliscono lo smoke con content vuoto.
- Non usare `BENCH_ATTEMPTS=2` su tutta la suite: e troppo lento. Meglio repair mirato solo sui task con checker eseguibile.
- Non trasferire conclusioni tra modelli solo perche condividono famiglia/nome commerciale: Granite 3B, Granite 8B bartowski+IK e Granite 8B Unsloth+mainline hanno comportamenti diversi.
- Non aggiungere regole router per una capacita isolata senza verificare lo stesso profilo concreto via endpoint reale.
- Non considerare `toolcall` passato se il modello scrive testo simile a una chiamata: il gate utile richiede `message.tool_calls` valido nell'API.
- Non fermarsi alla prima impressione "Granite sa fare toolcall": serve distinguere modello, runtime, template, alias e endpoint.
- Non usare Optuna prima di avere un profilo che carica, usa il template corretto e passa smoke deterministico. Prima fissare runtime/modello/flag, poi eventualmente cercare sampling.
- Non ritestare Qwen Coder Next sul file Q3 locale finche non viene riscaricato/verificato; usare il Q2 Unsloth gia smoke-OK.
- Non provare Mellum su runtime senza supporto `mellum`: il fallimento `unknown model architecture` e incompatibilita runtime, non qualita modello.
- Non lasciare processi `llama-server`/`llama-swap` attivi dopo benchmark lunghi; usare `-StopAfter` o controllare `Get-Process`.
- Non fare `pull` distruttivi su repo con conflitti, branch divergenti o file non tracciati che verrebbero sovrascritti; usare `fetch` e `pull --ff-only --autostash`, poi decidere manualmente.
- Non assumere che uno stream SSE valido via curl sia consumabile da OpenCode: AI SDK puo scartare chunk o non emettere `text-start`, producendo output vuoto e token 0 senza errore chiaro.
- Non attivare conversioni non-streaming globali sul router: sono utili per diagnosi, ma possono peggiorare drasticamente latenza e loop agentici.

## Regole pratiche

- Prima smoke tecnico, poi v4, poi v5.
- Un modello alla volta.
- Risultati nuovi in directory nuove, mai sopra i risultati storici.
- `llama-swap` diretto per i confronti modello/modello, router solo dopo.
- Aggiornare la graduatoria canonica solo quando ci sono dati sufficienti.
- Per ogni riga di classifica riportare insieme qualita, velocita osservata e caso d'uso consigliato: senza velocita la graduatoria e incompleta per l'uso operativo.
- Quando un risultato isolato sembra cambiare una decisione di routing, fare sempre un test sul profilo esatto usato dal router.
- Ordine corretto per debugging modelli strani: fonti primarie online -> verifica file/modello -> smoke manuale deterministico -> smoke via `llama-swap` -> toolcall/OpenCode/Ralph.
- Per candidati toolcall, usare prima `scripts/model_profile_gate.py`: e breve, deterministico e produce JSON confrontabile.
- Usare Optuna solo dopo questi passaggi, su benchmark brevi e stabili, per cercare `temperature`, `top_p`, `min_p`, `repeat_penalty`; non usarlo per problemi di caricamento/template.
- Per diagnosticare OpenCode vuoto/token 0: testare prima `/v1/chat/completions` con `stream:false`, poi `stream:true`, poi `opencode run --format json`; se API e OK ma OpenCode resta vuoto, provare temporaneamente `OPENCODE_ROUTER_NONSTREAM_MODELS=<modello>` per confermare un problema di parsing streaming.

## Prossimo uso consigliato

- Promuovere nel routing solo i profili che reggono Ralph oltre agli smoke base; per ora `quality-iq3` e il candidato piu forte.
- Non promuovere `granite-fast` corretto a OpenCode/coding: il motivo del vuoto e stato isolato nel percorso streaming OpenCode/AI SDK, ma il workaround non-stream e troppo lento/instabile. Per toolcall API resta positivo `5/5` sul gate atomico.
- Tenere `granite-4.1-3B-Q4_K_S` come candidato da investigare se si vuole aggiungere un profilo piccolo diretto separato e testarlo end-to-end.
- Ritestare `qwen-coder` Q2 Unsloth su OpenCode/Ralph leggero; non usare piu il Q3 locale finche non viene riscaricato.
- Ritestare `mellum2-instruct` su OpenCode con IK; non su mainline.
- Sistemare `qwopus9-mtp` reasoning/budget prima di altri benchmark.
- Per kata simili, usare regole generali trasferibili: stato originale prima delle mutazioni, soglie esatte, strategie esclusive e invarianti. Evitare pseudocodice specifico della soluzione quando si misura qualità del modello.
- Tenere `docs/model-test-ranking.md` come indice operativo e questa nota come memoria dei fallimenti e delle scelte.
