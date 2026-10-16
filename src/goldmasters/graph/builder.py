"""Bounded deterministic graph: typed state, async nodes, explicit edges (D-4.1).

Wiring only — every number comes from Phase 3 code or ``GOLDMASTERS_GRAPH_*``
settings. Nodes are thin async wrappers: validate input contracts, call one
Phase 3 function, validate the output contract, return sanitized Schema §10
errors on failure (never a guess). Retry covers transient transport only;
contract ``ValidationError``, gate ``passed=False`` and ``NOT_APPLICABLE``
are routing signals, never retried (D-4.2).

Checkpointer is ``InMemorySaver`` with ``thread_id=run_id`` for this slice;
durable resume (``AsyncSqliteSaver``) arrives with the model runtime.
"""

from __future__ import annotations

import dataclasses
import importlib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
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
    QualityStatus,
    RunId,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, TimeoutPolicy
from pydantic import TypeAdapter

from goldmasters_api.settings import Settings, hash_effective_config
from src.goldmasters.graph import edges
from src.goldmasters.graph.edges import BARRIER, EVALUATE, FINALIZE, GATE, SELECT
from src.goldmasters.graph.state import RunState, compute_input_ref, utc_now_iso
from src.goldmasters.risk.gate import GateVerdict, evaluate_gate, trade_eligible_levels
from src.goldmasters.strategies.base import (
    MarketContext,
    StrategyEvaluation,
    eligible_agents,
)

__all__ = [
    "AGENT_MODULES",
    "build_graph",
    "direction_from_levels",
    "initial_state",
    "matrix_from_settings",
    "run_to_decision",
]

#: The ten approved strategy packages, one per operator-spec rule family.
#: Nodes call these modules — never each other, never re-implemented numbers.
AGENT_MODULES = tuple(f"src.goldmasters.strategies.agent_{n:02d}" for n in range(1, 11))

#: Scope fields shared by every AgentNNParams row; the rest are numerics
#: read from the matching ``GOLDMASTERS_STRATEGY_AGENT_<NN>_*`` settings keys.
_SCOPE_FIELDS = ("enabled", "instruments", "timeframes", "regimes", "min_bars")

_BAR_ADAPTER = TypeAdapter(list[MarketBar])
_RUN_ADAPTER = TypeAdapter(RunId)

#: CEO-shaped synthesis has no model runtime yet (T0004 open): the slot
#: exists, is validated, and returns unavailable-with-cause, never prose.
CEO_STUB_CAUSE = "ceo_synthesis unavailable: no model runtime (T0004 open)"


def _params_class(module_name: str) -> Any:
    """The single ``AgentNNParams`` dataclass of a strategy package."""
    module = importlib.import_module(module_name)
    for value in vars(module).values():
        if dataclasses.is_dataclass(value) and value.__name__.startswith("Agent"):
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
        importlib.import_module(module).eligibility(
            build_params(module, f"{n:02d}", settings)
        )
        for n, module in enumerate(AGENT_MODULES, start=1)
    ]


def code_versions() -> dict[str, str]:
    """strategy_id -> ``version@code_hash`` stamps for the run record."""
    stamps: dict[str, str] = {}
    for module_name in AGENT_MODULES:
        module = importlib.import_module(module_name)
        stamps[str(module.STRATEGY_ID)] = (
            f"{module.STRATEGY_VERSION}@{module.CODE_HASH}"
        )
    return stamps


def initial_state(
    *,
    run_id: str,
    bars: Sequence[MarketBar] | Sequence[Mapping[str, Any]],
    ctx: MarketContext | Mapping[str, Any],
    settings: Settings,
) -> RunState:
    """Assemble and validate the opening state (contract constructors first).

    Raises ``ValidationError`` on a non-``run_<uuid>`` id or malformed
    bars/context — caller errors, never run outcomes.
    """
    valid_run_id = str(_RUN_ADAPTER.validate_python(run_id))  # run_<uuid> binding
    valid_bars = _BAR_ADAPTER.validate_python(list(bars))
    valid_ctx = (
        ctx if isinstance(ctx, MarketContext) else MarketContext.model_validate(ctx)
    )
    return RunState(
        run_id=valid_run_id,
        input_ref=compute_input_ref(valid_bars, valid_ctx),
        config_hash=hash_effective_config(settings),
        code_versions=code_versions(),
        agent_statuses={},
        evidence={},
        conflicts=[],
        evaluations={},
        gate_verdict=None,
        barrier_passed=None,
        barrier_reasons=[],
        decision=None,
        errors={},
        fatal=None,
        eligible=[],
        bars=valid_bars,
        market_context=valid_ctx,
        started_at=datetime.now(UTC).isoformat(),
        node_times={},
    )


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


def _retry_policy(settings: Settings) -> RetryPolicy:
    """Transient transport only — validation and policy outcomes never retry."""
    return RetryPolicy(
        max_attempts=1 + settings.graph_node_max_retries,
        retry_on=(httpx.TimeoutException, httpx.ConnectError),
    )


def _timeout(settings: Settings) -> TimeoutPolicy:
    """Per-node wall-clock cap; async-only, so every node is ``async def``."""
    return TimeoutPolicy(run_timeout=settings.graph_node_timeout_seconds)


def build_graph(settings: Settings) -> Any:
    """Assemble the bounded deterministic graph (tracer slice: full chain)."""
    retry = _retry_policy(settings)
    timeout = _timeout(settings)
    builder: StateGraph[RunState] = StateGraph(RunState)

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
                    edges.INGEST, state["run_id"], exc,
                    code=ErrorCode.CONTRACT_VALIDATION_FAILED,
                ),
            }
            update["fatal"] = edges.INGEST
            return update
        update = _stamp(state, edges.INGEST, AgentRunStatus.OK)
        update["bars"] = bars
        update["market_context"] = ctx
        return update

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
        update["agent_statuses"] = statuses
        update["eligible"] = eligible_ids
        selected_at = utc_now_iso()
        times = dict(update["node_times"])
        for sid in verdicts:
            if verdicts[sid] != "eligible":
                times.setdefault(sid, selected_at)
        update["node_times"] = times
        return update

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
                statuses[sid] = _status_of(evaluation).value
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
        update["agent_statuses"] = statuses
        update["evidence"] = evidence
        update["evaluations"] = evaluations
        if "errors" not in update:
            update["errors"] = errors
        update["conflicts"] = conflicts
        return update

    async def gate(state: RunState) -> dict[str, Any]:
        try:
            candidates = sorted(
                sid
                for sid, evaluation in state["evaluations"].items()
                if evaluation.setup_found
            )
            evidence = {
                key: EvidenceStatus(value)
                for key, value in state["evidence"].items()
            }
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

    async def barrier(state: RunState) -> dict[str, Any]:
        reasons: list[str] = []
        verdict = state["gate_verdict"]
        if verdict is None:
            reasons.append("no gate verdict present")
        elif list(verdict.conflicts) != list(state["conflicts"]):
            reasons.append("conflicts not preserved verbatim through the gate")
        invalid = sorted(
            key
            for key, value in state["evidence"].items()
            if value != EvidenceStatus.VALID.value
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
        passed = not reasons
        update = _stamp(
            state, edges.BARRIER, AgentRunStatus.OK if passed else AgentRunStatus.ERROR
        )
        update["barrier_passed"] = passed
        update["barrier_reasons"] = reasons
        return update

    async def finalize(state: RunState) -> dict[str, Any]:
        decision = _assemble_decision(state)
        update = _stamp(state, edges.FINALIZE, AgentRunStatus.OK)
        update["decision"] = decision
        return update

    builder.add_node(edges.INGEST, ingest, retry_policy=retry, timeout=timeout)
    builder.add_node(edges.SELECT, select, retry_policy=retry, timeout=timeout)
    builder.add_node(edges.EVALUATE, evaluate, retry_policy=retry, timeout=timeout)
    builder.add_node(edges.GATE, gate, retry_policy=retry, timeout=timeout)
    builder.add_node(edges.BARRIER, barrier, retry_policy=retry, timeout=timeout)
    builder.add_node(edges.FINALIZE, finalize, retry_policy=retry, timeout=timeout)
    builder.add_edge(START, edges.INGEST)
    builder.add_conditional_edges(edges.INGEST, edges.route_after_ingest)
    builder.add_edge(edges.SELECT, edges.EVALUATE)
    builder.add_conditional_edges(edges.EVALUATE, edges.route_after_evaluate)
    builder.add_conditional_edges(edges.GATE, edges.route_after_gate)
    builder.add_edge(edges.BARRIER, edges.FINALIZE)
    builder.add_edge(edges.FINALIZE, END)
    return builder.compile(checkpointer=InMemorySaver())


def _assemble_decision(state: RunState) -> DecisionRecord:
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
        and all(
            state["evidence"][sid] == EvidenceStatus.VALID.value
            for sid in state["eligible"]
        )
    )
    base: dict[str, Any] = {
        "decision_id": f"dec_{state['run_id'][len('run_'):]}",
        "run_id": state["run_id"],
        "instrument_id": ctx.instrument_id,
        "timeframe": ctx.timeframe,
        "created_at": datetime.now(UTC),
        "data_as_of": ctx.now_utc,
        "evidence_refs": sorted(state["evidence"]),
        "agent_statuses": {
            node: AgentRunStatus(status)
            for node, status in state["agent_statuses"].items()
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
            sid
            for sid, evaluation in state["evaluations"].items()
            if evaluation.setup_found
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


async def run_to_decision(
    graph: Any,
    opening: RunState,
    *,
    max_concurrency: int | None = None,
) -> RunState:
    """Invoke one run bound to ``thread_id=run_id``; returns the closing state."""
    config: dict[str, Any] = {"configurable": {"thread_id": opening["run_id"]}}
    if max_concurrency is not None:
        config["max_concurrency"] = max_concurrency
    closing = await graph.ainvoke(opening, config)
    return RunState(**closing)
