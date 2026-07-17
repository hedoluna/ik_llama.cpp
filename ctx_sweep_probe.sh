#!/bin/bash
# Probe decode throughput across context sizes, same model/flags as validated daily config.
set -e
cd /d/repos/ik_llama.cpp
PY="D:/repos/trading-algo/.venv-py312/Scripts/python.exe"
PORT=8096
CTX_VALUES="24000 32000 50000 64000 80000 100000"

taskkill //F //IM llama-server.exe 2>/dev/null || true
sleep 2

echo "ctx,predicted_per_second,prompt_per_second,load_time_s" > ctx_sweep_results.csv

for CTX in $CTX_VALUES; do
  echo "=== ctx=$CTX ===" >&2
  LOGF="ctx_probe_${CTX}.log"
  START=$(date +%s)
  ./build/bin/Release/llama-server.exe \
    --model models/Qwen3.6-35B-A3B-IQ3_K_R4.gguf \
    --host 127.0.0.1 --port $PORT --jinja --reasoning off \
    -c $CTX -ngl 95 --n-cpu-moe 30 \
    -ctk q4_0 -ctv q8_0 -b 1024 -ub 256 -fa on -t 8 --no-mmap \
    --chat-template-kwargs '{"enable_thinking":false}' \
    --ctx-checkpoints-interval 0 \
    > "$LOGF" 2>&1 &
  SPID=$!

  # wait for ready
  READY=0
  for i in $(seq 1 90); do
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/v1/models" 2>/dev/null | grep -q 200; then
      READY=1
      break
    fi
    sleep 1
  done
  LOADEND=$(date +%s)
  LOADTIME=$((LOADEND - START))

  if [ "$READY" != "1" ]; then
    echo "$CTX,FAIL,FAIL,$LOADTIME" >> ctx_sweep_results.csv
    taskkill //F //IM llama-server.exe 2>/dev/null || true
    sleep 2
    continue
  fi

  curl -s http://127.0.0.1:$PORT/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"q","messages":[{"role":"user","content":"Scrivi una funzione Python fizzbuzz(n) che stampa i numeri da 1 a n: Fizz se divisibile per 3, Buzz per 5, FizzBuzz per entrambi. Solo il codice."}],"temperature":0.7,"top_k":64,"top_p":0.75,"max_tokens":220,"stream":false,"cache_prompt":true,"chat_template_kwargs":{"enable_thinking":false}}' \
    > "probe_ctx_${CTX}.json"

  PPS=$("$PY" -c "import json; d=json.load(open('probe_ctx_${CTX}.json')); print(d.get('timings',{}).get('predicted_per_second','ERR'))")
  PROMPS=$("$PY" -c "import json; d=json.load(open('probe_ctx_${CTX}.json')); print(d.get('timings',{}).get('prompt_per_second','ERR'))")

  echo "$CTX,$PPS,$PROMPS,$LOADTIME" >> ctx_sweep_results.csv
  echo "  -> predicted_per_second=$PPS  load=${LOADTIME}s" >&2

  taskkill //F //IM llama-server.exe 2>/dev/null || true
  sleep 3
done

echo "=== DONE ===" >&2
cat ctx_sweep_results.csv >&2
