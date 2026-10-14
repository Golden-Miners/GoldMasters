"""Tests for version acceptance and prefix-bound identifiers (plan 01-03 Task 1).

Covers the five behaviours specified in the plan:
1. parse_contract_version accepts "1.0", "1.7", "1.0.3" and exposes major=1
2. parse_contract_version rejects "2.0", "", "", "v1", "1", "1.x"
3. Envelope accepts schema_version="1.4" and rejects "3.0"
4. run_id field accepts run_-prefixed UUID and rejects dec_-prefixed
5. Correct prefix with malformed UUID body is rejected; validation uses stdlib uuid only
"""

from __future__ import annotations

import json

import pytest
from goldmasters_contracts import Envelope, SchemaVersionStr, parse_contract_version
from goldmasters_contracts.ids import DecId, IdPrefix, ProviderId, RunId
from goldmasters_contracts.versions import CONTRACT_VERSION_MAJOR_SUPPORTED, ContractVersion
from pydantic import ValidationError

# A valid UUIDv7-like string for testing (stdlib uuid accepts any version)
VALID_UUID = "01890000-0000-7000-8000-000000000001"
VALID_RUN_ID = f"run_{VALID_UUID}"
VALID_DEC_ID = f"dec_{VALID_UUID}"

# Minimal valid envelope data for testing
BASE_ENVELOPE_JSON = json.dumps(
    {
        "run_id": VALID_RUN_ID,
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
)


# --- Test 1: parse_contract_version accepts valid 1.x versions ---


def test_parse_contract_version_accepts_1_0() -> None:
    version = parse_contract_version("1.0")
    assert isinstance(version, ContractVersion)
    assert version.major == 1
    assert version.minor == 0
    assert version.patch is None


def test_parse_contract_version_accepts_1_7() -> None:
    version = parse_contract_version("1.7")
    assert version.major == 1
    assert version.minor == 7
    assert version.patch is None


def test_parse_contract_version_accepts_1_0_3() -> None:
    version = parse_contract_version("1.0.3")
    assert version.major == 1
    assert version.minor == 0
    assert version.patch == 3


def test_parse_contract_version_exposes_major_as_1() -> None:
    for raw in ("1.0", "1.7", "1.0.3", "1.99", "1.0.0"):
        version = parse_contract_version(raw)
        assert version.major == CONTRACT_VERSION_MAJOR_SUPPORTED


# --- Test 2: parse_contract_version rejects invalid versions ---


@pytest.mark.parametrize(
    "raw", ["2.0", "", "v1", "1", "1.x", "0.1", "1.0.0.0", "1.0.", ".1", "1..0"]
)
def test_parse_contract_version_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_contract_version(raw)


def test_parse_contract_version_rejects_unknown_major() -> None:
    with pytest.raises(ValueError, match="unsupported major version 2"):
        parse_contract_version("2.0")


def test_parse_contract_version_rejects_v_prefix() -> None:
    with pytest.raises(ValueError, match="v.*prefix"):
        parse_contract_version("v1.0")


def test_parse_contract_version_rejects_empty() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_contract_version("")


def test_parse_contract_version_rejects_unparseable() -> None:
    for raw in ("v1", "1", "1.x", "not-a-version"):
        with pytest.raises(ValueError):
            parse_contract_version(raw)


# --- Test 3: Envelope accepts schema_version="1.4" and rejects "3.0" ---


def test_envelope_accepts_schema_version_1_4() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.4"
    envelope = Envelope.model_validate_json(json.dumps(data))
    assert envelope.schema_version == "1.4"


def test_envelope_accepts_schema_version_1_0() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    envelope = Envelope.model_validate_json(json.dumps(data))
    assert envelope.schema_version == "1.0"


def test_envelope_rejects_schema_version_3_0() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "3.0"
    with pytest.raises(ValidationError, match="unsupported major version 3"):
        Envelope.model_validate_json(json.dumps(data))


def test_envelope_rejects_schema_version_missing() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = ""  # Explicit empty to trigger the validator
    with pytest.raises(ValidationError, match="missing"):
        Envelope.model_validate_json(json.dumps(data))


def test_envelope_rejects_schema_version_v_prefix() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "v1.0"
    with pytest.raises(ValidationError, match="v.*prefix"):
        Envelope.model_validate_json(json.dumps(data))


def test_envelope_rejects_schema_version_unparseable() -> None:
    for raw in ("1", "1.x", "not-a-version"):
        data = json.loads(BASE_ENVELOPE_JSON)
        data["schema_version"] = raw
        with pytest.raises(ValidationError):
            Envelope.model_validate_json(json.dumps(data))


# --- Test 4: run_id accepts run_-prefixed UUID and rejects dec_-prefixed ---


def test_run_id_accepts_run_prefixed_uuid() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    envelope = Envelope.model_validate_json(json.dumps(data))
    assert envelope.run_id == VALID_RUN_ID


def test_run_id_rejects_dec_prefixed_uuid() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = VALID_DEC_ID
    with pytest.raises(ValidationError, match="run_id must start with prefix 'run_'"):
        Envelope.model_validate_json(json.dumps(data))


def test_run_id_rejects_agent_prefixed_uuid() -> None:
    agent_id = f"agent_{VALID_UUID}"
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = agent_id
    with pytest.raises(ValidationError, match="run_id must start with prefix 'run_'"):
        Envelope.model_validate_json(json.dumps(data))


def test_run_id_rejects_no_prefix() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = VALID_UUID
    with pytest.raises(ValidationError, match="run_id must start with prefix 'run_'"):
        Envelope.model_validate_json(json.dumps(data))


def test_run_id_rejects_wrong_prefix_case() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = f"RUN_{VALID_UUID}"
    with pytest.raises(ValidationError, match="run_id must start with prefix 'run_'"):
        Envelope.model_validate_json(json.dumps(data))


# --- Test 5: Correct prefix with malformed UUID body is rejected ---


def test_run_id_rejects_malformed_uuid() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = "run_not-a-uuid"
    with pytest.raises(ValidationError, match="malformed UUID body"):
        Envelope.model_validate_json(json.dumps(data))


def test_run_id_rejects_short_uuid() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = "run_123"
    with pytest.raises(ValidationError, match="malformed UUID body"):
        Envelope.model_validate_json(json.dumps(data))


def test_run_id_rejects_uuid_with_wrong_format() -> None:
    data = json.loads(BASE_ENVELOPE_JSON)
    data["schema_version"] = "1.0"
    data["run_id"] = "run_018900000000700080000000000000012"  # 33 chars - too long
    with pytest.raises(ValidationError, match="malformed UUID body"):
        Envelope.model_validate_json(json.dumps(data))


# --- Additional tests for IdPrefix, ProviderId, and annotated types ---


def test_id_prefix_enum_has_required_members() -> None:
    assert IdPrefix.RUN.value == "run_"
    assert IdPrefix.DEC.value == "dec_"
    assert IdPrefix.AGENT.value == "agent_"


def test_provider_id_accepts_valid_snake_case() -> None:
    # ProviderId is an annotated type; test via a model that uses it
    from pydantic import BaseModel

    class _ProviderModel(BaseModel):
        provider_id: ProviderId

    for valid in ("mt5", "alpha_vantage", "provider_1", "x", "a_b_c"):
        model = _ProviderModel.model_validate({"provider_id": valid})
        assert model.provider_id == valid


def test_provider_id_rejects_invalid_patterns() -> None:
    from pydantic import BaseModel

    class _ProviderModel(BaseModel):
        provider_id: ProviderId

    for invalid in (
        "MT5",
        "Alpha-Vantage",
        "provider 1",
        "provider@name",
        "",
        "123",
        "_provider",
        "provider_",
    ):
        with pytest.raises(ValidationError):
            _ProviderModel.model_validate({"provider_id": invalid})


def test_prefixed_id_factory_creates_distinct_types() -> None:
    # The factory returns distinct annotated types for each prefix
    assert RunId is not DecId
    from goldmasters_contracts.ids import AgentId

    assert RunId is not AgentId
    assert DecId is not AgentId


def test_dec_id_accepts_dec_prefixed_uuid() -> None:
    from pydantic import BaseModel

    class _DecModel(BaseModel):
        dec_id: DecId

    model = _DecModel.model_validate({"dec_id": VALID_DEC_ID})
    assert model.dec_id == VALID_DEC_ID


def test_dec_id_rejects_run_prefixed_uuid() -> None:
    from pydantic import BaseModel

    class _DecModel(BaseModel):
        dec_id: DecId

    with pytest.raises(ValidationError, match="dec_id must start with prefix 'dec_'"):
        _DecModel.model_validate({"dec_id": VALID_RUN_ID})


def test_schema_version_str_annotated_type_works() -> None:
    """Test that SchemaVersionStr can be used as a field type."""
    from pydantic import BaseModel

    class _VersionedModel(BaseModel):
        schema_version: SchemaVersionStr

    model = _VersionedModel.model_validate({"schema_version": "1.4"})
    assert model.schema_version == "1.4"

    with pytest.raises(ValidationError):
        _VersionedModel.model_validate({"schema_version": "2.0"})


def test_validation_uses_stdlib_uuid_only() -> None:
    """Verify that UUID validation uses only stdlib uuid (no third-party)."""
    # This is implicitly tested by the malformed UUID rejection tests above.
    # The implementation uses uuid.UUID() from the standard library.
    import inspect

    import goldmasters_contracts.ids as ids_module

    source = inspect.getsource(ids_module)
    assert "uuid.UUID" in source
    assert "import uuid" in source or "from uuid import" in source
