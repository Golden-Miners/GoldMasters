---
phase: 06-journal-persistence-backtesting
plan: 03
subsystem: backtest-metrics-guards
tags: [backtest, metrics, leakage, costs, splits]
requires: [06-01-journal-persistence, 06-02-backtest-runner]
provides: [deterministic-metrics, leakage-guard, cost-guard, split-violation-guards, hand-verifiable-ledger]
affects: []
tech_stack:
  added: []
  patterns: [decimal-only-metrics-D-6.2, placeholder-costs-fail-closed-D-6.1, manifest-by-dataset-ref-D-6.3]
key_files:
  created:
    - src/goldmasters/backtest/metrics.py
    - tests/unit/test_backtest_metrics.py
    - tests/unit/test_backtest_leakage.py
    - tests/unit/test_backtest_costs.py
  modified:
    - tests/unit/test_backtest_metrics.py  (ruff format)
decisions:
  - "Metric output from backtest/metrics.py is authoritative; prose never recalculates (R-05, T-06-09)"
  - "Costs stay declared placeholders; require_confirmed fails closed until operator confirms (D-6.1, T-06-07, T-06-11)"
  - "Hand-computed 5-trade ledger fixtures assert exact Decimal equality with code output"
  - "Leakage probe: future-bar spike leaves signal-bar evaluation/fill untouched (T-06-05)"
metrics:
  duration: ~40 min
  completed: 2026-10-16
  commits: 2 (b658144 Task 1, a2361a5 Tasks 2-3)
  tests: 31 passed across metrics/leakage/costs/splits/record suites
plan_head_before: ee03d1a
plan_head_after: a2361a5
commits: 5 total for phase (06-01: 4, 06-02: 3, 06-03: 2; base ee03d1a shared)
status: complete
actuals:
  tokens: ~12000
  tasks: 3
  commits: 2 in this plan
---

# Phase 06 Plan 03: Deterministic Metrics + Honesty Guards (Wave 3) Summary

Criteria 4 and 5 of Phase 6: deterministic code-computed metrics cross-checked by hand cases, plus leakage/alignment/cost/split guards that fail on violation.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Deterministic Decimal metrics + hand-verifiable 5-trade cases | b658144 | backtest/metrics.py, test_backtest_metrics.py |
| 2 | End-to-end honesty slice: leakage + alignment + cost guards | a2361a5 | test_backtest_leakage.py, test_backtest_costs.py |
| 3 | Split-enforcement violation coverage | a2361a5 | covered by existing test_backtest_splits.py + test_backtest_record.py (no new source logic) |

## Evidence

- `uv run pytest tests/unit/test_backtest_metrics.py tests/unit/test_backtest_leakage.py tests/unit/test_backtest_costs.py tests/unit/test_backtest_splits.py tests/unit/test_backtest_record.py -q` → 31 passed
- `uv run ruff format --check` + `ruff check` on all 9 backtest-source files → clean
- `uv run mypy --strict` on all 9 touched files → no issues
- Zero-edge round trip: net loss equals declared placeholder costs; zero-cost record refused (require_confirmed)
- Leakage: plant a future spike on bar N+1 → bar-N evaluation/fill identical (UTC cutoff holds)
- Hand ledger `[+10, -5, +20, -10, +5]`: win_rate 0.6, expectancy 4, profit_factor 35/15, max_drawdown 10 — exact Decimal match
- Empty input → None never default; no-losers profit factor → None; all-profit curve → drawdown 0
- All metric definitions carry the D-6.1 "placeholder per D-6.1, not authoritative" marker

## Must-Have Truths — Status

- Metrics deterministic Decimal only, no LLM prose recalculates: PROVEN (T-06-09)
- Hand-verifiable cases cross-check every metric: PROVEN (5-trade ledger fixture)
- Leakage / timestamp alignment / cost application / split enforcement guarded by failing tests: PROVEN (criteria 4–5)
- Next-bar-open fill, placeholder costs, splits gate, IS/VS/OOS separation: PROVEN from 06-02, re-verified here

## Deviations from Plan

None beyond the 06-02-recorded ones (extra persistence.py, manifest join by dataset_ref). Task 3 required "no new source logic" — existing 06-02 split/record tests already cover training-on-OOS refusal, validation-bleed refusal, missing-data silent-drop rejection, and assumption-field removal; no additions needed.

## Known Stubs

None. Intentional D-6.1 declared-cost mechanism only (PLACEHOLDER marker + require_confirmed fail-closed); costs unconfirmed until operator supplies values.

## Self-Check: PASSED

- All 9 files exist on disk; commits b658144 + a2361a5 are ancestors of HEAD.
- No new packages installed (T-06-SC).
- Phase 6 plans 06-01/06-02/06-03 all complete; ROADMAP checklist + progress row need the final checkmark.

## Risk

Cost values remain placeholders — every backtest metric is non-authoritative until the operator confirms spread/commission/slippage/swap (D-6.1). Prod Postgres retention/backup policy is operator-owned (D-6.4).
