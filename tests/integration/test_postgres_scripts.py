"""Static contract tests for the postgres provisioning scripts (01-05 Task 1)."""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
PG = REPO / "scripts" / "postgres"


def _read(name: str) -> str:
    return (PG / name).read_text(encoding="utf-8")


def test_scripts_and_pin_exist() -> None:
    for name in ("provision.ps1", "init.ps1", "start.ps1", "stop.ps1"):
        assert (PG / name).is_file(), name
    version = (PG / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+", version), version


def test_version_comes_from_version_file() -> None:
    provision = _read("provision.ps1")
    assert "VERSION" in provision
    assert "1260609" in provision  # verified 18.6 ID lives in the map, not inline per version
    assert provision.count("fileid") <= 2


def test_init_uses_explicit_auth_and_pwfile() -> None:
    text = _read("init.ps1")
    assert "--auth=scram-sha-256" in text
    assert "--pwfile" in text
    assert "--auth=trust" not in text


def test_start_binds_loopback_only() -> None:
    text = _read("start.ps1")
    assert "127.0.0.1" in text
    assert "5432" in text
    assert "0.0.0.0" not in text


def test_nothing_machine_wide() -> None:
    for name in ("provision.ps1", "init.ps1", "start.ps1", "stop.ps1"):
        text = _read(name).lower()
        assert "program files" not in text, name
        assert "register-service" not in text.replace(" ", ""), name
        assert "sc.exe" not in text, name
