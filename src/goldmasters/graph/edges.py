"""Explicit conditional edges: failure routing, never silent skips (D-4.1).

Every branch is a named function returning a literal node name, so the
failure policy reads as routing table, not hidden control flow. A fatal
stage failure skips ahead to ``finalize``, which maps it to
``INSUFFICIENT_DATA`` — no path strands a run without a terminal decision.
"""

from __future__ import annotations

from src.goldmasters.graph.state import RunState

__all__ = [
    "BARRIER",
    "EVALUATE",
    "FINALIZE",
    "GATE",
    "INGEST",
    "SELECT",
    "route_after_evaluate",
    "route_after_gate",
    "route_after_ingest",
]

INGEST = "ingest"
SELECT = "select"
EVALUATE = "evaluate"
GATE = "gate"
BARRIER = "barrier"
FINALIZE = "finalize"


def route_after_ingest(state: RunState) -> str:
    """Malformed input skips straight to the terminal mapper."""
    if state["fatal"] is not None:
        return FINALIZE
    return SELECT


def route_after_evaluate(state: RunState) -> str:
    """A broken fan-out (count mismatch) skips the gate to the terminal mapper."""
    if state["fatal"] is not None:
        return FINALIZE
    return GATE


def route_after_gate(state: RunState) -> str:
    """A crashed gate still records its breach through the barrier node.

    A *blocked* verdict is not fatal — it flows to the barrier, which passes
    complete-evidence blocks through to a terminal ``NO_TRADE``.
    """
    if state["fatal"] is not None:
        return FINALIZE
    return BARRIER
