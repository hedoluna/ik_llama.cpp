$profileDir = Split-Path $PROFILE
New-Item -ItemType Directory -Force -Path $profileDir -ErrorAction SilentlyContinue | Out-Null

if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Force -Path $PROFILE -ErrorAction SilentlyContinue | Out-Null
}
Write-Host "File exists now? $(Test-Path $PROFILE)"

$line = "`n. 'D:\repos\ik_llama.cpp\scripts\pi-commands.ps1'"
try {
    Add-Content -Path $PROFILE -Value $line -ErrorAction Stop
    Write-Host "Installato: piup / pidown / pistatus disponibili nel prossimo terminale PowerShell"
} catch {
    Write-Host "ERRORE scrittura profilo: $($_.Exception.Message)"
    Write-Host "Fallback: aggiungi manualmente questa riga a $PROFILE :"
    Write-Host $line
}
