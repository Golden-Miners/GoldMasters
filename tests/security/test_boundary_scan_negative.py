"""Negative meta-tests: the boundary scan has teeth (01-02 Task 2).

Names are drawn at runtime from the helper's own sets, so the mechanism is
proven against every member and cannot rot when the sets grow. Fully
self-contained — no files written, nothing committed.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def _load_boundary() -> object:
    path = REPO / "tests" / "security" / "_boundary.py"
    spec = importlib.util.spec_from_file_location("gm_boundary_negative", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scan_detects_forbidden_call() -> None:
    boundary = _load_boundary()
    names = sorted(boundary.FORBIDDEN_CALL_NAMES)  # type: ignore[attr-defined]
    assert names, "forbidden set is empty — the scan guards nothing"
    name = names[0]
    tree = ast.parse(f"def f():\n    obj.{name}()\n")
    assert boundary.scan_forbidden(tree) == {name}  # type: ignore[attr-defined]


def test_scan_detects_forbidden_import() -> None:
    boundary = _load_boundary()
    roots = sorted(boundary.FORBIDDEN_IMPORT_ROOTS)  # type: ignore[attr-defined]
    assert roots, "import set is empty — the scan guards nothing"
    root = roots[0]
    tree = ast.parse(f"import {root}\n")
    assert root in boundary.scan_import_roots(tree)  # type: ignore[attr-defined]
