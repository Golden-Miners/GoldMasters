# Wave 0 Compat Probe — langgraph + ollama on Python 3.14 (D-4.4)

**Date:** 2026-10-16 · **Verdict: GO** · **Interpreter: CPython 3.14.7** (repo pin `==3.14.7`, unchanged)

## Method

Isolated throwaway venv at `%TEMP%\lg-probe-041` via
`uv venv --python <system 3.14.7>` + `uv pip install langgraph langgraph-checkpoint-sqlite ollama`.
No `uv add`, no manifest edit, no project file touched.

## Resolved versions (latest, clean resolve on 3.14.7)

| Package | Resolved |
|---------|----------|
| `langgraph` | **1.2.15** |
| `langgraph-checkpoint-sqlite` | **3.1.2** (`langgraph-checkpoint` 4.3.0) |
| `ollama` (official PyPI client) | **0.6.3** |

Recommended Wave 1 pins: `langgraph==1.2.15`, `langgraph-checkpoint-sqlite==3.1.2`, `ollama==0.6.3`.

## Transitive-pin check (repo pins must hold)

| Pin | Repo | Resolved in probe | Match |
|-----|------|-------------------|-------|
| `pydantic==2.14.1` | apps/api | 2.14.1 | YES |
| `httpx==0.28.1` | apps/api | 0.28.1 | YES |

No conflict: latest langgraph/ollama resolve against the exact existing contract pins.

## Import check — PASS

`StateGraph`, `SqliteSaver`, `AsyncSqliteSaver`, `RetryPolicy`, `TimeoutPolicy`,
`ollama.Client` all import on 3.14.7.

## Graph smoke — PASS

Minimal async `StateGraph` (one node) compiled with `AsyncSqliteSaver`
(`:memory:`) and `ainvoke` returned `{'x': 2}`.

**Checkpointer note for Wave 1:** all Phase 4 nodes are `async def` (TimeoutPolicy
is async-only), so the checkpointer must be `AsyncSqliteSaver`
(`langgraph.checkpoint.sqlite.aio`), NOT sync `SqliteSaver` — sync saver raises
`NotImplementedError` on `ainvoke`. `aiosqlite==0.22.1` arrives transitively; pin
it explicitly if the lockfile needs it.

## T0004 — OPEN (operator-owned, D-4.1)

The probe did **not** verify any endpoint or model (localhost:11434 already
refused per 04-CONTEXT). To close T0004 the operator runs these and pastes output:

```powershell
ollama list
ollama ps
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 6
```

(or the same against the operator-configured `GOLDMASTERS_OLLAMA_HOST` if not loopback).
Needed output: endpoint host/port, installed model ids + sizes, VRAM/CPU limits,
usable context windows, per-call timeout budget.

Until T0004 output lands, all model-dependent tests in Wave 2 stay skip-gated;
deterministic graph work (T0401–T0403, T0409) proceeds regardless.
