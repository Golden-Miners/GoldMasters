"""Contract-layer version acceptance (D-02/D-05/D-23).

This module defines the version acceptance rule: a payload whose
``schema_version`` has an unknown major, is missing, or is unparseable is
rejected; a ``1.x`` payload is accepted and never coerced. The version
semantics are ``major.minor`` — adding an enum member or a new optional
field bumps the minor (monotonic within a major); a breaking change bumps
the major. A reader accepts any ``1.x`` and rejects anything else, so a
document written at ``1.2`` stays readable and replayable by a build at
``1.5``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated

from pydantic import AfterValidator, WithJsonSchema

__all__ = [
    "CONTRACT_VERSION_MAJOR_SUPPORTED",
    "ContractVersion",
    "parse_contract_version",
    "SchemaVersionStr",
]

#: The single supported major version for the contract layer (D-02/D-23).
CONTRACT_VERSION_MAJOR_SUPPORTED = 1

#: Pattern for ``major.minor`` or ``major.minor.patch`` where each component
#: is a non-negative integer with no leading zeros (except ``0`` itself).
_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$")


@dataclass(frozen=True, slots=True)
class ContractVersion:
    """Parsed contract version with major, minor, and optional patch."""

    major: int
    minor: int
    patch: int | None

    def __str__(self) -> str:
        if self.patch is not None:
            return f"{self.major}.{self.minor}.{self.patch}"
        return f"{self.major}.{self.minor}"


def parse_contract_version(raw: str) -> ContractVersion:
    """Parse and validate a contract version string.

    Args:
        raw: Version string in ``major.minor`` or ``major.minor.patch`` form.

    Returns:
        A :class:`ContractVersion` with the parsed components.

    Raises:
        ValueError: If ``raw`` is empty, unparseable, has a non-numeric
            component, has a ``v`` prefix, or has a major version other than
            :data:`CONTRACT_VERSION_MAJOR_SUPPORTED`.
    """
    if not raw:
        raise ValueError("schema_version is missing")

    if raw.startswith("v"):
        raise ValueError(f"schema_version {raw!r} has a 'v' prefix — not accepted")

    match = _VERSION_PATTERN.fullmatch(raw)
    if not match:
        raise ValueError(f"schema_version {raw!r} is not a valid major.minor[.patch] string")

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3)) if match.group(3) else None

    if major != CONTRACT_VERSION_MAJOR_SUPPORTED:
        raise ValueError(
            f"schema_version {raw!r} has unsupported major version {major}; "
            f"only major {CONTRACT_VERSION_MAJOR_SUPPORTED} is accepted"
        )

    return ContractVersion(major=major, minor=minor, patch=patch)


def _validate_schema_version(value: str) -> str:
    """Pydantic validator that wraps :func:`parse_contract_version`."""
    parse_contract_version(value)
    return value


#: Annotated string type that fails closed on an unknown major, missing, or
#: unparseable version (D-05/D-23). Use this as the field type for
#: ``schema_version`` in envelope and other contract models.
SchemaVersionStr = Annotated[
    str,
    AfterValidator(_validate_schema_version),
    WithJsonSchema({"type": "string", "pattern": r"^1\.\d+(\.\d+)?$"}),
]
