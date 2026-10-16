"""Pre-CEO validation barrier: deterministic, no LLM (criterion 3, T0402).

The barrier re-validates everything the decision rests on — evidence all
``VALID``, data quality ``OK`` with zero flags, a gate verdict present whose
conflicts match the run's verbatim — and fails closed otherwise. A breach
routes the terminal mapper to ``INSUFFICIENT_DATA``; the barrier never
reconciles, filters, or summarizes disagreements.
"""

from __future__ import annotations

from typing import Any

from goldmasters_contracts import AgentRunStatus, EvidenceStatus, QualityStatus

from src.goldmasters.graph import edges
from src.goldmasters.graph.state import NodeFn, RunState, utc_now_iso

__all__ = ["check_barrier", "check_ceo_required", "make_barrier_node"]


def check_barrier(state: RunState) -> list[str]:
    """Re-validate the run's decision inputs; empty list means pass.

    Pure predicate so the barrier policy unit-tests without the graph.
    """
    reasons: list[str] = []
    verdict = state["gate_verdict"]
    if verdict is None:
        reasons.append("no gate verdict present")
    elif list(verdict.conflicts) != list(state["conflicts"]):
        reasons.append("conflicts not preserved verbatim through the gate")
    invalid = sorted(
        key for key, value in state["evidence"].items() if value != EvidenceStatus.VALID.value
    )
    if invalid:
        reasons.extend(f"evidence not valid: {key}" for key in invalid)
    if not state["evidence"] and state["eligible"]:
        reasons.append("evidence incomplete: no eligible agent reported back")
    ctx = state["market_context"]
    if ctx.quality_status != QualityStatus.OK or len(ctx.quality_flags) > 0:
        reasons.append(
            f"data quality not healthy: status={ctx.quality_status.value}, "
            f"flags={[flag.value for flag in ctx.quality_flags]}"
        )
    return reasons


def check_ceo_required(statuses: dict[str, str], required: frozenset[str]) -> list[str]:
    """CEO agreement gate: every required node must report ``ok``.

    The CEO must never infer that a failed agent agreed (Rules §3.4): any
    required node missing from the full status map or reporting non-ok
    blocks CEO prose with reasons, and the caller fails closed to
    ``INSUFFICIENT_DATA`` without calling the model.
    """
    reasons: list[str] = []
    for node in sorted(required):
        status = statuses.get(node)
        if status is None:
            reasons.append(f"ceo blocked: required node {node} has no status")
        elif status != AgentRunStatus.OK.value:
            reasons.append(f"ceo blocked: required node {node} is {status}, not ok")
    return reasons


def make_barrier_node() -> NodeFn:
    """Barrier as a graph node: records pass/fail, never raises on breach."""

    async def barrier(state: RunState) -> dict[str, Any]:
        reasons = check_barrier(state)
        passed = not reasons
        return {
            "agent_statuses": {
                **state["agent_statuses"],
                edges.BARRIER: (AgentRunStatus.OK.value if passed else AgentRunStatus.ERROR.value),
            },
            "node_times": {**state["node_times"], edges.BARRIER: utc_now_iso()},
            "barrier_passed": passed,
            "barrier_reasons": reasons,
        }

    return barrier
