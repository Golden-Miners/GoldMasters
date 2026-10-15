---
phase: 03-deterministic-analysis-strategy-rules-and-risk-gates
plan: '02'
subsystem: domain
tags: [market-structure, regime, strategy-interface, determinism, decimal, fail-closed, goldmasters]

# Dependency graph
requires:
  - phase: 03-deterministic-analysis-strategy-rules-and-risk-gates
    provides: conventions.py tick/adjacency helpers, GOLDMASTERS_ policy surface (plan 03-01)
provides:
  - src/goldmasters/domain/structure.py (versioned swing/high-low primitives, fail-closed verdicts)
  - src/goldmasters/domain/regime.py (TrendRegime-only classification, UNKNOWN when indeterminate)
  - src/goldmasters/strategies/base.py (Strategy protocol, RuleCheck, no-setup-on-fail evaluation)
affects: [03-levels-gate, 03-risk-gate, 04-langgraph-nodes, future-approved-strategies]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 8760
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns: [versioned-rules-with-code-hash, ordinal-swing-classification, validator-encoded-interface-rule]

key-files:
  created: [src/goldmasters/domain/structure.py, src/goldmasters/domain/regime.py, src/goldmasters/strategies/base.py, src/goldmasters/strategies/__init__.py, tests/unit/test_structure_regime.py, tests/unit/test_strategies.py]
  modified: []

key-decisions:
  - "Swing = strict extreme over explicit [left_bars, right_bars] window; equal extremes claim nothing (fail-closed, no threshold)"
  - "Regime rule is purely ordinal (last-two-swings rising/falling); needs a swing pair per side, else UNKNOWN — zero numeric policy"
  - "No-setup-on-fail is a Pydantic validator on StrategyEvaluation, not a convention future packages could ignore"
  - "No now_utc parameter: closed-bar math has no clock read; bar timestamps are already explicit inputs"
  - "UTC-adjacency helper not re-invoked: no gap policy is approved, so structure checks order (MALFORMED) but invents no gap tolerance"

patterns-established:
  - "Versioned rules: RULE_SOURCE literal + hash_rule_source (hashlib) + version constant stamped on every output"
  - "Malformed raises (TypeError/ValueError), policy failures return fail-closed verdicts (Pattern 3)"

requirements-completed: [REQ-specialist-agent-responsibilities]

# Coverage metadata (#1602) — one entry per shipped deliverable. Drives DETERMINISTIC UAT routing in verify-work.
coverage:
  - id: D1
    description: "Structure primitives compute versioned, hash-stamped verdicts; repeat runs bit-identical; Decimal-only"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_structure_regime.py#test_deterministic_repeat_runs_identical"
        status: pass
      - kind: unit
        ref: "tests/unit/test_structure_regime.py#test_no_float_or_threshold_literals_in_new_modules"
        status: pass
    human_judgment: false
  - id: D2
    description: "Regime labels come ONLY from TrendRegime; indeterminate input yields UNKNOWN, never directional"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_structure_regime.py#test_regime_uptrend_downtrend_range"
        status: pass
      - kind: unit
        ref: "tests/unit/test_structure_regime.py#test_regime_unknown_when_indeterminate_never_directional"
        status: pass
    human_judgment: false
  - id: D3
    description: "Strategy evaluation returns setup_found + rule_checks stamped with id/version; any fail/unknown yields no setup and null levels; zero strategy packages"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_strategies.py#test_single_fail_yields_no_setup_and_null_levels"
        status: pass
      - kind: unit
        ref: "tests/unit/test_strategies.py#test_no_strategy_packages_exist_only_the_interface"
        status: pass
    human_judgment: false

# Metrics
duration: 30min
completed: 2026-10-15
status: complete
plan_head_before: 3ac81544942fa821a5096f4169c8b56843803190
plan_head_after: ece890014044a3399f4729b3556820d69c45a345
commits: 3
---

# Phase 3 Plan 02: Structure, Regime, and Strategy Interface Summary

**Versioned market-structure and regime primitives plus the strategy interface: strict-extreme swings, ordinal TrendRegime classification with UNKNOWN fail-closed, and a validator-encoded no-setup-on-fail evaluation — interface only, zero approved-strategy code**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-10-15
- **Tasks:** 3/3
- **Files modified:** 6 (6 created, 0 modified)

## Accomplishments

- `src/goldmasters/domain/structure.py`: `swing_highs`/`swing_lows` over an explicit `[left_bars, right_bars]` window (strict extremes; equal neighbours claim nothing), `highest_high`/`lowest_low` Decimal max/min, `describe_structure` returning a fail-closed `StructureState` (ok vs insufficient_data) stamped with `STRUCTURE_RULES_VERSION = "1.0"` + sha256 `code_hash`; misorder → insufficient via `check_bar_order`, tick alignment via `quantize_to_tick` when `tick_size` is given, skip when `None`
- `src/goldmasters/domain/regime.py`: `classify_regime` with a purely ordinal rule — swing pair per side required, last-two-highs+lows rising → UPTREND, both falling → DOWNTREND, other confirmed shapes → RANGE, anything indeterminate → UNKNOWN; labels ONLY from `TrendRegime`, stamped with `REGIME_RULES_VERSION = "1.0"` + `code_hash`
- `src/goldmasters/strategies/base.py`: `Strategy` protocol (`STRATEGY_ID/VERSION/CODE_HASH` + `evaluate`), `RuleCheck` (rule ID, pass/fail/unknown, inputs, evidence, reason), `StrategyEvaluation` with the no-escape validator (any non-pass → no setup + null levels; setup → levels required), semver-gated version, `build_evaluation` stamping helper — and no strategy package under `strategies/`
- 22 new tests: FIXTURE_-labelled golden vectors (rising/falling/range/flat zigzags), repeat-run determinism, unknown-branch, malformed-raises, no-float/no-threshold-literal AST scans, fixture-leak scan over `src/`, interface cheat-rejection, strategies-dir contents assertion

## Task Commits

Each task was committed atomically:

1. **Task 1: Structure primitives** - `29e4203` (feat)
2. **Task 2: Regime classification** - `85f277c` (feat)
3. **Task 3: Strategy interface** - `ece8900` (feat)

**Plan metadata:** docs commit follows (STATE/ROADMAP/SUMMARY)

## Files Created/Modified

- `src/goldmasters/domain/structure.py` - swing/high-low primitives + fail-closed verdict
- `src/goldmasters/domain/regime.py` - TrendRegime-only classification
- `src/goldmasters/strategies/base.py` - Strategy protocol + evaluation contract
- `src/goldmasters/strategies/__init__.py` - package marker (D-3.1 non-goal note)
- `tests/unit/test_structure_regime.py` - 15 structure/regime tests
- `tests/unit/test_strategies.py` - 7 interface contract tests (throwaway double in-file)

## Decisions Made

- Locked D-3.1…D-3.5 from 03-CONTEXT.md implemented as written, never re-decided
- `now_utc` omitted: closed-bar math performs no clock read; bar timestamps ride inside the `MarketBar` inputs, so a clock parameter would be dead API (minor plan deviation, documented)
- `utc_adjacent` not re-invoked in structure: no gap-tolerance policy is approved, and inventing one would violate no-invented-numbers; order is enforced (MALFORMED → insufficient), gap semantics stay with a future approved policy
- Integer `2` (swing-pair minimum) treated as pair-structure alongside 0/1 in the literal scan, with an inline comment; the scan rejects all floats and all other ints
- `build_evaluation` sets `setup_found` only when all rules pass AND levels are supplied: all-pass without levels is "not yet a setup", which the validator accepts (no-setup + null levels)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `uv run` stalls; used `.venv` binaries directly**
- **Found during:** Task 1 (first test run)
- **Issue:** Same resolver/sync stall seen in 03-01; the pinned `.venv` holds every dependency
- **Fix:** All checks via `.venv/Scripts/python.exe -m pytest/ruff/mypy` — same interpreter, same pinned packages
- **Files modified:** none (toolchain only)
- **Verification:** targeted 22 passed; full suite exit 0 (344 passed, 2 pre-existing live_mt5 skips)

**2. [Rule 1 - Bug] Ruff flagged unused import, `format()` call, import order, line lengths**
- **Found during:** Task 3 (lint pass)
- **Issue:** `STRUCTURE_CODE_HASH` imported-but-unused in regime.py; `.format()` instead of f-string; isort ordering; 3 lines over 100 chars
- **Fix:** Dropped the import, f-string RULE_SOURCE, `ruff check --fix` + `ruff format` on all touched files
- **Files modified:** regime.py, structure.py, base.py, both test files
- **Verification:** `ruff check` clean, `ruff format --check` clean, committed in task commits

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug-fix lint)
**Impact on plan:** Toolchain/format mechanics only; no behavior, scope, or decision changed.

## Issues Encountered

- Commits landed on `master`: this checkout is the main repo (not a worktree) and every prior phase commit is on `master` — followed repo precedent per 03-01. No `gsd_run` CLI exists in this environment, so STATE/ROADMAP were updated by direct edit below.

## Verification Evidence

- Targeted: `tests/unit/test_structure_regime.py + test_strategies.py` — 22 passed
- Full suite: exit 0, 346 collected (344 passed, 2 skipped pre-existing `live_mt5`) — Phase-2 baseline unbroken
- `ruff check` on all touched files: clean. `ruff format --check` on all touched files: clean
- `mypy --strict` on all 3 source + 2 test files: clean
- No post-commit deletions; no untracked leftovers from this plan

## User Setup Required

None - no external service configuration required. Swing windows and tick context arrive as explicit arguments / `GOLDMASTERS_`-adjacent call-site values; no new settings keys were needed.

## Next Phase Readiness

- Wave 3 (levels + risk gate, 03-03) can consume `StructureState`, `RegimeAssessment`, and `StrategyEvaluation` immediately; the gate's "any rule fail → BLOCK" half is already encoded in the interface validator
- Strategy approvals with rule parameters + hard risk limits still await operator approval (D-3.1) — the interface is ready to stamp them
- DST ground truth vs the live server clock remains operator-owned (03-CONTEXT.md open item, unchanged)

---
*Phase: 03-deterministic-analysis-strategy-rules-and-risk-gates*
*Completed: 2026-10-15*

## Self-Check: PASSED

- All created files exist (structure.py, regime.py, strategies/base.py + __init__, both test files, SUMMARY)
- All task commits are ancestors of HEAD (`29e4203`, `85f277c`, `ece8900`)
- No stub patterns in new code (every function implemented and test-wired); no new threat surface (pure computation over validated bars, within the plan's threat model; T-03-04/05/06 each covered by a test)
