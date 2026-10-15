# 02-03 Summary — Health states, single retry, code table, redaction

**Plan:** 02-03-PLAN.md (Wave 2) · **Status:** complete · **Date:** 2026-10-15
**Requirements:** REQ-market-data-ingestion-validation, REQ-instrument-provider-selection

## What was built

Failure side of the tracer (criterion 6, D-50/D-51):

- **Five distinct states** with precedence
  terminal-closed > disconnected > unsupported-symbol > missing-history >
  stale > connected: `initialize() False` forces terminal-closed regardless
  of `last_error`; stale/malformed batches degrade; weekend stays connected
  with `market_open=false`.
- **Single retry:** transient codes get exactly 2 attempts; unsupported /
  missing-history / terminal-closed never retry; recovery returns data.
- **Full code table** pinned (`RES_S_OK` … `TIMEOUT`/internal range, incl.
  `NOT_FOUND → missing-history`, `AUTH_FAILED → terminal-closed`).
- **Robustness fix:** raising `symbol_info` now reads disconnected instead of
  escaping `get_bars`/`get_instrument_spec`.
- **Redaction:** terminal text in no API body, health object, or trace;
  one sanitized capture per failed read (counts asserted).

## Files changed

`services/mt5_adapter/adapter.py` (precedence, attach rule, symbol_info guard),
`tests/unit/{test_mt5_health_states,test_mt5_retry_mapping}.py` (new, 13 tests).

## Test evidence (all green, exit 0)

- `uv run pytest tests/unit/test_mt5_health_states.py tests/unit/test_mt5_retry_mapping.py` — 13 passed.
- Tracer + API regression green; full suite green; ruff + mypy strict clean.

## Deviations / open items

- None from plan scope. `RES_E_AUTO_TRADING_DISABLED` maps disconnected
  (irrelevant for reads; surfaces visibly if ever seen).
- `account_info`/`terminal_info` field names remain must-verify-first
  (live-terminal follow-up, asserted defensively at runtime).

## Follow-ups

- Next: 02-04 (Wave 3: precision population, config hash, contracts, live scaffold).
