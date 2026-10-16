"""Shared builders for the Phase 4 graph test slice (FIXTURE-labelled only).

Test-only support: hermetic settings, agent-01 scope/numerics mirroring the
agent's own passing recipe, and deterministic run inputs. Fixtures never
leave ``tests/`` and are never surfaced as live conditions (Rules §9.7).
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest
from goldmasters_api.settings import Settings
from goldmasters_contracts import Timeframe, TrendRegime

from src.goldmasters.graph.builder import initial_state, run_to_decision
from src.goldmasters.graph.state import RunState
from tests.unit.agent_fixtures import bars_from_closes, make_ctx

DB = "postgresql+psycopg://goldmasters:secret@127.0.0.1:5432/goldmasters"

#: Agent-01 scope mirroring its own passing recipe (test_agent_01._params).
AGENT_01_SCOPE: dict[str, object] = {
    "strategy_agent_01_enabled": True,
    "strategy_agent_01_instruments": ["xauusd"],
    "strategy_agent_01_timeframes": [Timeframe.H1],
    "strategy_agent_01_regimes": [TrendRegime.UPTREND, TrendRegime.DOWNTREND],
    "strategy_agent_01_min_bars": 6,
}

#: Agent-01 numerics mirroring its own passing recipe (operator-spec values).
AGENT_01_NUMERICS: dict[str, object] = {
    "strategy_agent_01_fast_period": 3,
    "strategy_agent_01_slow_period": 5,
    "strategy_agent_01_htf_timeframe": "H4",
    "strategy_agent_01_adx_min": Decimal("0.1"),
    "strategy_agent_01_confirm_bars": 2,
}

#: Risk policy wide open except the uncomputed per-idea risk, so the gate's
#: only block is the documented Wave-1 "idea risk unknown" (no producer yet).
OPEN_RISK: dict[str, object] = {
    "max_risk_percent_per_idea": 100.0,
    "min_risk_reward_ratio": 0.01,
}

#: FIXTURE bars driving an agent-01 long setup (its own FIXTURE_UP vector).
FIXTURE_SETUP_CLOSES = ["100", "102", "104", "106", "108", "110", "112", "114"]

#: FIXTURE flat bars: no trend alignment, so no setup (chop fail).
FIXTURE_FLAT_CLOSES = ["100"] * 8


def apply_clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every GOLDMASTERS_ variable so each test controls its env fully."""
    for key in [k for k in os.environ if k.startswith("GOLDMASTERS_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GOLDMASTERS_DATABASE_URL", DB)
    monkeypatch.setenv("GOLDMASTERS_MT5_SERVER_TIMEZONE", "UTC")


def make_settings(**overrides: object) -> Settings:
    """Hermetic settings: required keys plus overrides (init beats env)."""
    base: dict[str, object] = {
        "database_url": DB,
        "mt5_server_timezone": "UTC",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def make_opening(settings: Settings, *, closes: list[str] | None = None) -> RunState:
    """Deterministic opening state: fresh run id, fixture bars, eligible ctx."""
    return initial_state(
        run_id=f"run_{uuid.uuid4()}",
        bars=bars_from_closes(closes or FIXTURE_SETUP_CLOSES),
        ctx=make_ctx(),
        settings=settings,
    )


async def run_closing(
    graph: object, opening: RunState, *, max_concurrency: int | None = None
) -> RunState:
    """Invoke one run and return the closing state (thread bound to run_id)."""
    return await run_to_decision(graph, opening, max_concurrency=max_concurrency)  # type: ignore[arg-type]
