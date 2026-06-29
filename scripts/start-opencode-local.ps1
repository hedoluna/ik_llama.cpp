param(
  [string]$Listen = "127.0.0.1:8292",
  [string]$Config = "D:\repos\ik_llama.cpp\llama-swap.config.yaml",
  [switch]$Restart,
  [switch]$Background,
  [int]$TimeoutSeconds = 30,
  [switch]$WithRouter = $true,
  [int]$ClassifierPort = 9998,
  [int]$RouterPort = 8291,
  [int]$ClassifierThreads = 8,
  [string]$SmallGguf = "D:\repos\ik_llama.cpp\models\Qwen_Qwen3.5-4B-Q4_K_M.gguf",
  [string]$LlamaServer = "D:\repos\ik_llama.cpp\build\bin\Release\llama-server.exe",
  [string]$RouterScript = "D:\repos\ik_llama.cpp\scripts\opencode-router.py"
)

$ErrorActionPreference = "Stop"
$logDir = "D:\repos\ik_llama.cpp\logs"

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

function Test-Url {
  param([string]$Url, [int]$TimeoutSec = 2)
  try {
    Invoke-RestMethod $Url -TimeoutSec $TimeoutSec | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Start-Classifier {
  param([string]$ListenHost, [int]$Port, [string]$Gguf, [string]$Exe,
        [int]$Threads, [string]$LogDir, [int]$TimeoutSeconds)

  if (Test-LocalPort -HostName $ListenHost -Port $Port) {
    if (Test-Url "http://${ListenHost}:$Port/v1/models") {
      Write-Host "classifier already responds on http://${ListenHost}:$Port"
      return
    }
    throw "Port ${ListenHost}:$Port is open but is not an OpenAI-compatible endpoint."
  }
  if (-not (Test-Path -LiteralPath $Exe)) { throw "llama-server.exe not found at $Exe" }
  if (-not (Test-Path -LiteralPath $Gguf)) { throw "classifier GGUF not found at $Gguf" }

  $out = Join-Path $LogDir "classifier.out.log"
  $err = Join-Path $LogDir "classifier.err.log"
  $a = @(
    "--model", $Gguf, "--alias", "qwen-small", "--port", "$Port", "--host", $ListenHost,
    "-ngl", "0", "--parallel", "1", "--ctx-size", "8192", "--jinja", "--reasoning", "off",
    "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--threads", "$Threads"
  )
  Start-Process -FilePath $Exe -ArgumentList $a -WindowStyle Hidden `
    -RedirectStandardOutput $out -RedirectStandardError $err

  if (-not (Wait-LocalPort -HostName $ListenHost -Port $Port -TimeoutSeconds ([Math]::Max($TimeoutSeconds, 60)))) {
    throw "classifier did not start on http://${ListenHost}:$Port. Check $err"
  }
  Write-Host "classifier (qwen-small, CPU) started on http://${ListenHost}:$Port"
}

function Start-Router {
  param([string]$ListenHost, [int]$Port, [string]$Script, [string]$LogDir, [int]$TimeoutSeconds)

  if (Test-LocalPort -HostName $ListenHost -Port $Port) {
    if (Test-Url "http://${ListenHost}:$Port/healthz") {
      Write-Host "router already responds on http://${ListenHost}:$Port"
      return
    }
    throw "Port ${ListenHost}:$Port is open but is not the router."
  }
  if (-not (Test-Path -LiteralPath $Script)) { throw "router script not found at $Script" }

  # Cloud tier (NVIDIA NIM) is opt-in via !cloud/!kimi/... overrides. The router
  # child inherits this process env; the key lives in D:\repos\.env (not a machine
  # var), so load it best-effort. Local-only routing is unaffected if it's absent.
  if (-not $env:NVIDIA_API_KEY) {
    $envFile = 'D:\repos\.env'
    if (Test-Path -LiteralPath $envFile) {
      $line = Select-String -LiteralPath $envFile -Pattern '^\s*NVIDIA_API_KEY\s*=' -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($line) {
        $env:NVIDIA_API_KEY = ($line.Line -replace '^\s*NVIDIA_API_KEY\s*=\s*', '').Trim().Trim('"')
        Write-Host "cloud tier enabled (NVIDIA_API_KEY loaded from $envFile)"
      }
    }
  }

  $out = Join-Path $LogDir "router.out.log"
  $err = Join-Path $LogDir "router.err.log"
  Start-Process -FilePath "py" -ArgumentList @($Script) -WindowStyle Hidden `
    -RedirectStandardOutput $out -RedirectStandardError $err

  if (-not (Wait-LocalPort -HostName $ListenHost -Port $Port -TimeoutSeconds ([Math]::Max($TimeoutSeconds, 15)))) {
    throw "router did not start on http://${ListenHost}:$Port. Check $err"
  }
  Write-Host "router started on http://${ListenHost}:$Port (model 'auto' -> hybrid routing)"
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if ($Restart) {
  # Stop only OUR processes: llama-swap + any llama-server under the repo (this
  # includes both the swap-managed instance on 9999 and the CPU classifier on
  # $ClassifierPort, which share build\bin\Release\llama-server.exe), and the
  # Python router. NEVER blanket-kill node/python.
  Get-Process llama-swap,llama-server -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith("D:\repos\ik_llama.cpp\", [System.StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force
  Get-CimInstance Win32_Process -Filter "Name='py.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "opencode-router\.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 1
}

# --- Ensure llama-swap (8292) is up ---------------------------------------
$swapUp = $false
if (Test-LocalPort -HostName $hostName -Port $port) {
  if (Test-LlamaSwapEndpoint -Listen $Listen) {
    Write-Host "llama-swap endpoint already responds on http://$Listen"
    $swapUp = $true
  } else {
    throw "Port $Listen is already open, but it is not a llama-swap OpenAI-compatible endpoint."
  }
}

if (-not $swapUp) {
  if (-not $Background -and -not $WithRouter) {
    # Foreground debug mode (no router): block on llama-swap.
    & $llamaSwap -config $Config -listen $Listen -watch-config
    return
  }

  $stdout = Join-Path $logDir "llama-swap.out.log"
  $stderr = Join-Path $logDir "llama-swap.err.log"
  $swapArgs = @("-config", $Config, "-listen", $Listen, "-watch-config")

  Start-Process -FilePath $llamaSwap `
    -ArgumentList $swapArgs `
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
}

# --- Ensure classifier (9998) + router (8291) -----------------------------
if ($WithRouter) {
  Start-Classifier -ListenHost $hostName -Port $ClassifierPort -Gguf $SmallGguf `
    -Exe $LlamaServer -Threads $ClassifierThreads -LogDir $logDir -TimeoutSeconds $TimeoutSeconds
  Start-Router -ListenHost $hostName -Port $RouterPort -Script $RouterScript `
    -LogDir $logDir -TimeoutSeconds $TimeoutSeconds

  Write-Host ""
  Write-Host "Stack ready:"
  Write-Host "  router      http://${hostName}:$RouterPort/v1   (point OpenCode here; model 'auto')"
  Write-Host "  llama-swap  http://$Listen/v1"
  Write-Host "  classifier  http://${hostName}:$ClassifierPort/v1"
}
