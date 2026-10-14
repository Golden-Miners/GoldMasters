#Requires -Version 5.1
<#
.SYNOPSIS
  Stop the repo-local cluster (fast, with immediate fallback).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$PostgresDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'vendor/postgres'
$BinDir = Join-Path $PostgresDir 'pgsql/bin'
$DataDir = Join-Path $PostgresDir 'data'

& (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir stop -m fast
if ($LASTEXITCODE -ne 0) {
  & (Join-Path $BinDir 'pg_ctl.exe') -D $DataDir stop -m immediate
  if ($LASTEXITCODE -ne 0) { throw "pg_ctl stop failed (exit $LASTEXITCODE)." }
}
Write-Host 'STEP stop ok'
