# Start local PostgreSQL server
$ErrorActionPreference = "Stop"

$PgBin = "C:\Program Files\PostgreSQL\17\bin"
$DataDir = Join-Path $PSScriptRoot "..\pgdata"

if (-not (Test-Path $DataDir)) {
    Write-Host "Data directory not found. Running init_postgres.ps1 first..."
    & "$PSScriptRoot\init_postgres.ps1"
}

Write-Host "Starting PostgreSQL server on port 5432..."
Start-Process -FilePath "$PgBin\postgres.exe" -ArgumentList "-D `"$DataDir`"" -WindowStyle Hidden

Start-Sleep -Seconds 2
& "$PgBin\pg_isready.exe" -h 127.0.0.1 -p 5432 -U traceiq
if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL is running and accepting connections."
} else {
    Write-Warning "PostgreSQL server start check returned code $LASTEXITCODE"
}
