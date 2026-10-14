"""News, sentiment and backtest contract tests (01-11 Tasks 1+3)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from goldmasters_contracts.backtest import BacktestRecord
from goldmasters_contracts.enums import EvidenceStatus, Timeframe
from goldmasters_contracts.news import NewsItem
from goldmasters_contracts.sentiment import SCORE_MAX, SCORE_MIN, SentimentRecord
from pydantic import ValidationError

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 1, 1, 1, tzinfo=UTC)

REPO = Path(__file__).resolve().parents[3]


def _news(**overrides: object) -> NewsItem:
    base: dict[str, object] = {
        "source_id": "reuters",
        "canonical_url": "https://example.com/gold-1",
        "title": "Gold steady",
        "published_at": T0,
        "retrieved_at": T1,
        "content_hash": "abc123",
        "source_attribution": "Example News",
        "access_method": "rss",
        "status": EvidenceStatus.VALID,
    }
    base.update(overrides)
    return NewsItem.model_validate(base)


def _sentiment(**overrides: object) -> SentimentRecord:
    base: dict[str, object] = {
        "instrument_id": "xauusd",
        "window_start": T0,
        "window_end": T1,
        "created_at": T1,
        "coverage_count": 3,
        "unique_source_count": 2,
        "duplicate_policy": "collapse-by-canonical-url",
    }
    base.update(overrides)
    return SentimentRecord.model_validate(base)


def _backtest(**overrides: object) -> BacktestRecord:
    base: dict[str, object] = {
        "backtest_run_id": "run_01890000-0000-7000-8000-000000000001",
        "strategy_id": "trend-breakout",
        "strategy_version": "1.0.0",
        "dataset_ref": "xauusd-h1-2025",
        "dataset_hash": "def456",
        "instrument_id": "xauusd",
        "timeframe": Timeframe.H1,
        "start": T0,
        "end": T1,
        "timezone": "Etc/UTC",
        "data_quality": EvidenceStatus.VALID,
        "parameter_hash": "p789",
        "assumptions": {
            "spread": "0.35",
            "commission": "0.00",
            "slippage": "0.10",
            "fill_model": "next-open",
        },
        "generated_at": T1,
        "code_version": "1.0.0",
        "status": EvidenceStatus.VALID,
    }
    base.update(overrides)
    return BacktestRecord.model_validate(base)


def test_news_accepts_and_rejects_mutations() -> None:
    _news()
    with pytest.raises(ValidationError):
        _news(title=None)
    with pytest.raises(ValidationError):
        _news(status="viral")
    with pytest.raises(ValidationError):
        _news(nonexistent_field="x")


def test_sentiment_score_bounds() -> None:
    _sentiment(score=SCORE_MIN, scoring_method="lexicon", scoring_method_version="1")
    _sentiment(score=SCORE_MAX, scoring_method="lexicon", scoring_method_version="1")
    with pytest.raises(ValidationError):
        _sentiment(
            score=SCORE_MAX + 0.1, scoring_method="lexicon", scoring_method_version="1"
        )
    with pytest.raises(ValidationError):
        _sentiment(score=0.5)


def test_backtest_accepts_and_rejects_price_form() -> None:
    _backtest()
    with pytest.raises(ValidationError):
        _backtest(dataset_ref=None)
    with pytest.raises(ValidationError):
        _backtest(
            assumptions={
                "spread": 0.35,
                "commission": "0.00",
                "slippage": "0.10",
                "fill_model": "next-open",
            }
        )


def test_unavailability_representable() -> None:
    item = _news(
        status=EvidenceStatus.UNAVAILABLE, content_hash=None, published_at=None
    )
    assert item.content_hash is None
    record = _sentiment(coverage_count=0, unique_source_count=0)
    assert record.score is None


def test_extra_fields_rejected_everywhere() -> None:
    for make in (_news, _sentiment, _backtest):
        with pytest.raises(ValidationError):
            make(extra="nope")


def _committed_documents() -> list[Path]:

    return sorted((REPO / "packages" / "contracts" / "schema").glob("*.json"))


def _load_exporter() -> object:
    import importlib.util

    path = REPO / "packages" / "contracts" / "_export_schema.py"
    spec = importlib.util.spec_from_file_location("goldmasters_export_schema", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enumeration_covers_barrel_and_documents() -> None:
    import goldmasters_contracts

    exporter = _load_exporter()
    contracts = exporter.CONTRACTS  # type: ignore[attr-defined]
    stems = sorted(stem for stem, _ in contracts)
    committed = sorted(p.stem for p in _committed_documents())
    assert stems == committed
    for _, attribute in contracts:
        assert hasattr(goldmasters_contracts, attribute), attribute


def test_export_is_deterministic(tmp_path: Path) -> None:
    exporter = _load_exporter()
    first = exporter.export_schema(tmp_path / "a")  # type: ignore[attr-defined]
    second = exporter.export_schema(tmp_path / "b")  # type: ignore[attr-defined]
    assert [p.name for p in first] == [p.name for p in second]
    for a, b in zip(first, second):
        raw_a = (tmp_path / "a" / a.name).read_bytes()
        raw_b = (tmp_path / "b" / b.name).read_bytes()
        assert raw_a == raw_b
        text = raw_a.decode("utf-8")
        assert "\r" not in text
        assert text.endswith("\n") and not text.endswith("\n\n")
        import json

        assert json.dumps(json.loads(text), sort_keys=True, indent=2) + "\n" == text


def test_wire_types_are_strings_not_number_unions() -> None:
    import json

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            node_t = node if isinstance(node, dict) else {}
            if "anyOf" in node_t:
                for branch in node_t["anyOf"]:
                    if branch.get("type") == "number":
                        assert path.startswith("sentiment.json/properties/score"), (
                            f"{path}: number union"
                        )
            if node_t.get("type") == "number":
                assert path.startswith("sentiment.json/properties/score"), (
                    f"{path}: number"
                )
            for key, value in node_t.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    for document in _committed_documents():
        walk(json.loads(document.read_text(encoding="utf-8")), document.name)


def test_envelope_still_matches_fresh_export() -> None:

    exporter = _load_exporter()
    fresh = exporter.canonicalise(  # type: ignore[attr-defined]
        __import__("goldmasters_contracts").Envelope.model_json_schema(
            mode="serialization"
        )
    )
    committed = (
        REPO / "packages" / "contracts" / "schema" / "envelope.json"
    ).read_text(encoding="utf-8")
    assert fresh == committed
