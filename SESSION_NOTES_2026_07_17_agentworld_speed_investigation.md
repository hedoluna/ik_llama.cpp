# Sessione 2026-07-17: Investigazione velocità Qwen-AgentWorld-35B-A3B (SOSPESA)

## Contesto

Durante il re-bench post-merge del 2026-07-17, `Qwen-AgentWorld-35B-A3B-IQ4_K_R4` è risultato l'unico modello del tier-7 a NON tornare al baseline storico dopo i fix di `--reasoning off`/ctx-size applicati agli altri (daily, quality, Ornith). È rimasto a ~51-62s di bench_time contro i ~20-27s degli altri 35B.

## Cosa c'è (stato attuale)

- **File in uso**: `D:\repos\ik_llama.cpp\models\Qwen-AgentWorld-35B-A3B-IQ4_K_R4.gguf` (19.7 GB), requantizzato Q8_0→IQ4_K_R4 il 2026-07-10 (vedi memoria `project_qwen_agentworld_2026_07_09`).
- **File sorgente Q8_0 ancora disponibile**: `F:\01_Modelli_AI\LLM_Models\archived_from_D\Qwen-AgentWorld-35B-A3B-Q8_0.gguf` — permette un requant locale a IQ3_K_R4 senza ri-scaricare nulla, se si deciderà di procedere.
- **Config attuale in `sweep_small_models.py`** (tier 7, riga ~155): `-ngl 8 --reasoning off -ctk q8_0 -ctv q8_0 -b 1024 -ub 1024 --chat-template-kwargs enable_thinking:false`. Nessun `--n-cpu-moe`.
- **Architettura**: `qwen35moe`, ibrida SSM/Mamba con `full_attention_interval=4` (1 layer ogni 4 è full-attention, gli altri ricorrenti/SSM). Questo è rilevante: il repack `_R4` (row-interleaved, usato dai quant `IQ*_K_R4`) accelera SOLO i matmul FFN degli esperti MoE, non i layer SSM/Mamba — limite già noto e documentato dal 2026-07-10.

## Cosa abbiamo trovato

1. **Non è un problema di offload/config**: testate 3 combinazioni (`-ngl 8` originale: 15.5 t/s; `-ngl 95 --n-cpu-moe 30` come `daily`: 14.9 t/s; `-ngl 99 --n-cpu-moe 15`: 10.0 t/s). Nessuna migliora sensibilmente sulle altre — anzi peggiorano.
2. **Discrepanza seria con la misura storica**: la memoria del 2026-07-10 documenta **tg64 = 32.0 t/s** per questo stesso identico file (IQ4_K_R4), misurato con `llama-bench`. Oggi, **stesso strumento** (`llama-bench.exe -m ... -ngl 8 -p 128 -n 64 -fa 1`), stesso file: **tg64 = 14.71 t/s**. Più del doppio più lento, senza alcun cambio di file/quant.
3. **Non è né il bug reasoning né il bug ctx-size** (già risolti oggi per gli altri modelli): `llama-bench` non usa chat template, non genera `<think>`, non passa da un context enorme — è un benchmark sintetico puro. Il rallentamento è quindi indipendente da entrambi i fix già applicati.
4. **Ipotesi principale, non verificata**: il merge di `origin/main` di oggi (`98836506`, vedi sez. 8 di `DEVELOPMENT_NOTES.md`) ha toccato/aggiunto kernel CUDA di attention complessa (`dsa_attn.cu`, `indexer_topk.cu`, `sinkhorn.cu`, `fattn.cu` modificato). `qwen35moe` è l'unico modello ibrido SSM/full-attention nel roster attuale — se uno di questi kernel ha sostituito un path più veloce per architetture ibride, spiegherebbe perché è l'UNICO modello rimasto lento mentre tutti i MoE puri sono tornati a piena velocità.

## Cosa volevamo fare (non ancora eseguito)

Due strade alternative identificate, **nessuna delle due eseguita**:

### Opzione A — Verificare l'ipotesi del kernel regredito
Checkout di `origin/main` pre-merge (commit prima di `98836506`, es. tramite worktree isolato come fatto il 2026-06-16 per `ik_llama.cpp-origin-main-test`) + rebuild CUDA completo + `llama-bench` identico su AgentWorld. Se il pre-merge dà ~32 t/s e il post-merge ~15 t/s, conferma la regressione e permette di isolare quale commit/kernel l'ha causata (bisect). Costo: ~20-25 min (rebuild CUDA completo in un secondo albero).

### Opzione B — Requant locale IQ4_K_R4 → IQ3_K_R4
`llama-quantize --allow-requantize` dal Q8_0 sorgente su F:. Costo: ~20 min. **Guadagno atteso solo parziale** (-22% dati da spostare, proporzionale alla differenza IQ4→IQ3), perché il repack R4 non tocca i layer SSM/Mamba che sono probabilmente la vera causa del rallentamento. Non risolverebbe l'Opzione A se confermata.

### Scartata — Scaricare un quant già pronto online
Verificato via ricerca web: **nessun quant `_R4` esiste per questo modello su nessun repository** (bartowski, mradermacher, unsloth) — `_R4` è un formato esclusivo di ik_llama.cpp, mai pubblicato da terzi. Anche un quant IQ3 standard scaricato (non-R4) sarebbe probabilmente più lento su questo fork per lo stesso motivo del repack R4 (lezione già nota: quant non-R4 offloadati su CPU sono molto più lenti degli R4 su ik_llama.cpp).

## Decisione

**Sospeso il 2026-07-17** — nessuna delle due opzioni eseguita, in attesa di priorità/tempo. AgentWorld resta nel roster con la config attuale (`-ngl 8`), funzionalmente corretto ma ~2× più lento del previsto rispetto al proprio stesso baseline storico.

## Come riprendere

1. Se si sceglie l'Opzione A: vedi procedura worktree in `DEVELOPMENT_NOTES.md` sez. "Verifica nuovi commit origin/main" (2026-06-16) come riferimento — stesso pattern, ma stavolta puntare a un commit PRIMA del merge di oggi invece che dopo.
2. Se si sceglie l'Opzione B: `llama-quantize.exe --allow-requantize F:\...\Qwen-AgentWorld-35B-A3B-Q8_0.gguf models\Qwen-AgentWorld-35B-A3B-IQ3_K_R4.gguf IQ3_K_R4`, poi ri-bench con `sweep_small_models.py --single`.
3. In entrambi i casi, validare con `llama-bench -ngl 8 -p 128 -n 64 -fa 1 -r 2` per confronto diretto con i 32 t/s storici e i 14.71 t/s odierni, prima di toccare la config di produzione.
