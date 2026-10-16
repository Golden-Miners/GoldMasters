# GoldMasters — Project Memory and Handoff

**Last updated:** 2026-10-13  
**Purpose:** Durable handoff state. Update this file only with confirmed decisions, work performed, test evidence, and explicit open items.

## Confirmed user decisions

- Project name: **GoldMasters** (the initial brief also used “GoldMaster”; use GoldMasters consistently unless user changes it).
- Primary user: personal trading team/workspace.
- V1: research and decision support only.
- Trade execution: explicitly out of scope; no order placement/modification/closure.
- Instruments: gold, silver, forex, oil, BTC and ETH, subject to verified provider symbol coverage.
- Technical direction: React/Next.js frontend, Python backend, LangGraph orchestration, PostgreSQL persistence.
- Local LLM runtime: Ollama.
- Definition of done: develop in small steps, test each step, update task state only after checks pass.
- User-stated OpenCode environment: Context7, Supermemory, Playwright, Caveman and GitHub MCPs; skills/plugins listed in Architecture.md. Their current availability/activation has not been verified here.

## Product rules that must not be lost

1. CEO agent gathers specialist outputs and decides TRADE / NO_TRADE / INSUFFICIENT_DATA.
2. CEO cannot override deterministic data-quality or risk gates.
3. No invented market/news/sentiment/backtest/sample data in production paths.
4. Every decision needs provenance, timestamps, schema validation, and versioned configuration.
5. Data provider must be selectable; no silent fallback or symbol substitution.
6. Local MT5 availability does not imply a remote backend can access it; deployment boundary must be designed.
7. No claim of perfect analysis, zero hallucinations, or guaranteed profit.
8. Debug first, confirm root cause, then propose the smallest fix.
9. Security audit findings require source evidence; no invented paths/line numbers; no code changes before user approval.
10. Mark tasks DONE only after their acceptance checks actually pass.

## Documentation created in this package

- `Prd.md` — scope, requirements, model, edge cases, metrics, open questions.
- `Design.md` — visual direction, tokens, screens, journeys, components, states and accessibility.
- `Security.md` — audit plan; actual source audit not performed.
- The debug protocol — diagnose/confirm/minimal-fix steps.
- `Architecture.md` — proposed system, agent graph, tools and phased plan.
- The task tracker — phased task checklist.
- This file — durable handoff state.
- `Schema.md` — shared contracts and conventions.
- The rules file — mandatory coding-agent rules.

## Work actually completed

- **04-02 Wave 1 deterministic graph completed (2026-10-16):** `src/goldmasters/graph/`
  (state/edges/nodes/barriers/builder) wires all 10 Phase 3 strategy packages through
  `eligible_agents` → `evaluate` → `evaluate_gate` → pre-CEO barrier → `DecisionRecord`,
  bounded by `GOLDMASTERS_GRAPH_*` settings (60s timeout, 2 transient-only retries).
  `langgraph==1.2.15` pinned in `apps/api` (04-01 GO; PyPI legitimacy verified).
  Evidence: full suite 625 passed / 2 pre-existing live-MT5 skips, ruff + mypy strict
  clean, boundary scan green; commits `a01846d`, `234904b`, `0d713c3`; Task.md
  T0401/T0402/T0403/T0407/T0409 checked with evidence.
- **Wave-1 TRADE-unreachable finding (fail-closed, tested):** no code produces
  `risk_percent_for_idea`, so the graph passes `None` and the gate blocks with
  "idea risk unknown" → terminal NO_TRADE. Unlocks when a later phase computes
  per-idea risk; no graph change needed. T0004 (Ollama) still operator-open.
- **Repo tooling note:** bare `uv sync` prunes workspace members from `.venv`;
  always use `uv sync --all-packages` in this repo.
- **04-03 Wave 2 model runtime completed (2026-10-16):** `src/goldmasters/graph/runtime.py`
  (Ollama `AsyncClient` binding on `GOLDMASTERS_OLLAMA_HOST`, run-start `list()`
  discovery, reachable+expected-model health, measured run record) plus
  `src/goldmasters/agents/` (prompts + `ContractModel` output schemas for analyst,
  news/sentiment, research, CEO prose — evidence/reason strings only) and
  `check_ceo_required` in barriers (failed required agent blocks prose, no model
  call). `ollama==0.6.3` + `langgraph-checkpoint-sqlite==3.1.2` pinned in
  `apps/api` (04-01 GO pins); `GOLDMASTERS_OLLAMA_HOST` loopback-allowlisted,
  `OLLAMA_MODEL` unset by default. Evidence: full suite 643 passed / 3 skips
  (2 pre-existing live-MT5 + 1 ollama-live, T0004 open), ruff + mypy strict
  clean, boundary scan green; commits `41c9884`, `5227881`, `487f1c8`.
  Deferred: `AsyncSqliteSaver` wiring (dep pinned, builder swap is a later plan),
  role-node graph wiring, T0004 operator close-out.

- Drafted the nine project Markdown files from the user-provided requirements and clarification answers.
- No repository was inspected.
- No source code was created or modified.
- No tests, linters, security scanners, MT5 connection, Ollama health check, or browser tests were run.
- **T0001 completed:** Repository inspected — no git repo, no source code, only documentation files (10 Markdown files + 2 agent config files). Python 3.14.7, Node 24.21.0, npm 11.19.0 available. No tests, manifests, or package files exist. Tree recorded above.
- **T0002 completed:** OpenCode inventory: 81 skills (caveman, tdd, to-tickets, triage, to-spec, wayfinder, domain-modeling, setup-matt-pocock-skills, stitch tools, vercel tools, etc.); MCPs: caveman (local binary found), context7 (remote, token present), github (remote, token present), playwright (@playwright/mcp@0.0.83, works); opencode.json model `apinex/free/claude-opus-4.6`, provider APInex (`https://api.apinex.bond/v1`); Supermemory plugin with `supermemory_recall` permission; `triage` skill installed so Section B labels may apply.
- Therefore no implementation task is marked complete.
- **Onboarding completed (tooling work, not a Task.md item):** Ran the GSD v1.16.0 onboard → ingest-docs → roadmapper chain on 2026-10-13.
  - `git init` performed — the repository had none before this session.
  - Detection gap: the doc conventions `docs/adr/`, `docs/prd/`, `docs/specs/`, `docs/rfc/` matched nothing; every project doc lives at the root as `<Name>.md`. Discovery therefore needed an explicit `ingest-manifest.yaml` (10 docs; 1 PRD, 1 SPEC, 8 DOC).
  - 4 cycle BLOCKERS (Memory.md ↔ Rules.md, ↔ Task.md, ↔ Debug.md, plus a Memory.md self-reference) were resolved by rewriting 7 lines in this file to drop literal product filenames; no other file was edited. Cycle-free on re-run.
  - Scaffold written by `gsd-roadmapper`: `.planning/PROJECT.md`, `REQUIREMENTS.md` (12 requirements), `ROADMAP.md` (8 phases), `STATE.md`, `.planning/onboarding/SUMMARY.md`, plus `.planning/intel/` and `.planning/INGEST-CONFLICTS.md`. Commits `f4198b2` and `f710f88`.
  - Unresolved in the scaffold, carried as open risks rather than decided: Phase 0 not closed and the `MetaTrader5` package still not installed; the `Schema.md` §12 contract items (tick quantization, timeframe enum and candle boundaries, freshness thresholds, timezone policy, identifier scheme, retention/backup, config versioning) are undecided; `AGENTS.md` cites a non-existent `Rules R-12` identifier and references `.scratch/`, `docs/adr/`, `GLOSSARY.md`, `docs/agents/domain.md` and `docs/agents/issue-tracker.md`, none of which exist yet; `AGENTS.md` also writes `PRD.md` while the file is `Prd.md` (Schema.md §11 requires exact casing).
  - OpenCode note: `gsd install --opencode` is stale — `C:\Users\wasim\.gsd\defaults.json` changed after the agents were last baked, so `model_overrides` are ignored on this runtime until re-installed.

## Open decisions

- Repository path, branch, and existing codebase.
- Host OS and whether backend/API will run on the same machine as MT5.
- Whether UI is local-only or accessible on a LAN.
- Broker/terminal and actual symbol names.
- Initial timeframes and per-instrument freshness policy.
- Approved strategy set and exact strategy definitions.
- Hard risk thresholds and news blackout policy.
- Installed Ollama model(s), hardware limits and timeout policy.
- News source access method, terms, and licensing.
- PostgreSQL installation/deployment and backup/retention policy.
- Authentication requirements if any network access is permitted.
- **New (T0003):** `MetaTrader5` Python package not installed — MT5 adapter cannot run until installed on a Python 3.10+ environment on the MT5 host machine. Symbol coverage, terminal state, and broker mapping not yet verified.

## Next-session instructions

1. Read the rules, this file, the task tracker, the schema, and the architecture docs before changing code.
2. **Current task: T0002 — inspect OpenCode config and verify installed MCP/skill names and activation paths.**
3. Do not create or overwrite project files until repository state is known.
4. Verify installed OpenCode skill/MCP names and instructions; do not assume listed names correspond to active tools.
5. Resolve environment constraints and open decisions. Update this file with evidence.
6. Implement one small task at a time; run its acceptance checks; update the task tracker only with actual results.
7. No order execution in V1.

## Phase 2 execution log (2026-10-15)

- 02-01 tracer DONE: `services/mt5_adapter/` + bars/quote endpoints + provider health + reworked boundary scan. Evidence: full `uv run pytest` green (213), `ruff check/format` clean, `mypy --strict .` clean (57 files).
- Next: 02-02 + 02-03 (Wave 2). `live_mt5` operator run still pending (no terminal here; field names + py3.14 wheel must-verify-first).
- 02-02 + 02-03 DONE (Wave 2, same session): full validation policy, session quotes, weekend classifier, gap backfill, 5 health states, single retry, code table, redaction. Evidence: full pytest green, ruff + mypy strict clean.
- Next: 02-04 (Wave 3: precision, hash, contracts, live scaffold).
