# Leaderboard re-benchmark 2026-06-20

Runtime: `ik_llama.cpp` commit `6209394f` (build 4676), Release, CUDA 13.1, RTX A2000 6GB, Ryzen 9 5950X.

I sette nomi richiesti corrispondono a sei GGUF unici: `qwen-small` e `Qwen3.5-4B-Q4_K_M` sono lo stesso modello.

## Risultati

| Modello / profilo | Offload | pp128 | tg64 | FFT quality | Tempo FFT | Lettura |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `Qwen3-4B-Instruct-2507-Q4_K_M` | 999 layer | `1704.35 +/- 435.35 tok/s` | `66.11 +/- 0.27 tok/s` | `4/4` | `9.53s` | Miglior combinazione velocita/qualita nel gate comune. |
| `quality-iq3` | 8 layer, MQKV | `200.19 +/- 53.92 tok/s` | `16.29 +/- 1.58 tok/s` | `4/4` | `34.97s` | Miglior 35B del run; Ralph storico resta il segnale quality principale. |
| `qwen36-mtp` | 6 layer, MQKV | `161.09 +/- 39.13 tok/s` | `13.78 +/- 1.02 tok/s` | `4/4` | `38.44s` | Il throughput e del target base; il gate server usa MTP `n_max=1`. |
| `qwen36-iq3` | 8 layer, MQKV | `197.50 +/- 48.85 tok/s` | `15.37 +/- 1.26 tok/s` | `4/4` | `41.95s` | Solido, ma leggermente dietro `quality-iq3` in questo run. |
| `Qwen3.5-4B-Q4_K_M` / `qwen-small` | 999 layer, MQKV | `1486.63 +/- 359.12 tok/s` | `54.40 +/- 0.31 tok/s` | `3/4` | `22.19s` | Fallisce `bit_reverse` con 8 casi errati; il vecchio `4/4` non e confermato. |
| `Phi-4 14B Q4_K_M` | 8 layer | `168.51 +/- 11.22 tok/s` | `4.32 +/- 0.21 tok/s` | `3/4` | `471.34s` | Fallisce `find_peak_frequency` per output non parsabile; molto lento. |

## Metodo e limiti

- Throughput: `llama-bench -p 128 -n 64 -r 5 -fa 1 -ctk q8_0 -ctv q8_0 -t 16`, con offload coerente con i profili locali.
- Qualita: `coding_benchmark_fft.py`, quattro task binari (`bit_reverse`, peak frequency, Parsons code, DFT), server isolato e sequenziale.
- `llama-bench` non misura la speculazione MTP. Per `qwen36-mtp`, il risultato `tg64` e il decode del target base; la suite FFT e stata invece eseguita con `--spec-type mtp:n_max=1,p_min=0.0`.
- Il gate FFT e stretto e non sostituisce Ralph v4/v5 o OpenCode end-to-end.
- La varianza `pp128` resta alta sui Qwen; il ranking di qualita non deve essere deciso dal prompt-processing throughput.

## File raw

Ogni modello ha un file throughput `*.txt`, un file qualita `*.quality.txt` e log server separati nella stessa directory. `run.log` conserva anche i primi tentativi rifiutati dalla CLI per la sintassi `-mqkv`; le misure valide sono nei file modello finali, rieseguiti con `-mqkv 1`.
