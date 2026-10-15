---
phase: "2"
slug: "market-data-and-provider-selection"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-15"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `uv run pytest`, config in `pyproject.toml [tool.pytest]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest <test-file> -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest <touched-test-file> -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01 T1 tracer slice | 02-01 | 1 | REQ-instrument-provider-selection / REQ-market-data-ingestion-validation | T-02-01..T-02-04 | bare initialize, no secrets, no substitution, TZ sanity | unit+contract | `uv sync --all-packages && uv run python -c "import goldmasters_contracts; print(goldmasters_contracts.CONTRACT_VERSION)" && uv run python packages/contracts/_export_schema.py && uv run pytest tests/contract/test_conformance.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01 T2 boundary rework | 02-01 | 1 | REQ-instrument-provider-selection | T-02-02 | path-scoped allowlist, symbol_select forbidden | unit | `uv run pytest tests/security/ -x -q` | ❌ W0 | ⬜ pending |
| 02-01 T3 health+endpoints | 02-01 | 1 | REQ-market-data-ingestion-validation | T-02-04 | probe never raises/leaks, C-09 mapping | integration | `uv run pytest tests/unit/test_mt5_tracer.py tests/integration/test_mt5_health_api.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02 T1 bar validation | 02-02 | 2 | REQ-market-data-ingestion-validation | T-02-05 | thresholds hashed, ±1s pinned | unit | `uv run pytest tests/unit/test_mt5_validation_bars.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02 T2 quote sessions | 02-02 | 2 | REQ-market-data-ingestion-validation | T-02-05 | session limits operator-tunable | unit | `uv run pytest tests/unit/test_mt5_validation_quotes.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02 T3 weekend classifier | 02-02 | 2 | REQ-market-data-ingestion-validation | T-02-06 | expected-gap vs missing-history | unit | `uv run pytest tests/unit/test_mt5_validation_weekend.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03 T1 health states | 02-03 | 2 | REQ-market-data-ingestion-validation | T-02-07 | distinct states, precedence, no leak | unit | `uv run pytest tests/unit/test_mt5_health_states.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03 T2 retry+mapping | 02-03 | 2 | REQ-market-data-ingestion-validation | T-02-07/T-02-08 | exact retry counts, redaction | unit | `uv run pytest tests/unit/test_mt5_retry_mapping.py -x -q` | ❌ W0 | ⬜ pending |
| 02-04 T1 precision | 02-04 | 3 | REQ-market-data-ingestion-validation | T-02-09 | append-only, interval audit | unit | `uv run pytest tests/unit/test_precision_population.py packages/contracts/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 02-04 T2 hash+contracts | 02-04 | 3 | REQ-instrument-provider-selection / REQ-market-data-ingestion-validation | T-02-10 | per-key hash proof, ID separation | contract+integration | `uv sync --all-packages && uv run python packages/contracts/_export_schema.py && uv run pytest tests/contract/test_mt5_market_contract.py tests/integration/test_mt5_health_api.py tests/unit/test_env_example.py -x -q` | ❌ W0 | ⬜ pending |
| 02-04 T3 live scaffold | 02-04 | 3 | REQ-market-data-ingestion-validation | — | live excluded from gate | manual+skip | `uv run pytest tests/integration/test_mt5_live.py -x -q` (must skip, not execute) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Wave 0 = plan 02-01 tasks (new `services/mt5_adapter` tree, FakeTerminal fixtures, boundary-scan rework) — must land before wave 2
- [ ] `pyproject.toml [tool.pytest]` — existing config covers discovery; add `live_mt5` marker registration (plan 02-04: `-m "not live_mt5"` default deselect)
- [ ] `uv sync --all-packages` — existing workspace install; `MetaTrader5` wheel stays OUT of manifests (Windows-only, MT5 host only, lazy gateway)

*Planner expands per-task rows once PLAN.md files exist.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live MT5 terminal read (XAUUSD H1 bars + tick) attaches to operator's logged-in terminal | REQ-market-data-ingestion-validation | Requires operator's live terminal on MT5 host; CI has no terminal | Operator runs marked `live_mt5` test on MT5 host with Market Watch XAUUSD enabled; record output as evidence (D-45) |
| Investor-login read-only assertion (`trade_allowed=False`) | REQ-instrument-provider-selection | Requires live account state | Same live run; assert health reports read-only, master password rejected (D-46) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
