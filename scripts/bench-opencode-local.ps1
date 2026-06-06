param(
  [string[]]$Modes = @("fast", "coding", "quality"),
  [string]$Project = "D:\repos\ik_llama.cpp",
  [string]$OutputDir = "D:\repos\ik_llama.cpp\bench-opencode-local",
  [switch]$IncludeMax,
  [switch]$Restart,
  [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"

$startScript = "D:\repos\ik_llama.cpp\scripts\start-opencode-local.ps1"
if (-not (Test-Path -LiteralPath $startScript)) {
  throw "start-opencode-local.ps1 not found at $startScript"
}

if ($IncludeMax -and "max" -notin $Modes) {
  $Modes += "max"
}

$modelByMode = @{
  fast = "llama-swap/qwen-small"
  granite = "llama-swap/granite-fast"
  coding = "llama-swap/qwen36-iq3"
  quality = "llama-swap/qwen36-opus-iq4"
  "qwen-coder-next" = "llama-swap/qwen-coder"
  oss = "llama-swap/gpt-oss-20b"
  max = "llama-swap/qwen-opus-q8"
}

$agentByMode = @{
  fast = "fast"
  granite = $null
  coding = "coding"
  quality = "quality"
  "qwen-coder-next" = "qwen-coder-next"
  oss = $null
  max = "max"
}

$tasks = @(
  @{
    id = "explain-bug"
    prompt = "In massimo 8 righe, spiega il bug in questo pseudo-codice e proponi una fix: function getUser(id) { if (cache[id]) return cache[id]; user = db.find(id); cache[id] = user.name; return user; }"
  },
  @{
    id = "write-patch"
    prompt = "Scrivi una patch TypeScript minimale per rendere questa funzione sicura quando input e null o undefined: export function slugify(input: string) { return input.trim().toLowerCase().replaceAll(' ', '-'); }"
  },
  @{
    id = "review"
    prompt = "Fai una code review concisa di questa funzione C++ e indica i 3 rischi principali: const char* name(std::string s) { return s.c_str(); }"
  }
)

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
& $startScript -Background -Restart:$Restart

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$summaryPath = Join-Path $OutputDir "summary-$stamp.csv"
$detailsPath = Join-Path $OutputDir "details-$stamp.jsonl"
$results = @()

foreach ($mode in $Modes) {
  if (-not $modelByMode.ContainsKey($mode)) {
    throw "Unknown mode '$mode'. Valid modes: $($modelByMode.Keys -join ', ')"
  }

  foreach ($task in $tasks) {
    $model = $modelByMode[$mode]
    $agent = $agentByMode[$mode]
    $args = @("run", "--dir", $Project, "--model", $model, "--format", "json")
    if ($agent) {
      $args += @("--agent", $agent)
    }
    $args += $task.prompt

    Write-Host "[$mode] $($task.id) -> $model"
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $raw = & opencode @args 2>&1
    $exitCode = $LASTEXITCODE
    $watch.Stop()

    $textParts = @()
    $finish = $null
    $events = @()
    foreach ($line in @($raw)) {
      if (-not $line) {
        continue
      }
      try {
        $event = $line | ConvertFrom-Json
        $events += $event
        if ($event.type -eq "text") {
          $textParts += $event.part.text
        }
        if ($event.type -eq "step_finish") {
          $finish = $event
        }
      } catch {
        $textParts += [string]$line
      }
    }

    $text = ($textParts -join "")
    $tokens = $finish.part.tokens
    $row = [pscustomobject]@{
      timestamp = (Get-Date).ToString("o")
      mode = $mode
      model = $model
      agent = $agent
      task = $task.id
      exit_code = $exitCode
      duration_ms = $watch.ElapsedMilliseconds
      input_tokens = if ($tokens) { $tokens.input } else { $null }
      output_tokens = if ($tokens) { $tokens.output } else { $null }
      total_tokens = if ($tokens) { $tokens.total } else { $null }
      output_chars = $text.Length
      output = $text
    }

    $results += $row
    ($row | ConvertTo-Json -Compress) | Add-Content -LiteralPath $detailsPath

    if ($exitCode -ne 0) {
      Write-Warning "opencode exited with $exitCode for mode '$mode' task '$($task.id)'"
    }
    if ($watch.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
      Write-Warning "mode '$mode' task '$($task.id)' exceeded TimeoutSeconds=$TimeoutSeconds"
    }
  }
}

$results |
  Select-Object timestamp, mode, model, agent, task, exit_code, duration_ms, input_tokens, output_tokens, total_tokens, output_chars |
  Export-Csv -LiteralPath $summaryPath -NoTypeInformation

Write-Host ""
Write-Host "Benchmark complete"
Write-Host "Summary: $summaryPath"
Write-Host "Details: $detailsPath"

$results |
  Sort-Object mode, task |
  Select-Object mode, task, duration_ms, total_tokens, output_chars, exit_code |
  Format-Table -AutoSize
