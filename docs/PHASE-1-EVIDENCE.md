# Phase 1 Evidence — Contracts and Foundation

Goal: a frozen, machine-checked contract layer and a running, observable
local skeleton, with the research-only boundary enforced structurally.

## Criterion 1 — Contract layer as validated versioned code

- `uv run pytest packages/contracts/tests -q` → green (incl. purity gate,
  drift gate, per-contract invariant tests).
- `uv run pytest tests/contract -q` → **59 passed**: Schema.md's two JSON
  examples validate verbatim (explicit placeholder substitutions), 10
  contracts hold accepted cases and ~45 rejected mutations across every D-06
  class plus named invariants (OHLC, manual-review, quality-omitted,
  unknown-major, wrong-prefix id, display-name provider, score bounds).
- `uv run python packages/contracts/_export_schema.py` regenerates
  `packages/contracts/schema/*.json` byte-identical (10 documents); decimals
  and timestamps export as flat `type: string` (only the documented float
  sentiment score is a JSON number).
- An invalid payload is rejected, never accepted (strict/forbid/frozen base).

## Criterion 2 — Backend + client skeleton on loopback

- `GET http://127.0.0.1:8000/health` → 200 with all five chain fields
  (`status`, `version`, `contract_schema_version`, `config_hash`,
  `database.reachable`) — observed live 2026-10-14.
- `http://127.0.0.1:3001/` (production `next start -H 127.0.0.1`) rendered
  all five values from the live backend (`ok / 0.1.0 / 1.0 / 9ca11c… / no`);
  with the backend down the page renders an explicit unavailable state.
- `npm --prefix apps/web run typecheck` clean; `next build` succeeds.
- Client types come from `npm run gen:types` (json2ts over the committed
  schemas into git-ignored `src/generated/`); failure bodies use the
  generated C-09 `ErrorPayload`.

## Criterion 3 — Research-only boundary, structurally enforced

- `uv run pytest tests/security -q` → green: AST scan finds no forbidden
  broker/order call or import; every declared dependency is allowlisted and
  none is order-capable; negative meta-tests prove the scan has teeth.
- No order-placement/modification/closure module, endpoint, tool or
  broker-trading credential exists — the scan would fail the build otherwise.

## Criterion 4 — Validated config, secret-free example, redacted observables

- Missing/invalid `GOLDMASTERS_*` key stops startup naming the key;
  unknown prefixed variables rejected; secrets are `SecretStr` and absent
  from repr/dump; `.env.example` covers every key with secrets empty;
  `config/goldmasters.yaml` carries only non-secret defaults as the
  lowest-priority source.
- Config hash deterministic, order-invariant, secret-excluding by field type,
  versioned (`HASH_ALGORITHM_VERSION`).
- Rendered logs are JSON with `correlation_id`, secrets redacted
  (nested-aware); per-request server-minted IDs echoed in `X-Correlation-ID`
  (forged headers rejected); spans append to repo-local `logs/traces.jsonl`.

## Criterion 5 — Migration applies/rolls back; evidence recorded

- `alembic upgrade head → downgrade base → upgrade head`: table + 4 indexes
  appear, vanish (minus Alembic bookkeeping), reappear — observed live.
- Throwaway `goldmasters_test_*` databases per run (created + dropped);
  all 10 accepted payloads round-trip byte-equal with decimals as strings
  and promoted columns populated.
- `docs/local-stack.md`: probe evidence — PostgreSQL 18.6
  (`sbp.enterprisedb.com/getfile.jsp?fileid=1260609`,
  sha256 `e2246ba9…c84e2`), runs on this machine, no elevation,
  `SELECT 1 = 1`. One transient Windows shared-memory fork failure (error
  487) observed mid-phase; cleared by restart.

## Phase-level green

- `sh scripts/gate` → `gate: PASS` (format clean, lint clean,
  `mypy --strict` clean, full pytest green — 200+ tests).
- `sh scripts/gate --fast` → `gate --fast: PASS`.

## CI — honest statement

This machine has no git remote and no CI provider; Docker is absent so
`nektos/act` is not viable. Criteria 3 and 5 are satisfied *structurally* by
the recorded build-failing local runner plus the tracked pre-commit hook.
Hosted-CI *execution* is pending a remote and is **NOT** claimed as done.
No workflow file is invented.

## Open assumptions (recorded, not invented)

Boundary thresholds, the rounding contract, and concurrency/interruption
semantics remain unspecified per the phase plans' FLAGGED ASSUMPTIONS.
