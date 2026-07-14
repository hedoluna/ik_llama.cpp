param(
  [string]$Base = "http://127.0.0.1:8291/v1",
  [string]$Provider = "llama-swap",
  [string[]]$ExpectedModels = @(
    "qwen36-iq3",
    "qwen36-opus-iq4",
    "qwen36-opus-iq3",
    "quality-guided",
    "qwen36-mtp",
    "nemotron-fast",
    "agentworld",
    "granite-fast",
    "minerva-ita",
    "mellum2-instruct",
    "mellum2-thinking",
    "gpt-oss-20b",
    "ornith-35b-iq3-imat",
    "ornith-9b-q4"
  ),
  [switch]$Chat
)

$ErrorActionPreference = "Stop"

Write-Host "Checking $base/models"
$models = Invoke-RestMethod "$base/models"
$models.data | Select-Object id, object | Format-Table -AutoSize

$modelIds = @($models.data | ForEach-Object { $_.id })
$missingApiModels = @($ExpectedModels | Where-Object { $_ -notin $modelIds })
if ($missingApiModels.Count -gt 0) {
  throw "Missing model(s) from $Base/models: $($missingApiModels -join ', ')"
}

Write-Host "`nChecking opencode model registration"
$opencodeModels = @(opencode models $Provider)
$opencodeModels

$expectedOpenCodeModels = @($ExpectedModels | ForEach-Object { "$Provider/$_" })
$missingOpenCodeModels = @($expectedOpenCodeModels | Where-Object { $_ -notin $opencodeModels })
if ($missingOpenCodeModels.Count -gt 0) {
  throw "Missing model(s) from opencode models ${Provider}: $($missingOpenCodeModels -join ', ')"
}

if ($Chat) {
  Write-Host "`nChecking chat completion with nemotron-fast"
  $body = @{
    model = "nemotron-fast"
    messages = @(@{ role = "user"; content = "Rispondi solo con OK." })
    max_tokens = 16
    temperature = 0
  } | ConvertTo-Json -Depth 6

  $response = Invoke-RestMethod -Method Post -Uri "$Base/chat/completions" -ContentType "application/json" -Body $body
  $content = $response.choices[0].message.content
  if ($content -ne "OK") {
    throw "Unexpected chat completion response: '$content'"
  }
  Write-Host "Chat completion OK"
}

Write-Host "`nLocal OpenCode model setup OK"
