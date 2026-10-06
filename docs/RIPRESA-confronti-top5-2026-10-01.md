# Stato aggiornato al 2026-10-07 — campagna agentica conclusa

Questa nota era un checkpoint scritto durante la pausa del 2026-10-01. La campagna Ralph/OpenCode è stata poi ripresa e completata il 2026-10-06; le istruzioni di ripresa sottostanti sono state sostituite dallo stato e dai gate attuali in questa nota. Non rilanciare la campagna come nuova.

## Campagna Ralph/OpenCode: completata

- Cinque modelli, tre task Ralph (`invoice`, `dag`, `cache`) con tre ripetizioni per task, più un task OpenCode (`invoice`) per modello: **50 run**.
- Esito finale: **36 PASS, 14 FAIL semantici/verifier, zero errori infrastrutturali** nell'aggregato pubblicato. Verifiche e specifiche immutate in tutti i 50 run.
- Per modello: Mellum2 3/10; Qwen Opus-distilled 8/10; Ornith 35B 8/10; daily Qwen 10/10; Ornith 9B 7/10.
- I tre timeout iniziali del cache 9B a 180 secondi sono stati esclusi dall'aggregato e rifatti a 600 secondi. I retry finali sono completi; due FAIL semantici e un PASS.
- Il runner ora supporta `--resume`, filtro `--labels`, timeout configurabile e normalizzazione dei percorsi assoluti per i worker. Tentativi interrotti o affetti da errore di percorso restano archiviati, non contati.
- Questi fixture test non sono il benchmark canonico Unified/Agentic v2 e non cambiano il ranking.

Report e dati completi sono in `D:/repos/ik-llama-bench/docs/agent-top5-2026-10-01-report.md` e `D:/repos/ik-llama-bench/docs/agent-top5-2026-10-01/results.json`. Registro cronologico e decisioni: `D:/repos/ik-llama-bench/docs/decision-log-2026-10-06.md`. I risultati e runner sono stati pubblicati sul branch `bench/qwen38-flash-next-optuna`, commit `0e7d50e`.

## Altri risultati già pubblicati

- Unified Top 5, semantic golden e confronto isolato upstream/MSVC: commit benchmark `28c3252`.
- Scout K2 e Julia/System One del 2026-10-06: commit benchmark `7179094`.
- K2-Horizon-MoVA carica in entrambi gli engine: Coding 56/56 su ik e 55/56 su mainline. La vecchia riga “non caricabile” è stata corretta. K2 resta fuori dalla classifica finché non completa Agentic v2 e throughput comparabili.
- Julia/System One supera l'API smoke ma sbaglia il routing descritto per fatturazione duplicata; non promuoverla senza una suite routing corretta.
- Il golden upstream baseline/candidato resta 14/15. Il candidato include una fix MSVC locale e non va descritto come puro upstream. Le misure throughput non giustificano una dichiarazione di accelerazione.

## Gate ancora aperti

1. **K2:** eseguire Agentic v2 e throughput dedicato sullo stesso harness/build/versione dei modelli in confronto.
2. **Extended output:** eseguire `scripts/revalidate_explicit_outputs.py` sui dieci risultati espliciti. Non pubblicare la leaderboard estesa finché la revalidazione e i gate seguenti non sono chiusi.
3. **OpenCode comparabile:** l'OpenCode eseguito qui copre un solo task invoice per modello. Un replay esplicito Windows (`--opencode-only`) su task coerenti non è stato fatto.
4. **Contesto lungo:** suite 24k/~98k token mai eseguita; se utile, mantenerla una categoria indipendente.
5. **Publisher esteso:** non eseguito; il ranking canonico non è stato aggiornato con i risultati eterogenei.

## Evidenze locali da non confondere

I risultati completi del fixture campaign sono nell'aggregato pubblicato. Trace HTTP, workspace, copie OpenCode, archivi dei tentativi interrotti e altre campagne WIP sono rimasti locali ed esclusi da Git. Non contarli come prove aggiuntive e non rimuoverli durante la pulizia automatica.

La graduatoria canonica e i relativi report sono nel repo `D:/repos/ik-llama-bench/docs/`. Per lo stato dei commit usare `git status` nel repo corretto: i tre commit benchmark sono pubblicati; questa nota nel repo engine resta un artefatto locale non committato.
