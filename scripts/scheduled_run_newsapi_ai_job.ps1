param(
  [string]$ScopePath = "config/newsapi_scope_peru_2025-11.yaml",
  [int]$LookbackDays = 1,
  [int]$MaxItems = 20,
  [switch]$AllowArchive
)

$ErrorActionPreference = "Stop"

# 1) resolver rutas
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
  Write-Host "ERROR: No existe $PythonExe. ¿Está creada la .venv?" -ForegroundColor Red
  exit 10
}

# 2) logs
$NewsLogDir = Join-Path $ProjectRoot "logs\newsapi_ai"
$OpsLogDir  = Join-Path $ProjectRoot "logs\ops"
New-Item -ItemType Directory -Force -Path $NewsLogDir | Out-Null
New-Item -ItemType Directory -Force -Path $OpsLogDir  | Out-Null

$Stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")

$LogFile = Join-Path $NewsLogDir "job_$Stamp.log"
$StdOutFile = Join-Path $NewsLogDir "job_$Stamp.stdout.log"
$StdErrFile = Join-Path $NewsLogDir "job_$Stamp.stderr.log"

$IncLogFile = Join-Path $OpsLogDir "incidents_$Stamp.log"
$IncStdOutFile = Join-Path $OpsLogDir "incidents_$Stamp.stdout.log"
$IncStdErrFile = Join-Path $OpsLogDir "incidents_$Stamp.stderr.log"

# 3) lock para evitar solapes
$LockDir = Join-Path $ProjectRoot "logs\locks"
New-Item -ItemType Directory -Force -Path $LockDir | Out-Null
$LockFile = Join-Path $LockDir "newsapi_ai_job.lock"

$LockTtlMinutes = 120
if (Test-Path $LockFile) {
  $age = (Get-Date) - (Get-Item $LockFile).LastWriteTime
  if ($age.TotalMinutes -lt $LockTtlMinutes) {
    $msg = "LOCK activo (edad: {0:N1} min). Se evita solape. Saliendo." -f $age.TotalMinutes
    $msg | Tee-Object -FilePath $LogFile -Append
    exit 0
  } else {
    "LOCK viejo (>TTL). Lo sobrescribo." | Tee-Object -FilePath $LogFile -Append
  }
}

"PID=$PID; START=$(Get-Date -Format o)" | Out-File -FilePath $LockFile -Encoding utf8

try {
  # 4) rango dinámico (granularidad día)
  $DateEnd = (Get-Date).ToString("yyyy-MM-dd")
  $DateStart = (Get-Date).AddDays(-1 * $LookbackDays).ToString("yyyy-MM-dd")

  # -------------------------------------------------------------------
  # 4.5) PRE-FLIGHT (opcional): validar checksum del gazetteer
  # -------------------------------------------------------------------
  $GazChecksumScript = Join-Path $ProjectRoot "scripts\validate_gazetteer_checksum.py"
  if (Test-Path $GazChecksumScript) {
    "=== PRE-FLIGHT GEO CHECKSUM ===" | Tee-Object -FilePath $LogFile -Append
    "cmd: $PythonExe scripts/validate_gazetteer_checksum.py" | Tee-Object -FilePath $LogFile -Append

    $preOut = Join-Path $NewsLogDir "pre_$Stamp.stdout.log"
    $preErr = Join-Path $NewsLogDir "pre_$Stamp.stderr.log"

    $p0 = Start-Process -FilePath $PythonExe `
                        -ArgumentList @("scripts/validate_gazetteer_checksum.py") `
                        -NoNewWindow -Wait -PassThru `
                        -RedirectStandardOutput $preOut `
                        -RedirectStandardError $preErr

    if (Test-Path $preOut) { Get-Content $preOut | Tee-Object -FilePath $LogFile -Append }
    if (Test-Path $preErr) { Get-Content $preErr | Tee-Object -FilePath $LogFile -Append }

    if ($p0.ExitCode -ne 0) {
      "PRE-FLIGHT FAIL EXIT_CODE=$($p0.ExitCode)" | Tee-Object -FilePath $LogFile -Append
      exit $p0.ExitCode
    }
  } else {
    "=== PRE-FLIGHT GEO CHECKSUM (SKIP: script not found) ===" | Tee-Object -FilePath $LogFile -Append
  }

  # 5) args (exe separado de args)
  $ArgsList = @(
    "scripts/run_newsapi_ai_job.py",
    "--scope", $ScopePath,
    "--max-items", "$MaxItems",
    "--date-start", $DateStart,
    "--date-end", $DateEnd
  )
  if ($AllowArchive) { $ArgsList += "--allow-archive" }

  "=== RUN NEWSAPI ===" | Tee-Object -FilePath $LogFile -Append
  "cwd=$ProjectRoot" | Tee-Object -FilePath $LogFile -Append
  "python=$PythonExe" | Tee-Object -FilePath $LogFile -Append
  "scope=$ScopePath" | Tee-Object -FilePath $LogFile -Append
  "date_start=$DateStart date_end=$DateEnd max_items=$MaxItems allow_archive=$AllowArchive" | Tee-Object -FilePath $LogFile -Append
  "cmd: $PythonExe $($ArgsList -join ' ')" | Tee-Object -FilePath $LogFile -Append
  "" | Tee-Object -FilePath $LogFile -Append

  # 6) Ejecutar sin crear NativeCommandError: redirecciones nativas
  $p = Start-Process -FilePath $PythonExe `
                     -ArgumentList $ArgsList `
                     -NoNewWindow -Wait -PassThru `
                     -RedirectStandardOutput $StdOutFile `
                     -RedirectStandardError $StdErrFile

  # 7) Volcar stdout+stderr al log principal
  if (Test-Path $StdOutFile) { Get-Content $StdOutFile | Tee-Object -FilePath $LogFile -Append }
  if (Test-Path $StdErrFile) { Get-Content $StdErrFile | Tee-Object -FilePath $LogFile -Append }

  $ExitCode = $p.ExitCode
  "EXIT_CODE=$ExitCode" | Tee-Object -FilePath $LogFile -Append

  if ($ExitCode -ne 0) {
    exit $ExitCode
  }

  # -------------------------------------------------------------------
  # 8) Extraer RUN_ID=... del stdout (para encadenar incidentes)
  # -------------------------------------------------------------------
  $RunIdLine = $null
  if (Test-Path $StdOutFile) {
    $RunIdLine = Select-String -Path $StdOutFile -Pattern "^RUN_ID=" | Select-Object -Last 1
  }

  if (-not $RunIdLine) {
    "ERROR: RUN_ID no encontrado en stdout ($StdOutFile). No se lanza incidents job." | Tee-Object -FilePath $LogFile -Append
    exit 20
  }

  $RunId = ($RunIdLine.Line -replace "^RUN_ID=", "").Trim()
  "RUN_ID=$RunId" | Tee-Object -FilePath $LogFile -Append

  # -------------------------------------------------------------------
  # 9) Ejecutar Incidents job con el RUN_ID
  # -------------------------------------------------------------------
  $IncScript = Join-Path $ProjectRoot "scripts\run_incidents_job.py"
  if (!(Test-Path $IncScript)) {
    "ERROR: No existe scripts/run_incidents_job.py. No se lanza incidents job." | Tee-Object -FilePath $LogFile -Append
    exit 21
  }

  "=== RUN INCIDENTS ===" | Tee-Object -FilePath $IncLogFile -Append
  "run_id=$RunId" | Tee-Object -FilePath $IncLogFile -Append
  "cmd: $PythonExe scripts/run_incidents_job.py --run-id $RunId" | Tee-Object -FilePath $IncLogFile -Append
  "" | Tee-Object -FilePath $IncLogFile -Append

  $IncArgsList = @(
    "scripts/run_incidents_job.py",
    "--run-id", $RunId
  )

  $p2 = Start-Process -FilePath $PythonExe `
                      -ArgumentList $IncArgsList `
                      -NoNewWindow -Wait -PassThru `
                      -RedirectStandardOutput $IncStdOutFile `
                      -RedirectStandardError $IncStdErrFile

  if (Test-Path $IncStdOutFile) { Get-Content $IncStdOutFile | Tee-Object -FilePath $IncLogFile -Append }
  if (Test-Path $IncStdErrFile) { Get-Content $IncStdErrFile | Tee-Object -FilePath $IncLogFile -Append }

  $IncExit = $p2.ExitCode
  "EXIT_CODE=$IncExit" | Tee-Object -FilePath $IncLogFile -Append

  if ($IncExit -ne 0) {
    exit $IncExit
  }

  exit 0
}
finally {
  if (Test-Path $LockFile) {
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
  }
}
