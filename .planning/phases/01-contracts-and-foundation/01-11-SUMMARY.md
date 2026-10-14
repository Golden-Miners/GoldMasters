---
phase: 01-contracts-and-foundation
plan: "11"
subsystem: contracts
tags: [python, pydantic, contracts, news, sentiment, backtest, json-schema, barrel]

# Dependency graph
requires: [01 (base/enums), 03 (market/decision/journal), 08 (export entry point)]
provides:
  - "`news.py`/`sentiment.py`/`backtest.py` reasoning-and-recall contracts"
  - "Final `__init__.py` barrel re-exporting every contract + `CONTRACT_VERSION`"
  - "Extended barrel-derived `_export_schema.py` enumeration + 10 committed schema documents"
  - "`.gitattributes` (`* text=auto`, `*.json text eol=lf`)"
affects: [04 (drift/conformance over the complete set), 07 (TypeScript generation from schema/)]

actuals:
  tokens: 0
  tasks: 3
  commits: 3
  plan_head_before: d73eb9c
  plan_head_after: 375e334

key-files:
  created:
    - packages/contracts/src/goldmasters_contracts/news.py
    - packages/contracts/src/goldmasters_contracts/sentiment.py
    - packages/contracts/src/goldmasters_contracts/backtest.py
    - packages/contracts/tests/test_reasoning_contracts.py
    - packages/contracts/schema/{market,quote,precision,decision,journal,news,sentiment,backtest,error}.json
    - .gitattributes
  modified:
    - packages/contracts/src/goldmasters_contracts/__init__.py
    - packages/contracts/_export_schema.py
    - packages/contracts/schema/envelope.json

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "News/sentiment/backtest accept valid + explicit-unavailability documents, reject wrong-enum/missing-field/extra-field mutations; sentiment bounds inclusive, score requires versioned method."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_reasoning_contracts.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Barrel resolves every contract name; .gitattributes pins * text=auto + *.json eol=lf."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "barrel import assertion in Task 2 verify command"
        status: pass
    human_judgment: false
  - id: D3
    description: "Enumeration equals committed set; export byte-deterministic with canonical form; decimals/timestamps string-typed (only documented float score is number); envelope stable across extension."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_reasoning_contracts.py#test_export_is_deterministic"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 11: Reasoning Contracts + Final Barrel + Schema Export Summary

**News, sentiment and backtest contracts as validated code, one explicit barrel, and the complete committed JSON Schema set exported deterministically from the models.**

## Task Commits

1. **Task 1: News, sentiment, backtest contracts** - `bb57a16`
2. **Task 2: Final barrel + line-ending rule** - `b7cb834`
3. **Task 3: Complete enumeration + committed set** - `375e334`

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **Sentiment `score` exports as JSON `number`:** the score is a bounded `float`, not a `Decimal` — no wire-form rule pins it to string. The export test allows `number` exactly at `sentiment.json/properties/score` and forbids it everywhere else.
2. **`CONTRACTS` holds barrel attribute names**, resolved via `getattr` on the barrel, rather than model references — the enumeration and the re-export list cannot disagree.

## Verification Evidence

- `uv run pytest packages/contracts/tests -q` → **86 passed**.
- `uv run ruff check` + `format --check` on all touched files → clean.
- `uv run mypy --strict packages/contracts/src` → clean, 14 files.

## Next Phase Readiness

- Criterion 1 complete: every Schema.md contract is validated versioned code with a committed schema document.
- Plans 04 (evidence) and 07 (TS generation) consume `schema/`.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
