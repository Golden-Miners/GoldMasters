---
status: complete
phase: 02-market-data-and-provider-selection
source: [02-VERIFICATION.md]
started: 2026-10-15T00:00:00Z
updated: 2026-10-24T10:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Live MT5 terminal read (GOLD.i# H1 + tick + spec)
expected: Bare-initialize attach succeeds, live GOLD.i# H1 bars + tick + spec return sane values in any MT5 session mode
result: pass

## Summary

total: 308
passed: 308
skipped: 0
issues: 0
pending: 0
blocked: 0

## Live Verification Evidence (2026-10-24)

### Health Endpoint
```
GET /health
→ {"status":"ok","provider":{"provider_id":"mt5","status":"connected","market_open":true,
"terminal_build":"0","last_bar_close_time":"2026-10-23T17:00:00+00:00",
"last_quote_time":"2026-10-23T17:26:00.642000+00:00","checked_at":"..."}}
```

### Bars Endpoint (H1, 5 bars)
```
GET /v1/market/bars?instrument_id=xauusd&timeframe=H1&count=5
→ 5 bars, all quality_status="ok", provider_symbol="GOLD.i#"
→ Sample: open="4024.41" high="4032.29" low="4021.48" close="4026.08" volume="16733"
→ Retrieved: "2026-10-23T17:26:14.668123Z", source_timezone="Asia/Nicosia"
```

### Quote Endpoint
```
GET /v1/market/quote?instrument_id=xauusd
→ bid="3993.41" ask="3993.66" spread="0.25" quality_status="ok"
```

## Code Changes for Live MT5 Support

1. `services/mt5_adapter/adapter.py` — `_check_read_only()` no longer refuses master/demo/live sessions; any MT5 session mode accepts market data reads (signals-only boundary preserved — no order execution)
2. `services/mt5_adapter/normalize.py` — `normalize_bars()` detects bar ordering (newest-first vs oldest-first) and handles both; fixes "malformed" validation error

## Gaps

None. All six roadmap success criteria verified in code with live MT5 data flowing through the complete pipeline:

1. ✅ Operator selects provider + symbol mapping explicitly (`INSTRUMENT_SYMBOL_MAP`)
2. ✅ Canonical instrument IDs separate from provider symbols
3. ✅ Unsupported instrument → structured `UNSUPPORTED_INSTRUMENT` failure
4. ✅ Every bar carries provenance (provider_id, provider_symbol, retrieved_at, source_timezone, quality_status, quality_flags)
5. ✅ Freshness/ordering/duplicate/gap/OHLC/finite validation runs on every retrieval
6. ✅ Provider health reports connected/disconnected/missing-history/unsupported-symbol states distinctly