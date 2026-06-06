# Piano Locale Router OpenCode

Obiettivo: scegliere il modello giusto per ogni prompt senza riavviare OpenCode a ogni richiesta.

## Routing

### Prima Fase

- Scrematura con `qwen-small`.
- Coding normale con `qwen36-iq3`.
- Review con `qwen36-iq3`.
- Qualita maggiore con `qwen36-opus-iq4`.
- Task pesanti con `qwen-opus-q8`.

### Router Vero

- Mettere uno shim OpenAI-compatible davanti a `llama-swap`.
- Far leggere al router ogni request.
- Usare regole semplici e deterministiche prima di passare a logiche piu sofisticate.
- Tenere OpenCode sempre acceso: niente riavvii per singolo prompt.

### Fallback

- Se il router non e sicuro, usare `qwen36-iq3`.
- Se il prompt e breve o banale, usare `qwen-small`.
- Se il task e ambiguo ma importante, salire a `qwen36-opus-iq4`.

## Cosa Abbiamo Già Verificato

I dettagli di stato, benchmark, classifica modelli e limiti attuali restano in [docs/opencode-local-llama-swap.md](D:/repos/ik_llama.cpp/docs/opencode-local-llama-swap.md).

## Prossimi Passi

1. Scrivere la policy di routing in forma tabellare.
2. Implementare uno shim minimale.
3. Agganciare OpenCode al router.
4. Testare 20-40 prompt reali.
5. Tenere un log di scelta modello, tempo e risultato.
6. Ritoccare le soglie solo dopo dati reali.

## Nota

Questa pagina e la sintesi operativa del piano. La documentazione di stato resta in `docs/opencode-local-llama-swap.md`.
