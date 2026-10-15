"""Strategy interface: evaluate() returns setup_found + rule_checks (D-3.1).

This module is the vocabulary every future approved strategy speaks — and
the constraint none can evade. The hard rule is encoded in
:class:`StrategyEvaluation`: any rule verdict other than ``pass`` (``fail``
*or* ``unknown``) means no setup and null levels, enforced by a Pydantic
validator so no future strategy package can emit levels on a failed rule.

No approved strategy packages exist yet (03-CONTEXT.md non-goals); only this
interface and its contract tests land here. ``STRATEGY_VERSION`` is semver
and is bumped on any rule change.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Literal, Protocol, runtime_checkable

from goldmasters_contracts import ContractModel, Levels, MarketBar
from pydantic import Field, model_validator

__all__ = [
    "RuleCheck",
    "RuleVerdict",
    "Strategy",
    "StrategyEvaluation",
    "build_evaluation",
    "hash_rule_source",
]

#: One verdict per rule: pass, fail, or unknown (Schema.md §8).
RuleVerdict = Literal["pass", "fail", "unknown"]


def hash_rule_source(source: str) -> str:
    """Integrity label over a rule text (hashlib stdlib; not tamper-proofing)."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class RuleCheck(ContractModel):
    """One rule's evidence: ID, verdict, observed inputs, trace, reason."""

    rule_id: str = Field(min_length=1)
    verdict: RuleVerdict
    inputs: dict[str, str] = Field(default_factory=dict)
    evidence: str
    reason: str


class StrategyEvaluation(ContractModel):
    """A strategy evaluation: setup flag plus per-rule evidence (Schema.md §8).

    Invariants (the no-escape clause): any non-``pass`` verdict forces
    ``setup_found=False`` with null levels; a ``True`` setup must carry
    candidate levels produced by defined rules.
    """

    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    code_hash: str = Field(min_length=1)
    setup_found: bool
    rule_checks: list[RuleCheck] = Field(min_length=1)
    candidate_levels: Levels | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_no_setup_on_fail(self) -> StrategyEvaluation:
        blocked = any(check.verdict != "pass" for check in self.rule_checks)
        if blocked and (self.setup_found or self.candidate_levels is not None):
            raise ValueError("any rule fail/unknown means no setup and null levels")
        if self.setup_found and self.candidate_levels is None:
            raise ValueError("a found setup must carry candidate levels from defined rules")
        if not self.setup_found and self.candidate_levels is not None:
            raise ValueError("no setup must carry null levels")
        return self


def build_evaluation(
    *,
    strategy_id: str,
    strategy_version: str,
    code_hash: str,
    rule_checks: Sequence[RuleCheck],
    candidate_levels: Levels | None = None,
    limitations: Sequence[str] = (),
) -> StrategyEvaluation:
    """Build a stamped evaluation; the invariants are enforced on construction."""
    return StrategyEvaluation(
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        code_hash=code_hash,
        setup_found=all(check.verdict == "pass" for check in rule_checks)
        and candidate_levels is not None,
        rule_checks=list(rule_checks),
        candidate_levels=candidate_levels,
        limitations=list(limitations),
    )


@runtime_checkable
class Strategy(Protocol):
    """What every future approved strategy package implements (D-3.1)."""

    STRATEGY_ID: str
    STRATEGY_VERSION: str
    CODE_HASH: str

    def evaluate(self, bars: Sequence[MarketBar]) -> StrategyEvaluation:
        """Evaluate closed bars; never emit levels on a failed rule."""
        ...
