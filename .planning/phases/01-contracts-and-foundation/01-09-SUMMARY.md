---
phase: 01-contracts-and-foundation
plan: "09"
subsystem: observability
tags: [structlog, redaction, correlation-id, opentelemetry, tracing, middleware]

# Dependency graph
requires: [08 (lifespan + call site), 10 (log_level + trace_file_path keys)]
provides:
  - "Redacted JSON logging (processor before renderer, nested-aware, SecretStr-aware)"
  - "Server-minted per-request correlation IDs (header never adopted)"
  - "On-disk spans with correlation attributes, no collector"
affects: [later phases (C-09 body reuses the correlation ID)]

actuals:
  tokens: 0
  tasks: 3
  commits: 3
  plan_head_before: 19fae87
  plan_head_after: b124717

key-files:
  created:
    - apps/api/src/goldmasters_api/logging.py
    - apps/api/src/goldmasters_api/middleware.py
    - apps/api/src/goldmasters_api/tracing.py
    - tests/unit/test_logging_redaction.py
    - tests/unit/test_correlation_id.py
  modified:
    - apps/api/src/goldmasters_api/app.py

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "Rendered lines are JSON with event/level/timestamp/correlation_id; secrets under any key name or nesting never render."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/unit/test_logging_redaction.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fresh server-minted ID per request echoed in header and logs; forged headers rejected; context cleared; span on disk with the ID."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/unit/test_correlation_id.py (5 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "App configures logging/tracing once in lifespan from resolved settings and mounts the middleware; health still green."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_health.py"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 09: Observability Summary

**Redacted structured logs, server-minted correlation IDs end to end, and collector-free on-disk traces — wired into the app lifespan.**

## Task Commits

1. **Task 1: Logging + redaction** - `ea15652`
2. **Task 2: Middleware + tracing** - `54910fb`
3. **Task 3: App wiring** - `b124717`

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **`configure_tracing` re-configures across paths** (shuts the previous provider down first): the process-wide OTel singleton plus per-test tmp files would otherwise strand spans in the first file opened.
2. **Spans resolve through the configured provider directly**, not the process-global tracer — same reason; no collector involved either way.

## Verification Evidence

- `uv run pytest tests/unit/test_logging_redaction.py tests/unit/test_correlation_id.py tests/integration/test_health.py` → green.
- ruff + format + mypy strict clean over `apps/api`.
- A request through `create_app()` emits one redacted JSON line with its ID and one span carrying it.

## Next Phase Readiness

- Wave 5 (01-06) unblocked.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
