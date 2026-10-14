"""Per-instrument precision table (D-19/D-24/D-26).

The table is keyed by ``(instrument_id, provider_id)`` and every row carries
provenance columns (provider spec version, ``retrieved_at``, ``superseded_at``,
``valid_from``, ``valid_to``). Rows are never overwritten: :class:`PrecisionTable`
is frozen and the only mutation path is :meth:`PrecisionTable.with_row`, which
returns a new table with the row appended — history is append-only from the
first populated row.

Phase 1 ships the table with zero rows; :meth:`PrecisionTable.lookup` answers
an explicit *unknown* result for a missing key or a key outside its validity
interval, never a default precision. Phase 2 fills this table from
``get_instrument_spec``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from goldmasters_contracts._base import ContractModel, UtcDatetime
from goldmasters_contracts.ids import ProviderId

__all__ = [
    "PrecisionLookupResult",
    "PrecisionRow",
    "PrecisionTable",
]


class PrecisionRow(ContractModel):
    """One precision record for an (instrument, provider) pair."""

    instrument_id: str
    provider_id: ProviderId
    tick_size: str
    decimals: int = Field(ge=0)
    provider_spec_version: str
    retrieved_at: UtcDatetime
    superseded_at: UtcDatetime | None = None
    valid_from: UtcDatetime | None = None
    valid_to: UtcDatetime | None = None

    @model_validator(mode="after")
    def _validate_interval(self) -> PrecisionRow:
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_from > self.valid_to
        ):
            raise ValueError("valid_from must be <= valid_to")
        return self


class PrecisionLookupResult(ContractModel):
    """Explicit lookup outcome: ``found`` carries the row, ``unknown`` carries nothing."""

    status: Literal["found", "unknown"]
    row: PrecisionRow | None = None

    @model_validator(mode="after")
    def _validate_outcome(self) -> PrecisionLookupResult:
        if self.status == "found" and self.row is None:
            raise ValueError("a found lookup must carry its row")
        if self.status == "unknown" and self.row is not None:
            raise ValueError("an unknown lookup must not carry a row")
        return self


class PrecisionTable(ContractModel):
    """Append-only container of precision rows. Constructed empty."""

    rows: tuple[PrecisionRow, ...] = ()

    def with_row(self, row: PrecisionRow) -> PrecisionTable:
        """Return a new table with ``row`` appended. No update path exists."""
        return PrecisionTable(rows=(*self.rows, row))

    def lookup(
        self,
        instrument_id: str,
        provider_id: str,
        at: datetime | None = None,
    ) -> PrecisionLookupResult:
        """Return the matching row or an explicit unknown — never a default."""
        for row in self.rows:
            if row.instrument_id != instrument_id or row.provider_id != provider_id:
                continue
            if at is not None:
                if row.valid_from is not None and at < row.valid_from:
                    continue
                if row.valid_to is not None and at > row.valid_to:
                    continue
            return PrecisionLookupResult(status="found", row=row)
        return PrecisionLookupResult(status="unknown")
