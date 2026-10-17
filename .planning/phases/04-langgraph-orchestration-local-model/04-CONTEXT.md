# Phase 4: LangGraph Orchestration and Local Model Runtime — CONTEXT

**Discussed:** 2026-10-16 (4 gray areas, operator-locked)
**Inputs:** 04-RESEARCH.md (HIGH), Ollama probe (localhost:11434 refused), operator answers

## Locked decisions

1. **Deterministic-first (D-4.1).** Build bounded graph + pre-CEO validation barrier +
   schema-per-node validation now against Phase 3 code. Model runtime plugs in when
   T0004 clears. No model-dependent plan blocks deterministic work (T0401–T0403, T0409).
2. **Balanced bounds (D-4.2).** 60s per-node timeout, 2 retries on transient transport
   errors only. Validation failures, gate blocks, NOT_APPLICABLE are routing signals —
   never retried. Fail-closed `GOLDMASTERS_GRAPH_*` settings, hash-covered.
3. **Minimal run log (D-4.3).** Phase 4 persists run_id, input ref, config/version ids,
   timestamps, per-node status. Outcomes + journal stay Phase 6. Boundary test pins it.
4. **Wave 0 compat probe (D-4.4).** Isolated pip-install probe of langgraph on Python
   3.14 records version verdict; no project files touched. Pins locked after verdict.

## Architecture (locked from research)

- Nodes call Phase 3 code (selection, levels, gate) — never re-implement numbers.
- All nodes `async def` (LangGraph TimeoutPolicy is async-only); httpx timeouts back up
  the Ollama client. RetryPolicy.retry_on covers transient transport only.
- Failure policy: critical node failure → INSUFFICIENT_DATA or NO_TRADE; no path ends
  in unqualified TRADE. Gate stays sole path to TRADE-eligible levels.

## Open (operator-owned)

- T0004: Ollama endpoint, installed models, hardware/context limits.
- ~40 strategy threshold values (unchanged, still gate real TRADE content).

## Next

Planner creates PLAN.md files against D-4.1…D-4.4. Do not re-ask locked items.
