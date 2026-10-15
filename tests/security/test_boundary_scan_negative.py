"""Negative meta-tests: the boundary scan has teeth (01-02 Task 2, 02-01 rework).

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


def test_gateway_import_allowed_only_at_gateway_path() -> None:
    """A broker-package import passes at terminal.py and fails anywhere else."""
    boundary = _load_boundary()
    gateway = boundary.ADAPTER_GATEWAY_PATH  # type: ignore[attr-defined]
    for root in sorted(boundary.ADAPTER_SCOPED_IMPORT_ROOTS):  # type: ignore[attr-defined]
        tree = ast.parse(f"import {root}\n")
        assert boundary.scan_adapter_imports(gateway, tree) == set()  # type: ignore[attr-defined]
        assert boundary.scan_adapter_imports("apps/api/src/goldmasters_api/market.py", tree) == {  # type: ignore[attr-defined]
            root
        }
        from_tree = ast.parse(f"from {root} import version\n")
        assert boundary.scan_adapter_imports("services/mt5_adapter/adapter.py", from_tree) == {  # type: ignore[attr-defined]
            root
        }


def test_scan_detects_forbidden_adapter_call() -> None:
    """Every adapter-banned name is reported over the adapter tree."""
    boundary = _load_boundary()
    names = sorted(boundary.FORBIDDEN_ADAPTER_CALLS)  # type: ignore[attr-defined]
    assert names, "adapter call set is empty — the scan guards nothing"
    for name in names:
        tree = ast.parse(f"def f(gateway):\n    gateway.{name}()\n")
        assert boundary.scan_adapter_calls(tree) == {name}  # type: ignore[attr-defined]
    clean = ast.parse("def f(gateway):\n    gateway.initialize()\n")
    assert boundary.scan_adapter_calls(clean) == set()  # type: ignore[attr-defined]


def test_global_scan_still_forbids_order_calls() -> None:
    """The rework keeps every order-capable call globally forbidden."""
    boundary = _load_boundary()
    assert "order_send" in set(boundary.FORBIDDEN_CALL_NAMES)  # type: ignore[attr-defined]
    tree = ast.parse("def f():\n    api.order_send(req)\n")
    assert boundary.scan_forbidden(tree) == {"order_send"}  # type: ignore[attr-defined]
