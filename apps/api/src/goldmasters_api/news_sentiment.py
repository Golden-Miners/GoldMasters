"""Read-only news + sentiment router (fail-closed: no sources registered)."""

from __future__ import annotations

from fastapi import APIRouter
from goldmasters_contracts import EvidenceStatus

from src.goldmasters.data.news.base import SOURCE_REGISTRY

__all__ = ["router"]

router = APIRouter(prefix="/v1/news-sentiment")


@router.get("", response_model=None)
def read_news_sentiment() -> dict[str, object]:
    """Return news + sentiment state. Fail-closed: unavailable when no sources."""
    if not SOURCE_REGISTRY:
        return {
            "status": EvidenceStatus.UNAVAILABLE.value,
            "items": [],
            "limitations": ["no news sources registered (D-5.1)"],
        }
    return {
        "status": EvidenceStatus.UNAVAILABLE.value,
        "items": [],
        "limitations": ["news sources registered but not fetchable via read-only API"],
    }
