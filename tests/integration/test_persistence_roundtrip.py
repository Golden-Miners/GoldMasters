"""Persistence round-trip of every accepted conformance payload (01-06 Task 3)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import create_engine, text

from tests.contract.cases import CONTRACT_ACCEPTED_CASES, CONTRACT_MODELS

_CREATED_AT_KEYS = ("created_at", "retrieved_at", "generated_at", "recorded_at")


def _promoted(document: dict[str, Any]) -> dict[str, Any]:
    created_at = next((document[key] for key in _CREATED_AT_KEYS if key in document), None)
    return {
        "run_id": document.get("run_id"),
        "agent_name": document.get("agent_name"),
        "instrument_id": document.get("instrument_id"),
        "created_at": created_at,
        "status": document.get("status"),
    }


def _assert_no_floats(node: Any, path: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _assert_no_floats(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_no_floats(value, f"{path}[{index}]")
    else:
        assert not isinstance(node, float), f"{path} stored as JSON number"


def test_every_accepted_payload_roundtrips(migrated_database: str) -> None:
    assert set(CONTRACT_ACCEPTED_CASES) >= set(CONTRACT_MODELS), "a contract lacks an accepted case"
    engine = create_engine(migrated_database)
    try:
        for contract in sorted(CONTRACT_MODELS):
            model = CONTRACT_MODELS[contract]
            original = model.model_validate_json(json.dumps(CONTRACT_ACCEPTED_CASES[contract]))
            stored = original.model_dump(mode="json")
            promoted = _promoted(stored)
            row_id = str(uuid.uuid4())
            # created_at is NOT NULL with a server default: when the contract
            # carries no timestamp (e.g. the error payload), omit the column
            # so the insertion time stands as provenance instead of a NULL.
            columns = ["id", "document"]
            params: dict[str, Any] = {"id": row_id, "document": json.dumps(stored)}
            for key in ("run_id", "agent_name", "instrument_id", "created_at", "status"):
                if promoted[key] is not None:
                    columns.append(key)
                    params[key] = promoted[key]
            placeholders = ", ".join(f":{key}" for key in columns)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"INSERT INTO contract_document ({', '.join(columns)}) "
                        f"VALUES ({placeholders})"
                    ),
                    params,
                )
                row = (
                    connection.execute(
                        text(
                            "SELECT run_id, agent_name, instrument_id, "
                            "created_at, status, document "
                            "FROM contract_document WHERE id = :id"
                        ),
                        {"id": row_id},
                    )
                    .mappings()
                    .first()
                )
            assert row is not None
            assert row["instrument_id"] == promoted["instrument_id"]
            assert row["status"] == promoted["status"]
            assert row["created_at"] is not None
            document = row["document"]
            if isinstance(document, str):
                document = json.loads(document)
            _assert_no_floats(document, contract)
            revived = model.model_validate_json(json.dumps(document))
            assert revived == original
    finally:
        engine.dispose()
