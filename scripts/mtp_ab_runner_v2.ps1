param(
  [Parameter(Mandatory)][string]$Label,
  [string]$Bin = 'D:/repos/llama/build/bin/Release/llama-server.exe',
  [string[]]$ExtraArgs = @()
)
$ErrorActionPreference = 'Stop'
$model = 'D:/repos/ik_llama.cpp/models/Qwen3.6-35B-A3B-MTP-IQ4_XS.gguf'
$promptFile = 'D:/repos/ik_llama.cpp/scripts/mtp_ab_prompt.txt'
$port  = 18080
$logDir = 'D:/tmp'
New-Item -ItemType Directory -Force $logDir | Out-Null
$serverLog = "$logDir/mtp_srv_v2_$Label.log"

Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

$base = @(
  '--model', $model,
  '--host', '127.0.0.1', '--port', "$port",
  '-c', '4096', '-ngl', '99', '--n-cpu-moe', '35',
  '-b', '512', '-ub', '32',
  '-ctk', 'q8_0', '-ctv', 'q4_0', '-fa', 'on',
  '-t', '12', '--mlock', '--no-mmap',
  '--checkpoint-every-n-tokens', '-1'
)
$allArgs = $base + $ExtraArgs

Write-Host "[$Label] bin=$Bin extra=$($ExtraArgs -join ' ')"
$srv = Start-Process -FilePath $Bin -ArgumentList $allArgs `
  -RedirectStandardOutput $serverLog -RedirectStandardError "$serverLog.err" `
  -NoNewWindow -PassThru

$deadline = (Get-Date).AddMinutes(3)
$ready = $false
while ((Get-Date) -lt $deadline) {
  try {
    $h = Invoke-WebRequest "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 2
    if ($h.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep 1 }
}
if (-not $ready) {
  Write-Host "[$Label] server failed to become ready"
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  exit 1
}

$prompt = Get-Content $promptFile -Raw
$body = @{
  prompt = $prompt
  n_predict = 256
  temperature = 0.1
  top_p = 0.95
  top_k = 20
  seed = 42
  cache_prompt = $false
} | ConvertTo-Json

$t0 = Get-Date
try {
  $resp = Invoke-RestMethod "http://127.0.0.1:$port/completion" `
    -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 300
  $wall = ((Get-Date) - $t0).TotalSeconds
  $t = $resp.timings
  $obj = [PSCustomObject]@{
    label = $Label
    wall_s = [math]::Round($wall, 2)
    prompt_n = $t.prompt_n
    pp_tps   = [math]::Round($t.prompt_per_second, 2)
    pred_n   = $t.predicted_n
    tg_tps   = [math]::Round($t.predicted_per_second, 2)
    pred_ms  = [math]::Round($t.predicted_ms, 1)
  }
  $obj | ConvertTo-Json -Compress
  $obj | Export-Csv -Append -NoTypeInformation "$logDir/mtp_ab_v2.csv"
} finally {
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep 2
}
