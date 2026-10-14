---
phase: 01-contracts-and-foundation
plan: "03"
subsystem: contracts
tags: [python, pydantic, contracts, market-data, precision, decision, journal, versioning, identifiers]

# Dependency graph
requires: [01 (workspace, shared base, enums, envelope shell)]
provides:
  - "`versions.py`: `CONTRACT_VERSION_MAJOR_SUPPORTED = 1`, `ContractVersion`, `parse_contract_version`, `SchemaVersionStr` fail-closed version acceptance"
  - "`ids.py`: closed `IdPrefix` registry (`run_`/`dec_`/`agent_`/`journal_`), `PrefixedId` stdlib-UUID factory, `ProviderId` snake_case key, `RunId`/`DecId`/`AgentId`/`JournalId` conveniences"
  - "refined `Envelope`: `schema_version` version-checked, `run_id` prefix-bound"
  - "`market.py`: `MarketBar`/`MarketQuote` reproducing Schema.md §4 with D-04 invariants"
  - "`precision.py`: append-only `(instrument_id, provider_id)` table, ships empty, lookup answers unknown"
  - "`decision.py`: `DecisionRecord`/`Levels` reproducing Schema.md §6, manual-review-required-true, null-unless-validated levels"
  - "`journal.py`: frozen `JournalEntry` bound to its decision snapshot"
affects: [04 (purity + drift + conformance over these models), 11 (schema export enumerates these modules + final barrel)]

actuals:
  tokens: 0
  tasks: 2
  commits: 2
  plan_head_before: 5838632
  plan_head_after: 41524f7

tech-stack:
  added: []
  patterns:
    - "Fail-closed acceptance at the boundary: unknown-major versions and wrong-prefix ids raise, never coerce"
    - "Append-only by construction: frozen models plus a `with_row` copy API instead of an update path"
    - "Null-unless-validated: TRADE carries every level, anything else carries none — ordering policy stays in Phase 3"

key-files:
  created:
    - packages/contracts/src/goldmasters_contracts/market.py
    - packages/contracts/src/goldmasters_contracts/precision.py
    - packages/contracts/src/goldmasters_contracts/decision.py
    - packages/contracts/src/goldmasters_contracts/journal.py
    - packages/contracts/tests/test_market_data_contracts.py
  modified:
    - packages/contracts/src/goldmasters_contracts/versions.py
    - packages/contracts/src/goldmasters_contracts/ids.py
    - packages/contracts/src/goldmasters_contracts/envelope.py
    - packages/contracts/src/goldmasters_contracts/__init__.py
    - packages/contracts/tests/test_contract_core.py

key-decisions:
  - "`risk_reward` stays a plain `Decimal` (a ratio, not a price) while every price field uses `PriceStr` — the wire form stays string-typed at serialization through the shared base."
  - "`JournalId` added a fourth `IdPrefix` member (`journal_`) rather than reusing `dec_` — a journal entry is its own entity type."
  - "Closed-interval lookup semantics: `at` outside `valid_from`/`valid_to` answers unknown, same as a missing key."

patterns-established:
  - "Version/identifier rules live in `versions.py`/`ids.py` and are referenced by field type, never re-implemented per contract."
  - "Every contract module docstring names its Schema.md section and locked decisions."

requirements-completed: [REQ-no-trade-execution]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Version acceptance: `1.0`/`1.7`/`1.0.3` parse, `2.0`/empty/`v1`/`1`/`1.x` raise; envelope accepts `1.4`, rejects `3.0`."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_versions_ids.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Prefix-bound ids: `run_` accepts a run UUID and rejects a `dec_` value; malformed UUID bodies rejected with stdlib `uuid` only."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_versions_ids.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Market bar validates when whole and rejects high-below-max, low-above-min, non-positive price, unordered timestamps, missing quality, provider-native timeframe and display-name provider_id."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_market_data_contracts.py#test_valid_bar_accepted_high_below_max_rejected"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_market_data_contracts.py#test_provider_native_timeframe_and_display_provider_id_rejected"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty precision table answers unknown for any key; populated rows round-trip and respect validity intervals."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_market_data_contracts.py#test_empty_precision_table_answers_unknown"
        status: pass
    human_judgment: false
  - id: D5
    description: "Decision enforces manual-review-required-true, tolerates null levels for non-TRADE, requires complete levels plus direction for TRADE."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_market_data_contracts.py#test_decision_manual_review_and_level_rules"
        status: pass
    human_judgment: false
  - id: D6
    description: "Journal entry binds to its snapshot; mismatched ids and post-construction mutations are rejected."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_market_data_contracts.py#test_journal_rejects_mutation"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 03: Version/Identity Rules + Market, Precision, Decision, Journal Contracts Summary

**Version acceptance and prefix-bound identifiers that fail closed, plus the Schema.md §4 market contracts, the append-only precision table, the Schema.md §6 decision contract and the immutability-bearing journal record — all as validated versioned code.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-10-14
- **Tasks:** 2
- **Files modified:** 5 created, 5 modified (incl. Task 1's files)

## Accomplishments

- Task 1 (prior commit `8553ad4`, verified not redone): `versions.py`, `ids.py` (`run_`/`dec_`/`agent_`), refined `envelope.py`, `test_versions_ids.py`.
- Task 2 (this run): `market.py` (`MarketBar`/`MarketQuote` with D-04 validators), `precision.py` (empty-by-default append-only table), `decision.py` (`DecisionRecord` + `Levels`), `journal.py` (frozen snapshot-bound entry), `test_market_data_contracts.py` (8 tests covering all 7 plan behaviours).
- Full contracts suite: **77 passed**; `mypy --strict` clean over 11 source files; new files `ruff check` + `ruff format` clean.

## Task Commits

1. **Task 1: Version acceptance, prefix-bound identifiers, refined envelope** - `8553ad4` (feat, prior run)
2. **Task 2: Market bar/quote, precision table, decision contract** - `41524f7` (feat)

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Files Created/Modified

- `packages/contracts/src/goldmasters_contracts/versions.py` - version acceptance (Task 1)
- `packages/contracts/src/goldmasters_contracts/ids.py` - prefix registry + `JournalId` + strict return annotations (Tasks 1+2)
- `packages/contracts/src/goldmasters_contracts/envelope.py` - version + prefixed-id fields (Task 1)
- `packages/contracts/src/goldmasters_contracts/market.py` - bar/quote contracts (Task 2)
- `packages/contracts/src/goldmasters_contracts/precision.py` - append-only table (Task 2)
- `packages/contracts/src/goldmasters_contracts/decision.py` - decision record + levels (Task 2)
- `packages/contracts/src/goldmasters_contracts/journal.py` - journal entry (Task 2)
- `packages/contracts/tests/test_versions_ids.py` - 5 behaviours (Task 1)
- `packages/contracts/tests/test_market_data_contracts.py` - 7 behaviours (Task 2)
- `packages/contracts/src/goldmasters_contracts/__init__.py` - added missing `QualityFlag`/`QualityStatus` barrel exports
- `packages/contracts/tests/test_contract_core.py` - envelope fixture uses `run_`-prefixed id

## Decisions Made

- Same three as key-decisions above.

## Deviations from Plan

### Auto-fixed Issues

1. **Stale envelope fixture:** `test_contract_core.py` used a bare-UUID `run_id` that the refined envelope correctly rejects. Updated the fixture to `run_`-prefixed form — the test, not the contract, was wrong.
2. **Barrel gap:** `__init__.py` imported `QualityFlag`/`QualityStatus` but omitted them from `__all__`; added (additive, no behaviour change).
3. **Missing strict annotations:** `ids.py` lacked return types on `_prefixed_id_validator`/`PrefixedId`; added `Callable[[str], str]` / `Any`.
4. **`risk_reward` strictness:** plain `Decimal` under `strict=True` rejects `"2.0"` strings; test passes `Decimal("2.0")` objects. Production wire stays numeric — serialization-mode export (plan 11) governs the JSON form.

### Deferred Issues (out of scope)

- Repo-wide `ruff check` still reports pre-existing violations outside this plan's files (20 at HEAD before this plan's work, incl. import-sort style the committed files share). New files are clean; the backlog belongs to plan 04's gate, not this plan.
- Committed JSON Schema export of these models stays with plan 11 per the plan's own split note.

---

**Total deviations:** 4 auto-fixed (all root-caused above).
**Impact on plan:** None. All must-have truths hold; verification suite green.

## Issues Encountered

- `JournalEntry.model_copy(update=...)` does not re-run validators, so the immutability test re-validates a mutated dump instead — frozen config still blocks attribute assignment.
- Prior wave-2 subagent dispatch failed on a provider rate limit (`free-models-per-day`); this plan was executed inline instead, reusing the ready dispatch brief. No scope change.

## User Setup Required

None - no external service configuration required.

## Threat Surface Scan

Mitigations for T-01-10 (model validators on OHLC/positivity/ordering/manual-review), T-01-11 (empty-table-unknown, no update path), T-01-12 (fail-closed version/prefix, stdlib-only) implemented and pinned by tests. T-01-SC unchanged (no new dependencies).

## Verification Evidence

- `uv run pytest packages/contracts/tests -q` → **77 passed**.
- `uv run mypy --strict packages/contracts/src` → **Success: no issues found in 11 source files**.
- `uv run ruff check` + `ruff format --check` on the 4 new files → clean.
- Plan-intercepts export readiness: `PriceStr`/`UtcDatetime` carry explicit `WithJsonSchema({"type": "string"})`, so plan 11's serialization-mode export emits flat string types (no `anyOf`).

## Next Phase Readiness

- Plans 04 (evidence over these models) and 11 (export + barrel + news/sentiment/backtest) can proceed; 01-11's export enumeration must include `market`, `precision`, `decision`, `journal`.
- Open FLAGGED ASSUMPTIONS unchanged (boundary thresholds, rounding contract, concurrency) — recorded, not invented.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
