"""The standard agent envelope (Schema.md §3; D-05/D-06/D-12/D-14/D-21).

Every agent result crosses the boundary wrapped in this envelope, so strictness,
unknown-field rejection and immutability are inherited from
:class:`~goldmasters_contracts._base.ContractModel`.

``schema_version`` uses the version-acceptance type that fails closed on an
unknown major, missing, or unparseable version (D-05/D-23). ``run_id`` uses the
prefix-bound ``run_`` identifier type (D-14/D-21). ``result`` stays an open
object because each agent declares its own result contract; an empty object is
not a claim that the envelope itself is complete.
"""

from __future__ import annotations

from typing import Any

from goldmasters_contracts._base import ContractModel, UtcDatetime
from goldmasters_contracts.enums import AgentRunStatus
from goldmasters_contracts.errors import ErrorPayload
from goldmasters_contracts.ids import RunId
from goldmasters_contracts.versions import SchemaVersionStr

__all__ = ["Envelope"]


class Envelope(ContractModel):
    """Schema.md §3, field for field — and no field more."""

    schema_version: SchemaVersionStr
    run_id: RunId
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
