# Phase 2: Market Data and Provider Selection — Research

**Written:** 2026-10-15
**Status:** Ready for planning
**Sources:** mql5.com Python Integration docs (fetched 2026-10-15), repo code as cited, D-44–D-59 / D-03 / D-08 / D-37.

---

## 1. MetaTrader5 Python package API surface

Docs root: `https://www.mql5.com/en/docs/python_metatrader5` (package installs via `pip install MetaTrader5`; author MetaQuotes Software Corp.).

### Connection: read-only attach (D-45/D-46/D-47)

- `mt5.initialize()` **with no arguments** attaches to the already-running, already-logged-in terminal (docs: "the terminal for connection is found automatically"; "if required, the terminal is launched"). This is the D-47 pattern: the adapter calls **bare `initialize()` only — never `initialize(login=, password=, server=)` and never `mt5.login()`**. No credential ever enters our code, config, logs, or traces; no `GOLDMASTERS_MT5_*` *secret* keys exist.
- Investor-password enforcement is therefore **verified, not performed**: after `initialize()`, check `mt5.terminal_info().trade_allowed` (False under an investor login) and `mt5.account_info()` trade-mode fields, and refuse to proceed unless read-only. D-46 ("master password rejected") becomes a runtime assertion in `health_check`, not a login flow. **Caveat:** exact `account_info`/`terminal_info` field names must be confirmed against the installed package version at implementation time — the package is NOT installed in this environment (RISK-03), so field names below are from docs, not verified imports.
- `mt5.shutdown()` closes the IPC connection (does not close the terminal). `mt5.version()` → `(version, build, date)`; use the build string as `provider_spec_version` for precision rows (§4).

### Data functions (all we need; all read-only)

| Call | Shape | Use |
|---|---|---|
| `copy_rates_from_pos(symbol, timeframe, start_pos, count)` | numpy array, named cols `time, open, high, low, close, tick_volume, spread, real_volume`; `start_pos=0` = current **forming** bar; returns `None` on error | Primary bars call. Request small N (proposed `GOLDMASTERS_MT5_BARS_COUNT`, default 10); **drop pos-0 forming bar**, validate closed bars only (D-55 "closed H1 bars") |
| `copy_rates_range(symbol, timeframe, start, end)` | Same columns, datetime window | Backfill / gap re-check only, not the hot path (datetime inputs are server-timezone-sensitive; from_pos avoids that) |
| `copy_rates_from(symbol, timeframe, start_datetime, count)` | Same columns from a date | Alternative hot path; from_pos preferred (no clock input, no TZ ambiguity) |
| `symbol_info_tick(symbol)` | Tuple `(time, bid, ask, last, volume, time_msc, flags, volume_real)`; `None` on error; note `last=0.0, volume=0` is normal for XAUUSD (no last price) — must map to `None`, never `0.0` as a price (Schema §4 "do not invent") | `get_latest_quote`. `time_msc` is the authoritative tick instant |
| `symbol_info(symbol)` | Namedtuple (~96 fields): `digits, point, trade_tick_size, trade_tick_value, trade_contract_size, select, visible, bid/ask/last, time, ...` | `get_instrument_spec` + read-only Market Watch check (`select`/`visible` flags) |
| `symbols_get()` / `symbols_total()` | Full symbol list | Capability reporting (supported vs unsupported), never for auto-substitution |

### `symbol_select` semantics vs D-49

- `symbol_select(symbol, True)` **mutates terminal state** (adds to Market Watch). D-49 forbids the adapter from changing terminal state, so the adapter **must never call it**. Read-only check instead: `info = symbol_info("XAUUSD")`; if `info is None` or `not info.visible` → structured `unsupported` failure (D-28/D-49). The operator enables the symbol by hand.
- Enforcement: add `symbol_select` to the repo-wide forbidden-call list for the adapter (see §6 boundary-scan note) — AST scan cannot easily distinguish `True`/`False` args, so forbid the name entirely in `services/mt5_adapter`.

### `last_error()` codes (verified from docs page)

`(code, description)` tuple. Planner-relevant mapping:

| Code | Value | Adapter meaning |
|---|---|---|
| `RES_S_OK` | 1 | success |
| `RES_E_FAIL` | -1 | generic fail → `disconnected` (after 1 retry, D-51) |
| `RES_E_INVALID_PARAMS` | -2 | bad symbol/timeframe args → `unsupported` (do NOT retry) |
| `RES_E_NO_MEMORY` | -3 | `disconnected`, retryable once |
| `RES_E_NOT_FOUND` | -4 | **no history** → `missing-history` (distinct from gap) |
| `RES_E_AUTH_FAILED` | -6 | logged out → `terminal-closed`/`disconnected`, surfaced visibly |
| `RES_E_UNSUPPORTED` | -7 | unsupported method → `unsupported` |
| `RES_E_AUTO_TRADING_DISABLED` | -8 | irrelevant for reads; treat as `disconnected` if seen |
| `RES_E_INTERNAL_FAIL*` | -10000…-10005 (incl. TIMEOUT -10005) | IPC/terminal-down → `terminal-closed` (init fails) or `disconnected` (mid-session) |

Rule: every `None` return or `initialize()==False` is followed by exactly one `last_error()` capture (sanitized into logs only, never into API `details` verbatim — C-09 redaction), then mapped to the table above.

### Timezone handling (critical)

- **Bar `time` is MT5 *server* time (seconds since epoch), not UTC.** The rates payload carries no timezone. Conversion to UTC requires the server offset, which the package does not report directly.
- Contract requires `bar_open_time`/`retrieved_at` as tz-aware UTC + preserved IANA `source_timezone` (`_base.py:74-95`; IANA name must be a real zoneinfo name).
- Plan therefore needs: (a) a non-secret `GOLDMASTERS_MT5_SERVER_TIMEZONE` IANA setting (operator-set to the broker's server zone; typical MT5 servers run EET with DST — operator confirms the actual value against the terminal's Market Watch clock, documented not invented); (b) conversion `server-local → UTC` via zoneinfo at normalization time; (c) a startup/periodic sanity check comparing terminal time (`symbol_info("XAUUSD").time`) against UTC now — if the implied offset disagrees with the setting by more than the configured tolerance, report `disconnected`/misconfigured rather than stamping wrong times (R-04 "no timezone assumption"). Candle-boundary semantics beyond H1 alignment stay deferred to Phase 3 per D-13/D-16.
- Tick `time`/`time_msc`: same server clock; same conversion.

### Weekend / market-closed behavior

- The package has **no "market closed" signal**: when gold is closed, `copy_rates_*` simply returns no new bars and `symbol_info_tick` returns the last Friday tick with a stale `time_msc`. Weekend detection is therefore clock + calendar logic in our code (§3), and a closed terminal (`initialize()==False`) vs logged-out (`RES_E_AUTH_FAILED`) vs market-shut (connected, data stale, weekend window) must map to distinct health states per D-50: `terminal-closed` / `disconnected` / expected-gap. Never serve last-known bars as fresh (D-50).

---

## 2. Provider interface design

- **Location:** `services/mt5_adapter/` (D-41) plus a thin `MarketDataProvider` Protocol in `apps/api` or `src/goldmasters/data/providers/` — **never in `goldmasters-contracts`** (purity boundary D-03/D-08; contracts gains no dependency, no new module).
- **Protocol (from Schema §5 / C-04b, D-55):** `provider_id: "mt5"` literal; `display_name`; `capabilities()` → supported instruments/timeframes for the *connected* terminal; `health_check()`; `get_bars(instrument_id, provider_symbol, timeframe, start, end)`; `get_latest_quote(instrument_id, provider_symbol)`; `get_instrument_spec(instrument_id, provider_symbol)`. Single MT5 implementation proves the interface (D-44).
- **Explicit selection, no silent fallback (C-04b, D-25, D-48):** selection = `GOLDMASTERS_PROVIDER_ID=mt5` + `GOLDMASTERS_INSTRUMENT=xauusd` settings (or per-request params validated against them); every retrieval stamps `provider_id="mt5"`; any substitution attempt is a structured error, never a fallback. `provider_id` stays bare `mt5`, no broker suffix (D-48).
- **ID separation (D-17/D-53):** `instrument_id="xauusd"` (canonical, validated by the existing pattern in `market.py:35-53`) vs `provider_symbol="XAUUSD"` (opaque string passed to MT5, echoed back verbatim). Broker-suffixed variants (e.g. `XAUUSDm`, `XAUUSD.pro`) are NOT auto-resolved — unknown symbol → `unsupported`. Only `xauusd`→`XAUUSD` mapping ships (D-52/D-53); silver/forex/oil/BTC/ETH are later work, and the mapping table must be data (dict/setting), not code branches, so adding symbols is config + test.
- **Unsupported shape:** reuse the existing closed `ErrorCode` — `UNSUPPORTED_INSTRUMENT` / `UNSUPPORTED_TIMEFRAME` (note: typo `INSTRUMENT` is locked in `errors.py:30`; **do not rename** — renaming is a breaking change per D-23; use as-is). Non-retryable (`retryable` forced by code, `errors.py:58-81`). Quality side: `quality_status="unsupported"` (closed `QualityStatus` enum, `enums.py:97-116`) on the bar/quote shell or health object. Non-H1 timeframes → `UNSUPPORTED_TIMEFRAME` even though the `Timeframe` enum lists them (D-54: enum membership ≠ adapter support; capability report lists H1 supported, rest unsupported).

## 3. Validation pipeline

Two layers per D-04 ("contract invariants now, policy later"): Pydantic (`MarketBar`/`MarketQuote` validators already enforce finite-positive prices, OHLC ordering, ordered timestamps, spread==ask-bid — `market.py:85-165`) stays untouched; Phase 2 adds a **deterministic policy module** (new file, e.g. `services/mt5_adapter/validation.py`) performing, in order per retrieval:

1. **finite** — reject NaN/Inf (defense in depth; contract also rejects).
2. **ordering** — strictly increasing `bar_open_time`; `bar_close_time == bar_open_time + 1h` for H1 (alignment; boundary semantics detail deferred to Phase 3, H1 arithmetic is exact).
3. **duplicate** — same `bar_open_time` twice → flag `duplicate`, keep first, audit-log the drop (Schema §4: flagged, not silently removed).
4. **gap** — expected hourly sequence broken → flag `gap`; then classify (§3 weekend rule): inside known-closed window → expected flagged interval (D-58); outside → `missing-history` trajectory.
5. **OHLC** — contract-level; policy layer only adds tick-size alignment *if* precision row exists (unknown precision → skip, never invent).
6. **volume_type preserved** — MT5 `tick_volume` → `volume=Decimal(tick_volume)`, `volume_type=tick`; `real_volume` is 0 for XAUUSD (no central exchange) → ignored, **never** mapped to `exchange` (R-04.3). Both zero/absent → `volume=None`, `volume_type=not_available`.
7. **freshness** — below.

### Quality vocabulary (closed, `enums.py:97-116`; D-20)

`quality_status` single value + `quality_flags` list from the same set: `stale, duplicate, gap, malformed, disconnected, missing-history, unsupported` (+ `not_evaluated`, never healthy, never emitted by Phase 2 code). Healthy bars carry the… **gap in current enum**: there is no `ok`/`valid` member — Phase 1 only emitted `not_evaluated` and "thresholds and the computing code stay in Phase 2" (`enums.py:97-102`). **Planning must decide**: add a healthy member (minor bump per D-23, vocabularies only grow) or reuse `not_evaluated`-with-empty-flags — the latter contradicts D-22's "never healthy" framing. Recommended: add `QualityStatus.OK = "ok"` (minor bump, documented in plan). Do not work around it.

### Freshness thresholds (D-56/D-57; concrete proposal for planning to confirm)

- **Bars (D-56, timeframe-relative):** last *closed* H1 bar is stale when `now_utc - bar_close_time > 2 × 1h + grace`. Default `GOLDMASTERS_BAR_STALE_CLOSED_BARS=2`, `GOLDMASTERS_BAR_STALE_GRACE_SECONDS=300`. (~2h per D-56.)
- **Quotes (D-57, session-aware, UTC hours, standard-time basis; DST shifts ±1h — operator confirms against broker):**

| Session (UTC approx) | Window | Proposed default |
|---|---|---|
| London/NY overlap (high liquidity) | 13:00–16:30 | `GOLDMASTERS_QUOTE_STALE_SECONDS_OVERLAP=30` |
| London *or* NY open | 08:00–13:00, 16:30–21:00 | `GOLDMASTERS_QUOTE_STALE_SECONDS_MAJOR=60` |
| Asia only | 00:00–08:00 | `GOLDMASTERS_QUOTE_STALE_SECONDS_ASIA=180` |
| Off-hours (21:00–00:00) | shoulder | `GOLDMASTERS_QUOTE_STALE_SECONDS_OFFHOURS=300` |
| Weekend closed (Fri ~21/22:00 UTC – Sun ~22:00 UTC, broker-dependent) | closed | quotes expected-absent → `unavailable`, **not** `stale`; no threshold applies |

Values are proposed defaults for operator confirmation against the live terminal, explicitly labelled as such (REQ "no invented defaults" = configured + documented, which D-59 settings satisfy). Session determination is pure UTC-clock logic on `retrieved_at`; session boundaries themselves are settings (`GOLDMASTERS_SESSION_*`) so DST/broker drift is operator-tunable without code change.

### Weekend-gap vs missing-history rule

- `now_utc` inside weekend-closed window → any absent bars/quotes in the window = expected flagged interval: bars present on either side get `quality_flags=[gap]`, no `missing-history`; health stays `connected` with `market_open=false`.
- `now_utc` outside closed windows and `copy_rates_from_pos` returns fewer closed bars than requested, or sequence gaps appear mid-week → `quality_status="missing-history"` (bars) and health `missing-history`; downstream maps to `INSUFFICIENT_DATA`, never synthesis (R-04.5).
- Daily gold maintenance break (~21:00–22:00 UTC, broker-dependent): allow a 1-bar gap tolerance adjacent to the break window (setting `GOLDMASTERS_DAILY_BREAK_UTC="21:00-22:00"`, operator-confirmed); larger gaps → `missing-history`.

### INSUFFICIENT_DATA downstream mapping

Any retrieval ending in `stale / disconnected / missing-history / unsupported / malformed` yields **no `MarketBar` presented as healthy**; the API layer maps to C-09 error (retryable only for transient `disconnected`, per `RETRYABLE_CODES`) and any future graph run records `insufficient_data`. The adapter itself never emits decisions — it returns typed results with provenance (`retrieved_at`, `source_timezone`, `provider_id`, `provider_symbol`) and explicit errors (Schema §5).

## 4. Precision table population

- Source fields from `symbol_info("XAUUSD")`: `digits` → `decimals` (int), `point` → `tick_size` (str, e.g. `"0.01"`), `trade_contract_size` recorded in provenance/details. `provider_spec_version` = terminal build from `mt5.version()` (e.g. `"build 4570"`); nothing in `symbol_info` versions the spec, so build + `retrieved_at` is the provenance (D-24).
- Write path: `get_instrument_spec` returns spec → API layer appends via existing `PrecisionTable.with_row` (`precision.py:77-79`); never overwrite; set `valid_from=retrieved_at`, leave `valid_to` open; supersede by appending (D-24/D-26: audit resolves row in force at payload `retrieved_at`). Table still ships empty until first successful spec fetch (D-19 zero-row conformance case stays green).
- No contracts change: `PrecisionRow`/`PrecisionTable` already carry all needed columns (`precision.py:33-97`).

## 5. Settings, health, API exposure

### Settings keys (all `GOLDMASTERS_`, non-secret → auto-hashed by `hash_effective_config`, `settings.py:100-113`; fail-closed per D-36)

| Key | Proposed default | Notes |
|---|---|---|
| `GOLDMASTERS_PROVIDER_ID` | `"mt5"` | validated against `ProviderId` pattern |
| `GOLDMASTERS_INSTRUMENT_ID` | `"xauusd"` | canonical ID |
| `GOLDMASTERS_MT5_SYMBOL` | `"XAUUSD"` | provider symbol (D-53 observed value) |
| `GOLDMASTERS_TIMEFRAME` | `"H1"` | closed enum member |
| `GOLDMASTERS_MT5_SERVER_TIMEZONE` | *(no default — required, operator-set IANA name)* | fail-closed startup if missing/invalid (D-36); IANA validated by existing `IanaTimezone` type |
| `GOLDMASTERS_MT5_PROBE_TIMEOUT_SECONDS` | `2` | mirrors `_PROBE_TIMEOUT_SECONDS` (`health.py:23`) |
| `GOLDMASTERS_MT5_RETRY_ATTEMPTS` | `1` | D-51 one quick retry |
| `GOLDMASTERS_MT5_RETRY_DELAY_MS` | `500` | "quick" quantified; fail fast |
| `GOLDMASTERS_MT5_BARS_COUNT` | `10` | from_pos window |
| `GOLDMASTERS_BAR_STALE_CLOSED_BARS` | `2` | D-56 |
| `GOLDMASTERS_BAR_STALE_GRACE_SECONDS` | `300` | |
| `GOLDMASTERS_QUOTE_STALE_SECONDS_{OVERLAP,MAJOR,ASIA,OFFHOURS}` | `30,60,180,300` | D-57 table above |
| `GOLDMASTERS_SESSION_*` / `GOLDMASTERS_WEEKEND_CLOSE_UTC` / `GOLDMASTERS_DAILY_BREAK_UTC` | windows above | operator-tunable, broker-confirmed |

### Health endpoint (follow `probe_database` pattern, `health.py:26-53`)

- New `probe_mt5()` in adapter: bounded (timeout setting), **never raises** (False/status on any exception), never leaks paths/logins/raw MT5 payloads. `GET /health` gains a `provider` object: `{provider_id, status, market_open, terminal_build, last_bar_close_time, last_quote_time, checked_at}` where `status ∈ {connected, terminal-closed, disconnected, missing-history, unsupported-symbol}` — the five D-50/Phase-2-criterion-6 states, distinct strings. Do NOT expose account login/server names (unneeded surface; C-01 no secrets in schemas).
- Status precedence when multiple hold: `terminal-closed` > `disconnected` > `unsupported-symbol` > `missing-history` > `stale` > `connected` (plan to confirm; rationale: connectivity before data quality).

### API exposure (minimal)

- `/health` provider join (above) — satisfies "status" visibility.
- One read-only bars endpoint + one quote endpoint (e.g. `GET /v1/market/bars?instrument_id=xauusd&timeframe=H1`, `GET /v1/market/quote?instrument_id=xauusd`) returning `MarketBar`/`MarketQuote` JSON — satisfies REQ "shows … last successful retrieval, latest candle timestamp and status". No POST, no params beyond instrument/timeframe/count, loopback-only unchanged (D-34). Timezone field in responses stays per-contract (`source_timezone` preserved + UTC instants).

## 6. Testing strategy without live terminal in CI

Constraint: CI/gate has no terminal, package likely uninstallable there; R-09.6 forbids live-market-dependent tests; R-01/R-09.7 require labelled fixtures never served live.

- **Seam:** all `MetaTrader5` imports live in one gateway module (`services/mt5_adapter/terminal.py`) imported **lazily inside functions** (`importlib`), so collection/import never fails without the package. The gateway exposes a narrow typed protocol (`initialize, copy_rates_from_pos, symbol_info, symbol_info_tick, last_error, shutdown, version`); the adapter codes against the protocol, tests inject a `FakeTerminal`.
- **Fixtures (labelled, tests-only):** hand-built numpy-lookalike rows / namedtuples mirroring the documented shapes (`FIXTURE_` prefix, docstring "fixture — never live"), covering: normal H1 sequence, weekend gap, duplicate bar, OHLC violation, zero-volume, `None`-return + each `last_error` code, symbol-not-visible, forming-bar-at-pos-0. Fixture files live under `tests/` only; a repo-grep test asserts no `FIXTURE_` symbol is imported outside tests (mirrors R-01 enforcement style).
- **Contract tests:** every adapter success output validated by `MarketBar`/`MarketQuote` constructors (invalid → test fails); precision rows validated by `PrecisionRow`.
- **Failure tests:** each health state from §5 forced via FakeTerminal; retry test asserts exactly 2 attempts then `disconnected` (D-51); stale-quote test per session row; unsupported instrument/timeframe tests assert `UNSUPPORTED_*` codes and no fallback call.
- **Boundary-scan compliance (required plan task):** `MetaTrader5`/`mt5` are currently blanket-forbidden import roots (`tests/security/_boundary.py:39-48`) — the adapter **will fail the gate as written**. Plan must rework the scan: keep `order_send` (+ add `order_check`? No — read-only, keep minimal: `order_send` stays; the scan's call-list already covers mutating names) while moving `MetaTrader5` from forbidden roots to an **adapter-scoped allowlist**: permitted only under `services/mt5_adapter/terminal.py`, plus a dedicated test asserting the adapter tree contains no forbidden call names and no `symbol_select`/`order_send` reference. Update the negative meta-test to cover the new shape. This is a planned, reviewed change to a gate — not a weakening: the forbidden-call set grows or holds, the import exception is path-scoped.
- **Live verification (operator-run, evidence-recorded):** `@pytest.mark.live_mt5` tests (skipped by default; excluded from gate) that run bare-`initialize`, fetch XAUUSD H1 + tick + spec against the real terminal; operator records output in the phase evidence doc. CI never claims them (R-10: unrun = BLOCKED, never DONE).

## 7. Risks / blockers

1. **Package install unverified (RISK-03, gating):** `MetaTrader5` wheel is Windows-only and ships per-Python-version binaries — repo Python is **3.14.7**, and the wheel historically lags new releases. `pip install MetaTrader5` on 3.14 may have no compatible build. Mitigation: attempt install as the phase's first spike; fallback is a documented Python 3.12 (or 3.10+) venv/bridge for the adapter per Architecture §6 option 1 (same-machine). Nothing else in Phase 2 can be live-verified until this resolves; unit/fixture work proceeds regardless.
2. **Live-terminal-only verification:** freshness thresholds, server timezone, symbol visibility, weekend behavior, and precision values are all broker-terminal-specific. CI proves logic; the operator's live run proves reality. Plan must schedule the live pass explicitly with Market Watch `XAUUSD` enabled by hand (D-49) and terminal logged in with investor password (D-46).
3. **Boundary-scan rework is load-bearing:** without the §6 scan change, a correct adapter breaks the build; with a careless one, the signals-only guarantee rots. Review the scan diff as its own plan step with the meta-test updated in the same step.
4. **Quality-enum gap:** no healthy `quality_status` member exists yet (§3) — needs a minor-bump enum addition; coordinate with the committed-schema drift test (regeneration must match).
5. **`UNSUPPORTED_INSTRUMENT` typo is locked** (`errors.py:30`); reuse verbatim.
6. **Terminal-clock skew:** server-time→UTC conversion is only as good as the setting + broker DST; the offset sanity check (§1) is not optional.

---

## Validation Architecture

*(Nyquist VALIDATION.md gate input: what will be validated, where, and by which check.)*

```
MT5 terminal ──IPC──▶ terminal.py (gateway: lazy import, timeouts, last_error capture)
                              │  FakeTerminal in tests; live_mt5 mark for operator runs
                              ▼
                     adapter.py (get_bars / get_latest_quote / get_instrument_spec / health_check)
                              │  one retry (D-51) → typed result or C-09 error
                              ▼
                     normalize.py (server-tz → UTC via GOLDMASTERS_MT5_SERVER_TIMEZONE;
                                   Decimal→PriceStr strings; tick_volume→volume/tick;
                                   drop forming bar; provenance stamp)
                              ▼
                     validation.py (freshness / ordering / duplicate / gap+weekend-classify /
                                    OHLC-tick-align / finite / volume semantics → quality_status+flags)
                              │  Pydantic MarketBar/MarketQuote construct = contract gate (D-04)
                              ▼
                     API layer (GET bars/quote; /health provider join; C-09 mapping;
                                INSUFFICIENT_DATA on stale/disconnected/missing/unsupported)
                              ▼
                     precision write (get_instrument_spec → PrecisionTable.with_row, append-only)
```

| Layer | Claim | Check (gate command `scripts/gate` + pytest) |
|---|---|---|
| Contract invariants | Invalid OHLC/finite/neutral payload rejected | Existing conformance suite (Phase 1, unchanged) |
| Policy validation | Each of freshness/ordering/duplicate/gap/OHLC/volume correct, incl. session table + weekend rule | `tests/unit/test_mt5_validation_*.py` over labelled fixtures; boundary cases at each threshold ±1s |
| Adapter mapping | Every `last_error` code → correct health/error; 1-retry-then-disconnected; no `symbol_select` call | `tests/unit/test_mt5_adapter_*.py` with FakeTerminal; AST assertion on adapter tree |
| Precision | Spec → row appended with build provenance; zero-row lookup still `unknown` | `tests/unit/test_precision_population.py` + existing precision tests |
| Health/API | Five distinct states render; `/health` never raises, never leaks; bars/quote endpoints return contract JSON | `tests/integration/test_mt5_health_api.py` (FakeTerminal-backed app) |
| Boundary | No order capability; `MetaTrader5` import only in gateway | Reworked `tests/security/test_boundary_scan*.py` + meta-test (same gate) |
| Live truth | Real terminal delivers XAUUSD H1 + tick with sane precision | `pytest -m live_mt5` by operator, output recorded (NOT in gate; unrun = BLOCKED) |
| No fabrication | No fixture importable from `src/`/`services/`/`apps/`; no live-shaped constant in production paths | Repo-grep test on `FIXTURE_` + existing audit expectations |

Determinism note: every layer except `terminal.py` is pure (inputs → outputs, clock injected as parameter) so thresholds/session/weekend logic is unit-testable without time mocking hacks — plan should require `now_utc` as an explicit argument through validation.

---

*Research complete. All external claims cite mql5.com doc pages fetched 2026-10-15 or repo files at the paths given. Unverifiable-until-installed items (exact `account_info`/`terminal_info` field names, wheel availability on Python 3.14) are flagged, not asserted.*
