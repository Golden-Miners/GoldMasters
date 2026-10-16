# Phase 04 Plan 01: Wave 0 Compat Probe Summary

**Phase:** 04-langgraph-orchestration-local-model · **Plan:** 01 · **Status:** complete
**Date:** 2026-10-16 · **Wave:** 0 · **Tasks:** 2/2

Isolated langgraph/ollama install probe for Python 3.14 — verdict GO, no project files touched.

## Tasks

1. **Isolated install/import probe** — throwaway venv (`uv venv`, system CPython 3.14.7),
   `uv pip install langgraph langgraph-checkpoint-sqlite ollama`: clean resolve, imports pass,
   async graph smoke passes.
2. **T0004 operator handoff** — close-out commands recorded in probe file, item explicitly OPEN.

## Verdict (for Wave 1)

**GO.** Recommended pins: `langgraph==1.2.15`, `langgraph-checkpoint-sqlite==3.1.2`,
`ollama==0.6.3`. Transitive pins match repo exactly (`pydantic==2.14.1`, `httpx==0.28.1`).
Key finding: async nodes require `AsyncSqliteSaver`, not sync `SqliteSaver`.

## Key files

- Created: `.planning/phases/04-langgraph-orchestration-local-model/langgraph-compat-probe.md`

## Decisions

- Interpreter pin `==3.14.7` stands; no loosening needed.
- Wave 1 must use `AsyncSqliteSaver` (`langgraph.checkpoint.sqlite.aio`) for async-node graphs.

## Deviations

None — plan executed exactly as written. (Probe-env `python -m venv` failed on
ensurepip; used `uv venv --python <system 3.14.7>` instead — tooling detail, same isolation.)

## Threat flags

None. Zero tracked-file modifications (`git diff` empty); probe ran fully outside the repo;
temp env deleted after the run.

## Self-Check: PASSED

- Probe file exists with version verdict + T0004 ×3.
- `git diff --stat` empty — no src/apps/packages/test/config touched.
