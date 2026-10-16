"""Bounded async node wrappers: validated I/O around Phase 3 calls (D-4.1).

Every node is ``async def`` (``TimeoutPolicy`` is async-only), reads bounds
from settings at build time, and never re-implements a number: strategy
selection via :func:`eligible_agents`, evaluation via each agent's
``evaluate``, levels via ``build_candidate_levels`` (inside the agents),
and the gate via ``evaluate_gate``. Fan-out is exactly the eligible set —
the evaluate node counts its calls and fails the run on any mismatch.
"""

from __future__ import annotations

import dataclasses
import importlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from goldmasters_api.settings import Settings
from goldmasters_contracts import (
    AgentRunStatus,
    Decision,
    DecisionRecord,
    Direction,
    ErrorCode,
    ErrorPayload,
    EvidenceStatus,
    Levels,
    MarketBar,
)
from pydantic import TypeAdapter

from src.goldmasters.graph import edges
from src.goldmasters.graph.state import NodeFn, RunState, utc_now_iso
from src.goldmasters.risk.gate import GateVerdict, evaluate_gate, trade_eligible_levels
from src.goldmasters.strategies.base import (
    MarketContext,
    StrategyEvaluation,
    eligible_agents,
)

__all__ = [
    "AGENT_MODULES",
    "CEO_STUB_CAUSE",
    "assemble_decision",
    "build_params",
    "code_versions",
    "direction_from_levels",
    "make_evaluate_node",
    "make_finalize_node",
    "make_gate_node",
    "make_ingest_node",
    "make_select_node",
    "matrix_from_settings",
]

#: The ten approved strategy packages, one per operator-spec rule family.
#: Nodes call these modules — never each other, never re-implemented numbers.
AGENT_MODULES = tuple(f"src.goldmasters.strategies.agent_{n:02d}" for n in range(1, 11))

#: Scope fields shared by every AgentNNParams row; the rest are numerics
#: read from the matching ``GOLDMASTERS_STRATEGY_AGENT_<NN>_*`` settings keys.
_SCOPE_FIELDS = ("enabled", "instruments", "timeframes", "regimes", "min_bars")

_BAR_ADAPTER = TypeAdapter(list[MarketBar])

#: CEO-shaped synthesis has no model runtime yet (T0004 open): the slot
#: exists, is validated, and returns unavailable-with-cause, never prose.
CEO_STUB_CAUSE = "ceo_synthesis unavailable: no model runtime (T0004 open)"


def _params_class(module_name: str) -> Any:
    """The single ``AgentNNParams`` dataclass of a strategy package."""
    module = importlib.import_module(module_name)
    for value in vars(module).values():
        if (
            isinstance(value, type)
            and dataclasses.is_dataclass(value)
            and value.__name__.startswith("Agent")
        ):
            return value
    raise ValueError(f"no AgentNNParams dataclass in {module_name}")


def _numeric_kwargs(params_class: Any, prefix: str, settings: Settings) -> dict[str, Any]:
    """Numerics for one agent row: settings values, lists read as tuples."""
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(params_class):
        if field.name in _SCOPE_FIELDS:
            continue
        value = getattr(settings, f"{prefix}_{field.name}")
        kwargs[field.name] = tuple(value) if isinstance(value, list) else value
    return kwargs


def build_params(module_name: str, agent_no: str, settings: Settings) -> Any:
    """One agent's params row from declared settings (fail-closed downstream)."""
    params_class = _params_class(module_name)
    prefix = f"strategy_agent_{agent_no}"
    return params_class(
        enabled=getattr(settings, f"{prefix}_enabled"),
        instruments=tuple(getattr(settings, f"{prefix}_instruments")),
        timeframes=tuple(getattr(settings, f"{prefix}_timeframes")),
        regimes=tuple(getattr(settings, f"{prefix}_regimes")),
        min_bars=getattr(settings, f"{prefix}_min_bars"),
        **_numeric_kwargs(params_class, prefix, settings),
    )


def matrix_from_settings(settings: Settings) -> list[Any]:
    """Eligibility matrix rows for all ten agents (T0407 supervisor seam).

    Numerics ride through unset (``None`` fails closed at evaluate time);
    scope comes from declared settings only. An empty instrument list means
    none, never all — enforced by :func:`eligible_agents`.
    """
    return [
        importlib.import_module(module).eligibility(build_params(module, f"{n:02d}", settings))
        for n, module in enumerate(AGENT_MODULES, start=1)
    ]


def code_versions() -> dict[str, str]:
    """strategy_id -> ``version@code_hash`` stamps for the run record."""
    stamps: dict[str, str] = {}
    for module_name in AGENT_MODULES:
        module = importlib.import_module(module_name)
        stamps[str(module.STRATEGY_ID)] = f"{module.STRATEGY_VERSION}@{module.CODE_HASH}"
    return stamps


def _stamp(state: RunState, node: str, status: AgentRunStatus) -> dict[str, Any]:
    """Per-node status plus completion instant (D-4.3 minimal log inputs)."""
    return {
        "agent_statuses": {**state["agent_statuses"], node: status.value},
        "node_times": {**state["node_times"], node: utc_now_iso()},
    }


def _sanitized_error(
    node: str, run_id: str, exc: BaseException, *, code: ErrorCode
) -> ErrorPayload:
    """Schema §10 error: stable code, no secrets/paths/traces, run-bound id."""
    return ErrorPayload(
        code=code,
        message=f"{type(exc).__name__} in graph node {node}",
        retryable=code == ErrorCode.INTERNAL_ERROR,
        correlation_id=run_id,
        details=None,
    )


def _status_of(evaluation: StrategyEvaluation) -> AgentRunStatus:
    """Adapter outcome from Phase 3's own encoding (locked gate-input table).

    ``_blocked`` stamps the cause in single-element ``limitations``;
    ``NOT_APPLICABLE`` maps to the verbatim ``skipped`` member (closed enum).
    Only ``SETUP_FOUND`` feeds the gate; every other outcome is recorded with
    rule checks and never reaches it.
    """
    if evaluation.setup_found:
        return AgentRunStatus.OK
    if evaluation.limitations == ["NOT_APPLICABLE"]:
        return AgentRunStatus.SKIPPED
    if evaluation.limitations == ["INSUFFICIENT_DATA"]:
        return AgentRunStatus.INSUFFICIENT_DATA
    return AgentRunStatus.NO_SETUP


def direction_from_levels(levels: Levels) -> Direction | None:
    """Recover direction from validated level geometry (deterministic, no guess).

    Long is ``stop < entry``, short mirrors; anything else has no ordering
    and the gate blocks it (``Direction.UNKNOWN`` has no ordering defined).
    """
    entry = Decimal(str(levels.entry))
    stop = Decimal(str(levels.stop_loss))
    if stop < entry:
        return Direction.LONG
    if entry < stop:
        return Direction.SHORT
    return None


def _describe_candidate(strategy_id: str, evaluation: StrategyEvaluation) -> str:
    """Verbatim candidate rendering for the conflicts list (no reconciliation)."""
    levels = evaluation.candidate_levels
    level_text = (
        f"entry={levels.entry} stop={levels.stop_loss} "
        f"tps={list(levels.take_profits)} rr={levels.risk_reward}"
        if levels is not None
        else "no levels"
    )
    return f"{strategy_id}@{evaluation.strategy_version}: {level_text}"


def make_ingest_node() -> NodeFn:
    """Validate the opening contracts; malformed input fails the run fast."""

    async def ingest(state: RunState) -> dict[str, Any]:
        try:
            bars = _BAR_ADAPTER.validate_python(list(state["bars"]))
            ctx = MarketContext.model_validate(
                state["market_context"].model_dump()
                if isinstance(state["market_context"], MarketContext)
                else state["market_context"]
            )
        except Exception as exc:  # noqa: BLE001 — boundary sanitizer, never a guess
            update = _stamp(state, edges.INGEST, AgentRunStatus.ERROR)
            update["errors"] = {
                **state["errors"],
                edges.INGEST: _sanitized_error(
                    edges.INGEST,
                    state["run_id"],
                    exc,
                    code=ErrorCode.CONTRACT_VALIDATION_FAILED,
                ),
            }
            update["fatal"] = edges.INGEST
            return update
        update = _stamp(state, edges.INGEST, AgentRunStatus.OK)
        update["bars"] = bars
        update["market_context"] = ctx
        return update

    return ingest


def make_select_node(settings: Settings) -> NodeFn:
    """Eligibility verdicts over the ten matrix rows (supervisor seam, T0407)."""

    async def select(state: RunState) -> dict[str, Any]:
        verdicts = eligible_agents(matrix_from_settings(settings), state["market_context"])
        eligible_ids = sorted(sid for sid, verdict in verdicts.items() if verdict == "eligible")
        statuses = dict(state["agent_statuses"])
        for sid in verdicts:
            statuses[sid] = (
                AgentRunStatus.RUNNING.value
                if verdicts[sid] == "eligible"
                else AgentRunStatus.SKIPPED.value
            )
        update = _stamp(state, edges.SELECT, AgentRunStatus.OK)
        update["agent_statuses"] = {
            **statuses,
            edges.SELECT: AgentRunStatus.OK.value,
        }
        update["eligible"] = eligible_ids
        selected_at = utc_now_iso()
        times = dict(update["node_times"])
        for sid in verdicts:
            if verdicts[sid] != "eligible":
                times.setdefault(sid, selected_at)
        update["node_times"] = times
        return update

    return select


def make_evaluate_node(settings: Settings) -> NodeFn:
    """Evaluate exactly the eligible set; crashes degrade to evidence, not silence."""

    async def evaluate(state: RunState) -> dict[str, Any]:
        evaluations: dict[str, StrategyEvaluation] = {}
        statuses = dict(state["agent_statuses"])
        evidence = dict(state["evidence"])
        errors = dict(state["errors"])
        conflicts: list[str] = []
        evaluate_calls = 0
        for index, module_name in enumerate(AGENT_MODULES):
            module = importlib.import_module(module_name)
            sid = str(module.STRATEGY_ID)
            if sid not in state["eligible"]:
                continue
            evaluate_calls += 1
            try:
                evaluation = module.evaluate(
                    state["bars"],
                    state["market_context"],
                    build_params(module_name, f"{index + 1:02d}", settings),
                )
                evaluations[sid] = evaluation
                status = _status_of(evaluation)
                statuses[sid] = status.value
                # A completed report is VALID evidence — except INSUFFICIENT_DATA:
                # the agent could not evaluate, so its evidence is MISSING and
                # the barrier fails the run closed (never NO_TRADE on partial
                # evaluation). Crashes below record INVALID.
                if status is AgentRunStatus.INSUFFICIENT_DATA:
                    evidence[sid] = EvidenceStatus.MISSING.value
                else:
                    evidence[sid] = EvidenceStatus.VALID.value
                if evaluation.setup_found:
                    conflicts.append(_describe_candidate(sid, evaluation))
            except Exception as exc:  # noqa: BLE001 — partial failure, recorded not raised
                statuses[sid] = AgentRunStatus.ERROR.value
                evidence[sid] = EvidenceStatus.INVALID.value
                errors[sid] = _sanitized_error(
                    sid, state["run_id"], exc, code=ErrorCode.INTERNAL_ERROR
                )
        update = _stamp(state, edges.EVALUATE, AgentRunStatus.OK)
        evaluated_at = utc_now_iso()
        times = dict(update["node_times"])
        for sid in state["eligible"]:
            times.setdefault(sid, evaluated_at)
        update["node_times"] = times
        if evaluate_calls != len(state["eligible"]):
            update["fatal"] = edges.EVALUATE
            update["errors"] = {
                **errors,
                edges.EVALUATE: ErrorPayload(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"fan-out mismatch in graph node {edges.EVALUATE}",
                    retryable=True,
                    correlation_id=state["run_id"],
                    details=None,
                ),
            }
        update["agent_statuses"] = {
            **statuses,
            edges.EVALUATE: AgentRunStatus.OK.value,
        }
        update["evidence"] = evidence
        update["evaluations"] = evaluations
        if "errors" not in update:
            update["errors"] = errors
        update["conflicts"] = conflicts
        return update

    return evaluate


def make_gate_node(settings: Settings) -> NodeFn:
    """The sole path to TRADE-eligible levels (T0409): first setup to the gate."""

    async def gate(state: RunState) -> dict[str, Any]:
        try:
            candidates = sorted(
                sid for sid, evaluation in state["evaluations"].items() if evaluation.setup_found
            )
            evidence = {key: EvidenceStatus(value) for key, value in state["evidence"].items()}
            ctx = state["market_context"]
            if not candidates:
                verdict = GateVerdict(
                    passed=False,
                    reasons_for_rejection=["no setup from any eligible agent"],
                    conflicts=list(state["conflicts"]),
                )
            else:
                first = state["evaluations"][candidates[0]]
                assert first.candidate_levels is not None  # noqa: S101 — setup invariant
                direction = direction_from_levels(first.candidate_levels)
                risk_min = settings.min_risk_reward_ratio
                risk_max = settings.max_risk_percent_per_idea
                verdict = evaluate_gate(
                    evaluation=first,
                    direction=direction if direction is not None else Direction.UNKNOWN,
                    regime=ctx.regime,
                    quality_status=ctx.quality_status,
                    quality_flags=list(ctx.quality_flags),
                    evidence=evidence,
                    conflicts=list(state["conflicts"]),
                    min_risk_reward_ratio=(
                        Decimal(str(risk_min)) if risk_min is not None else None
                    ),
                    max_risk_percent_per_idea=(
                        Decimal(str(risk_max)) if risk_max is not None else None
                    ),
                    # No producer computes per-idea risk in Wave 1: None fails
                    # closed inside the gate ("idea risk unknown"), never guessed.
                    risk_percent_for_idea=None,
                )
            update = _stamp(state, edges.GATE, AgentRunStatus.OK)
            update["gate_verdict"] = verdict
            return update
        except Exception as exc:  # noqa: BLE001 — gate crash is fatal, never silent
            update = _stamp(state, edges.GATE, AgentRunStatus.ERROR)
            update["errors"] = {
                **state["errors"],
                edges.GATE: _sanitized_error(
                    edges.GATE, state["run_id"], exc, code=ErrorCode.INTERNAL_ERROR
                ),
            }
            update["fatal"] = edges.GATE
            return update

    return gate


def assemble_decision(state: RunState) -> DecisionRecord:
    """Terminal mapper: the ONLY constructor of run decisions (CEO-shaped slot).

    Precedence: barrier breach (or any fatal stage) → ``INSUFFICIENT_DATA``;
    passed gate → ``TRADE`` with gate-validated levels only; blocked gate
    with complete evidence → ``NO_TRADE``; blocked with incomplete evidence
    → ``INSUFFICIENT_DATA``. A non-TRADE record never carries levels
    (``DecisionRecord`` validator enforces it).
    """
    ctx = state["market_context"]
    verdict = state["gate_verdict"]
    complete_evidence = (
        bool(state["eligible"])
        and all(sid in state["evidence"] for sid in state["eligible"])
        and all(state["evidence"][sid] == EvidenceStatus.VALID.value for sid in state["eligible"])
    )
    base: dict[str, Any] = {
        "decision_id": f"dec_{state['run_id'][len('run_') :]}",
        "run_id": state["run_id"],
        "instrument_id": ctx.instrument_id,
        "timeframe": ctx.timeframe,
        "created_at": datetime.now(UTC),
        "data_as_of": ctx.now_utc,
        "evidence_refs": sorted(state["evidence"]),
        "agent_statuses": {
            node: AgentRunStatus(status) for node, status in state["agent_statuses"].items()
        },
        "conflicts": list(state["conflicts"]),
        "data_quality_status": ctx.quality_status,
        "limitations": [CEO_STUB_CAUSE],
        "manual_review_required": True,
    }
    if state["barrier_passed"] is True and verdict is not None and verdict.passed:
        levels = trade_eligible_levels(verdict)
        assert levels is not None  # noqa: S101 — passed verdict carries levels
        direction = direction_from_levels(levels)
        candidates = sorted(
            sid for sid, evaluation in state["evaluations"].items() if evaluation.setup_found
        )
        first = state["evaluations"][candidates[0]]
        return DecisionRecord(
            **base,
            decision=Decision.TRADE,
            direction=direction if direction is not None else Direction.UNKNOWN,
            strategy_id=first.strategy_id,
            strategy_version=first.strategy_version,
            entry=levels.entry,
            stop_loss=levels.stop_loss,
            take_profits=list(levels.take_profits),
            risk_reward=levels.risk_reward,
            thesis=(
                f"{first.strategy_id} {first.strategy_version} setup passed "
                f"the risk/validation gate"
            ),
        )
    if (
        state["barrier_passed"] is True
        and verdict is not None
        and not verdict.passed
        and complete_evidence
        and state["fatal"] is None
    ):
        return DecisionRecord(
            **base,
            decision=Decision.NO_TRADE,
            reasons_for_rejection=list(verdict.reasons_for_rejection),
            thesis="gate blocked a completely evidenced run: no qualified candidate",
        )
    reasons = list(state["barrier_reasons"])
    if state["fatal"] is not None:
        reasons.append(f"fatal stage failure: {state['fatal']}")
    if verdict is not None and not verdict.passed:
        reasons.extend(verdict.reasons_for_rejection)
    return DecisionRecord(
        **base,
        decision=Decision.INSUFFICIENT_DATA,
        reasons_for_rejection=reasons or ["run did not validate end to end"],
        thesis="run failed validation: insufficient data for a qualified decision",
    )


def make_finalize_node() -> NodeFn:
    """Terminal decision assembly (deterministic CEO slot; synthesis stubbed)."""

    async def finalize(state: RunState) -> dict[str, Any]:
        decision = assemble_decision(state)
        update = _stamp(state, edges.FINALIZE, AgentRunStatus.OK)
        update["decision"] = decision
        return update

    return finalize
