"""Prefix-bound identifiers and provider identity key (D-14/D-21/D-25).

This module defines:
- :class:`IdPrefix`: a closed enum with one member per entity type and its
  canonical prefix string (e.g. ``run_``, ``dec_``, ``agent_``).
- :func:`PrefixedId`: a factory that returns an annotated string type
  validating that the value starts with the given entity's prefix and the
  remainder parses as a UUID using only the standard library.
- :data:`ProviderId`: an annotated type for a stable lowercase snake_case
  provider key (not a display name, not the provider's own naming).
"""

from __future__ import annotations

import re
import uuid
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, WithJsonSchema
from typing_extensions import Annotated as TypedAnnotated

__all__ = [
    "IdPrefix",
    "PrefixedId",
    "ProviderId",
]


class IdPrefix(StrEnum):
    """Closed registry of entity-type prefixes (D-14/D-21).

    Each member is the canonical prefix for an entity type. Adding an entity
    type is an explicit reviewed change (a new enum member).
    """

    RUN = "run_"
    DEC = "dec_"
    AGENT = "agent_"


#: Pattern for a stable lowercase snake_case provider key (D-25).
#: Lowercase letters, digits, and single underscores only; not a display name.
_PROVIDER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_PROVIDER_ID_ERROR = (
    "provider_id must be a stable lowercase snake_case key "
    "(e.g. 'mt5', 'alpha_vantage') — not a display name"
)


def _validate_provider_id(value: str) -> str:
    """Validate that a provider_id matches the required pattern."""
    if not _PROVIDER_ID_PATTERN.fullmatch(value):
        raise ValueError(_PROVIDER_ID_ERROR)
    return value


#: Annotated type for a stable lowercase snake_case provider identity key (D-25).
#: The registry of real provider IDs is created in Phase 2 with the adapters.
ProviderId = Annotated[
    str,
    AfterValidator(_validate_provider_id),
    WithJsonSchema({"type": "string", "pattern": _PROVIDER_ID_PATTERN.pattern}),
]


def _prefixed_id_validator(prefix: IdPrefix):
    """Create a validator for a specific prefix."""

    def _validate(value: str) -> str:
        expected_prefix = prefix.value
        if not value.startswith(expected_prefix):
            raise ValueError(
                f"{prefix.name.lower()}_id must start with prefix {expected_prefix!r}, "
                f"got {value!r}"
            )
        uuid_part = value[len(expected_prefix) :]
        try:
            # Validate UUID shape using stdlib only (D-14/D-21).
            # Accept any UUID version; the shape is what matters.
            uuid.UUID(uuid_part)
        except ValueError as exc:
            raise ValueError(
                f"{prefix.name.lower()}_id has malformed UUID body after prefix "
                f"{expected_prefix!r}: {exc}"
            ) from exc
        return value

    return _validate


def PrefixedId(prefix: IdPrefix):
    """Return an annotated string type that validates a prefixed UUID.

    Args:
        prefix: The :class:`IdPrefix` enum member for the entity type.

    Returns:
        An ``Annotated[str, ...]`` type that enforces:
        1. The value starts with exactly that entity's prefix.
        2. The remainder parses as a UUID using stdlib ``uuid`` only.

    The generated type includes a JSON schema with a pattern reflecting the
    prefix and UUID shape.
    """
    validator = _prefixed_id_validator(prefix)
    pattern = rf"^{re.escape(prefix.value)}[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$"
    return Annotated[
        str,
        BeforeValidator(validator),
        WithJsonSchema({"type": "string", "pattern": pattern}),
    ]


# Convenience re-exports for the three core entity types.
RunId = PrefixedId(IdPrefix.RUN)
DecId = PrefixedId(IdPrefix.DEC)
AgentId = PrefixedId(IdPrefix.AGENT)