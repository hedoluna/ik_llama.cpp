param(
  [Parameter(Mandatory)][string]$Model,
  [Parameter(Mandatory)][string]$Label,
  [string]$Bin = 'D:/repos/ik_llama.cpp/build/bin/Release/llama-server.exe',
  [int]$Port = 18080,
  [int]$Ngl = 999,
  [int]$Ctx = 8192,
  [string[]]$ExtraArgs = @()
)
$ErrorActionPreference = 'Stop'
$logDir = 'D:/tmp'
New-Item -ItemType Directory -Force $logDir | Out-Null
$serverLog = "$logDir/itlegal_srv_$Label.log"
$benchOut  = "D:/repos/ik_llama.cpp/scripts/results_it_legal_$Label.json"

Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

$base = @(
  '--model', $Model,
  '--host', '127.0.0.1', '--port', "$Port",
  '-c', "$Ctx", '-ngl', "$Ngl", '-fa', 'on', '-t', '8',
  '--no-mmap',
  '--ctx-checkpoints-interval', '0'
)
$allArgs = $base + $ExtraArgs

Write-Host "[$Label] starting server: $Model"
$srv = Start-Process -FilePath $Bin -ArgumentList $allArgs `
  -RedirectStandardOutput $serverLog -RedirectStandardError "$serverLog.err" `
  -NoNewWindow -PassThru

$deadline = (Get-Date).AddMinutes(3)
$ready = $false
while ((Get-Date) -lt $deadline) {
  try {
    $h = Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
    if ($h.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep 1 }
}
if (-not $ready) {
  Write-Host "[$Label] server failed to become ready"
  Get-Content "$serverLog.err" -Tail 30
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  exit 1
}

Write-Host "[$Label] running bench..."
try {
  py D:/repos/ik_llama.cpp/scripts/it_legal_bench.py `
    --base-url "http://127.0.0.1:$Port" `
    --model $Label `
    --output $benchOut
} finally {
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep 2
}
