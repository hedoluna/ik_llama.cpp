param(
  [Parameter(Mandatory = $true)]
  [string[]]$Model,

  [ValidateSet("v4", "v5", "both")]
  [string]$Suite = "v4",

  [string]$BenchUrl = "http://127.0.0.1:8292/v1/chat/completions",
  [string]$RalphDir = "D:\repos\ralph\local_ralph",
  [string]$OutputRoot = "D:\repos\ik_llama.cpp\bench-ralph-realworld",
  [switch]$Restart,
  [switch]$NoStart,
  [switch]$StopAfter,
  [int]$SmokeMaxTokens = 32
)

$ErrorActionPreference = "Stop"

$repo = "D:\repos\ik_llama.cpp"
$startScript = Join-Path $repo "scripts\start-opencode-local.ps1"
$stopScript = Join-Path $repo "scripts\opencode-local.ps1"
$v4Script = Join-Path $RalphDir "coding_benchmark_v4_realworld.py"
$v5Script = Join-Path $RalphDir "coding_benchmark_v5_ts_focus.py"

if (-not (Test-Path -LiteralPath $startScript)) { throw "Missing $startScript" }
if (-not (Test-Path -LiteralPath $stopScript)) { throw "Missing $stopScript" }
if (-not (Test-Path -LiteralPath $v4Script)) { throw "Missing $v4Script" }
if (-not (Test-Path -LiteralPath $v5Script)) { throw "Missing $v5Script" }

function Resolve-Python {
  $candidates = @(
    "py",
    "python",
    "python3",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python39\python.exe"
  )

  foreach ($candidate in $candidates) {
    try {
      $cmd = Get-Command $candidate -ErrorAction Stop
      $exe = $cmd.Source
      if ($candidate -eq "py") {
        & $exe -3 -c "import sys; print(sys.executable)" *> $null
      } else {
        & $exe -c "import sys; print(sys.executable)" *> $null
      }
      if ($LASTEXITCODE -eq 0) {
        return @{ File = $exe; Prefix = $(if ($candidate -eq "py") { @("-3") } else { @() }) }
      }
    } catch {
      continue
    }
  }
  throw "No working Python interpreter found. The Windows Store python alias is not enough."
}

function Invoke-Smoke {
  param([string]$Url, [string]$ModelId, [int]$MaxTokens)

  $body = @{
    model = $ModelId
    messages = @(@{ role = "user"; content = "Rispondi solo con OK." })
    max_tokens = $MaxTokens
    temperature = 0
    seed = 42
    cache_prompt = $true
    chat_template_kwargs = @{ enable_thinking = $false }
  } | ConvertTo-Json -Depth 8

  $t0 = Get-Date
  try {
    $response = Invoke-RestMethod -Method Post -Uri $Url -Body $body -ContentType "application/json" -TimeoutSec 180
    $elapsed = [Math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
    $message = $response.choices[0].message
    $content = [string]$message.content
    $reasoning = [string]$message.reasoning_content
    return [ordered]@{
      ok = ($content.Trim().Length -gt 0)
      elapsed_s = $elapsed
      content = $content
      reasoning_chars = $reasoning.Length
      usage = $response.usage
    }
  } catch {
    return [ordered]@{
      ok = $false
      elapsed_s = [Math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
      error = $_.Exception.Message
    }
  }
}

function Invoke-RalphSuite {
  param(
    [hashtable]$Python,
    [string]$Script,
    [string]$WorkDir,
    [string]$Url,
    [string]$ModelId,
    [string]$LogName
  )

  $env:BENCH_URL = $Url
  $env:BENCH_MODEL = $ModelId

  $log = Join-Path $WorkDir $LogName
  $stdoutLog = "$log.stdout"
  $stderrLog = "$log.stderr"
  Push-Location $WorkDir
  try {
    $args = @()
    $args += $Python.Prefix
    $args += $Script
    $proc = Start-Process -FilePath $Python.File -ArgumentList $args `
      -NoNewWindow -Wait -PassThru `
      -RedirectStandardOutput $stdoutLog `
      -RedirectStandardError $stderrLog

    $combined = @()
    if (Test-Path -LiteralPath $stderrLog) {
      $combined += Get-Content -LiteralPath $stderrLog -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $stdoutLog) {
      $combined += Get-Content -LiteralPath $stdoutLog -ErrorAction SilentlyContinue
    }
    $combined | Set-Content -LiteralPath $log -Encoding UTF8
    $combined | ForEach-Object { Write-Host $_ }
    return $proc.ExitCode
  } finally {
    Pop-Location
  }
}

$python = Resolve-Python
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = Join-Path $OutputRoot $timestamp
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null

if (-not $NoStart) {
  & $startScript -Background -WithRouter:$false -Restart:$Restart
}

$manifest = [ordered]@{
  timestamp = $timestamp
  bench_url = $BenchUrl
  suite = $Suite
  ralph_dir = $RalphDir
  python = $python.File
  models = @()
}

try {
  foreach ($modelId in $Model) {
    $safeModel = ($modelId -replace '[^A-Za-z0-9._-]', '_')
    $modelDir = Join-Path $runRoot $safeModel
    New-Item -ItemType Directory -Path $modelDir -Force | Out-Null

    Write-Host ""
    Write-Host "=== Ralph realworld bench: $modelId ==="
    Write-Host "Output: $modelDir"

    $smoke = Invoke-Smoke -Url $BenchUrl -ModelId $modelId -MaxTokens $SmokeMaxTokens
    $smoke | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $modelDir "smoke.json") -Encoding UTF8
    if (-not $smoke.ok) {
      Write-Warning "Smoke failed for $modelId; skipping benchmark suites."
      $manifest.models += [ordered]@{ model = $modelId; smoke = $smoke; skipped = $true }
      continue
    }

    $entry = [ordered]@{ model = $modelId; smoke = $smoke; suites = @() }

    if ($Suite -eq "v4" -or $Suite -eq "both") {
      Write-Host "Running v4 realworld suite for $modelId..."
      $code = Invoke-RalphSuite -Python $python -Script $v4Script -WorkDir $modelDir -Url $BenchUrl -ModelId $modelId -LogName "v4.log"
      if (Test-Path -LiteralPath (Join-Path $modelDir "coding_benchmark_v4_results.json")) {
        Rename-Item -LiteralPath (Join-Path $modelDir "coding_benchmark_v4_results.json") -NewName "v4-results.json" -Force
      }
      $entry.suites += [ordered]@{ suite = "v4"; exit_code = $code }
    }

    if ($Suite -eq "v5" -or $Suite -eq "both") {
      Write-Host "Running v5 TS-focus suite for $modelId..."
      $code = Invoke-RalphSuite -Python $python -Script $v5Script -WorkDir $modelDir -Url $BenchUrl -ModelId $modelId -LogName "v5.log"
      if (Test-Path -LiteralPath (Join-Path $modelDir "coding_benchmark_v5_results.json")) {
        Rename-Item -LiteralPath (Join-Path $modelDir "coding_benchmark_v5_results.json") -NewName "v5-results.json" -Force
      }
      $entry.suites += [ordered]@{ suite = "v5"; exit_code = $code }
    }

    $manifest.models += $entry
  }
} finally {
  $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runRoot "manifest.json") -Encoding UTF8
  if ($StopAfter) {
    & $stopScript -Stop
  }
  Write-Host ""
  Write-Host "Run manifest: $(Join-Path $runRoot 'manifest.json')"
}
