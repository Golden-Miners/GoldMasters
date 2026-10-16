"""Boundary scan: no forbidden calls/imports in the tree, deps on allowlist (01-02 Task 1).

Phase 2 rework: the MT5 package is allowlisted at exactly one path
(``services/mt5_adapter/terminal.py``) and reported anywhere else, while
``symbol_select``/``login`` are banned over the adapter tree. Order-capable
names stay globally forbidden.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import tomllib

REPO = pathlib.Path(__file__).resolve().parents[2]


def _load_boundary() -> object:
    path = REPO / "tests" / "security" / "_boundary.py"
    spec = importlib.util.spec_from_file_location("gm_boundary", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _relative_posix(path: pathlib.Path) -> str:
    return path.relative_to(REPO).as_posix()


def test_no_forbidden_call_in_source_tree() -> None:
    boundary = _load_boundary()
    failures: dict[str, set[str]] = {}
    for root_name in boundary.SCAN_ROOTS:  # type: ignore[attr-defined]
        root = REPO / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError, UnicodeDecodeError:
                continue
            hits = boundary.scan_forbidden(tree) | (  # type: ignore[attr-defined]
                boundary.scan_import_roots(tree)  # type: ignore[attr-defined]
                & set(boundary.FORBIDDEN_IMPORT_ROOTS)  # type: ignore[attr-defined]
            )
            rel = _relative_posix(path)
            hits |= boundary.scan_adapter_imports(rel, tree)  # type: ignore[attr-defined]
            if rel == boundary.ADAPTER_GATEWAY_PATH or rel.startswith(  # type: ignore[attr-defined]
                boundary.ADAPTER_TREE_PREFIX  # type: ignore[attr-defined]
            ):
                hits |= boundary.scan_adapter_calls(tree)  # type: ignore[attr-defined]
            if hits:
                failures[rel] = hits
    assert not failures, f"forbidden broker/order capability: {failures}"


def test_gateway_allowlist_permits_only_terminal() -> None:
    """The allowlist names exactly the lazy gateway, nothing else."""
    boundary = _load_boundary()
    assert boundary.ADAPTER_GATEWAY_PATH == "services/mt5_adapter/terminal.py"  # type: ignore[attr-defined]
    assert boundary.ADAPTER_TREE_PREFIX == "services/mt5_adapter/"  # type: ignore[attr-defined]
    assert set(boundary.ADAPTER_SCOPED_IMPORT_ROOTS) == {"MetaTrader5", "mt5"}  # type: ignore[attr-defined]
    assert set(boundary.FORBIDDEN_ADAPTER_CALLS) == {"symbol_select", "login"}  # type: ignore[attr-defined]
    assert "MetaTrader5" not in set(boundary.FORBIDDEN_IMPORT_ROOTS)  # type: ignore[attr-defined]
    assert "mt5" not in set(boundary.FORBIDDEN_IMPORT_ROOTS)  # type: ignore[attr-defined]
    gateway = REPO / "services" / "mt5_adapter" / "terminal.py"
    assert gateway.is_file(), "the allowlisted gateway module must exist"


ALLOWED_DEPENDENCIES: frozenset[str] = frozenset(
    {
        # Runtime (pinned stack, RESEARCH.md)
        "pydantic",
        "pydantic-settings",
        "fastapi",
        "uvicorn",
        "structlog",
        "opentelemetry-api",
        "opentelemetry-sdk",
        "pyyaml",
        "tzdata",
        "sqlalchemy",
        "alembic",
        "psycopg",
        "psycopg-binary",
        "httpx",
        "goldmasters-contracts",
        # Phase 4 D-4.4: orchestration runtime (04-01 GO probe on 3.14.7).
        "langgraph",
        # Phase 4 Wave 2 model runtime (04-03; 04-01 GO pins).
        "ollama",
        "langgraph-checkpoint-sqlite",
        # Dev tools
        "pytest",
        "pytest-cov",
        "time-machine",
        "mypy",
        "ruff",
        "hatchling",
        # Node side (plan 07; absent until then)
        "next",
        "react",
        "react-dom",
        "typescript",
        "json-schema-to-typescript",
        "@types/node",
        "concurrently",
        "wait-on",
    }
)

FORBIDDEN_DEPENDENCY_TERMS: frozenset[str] = frozenset(
    {
        "metatrader",
        "mt5",
        "oanda",
        "broker",
        "trade-exec",
        "order-exec",
    }
)


def _distribution_name(requirement: str) -> str:
    name = requirement.strip().split(";")[0]
    for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
        name = name.split(sep)[0]
    name = name.split("[")[0].strip()
    return name.lower().replace("_", "-")


def test_dependencies_match_allowlist() -> None:
    declared: set[str] = set()
    for manifest in [
        REPO / "pyproject.toml",
        *sorted(REPO.glob("*/pyproject.toml")),
        *sorted(REPO.glob("*/*/pyproject.toml")),
    ]:
        if not manifest.is_file():
            continue
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        project = data.get("project", {})
        for requirement in project.get("dependencies", []):
            declared.add(_distribution_name(requirement))
        for group in project.get("optional-dependencies", {}).values():
            for requirement in group:
                declared.add(_distribution_name(requirement))
        for group in data.get("dependency-groups", {}).values():
            for requirement in group:
                declared.add(_distribution_name(requirement))
    for package_json in sorted(REPO.glob("*/package.json")):
        data = json.loads(package_json.read_text(encoding="utf-8"))
        for section in ("dependencies", "devDependencies"):
            declared.update(str(k).lower() for k in data.get(section, {}))
    assert declared, "no dependencies found — the scan walked nothing"
    unknown = declared - {name.lower() for name in ALLOWED_DEPENDENCIES}
    assert not unknown, f"dependencies outside the allowlist: {sorted(unknown)}"
    for name in declared:
        for term in FORBIDDEN_DEPENDENCY_TERMS:
            assert term not in name, f"order-capable dependency: {name}"
