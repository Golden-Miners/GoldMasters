# Phase 4: LangGraph Orchestration and Local Model Runtime — Research

**Researched:** 2026-10-16
**Domain:** Bounded LangGraph run hosting deterministic strategy/gate code + Ollama local-model nodes, fail-closed
**Confidence:** HIGH (repo contracts/code read this session; LangGraph/Ollama APIs via Context7 official sources)

## Summary

Phase 4 puts the Phase 3 deterministic core inside a bounded, run-tracked LangGraph
execution: typed state, declared nodes, explicit conditional edges, configuration-bounded
retry/timeout/cancellation, per-node schema validation, a deterministic validation barrier
before the CEO, and a locally discovered Ollama model whose output is untrusted until
validated. A critical failure can only terminate as `INSUFFICIENT_DATA` or `NO_TRADE` —
never an unqualified `TRADE` — because `TRADE` requires a passed `GateVerdict` carrying
validated levels, and the `DecisionRecord` validator rejects anything else
[VERIFIED: src/goldmasters/risk/gate.py:44-64; Schema.md §6 invariants].

Everything Phase 4 orchestrates already exists as pure tested code: `eligible_agents`
selection over 10 matrix rows, the supervisor-consumption shape, `Strategy.evaluate(bars,
ctx)`, `build_candidate_levels`, `evaluate_gate`/`trade_eligible_levels`, and the
14-status role matrix in `docs/roles.md`. Phase 4 adds NO new numbers and NO new
strategies — it adds the graph, the run record, the bounds, the validation barrier, and
the Ollama runtime binding. LLM nodes are restricted to synthesis/explanation roles
(Market Analyst text, News/Sentiment/Research extraction); levels, regimes, R:R, and gate
verdicts stay in deterministic code per Rules §3.5.

**Primary recommendation:** Add `langgraph` + `ollama` (both PyPI, official) to
`apps/api` only; build `src/goldmasters/graph/` as `StateGraph` over a TypedDict run
state with async nodes (TimeoutPolicy is async-only), per-node `RetryPolicy` on transient
errors only, `SqliteSaver`/Postgres checkpointer keyed by `thread_id=run_id` for
resumability, Ollama calls via the official client with `format=<Pydantic JSON schema>`
+ `model_validate` + sanitized errors, a deterministic pre-CEO validation-barrier node,
and the existing `evaluate_gate` as the sole path to TRADE-eligible levels. Ollama
endpoint/models are UNVERIFIED (T0004 open) — Wave 0 must probe `GET /api/tags` on the
operator-configured endpoint before any model-dependent plan executes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Graph state, transitions, conditional routing, checkpointing, run metadata | LangGraph (`src/goldmasters/graph/`) | — | Architecture §2: LangGraph owns exactly this; agents are bounded nodes, not loops |
| Run record (run_id, input snapshot/ref, config + versions, timestamps, per-node status) | Persistence (PostgreSQL, Phase 5 expands) + graph checkpointer | API run endpoints | ROADMAP criterion 1; checkpointer gives resume, DB gives the immutable record |
| Retry/timeout/cancellation/partial-failure bounds | Graph wiring (config-bounded `GOLDMASTERS_GRAPH_*` settings) | — | Rules §3.8; no unbounded loops or recursive delegation |
| Evidence collection prose (analyst/trend/instrument/news/sentiment/research summaries) | LLM nodes (Ollama, temperature 0, schema-pinned) | — | Models explain; code computes (Rules §3.5) |
| Strategy evaluation, levels, regime, gate verdict | Deterministic code (Phase 3, called FROM nodes) | — | Never re-implemented in the graph; nodes are thin wrappers that validate I/O |
| Pre-CEO validation barrier | Deterministic graph node (no LLM) | — | ROADMAP criterion 3; disagreements preserved to `conflicts`, never reconciled |
| CEO decision | CEO node (Ollama-assisted prose + deterministic contract assembly) | Gate (hard veto) | CEO cannot bypass validation/quality/risk gates (Rules §2.5) |
| Model discovery, health, availability record | Ollama runtime binding (`Client(host=...)`, `list()`) | Settings | Architecture §2: discover at runtime; assume no model name, hardware, or context window |
| Failure termination (INSUFFICIENT_DATA / NO_TRADE) | Failure-policy edges + `DecisionRecord` validators | — | PRD §6.4 + Schema §6; no path to unqualified TRADE |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` (PyPI) | pin at plan time from official docs — NOT in manifests today [ASSUMED] | `StateGraph`, `RetryPolicy`, `TimeoutPolicy`, checkpointers, `Send`/fan-out, `Command` routing | Architecture-mandated orchestrator; `RetryPolicy(max_attempts, retry_on)` + `TimeoutPolicy(run_timeout)` + `step_timeout` are the exact bounded-node primitives [CITED: langchain-ai/langgraph types.py, test_retry.py via Context7] |
| `ollama` (PyPI, official client) | pin at plan time — NOT in manifests today [ASSUMED] | `Client(host=...).chat(model, messages, format=schema)`, `list()` discovery | Official client; `format=<JSON schema>` + `model_validate_json` is the documented structured-output pattern; `Client(host='http://localhost:11434')` constructor is documented [CITED: ollama/ollama-python via Context7] |
| `goldmasters-contracts` (existing) | existing | Node I/O validation, run/decision envelopes, error contract | Every node payload validates before use (criterion 4); `ContractModel` strict/forbid/frozen precedent |
| Phase 3 code (existing) | existing | `eligible_agents`, `evaluate`, `build_candidate_levels`, `evaluate_gate`, `trade_eligible_levels` | Nodes call these; no numeric logic is rebuilt in the graph layer |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langgraph-checkpoint-sqlite` or Postgres saver | pin at plan time [ASSUMED] | Resumable runs (`compile(checkpointer=...)`, `thread_id=run_id`) | `SqliteSaver(conn, check_same_thread=False)` + `interrupt`/`Command(resume=...)` is the documented resume pattern [CITED: langchain docs via Context7]; Postgres saver if the run store must live in the existing cluster |
| `httpx` timeout (via `ollama` client kwargs) | existing (`httpx==0.28.1` in apps/api) | Wall-clock cap on model calls | `Client` forwards extra kwargs to `httpx.Client` [CITED: ollama-python README via Context7] — defense-in-depth under `TimeoutPolicy` |
| pytest (existing) | existing | Graph-path/branch tests, failure-injection tests | Rules §9.3–9.4: test missing/stale/malformed/timed-out/unavailable inputs; critical failures cannot produce TRADE |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ollama` direct client | `langchain-ollama` ChatOllama wrapper | REJECT: extra LangChain dependency weight for no contract benefit; direct client + `format=` schema + our own `model_validate` keeps the validation barrier explicit and the signals-only boundary scan simple |
| Postgres checkpointer | `InMemorySaver` everywhere | InMemory is for tests/dev only — no resume across restart; production runs need a durable saver (sqlite file or Postgres) |
| Pydantic state model | `TypedDict` state | LangGraph state must be a `TypedDict`/dataclass/Pydantic — either works; TypedDict with `Annotated[..., add_messages]`-style reducers is the documented norm [CITED: langgraph examples via Context7]. Run-record *persistence* uses contract models regardless |

**Installation:**
```bash
# Exact pins resolved at plan time from official docs/PyPI; record in apps/api/pyproject.toml
uv add --project apps/api langgraph ollama
# Checkpointer backend: langgraph-checkpoint-sqlite (dev/test) and/or langgraph-checkpoint-postgres (prod)
```

**Version verification:** Neither `langgraph` nor `ollama` appears in any manifest
(`pyproject.toml`, `apps/api/pyproject.toml`, `packages/contracts/pyproject.toml` all
read this session — no graph/model dependency exists yet). Python pin is `==3.14.7`;
LangGraph-on-3.14 compatibility MUST be verified at plan time (check release notes;
if incompatible, planner escalates — do not downgrade the interpreter pin silently)
[ASSUMED risk — see A2].

## Package Legitimacy Audit

Legitimacy-gate tooling (`gsd_run query package-legitimacy`) was not available in this
research session — the planner MUST run it before pinning. Provisional assessment:

| Package | Registry | Age | Source Repo | Verdict | Disposition |
|---------|----------|-----|-------------|---------|-------------|
| `langgraph` | PyPI | mature (LangChain AI org) | github.com/langchain-ai/langgraph | presumed OK [ASSUMED] | Planner verifies via gate + `pip index versions langgraph` |
| `ollama` | PyPI | mature (Ollama org, official client) | github.com/ollama/ollama-python | presumed OK [ASSUMED] | Planner verifies via gate + `pip index versions ollama` |
| `langgraph-checkpoint-sqlite` / `-postgres` | PyPI | mature (same org) | same | presumed OK [ASSUMED] | Planner verifies; only install the backend actually used |

**Packages removed due to SLOP verdict:** none (no check run).
**Packages flagged as suspicious (SUS):** none (no check run).
*Both `langgraph` and `ollama` were sourced from official-org documentation via
Context7 (HIGH-reputation sources), not from web-search hearsay — but the registry
gate still must run at plan time.*

## Architecture Patterns

### System Architecture Diagram

```text
Operator input (instrument, provider, timeframe, run config)
        │
        ▼
Resolve instrument + provider configuration ── record selection in run (no silent fallback)
        │
        ▼
Fetch market data + instrument metadata (Phase 2 adapter)
        │
        ▼
Validate freshness/integrity ── fail ──► terminate INSUFFICIENT_DATA (critical node)
        │
        ▼ (fan-out: independent evidence collectors run in parallel)
┌───────┬──────────┬────────────┬──────┬───────────┬──────────┐
Market  Trend  Instrument  News  Sentiment  Research  (10 strategy
Analyst Agent   Agent     Analyst  Agent     Agent    agents via
(LLM)   (det.)  (det.)    (LLM)    (LLM)      (LLM)    supervisor ──► eligible only)
└───────┴──────────┴────────────┴──────┴───────────┴──────────┘
        │  each node output schema-validated; failures recorded w/ status,
        │  non-critical → continue w/ limitations+conflicts; critical → fail closed
        ▼
Strategy Supervisor: eligible_agents(matrix, ctx) → run eligible evaluate(bars, ctx)
        │
        ▼
Normalize + validate agent evidence (deterministic node)
        │
        ▼
Signaling: assemble candidate ONLY from GateVerdict(passed=True) via trade_eligible_levels
        │
        ▼
Deterministic Risk/Eligibility Gate (evaluate_gate — pure, no I/O, no retry on policy fail)
        │
        ▼
VALIDATION BARRIER (deterministic node, no LLM): evidence completeness + quality +
conflict preservation check ── fail ──► INSUFFICIENT_DATA / NO_TRADE
        │
        ▼
CEO Decision: TRADE / NO_TRADE / INSUFFICIENT_DATA
(manual_review_required=true always; TRADE only on passed verdict + complete levels)
        │
        ├──► Persist decision + evidence snapshot (immutable)
        ├──► Trade Journal append
        └──► Monitoring + run metrics (side-channel; never a decision input)
        ▼
       END
```

Data-flow rules: disagreements flow forward into `GateVerdict.conflicts` →
`DecisionRecord.conflicts`, never reconciled (roles.md rules 2–3). Monitoring emits no
recommendation (roles.md rule 1, test-pinned). No edge may carry unvalidated model
output into Signaling/Gate/CEO.

### Recommended Project Structure

```text
src/goldmasters/
├── graph/               # NEW — Phase 4 (T0401–T0403, T0411)
│   ├── state.py         # TypedDict run state + reducers
│   ├── nodes.py         # thin bounded wrappers: validate-in → call det.code/LLM → validate-out
│   ├── edges.py         # explicit conditional edges incl. failure-policy routing
│   ├── barriers.py      # pre-CEO validation barrier (deterministic, no LLM)
│   ├── runtime.py       # Ollama Client binding: endpoint, discovery, health, model record
│   └── builder.py       # StateGraph assembly + compile(checkpointer=...) + settings bounds
├── agents/              # NEW — LLM prompt/parse nodes (T0404–T0408 prose roles only)
├── strategies/          # existing — called, never re-implemented
├── risk/                # existing gate.py — the sole TRADE path
tests/unit/test_graph_*.py   # state/edge/retry/timeout/barrier/failure-policy tests (T0411)
tests/integration/           # branch + resume + Ollama-outage tests (needs discovered model or marked skip)
```

### Pattern 1: Typed state with run record fields

**What:** One `TypedDict` carries run identity, input snapshot reference, config +
version stamps, timestamps, per-node statuses, evidence accumulations, gate verdict,
and decision. Reducers (`add_messages`-style / `operator.add` for lists) append
evidence; nothing overwrites another node's findings.
**When to use:** The single `StateGraph(State)` schema for the whole run
(criterion 1: run_id, input snapshot/reference, configuration + version identifiers,
timestamps, per-node status).

```python
# Shape precedent: GraphState/AgentState TypedDicts with Annotated reducers
# [CITED: langchain-ai/langgraph examples via Context7]
class RunState(TypedDict):
    run_id: str
    input_ref: str            # snapshot/reference of run inputs (criterion 1)
    config_hash: str           # GOLDMASTERS_ effective-config hash (existing helper)
    code_versions: dict[str, str]  # strategy_id → version + code_hash stamps
    agent_statuses: dict[str, str] # node → AgentRunStatus verbatim member
    evidence: Annotated[list[str], operator.add]  # append-only, never overwrite
    conflicts: Annotated[list[str], operator.add] # disagreements preserved
    gate_verdict: GateVerdict | None
    decision: DecisionRecord | None
```

### Pattern 2: Bounded node — retry transient only, async timeout, validated I/O

**What:** Each node declares `retry_policy=RetryPolicy(max_attempts=N,
retry_on=<transient>)` from `GOLDMASTERS_GRAPH_*` settings; `TimeoutPolicy`
per async node + global `step_timeout`; node body validates input contracts,
calls deterministic code or ONE Ollama call, validates the output contract,
returns a sanitized `error` object on failure (Schema §10) — never a filled-in guess.
**When to use:** Every node (criteria 2 + 4).

```python
# Retry-then-error-handler is the documented composition: retries exhaust first,
# then the error handler runs [CITED: langchain-ai/langgraph test_retry.py via Context7]
builder.add_node("market_analyst", market_analyst,
                 retry_policy=RetryPolicy(max_attempts=cfg.max_attempts,
                                          retry_on=(httpx.TimeoutException, httpx.ConnectError)))
# TimeoutPolicy is ASYNC-NODES-ONLY [CITED: langgraph/types.py via Context7] —
# graph nodes MUST be async; sync deterministic helpers are called from async wrappers.
# Deterministic validation failures (contract ValidationError, gate policy fail)
# are NEVER in retry_on (PRD: do not retry deterministic validation failures endlessly).
```

### Pattern 3: Ollama structured-output + runtime discovery

**What:** `Client(host=<GOLDMASTERS_OLLAMA_HOST>)`; at run start call `list()` to
discover models (never assume a name/capability/context window); health = reachable +
expected model present; every generation uses `format=<Pydantic>.model_json_schema()`,
`options={"temperature": 0}`, then `Model.model_validate_json(content)`; any parse
failure → sanitized error + bounded retry → fail closed. Record model id/version +
availability/test status in the run record (criterion 5).
**When to use:** All LLM nodes + the T0004-closing Wave 0 probe.

```python
# [CITED: ollama/ollama-python README + structured-outputs example via Context7]
client = Client(host="http://localhost:11434")  # host from GOLDMASTERS_OLLAMA_HOST
models = client.list()                            # runtime discovery — no assumed names
resp = client.chat(model=model_id, messages=[...],
                   format=AnalystNote.model_json_schema(),
                   options={"temperature": 0})
note = AnalystNote.model_validate_json(resp.message.content)  # untrusted until this passes
```

### Anti-Patterns to Avoid

- **Sync nodes with TimeoutPolicy:** silently unenforced — TimeoutPolicy raises
  `NodeTimeoutError` only for async nodes. All graph nodes are async.
- **Retrying policy failures:** `retry_on` must list transient transport errors only;
  contract `ValidationError`, gate `passed=False`, and `NOT_APPLICABLE` are routing
  signals, not retries.
- **Model-authored numbers:** no LLM output enters entry/stop/targets/R:R/regime
  (Rules §3.5, roles.md rule 3). LLM nodes produce `evidence`/`reason` strings only.
- **Silent reconciliation:** a barrier or CEO that merges conflicting agent outputs
  into one summary violates roles.md rule 2 — conflicts ride verbatim to the verdict.
- **Assuming the model:** any literal model name, context window, or hardware claim
  in code/docs violates Architecture §2 and criterion 5 — Wave 0 discovery only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph orchestration, retries, checkpoint/resume | Custom runner/queue/state machine | `langgraph` StateGraph + checkpointer | Durable execution, fan-out cancel semantics (`_should_stop_others` fail-fast), `Command` routing, and resume are framework-solved and tested |
| Structured model output | Regex/JSON-repair parsing of free text | Ollama `format=` JSON schema + Pydantic `model_validate_json` | Documented pattern; free-text parsing is where fabricated levels leak in |
| Run-state persistence/resume | Custom thread store | Saver (`SqliteSaver`/Postgres) with `thread_id=run_id` | Documented interrupt/resume (`Command(resume=...)`) semantics |
| Timeout/cancellation plumbing | Thread-kill / signal hacks | `TimeoutPolicy` (async) + `step_timeout` + httpx timeouts + `graph.abort()` stream semantics | Cooperative, recorded as `timed_out`/`cancelled` statuses instead of lost runs |
| Error shape | Ad-hoc dicts / raw exceptions to state | Schema §10 error contract (`code`, sanitized `message`, `retryable`, `correlation_id`) | Retryability by code, no secret/stack leakage |

**Key insight:** The graph layer contributes *bounds and routing*, not logic. Every
number already has a home (Phase 3); every status already has an enum member
(`AgentRunStatus`, 9 verbatim members — no new members for graph states; map
resume/retry internals onto `running`/`error`/`timed_out`/`cancelled`).

## Common Pitfalls

### Pitfall 1: TimeoutPolicy on sync nodes does nothing
**What goes wrong:** Nodes written `def` (sync) hang past the configured timeout with
no `NodeTimeoutError`; an Ollama hang stalls the run forever.
**Why it happens:** Per-node timeout is async-only by framework design
[CITED: langgraph/types.py via Context7].
**How to avoid:** All nodes `async def`; deterministic helpers stay sync but are
called from async wrappers; belt-and-braces httpx timeout on the Ollama client.
**Warning signs:** any `builder.add_node` target that is not `async def`.

### Pitfall 2: Unbounded fan-out / recursive delegation
**What goes wrong:** Supervisor spawns strategy evaluations without limit, or an
agent node delegates to sub-agents recursively.
**Why it happens:** `Send` fan-out and subgraphs make unbounded parallelism easy.
**How to avoid:** Fan-out is exactly the 10 registered agents filtered by
`eligible_agents` (bounded set, contract-tested); `max_concurrency` set from config;
no node may launch sub-agents (Rules §3.8). Test asserts node count ≤ eligible set.

### Pitfall 3: Ollama endpoint/models assumed (T0004 STILL OPEN)
**What goes wrong:** Plans hardcode `llama3.1:8b` or `localhost:11434`; CI/prod runs
fail or, worse, silently fall back to a different model.
**Why it happens:** T0004 (Ollama health-check + model inventory) is unchecked;
Memory.md lists installed models/hardware/timeout policy as open decisions.
**How to avoid:** Wave 0 is a probe task: `Client(host=cfg).list()` (+ `/api/ps`
if needed), record endpoint + model inventory + test status; no model-dependent
plan executes before it. No silent fallback — model absent → run fails closed.
**Warning signs:** a model-name string literal anywhere outside settings/tests.

### Pitfall 4: Validation barrier placed AFTER the CEO or made LLM-based
**What goes wrong:** CEO prose influences what counts as "valid evidence" —
unvalidated output reaches a decision, violating criterion 4 and Rules §3.6.
**Why it happens:** Treating the barrier as a review step rather than a gate.
**How to avoid:** Barrier is a deterministic node between gate and CEO: checks
evidence-status map all-`VALID`, quality `OK` + zero flags, verdict present,
conflicts preserved; emits go/no-go. CEO receives statuses + verdict, never raw
unvalidated text. Test: malformed model output at any node → sanitized error,
never a decision input.

### Pitfall 5: Partial failure read as agreement
**What goes wrong:** A timed-out evidence agent is treated as "no objection" and
the CEO proceeds to TRADE.
**Why it happens:** Missing status propagation; CEO infers agreement from silence.
**How to avoid:** CEO input includes the full `agent_statuses` map; any non-`ok`
status on a required node forces `INSUFFICIENT_DATA` (roles.md rule: CEO must never
infer a failed agent agreed; Risk gate already preserves conflicts). Non-critical
optional nodes (Research when not requested) may degrade to limitations — the
required-vs-optional set is a locked plan decision.

### Pitfall 6: Python 3.14 vs LangGraph support unverified
**What goes wrong:** `uv add langgraph` resolves but the framework (or its
`pydantic`/`httpx` transitive pins) breaks on 3.14, stalling the phase.
**Why it happens:** Repo pins `==3.14.7` exactly (D-42); LangGraph's supported
range was not checked in this session (no network install allowed).
**How to avoid:** First plan task resolves + records the compatible `langgraph`
pin for 3.14 (or escalates); do NOT loosen the interpreter pin or transitive
contract pins (`pydantic==2.14.1`) to force resolution.

## Code Examples

### Supervisor fan-out over the seam-tested verdicts (no new selection logic)

```python
# eligible_agents verdicts ALREADY carry what PRD §6.4 requires:
# one verdict per strategy_id + scope on each eligible row
# [VERIFIED: tests/unit/test_strategy_supervisor_seam.py:1-60; base.py:244-266]
verdicts: dict[str, EligibilityVerdict] = eligible_agents(matrix_rows, ctx)
# Graph: conditional edge / Send ONLY to ids with verdict == "eligible".
# "disabled" → record skipped; "not_applicable" → AgentRunStatus.SKIPPED, no gate input
# (locked gate-input table: only SETUP_FOUND reaches evaluate_gate [VERIFIED: base.py:170-186]).
```

### Failure-policy terminal mapping (criterion 6)

```python
# Critical node failed (fetch/validate/gate/barrier/model-unavailable-after-retries):
# → DecisionRecord(decision=INSUFFICIENT_DATA, levels null, reasons cite cause)
# Gate blocked / no setup anywhere but evidence complete:
# → DecisionRecord(decision=NO_TRADE, levels null)
# No edge, no handler, no fallback may construct decision=TRADE without
# GateVerdict(passed=True, levels=<validated>) + complete levels —
# enforced by GateVerdict + DecisionRecord validators, test per Rules §9.4.
```

### Run record fields (criterion 1)

```python
# run_id (UUID), input snapshot/reference, GOLDMASTERS_ effective-config hash
# (hash_effective_config exists [VERIFIED: settings.py]), strategy versions +
# code_hash stamps, started/finished timestamps (tz-aware UTC), per-node
# AgentRunStatus map, model id + availability/test status, terminal decision.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No graph code (seam test consumes `eligible_agents` only, zero Phase 4 code) | Phase 4 builds `src/goldmasters/graph/` on the seam | This phase | Supervisor logic arrives WITHOUT changing selection semantics (contract-tested) |
| No model runtime (T0004 open, no Ollama dep) | Official `ollama` client + discovery + recorded health | This phase | Model availability becomes measured run metadata, not an assumption |
| Deterministic code unhosted (called by tests only) | Deterministic code called FROM bounded nodes | This phase | Same functions, same validators — new bounds, trace, and failure routing |
| `AgentRunStatus` 9 members (queued/running/ok/no_setup/insufficient_data/skipped/error/timed_out/cancelled) | Reused verbatim for node statuses | No change (closed enum, D-23) | Graph internals map onto existing members; CEO contract unchanged |

**Deprecated/outdated:** none. Do not add enum members; do not rebuild selection,
levels, or gate logic in the graph layer.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `langgraph` + `ollama` are the packages (PyPI, official orgs); exact pins resolved at plan time | Standard Stack, Audit | Wrong pin breaks 3.14 or contract pins; mitigation: resolve-first task, gate check |
| A2 | LangGraph supports Python 3.14 (unverified — no network in this session) | Pitfall 6 | Phase stalls; escalate rather than loosen pins |
| A3 | Ollama serves OpenAI-compatible `http://<host>:11434` with `/api/tags`, `/api/chat`, `/api/ps` (standard layout, endpoint itself UNVERIFIED per T0004) | Patterns, Pitfall 3 | Wave 0 probe corrects; no model code runs before it |
| A4 | Required-vs-optional evidence-node set (which failures are critical) can be locked at plan time from roles.md + PRD §6 | Pitfall 5 | Needs discuss-phase confirmation; default: all evidence nodes required except on-demand Research |
| A5 | Durable saver: Postgres-backed preferred (cluster exists per local-stack.md), sqlite acceptable for dev | Patterns | Planner confirms; InMemorySaver for unit tests regardless |
| A6 | CEO node = Ollama-drafted thesis/invalidation text + deterministic contract assembly (levels ONLY from `trade_eligible_levels`) | Patterns | Locks Rules §3.5 compliance; planner must not allow CEO prose to author numbers |

## Open Questions

1. **Ollama endpoint + installed models + hardware/context limits (T0004)**
   - What we know: preferred runtime is Ollama; nothing verified — no endpoint, no
     inventory, no health output recorded anywhere this session.
   - What's unclear: host/port, installed model ids, VRAM/CPU limits, usable
     context windows, per-call timeout budget.
   - Recommendation: Wave 0 probe task (operator runs `ollama list` / `Client.list()`
     output recorded); all model pins stay operator-confirmed settings.

2. **Graph timeout/retry numeric bounds**
   - What we know: bounds must be configuration-bounded (Rules §3.8); settings
     precedent is fail-closed declared keys (D-36).
   - What's unclear: per-node timeout seconds, max attempts, step timeout,
     retry backoff — all invented numbers if filled in now (Rules §1.1).
   - Recommendation: discuss-phase questions; `GOLDMASTERS_GRAPH_*` keys declared
     with no silent defaults.

3. **Which graph paths persist to PostgreSQL in Phase 4 vs Phase 6**
   - What we know: criterion 1 needs a run record; Phase 5/6 (journal/persistence)
     owns immutability/append-only semantics.
   - What's unclear: whether Phase 4 writes the run table or only the checkpointer.
   - Recommendation: Phase 4 writes the run record minimally (status/trace for
     criterion 1); immutability hardening stays Phase 6. Planner confirms boundary.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14.7 + `uv run pytest`, ruff, mypy strict | All plans | ✓ (repo pins + Phase 2/3 green precedent) | 3.14.7 | — |
| `langgraph` PyPI package | Graph builder/nodes/edges | ✗ (not in manifests) | — | None — must be added; Wave 0 resolves pin |
| `ollama` PyPI package | LLM nodes + discovery | ✗ (not in manifests) | — | None — must be added |
| Ollama server + models (T0004) | Runtime discovery, all LLM-node tests | ✗ UNVERIFIED | — | Deterministic-only graph tests run regardless; model tests marked skip until probe |
| PostgreSQL local cluster | Run-record persistence | ✓ (provisioned per local-stack.md) | 18.6 | SqliteSaver for checkpointer if PG saver deferred |

**Missing dependencies with no fallback:**
- Ollama server/models verification (T0004) — blocks model-dependent plans, not
  deterministic graph-skeleton plans (T0401–T0403, T0409, T0411 partial).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest via `uv run pytest` (config in `pyproject.toml [tool.pytest]`) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/unit/test_graph_<module>.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REQ-langgraph-orchestration (crit. 1) | Run record: run_id, input ref, config+versions, timestamps, per-node status | unit+integration | `uv run pytest tests/unit/test_graph_state.py tests/integration/test_run_record.py -x -q` | ❌ Wave 0 |
| REQ-langgraph-orchestration (crit. 2) | Bounded nodes: retry caps, async timeouts, cancel, partial-failure routing; node count ≤ eligible set | unit | `uv run pytest tests/unit/test_graph_bounds.py -x -q` | ❌ Wave 0 |
| REQ-langgraph-orchestration (crit. 3) | Pre-CEO barrier; disagreements preserved to conflicts | unit | `uv run pytest tests/unit/test_graph_barrier.py -x -q` | ❌ Wave 0 |
| REQ-langgraph-orchestration (crit. 4) | Per-node schema validation; malformed model output → sanitized error, never a decision | unit+contract | `uv run pytest tests/unit/test_graph_validation.py -x -q` | ❌ Wave 0 |
| REQ-local-model-support (crit. 5) | Endpoint config + health + discovery; no assumed model; availability recorded | integration | `uv run pytest tests/integration/test_ollama_discovery.py -x -q` (skip w/o server) | ❌ Wave 0 |
| REQ-local-model-support (crit. 6) | Critical failure → INSUFFICIENT_DATA/NO_TRADE; no path to unqualified TRADE | unit (failure injection) | `uv run pytest tests/unit/test_graph_failure_policy.py -x -q` | ❌ Wave 0 |
| T0404–T0410 agent nodes | Each role node: typed I/O per roles.md, version, timeout, failure status | unit+contract | per-node `test_graph_nodes_<role>.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** quick run command for the touched module
- **Per wave merge:** full suite `uv run pytest -x -q` (must stay green)
- **Phase gate:** full suite green + boundary scan (no order paths, no `MetaTrader5`
  outside adapter) + committed-schema drift clean before verify

### Wave 0 Gaps
- [ ] `src/goldmasters/graph/` + `agents/` tree — covers T0401–T0411
- [ ] `GOLDMASTERS_GRAPH_*` + `GOLDMASTERS_OLLAMA_*` settings keys (fail-closed, declared, hash-covered)
- [ ] T0004 probe: endpoint + `ollama list` inventory recorded (operator output)
- [ ] `langgraph` + `ollama` pins resolved for Python 3.14 + legitimacy gate run
- [ ] All `test_graph_*` / `test_ollama_discovery` files (table above)

## Security Domain

Graph + model-runtime surface is new: untrusted model output, outbound HTTP to the
Ollama endpoint (SSRF surface if host is operator-configurable), prompt-injection via
news/research content flowing into LLM nodes.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface; loopback-only API unchanged |
| V3 Session Management | no | `thread_id=run_id` is a resume key, not a session; no user sessions |
| V4 Access Control | partial | Ollama host allowlist: endpoint must be loopback/default or explicitly approved; never a public URL by default; UI never calls Ollama directly (Architecture §2) |
| V5 Input Validation | yes | Contract constructors on every node boundary; Ollama `format=` schema + `model_validate`; news/research treated as untrusted input (Rules §4.6, §7.6); sanitized error contract |
| V6 Cryptography | no | `code_hash` remains an integrity label, not tamper-proofing |

### Known Threat Patterns for graph + local-model stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via news/research content steering the CEO | Tampering | Untrusted-input marking; barrier + gate are deterministic and unpromptable; CEO levels come only from `trade_eligible_levels` |
| Model output with fabricated levels reaching a decision | Spoofing | `format=` schema + `model_validate_json`; levels fields accepted ONLY from deterministic code; failure-injection test per Rules §9.4 |
| SSRF via operator-configured Ollama host | Tampering | Host allowlist validation at startup (loopback default); outbound only to the declared endpoint |
| Run-state confusion across resume (stale checkpoint replayed as fresh) | Tampering | `thread_id=run_id` UUID; input snapshot hash checked on resume; resumed runs re-validate evidence freshness |

## Sources

### Primary (HIGH confidence — read this session)
- `src/goldmasters/strategies/base.py` (eligibility, adapter table, gate-input lock),
  `src/goldmasters/risk/gate.py` (verdict invariants, enforcement order),
  `src/goldmasters/risk/levels.py`, `src/goldmasters/strategies/agent_10/__init__.py`
- `docs/roles.md` (14-role matrix + 10-row eligibility matrix + normative rules),
  `tests/unit/test_strategy_supervisor_seam.py` (consumption contract, no Phase 4 code)
- `Schema.md` §§2/6/8/10, `Rules.md` §§1/3/4/7/9, `Architecture.md` §§2/3/7,
  `Prd.md` §6.4, ROADMAP.md Phase 4 criteria (6 items), `Task.md` T0401–T0411 + T0004
- `apps/api/pyproject.toml`, workspace + contracts manifests (no langgraph/ollama present)

### Secondary (MEDIUM confidence — official docs via Context7, verify pins at plan time)
- `/langchain-ai/langgraph`: StateGraph/TypedDict/reducers, RetryPolicy +
  error-handler composition, TimeoutPolicy async-only + step_timeout, SqliteSaver +
  interrupt/`Command(resume=...)` resume pattern
- `/ollama/ollama-python`: `Client(host=...)`, `list()` discovery, `chat(...,
  format=schema, options={'temperature': 0})`, `model_validate_json` pattern,
  httpx-kwarg forwarding

### Tertiary (LOW confidence — flagged, not decided)
- A1–A6 assumptions; T0004 endpoint/models; 3.14 compatibility; timeout/retry numbers

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — reuse targets verified in repo; new deps from official-org
  docs with pins + gate explicitly deferred to plan time
- Architecture: HIGH — topology is Architecture §3 + seam contract + gate invariants,
  all read this session; LangGraph primitives cited to official sources
- Pitfalls: HIGH — each traces to an explicit doc statement (async-only timeout,
  T0004 open, no-assumed-model rule) or a recorded open decision

**Research date:** 2026-10-16
**Valid until:** 30 days (stable domain; re-verify `langgraph`/`ollama` pins at plan time)
