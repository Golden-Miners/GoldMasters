# Phase 04 Plan 02: Wave 1 Deterministic Graph Summary

**Phase:** 04-langgraph-orchestration-local-model · **Plan:** 02 · **Wave:** 1
**Status:** complete · **Date:** 2026-10-16 · **Tasks:** 3/3
**Depends on:** 04-01 (GO: langgraph==1.2.15; AsyncSqliteSaver for async graphs)

Bounded deterministic LangGraph run over Phase 3 code — typed state, async bounded
nodes, explicit edges, pre-CEO validation barrier, gate wiring, minimal run log.
Zero model dependency; full suite green (625 passed, 2 pre-existing live-MT5 skips).

## Tasks

1. **End-to-end deterministic run (tracer)** — `state.py`, `builder.py`, `edges.py`,
   `GOLDMASTERS_GRAPH_*` settings, `test_graph_state.py`. Happy path (agent-01 setup
   bars) and chop bars both run input → gate → terminal decision. Commit `a01846d`.
2. **Bounded wrappers, validation barrier, gate wiring** — extracted `nodes.py`
   (validated async wrappers, fan-out == eligible set) and `barriers.py`
   (deterministic pre-CEO predicate, verbatim conflicts); CEO-shaped slot returns
   unavailable-with-cause. Suites: bounds/barrier/validation. Commit `234904b`.
3. **Failure policy + contract tests, full gate** — `test_graph_failure_policy.py`;
   fixed the stamp-ordering bug it exposed; updated the 3 blast-radius tests
   (declared-key set, .env example, dep allowlist). Full gate green.
   Commit `0d713c3`.

## Key files

- Created: `src/goldmasters/graph/{__init__,state,edges,nodes,barriers,builder}.py`
- Created: `tests/unit/{graph_fixtures,test_graph_state,test_graph_bounds,test_graph_barrier,test_graph_validation,test_graph_failure_policy}.py`
- Modified: `apps/api/pyproject.toml` (+`langgraph==1.2.15`), `uv.lock`,
  `apps/api/src/goldmasters_api/settings.py` (+3 keys), `.env.example`,
  `tests/unit/test_settings_startup.py`, `tests/security/test_boundary_scan.py`

## Decisions

- **TRADE unreachable in Wave 1 (fail-closed, by gate contract):** no code
  produces `risk_percent_for_idea`, so the graph passes `None` and the gate
  blocks with "idea risk unknown". Pinned by test, not just prose. A later
  phase supplying per-idea risk computation unlocks TRADE with no graph change.
- **Evidence semantics:** completed reports are VALID; `INSUFFICIENT_DATA`
  outcomes are MISSING (run → INSUFFICIENT_DATA, never NO_TRADE on partial
  evaluation); crashes are INVALID. Skipped/disabled agents carry no evidence key.
- **Retry composition:** nodes catch per-agent errors for partial-failure
  recording (no agent-level retry); node-level `RetryPolicy` stays armed for
  raising nodes and is proven by a select-level injection (2 attempts, then
  raises visibly).
- **First-setup-sorted to gate, rest verbatim to conflicts:** deterministic,
  no reconciliation; the CEO resolves later.
- **`compile()` in 1.2.15 exposes no `step_timeout`:** bound = per-node
  `TimeoutPolicy` + acyclic DAG + `recursion_limit` default. Revisit with the
  durable saver.
- **Committed on `master`:** repo precedent (04-01, Phase 3 merges all on
  master); no worktree/agent-branch setup exists in this checkout.

## Deviations

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bare `uv sync` pruned workspace members from `.venv`**
- **Found during:** Task 1 (langgraph install).
- **Issue:** `uv sync` synced only the root project (13 dev packages), deleting
  fastapi/contracts/etc. from `.venv`; `import fastapi` broke mid-plan.
- **Fix:** `uv sync --all-packages` restored all 56 workspace packages including
  langgraph 1.2.15. Future runs in this repo must use `--all-packages`.
- **Commit:** part of `a01846d` (uv.lock).

**2. [Rule 1 - Bug] select/evaluate node stamps lost from `agent_statuses`**
- **Found during:** Task 3 (`test_t0411_*` KeyError on `statuses["select"]`).
- **Issue:** `_stamp()` snapshotted statuses before the sid entries were added,
  then the overwrite dropped the node's own stamp.
- **Fix:** merge the node stamp into the final statuses dict in both nodes.
- **Commit:** `0d713c3`.

**3. [Rule 2 - Missing] Evidence/ID/datetime contract shapes**
- **Found during:** Tasks 1–3 (failing runs, not silent).
- **Issue:** Run ids must be `run_<uuid>` (closed `RunId`), decision ids
  `dec_<uuid>`; `created_at`/`data_as_of` must be datetimes, not ISO strings.
- **Fix:** `initial_state` validates via `TypeAdapter(RunId)`; mapper emits
  `dec_<suffix>` + real datetimes (`data_as_of = ctx.now_utc`).
- **Commits:** `a01846d`, `0d713c3`.

**4. [Rule 3 - Blocking] mypy vs langgraph node overloads**
- **Found during:** Task 2 (6 `call-overload` errors).
- **Issue:** An explicit `Callable[..., Awaitable[...]]` node alias never matches
  langgraph's contravariant node protocols (proven by minimal repro); bare
  `async def` does.
- **Fix:** `NodeFn` is a `Protocol` with `async __call__` (defined once in
  `state.py`). No `type: ignore` needed; mypy strict clean.

### Blast-radius updates (plan-caused, Rules 1–3)

- `test_declared_key_set` + `.env.example`: 3 new `GOLDMASTERS_GRAPH_*` keys.
- `test_dependencies_match_allowlist`: `langgraph` (legitimacy verified via
  PyPI: owner `langchain`, source github.com/langchain-ai/langgraph, MIT,
  1.2.15 released 2026-10-12, no vulns; 04-01 3.14.7 GO stands).

## Verification evidence

- `pytest` full suite: **625 passed, 2 skipped** (pre-existing live-MT5 markers).
- Plan verifies: `test_graph_state` (4), bounds+barrier+validation (16),
  `test_graph_failure_policy` (7) — all green.
- `.venv/Scripts/ruff.exe check src/ tests/ apps/ services/ packages/` — clean.
- `.venv/Scripts/mypy.exe src/ services/ apps/` — 64 files, strict clean.
- Boundary scan (`test_boundary_scan.py`, in-suite): no order paths — graph
  imports only contracts, strategies, risk, settings, langgraph, httpx.

## Known Stubs

None. (`CEO_STUB_CAUSE` is a validated unavailable-with-cause slot, not a stub:
every decision carries it in `limitations` with the T0004 cause.)

## Threat Flags

None beyond the plan register: T-04-02 (contract constructors on every node
boundary — done, incl. gate re-validation of evidence strings), T-04-03
(TimeoutPolicy + fan-out cap + optional max_concurrency — done), T-04-04
(thread_id=run_id + input snapshot hash recorded; cross-restart resume check
deferred to the durable-saver plan), T-04-SC (legitimacy gate passed, §above).

## Deferred / follow-ups (not blockers)

- Cross-restart resume with input-hash mismatch routing (needs durable saver).
- `step_timeout` revisit when the saver lands (see Decisions).
- T0004 (Ollama endpoint/models) still operator-open; CEO synthesis stays stubbed.

## Self-Check: PASSED

- All 6 graph modules + 6 test files exist on disk.
- Commits `a01846d`, `234904b`, `0d713c3` are ancestors of HEAD.
- No file deletions in any task commit (additions only, per-commit stats).
- Full suite re-run green after the final commit (625 passed).
