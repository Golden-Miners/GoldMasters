#Requires -Version 5.1
<#
.SYNOPSIS
  Initialise the repo-local PostgreSQL cluster (explicit auth, never trust).
.DESCRIPTION
  Runs the bundled initdb.exe with --auth=scram-sha-256 and --pwfile (Pitfall 6)
  into vendor/postgres/data. Idempotent: an existing cluster is left alone.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$PostgresDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'vendor/postgres'
$BinDir = Join-Path $PostgresDir 'pgsql/bin'
$DataDir = Join-Path $PostgresDir 'data'
$PwFile = Join-Path $PostgresDir 'goldmasters.pwfile'

if (Test-Path (Join-Path $DataDir 'PG_VERSION')) {
  Write-Host 'STEP init ok (cluster already initialised)'
  exit 0
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes) | Set-Content -NoNewline $PwFile

& (Join-Path $BinDir 'initdb.exe') -D $DataDir -U goldmasters --auth=scram-sha-256 --pwfile=$PwFile -E UTF8 --locale=C
if ($LASTEXITCODE -ne 0) { throw "initdb failed (exit $LASTEXITCODE)." }

# The working database the API and the test suite derive their URLs from.
# Idempotent: created once, left alone afterwards.
$env:PGPASSWORD = (Get-Content $PwFile -Raw).Trim()
& (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir -o '-p 5432 -h 127.0.0.1' -l (Join-Path (Split-Path -Parent $DataDir) 'server.log') start
if ($LASTEXITCODE -ne 0) { throw "temporary start for createdb failed (exit $LASTEXITCODE)." }
try {
  $exists = & (Join-Path $BinDir 'psql.exe') -h 127.0.0.1 -p 5432 -U goldmasters -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='goldmasters';"
  if ($LASTEXITCODE -ne 0) { throw 'database check failed.' }
  if ($exists.Trim() -ne '1') {
    & (Join-Path $BinDir 'createdb.exe') -h 127.0.0.1 -p 5432 -U goldmasters goldmasters
    if ($LASTEXITCODE -ne 0) { throw "createdb failed (exit $LASTEXITCODE)." }
  }
} finally {
  & (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir stop -m fast | Out-Null
}
Write-Host 'STEP init ok'
