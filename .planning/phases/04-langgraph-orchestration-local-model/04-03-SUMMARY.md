# Phase 04 Plan 03: Wave 2 Model Runtime Summary

**Phase:** 04-langgraph-orchestration-local-model · **Plan:** 03 · **Wave:** 2
**Status:** complete · **Date:** 2026-10-16 · **Tasks:** 3/3
**Depends on:** 04-01 (GO) + 04-02 (complete)
**Commits:** `41c9884` (tracer), `5227881` (roles), `487f1c8` (outage + gate)

Ollama endpoint config + health + runtime discovery plugging into the Wave 1
validated slots; LLM nodes restricted to synthesis/explanation roles. T0004
stays operator-open — no model name, hardware, or context window assumed.

## Tasks

1. **End-to-end discovery-to-health run slot (tracer)** — `runtime.py`
   (`AsyncClient` binding, run-start `list()` discovery, reachable +
   expected-model health, measured run record) + `GOLDMASTERS_OLLAMA_HOST`
   (loopback-only allowlist) / `OLLAMA_MODEL` (no default) settings keys.
   Live test skip-passes without a server; stub tests prove the path.
   Commit `41c9884`. ⚡ Tracer verified end-to-end — expanded.
2. **LLM role nodes on validated slots** — `agents/prompts.py` (4 builders) +
   `agents/parse.py` (`ContractModel` schemas, evidence/reason strings only,
   `model_validate_json` gate). Temperature 0, format-pinned, bounded retry
   then fail-closed. Commit `5227881`.
3. **Outage + failure-policy remainder, full gate** — `check_ceo_required`
   (failed required agent blocks prose without a model call),
   outage → `INSUFFICIENT_DATA`-shaped errors never TRADE, blast-radius
   updates, full suite green. Commit `487f1c8`.

## Key files

- Created: `src/goldmasters/graph/runtime.py`, `src/goldmasters/agents/{__init__,prompts,parse}.py`
- Created: `tests/integration/test_ollama_discovery.py`, `tests/unit/test_graph_nodes_roles.py`
- Modified: `apps/api/.../settings.py` (+2 keys), `apps/api/pyproject.toml` (+`ollama==0.6.3`, +`langgraph-checkpoint-sqlite==3.1.2`), `uv.lock`, `src/.../barriers.py` (+`check_ceo_required`), `.env.example`, `test_settings_startup.py`, `test_boundary_scan.py`, `Task.md`, `Memory.md`

## Decisions

- **Discovery, not assumption (criterion 5):** `list()` inventory is whatever
  the server reports; `ollama_model=None` never matches; absent model after
  bounded retries returns a sanitized error — callers record
  `INSUFFICIENT_DATA`, never a silent fallback model.
- **Transport set is httpx pair + refused/reset (`ConnectionError`):** a
  refused loopback endpoint raises builtin `ConnectionError` outside httpx
  wrapping (measured, not assumed) — retries bounded, then fail-closed.
- **Parse failures share the attempt budget:** transport and
  `model_validate_json` failures retry within `1 + graph_node_max_retries`
  total tries; unexpected errors return immediately as sanitized
  `INTERNAL_ERROR` (never retried blindly, never raised).
- **CEO agreement is structural:** `check_ceo_required(statuses, required)`
  blocks prose on any missing/non-ok required node; the model is never
  consulted on that path (call-count assertion pinned).
- **`AsyncSqliteSaver` pinned but NOT wired:** dep `3.1.2` in the manifest for
  the durable-saver plan; swapping `builder.py` off `InMemorySaver` would churn
  every graph test and is out of this plan's file scope — deferred, recorded.
- **Role nodes are units, not graph nodes yet:** `generate()` + schemas are
  tested standalone; wiring into `builder.py` is a later plan (CEO slot in
  `assemble_decision` still carries `CEO_STUB_CAUSE`).
- **Committed on `master`:** repo precedent (04-01, 04-02, Phase 3); no
  worktree/agent-branch setup in this checkout.

## Deviations

### Auto-fixed Issues

**1. [Rule 1 - Bug] Refused loopback raised outside the transient set**
- **Found during:** Task 1 verify (`attempts == 1`, immediate error).
- **Issue:** `AsyncClient.list()` against a refused port raises builtin
  `ConnectionError`, not `httpx.ConnectError` — first attempt bailed to the
  non-transient branch, so no bounded retry happened.
- **Fix:** `TRANSIENT_ERRORS` gains builtin `ConnectionError` (refused/reset
  are transport-level); measured via direct probe before/after.
- **Commit:** `487f1c8`.

**2. [Rule 1 - Bug] `test_health` forbids `ollama` in `sys.modules`**
- **Found during:** Task 3 full gate (collection imports every test module).
- **Issue:** Top-level `from ollama import ...` in the two new test files
  polluted the process before `test_import_pulls_no_terminal_or_model_runtime`.
- **Fix:** All `ollama` + `graph.runtime` imports in the two new test files
  moved to function level / `TYPE_CHECKING`; production import graph untouched
  (the API never imports the model runtime).
- **Commit:** `487f1c8`.

**3. [Rule 2 - Missing] SDK looseness vs mypy strict**
- **Found during:** Task 3 gate (`mypy` 3 errors).
- **Issue:** `ListResponse.Model.model/digest` and `ChatResponse.message.content`
  type as `Optional` in `ollama==0.6.3`.
- **Fix:** `DiscoveredModel` fields honestly `str | None` (absence recorded,
  never filled); missing content validates as empty → schema rejects → fail
  closed. PEP 695 `def f[T: ...]` for the two generics (ruff UP047).
- **Commit:** `487f1c8`.

### Blast-radius updates (plan-caused, Rules 1–3)

- `test_declared_key_set` + `.env.example`: 2 new `GOLDMASTERS_OLLAMA_*` keys.
- `test_dependencies_match_allowlist`: `ollama`, `langgraph-checkpoint-sqlite`
  (04-01 GO pins; official `ollama/ollama-python` + `langchain-ai` orgs,
  transitive `pydantic==2.14.1`/`httpx==0.28.1` hold per probe).
- `Task.md`: T0411 checked; T0404/T0405/T0406/T0410 annotated partial (prose
  roles landed; deterministic agents/adapters + graph wiring pending).

## Verification evidence

- Full suite: **643 passed, 3 skipped** (2 pre-existing live-MT5 + 1
  ollama-live skip with reason — T0004 open, no server here).
- Plan verifies: `test_ollama_discovery` (8: live-or-skip, outage×2,
  stub inventory, unset-model, host allowlist, shape pin),
  `test_graph_nodes_roles` (11: specs, no-number schemas, valid/malformed
  per-role, schema+temp-0 pin, parse retry, prompts, CEO block, import
  boundary).
- `.venv/Scripts/ruff.exe check src/ tests/ apps/ services/ packages/` — clean.
- `.venv/Scripts/mypy.exe src/ services/ apps/` — 68 files, strict clean.
- Boundary scan (in-suite): no order paths; model path imports
  `ollama/httpx/contracts/settings` only (pinned by test).
- No model-name literal in `src/` or settings (grep-verified; names live only
  in settings values and test fixtures).

## Known Stubs

None. (`CEO_STUB_CAUSE` remains the validated unavailable-with-cause slot;
`ollama_model=None` is a fail-closed default, not a stub.)

## Threat Flags

Covered by the plan register, all mitigated and tested: T-04-05 (schema pin +
`model_validate_json` + per-role injection tests; no level/regime/score field
exists on any output schema), T-04-06 (loopback-only validator rejects public
URLs at startup; client built solely from the declared endpoint),
T-04-07 (CEO levels only from `trade_eligible_levels`; `check_ceo_required`
+ deterministic barrier/gate unpromptable), T-04-SC (04-01 pins + legitimacy
prose; no new install beyond the GO verdict).

## T0004 — still OPEN (operator-owned)

No endpoint, model inventory, hardware, or context limits were assumed or
recorded here. To close, the operator runs (from the 04-01 probe file):

```powershell
ollama list
ollama ps
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 6
```

then sets `GOLDMASTERS_OLLAMA_HOST` (loopback) + `GOLDMASTERS_OLLAMA_MODEL`
(confirmed id) and re-runs `pytest tests/integration/test_ollama_discovery.py -q`
expecting the live test to pass instead of skip.

## Deferred / follow-ups (not blockers)

- `AsyncSqliteSaver` builder wiring + cross-restart resume check.
- Role-node wiring into `build_graph` (analyst/news/research/CEO slots).
- Trend/Instrument deterministic agents, news retrieval adapters, signaling.

## Self-Check: PASSED

- `runtime.py`, `agents/{prompts,parse}.py`, both test files exist on disk.
- Commits `41c9884`, `5227881`, `487f1c8` are ancestors of HEAD.
- No file deletions in any task commit (additions/edits only).
- Full suite re-run green after the final commit (643 passed).
