---
phase: 02-market-data-and-provider-selection
verified: 2026-10-15T00:00:00Z
status: human_needed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "Precision row carries contract size in provenance"
    addressed_in: "Phase 3"
    evidence: "02-04-SUMMARY.md deviation 1: PrecisionRow (Phase-1-locked, extra=forbid) has no contract-size column and the plan forbids a contracts change; build + retrieved_at recorded as provenance (D-24), contract size observed on descriptor but not persisted. Open item for Phase 3: contracts change adding a contract-size provenance column."
human_verification:
  - test: "Run the live_mt5 module on the MT5 host with the operator's logged-in terminal (investor password, Market Watch XAUUSD enabled by hand): uv run pytest tests/integration/test_mt5_live.py -m live_mt5 -s"
    expected: "Bare-initialize attach succeeds, investor read-only assertion holds (trade_allowed False, master rejected), live XAUUSD H1 bars + tick + spec return sane values; paste output as phase evidence (02-04 Task 3 flips BLOCKED to DONE)"
    why_human: "Requires the operator's live MT5 terminal on the MT5 host; CI has no terminal and MetaTrader5 wheel is Windows/MT5-host only (02-VALIDATION.md Manual-Only Verifications, D-45/D-46)"
---

# Phase 2: Market Data and Provider Selection Verification Report

**Phase Goal:** The operator can select a provider and instrument and receive real, validated, provenance-stamped market data — or a visible, structured failure.
**Verified:** 2026-10-15
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator selects provider + symbol mapping explicitly; selection recorded for the run, never silently substituted | ✓ VERIFIED | `INSTRUMENT_SYMBOL_MAP = {("xauusd","H1"): "XAUUSD"}` as data in `services/mt5_adapter/adapter.py:61`; unknown instrument/timeframe returns `UNSUPPORTED_INSTRUMENT`/`UNSUPPORTED_TIMEFRAME` verbatim with no fallback call (`adapter.py:118,162-184`); endpoints take explicit `instrument_id`/`timeframe` params (`market.py:105-122`); tests assert no fallback call on FakeTerminal |
| 2 | Canonical instrument IDs stay separate from provider symbols in storage and API responses | ✓ VERIFIED | `provider_symbol` is its own opaque field alongside canonical `instrument_id` in normalize (`normalize.py:80-125,156-178`) and adapter (`adapter.py:312,359,416`); contract suite includes suffix-instrument (`XAUUSDm`) rejection mutation + canonical-vs-provider ID separation test |
| 3 | Unsupported instrument/timeframe returns structured "unsupported" failure, no substitute | ✓ VERIFIED | `UNSUPPORTED_INSTRUMENT` returned verbatim at three sites (`adapter.py:118,168,184`); `FORBIDDEN_ADAPTER_CALLS={symbol_select,login}` scan forbids terminal-state mutation; grep confirms `symbol_select`/`login(`/`MetaTrader5` absent from `adapter.py` |
| 4 | Every bar carries provider_id, provider_symbol, timeframe, open/close times, retrieved_at, finite OHLC, volume + volume_type, quality_status + quality_flags | ✓ VERIFIED | Provenance stamp in `normalize.py:113-125,169-178` (provider_id `mt5`, provider_symbol, retrieved_at UTC, source_timezone); contract tests prove success construction (fresh/stale paths, quote `last=None`, spec) and wire-round-trip (`test_mt5_market_contract.py`, 18 tests) |
| 5 | Freshness/ordering/duplicate/gap/OHLC/finite validation runs on every retrieval; stale/malformed/disconnected yields non-healthy status or INSUFFICIENT_DATA, never a synthesized candle | ✓ VERIFIED | Pure `validation.py` (finite → ordering → duplicate → gap → OHLC-tick-align → volume → freshness); mid-week gaps stamp `MISSING_HISTORY`, weekend/break-adjacent gaps flag `GAP`; session-aware quote windows; single-bar daily-break tolerance, never synthesis; 25 tests (`test_mt5_validation_{bars,quotes,weekend}.py`) |
| 6 | Provider health reports terminal-closed, disconnected, missing-history, unsupported-symbol distinctly, with contract + failure tests | ✓ VERIFIED | Five states with precedence terminal-closed > disconnected > unsupported-symbol > missing-history > stale > connected; single retry (exactly 2 attempts on transient codes, never on unsupported/missing/terminal-closed); full `last_error()` code table pinned; redaction (one sanitized capture per failure, terminal text never in API/health/trace); `/health` provider object (provider_id, status, market_open, terminal_build, last_bar_close_time, last_quote_time, checked_at); 13 tests + parametrized five-state API test |

**Score:** 6/6 truths verified (0 present-behavior-unverified)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Contract-size value persisted in precision-row provenance | Phase 3 | 02-04-SUMMARY.md deviation 1: `PrecisionRow` has no contract-size column and plan forbids contracts change; build + `retrieved_at` recorded instead (D-24) |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `services/mt5_adapter/terminal.py` | Lazy-only MetaTrader5 gateway, bare initialize | ✓ VERIFIED | Exists; boundary scan allowlists this single path |
| `services/mt5_adapter/adapter.py` | get_bars/get_latest_quote/get_instrument_spec, mapping table, retry, precedence | ✓ VERIFIED | Exists (26KB), substantive, wired to market.py + health.py |
| `services/mt5_adapter/normalize.py` | tz→UTC, forming-bar drop, volume mapping, provenance | ✓ VERIFIED | Exists, substantive, wired |
| `services/mt5_adapter/validation.py` | Pure validation policy | ✓ VERIFIED | Exists (14KB), 25 dedicated tests |
| `apps/api/src/goldmasters_api/market.py` | GET bars/quote routers | ✓ VERIFIED | Exists, wired into app.py, contract-valid JSON |
| `tests/unit/test_mt5_tracer.py` | End-to-end FakeTerminal slice | ✓ VERIFIED | Passes |
| `tests/integration/test_mt5_health_api.py` | Endpoints + five-state provider object | ✓ VERIFIED | Passes (extended in 02-04) |
| `tests/unit/test_precision_population.py` | Append-only history, interval audit | ✓ VERIFIED | Exists (6125B), 5 tests pass |
| `tests/contract/test_mt5_market_contract.py` | Success + rejection mutations | ✓ VERIFIED | Exists, 18 tests pass |
| `tests/integration/test_mt5_live.py` | Operator-run live scaffold, skips by default | ✓ VERIFIED | Exists; default run skips (2 skipped), excluded from gate |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| adapter.py | terminal.py gateway | TerminalGateway protocol, never imports MetaTrader5 directly | WIRED | No MetaTrader5/symbol_select/login strings in adapter.py (grep-clean) |
| market.py | MarketBar/MarketQuote | Pydantic constructors on every success output | WIRED | Contract suite green over all quality paths |
| health.py | probe_mt5 | Bounded provider object on /health | WIRED | Seven-key shape asserted per state |
| spec fetch | PrecisionTable.with_row | Append-only, valid_from=retrieved_at, open valid_to | WIRED | History length 2 after two fetches; interval audit resolves first row |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| market.py bars route | MarketBar list | adapter.get_bars → normalize → validation (FakeTerminal-backed in tests) | ✓ FLOWING | ✓ FLOWING |
| market.py quote route | MarketQuote | adapter.get_latest_quote → symbol_info_tick, time_msc authoritative | ✓ FLOWING | ✓ FLOWING |

Note: live-terminal data flow (real MT5 IPC → same chain) is the human-verification item below; FakeTerminal proves the full chain structurally.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green | `uv run pytest` | 306 passed, 2 skipped (live_mt5) in 22.15s | ✓ PASS |
| MT5 + contract + health subset | 9 test files | all pass | ✓ PASS |
| Precision + live-skip | `test_precision_population.py test_mt5_live.py` | 5 passed, 2 skipped | ✓ PASS |
| Lint | `ruff check` on adapter + market | All checks passed | ✓ PASS |
| Types | `mypy --strict` on adapter + market | no issues, 6 files | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REQ-instrument-provider-selection | 02-01, 02-04 | Canonical ID vs provider symbol; operator selection | ✓ SATISFIED | Mapping table, ID-separation test, suffix rejection, per-key hash coverage (20 D-59 keys) |
| REQ-market-data-ingestion-validation | 02-01..02-04 | Provenance-stamped validated bars/quotes | ✓ SATISFIED | Validation policy + 25 tests, health states + 13 tests, contract suite + 18 tests |

### Anti-Patterns Found

None. Grep for TODO/FIXME/XXX/TBD/placeholder/NotImplemented across `services/mt5_adapter/*.py` and `market.py` returns zero matches. No stub patterns observed; `mypy --strict` and `ruff` clean.

### Human Verification Required

### 1. Live MT5 terminal read (XAUUSD H1 + tick + spec)

**Test:** On the MT5 host, with terminal logged in (investor password) and Market Watch XAUUSD enabled by hand, run `uv run pytest tests/integration/test_mt5_live.py -m live_mt5 -s` and record output as phase evidence.
**Expected:** Bare-initialize attach succeeds; investor read-only assertion holds (`trade_allowed=False`, master rejected); live bars + tick + spec return sane values.
**Why human:** Requires the operator's live terminal; CI has no terminal and the MetaTrader5 wheel is Windows/MT5-host only. Unrun reads BLOCKED, never DONE (R-10). This is the only item keeping the phase out of `passed`.

### Gaps Summary

No automated gaps. All six roadmap success criteria are verified in code with 306 passing tests, clean lint/types, and no anti-patterns. The single open item is the operator-owned live-terminal run, which by design cannot be performed in this environment — hence `human_needed`, not `passed`. One documented deferral (contract-size provenance column) belongs to Phase 3 by plan decision, not this phase.

---
_Verified: 2026-10-15_
_Verifier: the agent (gsd-verifier)_
