"""Static contract tests for the stack entry point (01-05 Task 3)."""

from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def _read() -> str:
    return (REPO / "scripts" / "stack").read_text(encoding="utf-8")


def test_stack_exists_and_is_executable() -> None:
    import subprocess

    path = REPO / "scripts" / "stack"
    assert path.is_file()
    indexed = subprocess.run(
        ["git", "ls-files", "-s", "scripts/stack"],
        capture_output=True,
        text=True,
        cwd=REPO,
    ).stdout
    if indexed.strip():
        assert indexed.startswith("100755"), indexed  # exec bit tracked in git
    else:  # untracked working tree (e.g. before first commit): needs a shebang
        assert path.read_text(encoding="utf-8").startswith("#!")


def test_stack_composes_loopback_legs() -> None:
    text = _read()
    assert "postgres/start.ps1" in text or "start.ps1" in text
    assert "--host 127.0.0.1" in text
    assert "0.0.0.0" not in text


def test_stack_has_no_container_or_service_dependency() -> None:
    text = _read().lower()
    assert "docker" not in text
    assert "new-service" not in text
    assert "sc.exe" not in text
