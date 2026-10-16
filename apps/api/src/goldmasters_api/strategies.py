"""Read-only strategies router: eligible strategy agents from settings."""

from __future__ import annotations

from fastapi import APIRouter, Request

__all__ = ["router"]

router = APIRouter(prefix="/v1/strategies")


@router.get("", response_model=None)
def list_strategies(request: Request) -> list[dict[str, object]]:
    """List strategy agents with their eligibility configuration."""
    settings = request.app.state.settings
    agents: list[dict[str, object]] = []
    for n in range(1, 11):
        prefix = f"strategy_agent_{n:02d}"
        agents.append(
            {
                "agent_id": f"agent_{n:02d}",
                "enabled": getattr(settings, f"{prefix}_enabled"),
                "instruments": list(getattr(settings, f"{prefix}_instruments")),
                "timeframes": [tf.value for tf in getattr(settings, f"{prefix}_timeframes")],
                "regimes": [r.value for r in getattr(settings, f"{prefix}_regimes")],
                "min_bars": getattr(settings, f"{prefix}_min_bars"),
            }
        )
    return agents
