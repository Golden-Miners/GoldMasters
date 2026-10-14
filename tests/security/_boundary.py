"""Signals-only boundary scan helpers (D-37, REQ-no-trade-execution).

The forbidden-name lists are the implementation: the positive scan asserts
their absence from the source tree, and the negative meta-test draws its
synthetic cases from these same sets so the mechanism cannot rot.
"""

from __future__ import annotations

import ast
from pathlib import Path

__all__ = [
    "FORBIDDEN_CALL_NAMES",
    "FORBIDDEN_IMPORT_ROOTS",
    "SCAN_ROOTS",
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

#: Module roots indicating a broker/trading SDK dependency.
FORBIDDEN_IMPORT_ROOTS: frozenset[str] = frozenset(
    {
        "MetaTrader5",
        "mt5",
        "oanda",
        "ig_trading",
        "binance",
        "ccxt",
    }
)

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


def scan_tree(root: Path) -> dict[str, set[str]]:
    """Scan every `*.py` under `root`; map path to its forbidden hits."""
    findings: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        hits = scan_forbidden(tree) | (scan_import_roots(tree) & set(FORBIDDEN_IMPORT_ROOTS))
        if hits:
            findings[str(path)] = hits
    return findings
