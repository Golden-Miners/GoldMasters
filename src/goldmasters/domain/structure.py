"""Market-structure primitives: versioned swing/high-low functions (D-3.1).

Pure :class:`~decimal.Decimal` functions over closed
:class:`~goldmasters_contracts.MarketBar` bars with explicit parameters — no
wall-clock reads, no module-global config, no mutation (``validation.py``
precedent). Every parameter a policy could tune (swing window, tick size)
arrives as an explicit argument; no threshold literal lives in this module.

Malformed *inputs* raise (contract constructors, ``TypeError``/``ValueError``);
policy *failures* (misordered bars, too few bars for the window) return a
fail-closed :class:`StructureState` verdict, never a guess (Pattern 3).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from goldmasters_contracts import ContractModel, MarketBar, PriceStr
from pydantic import Field, model_validator

from src.goldmasters.domain.conventions import check_bar_order, quantize_to_tick

__all__ = [
    "STRUCTURE_CODE_HASH",
    "STRUCTURE_RULES_VERSION",
    "RULE_SOURCE",
    "StructureState",
    "SwingPoint",
    "describe_structure",
    "hash_rule_source",
    "highest_high",
    "lowest_low",
    "swing_highs",
    "swing_lows",
]

#: Semver of the classification rules below; bumped on any rule change.
STRUCTURE_RULES_VERSION = "1.0"

#: The rule text the integrity label covers. A stable literal (not the file
#: bytes) so comments and formatting stay free while rule edits move the hash.
RULE_SOURCE = (
    "structure/1.0: swing high = bar high strictly greater than every other "
    "high in its [left_bars, right_bars] window; swing low mirrors on lows; "
    "equal extremes claim no swing; highest_high/lowest_low are Decimal "
    "max/min over closed bars; misordered or too-short input is "
    "insufficient_data, never a guess"
)


def hash_rule_source(source: str) -> str:
    """Integrity label over a rule text (hashlib stdlib; not tamper-proofing)."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


#: Integrity label stamped on every output of this module.
STRUCTURE_CODE_HASH = hash_rule_source(RULE_SOURCE)


class SwingPoint(ContractModel):
    """One confirmed swing extreme: bar index plus its Decimal price."""

    index: int = Field(ge=0)
    price: PriceStr
    kind: Literal["high", "low"]


class StructureState(ContractModel):
    """Fail-closed structure verdict, stamped with rules version + code hash."""

    rules_version: str
    code_hash: str
    bar_count: int = Field(ge=0)
    verdict: Literal["ok", "insufficient_data"]
    reason: str
    swing_highs: list[SwingPoint] = Field(default_factory=list)
    swing_lows: list[SwingPoint] = Field(default_factory=list)
    highest_high: PriceStr | None = None
    lowest_low: PriceStr | None = None

    @model_validator(mode="after")
    def _validate_verdict_invariants(self) -> StructureState:
        if self.verdict == "ok":
            if self.highest_high is None or self.lowest_low is None:
                raise ValueError("an ok structure verdict must carry both extremes")
        else:
            if self.swing_highs or self.swing_lows:
                raise ValueError("an insufficient_data verdict must claim no swings")
            if self.highest_high is not None or self.lowest_low is not None:
                raise ValueError("an insufficient_data verdict must carry no extremes")
        return self


def _checked_bars(bars: Sequence[MarketBar]) -> list[MarketBar]:
    """Malformed input raises; an empty sequence is malformed, not a policy."""
    ordered = list(bars)
    if not ordered:
        raise ValueError("at least one closed bar is required")
    for bar in ordered:
        if not isinstance(bar, MarketBar):
            raise TypeError("bars must be MarketBar (malformed input raises)")
    return ordered


def _checked_window(left_bars: int, right_bars: int) -> None:
    """Fail closed on a non-positive swing window (settings-arg validation)."""
    for name, value in (("left_bars", left_bars), ("right_bars", right_bars)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive int, got {value!r}")


def swing_highs(bars: Sequence[MarketBar], *, left_bars: int, right_bars: int) -> list[SwingPoint]:
    """Bars whose high strictly exceeds every other high in their window.

    Equal neighbouring highs claim no swing (fail-closed, never a guess); a
    window that fits nowhere yields no swings.
    """
    ordered = _checked_bars(bars)
    _checked_window(left_bars, right_bars)
    found: list[SwingPoint] = []
    for i in range(left_bars, len(ordered) - right_bars):
        high = ordered[i].high
        if all(high > ordered[j].high for j in range(i - left_bars, i + right_bars + 1) if j != i):
            found.append(SwingPoint(index=i, price=high, kind="high"))
    return found


def swing_lows(bars: Sequence[MarketBar], *, left_bars: int, right_bars: int) -> list[SwingPoint]:
    """Mirror of :func:`swing_highs` on bar lows (strictly lower wins)."""
    ordered = _checked_bars(bars)
    _checked_window(left_bars, right_bars)
    found: list[SwingPoint] = []
    for i in range(left_bars, len(ordered) - right_bars):
        low = ordered[i].low
        if all(low < ordered[j].low for j in range(i - left_bars, i + right_bars + 1) if j != i):
            found.append(SwingPoint(index=i, price=low, kind="low"))
    return found


def highest_high(bars: Sequence[MarketBar]) -> Decimal:
    """Decimal max over closed-bar highs (Decimal-only price path)."""
    return max(_checked_bars(bars), key=lambda bar: bar.high).high


def lowest_low(bars: Sequence[MarketBar]) -> Decimal:
    """Decimal min over closed-bar lows (Decimal-only price path)."""
    return min(_checked_bars(bars), key=lambda bar: bar.low).low


def _insufficient(bars: Sequence[MarketBar], reason: str) -> StructureState:
    return StructureState(
        rules_version=STRUCTURE_RULES_VERSION,
        code_hash=STRUCTURE_CODE_HASH,
        bar_count=len(bars),
        verdict="insufficient_data",
        reason=reason,
    )


def describe_structure(
    bars: Sequence[MarketBar],
    *,
    left_bars: int,
    right_bars: int,
    tick_size: Decimal | None = None,
) -> StructureState:
    """Versioned, hash-stamped structure verdict over closed bars.

    ``tick_size`` aligns swing/extreme prices via
    :func:`conventions.quantize_to_tick`; ``None`` skips alignment, never a
    default tick (Phase-2 precedent). Misordered input (``MALFORMED`` per
    :func:`conventions.check_bar_order`) and too-short input return
    ``insufficient_data`` with the order preserved untouched.
    """
    ordered = _checked_bars(bars)
    _checked_window(left_bars, right_bars)
    if tick_size is not None and (not isinstance(tick_size, Decimal) or tick_size <= 0):
        raise ValueError(f"tick_size must be a positive Decimal, got {tick_size!r}")
    if check_bar_order([bar.bar_open_time for bar in ordered]) is not None:
        return _insufficient(bars, "bar opens misordered (MALFORMED): order preserved, no analysis")
    if len(ordered) < left_bars + right_bars + 1:
        return _insufficient(
            bars,
            "too few bars for the swing window: no swing claimed",
        )

    def _align(price: Decimal) -> Decimal:
        return quantize_to_tick(price, tick_size) if tick_size is not None else price

    return StructureState(
        rules_version=STRUCTURE_RULES_VERSION,
        code_hash=STRUCTURE_CODE_HASH,
        bar_count=len(ordered),
        verdict="ok",
        reason="swings confirmed on ordered closed bars",
        swing_highs=[
            SwingPoint(index=point.index, price=_align(point.price), kind=point.kind)
            for point in swing_highs(ordered, left_bars=left_bars, right_bars=right_bars)
        ],
        swing_lows=[
            SwingPoint(index=point.index, price=_align(point.price), kind=point.kind)
            for point in swing_lows(ordered, left_bars=left_bars, right_bars=right_bars)
        ],
        highest_high=_align(highest_high(ordered)),
        lowest_low=_align(lowest_low(ordered)),
    )
