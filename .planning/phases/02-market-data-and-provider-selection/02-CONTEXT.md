# Phase 2: Market Data and Provider Selection - Context

**Gathered:** 2026-10-15
**Updated:** 2026-10-24
**Status:** Ready for planning

## Phase Boundary

The operator selects provider `mt5` and instrument `xauusd` (H1) and receives real, validated, provenance-stamped bars and quotes from the live MT5 terminal — or a visible, structured failure. MT5 is the only adapter; silver/forex/oil/BTC/ETH join in later work, not this phase.

## Implementation Decisions

### Provider lineup

- **D-44:** MT5 is the only adapter in Phase 2. The common provider interface is proven by a single real implementation; a second source is later-phase work.
- **D-45:** The adapter connects to the operator's live terminal with their live account (no demo, no missing-terminal fallback build).
- **D-46 [UPDATED]:** Any MT5 session mode (investor/master/demo/live) is acceptable for reading market data. GoldMasters is signals-only — it never places or modifies orders — so `trade_allowed` being `True` is not a blocker. The account authenticates with whatever credentials the operator uses to log in.
- **D-47:** Our system never handles credentials: the adapter attaches to the already-logged-in terminal. No `GOLDMASTERS_MT5_*` secret keys are introduced. — **Reversibility:** costly — switching to credential-handling later means adding secret plumbing, startup validation and redaction coverage for a new secret class.

### MT5 access mechanics

- **D-48:** `provider_id` stays the generic key `mt5` (D-25 form). No broker suffix is encoded; broker identity is revisited only if a second terminal ever appears.
- **D-49 [UPDATED]:** MT5 terminal is auto-started by the API via `TerminalManager` when `GOLDMASTERS_MT5_TERMINAL_PATH` is configured. Operator no longer needs to launch manually. The operator still enables symbols in Market Watch by hand. The adapter only reads what the terminal exposes and reports anything else unsupported (D-28); it never changes terminal state.
- **D-50:** Terminal closed, logged out, or market shut reads as unavailable: health reports disconnected/terminal-closed and downstream goes INSUFFICIENT_DATA. Last-known bars are never served as if fresh.
- **D-51:** Mid-session drops fail fast: one quick retry, then disconnected. Slow backoff and operator-configured retry budgets are rejected.

### First instruments

- **D-52:** Gold first and only: instrument `xauusd` mapped and proven end to end. Silver/forex/oil/BTC/ETH are explicitly later work, not stretch goals of this phase.
- **D-53:** The provider symbol is resolved at runtime through `SymbolResolver`. First match found: `GOLD.i#` (broker-specific), then `XAUUSD`, then aliases. `instrument_id` is `xauusd`, `provider_symbol` is whatever the broker exposes (D-17 separation).
- **D-54:** H1 is the only timeframe that must work. Other enum members are rejected as unsupported (D-54), never half-supported.

### Freshness thresholds

- **D-56:** An H1 bar older than two closed bars (~2h) reads stale. The limit is timeframe-relative, not a wall-clock constant.
- **D-57:** Quote staleness is session-aware: tighter in London/New York overlap, looser in Asian hours. The researcher maps sessions to concrete limits for planning.
- **D-58:** The weekend gap is an expected, honestly flagged interval (known market-hours gap), never `missing-history`. The adapter resumes cleanly at open.
- **D-59:** All limits live as `GOLDMASTERS_` settings keys with sane defaults: operator-tunable without code changes and captured by the config hash (D-15/D-27).

### Symbol resolution

- **D-60 [NEW]:** Canonical instrument IDs (`xauusd`, `xagusd`, `btcusd`, `ethusd`, `usoil`, `eurusd`) are the single source of truth. `SymbolResolver` queries `symbols_get()` from the live terminal, ranks exact match > alias match > partial match, and rejects ambiguous matches. Never substitutes silently.
- **D-61 [NEW]:** Broker-specific aliases are configurable through `BROKER_SYMBOL_ALIASES` in code, not runtime config. Default aliases per instrument cover common broker variations (e.g., `xauusd` → `GOLD.i#`, `XAUUSD`, `XAUUSDm`, `GOLD`, `XAUUSD+`, `XAUUSD#`, `Gold`, `gold`, `XAUUSD.m`, `GOLD.i`).
- **D-62 [NEW]:** Resolution results are cached per session. Cache refreshes on startup and again when a symbol lookup fails (re-query broker before reporting unsupported).
- **D-63 [NEW]:** If MT5 can't attach after `GOLDMASTERS_MT5_STARTUP_TIMEOUT_SECONDS` (default 10s), FastAPI server fails to start (fail-fast, not graceful degradation).

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contracts and decisions (locked)

- `.planning/phases/01-contracts-and-foundation/01-CONTEXT.md` — D-16/D-28 (timeframe mapping inside adapter), D-17 (ID separation), D-19/D-24/D-26 (precision from `get_instrument_spec`), D-20/D-22 (quality vocabulary), D-25 (provider key form)
- `Schema.md` §4 — market bar/quote fields and validation invariants
- `Schema.md` §5 — provider contract (`provider_id`, `get_bars`, `get_latest_quote`, `get_instrument_spec`, explicit selection, no silent fallback)
- `.planning/REQUIREMENTS.md` — REQ-instrument-provider-selection, REQ-market-data-ingestion-validation

### Existing code (reuse)

- `packages/contracts/src/goldmasters_contracts/market.py` — `MarketBar`/`MarketQuote` the adapter fills
- `packages/contracts/src/goldmasters_contracts/precision.py` — empty table Phase 2 populates
- `packages/contracts/src/goldmasters_contracts/ids.py` — `ProviderId` form
- `apps/api/src/goldmasters_api/settings.py` — where D-59 keys are declared
- `apps/api/src/goldmasters_api/health.py` — `probe_database` pattern for the provider health shape

### Existing Code Insights

### Reusable Assets

- `PrecisionTable.with_row` / `lookup`: append-only history the spec adapter writes, audit reads
- `Settings` + `hash_effective_config`: threshold keys join the hashed config automatically
- `probe_database` (bounded, quiet, never raises): template for terminal presence checks

### Established Patterns

- Fail-closed validation with named keys (D-36) applies to every new setting and every adapter error
- Purity boundary (D-03/D-08): provider code lives outside `goldmasters-contracts`; the package gains no dependency
- Boundary scan (D-37): the adapter must not introduce order-capable imports or the build fails

### Integration Points

- New `services/mt5_adapter` tree per the adopted layout (D-41); wired into `apps/api` without touching contract models
- Provider health joins the `/health` surface

## Specific Ideas

No specific requirements — open to standard approaches.

## Deferred Ideas

- Second market-data source alongside MT5 — later phase (D-44)
- Silver/forex/oil/BTC/ETH symbol mapping — later work after gold path proves out (D-52)
- Additional timeframes beyond H1 — later work (D-54)
- Symbol refresh TTL (periodic re-query regardless of failures) — future consideration if broker symbols change frequently

---

*Phase: 02-Market Data and Provider Selection*
*Context gathered: 2026-10-15*
*Context updated: 2026-10-24 (MT5 auto-start, symbol resolver aliases, cache refresh on miss, startup fail-fast)*