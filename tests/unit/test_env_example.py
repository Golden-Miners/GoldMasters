"""Config document + .env.example coverage tests (01-10 Task 3)."""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from goldmasters_api.settings import Settings
from pydantic_settings import SettingsConfigDict

REPO = pathlib.Path(__file__).resolve().parents[2]
YAML_PATH = REPO / "config" / "goldmasters.yaml"
ENV_EXAMPLE_PATH = REPO / ".env.example"

REQUIRED_KEYS = {"database_url"}
SECRET_KEYS = {"provider_api_key"}


def _env_names() -> set[str]:
    return {f"GOLDMASTERS_{name.upper()}" for name in Settings.model_fields}


def _parse_env_example() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        entries[key.strip()] = value.strip()
    return entries


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in [k for k in os.environ if k.startswith("GOLDMASTERS_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(
        "GOLDMASTERS_DATABASE_URL",
        "postgresql+psycopg://goldmasters:t@127.0.0.1:5432/goldmasters",
    )


def test_env_example_covers_every_key() -> None:
    assert set(_parse_env_example()) == _env_names()


def test_env_example_holds_no_real_secret() -> None:
    entries = _parse_env_example()
    for key in SECRET_KEYS:
        env_name = f"GOLDMASTERS_{key.upper()}"
        assert entries[env_name] == "", f"{env_name} must stay empty"
    for key, value in entries.items():
        if "SECRET" in value.upper() or "CHANGE_ME" in value.upper():
            continue
        field = key.removeprefix("GOLDMASTERS_").lower()
        if field in SECRET_KEYS:
            assert value == ""


def test_committed_files_carry_no_real_secret() -> None:
    document = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    blob = json.dumps(document).lower()
    assert "api_key" not in blob
    assert "password" not in blob
    assert "secret" not in blob.replace("non-secret", "")
    entries = _parse_env_example()
    for key in SECRET_KEYS:
        assert entries[f"GOLDMASTERS_{key.upper()}"] == ""


def test_document_parses_with_non_secret_defaults_only() -> None:
    document = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    assert not (set(document) & REQUIRED_KEYS), "document must not supply required keys"
    assert not (set(document) & SECRET_KEYS), "document must not carry secrets"
    assert document["bind_host"] == "127.0.0.1"
    assert document["bind_port"] == 8000


def test_document_supplies_defaults_env_wins(
    clean_env: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from goldmasters_api.settings import Settings as SettingsModel

    copy = tmp_path / "goldmasters.yaml"
    copy.write_text(
        YAML_PATH.read_text(encoding="utf-8").replace("log_level: INFO", "log_level: DEBUG"),
        encoding="utf-8",
    )

    class DocumentSettings(SettingsModel):
        model_config = SettingsConfigDict(
            env_prefix="GOLDMASTERS_",
            env_file=".env",
            extra="forbid",
            frozen=True,
            yaml_file=str(copy),
        )

    assert DocumentSettings().log_level == "DEBUG"  # type: ignore[call-arg]
    monkeypatch.setenv("GOLDMASTERS_LOG_LEVEL", "WARNING")
    assert DocumentSettings().log_level == "WARNING"  # type: ignore[call-arg]


def test_document_keys_are_model_subset() -> None:
    document = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    assert set(document) <= set(Settings.model_fields)
