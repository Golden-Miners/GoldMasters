# GoldMasters — Product Requirements Document

**Status:** Draft v1.0 — scope confirmed; open questions remain  
**Product:** GoldMasters (the user's brief also says “GoldMaster”; use **GoldMasters** consistently unless renamed)  
**Primary user:** One personal trader  
**V1 scope:** Research and decision support only; no trade execution  
**Initial instruments:** Gold, silver, forex, oil, BTC and ETH, subject to provider/broker symbol availability  
**Preferred stack:** Python, LangGraph, React/Next.js, PostgreSQL, Ollama; local MT5 as one selectable market-data provider  
**Definition of done:** Implement in small verified steps; update task state only after checks pass

## 1. Problem statement

A discretionary trader must reconcile price structure, trend state, strategy conditions, news, sentiment, instrument-specific behaviour, and historical performance before deciding whether a trade is justified. These inputs are often scattered across tools and may conflict. Language-model output can sound confident while relying on stale, missing, or fabricated facts.

GoldMasters aims to assemble evidence from specialist agents into a traceable research brief and an explainable **TRADE / NO TRADE / INSUFFICIENT DATA** decision. It must expose evidence freshness, source provenance, uncertainty, and disagreements rather than conceal them. It is a decision-support product, not a profit guarantee.

## 2. Target-user personas

### Persona A — Discretionary multi-asset trader
- Trades several asset classes and wants one research workspace.
- Needs a quick view of trend, structure, strategy eligibility, news risk, and invalidation.
- Needs entry, stop, targets, rationale, and explicit conditions that would invalidate a setup.
- Rejects opaque “AI confidence” without supporting evidence.

### Persona B — Systematic strategy evaluator
- Wants to compare strategy rules against historical data before trusting a signal.
- Needs reproducible backtests, transaction-cost assumptions, out-of-sample evaluation, and a journal of generated signals.
- Needs to distinguish live observations, historical results, estimates, and unavailable data.

## 3. Goals and non-goals

### Goals
1. Gather live or latest-available market data from explicitly selected providers.
2. Analyse instruments through typed, bounded specialist-agent responsibilities.
3. Give the CEO agent the evidence required to issue TRADE, NO TRADE, or INSUFFICIENT DATA.
4. Explain every decision with citations/references to underlying data, timestamps, rules, and conflicts.
5. Support news/sentiment analysis with source, publication time, retrieval time, and instrument relevance.
6. Record signals and their subsequent outcomes in a journal.
7. Evaluate strategies through reproducible backtesting without claiming future profitability.
8. Provide an operator-visible UI for provider status, freshness, errors, agent outputs, and task history.

### Non-goals for V1
- No placing, modifying, or closing orders; no broker credentials for trading.
- No autonomous execution, copy trading, portfolio management, or guaranteed returns.
- No invented/mock/sample market, news, sentiment, backtest, or signal data in production paths.
- No claim that news sentiment predicts price direction reliably.
- No mandatory multi-user SaaS, billing, mobile app, or social trading.
- No unsupported claim of “perfect analysis,” “zero errors,” or “zero hallucinations.” Controls must reduce and detect errors; they cannot mathematically guarantee their absence.

## 4. User stories

- As a trader, I want to select an instrument and timeframe so that analysis is scoped to the market I intend to trade.
- As a trader, I want to select a market-data provider so that I can control which feed supplies prices and candles.
- As a trader, I want to see provider health and data timestamps so that I can identify stale or incomplete evidence.
- As a trader, I want trend and market-structure states so that I can distinguish continuation, pullback, breakout, momentum, range, and possible reversal.
- As a trader, I want each strategy to report its rule checks so that I can understand why a setup did or did not qualify.
- As a trader, I want relevant news with source links and timestamps so that I can assess event risk.
- As a trader, I want sentiment analysis to show its source coverage and uncertainty so that I do not mistake weak evidence for consensus.
- As a trader, I want the CEO agent to reject a trade when critical evidence is missing or conflicting so that the system does not force a setup.
- As a trader, I want an entry, invalidation/stop, targets, risk/reward calculation, and reasoning for each proposed signal so that I can independently evaluate it.
- As a trader, I want every signal and its evidence stored so that I can review decisions later.
- As a trader, I want reproducible backtests with explicit assumptions so that I can assess a strategy without relying on anecdotes.
- As an operator, I want to inspect agent errors and execution traces so that I can diagnose failures without guessing.

## 5. Feature list by release

### MVP
- Instrument/timeframe selector and provider configuration.
- Provider abstraction and local MT5 market-data adapter.
- Data freshness, integrity, and availability checks.
- LangGraph orchestration with typed state and bounded agent outputs.
- Trend, market analyst, instrument context, strategy, news, sentiment, signal validation, CEO decision, journal, backtest, research, and monitoring roles.
- CEO decision with TRADE / NO TRADE / INSUFFICIENT DATA outcomes.
- Signal detail view with entry/stop/targets only when rule-derived and sufficiently supported.
- News/sentiment evidence with source metadata and links.
- Signal journal and agent run history.
- Backtesting with costs, spread/slippage assumptions, out-of-sample split, and leakage safeguards.
- Ollama model configuration, model health check, and provider/model status.
- Audit logging, tests, security controls, and operational health screen.

### V2
- More provider adapters based on verified API/licensing constraints.
- Multi-timeframe analysis and configurable strategy packs.
- Advanced walk-forward analysis, parameter sensitivity, and regime segmentation.
- Configurable alerts (without order execution).
- Strategy versioning and signal comparison.
- Exportable research reports.

### Later
- Multi-user tenancy and role-based collaboration.
- Cloud deployment and managed data pipelines.
- Optional execution only after a separate product/security/risk review and explicit scope approval; not part of this product brief.
- Portfolio-level exposure and correlation analytics.

## 6. Detailed MVP functional requirements

### 6.1 Instruments and provider selection
- Maintain a canonical instrument identifier separately from provider-specific symbols (for example, broker suffixes must not leak into strategy logic).
- User can choose provider and provider-specific symbol mapping.
- Show the selected provider, symbol, timezone, timeframe, last successful retrieval, latest candle timestamp, and status.
- If a requested instrument/timeframe is unsupported, fail visibly; do not silently substitute another symbol or provider.
- Initial universe includes gold, silver, forex, oil, BTC, and ETH. Exact symbols and venues remain configuration-dependent and must be confirmed against the chosen feed.

### 6.2 Market-data ingestion and validation
- Use a provider interface that returns normalized OHLCV/tick records plus provenance and quality metadata.
- Local MT5 adapter reads from the locally installed MT5 terminal through its supported Python integration. It must not assume every MT5 broker exposes the same symbols or history.
- Validate timestamps, monotonic ordering, duplicate bars, OHLC consistency, missing intervals, numeric finiteness, and provider status.
- Distinguish exchange-traded volume from broker/tick volume where the provider does not expose centralized volume.
- Reject or mark unusable data if freshness or integrity rules fail. Thresholds must be configurable per instrument/timeframe and documented; do not invent a universal threshold.
- Store raw provider metadata separately from normalized candles where practical.

### 6.3 LangGraph orchestration
- Use an explicit graph with typed state, declared nodes, conditional edges, bounded retries, timeouts, and a final decision node.
- Specialist agents return schema-validated structured outputs; free-form text is explanatory, not the source of truth for numeric fields.
- Parallelize independent evidence collection where safe; join at a validation barrier before CEO decision.
- Every run receives a run ID, input snapshot/reference, configuration/version identifiers, timestamps, and per-node status.
- Prevent a node from silently changing another agent's findings. Conflicts are preserved and passed to the CEO.
- Retry transient provider failures only within configured limits. Do not retry deterministic validation failures endlessly.
- If a critical node fails, the graph returns INSUFFICIENT DATA or NO TRADE according to the documented failure policy, never an unqualified trade.

### 6.4 Specialist agent responsibilities
- **Market Analyst:** structure, swing points, support/resistance or supply/demand zones when defined by versioned rules; cite candle ranges and timestamps.
- **Trend Agent:** classify trend/range and states such as breakout, pullback, momentum, continuation, or possible reversal using explicit rules and timeframe.
- **Instrument Agent:** instrument specifications, trading sessions, tick/point value where available, contract characteristics, and feed-specific caveats. Missing metadata must be marked unknown.
- **Strategy Supervisor:** selects eligible strategy agents based on instrument, timeframe, regime, and configuration; records all rule checks.
- **Strategy Agents:** each implement one named, versioned strategy. Return setup/no-setup and rule-by-rule evidence. Do not fabricate entries to fill output.
- **News Analyst:** retrieve relevant news from permitted sources/providers; preserve original title, publisher, published time, retrieval time, URL, and extracted claims. Respect robots, terms, rate limits, and API terms.
- **Sentiment Agent:** summarize source-backed sentiment and coverage; separate source statements from model interpretation; flag low sample size, duplicates, and conflicting sources.
- **Signaling Agent:** converts validated strategy proposals into a standardized candidate signal; computes levels only from defined rules and data; validates stop/target ordering and risk/reward.
- **CEO Agent:** decision authority for the research workflow. Applies hard gates, reviews agent outputs and conflicts, and emits TRADE, NO TRADE, or INSUFFICIENT DATA with reasons. It cannot override hard data-quality or risk gates by narrative persuasion.
- **Research Agent:** investigates strategies, instrument behaviour, and relevant methodology using cited sources; proposals are not promoted to live strategies without review and tests.
- **Backtesting Agent:** runs deterministic historical tests using versioned strategy code, point-in-time data, costs, and explicit assumptions. No look-ahead or survivorship shortcuts.
- **Trade Journal Agent:** stores signals and later observed outcomes; never rewrites the original decision record.
- **Monitoring Agent:** watches provider freshness, node failures, latency, schema failures, and system health; it does not generate trading recommendations.
- **Risk/Validation Gate:** validates level ordering, configured risk limits, data quality, and required evidence before CEO decision. Risk limits remain unresolved configuration until explicitly chosen.

### 6.5 CEO decision contract
Required decision fields:
- `decision`: `TRADE`, `NO_TRADE`, or `INSUFFICIENT_DATA`.
- `instrument`, `timeframe`, `direction` (nullable unless TRADE), `created_at`, `run_id`.
- `evidence_refs`, `agent_statuses`, `conflicts`, `data_quality_status`.
- `entry`, `stop_loss`, `take_profits`, `risk_reward` only when derived and validated; otherwise null.
- `thesis`, `invalidation_conditions`, `risk_factors`, `reasons_for_rejection`, `limitations`.
- `strategy_id` and `strategy_version` when applicable.
- `model_id` may be recorded for provenance but cannot be used as proof of correctness.

A TRADE decision is permitted only when required evidence is present, current under configured policy, schema-valid, strategy-qualified, and risk-validated. A missing critical input must not be filled by an LLM guess. Confidence scores, if displayed, must be defined and calibrated; otherwise omit them.

### 6.6 News and sentiment
- Use free/reputed sources only where access is permitted and stable. Candidate sources such as Forex Factory and CoinDesk are not guaranteed to provide an unrestricted API; verify access, licensing, terms, and reliability before implementation.
- Never scrape behind login, bypass access controls, or assume that a public webpage grants permission for bulk collection.
- News is not “live” merely because a page was fetched recently. Show publication and retrieval timestamps separately.
- Deduplicate articles by canonical URL and similarity policy; preserve original source attribution.
- If news cannot be retrieved, label coverage unavailable. Do not synthesize headlines or sentiment.
- Map news to instruments through explicit entity/keyword mappings and show mapping uncertainty.

### 6.7 UI and reports
- React/Next.js frontend; backend API owns orchestration and persistence.
- Screens: Overview, Instrument Workbench, Decision/Signal Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health, and System Health.
- Display evidence freshness and status near every decision.
- Clearly distinguish observed facts, deterministic calculations, strategy outputs, and LLM interpretations.
- Provide source links and expandable reasoning traces; avoid exposing secrets, raw prompts containing sensitive data, or uncontrolled internal chain-of-thought. Provide concise evidence-based rationale instead.

### 6.8 Journal and backtesting
- Journal immutable decision snapshots and append outcome observations.
- Backtests must declare dataset, date range, timezone, timeframe, symbol mapping, strategy version, parameter set, spread/commission/slippage assumptions, and fill model.
- Separate in-sample development from validation/out-of-sample results. Report missing data and excluded periods.
- Metrics are computed by code and tested; LLMs may explain results but must not invent or recalculate authoritative metrics in prose.
- Historical performance is not a guarantee of future performance.

### 6.9 Local model support
- Ollama is the preferred local model runtime.
- Configure base URL, model name, timeout, context limit where known, and health status without hardcoding assumptions about installed models.
- On model unavailable/timeout/schema-invalid output, follow bounded retry/fallback policy and fail closed for critical decisions.
- Never claim a model is installed or tested until runtime discovery or a health check confirms it.
- Use deterministic code for arithmetic, schema validation, and risk gates.

## 7. Data model sketch

- `Instrument`: canonical ID, asset class, display name, provider symbol mappings, specification status.
- `Provider`: provider ID, type, enabled flag, config reference (secrets excluded), capabilities, health status.
- `MarketBar`: instrument ID, provider ID, timeframe, open/high/low/close, volume, volume type, bar timestamp, retrieval timestamp, quality flags.
- `NewsItem`: source ID, URL, title, published timestamp, retrieved timestamp, content hash, instrument mappings, provenance.
- `SentimentAssessment`: source set, instrument, timeframe/window, sentiment label/score if method is defined, coverage count, limitations, model/version.
- `Strategy`: ID, name, version, code/config hash, supported instruments/timeframes/regimes, lifecycle status.
- `AgentRun`: run ID, graph version, configuration hash, start/end times, status, node statuses, error summary.
- `AgentEvidence`: run ID, agent name/version, typed payload, evidence references, status, timestamps.
- `SignalDecision`: decision ID, run ID, instrument/timeframe, decision, direction, levels, thesis, rejection reasons, risk checks, created timestamp.
- `JournalOutcome`: decision ID, observation time, outcome fields, methodology/version; append-only.
- `BacktestRun`: dataset references, strategy version, parameter hash, assumptions, date splits, metrics, status.
- `AuditEvent`: actor/service, event type, resource reference, timestamp, correlation ID, redacted metadata.
- `ModelConfig`: provider/runtime, model identifier, configuration reference, availability and test status.

Exact SQL types, indexes, retention periods, and migrations are implementation decisions to be recorded in `Schema.md` and Architecture ADRs.

## 8. Edge cases and failure states

- MT5 terminal closed, disconnected, logged out, or missing requested history.
- Broker symbol aliases, suffixes, contract differences, market closures, and timezone/session mismatch.
- Stale, duplicated, malformed, missing, or out-of-order candles.
- Provider disagreement or price gaps across feeds.
- Instrument is not tradable at the broker or lacks necessary contract metadata.
- News source is unavailable, blocks access, changes markup, duplicates stories, or provides ambiguous timestamps.
- Sentiment sources are sparse, coordinated, contradictory, or unrelated to the selected instrument.
- Ollama is unavailable, model is absent, model output fails schema validation, or context is insufficient.
- Agent timeout, partial graph failure, retry exhaustion, or conflicting findings.
- Strategy has no setup; system must return no setup rather than force a signal.
- Stop/target invalid ordering, zero/negative risk distance, impossible tick increments, or risk/reward below configured minimum.
- Backtest data leakage, insufficient history, missing bars, unrealistic fills, or cost assumptions unavailable.
- Duplicate run requests, concurrent writes, database outage, migrations failing, or partial persistence.
- UI must distinguish no result, no setup, provider unavailable, and application error.

## 9. Success metrics

Metrics must be instrumented before targets are set. Do not invent targets before baseline measurement.
- **Data integrity:** percentage of bars passing validation; number and duration of stale-feed incidents.
- **Decision traceability:** percentage of decisions with complete evidence references and configuration/version metadata.
- **Fail-closed compliance:** count of trade candidates blocked when required evidence is missing or invalid; test coverage of gate behaviour.
- **Operational reliability:** graph completion/failure rates, node latency distributions, retry exhaustion, and API error rates.
- **Reproducibility:** identical inputs/configuration produce identical deterministic strategy/risk outputs.
- **Backtest integrity:** tests for look-ahead leakage, cost inclusion, and correct train/validation/out-of-sample separation.
- **User utility:** time to review a decision, journal completeness, and user-rated clarity measured after use.
- **Signal quality:** measured only over a predeclared evaluation protocol with sample size, costs, drawdown, uncertainty, and out-of-sample data. No performance claim before evidence.

## 10. Open questions

1. Which exact broker/MT5 terminal and symbol names will be used?
2. Which timeframe set is required for V1?
3. What freshness thresholds apply per asset class/timeframe?
4. Which news sources can be accessed lawfully and reliably without paid APIs?
5. Which Ollama models are installed, and what hardware/context limits apply?
6. Which strategies are in the initial approved strategy registry?
7. What explicit risk gates should block a candidate (maximum risk per setup, minimum reward/risk, session restrictions, news blackout, etc.)?
8. Is the app strictly single-user/local, or should authentication be included from day one?
9. What retention and backup policy applies to market data, evidence, and journal records?
10. Which deployment target and operating system will host the backend/database?
11. Should “TRADE” mean “candidate worth considering” in the UI? Recommended wording: **Qualified setup — manual review required**, to avoid implying execution.
12. What evidence is sufficient to approve a research-discovered strategy for production use?
