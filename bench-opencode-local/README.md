# Benchmark OpenCode locale

Questa cartella contiene i risultati prodotti da:

```powershell
D:\repos\ik_llama.cpp\scripts\bench-opencode-local.ps1
```

Formato:

- `summary-*.csv`: metriche compatte per task/profilo.
- `details-*.jsonl`: dettagli con output testuale raccolto dagli eventi JSON di `opencode run`.

Baseline utile al 2026-06-07:

- `summary-20260606-231739.csv`: `fast` / `qwen-small`, 3 task brevi.
- `summary-20260606-233248.csv`: `coding` / `qwen36-iq3`, 3 task brevi.
- `summary-20260606-232234.csv`: run interrotto/parziale su `granite,coding,oss`; usarlo solo come segnale negativo per `granite` e `oss`.

Conclusioni operative:

- `qwen-small` e adatto a `ocl -Run "..."`.
- `qwen36-iq3` e il default principale per la Web UI/OpenCode interattivo.
- `granite-fast` e `gpt-oss-20b` non sono candidati principali per OpenCode locale in questa configurazione.

