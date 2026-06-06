param(
  [string]$Listen = "127.0.0.1:9292",
  [string]$Config = "D:\repos\ik_llama.cpp\llama-swap.config.yaml",
  [switch]$Restart,
  [switch]$Background,
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$llamaSwap = "D:\repos\ik_llama.cpp\bin\llama-swap.exe"
if (-not (Test-Path -LiteralPath $llamaSwap)) {
  throw "llama-swap.exe not found at $llamaSwap"
}

if (-not (Test-Path -LiteralPath $Config)) {
  throw "llama-swap config not found at $Config"
}

$hostName, $portText = $Listen -split ":", 2
$port = [int]$portText

function Test-LocalPort {
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

function Wait-LocalPort {
  param(
    [string]$HostName,
    [int]$Port,
    [int]$TimeoutSeconds
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-LocalPort -HostName $HostName -Port $Port) {
      return $true
    }
    Start-Sleep -Milliseconds 250
  }
  return $false
}

function Test-LlamaSwapEndpoint {
  param(
    [string]$Listen
  )

  try {
    $response = Invoke-RestMethod "http://$Listen/v1/models" -TimeoutSec 2
    return $null -ne $response.data
  } catch {
    return $false
  }
}

if ($Restart) {
  Get-Process llama-swap,llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith("D:\repos\ik_llama.cpp\", [System.StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force
  Start-Sleep -Seconds 1
}

if (Test-LocalPort -HostName $hostName -Port $port) {
  if (Test-LlamaSwapEndpoint -Listen $Listen) {
    Write-Host "llama-swap endpoint already responds on http://$Listen"
    Write-Host "Use -Restart to stop local llama-swap/llama-server processes and start again."
    return
  }

  throw "Port $Listen is already open, but it is not a llama-swap OpenAI-compatible endpoint."
}

if ($Background) {
  $logDir = "D:\repos\ik_llama.cpp\logs"
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null

  $stdout = Join-Path $logDir "llama-swap.out.log"
  $stderr = Join-Path $logDir "llama-swap.err.log"
  $args = @("-config", $Config, "-listen", $Listen, "-watch-config")

  Start-Process -FilePath $llamaSwap `
    -ArgumentList $args `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr

  if (-not (Wait-LocalPort -HostName $hostName -Port $port -TimeoutSeconds $TimeoutSeconds)) {
    throw "llama-swap did not start on http://$Listen within $TimeoutSeconds seconds. Check $stderr"
  }

  if (-not (Test-LlamaSwapEndpoint -Listen $Listen)) {
    throw "llama-swap started a process, but http://$Listen/v1/models did not respond. Check $stderr"
  }

  Write-Host "llama-swap started on http://$Listen"
  return
}

& $llamaSwap -config $Config -listen $Listen -watch-config
