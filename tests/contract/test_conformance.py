"""Golden conformance suite (D-06): shared cases, parametrized evidence.

Every payload crosses the wire as JSON, so cases validate through
`model_validate_json` — the same path production payloads take.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from tests.contract.cases import (
    CONTRACT_ACCEPTED_CASES,
    CONTRACT_MODELS,
    CONTRACT_REJECTED_CASES,
    SCHEMA_MD_EXAMPLES,
)


def _as_json(document: dict[str, object]) -> str:
    return json.dumps(document)


@pytest.mark.parametrize(
    "contract,document,substitutions",
    SCHEMA_MD_EXAMPLES,
    ids=[name for name, _, _ in SCHEMA_MD_EXAMPLES],
)
def test_schema_md_example_validates(
    contract: str, document: dict[str, object], substitutions: dict[str, Any]
) -> None:
    merged = {**document, **substitutions}
    CONTRACT_MODELS[contract].model_validate_json(_as_json(merged))


@pytest.mark.parametrize(
    "contract", sorted(CONTRACT_ACCEPTED_CASES), ids=sorted(CONTRACT_ACCEPTED_CASES)
)
def test_accepted_case_validates(contract: str) -> None:
    CONTRACT_MODELS[contract].model_validate_json(_as_json(CONTRACT_ACCEPTED_CASES[contract]))


@pytest.mark.parametrize(
    "contract,reason,document",
    CONTRACT_REJECTED_CASES,
    ids=[f"{contract}-{reason}" for contract, reason, _ in CONTRACT_REJECTED_CASES],
)
def test_rejected_case_fails(contract: str, reason: str, document: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CONTRACT_MODELS[contract].model_validate_json(_as_json(document))


def test_every_contract_has_evidence() -> None:
    accepted = set(CONTRACT_ACCEPTED_CASES)
    rejected = {contract for contract, _, _ in CONTRACT_REJECTED_CASES}
    for contract in CONTRACT_MODELS:
        assert contract in accepted, f"{contract} has no accepted case"
        assert contract in rejected, f"{contract} has no rejected case"
