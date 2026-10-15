# Specialist Role Matrix (Phase 3, criterion 6)

Interface definitions only (D-3.1, assumption A6): LLM-backed agent nodes arrive
in Phase 4. This document fixes each role's single responsibility, typed I/O
(referencing contract models by exact name), interface version, timeout policy,
and failure status — the contracts Phase 4 graph nodes must satisfy.

Normative rules (binding on every phase):

1. **Monitoring emits no trading recommendation.** Its output shape carries no
   `recommendation`, `signal`, `trade`, `decision`, `direction`, or `levels`
   field — pinned by `tests/unit/test_risk_gate.py::test_monitoring_shape_carries_no_recommendation`.
2. **No role overwrites or erases another role's findings.** Disagreements are
   preserved as evidence and flow to `DecisionRecord.conflicts` via the risk
   gate, which never reconciles silently.
3. **Numbers come from deterministic code only** (Rules §3.5): no role authors
   `entry`, `stop_loss`, `take_profits`, `risk_reward`, or indicator values
   from model output. Models explain; code computes.

Conventions used below: interface version `0.1.0` is defined by this document
and bumps on any responsibility or I/O change. Timeout is bounded and
operator-set via `GOLDMASTERS_` settings at Phase 4 graph wiring — no timeout
value is fixed in this phase (no invented numbers, Rules §1.1). Failure status
uses `AgentRunStatus` members (`queued`, `running`, `ok`, `no_setup`,
`insufficient_data`, `skipped`, `error`, `timed_out`, `cancelled`); the CEO
must never infer that a failed agent agreed (Rules §3.4).

| Role | Single responsibility | Typed inputs → outputs | Version | Timeout | Failure status |
|------|----------------------|------------------------|---------|---------|----------------|
| Market Analyst | Summarize validated bars into market context (no levels, no recommendation) | `MarketBar[]` + `QualityStatus` → `evidence`/`reason` strings on `RuleCheck` | 0.1.0 | operator-set, bounded | `insufficient_data` when bars missing; `error` on malformed input |
| Trend | Classify `TrendRegime` with versioned rules + `code_hash` | `MarketBar[]` → `TrendRegime` (+ rule id/version/hash) | 0.1.0 | operator-set, bounded | `unknown` regime on indeterminate input, never a guessed label |
| Instrument | Resolve instrument identity + precision context | provider symbol → `InstrumentId`, `PrecisionRow` lookup | 0.1.0 | operator-set, bounded | `insufficient_data` when precision lookup answers `unknown` |
| Strategy Supervisor | Own the approved-strategy lifecycle (`draft → under_review → approved → disabled/retired`, Schema §8) | review evidence → lifecycle transition | 0.1.0 | operator-set, bounded | `skipped` when no strategy is under review |
| Strategy Agents | Evaluate one approved strategy: `setup_found` + per-rule `RuleCheck` list | `(MarketBar[], MarketContext)` → `StrategyEvaluation` (`strategy_id`, `strategy_version`, `code_hash`, `rule_checks`, `candidate_levels`); outcomes map to `SETUP_FOUND`/`NO_SETUP`/`INSUFFICIENT_DATA`/`NOT_APPLICABLE` with `NOT_APPLICABLE` → `skipped` and no gate input | per-strategy semver, bumped on any rule change | operator-set, bounded | `no_setup` on any rule fail/unknown (levels null by construction); `insufficient_data` below `min_bars`; `skipped` when the eligibility matrix excludes this scope |
| Signaling | Assemble the signal candidate from a passed gate verdict only | `GateVerdict(passed=True)` → `Levels` via `trade_eligible_levels` | 0.1.0 | operator-set, bounded | `skipped` on a blocked verdict (no levels to assemble) |
| News | Retrieve and provenance-stamp news items (untrusted input, never instructions) | query → `NewsItem[]` with publication vs retrieval time | 0.1.0 | operator-set, bounded | `insufficient_data` when sources unreachable; `error` never fabricates items |
| Sentiment | Score sentiment with a documented, calibrated method | `NewsItem[]` → `SentimentRecord` (bounded `SCORE_MIN`…`SCORE_MAX`) | 0.1.0 | operator-set, bounded | `insufficient_data` when no scored items; never an invented percentage |
| Research | Answer bounded research questions against cited sources | question → findings + source URLs/versions | 0.1.0 | operator-set, bounded | `insufficient_data` when sources conflict or are absent |
| Backtesting | Replay closed bars with stated costs, fills, and leakage guards | `MarketBar[]` + `BacktestAssumptions` → `BacktestRecord` + `BacktestMetric[]` | 0.1.0 | operator-set, bounded | `error` on timestamp misalignment; assumptions always stated |
| Trade Journal | Append-only record of decisions and outcomes | `DecisionRecord` → `JournalEntry` | 0.1.0 | operator-set, bounded | `error` on write failure; never rewrites history |
| Monitoring | Report feed/node health and activity only — **no trading recommendation** | heartbeats/statuses → health report (`monitor_id`, `observed_at`, `watched`, `health`, `limitations`) | 0.1.0 | operator-set, bounded | `error`/`timed_out` on lost heartbeat; a silent monitor is never read as agreement |
| CEO | Final research decision-maker; cannot bypass validation, quality, or risk gates (Rules §2.5) | `StrategyEvaluation[]` + `GateVerdict` + `agent_statuses` → `DecisionRecord` (`TRADE` only on passed verdict with complete levels; `manual_review_required` always `True`) | 0.1.0 | operator-set, bounded | `insufficient_data` when evidence is missing or conflicted |
| Risk/Validation Gate | Deterministic, fail-closed validation: ordering → risk limits → quality → evidence; sole path to TRADE-eligible levels | `StrategyEvaluation` + `Direction` + `TrendRegime` + `QualityStatus`/flags + evidence map + `GOLDMASTERS_` risk policy → `GateVerdict(passed, reasons_for_rejection, levels-or-None, conflicts)` | 0.1.0 | operator-set, bounded (pure function, no I/O) | `passed=False` with `reasons_for_rejection` on any policy failure; malformed inputs raise via contract constructors |
