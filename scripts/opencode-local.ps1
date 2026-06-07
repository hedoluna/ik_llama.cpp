param(
  [ValidateSet("auto", "fast", "coding", "review", "italian", "max", "quality", "qwen-coder-next", "granite", "oss")]
  [string]$Mode = "auto",
  [string]$Project = (Get-Location).Path,
  [string]$Run,
  [switch]$Web,
  [switch]$Tui,
  [switch]$Restart,
  [switch]$NoStart,
  [int]$WebPort = 4097
)

$ErrorActionPreference = "Stop"
$stateDir = "$env:USERPROFILE\.local\state\opencode-local"
$tuiBrokenMarker = Join-Path $stateDir "opentui-broken.marker"

$startScript = "D:\repos\ik_llama.cpp\scripts\start-opencode-local.ps1"
if (-not (Test-Path -LiteralPath $startScript)) {
  throw "start-opencode-local.ps1 not found at $startScript"
}

if (-not $NoStart) {
  & $startScript -Background -Restart:$Restart
}

New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

# In 'auto' the request goes to the router shim (model 'llama-swap/auto'), which
# picks the best model per prompt - for both interactive and non-interactive runs.
$effectiveMode = $Mode

$modelByMode = @{
  auto = "llama-swap/auto"
  fast = "llama-swap/qwen-small"
  coding = "llama-swap/qwen36-iq3"
  review = "llama-swap/qwen36-iq3"
  italian = "llama-swap/cerbero-ita"
  max = "llama-swap/qwen-opus-q8"
  quality = "llama-swap/qwen36-opus-iq4"
  "qwen-coder-next" = "llama-swap/qwen-coder"
  granite = "llama-swap/granite-fast"
  oss = "llama-swap/gpt-oss-20b"
}

$agentByMode = @{
  auto = "auto"
  fast = "fast"
  coding = "coding"
  review = "review"
  italian = "italian"
  max = "max"
  quality = "quality"
  "qwen-coder-next" = "qwen-coder-next"
  granite = $null
  oss = $null
}

$model = $modelByMode[$effectiveMode]
$agent = $agentByMode[$effectiveMode]

Write-Host "Starting OpenCode mode '$effectiveMode'"
if ($effectiveMode -ne $Mode) {
  Write-Host "Auto selected '$effectiveMode' for non-interactive run"
}
if ($model) {
  Write-Host "Model: $model"
} else {
  Write-Host "Model: OpenCode default from opencode.jsonc"
}

if (-not $Run -and -not $Web -and -not $Tui -and (Test-Path -LiteralPath $tuiBrokenMarker)) {
  $Web = $true
  Write-Host "OpenCode TUI is marked broken; starting Web UI directly."
  Write-Host "Use -Tui to retry the native TUI after updating VC++/OpenCode."
}

if ($Run) {
  $opencodeArgs = @("run", "--dir", $Project)
  if ($model) {
    $opencodeArgs += @("--model", $model)
  }
  if ($agent) {
    $opencodeArgs += @("--agent", $agent)
  }
  $opencodeArgs += $Run
} elseif ($Web) {
  $opencodeArgs = @("web", "--hostname", "127.0.0.1", "--port", "$WebPort")
} else {
  $opencodeArgs = @($Project)
  if ($model) {
    $opencodeArgs += @("--model", $model)
  }
  if ($agent) {
    $opencodeArgs += @("--agent", $agent)
  }
}

function Start-OpenCodeWeb {
  param(
    [string]$Project,
    [int]$WebPort
  )

  Write-Warning "OpenCode TUI failed to initialize. Starting OpenCode Web UI instead."
  Write-Host "Web UI: http://127.0.0.1:$WebPort/"
  Push-Location $Project
  try {
    & opencode web --hostname 127.0.0.1 --port $WebPort
  } finally {
    Pop-Location
  }
}

function Test-TcpPort {
  param(
    [string]$HostName,
    [int]$Port
  )

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $connection = $client.BeginConnect($HostName, $Port, $null, $null)
    if (-not $connection.AsyncWaitHandle.WaitOne(500)) {
      return $false
    }
    $client.EndConnect($connection)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

if ($Web -and (Test-TcpPort -HostName "127.0.0.1" -Port $WebPort)) {
  Write-Host "OpenCode Web UI already appears to be running."
  Write-Host "Web UI: http://127.0.0.1:$WebPort/"
  exit 0
}

Push-Location $Project
try {
  & opencode @opencodeArgs
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}

if (-not $Run -and -not $Web -and $exitCode -ne 0) {
  $latestLog = Get-ChildItem "$env:USERPROFILE\.local\share\opencode\log" -Filter "*.log" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if ($latestLog -and (Select-String -LiteralPath $latestLog.FullName -Pattern "Failed to initialize OpenTUI render library" -Quiet)) {
    Set-Content -LiteralPath $tuiBrokenMarker -Value "OpenTUI failed at $(Get-Date -Format o). Use ocl -Tui to retry after fixing VC++/OpenCode."
    Start-OpenCodeWeb -Project $Project -WebPort $WebPort
    exit $LASTEXITCODE
  }
}

exit $exitCode
