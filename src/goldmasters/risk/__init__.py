"""Deterministic risk-local package (Phase 3, D-3.3)."""

from src.goldmasters.risk.gate import GateVerdict, evaluate_gate, trade_eligible_levels
from src.goldmasters.risk.levels import (
    build_candidate_levels,
    compute_risk_reward,
    validate_level_ordering,
)

__all__ = [
    "GateVerdict",
    "build_candidate_levels",
    "compute_risk_reward",
    "evaluate_gate",
    "trade_eligible_levels",
    "validate_level_ordering",
]
