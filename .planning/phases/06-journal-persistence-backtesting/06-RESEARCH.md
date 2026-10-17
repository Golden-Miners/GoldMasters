# Phase 6: Journal, Persistence and Backtesting — Research

**Researched:** 2026-10-16
**Domain:** Immutable decision journal + append-only outcomes on existing PostgreSQL/JSONB persistence; deterministic, cost-aware backtesting over 10 versioned strategies
**Confidence:** HIGH (contracts, migration, graph boundary, and strategy seam all read from source this session)

## Summary

Phase 6 has two halves that share one persistence foundation. The journal half persists `DecisionRecord` snapshots as immutable rows and appends outcome observations without mutating the original — the `JournalEntry` contract already enforces this shape (frozen model, binding validators, `supersedes`+`reason` corrections). The backtest half runs the 10 versioned strategy packages' `evaluate(bars, ctx)` over declared historical datasets with explicit fill/cost assumptions, enforced in-sample/validation/out-of-sample splits, and deterministic Decimal metrics cross-checked against hand-verifiable cases.

The physical persistence pattern is locked: validated JSONB document plus promoted columns (D-07), hand-written Alembic migrations with working downgrades, throwaway per-run test databases. Phase 6 adds migrations (0002+), never reinterprets `0001_contract_document`. The Phase 4 minimal run log boundary (`MINIMAL_LOG_KEYS`) pins exactly what Phase 4 owns — outcomes and journal belong to Phase 6, so there is no overlap to negotiate. No new external packages are needed: everything builds on the existing contracts package, `risk.levels`/`risk.gate` math, and the pinned `alembic`/`SQLAlchemy` stack.

**Primary recommendation:** Add `0002_journal_outcome` and `0003_backtest` migrations following the 0001 pattern; implement outcome-append and backtest-runner as thin deterministic modules reusing `JournalEntry`/`BacktestRecord` validators, `build_candidate_levels`/`compute_risk_reward` math, and the eligibility/gate seam — with leakage, timestamp-alignment, cost-application, and split-enforcement tests that fail when an assumption is violated.

## User Constraints

No CONTEXT.md discussion has been held for Phase 6 (no `05`-style CONTEXT file exists in `.planning/phases/`; only phases 01 and 05 have one). The governing constraints therefore come from the locked upstream sources below, treated as non-negotiable:

- **ROADMAP.md Phase 6 success criteria (5 items, verbatim §139–149):** (1) every decision persisted as immutable snapshot with evidence refs, outcomes appended without mutating the original, surviving restart; (2) every reported backtest carries run+dataset ref, date range, timezone, timeframe, symbol mapping, strategy version, parameter set, spread/commission/slippage assumptions, fill model; (3) in-sample separated from validation/out-of-sample, missing data and excluded periods reported not silently dropped; (4) metrics computed by deterministic code, cross-checked against hand-verifiable cases, no LLM prose introduces or recalculates an authoritative metric; (5) leakage, timestamp alignment, cost application, split enforcement covered by tests that fail when an assumption is violated.
- **Rules.md R-01:** never invent market/news/sentiment/backtest data in production paths; missing = `unknown`/`unavailable` [VERIFIED: Rules.md:7]. **Rules R-03/R-05:** LLMs never authoritatively calculate prices, indicators, risk/reward, backtest metrics, or levels — deterministic code only [VERIFIED: Rules.md:30].
- **Schema.md §6 line 166:** decision record immutable; corrections create a superseding record with a reason [VERIFIED: Schema.md:166]. **Schema.md §9:** metrics calculated in deterministic code; no report without run+dataset ref [VERIFIED: Schema.md:279].
- **REQ-journal-and-backtesting acceptance** (REQUIREMENTS.md:37-38): immutable snapshots, append-only outcomes, full assumption declaration, IS/VS/OOS separation, code-computed metrics, no metric without assumptions + sample period.
- **Operator-owned (Memory.md open decision, unchanged):** PostgreSQL deployment/backup/retention policy — Phase 6 must not invent a retention or backup policy; backup/rollback testing belongs to Phase 8 (T0806).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Journal/outcome persistence | API / Backend | Database / Storage | Validated-contract writes + append-only enforcement live in backend code; PostgreSQL stores them |
| Backtest runner + metrics | API / Backend | — | Deterministic Decimal computation over closed bars; no frontend, no model involvement |
| Dataset manifest + provenance | API / Backend | Database / Storage | Manifest is a validated record; bar data referenced by hash/ref, per Schema §12 open item on persist-vs-reference |
| Traceability display of journal/backtest completeness | API / Backend (log line) | — | Phase 5 pattern: `log_traceability` emits an operator-visible log line; console surface is Phase 7 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Existing `goldmasters_contracts` (`journal.py`, `backtest.py`, `decision.py`, `_base.py`) | repo-pinned | Journal/backtest/decision validation | Frozen (`strict`+`extra="forbid"`+`frozen=True`) validators already encode every Phase 6 invariant [VERIFIED: packages/contracts/src/goldmasters_contracts/_base.py:98-105] |
| Existing Alembic + SQLAlchemy stack (`apps/api/migrations/`) | as pinned in `apps/api/pyproject.toml` | 0002+ migrations | Reuse the proven 0001 pattern; no new migration tooling |
| Existing `src/goldmasters/risk/levels.py` + `risk/gate.py` | repo-pinned | Level math + gate verdicts inside backtest loop | `compute_risk_reward` (Decimal), `validate_level_ordering`, `evaluate_gate` are the tested deterministic core |
| Existing `src/goldmasters/strategies/base.py` | repo-pinned | Backtest subjects' entry point | `evaluate(bars, ctx)` is the sole strategy entry; closed-bars-only input discipline already enforced |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tests/conftest.py` throwaway-DB fixture | existing | Per-run isolated DB for journal/backtest integration tests | Every persistence test; never touch the working DB |
| `src/goldmasters/graph/traceability.py` pattern | existing | Template for backtest-completeness measurement | If Phase 6 adds a "backtest assumption completeness" log line, copy `TraceabilityReport` shape |

No new packages. No `Package Legitimacy Audit` required (nothing installed) [ASSUMED — planner to confirm if a DataFrame library is later proposed; recommendation is stdlib + existing stack only].

## Architecture Patterns

### System Architecture Diagram

```
Closed-bar dataset (manifest w/ hash + provenance)
  → split gate (IS / validation / OOS boundaries from BacktestRecord)
  → per-bar walk-forward loop [bar_close_time only, never touch future bars]
  → eligible_agents (scope matrix) → evaluate(bars_so_far, ctx) per strategy
  → evaluate_gate (ordering → risk limits → quality → evidence)
  → fill model (next-bar open ± spread/slippage/commission)
  → BacktestRecord (assumptions + metrics + sample_size) + errors list
  → persist via 0003 tables; missing bars → excluded-period report, never synthesis

Live path (journal half):
DecisionRecord (assemble_decision, Phase 4/5) → JournalEntry snapshot (0002 tables)
  → outcome observations appended as new rows (never UPDATE snapshot)
  → restart-survival proven by round-trip integration test
```

### Recommended Project Structure

```
apps/api/migrations/versions/
├── 0001_contract_document.py   # EXISTING — do not touch
├── 0002_journal_outcome.py     # NEW — journal_entry + outcome_observation tables
└── 0003_backtest.py            # NEW — backtest_run + dataset_manifest tables (or JSONB docs)
src/goldmasters/
├── journal/                    # NEW — snapshot writer + append-only outcome writer (thin)
│   └── store.py
├── backtest/                   # NEW — runner, splits, fills, metrics (deterministic only)
│   ├── runner.py
│   ├── splits.py
│   ├── fills.py
│   └── metrics.py
└── risk/|strategies/           # REUSE unchanged
tests/
├── integration/test_journal_roundtrip.py      # NEW — restart survival + immutability
├── integration/test_backtest_persistence.py   # NEW — record round-trip
└── unit/test_backtest_*.py                    # NEW — leakage/alignment/cost/splits/metrics
```

### Pattern 1: Immutable snapshot + append-only outcome (contract already encodes it)

**What:** `JournalEntry` is frozen; `decision_id`/`run_id` must equal the snapshot's; corrections use `supersedes` + `reason`, never edits [VERIFIED: packages/contracts/src/goldmasters_contracts/journal.py:21-38].
**When to use:** Every persisted decision. The DB layer mirrors it: snapshot table gets no UPDATE path in code (revoke via no-update API, not just convention); outcomes are INSERT-only rows keyed by `decision_id`.
**Example:**
```python
# Source: packages/contracts/src/goldmasters_contracts/journal.py:32-38
@model_validator(mode="after")
def _validate_binding(self) -> JournalEntry:
    if self.decision_id != self.snapshot.decision_id:
        raise ValueError("journal decision_id must equal the snapshot decision_id")
    if self.run_id != self.snapshot.run_id:
        raise ValueError("journal run_id must equal the snapshot run_id")
    return self
```

### Pattern 2: D-4.3 minimal-log boundary (what Phase 6 owns vs not)

**What:** `MINIMAL_LOG_KEYS = frozenset({"run_id","input_ref","config_hash","code_versions","started_at","node_statuses","node_times"})` — the boundary test pins this set so outcomes/journal can never leak into the Phase 4 run record [VERIFIED: src/goldmasters/graph/state.py:40-50]. `run_log()` exposes exactly those keys [VERIFIED: src/goldmasters/graph/state.py:112-126].
**When to use:** Phase 6 links journal rows to runs via `run_id` (+ `input_ref` for input binding via `compute_input_ref` [VERIFIED: src/goldmasters/graph/state.py:88-99]) but never extends the run log itself.

### Pattern 3: Backtest record carries its own reproducibility (contract already encodes it)

**What:** `BacktestRecord` requires `backtest_run_id`, `strategy_id/version`, `dataset_ref` + `dataset_hash`, instrument, `Timeframe`, start/end, `IanaTimezone`, `data_quality`, `parameter_hash`, `assumptions` (spread/commission/slippage/fill_model), IS/VS/OOS boundaries, `metrics` (each with `definition` + `sample_size`), `generated_at`, `code_version` [VERIFIED: packages/contracts/src/goldmasters_contracts/backtest.py:42-68]. A report without run+dataset ref is unrepresentable.
**When to use:** The runner constructs exactly this record; the "assumptions visible" criterion is satisfied structurally, not by documentation discipline.

### Pattern 4: Strategy evaluation no-escape clause (backtest subjects are safe by construction)

**What:** Any rule verdict other than `pass` forces `setup_found=False` with null levels via validator; `build_adapter_evaluation` nulls levels for every non-`SETUP_FOUND` status [VERIFIED: src/goldmasters/strategies/base.py:101-109, src/goldmasters/strategies/base.py:189-214]. The 10 backtest subjects are the Schema.md §8 table rows (`trend-following` … `carry-term-structure`, all `1.0.0`) [VERIFIED: Schema.md:255-266]. Gate is the sole path to TRADE-eligible levels (`trade_eligible_levels` returns `None` on block) [VERIFIED: src/goldmasters/risk/gate.py:138-146]. R:R is `|tp1-entry|/|entry-stop|` in Decimal, recomputed never trusted [VERIFIED: src/goldmasters/risk/levels.py:30-41].
**When to use:** Backtest loop calls `evaluate` → `evaluate_gate` per bar window, identical to the live path — no parallel strategy semantics.

### Anti-Patterns to Avoid

- **Reinterpreting `contract_document` or editing 0001:** the document/promotion split is one-way after records exist (D-07; migration docstring [VERIFIED: apps/api/migrations/versions/0001_contract_document.py:1-5]). Add tables/columns in 0002+, never rewrite history.
- **UPDATE/DELETE on snapshot rows:** corrections = new `JournalEntry` with `supersedes`; test must assert a direct UPDATE path does not exist in the store module.
- **LLM anywhere in the metric path:** prose may describe a backtest; only `backtest/metrics.py` (Decimal) is authoritative (Rules R-05).
- **Filling missing bars:** gaps → `quality_flags` + excluded-period report; synthesis violates R-01 and criterion 3.
- **String-concatenated SQL in migrations:** SQLAlchemy Core + parameterised `op.execute` only (01-06 threat model T-01-19).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decimal wire form / timestamp normalisation | Custom price parsing | `PriceStr`, `UtcDatetime`, `IanaTimezone` from `_base.py` | String-only decimals, UTC normalisation, IANA check already tested [VERIFIED: packages/contracts/src/goldmasters_contracts/_base.py:44-96] |
| ID generation | Sequential/random IDs | `run_`/`dec_`/`journal_`-prefixed UUIDs (`ids.py`) | Closed prefix registry; `JOURNAL` member already exists [VERIFIED: packages/contracts/src/goldmasters_contracts/ids.py:30-41] |
| Level ordering + R:R | Backtest-local math | `risk.levels.build_candidate_levels` / `compute_risk_reward` | Quantize→order→recompute pipeline with claimed-value cross-check [VERIFIED: src/goldmasters/risk/levels.py:86-132] |
| Eligibility + gate | Backtest-local filters | `eligible_agents` matrix + `evaluate_gate` | Locked adapter table (only `SETUP_FOUND` feeds gate) + fail-closed policy checks [VERIFIED: src/goldmasters/strategies/base.py:170-186, src/goldmasters/risk/gate.py:66-135] |
| Completeness measurement | Bespoke audit query | `traceability.py` pattern (`is_traceable`/`traceability_report`/log line) | Evidence-refs-resolve + metadata-present metric with no targets set [VERIFIED: src/goldmasters/graph/traceability.py:52-95] |
| Test DB isolation | Shared dev DB in tests | `tests/conftest.py` throwaway per-run DB | Proven in 01-06; tests must fail loudly, never skip, when the cluster is unavailable |

**Key insight:** Phase 6 is a wiring phase, not an invention phase. Every hard invariant (immutability, no-escape evaluation, gate-as-sole-path, assumption-carrying records) already exists as a tested validator; the new code is thin persistence + loop + deterministic arithmetic that reuses them.

## Common Pitfalls

### Pitfall 1: Look-ahead leakage through bar windows
**What goes wrong:** Backtest evaluates bar N using data from bar N+1 (e.g., passing the full series and slicing carelessly, or using `retrieved_at`/revised values).
**Why it happens:** `evaluate(bars, ctx)` takes a sequence — nothing stops the caller passing future bars.
**How to avoid:** Runner passes only bars with `bar_close_time <= current_bar.bar_close_time`; `data_as_of` pinned to current bar close; leakage test feeds a planted future spike and asserts the earlier evaluation is unaffected.
**Warning signs:** Backtest metrics suspiciously better than live gate behavior.

### Pitfall 2: Timestamp/timezone confusion in splits and fills
**What goes wrong:** IS/OOS boundary applied in the wrong timezone; fill attributed to the signal bar instead of the next bar.
**Why it happens:** Naive datetimes, or mixing source timezone with UTC.
**How to avoid:** Boundaries as `UtcDatetime`; display timezone is the record's `IanaTimezone` field only. Fill rule declared in `fill_model` string and implemented literally (recommended default: next-bar open minus/plus half-spread + slippage, commission per unit — declared, not invented [ASSUMED — no fill model is locked upstream; planner must surface the exact formula as a confirmation checkpoint]).
**Warning signs:** Split-boundary test with a DST-crossing dataset fails; fill test on a gap bar disagrees with the declared model.

### Pitfall 3: Costs silently not applied
**What goes wrong:** Metrics computed gross; spread/commission/slippage fields present but zero or ignored.
**Why it happens:** Assumptions carried but not wired into the P&L accumulation.
**How to avoid:** Cost-application test: a zero-edge round-trip strategy must show a net loss equal to declared costs; zero-cost record rejected by test (assumptions must be non-trivially applied).
**Warning signs:** Win rate and expectancy identical with and without costs.

### Pitfall 4: Decimal-as-float in metrics or JSONB
**What goes wrong:** Metric values round-trip through float and drift; stored JSONB contains JSON numbers for prices.
**Why it happens:** Pydantic/JSON default serialisation of `Decimal`.
**How to avoid:** Reuse `PriceStr` (serialises via `format(value, "f")` [VERIFIED: packages/contracts/src/goldmasters_contracts/_base.py:61-64]); persistence test asserts stored JSONB holds decimal strings, mirroring the 01-06 round-trip assertion.
**Warning signs:** `risk_reward` differs at the 8th decimal between memory and re-read.

### Pitfall 5: Downgrade-afterthought on 0002/0003
**What goes wrong:** `upgrade head` works, `downgrade base` leaves tables/indexes behind (01-06 Pitfall 7).
**Why it happens:** Downgrade written last, tested never.
**How to avoid:** Same proven cycle as 0001: `upgrade head && downgrade base && upgrade head` with post-rollback emptiness assertion, per migration.
**Warning signs:** Second `upgrade head` errors on existing objects.

### Pitfall 6: Scope creep into retention/backup policy
**What goes wrong:** Phase 6 invents journal retention windows or backup procedures.
**Why it happens:** "Surviving a restart" gets read as durability policy.
**How to avoid:** Restart-survival = round-trip persistence test only. Retention/backup stays operator-owned (Memory.md open item); backup/restore testing is Phase 8 T0806.

## Code Examples

### Journal snapshot write + outcome append (pattern from contracts)

```python
# Sources: packages/contracts/src/goldmasters_contracts/journal.py,
#          packages/contracts/src/goldmasters_contracts/decision.py
entry = JournalEntry(
    journal_id="journal_<uuid>", decision_id=decision.decision_id,
    run_id=decision.run_id, recorded_at=now_utc, snapshot=decision,
)
# Outcome: INSERT new row keyed by decision_id; never mutate `entry`.
# Correction: new JournalEntry(snapshot=corrected, supersedes=old_id, reason="...")
# `DecisionRecord` is frozen (ContractModel) and requires manual_review_required=True
# with TRADE⇔complete-levels invariant enforced on construction.
```

### Migration shape (follow 0001 exactly)

```python
# Source: apps/api/migrations/versions/0001_contract_document.py:19-46
revision = "0002_journal_outcome"  # down_revision = "0001_contract_documents"
# upgrade(): op.create_table(...) with sa Core types + postgresql.JSONB,
#   promoted columns + indexes; downgrade(): drop in exact reverse order.
```

### Deterministic metric + hand-verifiable case (pattern from risk.levels)

```python
# Source: src/goldmasters/risk/levels.py:30-41
# risk_reward = |tp1 - entry| / |entry - stop|, Decimal end to end.
# Hand case: entry=100, stop=90, tp1=120 → risk_reward = 20/10 = 2.
# Backtest metrics (win rate, expectancy, max drawdown, profit factor [ASSUMED set —
# no metric list is locked upstream; planner confirms the list]) follow the same
# shape: pure Decimal function + a 5-trade hand-computed fixture asserting equality.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `contract_document` generic table only | Dedicated journal/outcome/backtest tables in 0002/0003 | Phase 6 (this phase) | Queryable snapshots, outcomes, and backtest runs without scanning generic docs |
| Run log carries everything | D-4.3 minimal log; journal/outcomes in Phase 6 tables | Phase 4 (locked) | No dual-source-of-truth; `run_id` is the join key |
| Assumed model/capability in runtime | Discovery + health, nothing assumed (Phase 4) | Phase 4 (locked) | Backtest must likewise assume nothing: dataset, costs, splits all declared per record |

**Deprecated/outdated:** None — 0001, contracts, and graph seam are current and reused as-is.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | No new packages needed (stdlib + existing pins suffice) | Standard Stack | Planner adds a DataFrame dep → needs legitimacy audit + checkpoint |
| A2 | Exact fill formula (next-bar open ± half-spread + slippage, commission per unit) | Pitfalls §2, Code Examples | Wrong formula silently changes every metric; must be operator-confirmed |
| A3 | Backtest metric list (win rate, expectancy, max drawdown, profit factor) | Code Examples | Planner may need a different set; confirm list before Wave 0 test files are named |
| A4 | Outcome observation shape (new row keyed by decision_id; whether a dedicated outcome contract model is added vs reusing envelope) | Architecture Patterns | Affects 0002 table shape; planner decides and records |
| A5 | Dataset storage (bars persisted vs referenced by hash per Schema §12 open item) | Architecture Patterns | Affects 0003 table shape + provenance test design |
| A6 | PostgreSQL cluster availability on the build machine (repo-local scripts from 01-05) | Environment Availability | Integration tests block until cluster runs; unit-only fallback loses restart evidence |

## Open Questions

1. **Exact fill-model formula and cost defaults**
   - What we know: `BacktestAssumptions` requires spread/commission/slippage/fill_model as declared strings; nothing numeric is locked.
   - What's unclear: Per-unit vs per-trade commission, spread application side, slippage model, gap-bar handling.
   - Recommendation: Planner proposes one explicit formula as a `checkpoint:human-verify` item; tests encode exactly that formula and fail on any deviation.

2. **Outcome observation contract shape**
   - What we know: Outcomes must append without mutating the snapshot; no outcome field list is locked upstream.
   - What's unclear: Whether outcomes reuse the agent envelope, a new `OutcomeObservation` contract, or plain JSONB rows.
   - Recommendation: Planner proposes the minimal shape (outcome_id, decision_id, observed_at, outcome_type, payload refs) as a confirmation checkpoint.

3. **Dataset manifest storage**
   - What we know: `BacktestRecord` carries `dataset_ref` + `dataset_hash`; Schema §12 leaves persist-vs-reference open.
   - What's unclear: Whether 0003 stores bars, a manifest row, or just the hash.
   - Recommendation: Default to manifest row (range, symbol mapping, quality report, excluded periods) + hash; never persist inventable bars. Confirm in planning.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Repo-local PostgreSQL cluster (`scripts/postgres/`) | Migration + round-trip integration tests | [ASSUMED — not probed this session; 01-05 provisioned it] | — | Unit tests with throwaway-DB tests marked blocking until cluster runs |
| `uv` + workspace env | Test/lint/typecheck runs | [ASSUMED — used by all prior phases] | — | — |
| MT5 terminal / live data | Backtest datasets | Not required | — | Backtest uses declared historical datasets + fixtures, never live scraping |

**Missing dependencies with no fallback:** None identified — backtest datasets are declared inputs, not live dependencies.
**Missing dependencies with fallback:** PostgreSQL cluster (falls back to unit-only until available; planner must keep the round-trip tests blocking, not skipped).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing `tests/unit`, `tests/integration`, `tests/contract` layout) [ASSUMED — layout read, runner config not re-verified this session] |
| Config file | repo pytest config (see 01-VALIDATION Wave 0 notes) |
| Quick run command | `uv run pytest tests/unit -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-journal-and-backtesting (immutability) | Snapshot write/read unchanged; UPDATE path absent; correction via supersedes | integration | `uv run pytest tests/integration/test_journal_roundtrip.py -x -q` | ❌ Wave 0 |
| REQ-journal-and-backtesting (append-only + restart) | Outcomes append without mutating snapshot; records survive restart | integration | `uv run pytest tests/integration/test_journal_roundtrip.py -x -q` | ❌ Wave 0 |
| REQ-journal-and-backtesting (provenance) | Backtest record carries run+dataset ref, assumptions, splits | unit + integration | `uv run pytest tests/unit/test_backtest_record.py tests/integration/test_backtest_persistence.py -x -q` | ❌ Wave 0 |
| REQ-journal-and-backtesting (splits) | IS/VS/OOS enforcement; missing/excluded periods reported | unit | `uv run pytest tests/unit/test_backtest_splits.py -x -q` | ❌ Wave 0 |
| REQ-journal-and-backtesting (leakage/alignment/cost) | Future-bar probe, timestamp-alignment, cost-application tests fail on violation | unit | `uv run pytest tests/unit/test_backtest_leakage.py tests/unit/test_backtest_costs.py -x -q` | ❌ Wave 0 |
| REQ-journal-and-backtesting (metrics) | Deterministic Decimal metrics + hand-verifiable 5-trade fixture | unit | `uv run pytest tests/unit/test_backtest_metrics.py -x -q` | ❌ Wave 0 |
| Migration integrity (0002/0003) | apply → rollback → re-apply, no objects survive | integration | `uv run pytest tests/integration/test_migration_roundtrip.py -x -q` (extend) | ✅ exists — extend |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before verify; ruff + mypy strict clean (prior-phase gate convention)

### Wave 0 Gaps
- [ ] `tests/integration/test_journal_roundtrip.py` — snapshot immutability + outcome append + restart survival
- [ ] `tests/integration/test_backtest_persistence.py` — record round-trip with decimal-as-string assertion
- [ ] `tests/unit/test_backtest_splits.py` — IS/VS/OOS enforcement + excluded-period reporting
- [ ] `tests/unit/test_backtest_leakage.py` — future-bar probe + timestamp alignment
- [ ] `tests/unit/test_backtest_costs.py` — cost application (zero-edge strategy loses by exactly declared costs)
- [ ] `tests/unit/test_backtest_metrics.py` — Decimal metrics + hand-verifiable fixture
- [ ] `tests/unit/test_backtest_record.py` — assumption-completeness (record without run/dataset ref unrepresentable)
- [ ] Migrations `0002_journal_outcome.py`, `0003_backtest.py` with downgrades

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single local operator, loopback (out of scope) |
| V3 Session Management | no | No sessions in V1 |
| V4 Access Control | partial | No UPDATE/DELETE path on snapshot tables in store code |
| V5 Input Validation | yes | `JournalEntry`/`BacktestRecord` validators; strict+forbid+frozen base |
| V6 Cryptography | no | `dataset_hash`/`parameter_hash` are integrity labels (sha256), not security controls |

### Known Threat Patterns for PostgreSQL + Alembic stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via migration/test SQL | Tampering | SQLAlchemy Core + parameterised `op.execute`; no string-concatenated SQL (01-06 T-01-19) |
| Downgrade leaves objects behind | Tampering / DoS | Downgrade drops exactly what upgrade created, reverse order; round-trip test asserts emptiness |
| Test suite touches working DB | Tampering | Throwaway per-run DB fixture; fail loudly, never skip |
| Float-precision drift in metrics | Tampering (integrity) | `PriceStr` decimal-as-string wire form; JSONB stores strings not numbers |
| LLM-rec calculated metric presented as authoritative | Information / Tampering | Only `backtest/metrics.py` output is authoritative; prose never recalculates (Rules R-05) |

## Sources

### Primary (HIGH confidence)
- `packages/contracts/src/goldmasters_contracts/journal.py`, `backtest.py`, `decision.py`, `_base.py`, `ids.py`, `enums.py` — read this session
- `apps/api/migrations/versions/0001_contract_document.py` — read this session
- `src/goldmasters/graph/state.py` (D-4.3 boundary), `src/goldmasters/graph/traceability.py` — read this session
- `src/goldmasters/strategies/base.py`, `src/goldmasters/risk/levels.py`, `src/goldmasters/risk/gate.py` — read this session
- `.planning/ROADMAP.md` Phase 6 criteria, `.planning/REQUIREMENTS.md` REQ-journal-and-backtesting, `Schema.md` §§6/8/9, `Rules.md` R-01/R-05, `Memory.md` open decisions — read this session
- `.planning/phases/01-contracts-and-foundation/01-06-PLAN.md`, `.planning/phases/05-news-sentiment-ceo/05-03-PLAN.md` + `05-CONTEXT.md` — read this session

### Secondary (MEDIUM confidence)
- None — no external docs consulted; all findings are in-repo.

### Tertiary (LOW confidence)
- `tests/conftest.py` throwaway fixture behavior and pytest runner config — layout confirmed via glob, contents not re-read; tagged [ASSUMED] where cited.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all reuse targets read from source; no new packages.
- Architecture: HIGH — contracts + migration + graph boundary all source-verified.
- Pitfalls: HIGH for leakage/cost/precision/downgrade (grounded in existing validators); MEDIUM for fill-model specifics (no formula locked upstream → A2 + checkpoint).

**Research date:** 2026-10-16
**Valid until:** 30 days (stable domain; in-repo contracts change only by reviewed migration)
