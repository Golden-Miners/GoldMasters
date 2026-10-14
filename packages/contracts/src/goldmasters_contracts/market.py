"""Market bar and quote contracts (Schema.md §4; D-04/D-16/D-17/D-22/D-25/D-28).

This module defines the market data contracts with all Schema.md §4 fields and
the D-04 contract invariants enforced via Pydantic model validators:

- ``high`` is the maximum of open/close/low
- ``low`` is the minimum of open/close/high
- Prices are finite and positive
- Bar timestamps are ordered and aligned
- Quality information is required (no default fill; D-22)
- ``timeframe`` uses the closed canonical ``Timeframe`` enum (D-16/D-28)
- ``provider_id`` uses the ``ProviderId`` lowercase snake_case key (D-25)
- ``instrument_id`` is a provider-independent key validated against a pattern
  that forbids broker suffixes (D-17)
- Timestamps are timezone-aware UTC with preserved IANA source timezone
  (Schema.md §1 line 10)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import Field, model_validator

from goldmasters_contracts._base import ContractModel, IanaTimezone, PriceStr, UtcDatetime
from goldmasters_contracts.enums import QualityFlag, QualityStatus, Timeframe, VolumeType
from goldmasters_contracts.ids import ProviderId

__all__ = ["MarketBar", "MarketQuote"]


# Instrument ID pattern: provider-independent key, no broker suffix
# Alphanumeric with underscores, starting with a letter (D-17)
_INSTRUMENT_ID_PATTERN = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"


def _validate_instrument_id(value: str) -> str:
    """Validate instrument_id format (provider-independent, no broker suffix)."""
    import re

    if not re.fullmatch(_INSTRUMENT_ID_PATTERN, value):
        raise ValueError(
            "instrument_id must be a provider-independent lowercase snake_case key "
            "(e.g. 'xauusd', 'eurusd') — broker suffixes are forbidden"
        )
    return value


InstrumentId = Annotated[
    str,
    Field(pattern=_INSTRUMENT_ID_PATTERN),
]


class MarketBar(ContractModel):
    """Market bar contract reproducing Schema.md §4 exactly.

    All monetary/price fields use :data:`PriceStr` (decimal-as-string wire form).
    Invariants enforced by :meth:`_validate_bar_invariants`:
    - high >= max(open, close, low)
    - low <= min(open, close, high)
    - All prices finite and positive
    - Timestamps ordered (bar_open_time < bar_close_time if present)
    - Quality information present (no default fill per D-22)
    """

    instrument_id: InstrumentId
    provider_id: ProviderId
    provider_symbol: str
    timeframe: Timeframe
    bar_open_time: UtcDatetime
    bar_close_time: UtcDatetime | None = None
    open: PriceStr
    high: PriceStr
    low: PriceStr
    close: PriceStr
    volume: Decimal | None = None
    volume_type: VolumeType = VolumeType.NOT_AVAILABLE
    retrieved_at: UtcDatetime
    source_timezone: IanaTimezone
    quality_status: QualityStatus
    quality_flags: list[QualityFlag] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_bar_invariants(self) -> "MarketBar":
        """Enforce Schema.md §4 validation invariants (D-04)."""
        # All prices must be finite and positive (D-04, Schema.md:106)
        for price_name in ("open", "high", "low", "close"):
            price = getattr(self, price_name)
            if not price.is_finite() or price <= 0:
                raise ValueError(f"{price_name} must be finite and positive, got {price}")

        # high >= max(open, close, low) (Schema.md:107)
        max_ohl = max(self.open, self.close, self.low)
        if self.high < max_ohl:
            raise ValueError(
                f"high ({self.high}) must be >= max(open={self.open}, close={self.close}, low={self.low})"
            )

        # low <= min(open, close, high) (Schema.md:107)
        min_ohl = min(self.open, self.close, self.high)
        if self.low > min_ohl:
            raise ValueError(
                f"low ({self.low}) must be <= min(open={self.open}, close={self.close}, high={self.high})"
            )

        # Timestamps ordered (Schema.md:108)
        if self.bar_close_time is not None and self.bar_open_time >= self.bar_close_time:
            raise ValueError(
                f"bar_open_time ({self.bar_open_time}) must be < bar_close_time ({self.bar_close_time})"
            )

        # Quality information required — no default fill (D-22)
        if self.quality_status is None:
            raise ValueError("quality_status is required and must not be omitted")
        if self.quality_status == QualityStatus.NOT_EVALUATED and not self.quality_flags:
            # This is allowed — not_evaluated with empty flags means "not evaluated yet"
            pass

        return self


class MarketQuote(ContractModel):
    """Market quote contract (Schema.md §4 lines 112-119).

    A quote represents the current bid/ask spread. Missing bid, ask, last price,
    or volume is not invented (Schema.md:119).
    """

    instrument_id: InstrumentId
    provider_id: ProviderId
    provider_symbol: str
    bid: PriceStr | None = None
    bid_time: UtcDatetime | None = None
    ask: PriceStr | None = None
    ask_time: UtcDatetime | None = None
    last: PriceStr | None = None
    last_time: UtcDatetime | None = None
    spread: PriceStr | None = None
    retrieved_at: UtcDatetime
    quality_status: QualityStatus
    quality_flags: list[QualityFlag] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_quote_invariants(self) -> "MarketQuote":
        """Enforce quote invariants."""
        # Spread only when derived from valid bid/ask (Schema.md:116)
        if self.spread is not None:
            if self.bid is None or self.ask is None:
                raise ValueError("spread requires both bid and ask to be present")
            if self.ask <= self.bid:
                raise ValueError("ask must be > bid for a valid spread")
            expected_spread = self.ask - self.bid
            if self.spread != expected_spread:
                raise ValueError(f"spread ({self.spread}) must equal ask - bid ({expected_spread})")

        # Quality information required (D-22)
        if self.quality_status is None:
            raise ValueError("quality_status is required and must not be omitted")

        return self