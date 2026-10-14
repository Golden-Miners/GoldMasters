# Run Procedure (D-33: one entry point per surface)

Startup order: gate → stack (database + backend) → client.

## 1. Quality gate

```sh
sh scripts/gate          # full ordered gate (Git for Windows `sh` runs it here)
sh scripts/gate --fast   # commit subset: changed-file format/lint/mypy + security tests
```

Enable the pre-commit hook once (local only):

```sh
git config core.hooksPath .githooks
```

Green means: format clean → lint clean → `mypy --strict` clean → full pytest green
(contracts, boundary scan, unit, integration incl. throwaway-database tests).

## 2. Local stack (database + backend, loopback only)

```sh
sh scripts/stack          # provision/init if needed, start DB, launch the API
sh scripts/stack --stop  # stop the backend and the database
```

What you should see:

- `STEP provision ok` — pinned EDB archive verified against `artifact.lock`.
- `STEP init ok` — cluster initialised with `scram-sha-256` auth (or already initialised).
- `STEP start ok (listening on 127.0.0.1:5432)` — loopback only, never `0.0.0.0`.
- `Uvicorn running on http://127.0.0.1:8000` — the API leg passes `--host 127.0.0.1` explicitly.
- `GET http://127.0.0.1:8000/health` answers the five chain fields
  (`status`, `version`, `contract_schema_version`, `config_hash`, `database.reachable`).

The working database is `goldmasters`; the suite uses throwaway
`goldmasters_test_*` databases and never touches it. The local `.env`
(git-ignored, built from the cluster password file) supplies
`GOLDMASTERS_DATABASE_URL` on this machine.

## 3. Client (loopback health page)

```sh
npm --prefix apps/web run gen:types   # regenerate TS types from committed schemas
npm --prefix apps/web run dev         # serves http://127.0.0.1:3000
```

Open `http://127.0.0.1:3000`: the five chain fields, or an explicit
`API unavailable` state when the backend is down — never a fabricated value.
`npm --prefix apps/web run typecheck` must stay clean.
