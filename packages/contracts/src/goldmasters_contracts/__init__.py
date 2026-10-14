"""GoldMasters shared contracts.

This module is the single import surface for the ``goldmasters-contracts``
distribution: every contract module and :data:`CONTRACT_VERSION` is re-exported
here so consumers (the API, the TypeScript type generator, and later phases)
import one name rather than reaching into submodules. Plans 03 and 11 extend the
barrel as they add contracts; it is never replaced.
"""

from __future__ import annotations

from goldmasters_contracts._base import (
    DECIMAL_PATTERN,
    ContractModel,
    IanaTimezone,
    PriceStr,
    UtcDatetime,
)
from goldmasters_contracts.enums import (
    AgentRunStatus,
    Decision,
    Direction,
    EvidenceStatus,
    QualityFlag,
    QualityStatus,
    Timeframe,
    TrendRegime,
    VolumeType,
)
from goldmasters_contracts.envelope import Envelope
from goldmasters_contracts.errors import RETRYABLE_CODES, ErrorCode, ErrorPayload
from goldmasters_contracts.ids import AgentId, DecId, IdPrefix, PrefixedId, ProviderId, RunId
from goldmasters_contracts.versions import (
    CONTRACT_VERSION_MAJOR_SUPPORTED,
    ContractVersion,
    SchemaVersionStr,
    parse_contract_version,
)

__all__ = [
    "CONTRACT_VERSION",
    "CONTRACT_VERSION_MAJOR_SUPPORTED",
    "AgentId",
    "AgentRunStatus",
    "ContractModel",
    "ContractVersion",
    "DECIMAL_PATTERN",
    "DecId",
    "Decision",
    "Direction",
    "Envelope",
    "ErrorCode",
    "ErrorPayload",
    "EvidenceStatus",
    "IanaTimezone",
    "IdPrefix",
    "PrefixedId",
    "PriceStr",
    "ProviderId",
    "QualityFlag",
    "QualityStatus",
    "RETRYABLE_CODES",
    "RunId",
    "SchemaVersionStr",
    "Timeframe",
    "TrendRegime",
    "UtcDatetime",
    "VolumeType",
    "parse_contract_version",
]

# The contract-layer version shared by every contract (Schema.md §1; D-02/D-23).
# It is a ``major.minor`` string: a reader accepts any ``1.x`` and rejects an
# unknown major, so a document written at ``1.0`` stays readable and replayable
# by a later ``1.x`` build.
CONTRACT_VERSION = "1.0"