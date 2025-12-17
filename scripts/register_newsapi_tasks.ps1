param(
  [string]$ProjectRoot = "",
  [string]$ScopeYaml = "",
  [int]$LookbackDays = 1,
  [int]$MaxItems = 20,
  [switch]$AllowArchive
)

$ErrorActionPreference = "Stop"

# Default: project root = carpeta padre de /scripts
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

# Default: scope yaml del proyecto
if ([string]::IsNullOrWhiteSpace($ScopeYaml)) {
  $ScopeYaml = Join-Path $ProjectRoot "config\newsapi_scope_peru_2025-11.yaml"
}

# PowerShell de sistema (evita depender del PATH)
$ps = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

# Construimos un comando interno que llama al wrapper con rutas ABSOLUTAS.
# Ojo: lo codificamos en Base64 (EncodedCommand) para evitar problemas con espacios.
$allow = ""
if ($AllowArchive) { $allow = " -AllowArchive" }

$inner = @"
& '$ProjectRoot\scripts\scheduled_run_newsapi_ai_job.ps1' -ScopePath '$ScopeYaml' -LookbackDays $LookbackDays -MaxItems $MaxItems$allow
"@

# EncodedCommand requiere UTF-16LE
$bytes = [System.Text.Encoding]::Unicode.GetBytes($inner)
$encoded = [Convert]::ToBase64String($bytes)

$arg = "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded"

# Limpieza de tareas previas (si existían)
if (Get-ScheduledTask -TaskName "OSINT-NewsAPI-Morning" -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName "OSINT-NewsAPI-Morning" -Confirm:$false
}
if (Get-ScheduledTask -TaskName "OSINT-NewsAPI-Evening" -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName "OSINT-NewsAPI-Evening" -Confirm:$false
}

# Settings recomendados
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Acción y triggers
$action = New-ScheduledTaskAction -Execute $ps -Argument $arg

$triggerMorning = New-ScheduledTaskTrigger -Daily -At 07:15
Register-ScheduledTask -TaskName "OSINT-NewsAPI-Morning" -Action $action -Trigger $triggerMorning -Settings $settings -Force

$triggerEvening = New-ScheduledTaskTrigger -Daily -At 19:15
Register-ScheduledTask -TaskName "OSINT-NewsAPI-Evening" -Action $action -Trigger $triggerEvening -Settings $settings -Force

Write-Host "OK: tareas creadas/actualizadas."
Write-Host "  - OSINT-NewsAPI-Morning (07:15)"
Write-Host "  - OSINT-NewsAPI-Evening (19:15)"
Write-Host ""
Write-Host "Comando interno (debug):"
Write-Host $inner
