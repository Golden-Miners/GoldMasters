---
phase: 05-news-sentiment-ceo
plan: 02
subsystem: news-sentiment
tags: [sentiment, scoreless-evidence, D-5.2, criterion-3]
requires: [05-01]
provides: [scoreless-sentiment-assembler, score-absence-gate]
affects: [05-03, ceo-decision-contract]
tech-stack:
  added: []
  patterns: [deterministic-assembler, frozen-contract-validation, fail-closed-outage]
key-files:
  created: [src/goldmasters/data/news/sentiment.py, tests/unit/test_news_sentiment.py]
  modified: [src/goldmasters/data/news/__init__.py]
decisions: []
metrics:
  duration: "25 min"
  completed: "2026-10-16"
status: complete
actuals:
  tokens: 2800
  tasks: 3
  commits: 2
plan_head_before: 02889e3
plan_head_after: b564592
commits: 2
---

# Phase 5 Plan 02: Scoreless Sentiment Evidence Summary

Deterministic scoreless sentiment-evidence assembler per locked decision D-5.2: source statements, window, coverage counts, conflicts, limitations and model version — score stays `None` until a versioned scoring method is approved. No scoring method invented.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | End-to-end collapsed coverage to validated scoreless SentimentRecord | 962ec32 | src/goldmasters/data/news/sentiment.py, src/goldmasters/data/news/__init__.py |
| 2 | Score-absence gate plus unavailable and stale coverage paths | b564592 | tests/unit/test_news_sentiment.py |
| 3 | Conflicts, limitations and source-vs-interpretation separation pins | b564592 | tests/unit/test_news_sentiment.py |

Tasks 2 and 3 ship in one test commit: all pins live in a single test module verified by one suite run, so splitting the file across two commits would have been artificial. Each task's done-criterion was verified by the suite.

## Key Decisions

None — plan executed exactly as written; D-5.2 already locked all design choices (scoreless, no label vocabulary, no freshness threshold).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `model_copy(update=...)` skips Pydantic validation**
- **Found during:** Task 2 (score-absence gate test)
- **Issue:** `record.model_copy(update={"score": 1.5})` did not raise `ValidationError` — `model_copy` bypasses validators, so the out-of-range rejection test failed with DID NOT RAISE.
- **Fix:** Revalidate via `SentimentRecord.model_validate({**record.model_dump(), **overrides})` in the test helper. This also more faithfully tests the real ingestion path (fresh validation, not in-memory mutation).
- **Files modified:** tests/unit/test_news_sentiment.py
- **Commit:** b564592

**2. [Rule 3 - Blocking] `NewsItem.status` requires `EvidenceStatus` instance**
- **Found during:** Task 1 (test fixture construction)
- **Issue:** String `"valid"` rejected by contract (`is_instance_of`); fixtures used `EvidenceStatus.VALID` instead.
- **Fix:** Import `EvidenceStatus` and use `EvidenceStatus.VALID` in the fixture helper.
- **Files modified:** tests/unit/test_news_sentiment.py
- **Commit:** b564592

## Verification

- `uv run pytest tests/unit/test_news_sentiment.py tests/unit/test_news_adapter.py -q` — 15 passed (8 new + 7 adapter, no regressions).
- `uv run ruff check src/goldmasters/data/news/ tests/unit/test_news_sentiment.py` — clean.
- `uv run mypy --strict src/goldmasters/data/news/` — clean, 4 files.
- Post-commit deletion check: no deletions.

## Threat Flags

None — no new surface beyond the plan's threat model. T-05-04 mitigated (score/label hard-coded `None`; contract validator rejects method-less and out-of-range scores); T-05-05 mitigated (every source_ref is a contributing item's canonical URL); T-05-SC holds (no new packages; stdlib + frozen contracts only).

## Known Stubs

None.

## Self-Check: PASSED

- `src/goldmasters/data/news/sentiment.py` FOUND; `tests/unit/test_news_sentiment.py` FOUND.
- Commits 962ec32 and b564592 are ancestors of HEAD.
