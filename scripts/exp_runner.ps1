param(
  [Parameter(Mandatory)][string]$Label,
  [Parameter(Mandatory)][string]$Bin,
  [Parameter(Mandatory)][string]$Model,
  [string[]]$ExtraArgs = @(),
  [string]$PromptFile = 'D:/repos/ik_llama.cpp/scripts/mtp_ab_prompt.txt',
  [int]$NPredict = 256,
  [int]$Port = 18080,
  [int]$ReadyTimeoutMin = 5,
  [string]$Samplers = $null,
  [hashtable]$ReqOverride = @{}
)
$ErrorActionPreference = 'Stop'
$logDir = 'D:/tmp'
New-Item -ItemType Directory -Force $logDir | Out-Null
$serverLog = "$logDir/exp_$Label.log"

Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

$base = @(
  '--model', $Model,
  '--host', '127.0.0.1', '--port', "$Port",
  '-c', '4096', '-ngl', '99',
  '-fa', 'on',
  '-t', '12', '--mlock', '--no-mmap'
)
$allArgs = $base + $ExtraArgs

Write-Host "[$Label] starting: $($ExtraArgs -join ' ')"
$srv = Start-Process -FilePath $Bin -ArgumentList $allArgs `
  -RedirectStandardOutput $serverLog -RedirectStandardError "$serverLog.err" `
  -NoNewWindow -PassThru

$deadline = (Get-Date).AddMinutes($ReadyTimeoutMin)
$ready = $false
while ((Get-Date) -lt $deadline) {
  try {
    $h = Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
    if ($h.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep 1 }
}
if (-not $ready) {
  Write-Host "[$Label] not ready in $ReadyTimeoutMin min"
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  exit 1
}

$prompt = Get-Content $PromptFile -Raw
$req = @{
  prompt = $prompt
  n_predict = $NPredict
  temperature = 0.1
  top_p = 0.95
  top_k = 20
  seed = 42
  cache_prompt = $false
}
foreach ($k in $ReqOverride.Keys) { $req[$k] = $ReqOverride[$k] }
if ($Samplers) { $req['samplers'] = $Samplers }
$body = $req | ConvertTo-Json

$t0 = Get-Date
try {
  $resp = Invoke-RestMethod "http://127.0.0.1:$Port/completion" `
    -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 600
  $wall = ((Get-Date) - $t0).TotalSeconds
  $t = $resp.timings
  $obj = [PSCustomObject]@{
    label    = $Label
    wall_s   = [math]::Round($wall, 2)
    prompt_n = $t.prompt_n
    pp_tps   = [math]::Round($t.prompt_per_second, 2)
    pred_n   = $t.predicted_n
    tg_tps   = [math]::Round($t.predicted_per_second, 2)
    pred_ms  = [math]::Round($t.predicted_ms, 1)
  }
  $obj | ConvertTo-Json -Compress
  $obj | Export-Csv -Append -NoTypeInformation "$logDir/exp_results.csv"
} finally {
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep 2
}
