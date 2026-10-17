# Phase 6: Journal, Persistence and Backtesting — CONTEXT

**Discussed:** 2026-10-16 (4 gray areas, operator-locked)
**Inputs:** 06-RESEARCH.md (HIGH), operator answers

## Locked decisions

1. **Standard fill + placeholder costs (D-6.1).** Fill at next-bar open; costs as
   fail-closed settings (spread, commission, slippage, swap). Values stay
   placeholders until operator confirms. No metric is authoritative before that.
2. **Standard outcome fields (D-6.2).** observation_id, decision_id, observed_at,
   observed levels/exit, pnl terms; corrections via `supersedes` (never mutation).
3. **Manifests as DB rows (D-6.3).** Versioned manifest rows joined by
   run_id/dataset_id; source files hashed and referenced, never silently dropped.
4. **Local + operator policy (D-6.4).** Local Postgres via repo scripts for dev/test;
   retention/backup documented as operator-owned with safe defaults. Prod deploy
   stays operator business.

## Already exists (reuse, don't rebuild)

- `JournalEntry` frozen + binding checks; `BacktestRecord` structural refs;
  migration pattern D-07 (0001 untouched — add 0002/0003); D-4.3 run_id join key.

## Phase 6 build (new)

- 0002/0003 migrations; immutable snapshots + append-only outcomes; backtest loop
  over live-path seam (`evaluate` → gate → levels Decimal math) on 10 pinned 1.0.0
  strategies; split enforcement; leakage/timestamp/cost tests; deterministic
  metrics + hand-verifiable cases.

## Open (operator-owned)

- Cost values; news sources; T0004; strategy thresholds; prod Postgres policy.

## Next

Planner creates PLAN.md files against D-6.1…D-6.4. Do not re-ask locked items.
