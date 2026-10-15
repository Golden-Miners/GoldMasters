# Phase 2: Market Data and Provider Selection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-15
**Phase:** 02-market-data-and-provider-selection
**Areas discussed:** Provider lineup, MT5 access mechanics, First instruments, Freshness thresholds

---

## Provider lineup

| Option | Description | Selected |
|--------|-------------|----------|
| MT5 only | One real adapter; second source later | ✓ |
| MT5 plus second source | Proves common interface now; costs a second adapter | |
| Interface only | Plumbing first, live data later | |

**User's choice:** MT5 only (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Live terminal | Installed, logged-in account on this machine | ✓ |
| Not yet set up | Build against interface with recorded blocker | |
| Demo account | Papers over coverage questions | |

**User's choice:** Live terminal (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Investor login | Read-only; cannot trade even if code went rogue | ✓ |
| Master password | Full rights; boundary rests on code alone | |
| You decide | Operator provides whatever logs in | |

**User's choice:** Investor login (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Nowhere in our system | Attach to logged-in terminal; never handle password | ✓ |
| Environment variable | `GOLDMASTERS_MT5_*`; adapter logs in | |
| `.env` entry | Persistent on disk, git-ignored | |

**User's choice:** Nowhere in our system (1)
**Notes:** None

---

## MT5 access mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Broker name | Shapes provider_id key | |
| Skip | Generic `mt5` for now | ✓ |

**User's choice:** Skip (2)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Operator enables | Hand-maintained Market Watch; adapter reads only | ✓ |
| Adapter auto-enables | Convenient; code changes terminal state | |

**User's choice:** Operator enables (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Report unavailable | Disconnected/terminal-closed; INSUFFICIENT_DATA downstream | ✓ |
| Serve stale flagged | Charts keep showing something, explicitly marked | |
| You decide | Tradeoff for researcher | |

**User's choice:** Report unavailable (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Fail fast | One quick retry, then disconnected | ✓ |
| Patient reconnect | Backoff for minutes; covers restarts | |
| Operator-configured | Settings key for retry budget | |

**User's choice:** Fail fast (1)
**Notes:** None

---

## First instruments

| Option | Description | Selected |
|--------|-------------|----------|
| Gold first | XAUUSD proven end to end; rest later | ✓ |
| Gold + silver | Metals pair, same sessions | |
| All six now | Widest scope, slowest to verify | |

**User's choice:** Gold first (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Plain XAUUSD | Trivial mapping | ✓ |
| Suffixed | Real name in provider_symbol | |
| Check later | Researcher reads terminal | |

**User's choice:** Plain XAUUSD (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| H1 only | One timeframe proven | ✓ |
| Intraday set | M15, H1, H4 | |
| Full spread | M1 to D1 | |

**User's choice:** H1 only (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Bars and quotes | Closed bars + live ticks | ✓ |
| Bars only | Candles are the research input | |
| Quotes only | Nonsense option, listed for completeness | |

**User's choice:** Bars and quotes (1)
**Notes:** the agent listed quotes-only as an explicit non-option; user picked bars and quotes.

---

## Freshness thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Two closed bars | ~2h; timeframe-relative | ✓ |
| One bar + grace | Tighter; late bars flag sooner | |
| Researcher proposes | Derived from MT5 semantics | |

**User's choice:** Two closed bars (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| 60 seconds | Survives quiet minutes | |
| 10 seconds | Strict live-stream check | |
| Session-aware | Tighter London/NY, looser Asia | ✓ |

**User's choice:** Session-aware (3)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Expected gap | Known market-hours gap, resumes cleanly | ✓ |
| Missing history | Simpler, noisier | |
| Researcher decides | Calendar vs flag semantics to planning | |

**User's choice:** Expected gap (1)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Settings keys | Tunable, hash-captured | ✓ |
| Code constants | Fixed; changes need commits | |
| Config YAML | Same effect, different home | |

**User's choice:** Settings keys (1)
**Notes:** None

---

## the agent's Discretion

None — the operator answered every area directly.

## Deferred Ideas

- Second market-data source — later phase
- Silver/forex/oil/BTC/ETH mapping — later work
- Additional timeframes beyond H1 — later work
