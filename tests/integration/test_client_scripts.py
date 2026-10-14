"""Static client-script tests (01-07 Task 2)."""

from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
WEB = REPO / "apps" / "web"


def test_dev_and_start_bind_loopback() -> None:
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    for script in ("dev", "start"):
        command = package["scripts"][script]
        assert "127.0.0.1" in command, script
        assert "0.0.0.0" not in command, script


def test_generated_types_are_gitignored() -> None:
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "apps/web/src/generated/" in gitignore


def test_api_client_uses_generated_types() -> None:
    source = (WEB / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    assert "../generated/" in source
    assert "import" in source.split("../generated/")[0].splitlines()[-1]
    assert "/health" in source
    assert 'cache: "no-store"' in source or "cache: 'no-store'" in source
    assert "Python" not in source
    assert "available: false" in source
    assert "API unreachable" in source


def test_page_renders_five_chain_fields() -> None:
    source = (WEB / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
    for field in (
        "health.status",
        "health.version",
        "health.contract_schema_version",
        "health.config_hash",
        "health.database.reachable",
    ):
        assert field in source, field
    assert "unavailable" in source.lower()
