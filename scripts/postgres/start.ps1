#Requires -Version 5.1
<#
.SYNOPSIS
  Start the repo-local cluster on loopback only.
#>
[CmdletBinding()]
param(
  [switch]$Wait
)

$ErrorActionPreference = 'Stop'

$PostgresDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'vendor/postgres'
$BinDir = Join-Path $PostgresDir 'pgsql/bin'
$DataDir = Join-Path $PostgresDir 'data'
$LogFile = Join-Path $PostgresDir 'server.log'

& (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir status 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
  Write-Host 'STEP start ok (already running on 127.0.0.1:5432)'
  exit 0
}

& (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir -o '-p 5432 -h 127.0.0.1' -l $LogFile start
if ($LASTEXITCODE -ne 0) { throw "pg_ctl start failed (exit $LASTEXITCODE)." }

$deadline = (Get-Date).AddSeconds(30)
while ($true) {
  $ready = & (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir status 2>$null
  if ($LASTEXITCODE -eq 0) { break }
  if ((Get-Date) -gt $deadline) { throw 'Server did not become ready within 30s.' }
  Start-Sleep -Seconds 1
}
Write-Host 'STEP start ok (listening on 127.0.0.1:5432)'
