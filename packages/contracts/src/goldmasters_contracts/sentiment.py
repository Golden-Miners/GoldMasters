"""Sentiment assessment contract (Schema.md §7 lines 182-189).

Sentiment is contextual evidence, not a price prediction. A score is carried
only with its defined, versioned scoring method; source statements and model
interpretation stay separate fields. ``SCORE_MIN``/``SCORE_MAX`` are the
documented bounds — out-of-range scores are rejected, never clamped.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from goldmasters_contracts._base import ContractModel, UtcDatetime

__all__ = ["SCORE_MAX", "SCORE_MIN", "SentimentRecord"]

#: Documented score bounds (inclusive).
SCORE_MIN = -1.0
SCORE_MAX = 1.0


class SentimentRecord(ContractModel):
    """Schema.md §7 sentiment assessment, field for field."""

    instrument_id: str
    window_start: UtcDatetime
    window_end: UtcDatetime
    created_at: UtcDatetime
    source_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    coverage_count: int = Field(ge=0)
    unique_source_count: int = Field(ge=0)
    duplicate_policy: str
    label: str | None = None
    score: float | None = None
    scoring_method: str | None = None
    scoring_method_version: str | None = None
    conflicts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    model_version: str | None = None

    @model_validator(mode="after")
    def _validate_score(self) -> "SentimentRecord":
        if self.score is None:
            return self
        if not (SCORE_MIN <= self.score <= SCORE_MAX):
            raise ValueError(f"score {self.score} outside [{SCORE_MIN}, {SCORE_MAX}]")
        if self.scoring_method is None or self.scoring_method_version is None:
            raise ValueError("a score requires its defined, versioned scoring method")
        return self
