# Requirements: GoldMasters

**Defined:** 2026-10-13 (from ingest synthesis of 10 documents; all 12 requirements sourced from `Prd.md`)
**Core Value:** Every output is traceable to real, timestamped market data with provenance; nothing is fabricated, and the system fails closed to NO_TRADE or INSUFFICIENT_DATA when evidence is missing or stale.

Requirement IDs are carried verbatim from the PRD's own section structure (`REQ-{slug}`). Acceptance conditions are reproduced from the source document; nothing is invented.

## v1 Requirements

Requirements for the initial release. Each maps to exactly one roadmap phase (see Traceability).

### Instruments & Provider Selection

- [ ] **REQ-instrument-provider-selection** — Maintain a canonical instrument identifier separately from provider-specific symbols (broker suffixes must not leak into strategy logic); the operator selects provider and provider-specific symbol mapping; the system shows selected provider, symbol, timezone, timeframe, last successful retrieval, latest candle timestamp and status.
  - **Acceptance:** If a requested instrument/timeframe is unsupported, fail visibly — never silently substitute another symbol or provider. Initial universe includes gold, silver, forex, oil, BTC and ETH; exact symbols and venues remain configuration-dependent and must be confirmed against the chosen feed. *(Prd.md §6.1)*

### Market Data

- [ ] **REQ-market-data-ingestion-validation** — A provider interface returns normalized, provenance-stamped bars/quotes, and every retrieval is validated.
  - **Acceptance:** Validate timestamps, ordering, duplicates, gaps, OHLC invariants, finite values, freshness and volume semantics; preserve `volume_type` (never relabel tick/broker volume as exchange volume); attach `quality_status`/`quality_flags`; allow configured, documented freshness thresholds per instrument/timeframe (no invented defaults). **Source:** Prd.md §6.2; Schema.md §4 (C-04); Rules.md R-04.

- [ ] **REQ-langgraph-orchestration** — A bounded, typed LangGraph workflow coordinates the team with recorded run identity and fail-closed behaviour.
  - **Acceptance:** Typed graph state, explicit conditional edges, bounded retries/timeouts, checkpointing and per-run metadata (`run_id`, input snapshot/refs, config/version identifiers, timestamps, per-node status); a validation barrier precedes the CEO decision; a critical-node failure yields `INSUFFICIENT_DATA` or `NO_TRADE` — never an unqualified `TRADE`. **Source:** Prd.md §6.3; C-03; DR-10; Rules.md R-03.

- [ ] **REQ-specialist-agent-responsibilities** — Bounded specialist roles with documented single responsibility, typed I/O, version, timeout and failure status.
  - **Acceptance:** Each agent reports rule-by-rule evidence; the Signaling Agent computes levels only from defined rules and data and validates stop/target ordering and risk/reward; agents must not fabricate entries to fill output; missing metadata is marked unknown; Monitoring generates no trading recommendations; the Risk/Validation Gate enforces level ordering, configured risk limits, data quality and required evidence before the CEO decision. **Source:** Prd.md §6.4; Rules.md R-03.

- [ ] **REQ-ceo-decision-contract** — The CEO emits a schema-valid record with the required fields and the documented decision vocabulary.
  - **Acceptance:** `decision` ∈ {TRADE, NO_TRADE, INSUFFICIENT_DATA} with `instrument_id`, `timeframe`, `direction` (nullable unless TRADE), `created_at`, `run_id`, `evidence_refs`, `agent_statuses`, `conflicts`, `data_quality_status`, `thesis`, `invalidation_conditions`, `risk_factors`, `reasons_for_rejection`, `limitations`, `strategy_id`/`strategy_version` when applicable, and `manual_review_required = true`; `entry`/`stop_loss`/`take_profits`/`risk_reward` are `null` unless derived and validated; `TRADE` only with present, current, schema-valid, strategy-qualified and risk-validated evidence; a missing critical input is never filled by an LLM guess, and narrative cannot override a hard data-quality or risk gate; records are immutable. **Source:** Prd.md §6.5; Schema.md §5 (C-05); Rules.md R-02, R-03.

- [ ] **REQ-news-and-sentiment** — Source-attributed news retrieval and bounded sentiment analysis with provenance and uncertainty.
  - **Acceptance:** News preserves original title, publisher, published time, retrieval time, URL and extracted claims; verify access, licensing, terms and reliability before implementation; never scrape behind login, bypass access controls, or assume bulk-collection permission; deduplicate by canonical URL/similarity policy while preserving attribution; if news is not retrievable, label coverage `unavailable` — never synthesize headlines or sentiment; sanitize/validate all ingested content; timestamp basis (publication vs retrieval) always recorded. **Source:** Prd.md §6.6; Schema.md §7 (C-06); Rules.md R-04.

- [ ] **REQ-ui-and-reports** — A read-only research console over the real API with explicit state and evidence surfacing.
  - **Acceptance:** React/Next.js UI driven only by API state; surfaces include Overview, Instrument Workbench, Decision/Signal Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health and System Health; every decision shows evidence freshness and status; observed facts, deterministic calculations, strategy outputs and LLM interpretations are visually distinguished; source links and expandable evidence traces; never render placeholder or sample data as live. **Source:** Prd.md §6.7; Design.md §4–§8; Rules.md R-01.

- [ ] **REQ-journal-and-backtesting** — Immutable decision snapshots with appended outcomes, and reproducible, cost-aware backtests.
  - **Acceptance:** Journal entries are immutable decision snapshots with append-only outcome observations; every backtest declares dataset + provenance, date range, timezone, timeframe, symbol mapping, strategy version, parameter set, spread/commission/slippage assumptions and fill model, and separates in-sample development from validation/out-of-sample results while reporting missing data and excluded periods; metrics are computed by code and tested, never recalculated authoritatively by an LLM; a reported result without its run/dataset reference is invalid; never present a metric without its assumptions and sample period. **Source:** Prd.md §6.8; Schema.md §8 (C-08); Rules.md R-09.

- [ ] **REQ-local-model-support** — Local, discovered model runtime with health status and no assumed capability.
  - **Acceptance:** Ollama endpoint and model are configurable with runtime discovery (no assumed model name, hardware or context window), health check and provider/model status recorded (`ModelConfig`); all model output is untrusted until schema-validated and checked against evidence references; deterministic code owns prices, indicator values, risk/reward arithmetic, validation and gates; show `unavailable`/degraded states honestly; never send sensitive data to unapproved endpoints. **Source:** Prd.md §6.9; Architecture.md §2 Local model; Rules.md R-03, R-08.

- [ ] **REQ-no-trade-execution** — The V1 boundary is structural: no order capability exists anywhere in the codebase.
  - **Acceptance:** No order-placement/modification/closure code, endpoint, tool or broker-trading credentials exist; a `TRADE` result is a qualified research candidate requiring manual review — not an order; any future execution capability requires an explicit user decision that supersedes DR-04/R-02. **Source:** Prd.md §3; Rules.md R-02; Task.md T0804.

- [ ] **REQ-no-fabricated-data** — No synthetic market, news, sentiment, backtest or signal data in production paths.
  - **Acceptance:** Missing or unavailable data is labelled as such — never synthesized; test fixtures are labelled and confined to tests; no claim of "perfect analysis", "zero errors" or "zero hallucinations"; errors and failures are measured and reported honestly. **Source:** Prd.md §1, §3; Rules.md R-01, R-09.

- [ ] **REQ-evidence-and-provenance** — Explainability is the product, not an add-on.
  - **Acceptance:** Every decision is traceable to real, timestamped data with a recorded provider, configuration and version baseline; each decision explains, with references to underlying data, timestamps, rules and conflicts, why it was reached and why alternatives were rejected; every decision carries provenance back to the provider in machine-readable form; decision traceability metric = percentage of decisions with complete evidence references and configuration/version metadata, and it is instrumented *before* any target is set (no invented targets before baseline measurement). **Source:** Prd.md §1, §3.

## v2 Requirements

Deferred beyond the V1 roadmap. Not actionable yet — listed so they are not lost or smuggled into V1.

### Deferred (recorded, not scheduled)

- **REQ-v2-timescaledb** — TimescaleDB adoption for time-series market data, if measured need justifies it (Architecture.md §2: open pending measured need).
- **REQ-no-trade-execution#extension** — *(deliberately absent)*: no order-management or execution requirements exist in this project; see Out of Scope.
- **REQ-ui-remote-access** — LAN-accessible UI and authentication, only if the single-operator/loopback assumption is revisited. **Source:** Memory.md open decisions.
- **REQ-journal-retention** — Retention/backup policy for market data, evidence and journal records (C-11 open item) — to be decided, not built implicitly.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Order placement, modification or closure | V1 is research and decision support only (DR-04, DR-03); a `TRADE` is a qualified candidate requiring manual review, not an order (R-02, C-05) |
| Copy trading, broker execution, autonomous trading, portfolio management | Explicit product boundary; no trading credentials may exist in the project (R-02, DR-04) |
| Fabricated or mock data in `src/` production paths | Violates the core value and R-01; missing evidence must surface as `unknown`/`unavailable`; fixtures only in labelled tests (R-09) |
| LLM-emitted price levels, SL/TP or R:R | Levels and arithmetic are computed by deterministic code; model output is untrusted until schema-validated (DR-13, R-03) |
| Cloud/hosted multi-user deployment and authentication | Target runtime is a single local Windows host, UI bound to loopback, no authentication in V1 |
| Monetization, billing, marketing or tenant features | Internal research tool for one operator; not a commercial product |

## Traceability

Which phase covers which requirement (assigned during roadmap creation; one phase per requirement).

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-no-trade-execution | Phase 1 | Pending |
| REQ-instrument-provider-selection | Phase 2 | Pending |
| REQ-market-data-ingestion-validation | Phase 2 | Pending |
| REQ-specialist-agent-responsibilities | Phase 3 | Pending |
| REQ-langgraph-orchestration | Phase 4 | Pending |
| REQ-local-model-support | Phase 4 | Pending |
| REQ-news-and-sentiment | Phase 5 | Pending |
| REQ-ceo-decision-contract | Phase 5 | Pending |
| REQ-evidence-and-provenance | Phase 5 | Pending |
| REQ-journal-and-backtesting | Phase 6 | Pending |
| REQ-ui-and-reports | Phase 7 | Pending |
| REQ-no-fabricated-data | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-13 from `.planning/intel/requirements.md` (Prd.md §1, §3, §6.1–§6.9)*
*Last updated: 2026-10-13 after roadmap traceability assignment*
