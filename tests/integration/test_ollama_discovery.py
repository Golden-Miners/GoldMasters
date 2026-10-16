"""Ollama discovery + health: live-or-skip (T0004 open), outage fail-closed.

Without a server the live test skips with reason; deterministic paths use a
stub transport returning the real ollama response types (test-only, never
surfaced as live conditions per Rules §9.7). An unreachable server yields
sanitized errors — never a model id, so no path can reach TRADE unqualified.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

import pytest
from goldmasters_contracts import ErrorCode
from pydantic import ValidationError

from tests.unit.graph_fixtures import apply_clean_env, make_settings

if TYPE_CHECKING:
    from ollama import ListResponse

#: Loopback discard port: refused immediately, no blackhole wait.
CLOSED_PORT_HOST = "http://127.0.0.1:9"


@pytest.fixture
def run_id() -> str:
    return f"run_{uuid.uuid4()}"


class _StubList:
    """Test-only transport stub returning real ollama response types."""

    def __init__(
        self,
        response: ListResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.list_calls = 0

    async def list(self) -> ListResponse:
        self.list_calls += 1
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _live_models() -> ListResponse:
    from ollama import ListResponse

    return ListResponse(
        models=[
            ListResponse.Model(model="live-model", digest="sha256:live"),
            ListResponse.Model(model="other-model", digest="sha256:other"),
        ]
    )


async def _probe_reachable(host: str) -> bool:
    """Fast loopback probe: True only when a server answers list()."""
    from ollama import AsyncClient

    try:
        await AsyncClient(host=host, timeout=2).list()
    except Exception:  # noqa: BLE001 — reachability probe, fail closed to skip
        return False
    return True


def test_discovery_live_or_skip(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    """Tracer verify: discovery + health against a live server, skip without one."""
    from src.goldmasters.graph import runtime
    from src.goldmasters.graph.runtime import check_health, discover, run_model_record

    apply_clean_env(monkeypatch)
    settings = make_settings()
    if not asyncio.run(_probe_reachable(settings.ollama_host)):
        pytest.skip("no Ollama server (T0004 open) — live discovery unverified")
    client = runtime.build_client(settings)
    discovery = asyncio.run(
        discover(settings, client, run_id=run_id, node="ollama_discovery")
    )
    assert discovery.reachable and discovery.error is None and discovery.attempts >= 1
    health = check_health(settings, discovery)
    assert health.reachable
    # No assumed name: unset model is never "present", even when reachable.
    assert settings.ollama_model is None
    assert not health.present
    record = run_model_record(settings, discovery, health)
    assert record["reachable"] is True
    assert record["model_present"] is False
    assert record["available_models"] == sorted(record["available_models"])


def test_discovery_outage_fails_closed(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    """Server unreachable: bounded retries, then sanitized error, never a model."""
    from src.goldmasters.graph import runtime
    from src.goldmasters.graph.runtime import (
        check_health,
        discover,
        resolve_model,
        run_model_record,
    )

    apply_clean_env(monkeypatch)
    settings = make_settings(ollama_host=CLOSED_PORT_HOST, graph_node_max_retries=1)
    discovery = asyncio.run(
        discover(
            settings, runtime.build_client(settings), run_id=run_id, node="ollama_discovery"
        )
    )
    assert not discovery.reachable
    assert discovery.models == ()
    assert discovery.attempts == 2  # first try + the one locked retry
    assert discovery.error is not None
    assert discovery.error.code == ErrorCode.INTERNAL_ERROR
    assert discovery.error.correlation_id == run_id
    resolved = resolve_model(settings, discovery, run_id=run_id, node="ollama_discovery")
    assert not isinstance(resolved, str)  # no model id: callers record INSUFFICIENT_DATA
    assert resolved.code == ErrorCode.INTERNAL_ERROR
    record = run_model_record(settings, discovery, check_health(settings, discovery))
    assert record["reachable"] is False and record["model_present"] is False


def test_generate_outage_returns_error_never_text(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    """Outage on the chat path: (None, ErrorPayload) — raw text never escapes."""
    from src.goldmasters.agents.parse import AnalystNote
    from src.goldmasters.graph import runtime
    from src.goldmasters.graph.runtime import generate

    apply_clean_env(monkeypatch)
    settings = make_settings(ollama_host=CLOSED_PORT_HOST, graph_node_max_retries=0)
    content, error = asyncio.run(
        generate(
            settings,
            runtime.build_client(settings),
            model="any-model",
            messages=[{"role": "user", "content": "summarize"}],
            response_model=AnalystNote,
            run_id=run_id,
            node="market_analyst",
        )
    )
    assert content is None
    assert error is not None and error.code == ErrorCode.INTERNAL_ERROR


def test_discovery_stub_lists_measured_inventory(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    """Deterministic discovery: inventory is whatever the server reports."""
    from src.goldmasters.graph.runtime import (
        check_health,
        discover,
        resolve_model,
        run_model_record,
    )

    apply_clean_env(monkeypatch)
    settings = make_settings(ollama_model="live-model")
    discovery = asyncio.run(
        discover(
            settings,
            _StubList(response=_live_models()),  # type: ignore[arg-type]
            run_id=run_id,
            node="ollama_discovery",
        )
    )
    assert discovery.reachable and discovery.attempts == 1 and discovery.error is None
    health = check_health(settings, discovery)
    assert health.present and health.expected == "live-model"
    assert resolve_model(settings, discovery, run_id=run_id, node="x") == "live-model"
    record = run_model_record(settings, discovery, health)
    assert record["available_models"] == ["live-model", "other-model"]
    assert record["model_digest"] == "sha256:live"

    missing = make_settings(ollama_model="not-installed")
    absent = check_health(missing, discovery)
    assert not absent.present
    resolved = resolve_model(missing, discovery, run_id=run_id, node="x")
    assert not isinstance(resolved, str)


def test_unset_model_never_matches(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> None:
    """No model-name default: None expected never resolves, even when reachable."""
    from src.goldmasters.graph.runtime import check_health, discover, resolve_model

    apply_clean_env(monkeypatch)
    settings = make_settings()
    assert settings.ollama_model is None
    discovery = asyncio.run(
        discover(
            settings,
            _StubList(response=_live_models()),  # type: ignore[arg-type]
            run_id=run_id,
            node="ollama_discovery",
        )
    )
    assert not check_health(settings, discovery).present
    assert not isinstance(
        resolve_model(settings, discovery, run_id=run_id, node="x"), str
    )


def test_public_host_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-04-06: only loopback endpoints start; a public URL names the key."""
    from goldmasters_api.settings import Settings

    apply_clean_env(monkeypatch)
    with pytest.raises(ValidationError, match="ollama_host"):
        Settings(database_url="x", mt5_server_timezone="UTC", ollama_host="https://models.example.com:11434")  # type: ignore[call-arg]
    with pytest.raises(ValidationError, match="ollama_host"):
        Settings(database_url="x", mt5_server_timezone="UTC", ollama_host="notaurl")  # type: ignore[call-arg]
    for host in ("http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434"):
        assert (
            Settings(database_url="x", mt5_server_timezone="UTC", ollama_host=host).ollama_host  # type: ignore[call-arg]
            == host
        )


def test_chat_response_shape_assumed_by_generate() -> None:
    """Pin the transport contract the stub-based tests rely on."""
    from ollama import ChatResponse

    response = ChatResponse(message={"role": "assistant", "content": "{}"})
    assert response.message.content == "{}"
