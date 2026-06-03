# Coding bench: pass --models <stable name> so the bench tests only the loaded server
$ErrorActionPreference = 'Continue'
$out = 'D:/tmp/bench_new_v2.csv'
"model,build,wall_s,passed,total" | Out-File $out -Encoding utf8

$ml = 'D:/repos/llama_mtp/build_new/bin/Release/llama-server.exe'
$ik = 'D:/repos/ik_llama.cpp/build/bin/Release/llama-server.exe'

$matrix = @(
  @{ tag='Coder-1.5B';      label='qwen2.5-coder-1.5b';
     bin=$ik; mod='F:/LLM_Models/lm-studio/models/migarcoes/Qwen-Qwen2.5-Coder-1.5B-Instruct/Qwen-Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--no-mmap','--jinja') },
  @{ tag='Phi-4-mini';      label='phi-4-mini-instruct';
     bin=$ml; mod='D:/repos/ik_llama.cpp/models/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--jinja') },
  @{ tag='Qwen3.5-4B';      label='qwen3.5-4b';
     bin=$ik; mod='D:/repos/ik_llama.cpp/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--no-mmap','--jinja') },
  @{ tag='Granite-4.1-8B';  label='granite-4.1-8b';
     bin=$ml; mod='D:/repos/ik_llama.cpp/models/ibm-granite_granite-4.1-8b-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--jinja') },
  @{ tag='Qwen3-8B-CSDist'; label='qwen3-8b-claude-distill';
     bin=$ml; mod='D:/repos/ik_llama.cpp/models/Qwen3-8B-claude-sonnet-4.5-high-reasoning-distill-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--jinja') }
)

foreach ($m in $matrix) {
  Write-Host ("==== {0} ====" -f $m.tag)
  Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
  Start-Sleep 2

  $srvLog = "D:/tmp/bench2_srv_$($m.tag).log"
  $allArgs = @('--model',$m.mod,'--host','127.0.0.1','--port','1234') + $m.args
  $srv = Start-Process -FilePath $m.bin -ArgumentList $allArgs `
    -RedirectStandardOutput $srvLog -RedirectStandardError "$srvLog.err" `
    -NoNewWindow -PassThru

  $ok = $false
  for ($i=0; $i -lt 240; $i++) {
    try {
      $r = Invoke-WebRequest 'http://127.0.0.1:1234/v1/models' -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep 1 }
  }
  if (-not $ok) {
    Write-Host "FAIL ready: $($m.tag)"
    "$($m.tag),fail,0,0,0" | Out-File $out -Append -Encoding utf8
    Stop-Process -Id $srv.Id -Force -EA SilentlyContinue
    continue
  }

  $t0 = Get-Date
  $benchOut = "D:/tmp/bench2_run_$($m.tag).log"
  Push-Location D:/repos/ralph/local_ralph
  & py coding_benchmark.py --models $m.label 2>&1 | Tee-Object $benchOut | Out-Null
  Pop-Location
  $wall = ((Get-Date) - $t0).TotalSeconds

  # robust parse: search for 'Test totali: X/Y' or 'Passed: X/Y' or '\d+/\d+' near 'Risultat'
  $line = (Select-String -Path $benchOut -Pattern '(\d+)\s*/\s*(\d+)' | Select-Object -Last 1).Line
  $passed = '?'; $total = '?'
  if ($line -match '(\d+)\s*/\s*(\d+)') { $passed = $matches[1]; $total = $matches[2] }
  "$($m.tag),$([System.IO.Path]::GetFileName($m.bin) -replace '.exe',''),$([math]::Round($wall,1)),$passed,$total" | Out-File $out -Append -Encoding utf8

  Stop-Process -Id $srv.Id -Force -EA SilentlyContinue
  Start-Sleep 3
}
Write-Host "DONE -- summary:"
Get-Content $out
