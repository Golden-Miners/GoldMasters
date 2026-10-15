"""Signals-only boundary scan helpers (D-37, REQ-no-trade-execution).

The forbidden-name lists are the implementation: the positive scan asserts
their absence from the source tree, and the negative meta-test draws its
synthetic cases from these same sets so the mechanism cannot rot.

Phase 2 rework: ``MetaTrader5``/``mt5`` moved out of the blanket
``FORBIDDEN_IMPORT_ROOTS`` into a path-scoped rule — permitted only in the
lazy gateway ``services/mt5_adapter/terminal.py``, reported anywhere else.
``symbol_select``/``login`` are forbidden by name over the adapter tree
(AST cannot distinguish call arguments, so the names are banned entirely);
``order_send`` and friends stay globally forbidden.
"""

from __future__ import annotations

import ast
from pathlib import Path

__all__ = [
    "ADAPTER_GATEWAY_PATH",
    "ADAPTER_SCOPED_IMPORT_ROOTS",
    "ADAPTER_TREE_PREFIX",
    "FORBIDDEN_ADAPTER_CALLS",
    "FORBIDDEN_CALL_NAMES",
    "FORBIDDEN_IMPORT_ROOTS",
    "SCAN_ROOTS",
    "scan_adapter_calls",
    "scan_adapter_imports",
    "scan_forbidden",
    "scan_import_roots",
]

#: Broker/order mutating call names. Any occurrence in the source tree fails
#: the build — signals only, never execution.
FORBIDDEN_CALL_NAMES: frozenset[str] = frozenset(
    {
        "order_send",
        "order_modify",
        "order_close",
        "position_close",
        "place_order",
        "submit_order",
        "cancel_order",
        "close_order",
        "modify_order",
        "send_order",
    }
)

#: Module roots indicating a broker/trading SDK dependency. The MT5 package is
#: deliberately absent: it lives under the adapter-scoped rule below.
FORBIDDEN_IMPORT_ROOTS: frozenset[str] = frozenset(
    {
        "oanda",
        "ig_trading",
        "binance",
        "ccxt",
    }
)

#: Exact repo-relative path (forward slashes) of the lazy MT5 gateway: the
#: only module that may reference the broker package.
ADAPTER_GATEWAY_PATH = "services/mt5_adapter/terminal.py"

#: Repo-relative prefix of the adapter tree the call-name ban covers.
ADAPTER_TREE_PREFIX = "services/mt5_adapter/"

#: Broker-package roots permitted only at :data:`ADAPTER_GATEWAY_PATH`.
ADAPTER_SCOPED_IMPORT_ROOTS: frozenset[str] = frozenset({"MetaTrader5", "mt5"})

#: Terminal-state mutating names, banned over the adapter tree. ``login``
#: covers every credential-bearing attach form (bare ``initialize()`` only);
#: ``symbol_select`` mutates Market Watch, which the operator owns by hand.
FORBIDDEN_ADAPTER_CALLS: frozenset[str] = frozenset({"symbol_select", "login"})

#: Source roots the scan walks; missing paths are skipped.
SCAN_ROOTS: tuple[str, ...] = ("packages", "apps", "src", "services")


def scan_forbidden(tree: ast.AST) -> set[str]:
    """Return the forbidden call names invoked anywhere in `tree`."""
    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if isinstance(name, str) and name in FORBIDDEN_CALL_NAMES:
                hits.add(name)
    return hits


def scan_adapter_calls(tree: ast.AST) -> set[str]:
    """Return the adapter-banned call names invoked anywhere in `tree`."""
    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if isinstance(name, str) and name in FORBIDDEN_ADAPTER_CALLS:
                hits.add(name)
    return hits


def scan_import_roots(tree: ast.AST) -> set[str]:
    """Return the top-level import roots present anywhere in `tree`."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def scan_adapter_imports(relative_posix_path: str, tree: ast.AST) -> set[str]:
    """Return broker-package roots outside the gateway allowlist path."""
    if relative_posix_path == ADAPTER_GATEWAY_PATH:
        return set()
    return scan_import_roots(tree) & set(ADAPTER_SCOPED_IMPORT_ROOTS)


def scan_tree(root: Path) -> dict[str, set[str]]:
    """Scan every `*.py` under `root`; map path to its forbidden hits."""
    findings: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError, UnicodeDecodeError:
            continue
        hits = scan_forbidden(tree) | (scan_import_roots(tree) & set(FORBIDDEN_IMPORT_ROOTS))
        if hits:
            findings[str(path)] = hits
    return findings
