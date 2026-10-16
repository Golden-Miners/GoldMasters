"""Read-only settings router: non-secret effective configuration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

__all__ = ["router"]

router = APIRouter(prefix="/v1/settings")


def _is_secret_field(settings: Any, name: str) -> bool:
    """True when the field's type involves SecretStr."""
    import typing

    from pydantic import SecretStr

    annotation = type(settings).model_fields[name].annotation
    return annotation is SecretStr or SecretStr in typing.get_args(annotation)


@router.get("", response_model=None)
def read_settings(request: Request) -> dict[str, Any]:
    """Return non-secret effective configuration."""
    settings = request.app.state.settings
    return {
        key: value
        for key, value in settings.model_dump().items()
        if not _is_secret_field(settings, key)
    }
