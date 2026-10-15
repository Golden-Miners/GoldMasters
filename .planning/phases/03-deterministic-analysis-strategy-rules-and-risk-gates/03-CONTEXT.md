# Phase 3: Deterministic Analysis, Strategy Rules and Risk Gates — CONTEXT

**Discussed:** 2026-10-15 (all 5 gray areas, operator-locked)
**Inputs:** 03-RESEARCH.md (HIGH), assumptions-analyzer (codebase evidence), operator answers

## Locked decisions

1. **Scope: interfaces + gate only (D-3.1).** No strategy approved yet. Phase 3 builds
   strategy interface (`strategies/base.py`), conventions, structure/regime, levels, gate,
   role matrix. Strategy packages land only after operator supplies rules. No threshold
   literal in code; all policy via `GOLDMASTERS_` settings, hash-covered.
2. **Rounding: `decimal.ROUND_HALF_UP` (D-3.2).** Single `quantize_to_tick` in
   `domain/conventions.py`. Boundary tests pin exact-half-tick. One-line swap if broker
   mandates otherwise.
3. **Ordering: standard mirror (D-3.3).** Long `stop < entry < tp1 < tp2…`, short mirrors.
   `risk_reward` recomputed in `Decimal`, never trusted. Violation → gate BLOCK, levels null.
4. **Contract-size: optional decimal-string (D-3.4).** `contract_size: str | None`,
   `None` = unknown provenance. Minor-bump contracts change (D-23); regen schemas, no drift.
5. **DST + misorder: UTC adjacency + reject (D-3.5).** Compare UTC instants; server-local
   fold clause for ambiguous hour. Misordered analysis input → `MALFORMED` →
   `INSUFFICIENT_DATA`, never silent sort. Both-transition-weekend tests required.

## Architecture (locked from research)

- New tree `src/goldmasters/{domain,strategies,risk}/` per Architecture §7. Purity boundary:
  deterministic code imports contracts, never reverse. No `MetaTrader5` import outside
  `services/mt5_adapter/terminal.py`. Stdlib only (`decimal`, `zoneinfo`); TA-Lib/pandas
  rejected (float64 breaks tick alignment).
- Closed bars only. Unknown regime → `UNKNOWN` → no setup. Any rule fail → no setup,
  no levels. Gate is sole path to TRADE-eligible levels.

## Explicit non-goals

- No approved strategy code. No LLM-backed agent nodes (Phase 4). No new endpoints.
  `code_hash` is integrity label, not tamper-proofing.

## Open (operator-owned, unchanged)

- Live MT5 run (Phase 2 Task 3) + DST transition ground truth vs live server clock.
- Future: strategy approvals with rule parameters + hard risk limits.

## Next

Planner creates PLAN.md files against D-3.1…D-3.5. Research + analyzer evidence stand;
do not re-ask locked items.
