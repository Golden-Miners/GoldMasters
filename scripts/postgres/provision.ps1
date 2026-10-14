#Requires -Version 5.1
<#
.SYNOPSIS
  Download the pinned EDB no-installer PostgreSQL archive into vendor/postgres.
.DESCRIPTION
  Reads scripts/postgres/VERSION, downloads the matching EDB binaries archive
  (verified file IDs, see docs/local-stack.md), records the resolved URL and
  sha256 in vendor/postgres/artifact.lock, and extracts it so that
  vendor/postgres/pgsql/bin/initdb.exe exists. Re-verifies the hash against
  the lock on every later run and aborts on mismatch. Nothing is installed
  outside vendor/postgres and no Windows service is registered (D-29).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PostgresDir = Join-Path $Root 'vendor/postgres'
$Version = (Get-Content (Join-Path $PSScriptRoot 'VERSION') -Raw).Trim()

# Verified EDB no-installer archive IDs (docs/local-stack.md, D-29).
$FileIds = @{
  '18.6'  = '1260609'
  '17.11' = '1260616'
}

if (-not $FileIds.ContainsKey($Version)) {
  throw "No verified EDB file ID for PostgreSQL $Version (VERSION). Refusing to guess a URL."
}

$Url = "https://sbp.enterprisedb.com/getfile.jsp?fileid=$($FileIds[$Version])"
$ZipPath = Join-Path $PostgresDir 'pgsql.zip'
$LockPath = Join-Path $PostgresDir 'artifact.lock'
$BinDir = Join-Path $PostgresDir 'pgsql/bin'

New-Item -ItemType Directory -Force -Path $PostgresDir | Out-Null

function Get-Sha256([string]$Path) {
  return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

if ((Test-Path $ZipPath) -and (Test-Path $LockPath)) {
  $recorded = @{}
  foreach ($line in Get-Content $LockPath) {
    $k, $v = $line -split '=', 2
    $recorded[$k.Trim()] = $v.Trim()
  }
  if ($recorded['url'] -ne $Url) {
    throw "artifact.lock URL ($($recorded['url'])) differs from resolved URL ($Url). Delete vendor/postgres to re-provision deliberately."
  }
  $actual = Get-Sha256 $ZipPath
  if ($actual -ne $recorded['sha256']) {
    throw "pgsql.zip sha256 $actual differs from recorded $($recorded['sha256']). Possible swapped artifact -- aborting."
  }
  Write-Host "STEP provision ok (cached, hash verified)"
} else {
  Write-Host "Downloading $Url ..."
  Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
  $hash = Get-Sha256 $ZipPath
  "url=$Url" | Set-Content $LockPath
  "sha256=$hash" | Add-Content $LockPath
  Write-Host "STEP provision ok (downloaded, sha256=$hash)"
}

if (-not (Test-Path (Join-Path $BinDir 'initdb.exe'))) {
  Expand-Archive -Path $ZipPath -DestinationPath $PostgresDir -Force
}

foreach ($exe in @('initdb.exe', 'pg_ctl.exe', 'psql.exe')) {
  if (-not (Test-Path (Join-Path $BinDir $exe))) {
    throw "Expected $(Join-Path $BinDir $exe) after extraction."
  }
}
Write-Host "STEP provision ok"
