# Run ralph coding_benchmark across the new 2026-05-17 models + Coder-1.5B baseline
$ErrorActionPreference = 'Continue'
$out = 'D:/tmp/bench_new_2026_05_17.csv'
"model,build,wall_s,score" | Out-File $out -Encoding utf8

$ml = 'D:/repos/llama_mtp/build_new/bin/Release/llama-server.exe'
$ik = 'D:/repos/ik_llama.cpp/build/bin/Release/llama-server.exe'

$matrix = @(
  @{ name='Coder-1.5B-baseline';
     bin=$ik;
     mod='F:/LLM_Models/lm-studio/models/migarcoes/Qwen-Qwen2.5-Coder-1.5B-Instruct/Qwen-Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--no-mmap','--jinja','--host','127.0.0.1','--port','1234') },
  @{ name='Phi-4-mini-instruct';
     bin=$ml;
     mod='D:/repos/ik_llama.cpp/models/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--jinja','--host','127.0.0.1','--port','1234') },
  @{ name='Qwen3.5-4B';
     bin=$ik;
     mod='D:/repos/ik_llama.cpp/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--no-mmap','--jinja','--host','127.0.0.1','--port','1234') },
  @{ name='Granite-4.1-8B';
     bin=$ml;
     mod='D:/repos/ik_llama.cpp/models/ibm-granite_granite-4.1-8b-Q4_K_M.gguf';
     args=@('-c','16384','-ngl','999','-fa','on','-t','8','--jinja','--host','127.0.0.1','--port','1234') }
)

foreach ($m in $matrix) {
  Write-Host "==== $($m.name) ===="
  Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
  Start-Sleep 2

  $srvLog = "D:/tmp/bench_srv_$($m.name).log"
  $srv = Start-Process -FilePath $m.bin -ArgumentList (@('--model',$m.mod) + $m.args) `
    -RedirectStandardOutput $srvLog -RedirectStandardError "$srvLog.err" `
    -NoNewWindow -PassThru

  # wait ready
  $ok = $false
  for ($i=0; $i -lt 240; $i++) {
    try {
      $r = Invoke-WebRequest 'http://127.0.0.1:1234/v1/models' -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep 1 }
  }
  if (-not $ok) {
    Write-Host "FAIL ready: $($m.name)"
    "$($m.name),fail,0,not-ready" | Out-File $out -Append -Encoding utf8
    Stop-Process -Id $srv.Id -Force -EA SilentlyContinue
    continue
  }

  $t0 = Get-Date
  $benchOut = "D:/tmp/bench_run_$($m.name).log"
  Push-Location D:/repos/ralph/local_ralph
  & py coding_benchmark.py 2>&1 | Tee-Object $benchOut | Select-Object -Last 5
  Pop-Location
  $wall = ((Get-Date) - $t0).TotalSeconds

  # extract score line like "Passed: X/Y"
  $score = (Select-String -Path $benchOut -Pattern 'Passed:\s*\d+/\d+' | Select-Object -First 1).Line
  if (-not $score) { $score = (Select-String -Path $benchOut -Pattern '\d+/51|\d+ ?/ ?51' | Select-Object -First 1).Line }
  "$($m.name),$([System.IO.Path]::GetFileName($m.bin) -replace '.exe',''),$([math]::Round($wall,1)),$score" | Out-File $out -Append -Encoding utf8

  Stop-Process -Id $srv.Id -Force -EA SilentlyContinue
  Start-Sleep 3
}
Write-Host "DONE -- summary:"
Get-Content $out
