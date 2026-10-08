# Stop local PostgreSQL server
$ErrorActionPreference = "SilentlyContinue"

$PgBin = "C:\Program Files\PostgreSQL\17\bin"
$DataDir = Join-Path $PSScriptRoot "..\pgdata"

if (Test-Path "$PgBin\pg_ctl.exe") {
    & "$PgBin\pg_ctl.exe" -D "$DataDir" stop
} else {
    Get-Process -Name postgres -ErrorAction SilentlyContinue | Stop-Process -Force
}

Write-Host "PostgreSQL stopped."
