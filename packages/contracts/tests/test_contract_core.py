"""Core contract behaviours for the ``goldmasters-contracts`` package.

Covers the shared model config, the decimal wire form and the closed
vocabularies (plan 01-01 Task 2); the C-09 error payload and the agent envelope
are covered by the Task 3 cases at the bottom of this module.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from goldmasters_contracts import CONTRACT_VERSION, Envelope
from goldmasters_contracts._base import DECIMAL_PATTERN, ContractModel, PriceStr
from goldmasters_contracts.enums import (
    AgentRunStatus,
    QualityFlag,
    QualityStatus,
    Timeframe,
)
from goldmasters_contracts.errors import RETRYABLE_CODES, ErrorCode, ErrorPayload
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


# --- Task 3 fixtures: the two documented example shapes ---

#: Schema.md §10 with a synthetic correlation id (no real identifier is invented).
C09_DOCUMENT: dict[str, object] = {
    "code": "CONTRACT_VALIDATION_FAILED",
    "message": "Payload failed contract validation.",
    "retryable": False,
    "correlation_id": "01890000-0000-7000-8000-000000000000",
    "details": None,
}

#: Schema.md §3 with synthetic identifiers and no market data.
ENVELOPE_DOCUMENT: dict[str, object] = {
    "schema_version": "1.0",
    "run_id": "run_01890000-0000-7000-8000-000000000001",
    "agent_name": "trend_agent",
    "agent_version": "1.0.0",
    "status": "ok",
    "created_at": "2026-01-01T00:00:00Z",
    "as_of": None,
    "input_refs": [],
    "evidence_refs": [],
    "limitations": [],
    "error": None,
    "result": {},
}

#: The codes plan 01-01 settles; later phases add theirs by minor bump (D-23).
PINNED_ERROR_CODES = frozenset(
    {
        "CONTRACT_VALIDATION_FAILED",
        "UNKNOWN_CONTRACT_MAJOR",
        "CONFIG_INVALID",
        "UNSUPPORTED_INSTRUMENT",
        "UNSUPPORTED_TIMEFRAME",
        "INTERNAL_ERROR",
    }
)


# --- Test 7: the C-09 error payload (Schema.md §10; D-12/D-23) ---


def test_error_payload_accepts_the_documented_document() -> None:
    payload = ErrorPayload.model_validate_json(json.dumps(C09_DOCUMENT))
    assert payload.code is ErrorCode.CONTRACT_VALIDATION_FAILED
    assert payload.retryable is False
    assert payload.details is None
    assert payload.model_dump_json() == json.dumps(C09_DOCUMENT, separators=(",", ":"))


def test_error_payload_rejects_an_unknown_extra_field() -> None:
    with pytest.raises(ValidationError):
        ErrorPayload.model_validate_json(
            json.dumps({**C09_DOCUMENT, "unexpected": "x"})
        )


def test_error_payload_rejects_a_missing_code() -> None:
    without_code = {k: v for k, v in C09_DOCUMENT.items() if k != "code"}
    with pytest.raises(ValidationError):
        ErrorPayload.model_validate_json(json.dumps(without_code))


def test_error_payload_rejects_a_non_boolean_retryable() -> None:
    with pytest.raises(ValidationError):
        ErrorPayload.model_validate_json(
            json.dumps({**C09_DOCUMENT, "retryable": "no"})
        )


# --- Test 8: the closed ErrorCode vocabulary (D-23) ---


def test_error_code_pins_the_settled_vocabulary() -> None:
    assert PINNED_ERROR_CODES <= {code.value for code in ErrorCode}
    assert all(isinstance(code.retryable, bool) for code in ErrorCode)


def test_retryable_is_per_code_not_a_constant() -> None:
    assert {code.retryable for code in ErrorCode} == {False, True}
    assert RETRYABLE_CODES == frozenset(code for code in ErrorCode if code.retryable)
    assert ErrorCode.INTERNAL_ERROR.retryable is True
    assert ErrorCode.CONTRACT_VALIDATION_FAILED.retryable is False


# --- Test 9: retryable comes from the code, never the caller (T-01-26) ---


def test_retryable_comes_from_the_code_not_the_caller() -> None:
    overridden = ErrorPayload.model_validate_json(
        json.dumps({**C09_DOCUMENT, "retryable": True})
    )
    assert overridden.retryable is False

    retryable = ErrorPayload.model_validate_json(
        json.dumps({**C09_DOCUMENT, "code": "INTERNAL_ERROR", "retryable": False})
    )
    assert retryable.retryable is True


def test_retryable_is_derived_when_the_document_omits_it() -> None:
    without_retryable = {k: v for k, v in C09_DOCUMENT.items() if k != "retryable"}
    payload = ErrorPayload.model_validate_json(json.dumps(without_retryable))
    assert payload.retryable is ErrorCode.CONTRACT_VALIDATION_FAILED.retryable


# --- Test 10: the agent envelope (Schema.md §3; D-06/D-12) ---


def test_envelope_accepts_the_documented_document() -> None:
    envelope = Envelope.model_validate_json(json.dumps(ENVELOPE_DOCUMENT))
    assert envelope.status is AgentRunStatus.OK
    assert envelope.schema_version == CONTRACT_VERSION
    assert envelope.error is None
    assert envelope.as_of is None
    assert envelope.model_dump_json() == json.dumps(
        ENVELOPE_DOCUMENT, separators=(",", ":")
    )


def test_envelope_rejects_an_unknown_extra_field() -> None:
    with pytest.raises(ValidationError):
        Envelope.model_validate_json(
            json.dumps({**ENVELOPE_DOCUMENT, "unexpected": "x"})
        )


# --- Test 11: the package barrel (D-06) ---


def test_barrel_reexports_every_module_surface() -> None:
    import goldmasters_contracts as contracts

    for name in (
        "CONTRACT_VERSION",
        "ContractModel",
        "PriceStr",
        "UtcDatetime",
        "IanaTimezone",
        "DECIMAL_PATTERN",
        "Decision",
        "AgentRunStatus",
        "EvidenceStatus",
        "Direction",
        "TrendRegime",
        "QualityStatus",
        "QualityFlag",
        "VolumeType",
        "Timeframe",
        "ErrorCode",
        "ErrorPayload",
        "RETRYABLE_CODES",
        "Envelope",
    ):
        assert name in contracts.__all__, name
        assert hasattr(contracts, name), name

    from goldmasters_contracts.envelope import Envelope as SubmoduleEnvelope

    assert contracts.Envelope is SubmoduleEnvelope
