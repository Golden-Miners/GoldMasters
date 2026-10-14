#Requires -Version 5.1
<#
.SYNOPSIS
  Falsification probe: provision → init → start → query → stop, for real.
.DESCRIPTION
  Prints one machine-readable STEP line per stage and fails loudly naming the
  exact step on error. Never falls back to a machine-wide install. Its output
  is the evidence recorded in docs/local-stack.md (A2/A3/A4/A7).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$ScriptsDir = $PSScriptRoot
$PostgresDir = Join-Path (Split-Path -Parent $ScriptsDir) '..' 'vendor/postgres'
$PostgresDir = [System.IO.Path]::GetFullPath($PostgresDir)
$BinDir = Join-Path $PostgresDir 'pgsql/bin'

function Step([string]$Name, [scriptblock]$Body) {
  try {
    & $Body
    Write-Host "STEP $Name ok"
  } catch {
    Write-Host "STEP $Name FAILED: $($_.Exception.Message)"
    throw
  }
}

Step 'provision' { & (Join-Path $ScriptsDir 'provision.ps1') }
Step 'init' { & (Join-Path $ScriptsDir 'init.ps1') }
Step 'start' { & (Join-Path $ScriptsDir 'start.ps1') }

$env:PGPASSWORD = (Get-Content (Join-Path $PostgresDir 'goldmasters.pwfile') -Raw).Trim()

try {
  $version = & (Join-Path $BinDir 'psql.exe') -h 127.0.0.1 -p 5432 -U goldmasters -d postgres -tAc 'SELECT version();'
  if ($LASTEXITCODE -ne 0) { throw 'psql version query failed.' }
  Write-Host "STEP connect ok ($version)"
  $one = & (Join-Path $BinDir 'psql.exe') -h 127.0.0.1 -p 5432 -U goldmasters -d postgres -tAc 'SELECT 1;'
  if ($LASTEXITCODE -ne 0 -or $one.Trim() -ne '1') { throw 'SELECT 1 did not return 1.' }
  Write-Host 'STEP query ok (SELECT 1 = 1)'
} finally {
  Step 'stop' { & (Join-Path $ScriptsDir 'stop.ps1') }
}
Write-Host 'STEP probe ok'
