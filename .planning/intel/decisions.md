# Decisions (synthesized)

Provenance: derived from the ingest set's ADR-classified documents, applying
precedence ADR > SPEC > PRD > DOC.

ADR-classified documents found: **0**
Documents carrying `locked: true`: **0**

The ingest set contains no ADR-type document and no locked decision. The
decision records below are therefore sourced from DOC-classified documents
that explicitly record confirmed or proposed decisions. They are included with
full provenance so that downstream routing does not lose them; they are not
ADR-adopted and must not be treated as higher-precedence than the SPEC/PRD.

---

## DR-01: Project name is GoldMasters
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: Use **GoldMasters** consistently; the initial brief also used “GoldMaster” — GoldMasters stands unless the user changes it.
- scope: project identity, naming

## DR-02: Primary user is a single personal trading team/workspace
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: Primary user is a personal trading team/workspace (not multi-user SaaS).
- scope: target user

## DR-03: V1 is research and decision support only
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: V1 scope is research and decision support only.
- scope: product scope

## DR-04: Trade execution is explicitly out of scope
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: No order placement, modification, or closure; no broker trading credentials.
- scope: product boundary

## DR-05: Initial instrument universe
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: Instruments are gold, silver, forex, oil, BTC and ETH, subject to verified provider symbol coverage.
- scope: instruments

## DR-06: Technical direction
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: React/Next.js frontend, Python backend, LangGraph orchestration, PostgreSQL persistence.
- scope: stack

## DR-07: Local LLM runtime is Ollama
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: Ollama is the local LLM runtime.
- scope: local model runtime

## DR-08: Definition of done
- source: Memory.md (Confirmed user decisions)
- status: locked
- decision: Develop in small steps, test each step, and update task state only after checks pass.
- scope: development workflow

## DR-09: Backend and API framework
- source: Architecture.md (§2 Backend and API)
- status: proposed
- decision: Python backend; FastAPI proposed as the API framework (confirm compatibility before pinning); Pydantic typed validation for payloads and agent contracts; domain logic separated from HTTP routes and UI.
- scope: backend, API

## DR-10: LangGraph owns orchestration state
- source: Architecture.md (§2 Agent orchestration)
- status: proposed
- decision: LangGraph owns graph state, node transitions, conditional routing, checkpointing and run metadata; agents are bounded nodes (not uncontrolled loops); a validation barrier precedes CEO decision; disagreements are preserved.
- scope: orchestration

## DR-11: Frontend boundary
- source: Architecture.md (§2 Frontend)
- status: proposed
- decision: React/Next.js as selected; UI reads API state and must not call MT5 or Ollama directly; never expose prompts, credentials, provider secrets, or privileged agent tools to the client.
- scope: frontend

## DR-12: Persistent storage
- source: Architecture.md (§2 Data storage)
- status: proposed
- decision: PostgreSQL preferred; use migrations, explicit transaction boundaries, indexes justified by query patterns, and append-only decision/outcome records; no credentials in ordinary config tables.
- scope: persistence

## DR-13: Local model usage policy
- source: Architecture.md (§2 Local model)
- status: proposed
- decision: Ollama preferred; discover available models at runtime (no assumed model/hardware/context); LLMs for synthesis, classification, extraction and explanation; deterministic code for prices, indicator values, risk/reward arithmetic, validation and gates; all model output untrusted until schema-validated.
- scope: local model

## DR-14: Market-data provider boundary
- source: Architecture.md (§2 Market-data providers)
- status: proposed
- decision: Common provider interface (get_bars, get_latest_quote, get_instrument_spec, health_check, capabilities); local MT5 as one adapter; canonical instrument IDs kept separate from provider symbols; provider choice explicit and persisted per run; no silent fallback.
- scope: market data providers

## DR-15: News and sentiment ingestion policy
- source: Architecture.md (§2 News and sentiment)
- status: proposed
- decision: Source adapters with terms-of-use review, attribution, URL canonicalization, timestamps, deduplication and rate limiting; named sources (Forex Factory, CoinDesk) are candidates only pending access checks; separate fetched source facts from model interpretation.
- scope: news, sentiment
