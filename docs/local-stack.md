# Local Stack Evidence (01-05 Task 2)

Falsification probe run on this machine, 2026-10-14: `pwsh -NoProfile -File scripts/postgres/probe.ps1`.

## Observed output (abridged)

- `STEP provision ok (downloaded, sha256=e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2)`
- `STEP init ok` (initdb completed, locale `C`, no UAC prompt, no elevation)
- `STEP start ok (listening on 127.0.0.1:5432)`
- `STEP connect ok (PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35229, 64-bit)`
- `STEP query ok (SELECT 1 = 1)`
- `STEP stop ok`, `STEP probe ok`

## Resolved pin and URL

- Pin in `scripts/postgres/VERSION`: `18.6` (the preferred pin ran; no fallback needed).
- Resolved URL: `https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609`
- sha256: `e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2` (recorded in `vendor/postgres/artifact.lock`, re-verified on every run)

## Assumption verdicts

- **A2 (EDB binaries run on this Windows 10 machine): YES.** Observed `PostgreSQL 18.6 on x86_64-windows` from the bundled `psql.exe`.
- **A3 (`initdb`/`pg_ctl` need no elevation): YES.** Ran as a normal user with no UAC prompt.
- **A4 (URL/hash stable enough): OBSERVED.** The resolved URL and hash above are recorded; the script aborts on mismatch.
- **A7 (pin): `18.6`.** The conservative alternate `17.11` (fileid `1260616`) was not needed.

## Reproducible procedure

```powershell
pwsh -NoProfile -File scripts/postgres/provision.ps1
pwsh -NoProfile -File scripts/postgres/init.ps1
pwsh -NoProfile -File scripts/postgres/start.ps1
sh scripts/stack            # database + backend together on loopback
sh scripts/stack --stop
```

The cluster lives in `vendor/postgres/` (binaries, lock, data, password file — all git-ignored), listens on `127.0.0.1:5432`, and uses `scram-sha-256` auth, never `trust`.
