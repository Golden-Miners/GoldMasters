# Requirements (synthesized)

Provenance: derived from PRD-classified documents. Precedence ADR > SPEC > PRD > DOC.

PRD-classified documents found: 1 (Prd.md, confidence high)
Requirement IDs are derived as `REQ-{slug}` from the source PRD's own section structure.
Acceptance conditions are taken from the source document; where the source states a
condition, it is reproduced; nothing is invented.

---

## REQ-instrument-provider-selection
- source: Prd.md (§6.1 Instruments and provider selection)
- description: Maintain a canonical instrument identifier separately from provider-specific symbols (broker suffixes must not leak into strategy logic). User selects provider and provider-specific symbol mapping. Show selected provider, symbol, timezone, timeframe, last successful retrieval, latest candle timestamp, and status.
- acceptance: If a requested instrument/timeframe is unsupported, fail visibly — never silently substitute another symbol or provider. Initial universe includes gold, silver, forex, oil, BTC and ETH; exact symbols and venues remain configuration-dependent and must be confirmed against the chosen feed.
- scope: instruments, provider selection, symbol mapping

## REQ-market-data-ingestion-validation
- source: Prd.md (§6.2 Market-data ingestion and validation)
- description: A provider interface returns normalized OHLCV/tick records plus provenance and quality metadata. The local MT5 adapter reads from the locally installed MT5 terminal through its supported Python integration and must not assume every broker exposes the same symbols or history. Validate timestamps, monotonic ordering, duplicate bars, OHLC consistency, missing intervals, numeric finiteness, and provider status.
- acceptance: Distinguish exchange-traded volume from broker/tick volume. Reject or mark unusable data if freshness or integrity rules fail; thresholds must be configurable per instrument/timeframe and documented — no universal threshold may be invented. Store raw provider metadata separately from normalized candles where practical.
- scope: market data ingestion and validation

## REQ-langgraph-orchestration
- source: Prd.md (§6.3 LangGraph orchestration)
- description: Explicit graph with typed state, declared nodes, conditional edges, bounded retries, timeouts and a final decision node. Specialist agents return schema-validated structured outputs (free-form text is explanatory, not authoritative for numeric fields). Parallelize independent evidence collection where safe; join at a validation barrier before CEO decision.
- acceptance: Every run receives a run ID, input snapshot/reference, configuration/version identifiers, timestamps and per-node status. No node may silently change another agent's findings — conflicts are preserved and passed to the CEO. Retry transient provider failures only within configured limits. If a critical node fails, the graph returns INSUFFICIENT DATA or NO TRADE per the documented failure policy — never an unqualified trade.
- scope: orchestration

## REQ-specialist-agent-responsibilities
- source: Prd.md (§6.4 Specialist agent responsibilities)
- description: Bounded, typed specialist roles: Market Analyst, Trend Agent, Instrument Agent, Strategy Supervisor, Strategy Agents, News Analyst, Sentiment Agent, Signaling Agent, CEO Agent, Research Agent, Backtesting Agent, Trade Journal Agent, Monitoring Agent, and Risk/Validation Gate.
- acceptance: Each agent reports rule-by-rule evidence (e.g. strategy `rule_checks`); the Signaling Agent computes levels only from defined rules and data and validates stop/target ordering and risk/reward; agents must not fabricate entries to fill output; missing metadata is marked unknown; Monitoring generates no trading recommendations; Risk/Validation Gate enforces level ordering, configured risk limits, data quality and required evidence before CEO decision.
- scope: specialist agents

## REQ-ceo-decision-contract
- source: Prd.md (§6.5 CEO decision contract)
- description: CEO Agent emits TRADE / NO_TRADE / INSUFFICIENT_DATA with required fields: decision, instrument, timeframe, direction (nullable unless TRADE), created_at, run_id, evidence_refs, agent_statuses, conflicts, data_quality_status, entry/stop_loss/take_profits/risk_reward (only when derived and validated, else null), thesis, invalidation_conditions, risk_factors, reasons_for_rejection, limitations, strategy_id/strategy_version (when applicable); model_id may be recorded for provenance but cannot prove correctness.
- acceptance: A TRADE decision is permitted only when required evidence is present, current under configured policy, schema-valid, strategy-qualified and risk-validated. A missing critical input must not be filled by an LLM guess. Confidence scores, if displayed, must be defined and calibrated — otherwise omit them. The CEO cannot override hard data-quality or risk gates by narrative persuasion.
- scope: CEO decision contract

## REQ-news-and-sentiment
- source: Prd.md (§6.6 News and sentiment)
- description: News Analyst retrieves relevant news from permitted sources/providers, preserving original title, publisher, published time, retrieval time, URL and extracted claims. Sentiment Agent summarizes source-backed sentiment and coverage, separating source statements from model interpretation and flagging low sample size, duplicates and conflicting sources.
- acceptance: Use free/reputed sources only where access is permitted and stable; verify access, licensing, terms and reliability before implementation. Never scrape behind login, bypass access controls, or assume a public page grants bulk-collection permission. Show publication and retrieval timestamps separately. Deduplicate by canonical URL and similarity policy, preserving source attribution. If news cannot be retrieved, label coverage unavailable — do not synthesize headlines or sentiment. Map news to instruments through explicit entity/keyword mappings and show mapping uncertainty.
- scope: news, sentiment

## REQ-ui-and-reports
- source: Prd.md (§6.7 UI and reports)
- description: React/Next.js frontend with the backend API owning orchestration and persistence. Screens: Overview, Instrument Workbench, Decision/Signal Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health, and System Health.
- acceptance: Display evidence freshness and status near every decision. Clearly distinguish observed facts, deterministic calculations, strategy outputs and LLM interpretations. Provide source links and expandable reasoning traces; avoid exposing secrets, raw prompts containing sensitive data, or uncontrolled internal chain-of-thought.
- scope: UI, reports

## REQ-journal-and-backtesting
- source: Prd.md (§6.8 Journal and backtesting)
- description: Journal immutable decision snapshots and append outcome observations. Backtests must declare dataset, date range, timezone, timeframe, symbol mapping, strategy version, parameter set, spread/commission/slippage assumptions and fill model.
- acceptance: Separate in-sample development from validation/out-of-sample results; report missing data and excluded periods. Metrics are computed by code and tested; LLMs may explain results but must not invent or recalculate authoritative metrics in prose. Historical performance is not a guarantee of future performance.
- scope: journal, backtesting

## REQ-local-model-support
- source: Prd.md (§6.9 Local model support)
- description: Ollama as the preferred local inference runtime; configure endpoint and model with model health check and provider/model status; discover available models at runtime.
- acceptance: Do not assume a model name, hardware capability or context window. All model output is untrusted until schema-validated and checked against evidence references. Use deterministic code for prices, indicator values, risk/reward arithmetic, validation and gates. Record model availability and test status (ModelConfig).
- scope: local models

## REQ-no-trade-execution
- source: Prd.md (§3 Goals and non-goals)
- description: V1 must not place, modify or close orders; no broker credentials for trading; no autonomous execution, copy trading or portfolio management.
- acceptance: No order-placement/modification/closure code or endpoints exist. A `TRADE` result is a qualified research candidate requiring manual review — not an order.
- scope: product boundary

## REQ-no-fabricated-data
- source: Prd.md (§3 Goals and non-goals; §1 Problem statement)
- description: No invented/mock/sample market, news, sentiment, backtest or signal data in production paths.
- acceptance: Missing or unavailable data is labelled as such (never synthesized). No unsupported claim of “perfect analysis”, “zero errors” or “zero hallucinations”; controls reduce and detect errors and failures are measured honestly.
- scope: data integrity

## REQ-evidence-and-provenance
- source: Prd.md (§1 Problem statement; §3 Goals 1–8)
- description: Assemble evidence from specialist agents into a traceable research brief; explain every decision with citations/references to underlying data, timestamps, rules and conflicts; expose evidence freshness, source provenance, uncertainty and disagreements.
- acceptance: Decision traceability metric = percentage of decisions with complete evidence references and configuration/version metadata; metrics must be instrumented before targets are set (no invented targets before baseline measurement).
- scope: traceability
