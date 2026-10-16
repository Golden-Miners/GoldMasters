"""Decision traceability: measured before any target is set (criterion 5).

A decision is traceable when every entry of its ``evidence_refs`` resolves
to a persisted envelope AND the run carries configuration/version metadata
(``config_hash`` plus ``code_versions`` from ``RunState``; agent versions
from ``ROLE_SPECS`` ride along for display). Read-only over persisted
decisions plus state fields — no target threshold is set anywhere here.
Display is operator-visible via a log line; any console surface belongs to
Phase 7.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from goldmasters_contracts import DecisionRecord

from src.goldmasters.agents.prompts import ROLE_SPECS
from src.goldmasters.graph.state import RunState

__all__ = [
    "TraceabilityReport",
    "format_traceability",
    "is_traceable",
    "log_traceability",
    "report_for_state",
    "traceability_report",
]

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class TraceabilityReport:
    """One measurement over a decision set: counts, percent, agent versions."""

    total: int
    complete: int
    percent: float  # 0..100; 100.0 on the empty set (nothing incomplete)
    agent_versions: dict[str, str]
    incomplete_ids: tuple[str, ...]


def _agent_versions() -> dict[str, str]:
    """Role name -> pinned version (roles.md 0.1.0 convention)."""
    return {role: spec.version for role, spec in ROLE_SPECS.items()}


def is_traceable(
    decision: DecisionRecord,
    *,
    envelopes: Mapping[str, Any],
    config_hash: str,
    code_versions: Mapping[str, str],
) -> bool:
    """One decision: every ref resolves and run metadata is present.

    An empty ``evidence_refs`` is incomplete — a decision with no evidence
    references traces to nothing.
    """
    refs_ok = bool(decision.evidence_refs) and all(
        ref in envelopes for ref in decision.evidence_refs
    )
    meta_ok = bool(config_hash) and bool(code_versions)
    return refs_ok and meta_ok


def traceability_report(
    decisions: Sequence[DecisionRecord],
    *,
    envelopes: Mapping[str, Any],
    config_hash: str,
    code_versions: Mapping[str, str],
) -> TraceabilityReport:
    """Percentage of decisions with complete evidence refs plus metadata."""
    incomplete = tuple(
        decision.decision_id
        for decision in decisions
        if not is_traceable(
            decision, envelopes=envelopes, config_hash=config_hash, code_versions=code_versions
        )
    )
    total = len(decisions)
    complete = total - len(incomplete)
    percent = 100.0 * complete / total if total else 100.0
    return TraceabilityReport(
        total=total,
        complete=complete,
        percent=percent,
        agent_versions=_agent_versions(),
        incomplete_ids=incomplete,
    )


def report_for_state(
    decisions: Sequence[DecisionRecord],
    envelopes: Mapping[str, Any],
    state: RunState,
) -> TraceabilityReport:
    """Convenience: metadata straight from the run state's own fields."""
    return traceability_report(
        decisions,
        envelopes=envelopes,
        config_hash=state["config_hash"],
        code_versions=state["code_versions"],
    )


def format_traceability(report: TraceabilityReport) -> str:
    """The operator-visible line: counts, percent, versions, gaps."""
    line = (
        f"decision traceability: {report.complete}/{report.total} complete "
        f"({report.percent:.1f}%) | "
        f"agents={{{', '.join(f'{r}={v}' for r, v in sorted(report.agent_versions.items()))}}}"
    )
    if report.incomplete_ids:
        line += f" | incomplete={list(report.incomplete_ids)}"
    return line


def log_traceability(report: TraceabilityReport) -> str:
    """Emit the operator-visible line at info; return it for tests/callers."""
    line = format_traceability(report)
    logger.info(line)
    return line
