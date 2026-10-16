"""Read-only agent-runs router: graph run log (no persistence layer)."""

from __future__ import annotations

from fastapi import APIRouter

__all__ = ["router"]

router = APIRouter(prefix="/v1/agent-runs")


@router.get("", response_model=None)
def list_agent_runs() -> dict[str, object]:
    """Return agent run state. No persistence layer exists for run logs."""
    return {
        "status": "unavailable",
        "runs": [],
        "limitations": ["graph run log has no persistence layer; runs are in-memory only"],
    }
