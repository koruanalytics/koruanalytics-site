param(
  [string]$OutZip = "..\2026_Peru_context.zip"
)

$ErrorActionPreference = "Stop"

# Root robusto: si $PSScriptRoot está vacío, usamos el directorio actual
if ($PSScriptRoot -and $PSScriptRoot.Trim().Length -gt 0) {
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
  $ProjectRoot = (Resolve-Path ".").Path
}

Set-Location $ProjectRoot

if (Test-Path $OutZip) { Remove-Item $OutZip -Force }

# Excluir cosas que dan problemas o pesan mucho
$excludeDirs = @(".venv", ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".vscode", "node_modules", "logs")
$excludeDirPatterns = $excludeDirs | ForEach-Object { "*\$_\*" }

$excludeFiles = @("*.pyc", "*.pyo", "*.pyd", "*.tmp", "*.lock")

# Si quieres excluir data pesada, descomenta:
# $excludeDirPatterns += "*\data\raw\*"
# $excludeDirPatterns += "*\data\interim\*"
# $excludeDirPatterns += "*\data\processed\*"
# $excludeDirPatterns += "*\data\osint_dw.duckdb"

Write-Host "Exporting from: $ProjectRoot"
Write-Host "To zip: $OutZip"

$items = Get-ChildItem -Path $ProjectRoot -Recurse -File |
  Where-Object {
    $full = $_.FullName
    ($excludeDirPatterns | Where-Object { $full -like $_ }).Count -eq 0
  } |
  Where-Object {
    $name = $_.Name
    ($excludeFiles | Where-Object { $name -like $_ }).Count -eq 0
  }

$items | Compress-Archive -DestinationPath $OutZip -Force

Write-Host "OK: created $OutZip"
