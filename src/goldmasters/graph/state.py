"""Deterministic run state: typed TypedDict, input snapshot, minimal run log.

D-4.1: the run state is a ``TypedDict`` every node reads and writes with
contract-validated payloads only. D-4.3: the persisted run log is minimal —
run id, input ref, config/version ids, timestamps, per-node status. Outcomes
and journal stay Phase 6, so :func:`run_log` exposes exactly those keys and
the boundary test pins them.
"""

from __future__ import annotations

import hashlib
import json
import operator
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict

from goldmasters_contracts import (
    AgentRunStatus,
    DecisionRecord,
    ErrorPayload,
    EvidenceStatus,
    MarketBar,
)

from src.goldmasters.strategies.base import MarketContext, StrategyEvaluation
from src.goldmasters.risk.gate import GateVerdict

__all__ = [
    "MINIMAL_LOG_KEYS",
    "RunState",
    "compute_input_ref",
    "run_log",
    "utc_now_iso",
]

#: The exact D-4.3 minimal-log key set; the boundary test pins this frozenset
#: so outcomes/journal can never leak into the Phase 4 run record.
MINIMAL_LOG_KEYS = frozenset(
    {
        "run_id",
        "input_ref",
        "config_hash",
        "code_versions",
        "started_at",
        "node_statuses",
        "node_times",
    }
)


class RunState(TypedDict):
    """One bounded deterministic run (D-4.1, RESEARCH Pattern 1)."""

    run_id: str
    input_ref: str  # snapshot hash of (bars, ctx); resume binding (T-04-04)
    config_hash: str  # GOLDMASTERS_ effective-config hash (existing helper)
    code_versions: dict[str, str]  # strategy_id -> "version@code_hash" stamps
    agent_statuses: dict[str, str]  # node/agent -> AgentRunStatus verbatim value
    evidence: dict[str, str]  # evidence key -> EvidenceStatus verbatim value
    conflicts: Annotated[list[str], operator.add]  # append-only, never overwrite
    evaluations: dict[str, StrategyEvaluation]  # strategy_id -> Phase 3 evaluation
    gate_verdict: GateVerdict | None
    barrier_passed: bool | None
    barrier_reasons: list[str]
    decision: DecisionRecord | None
    errors: dict[str, ErrorPayload]  # node/agent -> sanitized Schema §10 error
    fatal: str | None  # stage name that failed fatally (skip-ahead routing)
    eligible: list[str]  # sorted eligible strategy_ids (the fan-out set)
    bars: list[MarketBar]
    market_context: MarketContext
    started_at: str  # ISO-8601 UTC instant the run was assembled
    node_times: dict[str, str]  # node -> ISO-8601 UTC completion instant


def utc_now_iso() -> str:
    """Now as timezone-aware ISO-8601 UTC (Schema §1: never naive)."""
    return datetime.now(UTC).isoformat()


def compute_input_ref(bars: list[MarketBar], ctx: MarketContext) -> str:
    """Snapshot hash binding a run to its exact inputs (T-04-04).

    Canonical JSON of the validated bars plus context, sha256 hex. A resume
    with a different input set hashes differently and fails closed.
    """
    payload = {
        "bars": [bar.model_dump(mode="json") for bar in bars],
        "ctx": ctx.model_dump(mode="json"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verbatim_statuses(statuses: dict[str, str]) -> dict[str, str]:
    """Round-trip status strings through the closed enum (D-23, no new members)."""
    return {node: AgentRunStatus(status).value for node, status in statuses.items()}


def _verbatim_evidence(evidence: dict[str, str]) -> dict[str, str]:
    """Round-trip evidence strings through the closed enum."""
    return {key: EvidenceStatus(status).value for key, status in evidence.items()}


def run_log(state: RunState) -> dict[str, Any]:
    """The D-4.3 minimal run log: ids, timestamps, per-node status only.

    No outcomes, no levels, no journal — Phase 6 owns those. Verbatim enum
    round-trips prove no magic status strings (Schema §1).
    """
    return {
        "run_id": state["run_id"],
        "input_ref": state["input_ref"],
        "config_hash": state["config_hash"],
        "code_versions": dict(state["code_versions"]),
        "started_at": state["started_at"],
        "node_statuses": _verbatim_statuses(state["agent_statuses"]),
        "node_times": dict(state["node_times"]),
    }
