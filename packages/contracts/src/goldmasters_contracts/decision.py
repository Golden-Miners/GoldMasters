"""Signal decision contract (Schema.md §6; D-04).

A decision is a research candidate, never an order. ``manual_review_required``
is always ``True`` in V1. Levels (``entry``/``stop_loss``/``take_profits``/
``risk_reward``) stay null unless validated: a ``TRADE`` decision must carry
every level, any other decision must carry none. Level *ordering* policy is
Phase 3 work (D-04), not enforced here.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator

from goldmasters_contracts._base import ContractModel, PriceStr, UtcDatetime
from goldmasters_contracts.enums import (
    AgentRunStatus,
    Decision,
    Direction,
    QualityStatus,
    Timeframe,
)
from goldmasters_contracts.ids import DecId, RunId

__all__ = [
    "DecisionRecord",
    "Levels",
]


class Levels(ContractModel):
    """Validated level bundle: only produced by deterministic code (Phase 3)."""

    entry: PriceStr
    stop_loss: PriceStr
    take_profits: list[PriceStr] = Field(min_length=1)
    risk_reward: Decimal


class DecisionRecord(ContractModel):
    """Schema.md §6, field for field."""

    decision_id: DecId
    run_id: RunId
    instrument_id: str
    timeframe: Timeframe
    decision: Decision
    direction: Direction | None = None
    created_at: UtcDatetime
    data_as_of: UtcDatetime
    strategy_id: str | None = None
    strategy_version: str | None = None
    entry: PriceStr | None = None
    stop_loss: PriceStr | None = None
    take_profits: list[PriceStr] = Field(default_factory=list)
    risk_reward: Decimal | None = None
    thesis: str
    invalidation_conditions: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    reasons_for_rejection: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    agent_statuses: dict[str, AgentRunStatus] = Field(default_factory=dict)
    conflicts: list[str] = Field(default_factory=list)
    data_quality_status: QualityStatus
    limitations: list[str] = Field(default_factory=list)
    manual_review_required: bool = True

    @model_validator(mode="after")
    def _validate_decision_invariants(self) -> DecisionRecord:
        if self.manual_review_required is not True:
            raise ValueError("manual_review_required must be true for every V1 decision")
        has_levels = (
            self.entry is not None
            or self.stop_loss is not None
            or len(self.take_profits) > 0
            or self.risk_reward is not None
        )
        complete_levels = (
            self.entry is not None
            and self.stop_loss is not None
            and len(self.take_profits) > 0
            and self.risk_reward is not None
        )
        if self.decision == Decision.TRADE:
            if self.direction is None:
                raise ValueError("a TRADE decision must carry a direction")
            if not complete_levels:
                raise ValueError("a TRADE decision must carry all validated levels")
        elif has_levels:
            raise ValueError("a non-TRADE decision must keep levels null")
        return self

    def validated_levels(self) -> Levels | None:
        """Return the level bundle when complete, else ``None``."""
        if (
            self.entry is not None
            and self.stop_loss is not None
            and len(self.take_profits) > 0
            and self.risk_reward is not None
        ):
            return Levels(
                entry=self.entry,
                stop_loss=self.stop_loss,
                take_profits=self.take_profits,
                risk_reward=self.risk_reward,
            )
        return None
