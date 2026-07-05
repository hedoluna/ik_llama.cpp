param(
  [ValidateSet("auto", "fast", "omp", "yi", "qwen2", "g2b", "g3b", "next", "big", "ornith")]
  [string]$Mode = "auto",
  [string]$Project = (Get-Location).Path,
  [string]$Run,
  [switch]$Restart,
  [switch]$NoStart,
  [switch]$Stop,
  [int]$RouterPort = 8291,
  [int]$SwapPort = 8292,
  [int]$ClassifierPort = 9998,
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

$startScript = "D:\repos\ik_llama.cpp\scripts\start-opencode-local.ps1"
if (-not (Test-Path -LiteralPath $startScript)) {
  throw "start-opencode-local.ps1 not found at $startScript"
}

if ($Stop) {
  Write-Host "Stopping OpenCode local stack..."
  & $startScript -Stop
  exit 0
}

if (-not $NoStart) {
  & $startScript -Background -Restart:$Restart
}

# Resolve local model name for llama-swap
$modelByMode = @{
  auto = "auto"
  fast = "qwen-small"
  omp = "qwen-small"
  yi = "Yi-Coder-1.5B-Chat-Q4_K_M"
  qwen2 = "Qwen2.5-Coder-1.5B-Q4_K_M"
  g2b = "granite-3.3-2b-instruct-Q6_K"
  g3b = "granite-4.1-3B-Q4_K_S"
  next = "Qwen3-Coder-Next-UD-Q2_K_XL"
  big = "daily-Qwen3.6-35B-A3B-IQ3_K_R4"
  ornith = "Ornith-1.0-35B-A3B-IQ3_K_R4-imat"
}

$model = $modelByMode[$Mode]

# We point OMP to llama-swap (or the router if auto-routing is desired)
if ($Mode -eq "auto") {
  $env:LM_STUDIO_BASE_URL = "http://127.0.0.1:$RouterPort/v1"
} else {
  $env:LM_STUDIO_BASE_URL = "http://127.0.0.1:$SwapPort/v1"
}
$env:LM_STUDIO_API_KEY = "dummy"

Write-Host "Starting OMP local mode '$Mode'"
if ($model -eq "auto") {
  Write-Host "Model: local auto-router"
} else {
  Write-Host "Model: lm-studio/$model"
}

$ompArgs = @()
if ($model -eq "auto") {
  $ompArgs += @("--model", "lm-studio/auto")
} else {
  $ompArgs += @("--model", "lm-studio/$model")
}

if ($Run) {
  $ompArgs += @("-p", $Run)
}

if ($RemainingArgs) {
  $ompArgs += $RemainingArgs
}

Push-Location $Project
try {
  & omp @ompArgs
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}

exit $exitCode
