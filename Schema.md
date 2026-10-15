# GoldMasters — Shared Schema and Naming Conventions

**Status:** Contract proposal v1.0. Treat as canonical only after review and implementation tests.

## 1. General conventions

- Python identifiers: `snake_case`; TypeScript variables/functions: `camelCase`; types/classes: `PascalCase`.
- JSON keys use `snake_case` to match API/domain models consistently.
- SQL tables and columns use `snake_case`; primary keys are explicit and stable.
- Every timestamp is ISO 8601 with timezone/UTC offset. Internally normalize instants to UTC; preserve source timezone when meaningful.
- Never store a timezone-naive timestamp for market events.
- Currency/price precision must follow instrument/provider metadata; do not assume all instruments share decimal precision.
- Do not use binary floating point as the sole authoritative representation for money/price arithmetic where exact tick alignment matters. Define Decimal/tick quantization rules.
- Missing value is `null` only when the field is nullable. Unknown, unavailable, not applicable, and failed are different semantic states.
- No magic status strings outside enums.
- Add `schema_version` to persisted agent payloads and externally exchanged contracts.
- All external/model/provider input is untrusted until validated.
- Do not include secrets in schemas, logs, traces, or examples.

## 2. Enumerations

### Decision
- `TRADE`
- `NO_TRADE`
- `INSUFFICIENT_DATA`

In the UI, explain that `TRADE` means a qualified research candidate requiring manual review; it does not execute an order.

### Agent/run status
- `queued`
- `running`
- `ok`
- `no_setup`
- `insufficient_data`
- `skipped`
- `error`
- `timed_out`
- `cancelled`

### Evidence status
- `valid`
- `stale`
- `missing`
- `conflicted`
- `invalid`
- `unavailable`

### Direction
- `long`
- `short`
- `neutral`
- `unknown`

### Trend/regime state
- `uptrend`
- `downtrend`
- `range`
- `breakout`
- `pullback`
- `momentum`
- `continuation`
- `possible_reversal`
- `unknown`

These labels require documented, versioned classification rules; labels must not be generated solely from an unconstrained LLM.

## 3. Standard agent envelope

```json
{
  "schema_version": "1.0",
  "run_id": "UUID",
  "agent_name": "trend_agent",
  "agent_version": "semver-or-commit-reference",
  "status": "ok",
  "created_at": "ISO-8601-with-timezone",
  "as_of": "ISO-8601-with-timezone-or-null",
  "input_refs": [],
  "evidence_refs": [],
  "limitations": [],
  "error": null,
  "result": {}
}
```

The strings above describe formats, not real IDs or sample market data. Production output must use generated real identifiers and actual results. `error` is a structured sanitized error object when status indicates failure.

## 4. Market data contract

### Market bar
Required fields:
- `instrument_id`
- `provider_id`
- `provider_symbol`
- `timeframe`
- `bar_open_time`
- `bar_close_time` if the provider exposes or the system can deterministically derive it
- `open`, `high`, `low`, `close`
- `volume` nullable
- `volume_type`: `tick`, `exchange`, `broker`, `unknown`, or `not_available`
- `retrieved_at`
- `source_timezone` if known
- `quality_status` and `quality_flags`

Validation invariants:
- All required prices are finite and positive unless the instrument's documented contract permits otherwise.
- `high >= max(open, close, low)` and `low <= min(open, close, high)`.
- Timestamps are ordered and aligned to the declared timeframe according to provider semantics.
- Duplicates and gaps are flagged, not silently removed without audit.
- Provider volume semantics are preserved; never relabel tick volume as centralized exchange volume.

### Quote
- `instrument_id`, `provider_id`, `provider_symbol`
- bid/ask and their timestamps when provided
- last price and timestamp when provided
- spread only when derived from valid bid/ask
- `retrieved_at`, `quality_status`

Do not invent missing bid, ask, last price, or volume.

## 5. Provider contract

```text
MarketDataProvider
  provider_id
  display_name
  capabilities
  health_check()
  get_bars(instrument_id, provider_symbol, timeframe, start, end)
  get_latest_quote(instrument_id, provider_symbol)
  get_instrument_spec(instrument_id, provider_symbol)
```

- All methods return typed results with provenance and explicit errors.
- Provider-specific symbols must not become canonical instrument IDs.
- Provider selection must be recorded in each run.
- No automatic fallback unless the user explicitly configures it and the run records the switch.
- Secrets are referenced through a secret/config mechanism; they are not part of returned metadata.

## 6. Signal decision contract

Required fields:
- `decision_id`, `run_id`, `instrument_id`, `timeframe`
- `decision` enum
- `direction` nullable unless `TRADE`
- `created_at`, `data_as_of`
- `strategy_id`, `strategy_version` nullable if no strategy applies
- `entry`, `stop_loss`, `take_profits` nullable unless validated
- `risk_reward` nullable unless computable
- `thesis`
- `invalidation_conditions`
- `risk_factors`
- `reasons_for_rejection`
- `evidence_refs`
- `agent_statuses`
- `conflicts`
- `data_quality_status`
- `limitations`
- `manual_review_required` must be `true` for every V1 decision

Invariants:
- A `TRADE` candidate cannot be emitted if critical data is missing/stale under policy, required agents fail, strategy rules do not qualify, or risk gates fail.
- Long/short level ordering must be validated against the defined order type/strategy model.
- Targets and risk/reward are derived by deterministic code.
- If any level is unknown or invalid, it must remain null and the decision cannot be represented as a qualified trade.
- Decision record is immutable; corrections create a superseding record with a reason.

## 7. News item and sentiment contract

### News item
- `source_id`, `canonical_url`, `title`
- `published_at` nullable when source does not provide a reliable timestamp
- `retrieved_at`
- `content_hash`
- `instrument_mappings` with mapping rationale and confidence method
- `source_attribution`
- `access_method`
- `status`, `limitations`

Do not treat retrieval time as publication time. Do not store or republish source content beyond allowed terms.

### Sentiment assessment
- `instrument_id`, analysis window, `created_at`
- source/evidence references
- coverage count, unique-source count, duplicate policy
- sentiment label/score only if the scoring method is defined and versioned
- conflicts, limitations, model/version

Sentiment is contextual evidence, not a deterministic price prediction.

## 8. Strategy contract

- `strategy_id`, `name`, `version`
- `code_hash` or immutable code reference
- supported instruments/timeframes/regimes
- parameters with schema and defaults
- rule definitions and rule version
- `status`: draft, under_review, approved, disabled, retired
- test evidence and backtest references

Each strategy evaluation returns:
- `setup_found`
- `rule_checks` with rule ID, pass/fail/unknown, inputs/evidence, reason
- candidate levels only when produced by defined rules
- limitations and strategy version

A strategy cannot become approved because an LLM recommends it; require explicit review and tests.

### Strategy evaluation protocol (Phase 3.1 framework)

Every approved agent implements `evaluate(bars, ctx)` — the only strategy
entry point. `bars` are the sole price input (closed bars only); `ctx` is a
`MarketContext` carrying non-price context only: `instrument_id`,
`provider_id`, `timeframe`, `regime`, `quality_status`, `quality_flags`,
`volume_type` (tick is never relabelled exchange), `tick_size` /
`contract_size` as decimal strings (`None` means unknown — skip alignment,
never a default), `bar_count`, and `now_utc`. No price or volume data lives
in `ctx`.

Agent outcomes map to exactly one adapter status with the locked table:

| Adapter status | `StrategyEvaluation` | agent/run status | Gate input? |
|---|---|---|---|
| `SETUP_FOUND` | `setup_found=True` + levels (validator-enforced) | `ok` | Yes — candidate flows to `evaluate_gate` |
| `NO_SETUP` | `setup_found=False`, null levels | `no_setup` | No (recorded with rule_checks) |
| `INSUFFICIENT_DATA` | `setup_found=False`, null levels, reason cites cause | `insufficient_data` | No |
| `NOT_APPLICABLE` | `setup_found=False`, null levels, reason cites scope mismatch | `skipped` | No — never reaches gate |

Any rule fail or unknown still means no setup and null levels — the
`StrategyEvaluation` validator is unchanged and every state satisfies it.
The agent/run status enum gains no new member: `NOT_APPLICABLE` maps to the
verbatim `skipped` member.

Agent selection uses the eligibility matrix (`EligibilityRule` per agent:
`strategy_id`, `enabled`, `instruments`, `timeframes`, `regimes`,
`min_bars`): disabled rows yield `disabled`; any instrument/timeframe/regime
mismatch yields `not_applicable` (an empty instrument list means none, never
all). Bar count never excludes — below `min_bars` the agent reports
`INSUFFICIENT_DATA` at evaluate time. Matrix values arrive via declared
`GOLDMASTERS_STRATEGY_<ID>_*` settings; every key is declared or startup
rejects it. Agents import `strategies/base`, `domain.*` and
`risk.levels.build_candidate_levels` only — never each other.

## 9. Backtest contract

- `backtest_run_id`, strategy ID/version, dataset reference/hash
- instrument, timeframe, start/end, timezone
- data-quality report
- parameter hash
- spread/commission/slippage/fill assumptions
- in-sample, validation and out-of-sample boundaries
- metrics with definitions and sample size
- generated timestamp, code version, status and errors

Metrics are calculated in deterministic code. Any report must show assumptions and sample period. Never claim a result without its run and dataset reference.

## 10. Error contract

```json
{
  "code": "STABLE_MACHINE_READABLE_CODE",
  "message": "Sanitized user-facing description",
  "retryable": false,
  "correlation_id": "UUID",
  "details": null
}
```

- `message` must not expose secrets, SQL, stack traces, local paths, tokens, or full provider responses.
- `details` are schema-limited and redacted.
- Retryability is determined by code, not by model judgement.
- Internal diagnostics may retain stack traces only in access-controlled logs with redaction.

## 11. Naming and formatting

- Files: lowercase or established PascalCase names consistently; the nine user-requested Markdown filenames retain exact casing.
- Agent modules: `<agent_name>_agent.py` or a consistent package convention selected during implementation.
- Tests: `test_<module_or_behaviour>.py`.
- Environment variables: uppercase with product prefix where appropriate, e.g. `GOLDMASTERS_...`; never commit actual secret values.
- IDs: UUID or another documented stable identifier; no sequential public IDs where enumeration creates risk.
- Units must be explicit in field names or metadata (e.g. seconds, ticks, price currency). Avoid ambiguous names such as `points` unless the instrument convention is documented.
- JSON must be valid UTF-8 JSON; no comments, trailing commas, NaN, or Infinity.
- API schemas and database migrations must evolve deliberately; breaking changes increment schema/API version and include migration tests.

## 12. Unresolved schema decisions

- Decimal precision and tick quantization per instrument/provider.
- Exact timeframe enum and candle boundary semantics.
- Freshness policy by instrument/timeframe.
- Stable identifier strategy and retention.
- Whether to persist full candles or references to external datasets.
- News-content retention limits.
- Exact API versioning convention.
