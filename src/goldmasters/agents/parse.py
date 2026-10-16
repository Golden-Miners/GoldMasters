"""Role output schemas plus validation: untrusted until proven (T-04-05).

Every generation is format-pinned to one of these Pydantic schemas with
temperature 0, then ``model_validate_json`` — model text is untrusted until
that passes. Parse failure yields a sanitized Schema §10 error; callers
retry bounded and then fail closed, never a filled-in guess. No schema
carries a level, regime, R:R, or recommendation field (roles.md rule 3) —
a test pins that the forbidden names stay out.
"""

from __future__ import annotations

from typing import TypeVar

from goldmasters_contracts import ContractModel, ErrorCode, ErrorPayload
from pydantic import Field

from src.goldmasters.agents.prompts import ROLE_SPECS

__all__ = [
    "AnalystNote",
    "CeoProse",
    "ResearchFindings",
    "SentimentExtraction",
    "ROLE_OUTPUTS",
    "parse_output",
    "role_output_model",
]

T = TypeVar("T", bound=ContractModel)


class AnalystNote(ContractModel):
    """Market Analyst text (T0404): evidence/reason strings, no numbers."""

    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class SentimentExtraction(ContractModel):
    """News/Sentiment extraction (T0405): evidence/reason strings, no scores."""

    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ResearchFindings(ContractModel):
    """Research with citations (T0406): findings plus source URLs/versions."""

    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    sources: list[str] = Field(default_factory=list)


class CeoProse(ContractModel):
    """CEO prose (T0410): thesis/invalidation text only, never levels."""

    thesis: str = Field(min_length=1)
    invalidation: str = Field(min_length=1)


#: Role name -> its pinned output schema (``format=`` source of truth).
ROLE_OUTPUTS: dict[str, type[ContractModel]] = {
    "market_analyst": AnalystNote,
    "news_sentiment": SentimentExtraction,
    "research": ResearchFindings,
    "ceo": CeoProse,
}


def role_output_model(role: str) -> type[ContractModel]:
    """The pinned schema for a role; unknown roles are caller errors."""
    if role not in ROLE_OUTPUTS or role not in ROLE_SPECS:
        raise KeyError(f"unknown LLM role: {role}")
    return ROLE_OUTPUTS[role]


def parse_output(
    model: type[T], content: str, *, run_id: str, node: str
) -> tuple[T | None, ErrorPayload | None]:
    """Validate raw model text; malformed output never reaches a decision."""
    try:
        return model.model_validate_json(content), None
    except Exception as exc:  # noqa: BLE001 — boundary sanitizer, never a guess
        return None, ErrorPayload(
            code=ErrorCode.CONTRACT_VALIDATION_FAILED,
            message=f"{type(exc).__name__} in graph node {node}",
            retryable=False,
            correlation_id=run_id,
            details=None,
        )
