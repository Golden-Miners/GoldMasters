"""News item contract (Schema.md §7 lines 168-180).

Retrieval time is never publication time: ``published_at`` is nullable for
sources without a reliable timestamp. Absence stays representable — an
``UNAVAILABLE`` item may carry null content rather than an invented
substitute (R-01).
"""

from __future__ import annotations

from pydantic import Field

from goldmasters_contracts._base import ContractModel, UtcDatetime
from goldmasters_contracts.enums import EvidenceStatus

__all__ = ["InstrumentMapping", "NewsItem"]


class InstrumentMapping(ContractModel):
    """Instrument link with rationale and confidence method."""

    instrument_id: str
    rationale: str
    confidence_method: str


class NewsItem(ContractModel):
    """Schema.md §7 news item, field for field."""

    source_id: str
    canonical_url: str
    title: str
    published_at: UtcDatetime | None = None
    retrieved_at: UtcDatetime
    content_hash: str | None = None
    instrument_mappings: list[InstrumentMapping] = Field(default_factory=list)
    source_attribution: str
    access_method: str
    status: EvidenceStatus
    limitations: list[str] = Field(default_factory=list)
