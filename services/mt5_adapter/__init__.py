"""Local MT5 read-only adapter (Phase 2; D-44/D-47).

Signals only: this tree attaches to the operator's already-running terminal,
reads bars/ticks/specs, and never changes terminal state or handles
credentials. The broker package is imported lazily inside
:mod:`services.mt5_adapter.terminal` only — enforced by the reworked
boundary scan (``tests/security/_boundary.py``).
"""
