"""Read-only model-health router: Ollama discovery (gated on T0004)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from goldmasters_contracts import EvidenceStatus

__all__ = ["router"]

router = APIRouter(prefix="/v1/model-health")


@router.get("", response_model=None)
def read_model_health(request: Request) -> dict[str, object]:
    """Return model health. Unavailable when endpoint unset (T0004 open)."""
    settings = request.app.state.settings
    if settings.ollama_model is None:
        return {
            "status": EvidenceStatus.UNAVAILABLE.value,
            "endpoint": settings.ollama_host,
            "expected_model": None,
            "limitations": ["T0004 open: no model configured"],
        }
    return {
        "status": EvidenceStatus.UNAVAILABLE.value,
        "endpoint": settings.ollama_host,
        "expected_model": settings.ollama_model,
        "limitations": ["model health check not implemented in read-only foundation wave"],
    }
