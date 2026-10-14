---
phase: 01-contracts-and-foundation
plan: "08"
subsystem: api-skeleton
tags: [python, fastapi, pydantic-settings, json-schema, loopback, health, uv]

# Dependency graph
requires: [01 (contracts core + envelope)]
provides:
  - "`packages/contracts/_export_schema.py` + committed `schema/envelope.json` (serialization mode, canonicalised)"
  - "`goldmasters-api` distribution in the uv workspace with pinned deps"
  - "`Settings` (GOLDMASTERS_ prefix, forbid extras, frozen) + `hash_effective_config` (sha256 over non-secrets)"
  - "`create_app`/`lifespan` (settings resolved once) + `assert_loopback` (D-34)"
  - "`GET /health` five-field chain surface + bounded quiet `probe_database`"
  - "`tests/integration/test_health.py` (9 tests: surface, loopback, independence, probe)"
affects: [09 (logging/tracing call site in lifespan), 10 (settings field set + hash hardening), 04 (drift test byte-compares envelope.json)]

actuals:
  tokens: 0
  tasks: 3
  commits: 4
  plan_head_before: 11f74a0
  plan_head_after: 8d78ca1

tech-stack:
  added: ["fastapi==0.143.0", "uvicorn==0.54.0", "pydantic-settings==2.15.0", "structlog==26.1.0", "opentelemetry-sdk==1.45.1", "opentelemetry-api==1.45.1", "pyyaml==6.0.3", "sqlalchemy==2.1.4", "psycopg[binary]==3.3.6", "httpx==0.28.1"]
  patterns:
    - "Health proves the chain: every field read from app state set up in lifespan, nothing hard-coded"
    - "Probe failures are values (`reachable: false`), never exceptions and never URL fragments"
    - "Export imports only from the contracts package — the committed schema cannot acquire an HTTP dependency"

key-files:
  created:
    - packages/contracts/_export_schema.py
    - packages/contracts/schema/envelope.json
    - apps/api/pyproject.toml
    - apps/api/src/goldmasters_api/__init__.py
    - apps/api/src/goldmasters_api/settings.py
    - apps/api/src/goldmasters_api/app.py
    - apps/api/src/goldmasters_api/health.py
    - tests/integration/test_health.py
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "`database_url` defaults to an unreachable localhost URL (no secret) so the skeleton answers `reachable: false` on a machine with no PostgreSQL instead of failing startup."
  - "`assert_loopback` resolves the `localhost` name and checks every result — a name resolving to a non-loopback address is refused."
  - "`httpx==0.28.1` added beyond the plan's dep list: FastAPI's TestClient requires it, and the plan's verify step mandates a test client."

patterns-established:
  - "`CONTRACTS` data constant enumerates the export set; plan 11 appends rows, never restructures the writer."
  - "One integration test file answers 'does the skeleton bind safely and answer correctly' for all three tasks."

requirements-completed: [REQ-no-trade-execution]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Committed `schema/envelope.json` is byte-identical to a fresh serialization-mode export; decimal fields are flat string types."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "uv run python packages/contracts/_export_schema.py && git diff --exit-code packages/contracts/schema/envelope.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "`GET /health` returns 200 with `status`, `version`, `contract_schema_version`, `config_hash` and boolean `database.reachable`."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_health.py#test_health_returns_five_chain_fields"
        status: pass
    human_judgment: false
  - id: D3
    description: "Loopback guard accepts `127.0.0.1`/`::1`/`localhost`, refuses `0.0.0.0`/LAN/`::` naming the host, and fails startup instead of serving."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_health.py#test_loopback_guard_refuses_non_loopback"
        status: pass
    human_judgment: false
  - id: D4
    description: "Skeleton imports no terminal/model-runtime module; answers with both absent; unreachable DB yields `reachable: false` within the bound leaking no URL fragment."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_health.py#test_probe_is_bounded_on_black_holed_address"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 08: API Spine Tracer Summary

**End-to-end contract envelope → committed JSON Schema → loopback-only FastAPI skeleton answering a five-field chain-proof `/health` — with MT5 and Ollama absent.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-10-14
- **Tasks:** 3
- **Files modified:** 8 created, 2 modified

## Accomplishments

- Export entry point + committed `schema/envelope.json` (serialization mode, canonical JSON); `schema_version` exports as flat `type: string`.
- `goldmasters-api` workspace member with pinned deps; `uv sync --all-packages` green.
- `Settings` + `hash_effective_config`; `lifespan` resolves once; `assert_loopback`; `/health` five fields from app state; bounded quiet probe.
- 9 integration tests green; full suite **86 passed**; `mypy --strict` clean (15 files); `ruff check` + `format` clean on all new files.

## Task Commits

1. **Task 1: Envelope → schema → loopback /health tracer** - `73516a1` (feat)
2. **Task 2: Loopback guard acceptance + refusal** - `d77fdaa` (test)
3. **Task 3: Runtime independence + DB probe** - `ed8329f` (test)
4. **Strict/lint follow-up** - fix commit (this run)

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Files Created/Modified

- `packages/contracts/_export_schema.py` - serialization-mode exporter, `CONTRACTS` constant
- `packages/contracts/schema/envelope.json` - committed envelope schema
- `apps/api/pyproject.toml` - `goldmasters-api` manifest, workspace source wiring
- `apps/api/src/goldmasters_api/__init__.py` - `__version__`
- `apps/api/src/goldmasters_api/settings.py` - `Settings`, `hash_effective_config`
- `apps/api/src/goldmasters_api/app.py` - `create_app`, `lifespan`, `assert_loopback`
- `apps/api/src/goldmasters_api/health.py` - `/health`, `probe_database`
- `tests/integration/test_health.py` - 9 tests across the three tasks
- `pyproject.toml` - workspace members += `apps/api`
- `uv.lock` - resolved API dependencies

## Decisions Made

- Same three as key-decisions above.

## Deviations from Plan

### Auto-fixed Issues

1. **`getaddrinfo` unpack bug:** the guard unpacked the result list as one 5-tuple; fixed to iterate the list. Caught by the new acceptance test.
2. **Mypy strict:** `str()` wrap on resolved addresses; dropped an unneeded `type: ignore` on `Settings()`.
3. **BLE001:** the probe's catch-all is the contract (never raise), documented with a targeted `noqa` instead of a narrower-but-lying handler list.
4. **`httpx` addition:** see key-decisions — required by the plan-mandated TestClient.

### Deferred Issues (out of scope)

- `uvicorn`/`structlog`/`opentelemetry`/`pyyaml` are declared but not yet imported — plans 09/10 wire them at the marked lifespan call site.
- Repo-wide `ruff check` still carries pre-existing violations outside this plan's files.

---

**Total deviations:** 4 auto-fixed.
**Impact on plan:** None. All must-have truths hold.

## Issues Encountered

- None beyond the auto-fixed items above. `uv sync` pulled the pinned API deps without conflict.

## User Setup Required

None - no external service configuration required. No PostgreSQL on this machine; the suite asserts `reachable: false`.

## Threat Surface Scan

Mitigations for T-01-02 (loopback refusal naming the host, startup-fail not warn), T-01-28 (bounded quiet probe, no URL echo), T-01-29 (contracts-only exporter import surface, serialization mode) implemented and pinned by tests. T-01-SC unchanged (exact pins + lockfile; `httpx` added pinned).

## Verification Evidence

- `uv sync --all-packages` — OK.
- `uv run python packages/contracts/_export_schema.py` — regenerates `envelope.json` byte-identical.
- `uv run pytest packages/contracts/tests tests/integration -q` → **86 passed**.
- `uv run mypy --strict apps/api/src packages/contracts/src` → **clean, 15 files**.
- `uv run ruff check` + `ruff format --check` on all new files → clean.

## Next Phase Readiness

- Wave 3 unblocked: plans 02, 05, 10, 11 are `ready` (deps on 01-01/01-03/01-08 satisfied).
- Plan 09/10 extension points marked: lifespan logging call site, settings field set, `hash_effective_config` secret-exclusion hardening.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
