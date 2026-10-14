"""Shared contract base, the decimal wire form and the timestamp forms.

Every contract model derives from :class:`ContractModel` so that strictness,
unknown-field rejection and immutability have exactly one definition
(D-04/D-08/D-12). :data:`PriceStr` is the single decimal-as-string wire form
(D-11/D-19); :data:`UtcDatetime` and :data:`IanaTimezone` are the shared
timestamp forms (Schema.md §1 line 10).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    WithJsonSchema,
)

__all__ = [
    "DECIMAL_PATTERN",
    "ContractModel",
    "IanaTimezone",
    "PriceStr",
    "UtcDatetime",
]

#: D-11/D-19 — the decimal wire form: digits with an optional single dot, no
#: exponent, no leading ``+`` and no ``NaN``/``Infinity``. Form only: no tick
#: multiple and no decimal-place count are enforced while the precision table
#: has zero rows.
DECIMAL_PATTERN = r"^-?\d+(\.\d+)?$"

_DECIMAL_RE = re.compile(DECIMAL_PATTERN)


def _parse_wire_decimal(value: object) -> object:
    """Enforce the decimal *wire form* and hand the core schema a ``Decimal``.

    Pydantic's own ``Decimal`` parser would accept ``"2.41537e3"``,
    ``"+2415.37"`` and non-finite texts and normalise them to a value the wire
    form forbids (Pitfall 4), so the raw string is inspected first. A JSON
    number (or any non-string) is rejected rather than accepted as a price, so
    a price is always a documented decimal *string* on the wire (D-06/D-11).
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str) and _DECIMAL_RE.fullmatch(value) is not None:
        return Decimal(value)
    msg = f"price must be a decimal string matching {DECIMAL_PATTERN}"
    raise ValueError(msg)


def _serialise_decimal(value: Decimal) -> str:
    """Serialise a price as a fixed-point string with no exponent (D-11)."""
    return format(value, "f")


PriceStr = Annotated[
    Decimal,
    BeforeValidator(_parse_wire_decimal),
    PlainSerializer(_serialise_decimal, return_type=str),
    WithJsonSchema({"type": "string", "pattern": DECIMAL_PATTERN}),
]


def _normalise_to_utc(value: datetime) -> datetime:
    """Require an explicit offset and normalise the instant to UTC (Schema.md §1)."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = "timestamp must be timezone-aware"
        raise ValueError(msg)
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_normalise_to_utc)]


def _require_known_iana_timezone(value: str) -> str:
    """Reject a source timezone that is not a known IANA zone name."""
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        msg = f"unknown IANA timezone {value!r}"
        raise ValueError(msg) from exc
    return value


IanaTimezone = Annotated[str, AfterValidator(_require_known_iana_timezone)]


class ContractModel(BaseModel):
    """Shared base for every contract model (D-04/D-08/D-12).

    ``strict`` rejects type coercion, ``extra="forbid"`` rejects unknown fields
    and ``frozen`` makes an instance immutable once constructed.
    """

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
