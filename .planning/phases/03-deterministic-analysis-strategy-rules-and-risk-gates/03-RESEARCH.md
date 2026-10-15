# Phase 3: Deterministic Analysis, Strategy Rules and Risk Gates — Research

**Researched:** 2026-10-15
**Domain:** Deterministic market-structure / strategy / risk-gate code over validated MT5 bars
**Confidence:** HIGH (contracts, validation policy, and open items all read from repo this session)

## Summary

Phase 3 turns validated Phase-2 bars into numbers a signal can depend on — and nothing else.
Every price, level, regime label, rule verdict, and risk/reward figure must come out of
versioned, pure, deterministic code with rule-by-rule evidence; any LLM involvement in
authoring these numbers is forbidden by Rules §3.5 and Architecture §2 ("Use deterministic
code for prices, indicator values, risk/reward arithmetic, validation, and gates")
[VERIFIED: Rules.md §3.5, Architecture.md:63-67].

The contract layer already reserves Phase 3's exact extension points: `decision.py`
states "Level *ordering* policy is Phase 3 work (D-04), not enforced here"
[VERIFIED: packages/contracts/src/goldmasters_contracts/decision.py:1-8], `TrendRegime`
labels "require documented, versioned classification rules" [VERIFIED: enums.py:79-84],
and Schema §8 requires strategy evaluations to return `setup_found` plus `rule_checks`
with rule ID, pass/fail/unknown, inputs/evidence, and reason. Phase 2 finished the input
side (provenance-stamped bars, five-state health, append-only precision history) and left
three explicit open items for Phase 3: (1) a contract-size provenance column on
`PrecisionRow`, (2) DST-shifted server-clock adjacency, (3) out-of-order recovery beyond
strict rejection [VERIFIED: 02-04-SUMMARY.md:58-74].

**Primary recommendation:** Create `src/goldmasters/{domain,strategies,risk}/` per the
Architecture §7 layout (no `src/` exists yet — Phase 3 creates it), implement everything as
pure functions on `Decimal` with explicit `now_utc`/parameter arguments following the
`validation.py` precedent, add the contract-size column as a minor-bump contracts change,
and define the two hard policies Phase 1/2 deferred: tick-quantization rounding mode and
level-ordering rules per direction.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Candle/timeframe conventions, timezone policy, tick quantization | Deterministic domain (`src/goldmasters/domain/`) | Contracts package (form only) | Numbers live in versioned code; contracts enforce wire *form* only (D-19 precedent) |
| Market-structure + trend/regime primitives | Deterministic domain | — | Pure functions, identical outputs for identical inputs (ROADMAP criterion 2) |
| Strategy interface, rule checks, candidate levels | Strategies (`src/goldmasters/strategies/`) | — | Schema §8: evaluation returns `setup_found` + `rule_checks`; levels only from defined rules |
| Ordering validation, risk limits, evidence completeness gate | Risk (`src/goldmasters/risk/`) | — | Hard gate blocks candidates before any decision; CEO cannot bypass (Rules §2.5) |
| Specialist-role I/O contracts (typed inputs/outputs, versions, timeouts) | Phase 3 (interface definitions) | Phase 4 (LangGraph nodes) | Criterion 6 needs documented responsibilities now; bounded graph nodes come in Phase 4 |
| Precision history with contract-size provenance | Contracts (column) + adapter (persist) | Deterministic domain (lookup/quantize) | `PrecisionRow` is Phase-1-locked `extra="forbid"`; needs a minor-bump change per D-23 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `decimal` | stdlib (repo Python 3.14.7 per 02-RESEARCH §7) | All price/level/risk-reward arithmetic | Schema §1 forbids binary float as sole authoritative representation where tick alignment matters; `PriceStr` wire form is decimal-string [VERIFIED: _base.py:35-71] |
| Python stdlib `zoneinfo` | stdlib | Timezone/DST conversions | Already the contract mechanism: `IanaTimezone` validates against real zoneinfo names [VERIFIED: _base.py:85-95] |
| Pydantic v2 (existing) | pinned in repo manifests — read from `pyproject.toml` at plan time, do not invent | Result/evidence models, validation barrier | Every contract model derives from `ContractModel` (`strict=True, extra="forbid", frozen=True`) [VERIFIED: _base.py:98-105] |
| `goldmasters-contracts` (existing) | minor bump for contract-size column | `MarketBar`, `PrecisionRow/Table`, `DecisionRecord`/`Levels`, enums | Locked layer; vocabularies only grow within a major (D-23) [VERIFIED: versions.py:1-11] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| pytest (existing, `uv run pytest`) | existing | Deterministic unit tests, boundary tests, golden vectors | Phase 2 precedent: 25 validation tests over labelled fixtures, all pure with explicit `now_utc` |
| Existing `PrecisionTable.with_row` / `lookup` | existing | Tick-size source for quantization; audit lookup at payload `retrieved_at` | Append-only, `lookup` answers `unknown` never a default [VERIFIED: precision.py:72-97] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled Decimal primitives | TA-Lib / pandas / numpy indicators | REJECT: float64 intermediates break tick alignment against the `PriceStr` wire form and the Phase-2 OHLC-tick-align check; adds a native dependency for logic that must be hand-verifiable in tests |
| New `src/goldmasters/` tree | Extend `services/mt5_adapter/` | REJECT: adapter is provider I/O; Architecture §7 places `domain/`, `strategies/`, `risk/` under `src/goldmasters/` [CITED: Architecture.md §7]. Analysis must not couple to one provider |

**Installation:** none — stdlib + existing workspace packages only. No new dependency.

**Version verification:** no new packages; nothing to verify on a registry.

## Package Legitimacy Audit

No external packages installed in this phase. Skipped by design (stdlib-only phase).

## Architecture Patterns

### System Architecture Diagram

```text
Closed H1 MarketBars (quality-stamped, Phase 2)
        │
        ▼
domain/conventions.py ── candle/timeframe rules, server-tz→UTC policy, DST handling
        │                  (consumes PrecisionTable.lookup for tick context)
        ▼
domain/structure.py ── swing/structure primitives (pure, versioned)
        │
        ▼
domain/regime.py ── TrendRegime classification w/ versioned rules + code_hash
        │             (labels ONLY from TrendRegime enum; unknown when indeterminate)
        ▼
strategies/<strategy_id>/ ── rule_checks (pass/fail/unknown + evidence) → setup_found?
        │                      candidate levels ONLY when all rules pass
        ▼
risk/gate.py ── ordering check → risk-limit check → evidence/quality check
        │         BLOCK (with reasons_for_rejection) or PASS (validated Levels)
        ▼
DecisionRecord-shaped output (TRADE iff complete validated levels, else NO_TRADE/
INSUFFICIENT_DATA; manual_review_required=true always) ──► Phase 4 graph consumes
```

Decision points: regime `unknown` → `no_setup`; any rule `fail` → no setup, no levels;
any gate failure → blocked candidate, never a qualified trade. No branching path may
synthesize a level — unknown/invalid levels stay null per Schema §6 invariants
[VERIFIED: decision.py:69-92].

### Recommended Project Structure

```text
src/goldmasters/
├── domain/              # candle conventions, structure + regime primitives (T0301-T0303)
│   ├── conventions.py   # timeframe arithmetic, tz/DST policy, quantization (tick round)
│   ├── structure.py     # swing/high-low/structure primitives, versioned
│   └── regime.py        # TrendRegime classification, versioned rules + code_hash
├── strategies/          # strategy interface + approved strategies only (T0304-T0305)
│   ├── base.py          # Strategy protocol: evaluate() → setup_found + rule_checks
│   └── <strategy_id>/   # one package per user-approved strategy, pinned version
└── risk/                # ordering validation + hard gate (T0306 + gate)
    ├── levels.py        # entry/stop/targets/risk_reward computation + ordering check
    └── gate.py          # risk limits, quality, evidence completeness → block/pass
tests/unit/test_<module>.py   # golden vectors + boundary tests per module
```

Purity boundary (load-bearing): deterministic code lives OUTSIDE `goldmasters-contracts`
and imports from it — never the reverse (D-03/D-08 precedent from Phase 2)
[VERIFIED: 02-CONTEXT.md:70-75]. The `MetaTrader5` import allowlist stays scoped to
`services/mt5_adapter/terminal.py`; Phase 3 code must not import it (boundary scan keeps
passing).

### Pattern 1: Pure function with explicit clock and parameters

**What:** Every deterministic function takes `now_utc` and thresholds/limits as explicit
arguments and returns new immutable values — no wall-clock reads, no module-global
config, no mutation.
**When to use:** Every function in `domain/`, `strategies/`, `risk/`.
**Example (precedent, not new code):**

```python
# Precedent: services/mt5_adapter/validation.py:70-80
def validate_bars(
    bars: Sequence[MarketBar],
    *,
    now_utc: datetime,          # explicit clock — unit-testable, no mocking
    stale_closed_bars: int = 2, # explicit policy — operator-tunable via settings
    stale_grace_seconds: int = 300,
    precision_table: PrecisionTable | None = None,
    ...
) -> list[MarketBar]: ...
```

### Pattern 2: Versioned classification with code hash

**What:** Each strategy/regime module exposes `STRATEGY_ID`, `STRATEGY_VERSION`
(semver, bumped on any rule change), and a `code_hash` (hash of the rule source);
every evaluation output stamps all three, satisfying Schema §8
(`strategy_id`, `version`, `code_hash or immutable code reference`) and the
`strategy_id`/`strategy_version` fields on `DecisionRecord`.
**When to use:** `domain/regime.py`, every `strategies/<id>/` package.

### Pattern 3: Fail-closed gate returning reasons, never exceptions for policy

**What:** `risk/gate.py` returns a `GateVerdict(passed: bool, reasons: list[str],
levels: Levels | None)`-shaped result: `passed=False` carries structured
`reasons_for_rejection` strings that flow into `DecisionRecord`; malformed *inputs*
raise (contract validation), policy *failures* return verdicts. Mirrors the Phase-2
`AdapterFailure` vs contract-`ValidationError` split (malformed spec → `AdapterFailure`,
never a default row) [VERIFIED: test_precision_population.py:149-162].

### Anti-Patterns to Avoid

- **Float intermediates in price math:** compute on `Decimal` end to end; a `float`
  anywhere in the level path breaks tick alignment and the OHLC-tick-align check.
- **LLM-authored numbers:** no model output may enter `entry`/`stop_loss`/`take_profits`/
  `risk_reward`/indicator values (Rules §3.5). Models explain; code computes.
- **Silent defaults for missing policy:** unknown precision → skip tick-alignment
  (Phase-2 precedent), unknown regime → `TrendRegime.UNKNOWN`, unknown level → null.
  Never a default row, default tick, or filled-in guess.
- **Consuming the forming bar:** Phase 2 drops pos-0 forming bar; Phase 3 analysis
  inputs are closed bars only.
- **Erasing disagreement:** per criterion 6, no role overwrites another's findings;
  the gate preserves conflicts as evidence (flows to `DecisionRecord.conflicts`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decimal wire form, UTC normalization, IANA validation | Custom price/timestamp types | `PriceStr`, `UtcDatetime`, `IanaTimezone` from `goldmasters-contracts._base` | Single strict definition; `strict`+`forbid`+`frozen` already enforced [VERIFIED: _base.py] |
| Version acceptance | Custom version compare | `parse_contract_version` / `SchemaVersionStr` | Major-gate + no-`v`-prefix rules already tested [VERIFIED: versions.py:50-84] |
| OHLC/finite/ordered-timestamp invariants | Re-implemented checks | `MarketBar`/`MarketQuote` constructors as the contract gate | D-04 split: invariants in contracts, policy in new code |
| Precision history | New store | `PrecisionTable.with_row` / `lookup` | Append-only + interval audit already proven (D-26, 5 tests) |
| Timezone conversion tables | Hardcoded offsets | `zoneinfo` + operator-set `GOLDMASTERS_MT5_SERVER_TIMEZONE` | DST shifts ±1h; hardcoded offsets rot twice a year |

**Key insight:** Phase 3's novelty is confined to conventions + structure/regime math +
strategy rules + gate. Everything about representing, validating, and versioning those
numbers already exists — reuse it or the committed-schema drift test fails the build.

## Common Pitfalls

### Pitfall 1: Unspecified rounding at tick quantization
**What goes wrong:** Two implementations quantize `entry` to tick grid differently
(half-up vs half-to-even vs truncate) and golden tests disagree with production.
**Why it happens:** Phase 1 explicitly deferred the rounding contract: "the exact
rounding contract (half-up vs half-to-even, ceil/floor/truncate) is NOT yet specified"
and enforces decimal *form* only [VERIFIED: ROADMAP.md:74].
**How to avoid:** `domain/conventions.py` defines ONE `quantize_to_tick(price, tick_size,
rounding=...)` with an explicit, documented `decimal.ROUND_*` mode; boundary tests pin
exact-half-tick behavior. Planner: this needs a locked decision (recommend `ROUND_HALF_UP`
with rationale, or operator choice — do not leave it implicit).
**Warning signs:** any quantization code without a named rounding mode in review.

### Pitfall 2: DST-shift adjacency treated as a gap or as clean data
**What goes wrong:** Spring-forward/fall-back shifts the server-clock hourly sequence by
±1h; strict `+3600s` adjacency flags a false gap (or worse, a backfill "fills" an hour
that never traded).
**Why it happens:** Carried open from Phase 2: "DST-shifted server-clock adjacency
(`category=adjacency`)" recorded open [VERIFIED: 02-04-SUMMARY.md:72-74]; session/DST
bounds are "operator-confirmed" settings, and validation's `H1_SECONDS = 3600` exact
arithmetic explicitly defers "boundary semantics beyond exact arithmetic" to Phase 3
[VERIFIED: validation.py:39-40].
**How to avoid:** T0301 (candle/timeframe conventions + timezone policy) MUST specify:
UTC-normalized adjacency (compare UTC instants, where DST has no effect) as the
canonical rule, plus the server-local DST-fold handling for the one ambiguous hour.
Close the carried assumption with tests on both transition weekends.
**Warning signs:** adjacency logic comparing server-local naive datetimes.

### Pitfall 3: Out-of-order input beyond strict rejection
**What goes wrong:** Analysis receives a repaired/reordered bar sequence and either
crashes or silently analyzes shuffled data.
**Why it happens:** Current policy flags out-of-order as `MALFORMED` on the offending
bar (`bar_open_time < previous_open → MALFORMED`) [VERIFIED: validation.py:103-105];
"out-of-order recovery beyond strict rejection (`category=ordering`)" is recorded open
[VERIFIED: 02-04-SUMMARY.md:72-74].
**How to avoid:** Phase 3 defines the analysis-input contract explicitly: reject
(inputs must arrive ordered; `MALFORMED` → `INSUFFICIENT_DATA`) OR sort-with-audit.
Recommend reject (matches "flagged, not silently removed" and the `preserve` precedent
that refuses to "launder misordering evidence" [VERIFIED: validation.py:87-90]).
**Warning signs:** a `sorted()` call on bars without an accompanying audit flag.

### Pitfall 4: Inventing strategy thresholds or risk limits
**What goes wrong:** Planner fills in stop distances, R:R minima, or risk caps that look
authoritative but were never approved — violating "no invented numbers" (Rules §1.1)
and Architecture §10, which lists "approved strategy set and hard risk thresholds" as
decisions requiring approval.
**Why it happens:** T0305 says "user-approved initial strategies" but no strategy set
has been approved yet in any planning artifact read this session.
**How to avoid:** All thresholds are `GOLDMASTERS_` settings with fail-closed validation
(D-36/D-59 precedent), defaults marked as operator-confirmed, every key covered by the
config-hash test. No threshold literal in strategy code. Planner must surface the
strategy set + limits as discuss-phase questions, not fill them in.
**Warning signs:** a numeric literal (other than 0/1 structural constants) in
`strategies/` or `risk/` code.

### Pitfall 5: Level-ordering assumed instead of specified
**What goes wrong:** A `TRADE` candidate passes with `stop_loss` on the wrong side of
`entry`, or targets unordered — an unqualified trade.
**Why it happens:** Ordering is deliberately unenforced in contracts ("Phase 3 work")
[VERIFIED: decision.py:1-8]; Schema §6 requires "long/short level ordering validated
against the defined order type/strategy model" — but no order-type model is defined yet.
**How to avoid:** `risk/levels.py` specifies per-direction ordering
(long: `stop_loss < entry < tp_1 < tp_2 ...`; short: mirror) plus `risk_reward`
recomputed from validated levels in `Decimal` (never trusted from strategy output);
any violation → gate BLOCK with reason, levels stay null, decision cannot be TRADE.
**Warning signs:** `risk_reward` accepted as an input rather than recomputed.

## Code Examples

Verified patterns from repo sources read this session (skeletons — exact field names
and enum values quoted verbatim):

### Strategy evaluation shape (fields per Schema §8 + DecisionRecord)

```python
# Enum values verbatim from enums.py:37-42, 70-77, 79-94:
# Decision: TRADE | NO_TRADE | INSUFFICIENT_DATA
# Direction: long | short | neutral | unknown
# TrendRegime: uptrend | downtrend | range | breakout | pullback
#              | momentum | continuation | possible_reversal | unknown
from goldmasters_contracts import DecisionRecord  # decision_id, run_id,
    # instrument_id, timeframe, decision, direction, strategy_id,
    # strategy_version, entry, stop_loss, take_profits, risk_reward, thesis,
    # invalidation_conditions, risk_factors, reasons_for_rejection,
    # evidence_refs, agent_statuses, conflicts, data_quality_status,
    # limitations, manual_review_required (always True in V1)
    # [VERIFIED: decision.py:41-67]
```

### Tick quantization against the precision table (contract-size note)

```python
# PrecisionRow fields verbatim: instrument_id, provider_id, tick_size (str),
# decimals (ge=0), provider_spec_version, retrieved_at, superseded_at,
# valid_from, valid_to [VERIFIED: precision.py:33-54].
# OPEN ITEM: no contract-size column (extra="forbid" blocks ad-hoc addition).
# Phase 3 contracts change (minor bump per D-23): add e.g.
#   contract_size: str | None  (decimal-string form, None = unknown provenance)
# then persist trade_contract_size observed on the MT5 descriptor
# (currently visible in fixtures: trade_contract_size=100.0, trade_tick_size=0.01
#  [VERIFIED: test_precision_population.py:37-43]) via get_instrument_spec.
from decimal import Decimal, ROUND_HALF_UP  # rounding mode = locked decision (Pitfall 1)
```

### Gate verdict → DecisionRecord mapping (invariants verbatim)

```python
# TRADE requires direction + ALL levels (entry, stop_loss, take_profits>=1,
# risk_reward); non-TRADE must carry NO levels (null/empty), else ValidationError
# [VERIFIED: decision.py:69-92]. manual_review_required must be True.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `QualityStatus` without healthy member | `QualityStatus.OK = "ok"` added as single healthy value (minor bump, D-23) | Phase 2 | Gate can distinguish healthy bars from flagged ones; `OK` only with zero flags [VERIFIED: enums.py:97-105; validation.py:10-13] |
| Tracer `in_weekend_close` stub | Settings-driven `is_weekend_closed` + `classify_gap` + `missing_opens` (fail-closed `ValueError`) | Phase 2 (02-02) | Single implementation; weekend vs missing-history distinction is tested |
| Zero-row precision table | Populated via `get_instrument_spec`, append-only, build provenance | Phase 2 (02-04) | Tick context available for Phase-3 quantization; contract-size still missing (open item) |
| Form-only Decimal (`D-19`) | Form-only still; value-level tick/rounding rules pending | Phase 3 (this phase) | `conventions.py` closes the Phase-1 rounding assumption |

**Deprecated/outdated:** none. Do not rename `UNSUPPORTED_INSTRUMENT` (typo locked per
D-23; reuse verbatim) [VERIFIED: 02-RESEARCH.md §2].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The initial strategy set and hard risk thresholds will be supplied/approved by the operator (T0305 "user-approved"; Architecture §10) — this research specifies the interface and gate mechanics, not threshold values | Pitfall 4, Patterns | Invented thresholds violate Rules §1.1; planner must ask, not fill in |
| A2 | `ROUND_HALF_UP` recommended (not locked) for tick quantization; needs a locked decision | Pitfall 1 | Golden-test disputes; half-tick behavior differs by mode |
| A3 | UTC-normalized adjacency recommended for DST handling; needs confirmation against broker server-tz behavior on transition weekends | Pitfall 2 | False gaps or filled non-trading hours at DST transitions |
| A4 | Reject (don't sort) out-of-order analysis input recommended; needs locked decision | Pitfall 3 | Silent analysis of shuffled data if sorted without audit |
| A5 | `src/goldmasters/` layout follows Architecture §7 proposal — no `src/` exists yet, so this is a new-tree decision, not reuse | Structure | Planner must confirm; alternative is a new `packages/` member |
| A6 | Specialist-role work in Phase 3 is interface + deterministic logic only; LLM-backed agent nodes belong to Phase 4 | Responsibility Map | Scope creep if Phase 3 attempts full agent implementations |

## Open Questions

1. **Which initial strategies are approved, and what are their rule parameters and risk limits?**
   - What we know: Schema §8 defines the strategy lifecycle
     (`draft → under_review → approved → disabled/retired`) and requires explicit review
     + tests before `approved`; Task T0305 says "user-approved initial strategies".
   - What's unclear: the actual set (e.g. SMA-breakout? swing-continuation?), each rule's
     parameters, and the hard risk limits (max risk per idea, min R:R, daily-break handling).
   - Recommendation: discuss-phase questions to the operator; Phase 3 plans implement ONLY
     the approved set, each in its own versioned package with tests. No unapproved strategy
     code.

2. **Contract-size column shape**
   - What we know: `PrecisionRow` is frozen/`extra="forbid"`; vocabularies/optional fields
     grow by minor bump (D-23); descriptor carries `trade_contract_size` (observed 100.0
     in fixtures — a test value, not a production claim).
   - What's unclear: decimal-string vs numeric form, nullability when a provider omits it.
   - Recommendation: optional decimal-string `contract_size` (`None` = unknown provenance),
     mirroring `PriceStr` form conventions; planner confirms in plan review.

3. **DST transition-weekend ground truth**
   - What we know: server-tz setting + offset sanity check exist (Phase 2); DST ±1h is
     operator-confirmed per D-57.
   - What's unclear: broker-specific transition behavior (missing hour vs repeated hour in
     server clock) until the live terminal is observed.
   - Recommendation: specify UTC-adjacency rule + both-transition tests now; operator
     confirms against live terminal when available (same human-verification channel as
     Phase 2's live run).

## Environment Availability

No external dependencies: pure-stdlib phase (no new tools, services, CLIs, or packages).
Phase-2 toolchain (`uv run pytest`, `ruff`, `mypy --strict`, `scripts/gate`) is proven
green (306 passed, 2 skipped live_mt5) [VERIFIED: 02-VERIFICATION.md:81-87] and is reused
unchanged. No `AGENTS.md` exists at repo root (root listing shows none); Rules.md is the
governing constraints document and is honored throughout (no invented data, signals-only
boundary, deterministic-numbers rule).

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | pytest via `uv run pytest` (config in `pyproject.toml [tool.pytest]`), established Phase-2 precedent |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/unit/test_<module>.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REQ-specialist-agent-responsibilities (criterion 1) | Conventions/tz/quantization incl. DST + rounding boundaries | unit | `uv run pytest tests/unit/test_conventions.py -x -q` | ❌ Wave 0 |
| REQ-specialist-agent-responsibilities (criterion 2) | Structure/regime determinism: identical in → identical out | unit | `uv run pytest tests/unit/test_structure_regime.py -x -q` | ❌ Wave 0 |
| REQ-specialist-agent-responsibilities (criterion 3) | rule_checks per rule; no setup on any fail; id+version stamped | unit | `uv run pytest tests/unit/test_strategies.py -x -q` | ❌ Wave 0 |
| REQ-specialist-agent-responsibilities (criterion 4) | Levels computed in code; ordering validated; null-when-unknown | unit | `uv run pytest tests/unit/test_levels.py -x -q` | ❌ Wave 0 |
| REQ-specialist-agent-responsibilities (criterion 5) | Gate blocks on ordering/limits/quality/evidence; reasons recorded | unit | `uv run pytest tests/unit/test_risk_gate.py -x -q` | ❌ Wave 0 |
| REQ-specialist-agent-responsibilities (criterion 6) | Role responsibility matrix: typed I/O, version, timeout, failure status per role; monitoring emits no recommendation; no overwrite | contract/doc | Role-matrix doc + typed protocols + test asserting monitoring output shape carries no recommendation field | ❌ Wave 0 |
| Deferred open item | Contract-size column persists `trade_contract_size` via spec path | unit+contract | Extend `tests/unit/test_precision_population.py` + contract suite | Exists (extend) |

### Sampling Rate

- **Per task commit:** quick run command for the touched module
- **Per wave merge:** full suite `uv run pytest -x -q` (must stay green; Phase-2 baseline 306 passed)
- **Phase gate:** full suite green + committed-schema drift check
  (`uv run python packages/contracts/_export_schema.py` then `git status` clean under
  `packages/`, Phase-2 precedent) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `src/goldmasters/{domain,strategies,risk}/` tree (or confirmed alternative) — covers all criteria
- [ ] `tests/unit/test_conventions.py`, `test_structure_regime.py`, `test_strategies.py`, `test_levels.py`, `test_risk_gate.py`
- [ ] Contracts minor bump: `contract_size` column + regenerated schemas (no drift)
- [ ] No framework install needed (stdlib + existing workspace)

## Security Domain

No new network, auth, credential, or execution surface in this phase (pure computation
over already-validated bars; signals-only boundary unchanged — boundary scan must keep
passing: no `order_send`, no `symbol_select`, `MetaTrader5` import still confined to
`services/mt5_adapter/terminal.py`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface in this phase |
| V3 Session Management | no | Stateless pure functions |
| V4 Access Control | no | No new endpoints (if a Strategy-Lab read endpoint is added later, it stays read-only, loopback-only per D-34) |
| V5 Input Validation | yes | Bars are validated at construction (`MarketBar` invariants); strategy/gate inputs re-validated via contract constructors; settings fail-closed (D-36); `now_utc` tz-aware enforced by `UtcDatetime` |
| V6 Cryptography | no | `code_hash` is an integrity label (hashlib, existing stdlib), not a security control — do not present it as tamper-proofing |

### Known Threat Patterns for deterministic-signal stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Float-contaminated level presented as tick-valid | Tampering | Decimal-only price path; contract-form + tick-alignment checks |
| Strategy output bypassing the gate | Elevation | Gate is the sole path to TRADE-eligible levels; CEO cannot bypass (Rules §2.5); test asserts no level reaches `DecisionRecord` unvalidated |
| Fixture/golden data mistaken for live | Spoofing | `FIXTURE_` prefix convention + repo-grep test (Phase-2 precedent); golden vectors labelled as vectors |

## Sources

### Primary (HIGH confidence — read from repo this session)

- `packages/contracts/src/goldmasters_contracts/{decision,precision,enums,_base,versions,market}.py` — exact fields, invariants, vocabularies quoted verbatim above
- `services/mt5_adapter/validation.py` — pipeline order, MALFORMED-on-misorder, H1_SECONDS exact arithmetic, `preserve` semantics
- `.planning/phases/02-market-data-and-provider-selection/{02-VERIFICATION.md,02-04-SUMMARY.md,02-02-SUMMARY.md,02-CONTEXT.md,02-VALIDATION.md,02-RESEARCH.md}` — criteria evidence, open items, D-44–D-59 decisions
- `.planning/ROADMAP.md` Phase 3 success criteria (6 items); `Task.md` T0301–T0306; `Rules.md` §§1–4; `Schema.md` §§2/4/6/8; `Architecture.md` §§2/6/7/10

### Secondary (MEDIUM confidence)

- `tests/unit/test_precision_population.py` docstring + fixtures — confirms contract-size
  observation (`trade_contract_size` on descriptor, not persisted) and the Phase-3 open item

### Tertiary (LOW confidence — needs confirmation)

- A1–A6 assumptions (strategy set, rounding mode, DST/ordering policies, layout) — flagged
  for discuss-phase; nothing here is presented as decided

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only; every reused contract cited to lines read this session
- Architecture: HIGH — follows Architecture §7 layout + Phase-2 purity/boundary precedents
- Pitfalls: HIGH — each traces to an explicit deferred/open statement in Phase-1/2 artifacts

**Research date:** 2026-10-15
**Valid until:** 30 days (stable domain; contracts frozen except the planned minor bump)
