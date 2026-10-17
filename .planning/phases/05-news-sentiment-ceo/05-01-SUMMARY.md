---
phase: 05-news-sentiment-ceo
plan: 01
subsystem: news-retrieval
tags: [news, adapter, dedup, evidence, fail-closed]
requires: [frozen NewsItem contract, EvidenceStatus vocabulary]
provides: [NewsSourceAdapter interface, empty source registry, outage-to-unavailable path, dedup policy]
affects: [05-02 sentiment assembler, 05-03 graph wiring]
tech-stack:
  added: []
  patterns: [protocol-based adapter, fail-closed coverage, deterministic dedup]
key-files:
  created:
    - src/goldmasters/data/__init__.py
    - src/goldmasters/data/news/__init__.py
    - src/goldmasters/data/news/base.py
    - src/goldmasters/data/news/dedup.py
    - tests/unit/test_news_adapter.py
  modified: []
decisions:
  - "Registry ships empty; sources added only after operator approval (D-5.1)"
  - "Canonical rule pinned: lower scheme/host, strip trackers, single-slash rule"
  - "Published_at passed verbatim; unreliable yields None, never retrieved_at"
status: complete
actuals:
  tokens: 9000
  tasks: 3
  commits: 3
plan_head_before: e29c421
plan_head_after: 02889e3
---

# Phase 05 Plan 01: News Adapter Tracer Summary

Retrieval-adapter interface plus fail-closed outage path per locked D-5.1. No live source wired — the registry ships empty pending operator approval. Nothing synthesized, ever.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Stub-adapter fetch to validated NewsItem list | 6753448 | base.py, news/__init__.py, data/__init__.py |
| 2 | Outage to unavailable coverage, no-synthesis guard | 6753448 | base.py (fetch_coverage) + tests |
| 3 | Dedup collapse plus publication-time integrity pins | 3f2c5d0, 02889e3 | dedup.py, test_news_adapter.py |

Tasks 1+2 share one commit (same `fetch_coverage` path); task 3 split into impl + test commits.

## Verification Evidence

- `uv run pytest tests/unit/test_news_adapter.py -x` → **7 passed**
- `uv run ruff check src/goldmasters/data/news/ tests/unit/test_news_adapter.py` → **clean**
- `uv run mypy src/goldmasters/data/news/` → **strict clean, 3 files**
- `uv run ruff format` applied to new files

## Deviations from Plan

None — plan executed exactly as written.

## Key Decisions

- Empty `SOURCE_REGISTRY` with a `register_source` helper: approval-gated by construction.
- Keyword link targets `XAUUSD` only; narrow by design (a missed link drops a mapping, a loose link fabricates evidence).
- Test-only stub adapter lives in the test file, never in `src/` (AGENTS.md: no mock data in src).
- Committed on `master` per spawn instruction (no worktree/agent branch in this run).

## Known Stubs

None in `src/`. The test-file stub adapter is intentional and permanent as a test double.

## Self-Check: PASSED

- All 5 created files exist on disk.
- All 3 commits (6753448, 3f2c5d0, 02889e3) are ancestors of HEAD.
- No file deletions in task commits; no leftover untracked task files.
