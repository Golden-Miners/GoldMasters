---
phase: 03-deterministic-analysis-strategy-rules-and-risk-gates
plan: '03'
subsystem: risk
tags: [levels, risk-gate, ordering, decimal, fail-closed, role-matrix, goldmasters]

# Dependency graph
requires:
  - phase: 03-deterministic-analysis-strategy-rules-and-risk-gates
    provides: conventions.py quantization, strategies/base.py rule_checks + evaluation (plans 03-01/03-02)
provides:
  - src/goldmasters/risk/levels.py (code-computed levels, Decimal R:R recompute, standard-mirror ordering, null-when-unknown)
  - src/goldmasters/risk/gate.py (fail-closed GateVerdict, sole path to TRADE-eligible levels)
  - docs/roles.md (14-role matrix: responsibility, typed I/O, version, timeout policy, failure status)
affects: [04-langgraph-nodes, future-approved-strategies, ceo-decision-wiring]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 8546
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns: [recomputed-not-trusted-risk-reward, sole-accessor-gate-verdict, test-only-contract-double]

key-files:
  created: [src/goldmasters/risk/levels.py, src/goldmasters/risk/gate.py, src/goldmasters/risk/__init__.py, tests/unit/test_levels.py, tests/unit/test_risk_gate.py, docs/roles.md]
  modified: []

key-decisions:
  - "Ordering validated on quantized values: a pair that orders pre-quantization but collides on the grid stays null"
  - "Unset GOLDMASTERS_ risk policy blocks fail-closed (never defaults); settings floats arrive via Decimal(str(value)) at the call site"
  - "trade_eligible_levels is the sole accessor: blocked verdicts yield None, and TRADE requires complete levels, so nothing reaches a decision unvalidated"
  - "Monitoring shape pinned by a test-only ContractModel double (extra=forbid rejects recommendation=); src stays free of a monitoring model that belongs to Phase 4"
  - "Role timeouts documented as operator-set bounded policy, not invented seconds (Rules 1.1); interface version 0.1.0 defined by docs/roles.md"

patterns-established:
  - "Claimed-value cross-check: an optional claimed output that differs from the recomputed value blocks (T-03-08)"
  - "Pass/block split validators: passed carries levels and no reasons, blocked carries reasons and no levels"

requirements-completed: [REQ-specialist-agent-responsibilities]

# Coverage metadata (#1602) — one entry per shipped deliverable. Drives DETERMINISTIC UAT routing in verify-work.
coverage:
  - id: D1
    description: "Levels computed in code, quantized to tick, standard-mirror ordered; any violation yields null; risk_reward recomputed never trusted"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_levels.py#test_long_ordering_passes_and_quantizes"
        status: pass
      - kind: unit
        ref: "tests/unit/test_levels.py#test_claimed_risk_reward_mismatch_blocks"
        status: pass
    human_judgment: false
  - id: D2
    description: "Gate blocks on ordering, risk limits, quality, and evidence with reasons; bypass impossible via sole accessor; conflicts preserved"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_risk_gate.py#test_bypass_blocked_levels_cannot_become_trade"
        status: pass
      - kind: unit
        ref: "tests/unit/test_risk_gate.py#test_conflicts_preserved_never_reconciled"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every specialist role documented with responsibility, typed I/O, version, timeout, failure status; monitoring recommendation-free; no-overwrite normative"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_risk_gate.py#test_monitoring_shape_carries_no_recommendation"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-10-15
status: complete
plan_head_before: 957bf8ead626b468890eea526cc097abae5a14d3
plan_head_after: 814d6ae920545462699e0847a15c712fc656bbeb
commits: 3
---

# Phase 3 Plan 03: Candidate Levels, Risk Gate, and Role Matrix Summary

**Deterministic candidate levels with Decimal R:R recomputation and null-when-unknown, a fail-closed risk gate as the sole path to TRADE-eligible levels, and the 14-role specialist matrix fixing Phase 4's contracts**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-10-15
- **Tasks:** 3/3
- **Files modified:** 6 (6 created, 0 modified)

## Accomplishments

- `src/goldmasters/risk/levels.py`: `build_candidate_levels` consuming strategy `rule_checks` (any non-pass → null) and `conventions.quantize_to_tick` (never re-implemented); standard-mirror ordering validated on quantized values; `compute_risk_reward` in Decimal; claimed-value mismatch → null (T-03-08); no threshold literal — tick size and policy arrive as arguments
- `src/goldmasters/risk/gate.py`: `evaluate_gate` in enforcement order (ordering → `GOLDMASTERS_` risk limits fail-closed → `QualityStatus.OK`-with-zero-flags → all-`VALID` evidence); `GateVerdict` pass/block-split validator; unknown regime / no-setup blocks; conflicts preserved verbatim; `trade_eligible_levels` sole accessor (T-03-07)
- `docs/roles.md`: 14 roles each with single responsibility, contract-typed I/O by exact model name, interface version 0.1.0, operator-set bounded timeout policy, `AgentRunStatus` failure mapping; normative Monitoring-no-recommendation and no-overwrite rules
- 21 new tests: long/short pass, 7 misordering directions → null, unknown direction/rule-fail → null, quantization-collision → null, R:R mismatch blocks, per-check gate blocks with reasons, verdict invariants, bypass proof (blocked → null → TRADE construction rejected), monitoring shape (extra=forbid rejects `recommendation=`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Levels** - `5bb66af` (feat)
2. **Task 2: Gate** - `f4cef0e` (feat)
3. **Task 3: Role matrix** - `814d6ae` (docs)

**Plan metadata:** docs commit follows (STATE/ROADMAP/SUMMARY)

## Files Created/Modified

- `src/goldmasters/risk/levels.py` - candidate levels + ordering + R:R recompute
- `src/goldmasters/risk/gate.py` - fail-closed gate + sole TRADE accessor
- `src/goldmasters/risk/__init__.py` - risk package barrel
- `tests/unit/test_levels.py` - 9 levels tests
- `tests/unit/test_risk_gate.py` - 12 gate + monitoring-shape tests
- `docs/roles.md` - 14-role matrix

## Decisions Made

- Locked D-3.1…D-3.5 from 03-CONTEXT.md implemented as written, never re-decided
- Ordering validated post-quantization (strictest point): pre-quantization order that collides on the grid is a violation, caught by `test_ordering_validated_on_quantized_values`
- Gate risk arguments typed `Decimal | None`; the settings-float → Decimal conversion lives at the call site (`Decimal(str(value))`), keeping float out of the level path entirely
- `PositiveDecimal` exported from gate.py documents the argument form for future call sites; the fail-closed `None`-blocks behavior is tested, not just typed
- Monitoring output shape lives as a test-only ContractModel double mirroring docs/roles.md (like 03-02's throwaway strategy double) — no src model for a Phase 4 concern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff line-length + format on 2 files**
- **Found during:** Task 2 (lint pass)
- **Issue:** 4 lines over 100 chars (ordering reason strings, test case tuples); `ruff format` preferred parenthesized wrap
- **Fix:** `ruff format` on the touched files, re-ran check clean + targeted tests green
- **Files modified:** levels.py, test_levels.py (within their task commits)
- **Verification:** `ruff check` clean, `ruff format --check` clean

---

**Total deviations:** 1 auto-fixed (bug-fix lint)
**Impact on plan:** Formatting mechanics only; no behavior, scope, or decision changed.

## Issues Encountered

- Commits landed on `master`: this checkout is the main repo (not a worktree) and every prior phase commit is on `master` — followed repo precedent per 03-01/03-02. No `gsd_run` CLI exists in this environment, so STATE/ROADMAP were updated by direct edit below.

## Verification Evidence

- Targeted: `tests/unit/test_levels.py + test_risk_gate.py` — 21 passed
- Full suite: exit 0, 365 passed + 2 skipped (pre-existing `live_mt5`) — Phase-2 baseline unbroken (+21 new)
- `ruff check` on all touched files: clean. `ruff format --check` on all touched files: clean
- `mypy --strict` on both risk modules: clean
- Signals-only boundary scan: no `order_send`/`symbol_select`/`MetaTrader5` in `src/` or new tests
- No post-commit deletions; no untracked leftovers from this plan

## User Setup Required

None - no external service configuration required. Risk limits arrive via existing `GOLDMASTERS_MAX_RISK_PERCENT_PER_IDEA` / `GOLDMASTERS_MIN_RISK_REWARD_RATIO` settings (still `None` placeholders until the operator approves a strategy set — the gate blocks fail-closed until then, by design).

## Next Phase Readiness

- Phase 3 success criteria 4, 5, 6 now TRUE: levels computed/validated null-when-unknown; gate enforces all four checks and can block; role matrix fixes Phase 4 node contracts
- Phase 4 can wire `evaluate_gate` → `trade_eligible_levels` → CEO `DecisionRecord` immediately; the only remaining input is operator approval of the strategy set + risk-limit values (D-3.1 open item, unchanged)
- DST ground truth vs the live server clock remains operator-owned (03-CONTEXT.md open item, unchanged)

---
*Phase: 03-deterministic-analysis-strategy-rules-and-risk-gates*
*Completed: 2026-10-15*

## Self-Check: PASSED

- All created files exist (risk/levels.py, risk/gate.py, risk/__init__.py, both test files, docs/roles.md, SUMMARY)
- All task commits are ancestors of HEAD (`5bb66af`, `f4cef0e`, `814d6ae`)
- No stub patterns in new code (every function implemented and test-wired); no new threat surface (pure computation over validated bars, within the plan's threat model; T-03-07/08/09 each covered by a test; T-03-SC honored — zero installs)
