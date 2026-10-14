---
phase: 01-contracts-and-foundation
plan: "04"
subsystem: contracts
tags: [purity, drift, conformance, json-schema, evidence]

# Dependency graph
requires: [01 (base), 03 (market/decision/journal), 11 (complete schema set)]
provides:
  - "Purity gate: contracts import only pydantic + fixed stdlib + self"
  - "Drift gate: committed schema byte-matches fresh export (CRLF-tolerant)"
  - "Golden conformance: shared accepted/rejected cases incl. verbatim Schema.md examples"
affects: [06 (imports cases.py for the persistence round-trip), 07 (type generation input), 08 (Phase 8 re-run)]

actuals:
  tokens: 0
  tasks: 3
  commits: 2
  plan_head_before: 03f8829
  plan_head_after: 19fae87

key-files:
  created:
    - packages/contracts/tests/test_import_purity.py
    - packages/contracts/tests/test_schema_export.py
    - tests/__init__.py
    - tests/contract/__init__.py
    - tests/contract/cases.py
    - tests/contract/test_conformance.py
  modified: []

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "Contracts import nothing outside the in-test allowlist; HTTP/DB roots would fail the test."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_import_purity.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Committed schema byte-matches a fresh export; enumeration equals the committed set; decimals/timestamps string-typed."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_schema_export.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Schema.md examples validate verbatim (with explicit placeholder substitutions); 10 contracts hold accepted cases and ~45 rejected mutations across every D-06 class plus named invariants."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/contract/test_conformance.py (59 tests)"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 04: Contract Evidence Summary

**Purity enforced by test, schema drift impossible silently, and every contract carrying accepted + rejected conformance evidence.**

## Task Commits

1. **Task 1: Purity test** + **Task 2: Drift test** - `c18d3b1`
2. **Task 3: Conformance suite + shared cases** - `19fae87`

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **Conformance validates through `model_validate_json`**, not `model_validate` — `strict=True` rejects Python `str`→enum/datetime coercion, while the JSON path (what production payloads take) parses them. Cases stay JSON-shaped, which plan 06 needs for its JSONB round-trip.
2. **Schema.md examples carry explicit substitutions** (`"UUID"` → prefixed UUID, format words → real timestamps/versions): the book's strings describe formats, and transcribing that honestly beats forcing a literal `"UUID"` through a prefix validator.
3. **Tasks 1+2 share one commit** (both are single-file evidence tests landed together).

## Verification Evidence

- `uv run pytest tests/contract -q` → **59 passed**.
- `uv run pytest packages/contracts/tests -q` → green incl. purity + drift.
- ruff + format + mypy strict clean on all new files.

## Next Phase Readiness

- Plan 06 imports `tests.contract.cases` for its round-trip.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
