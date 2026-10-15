"""Closed contract vocabularies (Schema.md §2; D-16/D-20/D-28).

Every enum here is closed: a value outside it is rejected by any field typed
with it rather than coerced, rounded onto a neighbouring member, or passed
through under a provider name.

``Timeframe`` members are transcribed from the selected provider's documented
timeframe list (MetaTrader 5 — the V1 provider per PROJECT.md), not from memory
(D-13/D-16). Sources:

- https://www.mql5.com/en/docs/constants/chartconstants/enum_timeframes
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrom_py

``PERIOD_CURRENT`` is deliberately excluded: it is a chart property, not a bar
period. Members can only be added, never removed, within a major (D-16/D-23);
a provider-native string outside this enum is reported unsupported for that
provider and never reaches strategy logic (D-28).
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AgentRunStatus",
    "Decision",
    "Direction",
    "EvidenceStatus",
    "QualityFlag",
    "QualityStatus",
    "Timeframe",
    "TrendRegime",
    "VolumeType",
]


class Decision(StrEnum):
    """Schema.md §2 ``Decision`` — a research candidate, never an order."""

    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AgentRunStatus(StrEnum):
    """Schema.md §2 agent/run status."""

    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    NO_SETUP = "no_setup"
    INSUFFICIENT_DATA = "insufficient_data"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class EvidenceStatus(StrEnum):
    """Schema.md §2 evidence status."""

    VALID = "valid"
    STALE = "stale"
    MISSING = "missing"
    CONFLICTED = "conflicted"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


class Direction(StrEnum):
    """Schema.md §2 direction."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class TrendRegime(StrEnum):
    """Schema.md §2 trend/regime state.

    These labels require documented, versioned classification rules; they must
    not be generated solely from an unconstrained LLM (Schema.md §2 line 65).
    """

    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    MOMENTUM = "momentum"
    CONTINUATION = "continuation"
    POSSIBLE_REVERSAL = "possible_reversal"
    UNKNOWN = "unknown"


class QualityStatus(StrEnum):
    """The D-20 quality vocabulary, shared by ``quality_status``/``quality_flags``.

    ``not_evaluated`` is the only value Phase 1 may emit and is never a healthy
    value (D-20/D-22); ``ok`` (added in Phase 2, minor bump per D-23) is the
    single healthy value Phase 2 validation stamps on a fully passing bar.
    """

    OK = "ok"
    STALE = "stale"
    DUPLICATE = "duplicate"
    GAP = "gap"
    MALFORMED = "malformed"
    DISCONNECTED = "disconnected"
    MISSING_HISTORY = "missing-history"
    UNSUPPORTED = "unsupported"
    NOT_EVALUATED = "not_evaluated"


# D-20 pins a single quality vocabulary for both fields, so ``quality_flags``
# uses the same closed member set as ``quality_status``.
QualityFlag = QualityStatus


class VolumeType(StrEnum):
    """Schema.md §4 volume semantics — tick volume is never relabelled exchange."""

    TICK = "tick"
    EXCHANGE = "exchange"
    BROKER = "broker"
    UNKNOWN = "unknown"
    NOT_AVAILABLE = "not_available"


class Timeframe(StrEnum):
    """The closed canonical timeframe enum (D-13/D-16/D-28).

    Members are the documented MetaTrader 5 period tokens (module docstring
    cites the source); a value outside this enum is rejected by a field typed
    with it.
    """

    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"
    M6 = "M6"
    M10 = "M10"
    M12 = "M12"
    M15 = "M15"
    M20 = "M20"
    M30 = "M30"
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H6 = "H6"
    H8 = "H8"
    H12 = "H12"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"
