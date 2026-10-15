# Phase 2 — MT5 Integration Surface Coverage

**Written:** 2026-10-15
**Scope:** `MetaTrader5` Python package surface used by `services/mt5_adapter` (docs: mql5.com Python Integration, fetched 2026-10-15).

Default is INTEGRATE. OPT-OUT carries a one-line reason. Field names marked must-verify-first (package not installed here, RISK-03).

## Capability matrix

| MT5 capability | Disposition | Plan | Notes |
|---|---|---|---|
| `initialize()` bare (no args) | INTEGRATE | 02-01 | D-47 attach pattern; only credential-free form allowed |
| `initialize(login=, password=, server=)` / `login()` | OPT-OUT | — | D-47 forbids credential handling; bare form only |
| `shutdown()` | INTEGRATE | 02-01 | closes IPC, not the terminal |
| `version()` → build string | INTEGRATE | 02-04 | `provider_spec_version` for precision rows (D-24) |
| `copy_rates_from_pos` | INTEGRATE | 02-01 | primary bars call; drop pos-0 forming bar |
| `copy_rates_range` | INTEGRATE | 02-02 | gap re-check / backfill only, not the hot path |
| `copy_rates_from` | OPT-OUT | — | from_pos preferred; avoids server-clock input and TZ ambiguity |
| `symbol_info_tick` | INTEGRATE | 02-01 | `get_latest_quote`; `time_msc` authoritative; last=0.0/volume=0 → None |
| `symbol_info` | INTEGRATE | 02-01/02-04 | spec + read-only Market Watch check (`select`/`visible`); digits/point/contract-size |
| `symbols_get` / `symbols_total` | INTEGRATE | 02-01 | capability reporting only, never auto-substitution |
| `symbol_select` | OPT-OUT | — | mutates terminal state; forbidden by name in adapter tree (D-49) |
| `last_error()` codes | INTEGRATE | 02-03 | full table mapped; one sanitized capture per failure (C-09) |
| `terminal_info().trade_allowed` + `account_info()` trade-mode | INTEGRATE | 02-01/02-04 | investor read-only assertion (D-46); exact field names must-verify-first |
| order/trade functions (`order_send`, `order_check`, history/positions trade ops) | OPT-OUT | — | signals-only boundary; globally forbidden by the scan (R-02) |

## No-integration declaration

No second data source is integrated in Phase 2 (D-44, deferred). No additional instrument, timeframe, or MT5 trade-adjacent capability is integrated; each OPT-OUT above cites its decision. Nothing on this surface is left unexamined.
