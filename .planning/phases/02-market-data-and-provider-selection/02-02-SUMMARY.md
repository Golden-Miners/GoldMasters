# 02-02 Summary — Full validation policy: bars, session quotes, weekend classifier

**Plan:** 02-02-PLAN.md (Wave 2) · **Status:** complete · **Date:** 2026-10-15
**Requirements:** REQ-market-data-ingestion-validation, REQ-instrument-provider-selection

## What was built

Tracer validation expanded to the full deterministic policy (research §3):

- **Bars:** finite → ordering → duplicate → gap → OHLC-tick-align → volume →
  freshness, all pure with explicit `now_utc`. Mid-week gaps stamp
  `MISSING_HISTORY` on the later bar; weekend/break-adjacent gaps flag `GAP`.
- **Session quotes:** `session_for` + settings-driven windows
  (`GOLDMASTERS_SESSION_{OVERLAP,MAJOR,ASIA}_UTC`, research §3 defaults);
  weekend ticks read disconnected (unavailable), never stale.
- **Classifier:** `is_weekend_closed`, `classify_gap`, `missing_opens`,
  window parsers (all fail-closed `ValueError`); single-bar daily-break
  tolerance; never synthesis.
- **Backfill:** one `copy_rates_range` re-fetch per unexpected gap in
  `get_bars`; merges only missing opens; first-pass `MALFORMED`/`DUPLICATE`
  evidence preserved across the merge (`preserve` param).
- **Settings:** 3 session keys + fail-closed format validators; yaml +
  `.env.example` extended; key-set tests updated.

## Files changed

`services/mt5_adapter/{validation,adapter,normalize}.py`,
`apps/api/src/goldmasters_api/{settings,market,health}.py`,
`config/goldmasters.yaml`, `.env.example`,
`tests/unit/{test_mt5_validation_bars,quotes,weekend}.py` (new, 25 tests),
`tracer/integration/settings tests` updated to the 02-02 contract.

## Test evidence (all green, exit 0)

- `uv run pytest tests/unit/test_mt5_validation_{bars,quotes,weekend}.py` — 25 passed.
- Full `uv run pytest` green; `ruff check/format` clean; `mypy --strict .` clean.
- Tracer regression: mid-week gap test updated to `missing-history`
  (documented supersession, not a break).

## Deviations / open items

- `_probe_once` verdict branch mapped kinds explicitly (verdict
  missing-history → health missing-history; stale/malformed → disconnected).
- `in_weekend_close` tracer stub deleted; settings-driven
  `is_weekend_closed` is the single implementation.
- DST ±1h remains operator-confirmed (documented in setting help + tests).

## Follow-ups

- 02-03 consumes `classify_gap` output for health precedence (same wave, done next).
- Live-terminal confirmation of weekend/break windows still pending (operator).
