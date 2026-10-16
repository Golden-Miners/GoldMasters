# Deferred items — Phase 06 (journal, persistence, backtesting)

Out-of-scope discoveries left for their owners. Nothing here blocks 06-02:
all three of its tasks verify green on the files it touched.

## 2026-10-16 — Repo-wide `mypy --strict .` red before and after 06-02

- **What:** `mypy --strict src packages tests apps` reports 78 errors in 20 files
  (e.g. `tests/unit/test_ceo_contract.py`, `tests/integration/test_ollama_discovery.py`
  unused-ignores and arg-type errors); `mypy --strict .` additionally trips on
  vendored module-mapping noise under untracked scratch dirs (`agent/skills/...`).
- **Scope:** None of the 78 are in 06-02 files (`src/goldmasters/backtest/*`,
  `test_backtest_*`, `agent_fixtures.py` are strict-clean, verified). Pre-existing
  on master, untouched by this plan.
- **Owner:** Respective phase owners (05 for CEO/news/ollama); scratch-dir noise
  belongs to whoever owns those worktrees.
- **Note:** 06-02 fixed the one error in its path (`agent_fixtures.tick_size`,
  Rule 3) since the plan mandates the mypy gate.
