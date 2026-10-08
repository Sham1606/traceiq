# Initialize local PostgreSQL cluster and create traceiq databases
$ErrorActionPreference = "Stop"

$PgBin = "C:\Program Files\PostgreSQL\17\bin"
if (-not (Test-Path $PgBin)) {
    Write-Error "PostgreSQL 17 bin directory not found at $PgBin. Please adjust path or use docker-compose up -d."
}

$DataDir = Join-Path $PSScriptRoot "..\pgdata"
if (-not (Test-Path $DataDir)) {
    Write-Host "Initializing PostgreSQL cluster in $DataDir..."
    & "$PgBin\initdb.exe" -D "$DataDir" -U traceiq --auth-local=trust --auth-host=trust --encoding=UTF8
} else {
    Write-Host "PostgreSQL data directory already exists at $DataDir."
}

Write-Host "Done. Start PostgreSQL with scripts/start_postgres.ps1"
