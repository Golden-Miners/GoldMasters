# Phase 5: News, Sentiment and CEO Decision Contract — CONTEXT

**Discussed:** 2026-10-16 (3 gray areas, operator-locked)
**Inputs:** 05-RESEARCH.md (HIGH), operator answers

## Locked decisions

1. **Adapter interface first (D-5.1).** Build the retrieval-adapter interface +
   outage→`unavailable` coverage path now. No live source wired until operator
   approves access method + terms. Never synthesize headlines or sentiment.
2. **Scoreless evidence (D-5.2).** Sentiment carries source statements, window,
   coverage counts, conflicts, limitations, model version. No score field populated
   until a versioned scoring method is approved. Score-gating tests assert absence.
3. **Roles as graph nodes (D-5.3).** Wire analyst/news-sentiment/research roles as
   bounded async graph nodes through the pre-CEO barrier. Closes Phase 4 O-1 in the
   same wave. Spine semantics unchanged: failed required agent blocks prose.

## Already exists (reuse, don't rebuild)

- `NewsItem`, `SentimentRecord`, `DecisionRecord` frozen contracts (Phase 1 01-11).
- `assemble_decision` sole constructor, `check_barrier`, `check_ceo_required` (Phase 4).

## Phase 5 build (new)

- Retrieval-adapter interface + `unavailable` path; TRADE conjunction test
  (evidence present + current + valid + strategy-qualified + risk-validated);
  decision traceability metric (% decisions with complete evidence refs).

## Open (operator-owned)

- News source approvals + terms; T0004; ~40 strategy thresholds.

## Next

Planner creates PLAN.md files against D-5.1…D-5.3. Do not re-ask locked items.
