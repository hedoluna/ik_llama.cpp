$piLogDir = "D:\repos\ik_llama.cpp\scripts\logs"
if (-not (Test-Path $piLogDir)) { New-Item -ItemType Directory -Path $piLogDir -Force | Out-Null }

function piup {
    $exe = "D:\repos\ik_llama.cpp\build\bin\Release\llama-server.exe"
    $args = @(
        '--model', 'D:\repos\ik_llama.cpp\models\Qwen3.6-35B-A3B-IQ3_K_R4.gguf',
        '--host', '127.0.0.1',
        '--port', '8080',
        '--jinja',
        '--reasoning', 'off',
        '-ngl', '95',
        '--n-cpu-moe', '30',
        '-b', '2048',
        '-ub', '2048',
        '-ctk', 'q4_0',
        '-ctv', 'q8_0',
        '-fa', 'on',
        '-t', '8',
        '--no-mmap'
    )
    $p = Start-Process $exe -ArgumentList $args -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$piLogDir\daily_out.log" `
        -RedirectStandardError "$piLogDir\daily_err.log"
    Write-Host "Avvio daily-winner su :8080 (PID $($p.Id))... attendi ~10-20s prima di usare pi"
    Write-Host "Log: $piLogDir\daily_out.log / daily_err.log"
}

function pidown {
    Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "llama-server fermato"
}

function pistatus {
    $ok = $false
    for ($i = 0; $i -lt 3 -and -not $ok; $i++) {
        try {
            Invoke-WebRequest http://127.0.0.1:8080/health -UseBasicParsing -TimeoutSec 8 | Out-Null
            $ok = $true
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if ($ok) {
        Write-Host "UP - modello pronto su :8080"
    } else {
        Write-Host "DOWN - nessun server su :8080"
    }
}

# --- Modello uncensored (Opus-abliterated, score 96.4) su porta dedicata 8092 ---

function piuncup {
    $exe = "D:\repos\ik_llama.cpp\build\bin\Release\llama-server.exe"
    $args = @(
        '--model', 'D:\repos\ik_llama.cpp\models\Huihui-Qwen3.6-35B-A3B-Opus-abliterated-Q4_K.gguf',
        '--host', '127.0.0.1',
        '--port', '8092',
        '--jinja',
        '--reasoning', 'off',
        '--cpu-moe',
        '-ngl', '99',
        '-t', '12',
        '-c', '131072'
    )
    $p = Start-Process $exe -ArgumentList $args -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$piLogDir\unc_out.log" `
        -RedirectStandardError "$piLogDir\unc_err.log"
    Write-Host "Avvio Opus-abliterated (uncensored) su :8092, ctx 131072, PID $($p.Id)"
    Write-Host "Log: $piLogDir\unc_out.log / unc_err.log"
    Write-Host "Attendi ~20-40s, poi: piuncstatus"
}

function piuncdown {
    Get-CimInstance Win32_Process -Filter "Name = 'llama-server.exe'" |
        Where-Object { $_.CommandLine -match '8092' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Write-Host "llama-server (uncensored, :8092) fermato"
}

function piuncstatus {
    $ok = $false
    for ($i = 0; $i -lt 3 -and -not $ok; $i++) {
        try {
            Invoke-WebRequest http://127.0.0.1:8092/health -UseBasicParsing -TimeoutSec 8 | Out-Null
            $ok = $true
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if ($ok) {
        Write-Host "UP - uncensored pronto su :8092"
        return
    }
    Write-Host "DOWN - nessun server su :8092"
    $proc = Get-CimInstance Win32_Process -Filter "Name = 'llama-server.exe'" | Where-Object { $_.CommandLine -match '8092' }
    if ($proc) {
        Write-Host "  (processo attivo, PID $($proc.ProcessId) - probabilmente ancora in fase di caricamento modello o occupato con una richiesta)"
    } else {
        Write-Host "  (nessun processo llama-server per la porta 8092 - controlla i log:)"
        Write-Host "  Get-Content 'D:\repos\ik_llama.cpp\scripts\logs\unc_err.log' -Tail 40"
    }
}

# --- Switch rapido del defaultProvider/defaultModel di pi tra daily-winner e uncensored ---

function pi-switch {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("daily", "uncensored")]
        [string]$Target
    )

    $settingsPath = "$env:USERPROFILE\.pi\agent\settings.json"
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json

    if ($Target -eq "uncensored") {
        $settings.defaultProvider = "local-uncensored"
        $settings.defaultModel = "models/Huihui-Qwen3.6-35B-A3B-Opus-abliterated-Q4_K.gguf"
        Write-Host "pi -> uncensored (Opus-abliterated, :8092). Assicurati che il server sia su: piuncup"
    } else {
        $settings.defaultProvider = "local"
        $settings.defaultModel = "models/Qwen3.6-35B-A3B-IQ3_K_R4.gguf"
        Write-Host "pi -> daily-winner (:8080). Assicurati che il server sia su: piup"
    }

    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
}
