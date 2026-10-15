# Operator 10-Agent Spec (transcribed from operator message 2026-10-15)

Source of rule families for plans 3.2–3.5. Rule text is operator-supplied;
numeric thresholds are NOT set here — they ride as
`GOLDMASTERS_STRATEGY_AGENT_<N>_*` settings placeholders (fail-closed, None).

## Agent 1 — trend-following (Trend Following)

Hypothesis: directional trends persist long enough for confirmed trend signals
to capture a portion of the move.
Rules: configurable fast/slow moving-average relationship or crossover;
higher-timeframe trend filter; configurable trend-strength filter (e.g. ADX
where supported); explicit entry confirmation, invalidation, stop methodology,
exit/trailing-stop rules. Crossover alone is never sufficient in chop.
Scope: configurable instruments + timeframes. Parameters are hypotheses, not
profitability claims.
Settings: FAST_PERIOD, SLOW_PERIOD, HTF_TIMEFRAME, ADX_MIN, CONFIRM_BARS.

## Agent 2 — time-series-momentum (Time-Series Momentum)

Hypothesis: an instrument's own past directional performance may contain
information about subsequent returns.
Rules: historical returns over configurable lookback horizons; direction from a
defined return/momentum rule; volatility/ATR risk normalization; holding
periods, signal expiry, reversal/exit logic. Return-based signal — distinct
from Agent 1's crossover logic.
Scope: longer-horizon/swing; gold, silver, major forex, BTCUSD, ETHUSD, oil
where history suffices.
Settings: LOOKBACKS, ENTRY_THRESHOLD, VOL_LOOKBACK, MAX_HOLD_BARS, EXPIRY_BARS.

## Agent 3 — donchian-breakout (Donchian Channel Breakout)

Hypothesis: a confirmed break of a prior price channel can indicate
directional continuation.
Rules: upper/lower channels from prior completed candles (forming candle
excluded unless the backtest models intrabar execution); configurable breakout
buffer + optional trend/regime confirmation; false-breakout handling, stops,
time/channel-based exits. Long and short tested separately.
Settings: CHANNEL_BARS, BUFFER_TICKS, CONFIRM_BARS, EXIT_BARS.

## Agent 4 — vol-expansion-breakout (Volatility Expansion Breakout)

Hypothesis: low-volatility compression can precede directional expansion;
expansion alone does not predict direction.
Rules: compression via configurable ATR / Bollinger Bandwidth / documented
measure; separate directional breakout confirmation; entry confirmation,
failure handling, stops, exits. Implementation and evaluation distinct from
Agent 3. Filter signals around gaps/unreliable candles.
Settings: VOL_LOOKBACK, COMPRESSION_PCTILE, CONFIRM_BARS.

## Agent 5 — trend-pullback-continuation (Trend Pullback Continuation)

Hypothesis: pullbacks in an established trend offer clearer invalidation than
chasing extension.
Rules: trend + HTF direction first; pullback via configurable MAs and/or price
structure; documented confirmation required; structural invalidation, stops,
targets, expiry. Reject pullbacks that break the governing trend.
Settings: TREND_PERIOD, PULLBACK_MA, CONFIRM_BARS, EXPIRY_BARS.

## Agent 6 — session-opening-range (Session Opening Range Breakout)

Hypothesis: a confirmed break of a predefined session range may capture a
directional move.
Rules: named sessions, timezones, range duration, eligible instruments; range
from in-session candles only; completed-range breakout + confirmation,
optional retest; session-end expiry, spread filters, failure handling; DST and
server-time correctness.
Scope: gold + major forex first; others after session validation.
Settings: SESSION_NAME, SESSION_TZ, RANGE_MINUTES, BUFFER_TICKS, EXPIRY_MINUTES,
MAX_SPREAD_TICKS.

## Agent 7 — mean-reversion (Mean Reversion)

Hypothesis: in range-bound regimes, unusually large deviations from a
reference distribution may partially reverse.
Rules: range-bound regime gate first; configurable Bollinger Bands / z-score /
RSI extension evidence; reversal confirmation; reference price/range target;
volatility/regime invalidation + protective stops. Never auto-fade strong
trends. Per-instrument testing (gold, silver, forex majors, BTCUSD, ETHUSD);
no cross-instrument transfer assumed.
Settings: BASIS_PERIOD, BAND_WIDTH, Z_MIN, RSI_PERIOD, RSI_EXTREME, CONFIRM_BARS.

## Agent 8 — vwap-reversion (VWAP Reversion)

Hypothesis: session-VWAP deviations may revert under specified intraday
conditions.
Rules: session VWAP + deviation bands from a documented volume source; session
anchor, timezone, reset, entry/exit; range/reversion regime filter; reject on
missing/unsuitable volume; tick-volume VWAP never labelled centralized-volume
VWAP; spread/session/volatility filters. Independent config + evaluation from
Agent 7.
Settings: SESSION_NAME, SESSION_TZ, BAND_SIGMAS, MIN_VOLUME_BARS.

## Agent 9 — smc-ict-liquidity-sweep (SMC/ICT Liquidity Sweep)

Hypothesis: sweep + confirmed displacement + structure shift may mark
reversal/continuation.
Ordered model: (1) HTF bias → (2) external liquidity levels → (3) sweep on
completed candles + tolerance → (4) displacement → (5) CHOCH/BOS per setup
type → (6) valid FVG and/or OB → (7) retest + entry confirmation →
(8) invalidation/stop/targets/R:R before valid setup.
Rules: explicit swing/equal-high-low/tolerance/displacement/BOS/CHOCH/OB/FVG/
retest definitions; configurable + instrument-specific thresholds; never
signal from lone OB/FVG/CHOCH; pattern ≠ validated setup; reason code per
required and per failed condition.
Scope: XAUUSD + BTCUSD first, others independently validated.
Settings: SWING_BARS, EQUAL_TOL_TICKS, SWEEP_TOL_TICKS, DISP_BODY_MIN_ATR,
EXPIRY_BARS.

## Agent 10 — carry-term-structure (Carry and Term Structure)

Hypothesis: financing/funding/basis/curve information signals distinctly
from price direction.
Legs (one contract): forex (verified financing/forward-premium; broker swaps
displayed separately, never auto-treated as carry model); crypto (verified
funding/basis with timestamps + venue/ids); oil/commodities (verified curve
with expiry + roll handling).
Rules: never infer funding/curves from spot candles; require timestamped
source data + documented calc; account financing/spread/fees/roll/staleness;
INSUFFICIENT_DATA or NOT_APPLICABLE when prerequisites missing; never relabel
momentum as carry.
Settings: MAX_DATA_AGE_HOURS, MIN_HISTORY_POINTS. (Source-data adapters are
Phase 6+/operator-supplied; legs ship NOT_APPLICABLE-first.)
