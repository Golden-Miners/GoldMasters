"""Contracts-package purity test (D-08).

The allowlist lives here, so broadening the contracts dependency surface is
a visible diff in a test rather than a quiet `pyproject.toml` change.
"""

from __future__ import annotations

import ast
import pathlib

ALLOWED_TOP_LEVEL = frozenset(
    {
        "pydantic",
        "typing",
        "decimal",
        "datetime",
        "enum",
        "uuid",
        "re",
        "json",
        "zoneinfo",
        "collections",
        "abc",
        "functools",
        "dataclasses",
        "__future__",
        "warnings",
        "types",
        "math",
        "goldmasters_contracts",
    }
)


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_no_forbidden_imports() -> None:
    root = pathlib.Path(__file__).parents[1] / "src"
    modules = sorted(root.rglob("*.py"))
    assert modules, "purity walk discovered no Python files"
    offenders: dict[str, list[str]] = {}
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = sorted(_imported_roots(tree) - ALLOWED_TOP_LEVEL)
        if bad:
            offenders[str(path)] = bad
    assert not offenders, f"purity violation: {offenders}"
