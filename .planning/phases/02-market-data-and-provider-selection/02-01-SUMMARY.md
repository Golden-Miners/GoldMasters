# 02-01 Summary — Tracer: settings → gateway → adapter → API

**Plan:** 02-01-PLAN.md (Wave 1 tracer) · **Status:** complete · **Date:** 2026-10-15
**Requirements:** REQ-instrument-provider-selection, REQ-market-data-ingestion-validation

## What was built

End-to-end FakeTerminal-backed slice for XAUUSD/H1: `services/mt5_adapter/`
(`terminal.py` lazy-only `MetaTrader5` import, `adapter.py`, `normalize.py`,
`validation.py`) → `QualityStatus.OK` + contracts minor bump (`1.0`→`1.1`,
schemas regenerated) → D-59 `GOLDMASTERS_` settings keys (fail-closed server
timezone, no `GOLDMASTERS_MT5_*` secret) → `probe_mt5` + `GET /v1/market/bars`,
`GET /v1/market/quote` + `/health` provider object → boundary-scan rework
(path-scoped adapter allowlist, `FORBIDDEN_ADAPTER_CALLS={symbol_select,login}`)
→ `tests/unit/test_mt5_tracer.py` + `tests/integration/test_mt5_health_api.py`.

## Files changed

New: `services/mt5_adapter/{__init__,terminal,adapter,normalize,validation}.py`,
`apps/api/src/goldmasters_api/market.py`,
`tests/{unit/test_mt5_tracer,integration/test_mt5_health_api}.py`.
Modified: contracts `enums/versions/__init__` + 4 schemas, `settings/health/app`,
`config/goldmasters.yaml`, `.env.example`, `tests/security/_boundary*` (+2),
`tests/{conftest,contract_core,env_example,settings_startup,health}`.

## Test evidence (all green, exit 0)

- `uv run pytest` — full suite green (213 tests, incl. 22 tracer + 5 API + DB round-trips against repo-local cluster).
- `uv run ruff format --check` + `uv run ruff check` — clean on changed files.
- `uv run mypy --strict .` — clean, 57 files.
- Gate `--fast` steps replicated natively (`sh`/`bash` unusable here: no `sh`, WSL has no `uv`).

## Fixes applied during execution (beyond partial work found on disk)

1. `market.py` union return annotations (`list[MarketBar] | JSONResponse`) broke
   FastAPI collection → `response_model=None` on both routes.
2. Contract-version bump broke `test_envelope_accepts_the_documented_document`
   (hardcoded `"1.0"`) → document now references `CONTRACT_VERSION`.
3. New required `MT5_SERVER_TIMEZONE` broke session-scoped DB fixtures
   (`_working_url` misreported it as DATABASE_URL) → `setdefault("UTC")` in
   `_working_url`; production stays fail-closed.
4. `mypy --strict` workspace: `cast(ProviderKind, …)` in `market.py`,
   `QualityStatus.STALE` instead of `"stale"`, removed stale type-ignores,
   `verdict_for_bars` imported from `validation` (not re-exported).
5. Decimal wire form strips trailing zeros (`2387.1`, not `2387.10`) —
   test expectation corrected, code correct per contract.

## Deviations / open items

- None from plan scope. `live_mt5` operator verification still
  pending (no terminal here): exact `account_info`/`terminal_info` field names
  and the Python 3.14 `MetaTrader5` wheel are must-verify-first on the MT5 host.
- Weekend-gap classifier, full health-state matrix, precision population are
  plans 02-02 → 02-04 (waves 2–3), untouched.

## Follow-ups

- Next: execute 02-02 + 02-03 (Wave 2, parallel) after this commit.
- Note for 02-04: `T-02-SC` lockfile pin must be platform-marker-scoped so
  `uv sync` stays green on non-Windows CI.
