"""Server-timezone normalization into contract models (pure; 02-RESEARCH.md §1/§3).

MT5 bar/tick instants arrive as *server-wall* epoch values: the broker wall
clock read as seconds since the Unix epoch, with no zone attached. They become
tz-aware UTC via the operator-configured ``GOLDMASTERS_MT5_SERVER_TIMEZONE``
IANA name (fail-closed upstream when missing/invalid). Every output carries
provenance (``retrieved_at``, ``source_timezone``, ``provider_id``,
``provider_symbol``); volume follows Schema §4 tick semantics and a
``last=0.0`` tick maps to ``None``, never a price.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from goldmasters_contracts import MarketBar, MarketQuote, QualityStatus, Timeframe, VolumeType
from pydantic import ValidationError

__all__ = [
    "H1_SECONDS",
    "NormalizationError",
    "normalize_bars",
    "normalize_quote",
    "server_to_utc",
]

#: Seconds per H1 bar; the tracer derives ``bar_close_time`` arithmetically.
H1_SECONDS = 3600

_TIMEFRAME_SECONDS: dict[str, int] = {"H1": H1_SECONDS}


class NormalizationError(ValueError):
    """A terminal payload that cannot become a contract model."""


def server_to_utc(epoch_seconds: float, server_timezone: str) -> datetime:
    """Interpret a server-wall epoch value as tz-aware UTC.

    The epoch value first renders as a naive wall reading, is attached to the
    configured server zone, then converted to UTC. DST folds stay a known
    tracer limitation (flagged for plan 02-02).
    """
    wall = datetime.fromtimestamp(epoch_seconds, tz=UTC).replace(tzinfo=None)
    return wall.replace(tzinfo=ZoneInfo(server_timezone)).astimezone(UTC)


def _price(value: Any, field: str) -> Decimal:
    """Coerce a terminal price to ``Decimal`` without float artefacts."""
    if isinstance(value, bool):
        raise NormalizationError(f"{field} must be a number, got {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise NormalizationError(f"{field} must be a number, got {value!r}") from exc
    if not isfinite(number) or number <= 0:
        raise NormalizationError(f"{field} must be finite and positive, got {value!r}")
    return Decimal(str(number))


def _tick_instant(tick: dict[str, Any], server_timezone: str, field: str) -> datetime | None:
    """Tick instant from ``time_msc`` (authoritative) or ``time``; ``None`` when absent."""
    raw_ms = tick.get("time_msc")
    if raw_ms is not None:
        return server_to_utc(float(raw_ms) / 1000.0, server_timezone)
    raw_s = tick.get(field, tick.get("time"))
    if raw_s is None:
        return None
    return server_to_utc(float(raw_s), server_timezone)


def normalize_bars(
    rows: list[dict[str, Any]],
    *,
    instrument_id: str,
    provider_symbol: str,
    timeframe: str,
    server_timezone: str,
    retrieved_at: datetime,
    forming_first: bool = True,
) -> list[MarketBar]:
    """Normalize closed bars into chronological contract order.

    Terminal order is newest-first with the ``pos-0`` still-forming bar at
    index 0: it is dropped, and the remaining closed bars are reversed into
    chronological order for validation. Backfill rows (already chronological,
    no forming bar) pass ``forming_first=False``. Raises
    :class:`NormalizationError` on an empty input or a row that cannot satisfy
    the contract invariants (the adapter maps empties to missing-history
    before reaching here).
    """
    try:
        bar_seconds = _TIMEFRAME_SECONDS[timeframe]
    except KeyError as exc:
        raise NormalizationError(f"unsupported timeframe for normalization: {timeframe}") from exc
    if not rows:
        raise NormalizationError("no rows to normalize")
    try:
        timeframe_enum = Timeframe(timeframe)
    except ValueError as exc:
        raise NormalizationError(f"unsupported timeframe for normalization: {timeframe}") from exc
    bars: list[MarketBar] = []
    ordered = reversed(rows[1:]) if forming_first else iter(rows)
    for row in ordered:
        try:
            open_time = server_to_utc(float(row["time"]), server_timezone)
            bar = MarketBar(
                instrument_id=instrument_id,
                provider_id="mt5",
                provider_symbol=provider_symbol,
                timeframe=timeframe_enum,
                bar_open_time=open_time,
                bar_close_time=open_time + timedelta(seconds=bar_seconds),
                open=_price(row["open"], "open"),
                high=_price(row["high"], "high"),
                low=_price(row["low"], "low"),
                close=_price(row["close"], "close"),
                volume=_volume(row),
                volume_type=_volume_type(row),
                retrieved_at=retrieved_at,
                source_timezone=server_timezone,
                quality_status=QualityStatus.NOT_EVALUATED,
                quality_flags=[],
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise NormalizationError(f"row cannot satisfy the bar contract: {exc}") from exc
        bars.append(bar)
    return bars


def _volume(row: dict[str, Any]) -> Decimal | None:
    """``tick_volume`` → ``Decimal``; ``real_volume`` ignored; zero/absent → ``None``."""
    tick_volume = row.get("tick_volume")
    if tick_volume is None:
        return None
    try:
        amount = int(tick_volume)
    except TypeError, ValueError:
        return None
    return Decimal(amount) if amount > 0 else None


def _volume_type(row: dict[str, Any]) -> VolumeType:
    """``tick`` when a positive tick volume exists, else ``not_available``."""
    return VolumeType.TICK if _volume(row) is not None else VolumeType.NOT_AVAILABLE


def normalize_quote(
    tick: dict[str, Any],
    *,
    instrument_id: str,
    provider_symbol: str,
    server_timezone: str,
    retrieved_at: datetime,
) -> MarketQuote:
    """Normalize one tick; ``last=0.0``/``volume=0`` maps to ``None``, never ``0.0``."""
    try:
        bid_raw, ask_raw, last_raw = tick.get("bid"), tick.get("ask"), tick.get("last")
        bid = _price(bid_raw, "bid") if bid_raw else None
        ask = _price(ask_raw, "ask") if ask_raw else None
        last = _price(last_raw, "last") if last_raw else None
        instant = _tick_instant(tick, server_timezone, "time")
        quote = MarketQuote(
            instrument_id=instrument_id,
            provider_id="mt5",
            provider_symbol=provider_symbol,
            bid=bid,
            bid_time=instant if bid is not None else None,
            ask=ask,
            ask_time=instant if ask is not None else None,
            last=last,
            last_time=instant if last is not None else None,
            spread=(ask - bid) if bid is not None and ask is not None else None,
            retrieved_at=retrieved_at,
            quality_status=QualityStatus.NOT_EVALUATED,
            quality_flags=[],
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise NormalizationError(f"tick cannot satisfy the quote contract: {exc}") from exc
    return quote
