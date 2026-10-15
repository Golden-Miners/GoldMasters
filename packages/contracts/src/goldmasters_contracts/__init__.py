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
from goldmasters_contracts.backtest import (
    BacktestAssumptions,
    BacktestMetric,
    BacktestRecord,
)
from goldmasters_contracts.decision import DecisionRecord, Levels
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
from goldmasters_contracts.ids import (
    AgentId,
    DecId,
    IdPrefix,
    JournalId,
    PrefixedId,
    ProviderId,
    RunId,
)
from goldmasters_contracts.journal import JournalEntry
from goldmasters_contracts.market import InstrumentId, MarketBar, MarketQuote
from goldmasters_contracts.news import InstrumentMapping, NewsItem
from goldmasters_contracts.precision import (
    PrecisionLookupResult,
    PrecisionRow,
    PrecisionTable,
)
from goldmasters_contracts.sentiment import SCORE_MAX, SCORE_MIN, SentimentRecord
from goldmasters_contracts.versions import (
    CONTRACT_VERSION_MAJOR_SUPPORTED,
    ContractVersion,
    SchemaVersionStr,
    parse_contract_version,
)

__all__ = [
    "CONTRACT_VERSION",
    "CONTRACT_VERSION_MAJOR_SUPPORTED",
    "DECIMAL_PATTERN",
    "RETRYABLE_CODES",
    "SCORE_MAX",
    "SCORE_MIN",
    "AgentId",
    "AgentRunStatus",
    "BacktestAssumptions",
    "BacktestMetric",
    "BacktestRecord",
    "ContractModel",
    "ContractVersion",
    "DecId",
    "Decision",
    "DecisionRecord",
    "Direction",
    "Envelope",
    "ErrorCode",
    "ErrorPayload",
    "EvidenceStatus",
    "IanaTimezone",
    "IdPrefix",
    "InstrumentId",
    "InstrumentMapping",
    "JournalEntry",
    "JournalId",
    "Levels",
    "MarketBar",
    "MarketQuote",
    "NewsItem",
    "PrecisionLookupResult",
    "PrecisionRow",
    "PrecisionTable",
    "PrefixedId",
    "PriceStr",
    "ProviderId",
    "QualityFlag",
    "QualityStatus",
    "RunId",
    "SchemaVersionStr",
    "SentimentRecord",
    "Timeframe",
    "TrendRegime",
    "UtcDatetime",
    "VolumeType",
    "parse_contract_version",
]

# The contract-layer version shared by every contract (Schema.md §1; D-02/D-23).
# It is a ``major.minor`` string: a reader accepts any ``1.x`` and rejects an
# unknown major, so a document written at ``1.0`` stays readable and replayable
# by a later ``1.x`` build. Bumped to ``1.1`` for the Phase 2 ``QualityStatus.OK``
# enum addition (vocabularies only grow — a minor bump per D-23).
CONTRACT_VERSION = "1.1"
