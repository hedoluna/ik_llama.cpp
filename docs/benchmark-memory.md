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

## Ultimi run reali

### Baseline `qwen36-iq3`

- Esito: `1/9` su Ralph v4.
- Passato: solo `apperror_pattern`.
- Falliti: `gilded_rose_refactor_with_conjured`, `drizzle_multitenant`, `advisory_lock`, `monetary_rounding`, `crypto_aes_gcm`, `state_machine`, `piva_validator`, `vitest4_integration`.
- Lettura pratica: baseline utile come controllo, ma troppo debole per essere candidato reale su questa batteria.

### Candidato `quality-iq3`

- Esito: `7/9` su Ralph v4.
- Passati: `apperror_pattern`, `advisory_lock`, `monetary_rounding`, `crypto_aes_gcm`, `state_machine`, `piva_validator`, `vitest4_integration`.
- Falliti: `gilded_rose_refactor_with_conjured`, `drizzle_multitenant`.
- Lettura pratica: miglioramento netto rispetto a `qwen36-iq3`; al momento e il candidato locale piu convincente su questa batteria.

### Lezioni sul wrapper

- Il primo wrapper Ralph falliva sui warning Python stampati su stderr.
- La correzione giusta e stata separare stdout/stderr e poi consolidare i log.
- `smoke OK` non basta: serve il report completo della suite per parlare di qualita.

## Cosa ha avuto successo

- `qwen36-iq3` resta un baseline affidabile per uso quotidiano.
- `qwen36-mtp` si carica e passa gli smoke API/OpenCode di base.
- `quality-iq3` è un candidato pragmatico da tenere sotto osservazione.
- Ralph v4/v5 è la fonte migliore per distinguere qualità reale da semplice capacità di rispondere a `OK`.
- La documentazione è stata deduplicata: routing, benchmark e ranking ora puntano a fonti canoniche distinte.
- `quality-iq3` ha dimostrato di superare nettamente `qwen36-iq3` sul gate reale Ralph v4.

## Cosa non ha avuto successo

- `qwen36-iq3` e risultato troppo debole su Ralph v4 per essere un candidato serio.
- `mellum` in OpenCode ha mostrato comportamento instabile, con output ripetitivo e poco utile.
- `granite-fast` ha caricato ma ha prodotto output inutilizzabile su smoke brevi.
- `qwen-coder` ha iniziato a crashare con `upstream command exited prematurely`.
- `qwopus9` ha richiesto tuning ulteriore: reasoning content e budget non erano ancora allineati.
- Il primo tentativo di wrapper Ralph ha sofferto per gestione stderr/warning Python troppo aggressiva.

## Errori da non ripetere

- Non usare uno smoke `OK` come sostituto di un benchmark realistico.
- Non sovrascrivere i file storici di Ralph quando si prova un nuovo modello.
- Non lanciare benchmark paralleli sulla stessa macchina locale.
- Non inferire che un modello sia buono solo perché risponde velocemente.
- Non lasciare che warning Python o stderr innocui interrompano il processo di benchmark.
- Non fare routing automatico su modelli che non hanno passato almeno un gate realistico.
- Non promuovere il baseline storico senza passarlo prima su Ralph reale.

## Regole pratiche

- Prima smoke tecnico, poi v4, poi v5.
- Un modello alla volta.
- Risultati nuovi in directory nuove, mai sopra i risultati storici.
- `llama-swap` diretto per i confronti modello/modello, router solo dopo.
- Aggiornare la graduatoria canonica solo quando ci sono dati sufficienti.

## Prossimo uso consigliato

- Eseguire `coding_benchmark_v4_realworld.py` e `coding_benchmark_v5_ts_focus.py` su `qwen36-iq3`, `quality-iq3`, `qwen36-mtp` e `qwopus9-mtp`.
- Promuovere nel routing solo i profili che reggono Ralph oltre agli smoke base.
- Tenere `docs/model-test-ranking.md` come indice operativo e questa nota come memoria dei fallimenti e delle scelte.
