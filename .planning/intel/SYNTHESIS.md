# Ingest Synthesis — GoldMasters documentation set

Entry point for downstream consumers (`gsd-roadmapper`). Synthesized from 10
classified documents in `C:\XauMaster`. Mode: **new** (no pre-existing
`.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md` or `STATE.md`).
Precedence applied: **ADR > SPEC > PRD > DOC**. Every document carried
`manifest_override: true`; all 10 are high-confidence.

## Documents by type

- PRD: 1 — Prd.md (GoldMasters — Product Requirements Document)
- SPEC: 1 — Schema.md (Shared Schema and Naming Conventions)
- ADR: 0
- DOC: 8 — Architecture.md, Rules.md, Design.md, Security.md, Debug.md, Memory.md, Task.md, AGENTS.md
- UNKNOWN / low-confidence: 0

## Decisions

- ADR-adopted decisions: **0** (no ADR-classified documents, no `locked: true`).
- Decision records captured (all DOC-sourced, with provenance): **15**
  - 8 user-confirmed (`status: locked`) from Memory.md — project name, primary user, V1 scope, no execution, instruments, tech stack, Ollama, definition of done.
  - 7 proposed (`status: proposed`) from Architecture.md §2 — backend/API, orchestration, frontend boundary, storage, local model policy, provider boundary, news/sentiment policy.
- Detail: `.planning/intel/decisions.md`

## Requirements

- Total: **12** (all from Prd.md)
- IDs: REQ-instrument-provider-selection, REQ-market-data-ingestion-validation,
  REQ-langgraph-orchestration, REQ-specialist-agent-responsibilities,
  REQ-ceo-decision-contract, REQ-news-and-sentiment, REQ-ui-and-reports,
  REQ-journal-and-backtesting, REQ-local-model-support, REQ-no-trade-execution,
  REQ-no-fabricated-data, REQ-evidence-and-provenance
- Detail: `.planning/intel/requirements.md`

## Constraints

- Total: **23**
  - From Schema.md (SPEC): 12 — C-01 … C-11 plus one sub-entry (C-04b provider protocol)
  - From Rules.md (mandatory policy, DOC): 11 — R-01 … R-10 plus one sub-entry (R-04b session-start reading)
- Type breakdown: schema 5 (C-01, C-02, C-04, C-06, C-08); api-contract 4 (C-03, C-05, C-07, C-09); protocol 1 (C-04b); nfr 13 (C-10, C-11, R-01 … R-10, R-04b)
- Detail: `.planning/intel/constraints.md`

## Context topics

- Total: **17** topics with source attribution (DOC-sourced): project overview,
  confirmed user decisions, product rules that must not be lost, mandatory project
  rules (Rules.md, reproduced), architecture overview, agent topology, deployment
  boundary, repository layout, quality gates, phased development plan, design
  brief (principles/tokens), design brief (screens/flows/components/states),
  accessibility, security review plan, debugging protocol, task tracker,
  agent operating guide, open questions and unresolved items.
- Detail: `.planning/intel/context.md`

## Cross-reference integrity

- Cycle detection on the cross-ref graph: **no cycles**. The previous run's 4
  blockers (a `Memory.md`-centred cross-reference cycle) are cleared by the
  applied fix. Traversal depth stayed well under the depth-50 cap.
- Dangling (non-cyclic) references are recorded as INFO in the conflicts report.

## Conflicts

- **0 blockers**
- **2 warnings** — task-tracking state contradictions (Task.md internally; and between Memory.md and Task.md)
- **5 informational** — no ADRs/locked docs; Design-vs-Schema status vocabulary (auto-resolved to SPEC); dangling "Rules R-12" reference; references to not-yet-present artifacts (README, docs/adr, GLOSSARY.md, .scratch/, PRD.md casing); Memory.md repo snapshot vs current git state
- Detail: `.planning/INGEST-CONFLICTS.md`

## Per-type intel files

- `.planning/intel/decisions.md`
- `.planning/intel/requirements.md`
- `.planning/intel/constraints.md`
- `.planning/intel/context.md`

## Status

No BLOCKERS. Routing is safe with respect to locked decisions and precedence.
Two WARNINGS concern task-progress bookkeeping (DOC-vs-DOC, no precedence
resolution available) and are informational for planning; they do not invalidate
the synthesized requirements, constraints or confirmed decisions.
