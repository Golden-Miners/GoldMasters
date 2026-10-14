"""The standard agent envelope (Schema.md §3; D-06/D-12).

Every agent result crosses the boundary wrapped in this envelope, so strictness,
unknown-field rejection and immutability are inherited from
:class:`~goldmasters_contracts._base.ContractModel`.

``schema_version``, ``run_id`` and ``agent_version`` are plain strings for now:
plan 01-03 refines them with the version-acceptance and prefix-bound identifier
types (D-05/D-14/D-21). ``result`` stays an open object because each agent
declares its own result contract; an empty object is not a claim that the
envelope itself is complete.
"""

from __future__ import annotations

from typing import Any

from goldmasters_contracts._base import ContractModel, UtcDatetime
from goldmasters_contracts.enums import AgentRunStatus
from goldmasters_contracts.errors import ErrorPayload

__all__ = ["Envelope"]


class Envelope(ContractModel):
    """Schema.md §3, field for field — and no field more."""

    schema_version: str
    run_id: str
    agent_name: str
    agent_version: str
    status: AgentRunStatus
    created_at: UtcDatetime
    as_of: UtcDatetime | None
    input_refs: list[str]
    evidence_refs: list[str]
    limitations: list[str]
    error: ErrorPayload | None
    result: dict[str, Any]
