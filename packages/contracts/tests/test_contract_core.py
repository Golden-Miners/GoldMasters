"""Core contract behaviours for the ``goldmasters-contracts`` package.

Covers the shared model config, the decimal wire form and the closed
vocabularies (plan 01-01 Task 2); the C-09 error payload and the agent envelope
are covered by the Task 3 cases at the bottom of this module.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from goldmasters_contracts._base import DECIMAL_PATTERN, ContractModel, PriceStr
from goldmasters_contracts.enums import QualityFlag, QualityStatus, Timeframe
from pydantic import ValidationError

#: The documented provider timeframe tokens transcribed into `enums.Timeframe`.
DOCUMENTED_TIMEFRAMES = frozenset(
    {
        "M1",
        "M2",
        "M3",
        "M4",
        "M5",
        "M6",
        "M10",
        "M12",
        "M15",
        "M20",
        "M30",
        "H1",
        "H2",
        "H3",
        "H4",
        "H6",
        "H8",
        "H12",
        "D1",
        "W1",
        "MN1",
    }
)


class _Named(ContractModel):
    name: str


class _Priced(ContractModel):
    price: PriceStr


class _Timed(ContractModel):
    timeframe: Timeframe


# --- Test 1: unknown extra field rejected (D-06/D-12) ---


def test_unknown_extra_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _Named.model_validate({"name": "trend_agent", "unexpected": "x"})


# --- Test 2: type coercion rejected (D-04) ---


def test_type_coercion_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _Named.model_validate({"name": 123})


# --- Test 3: instance immutable (D-04) ---


def test_instance_is_immutable() -> None:
    named = _Named(name="trend_agent")
    with pytest.raises(ValidationError):
        setattr(named, "name", "other")  # noqa: B010
    assert named.name == "trend_agent"


# --- Test 4: decimal wire form (D-11/D-19) ---


def test_decimal_string_is_accepted_and_round_trips() -> None:
    priced = _Priced.model_validate_json(json.dumps({"price": "2415.37"}))
    assert priced.price == Decimal("2415.37")
    assert priced.model_dump() == {"price": "2415.37"}
    assert priced.model_dump_json() == '{"price":"2415.37"}'


@pytest.mark.parametrize("raw", ["2.41537e3", "NaN", "Infinity", "+2415.37"])
def test_decimal_rejects_non_wire_strings(raw: str) -> None:
    with pytest.raises(ValidationError):
        _Priced.model_validate_json(json.dumps({"price": raw}))


def test_decimal_rejects_a_json_number() -> None:
    with pytest.raises(ValidationError):
        _Priced.model_validate_json(json.dumps({"price": 2415.37}))


def test_decimal_pattern_is_the_documented_form() -> None:
    assert DECIMAL_PATTERN == r"^-?\d+(\.\d+)?$"
    assert _Priced.model_json_schema(mode="serialization")["properties"]["price"] == {
        "type": "string",
        "pattern": DECIMAL_PATTERN,
        "title": "Price",
    }


# --- Test 5: canonical timeframe enum (D-13/D-16/D-28) ---


def test_timeframe_enum_matches_documented_members() -> None:
    assert frozenset(member.value for member in Timeframe) == DOCUMENTED_TIMEFRAMES


def test_timeframe_members_round_trip() -> None:
    timed = _Timed.model_validate_json(json.dumps({"timeframe": "M15"}))
    assert timed.timeframe is Timeframe.M15


@pytest.mark.parametrize("outside", ["1m", "PERIOD_M7", "M7", "H24"])
def test_provider_native_timeframe_outside_enum_is_rejected(outside: str) -> None:
    with pytest.raises(ValidationError):
        _Timed.model_validate_json(json.dumps({"timeframe": outside}))


# --- Test 6: quality vocabulary (D-20/D-22) ---


def test_quality_not_evaluated_is_its_own_member() -> None:
    assert QualityStatus.NOT_EVALUATED.value == "not_evaluated"
    others = {m for m in QualityStatus if m is not QualityStatus.NOT_EVALUATED}
    assert others
    assert all(member.value != "not_evaluated" for member in others)


def test_quality_flag_shares_the_status_vocabulary() -> None:
    assert {m.value for m in QualityFlag} == {m.value for m in QualityStatus}
