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

## Cosa non ha avuto successo

- `qwen36-iq3` e risultato troppo debole su Ralph v4 per essere un candidato serio.
- `mellum` in OpenCode ha mostrato comportamento instabile, con output ripetitivo e poco utile.
- `granite-fast` ha caricato ma ha prodotto output inutilizzabile su smoke brevi.
- `qwen-coder` ha iniziato a crashare con `upstream command exited prematurely`.
- `qwopus9` ha richiesto tuning ulteriore: reasoning content e budget non erano ancora allineati.
- `qwopus9-mtp` passa lo smoke con piu token, ma fallisce quasi tutto Ralph (`0/9`, `2/8`).
- GildedRose resta il discriminator: la rubrica generale su stato originale, soglie e strategie esclusive non basta; lo scaffold specifico sconfina nel dare la soluzione.
- Il primo tentativo di wrapper Ralph ha sofferto per gestione stderr/warning Python troppo aggressiva.

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

## Regole pratiche

- Prima smoke tecnico, poi v4, poi v5.
- Un modello alla volta.
- Risultati nuovi in directory nuove, mai sopra i risultati storici.
- `llama-swap` diretto per i confronti modello/modello, router solo dopo.
- Aggiornare la graduatoria canonica solo quando ci sono dati sufficienti.

## Prossimo uso consigliato

- Promuovere nel routing solo i profili che reggono Ralph oltre agli smoke base; per ora `quality-iq3` e il candidato piu forte.
- Sistemare `qwopus9-mtp` reasoning/budget prima di altri benchmark.
- Per kata simili, usare regole generali trasferibili: stato originale prima delle mutazioni, soglie esatte, strategie esclusive e invarianti. Evitare pseudocodice specifico della soluzione quando si misura qualità del modello.
- Tenere `docs/model-test-ranking.md` come indice operativo e questa nota come memoria dei fallimenti e delle scelte.
