# Phase 1: Contracts and Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-13
**Phase:** 1-Contracts and Foundation
**Areas discussed:** Contract source of truth, Pin now vs defer (C-11), Local runtime topology, Boundary + gate enforcement, Repository layout

Every selection below was the recommended option; no free-text "Other" alternative was chosen. Options are listed in the order presented.

---

## Contract source of truth

| Question | Options considered | Selected |
|---|---|---|
| Where should the contract truth live? | Python-first (Pydantic canonical → JSON Schema → TS) · Schema-first (JSON Schema) · Hand-written both sides · You decide | Python-first |
| How should schema_version work? | One contract-layer version · Per-contract versions · Split by artifact class | One contract-layer version (refined to major.minor) |
| Where do the contract modules physically live? | Standalone importable contracts package · Inside the backend package · Submodule of the backend | Standalone package (Pydantic + stdlib only) |
| How deep should validation go, and where does rejection happen? | Contract invariants now, policy later · All rules in the frozen layer · Shape-only plus a separate gate layer | Contract invariants now, policy later |
| What happens on an unknown schema_version? | Fail closed on unknown version · Accept same-major versions · Strict write, permissive read | Fail closed (refined to unknown major) |
| How should contract test evidence be built? | Golden conformance suite · Targeted unit tests · Round-trip generated fixtures | Golden conformance suite |
| How should the database schema relate to the contracts? | JSONB document + promoted columns · Normalised columns per field · Generate tables from contracts | JSONB + promoted columns, with a round-trip test |
| How is package dependency purity enforced? | AST import test with allowlist · Declarative import linter · Convention and review only | AST import test with allowlist |
| How are the exported schema and frontend types produced? | Pydantic → JSON Schema → TS · Via the FastAPI OpenAPI document · Hand-written TS, fixture-checked | Pydantic → JSON Schema → TS |
| Are generated artifacts committed and freshness-checked? | Commit schema, gate freshness · Commit schema and TS types · Generate at build time only | Commit schema, gate freshness (TS not committed) |
| How are Decimal values represented at the JSON boundary? | Decimal as JSON strings · JSON numbers with tick validation · String plus numeric mirror | Decimal as JSON strings |
| What should a contract do with an undeclared field? | Reject unknown fields · Strict on input, lenient on read-back · Allow but record as limitations | Reject unknown fields |

**Notes:** The version question was refined mid-discussion — fail-closed (D-05) was reconciled with major.minor (D-23) to mean an unknown *major*, or a missing/unparseable version, because a reader must still understand its own older records.

---

## Pin now vs defer (C-11)

| Question | Options considered | Selected |
|---|---|---|
| How much of C-11 should Phase 1 decide? | Pin the contract-shaping subset · Freeze all seven now · Defer all seven | Pin the contract-shaping subset, defer with named owner phases |
| What identifier scheme should the contracts use? | UUIDv7 with a type prefix · Plain UUIDv7 · Plain UUIDv4 · Semantic string keys | UUIDv7 with a type prefix |
| How should configuration be versioned and recorded? | Typed config plus effective-config hash · Environment-only configuration · Versioned config file, no hash | Typed config plus effective-config hash |
| How should the timeframe vocabulary be fixed? | Closed enum from provider capabilities · Narrow initial set, grow on demand · Minutes plus calendar flag | Closed enum from provider capabilities |
| How should canonical instrument IDs be handled now? | Form now, vocabulary in Phase 2 · Pin the vocabulary now · Defer entirely | Form now, vocabulary in Phase 2 |
| How should deferred C-11 items be recorded? | CONTEXT.md table plus tracker capture · CONTEXT.md table only · Machine-checked open-decisions file | CONTEXT.md table plus tracker capture |
| What should Phase 1 enforce about price scale with no precision rows? | Form now, scale policy in Phase 2 · Seed precision values now · Global decimal-place bound | Form now, scale policy in Phase 2 |
| How much of the data-quality vocabulary should Phase 1 pin? | Pin the vocabulary, defer the thresholds · Field and one value only · Defer the fields to Phase 2 | Pin the vocabulary, defer the thresholds |
| How strict should the identifier prefix scheme be? | Closed registry, one prefix per field · Open prefix, validate the UUID only · Convention only | Closed registry, one prefix per field |
| How is "quality not evaluated" kept from being read as healthy? | Explicit member, no default, pinned by a test · Document the rule, enforce in Phase 7 · Null means not evaluated | Explicit member, no default, pinned by a test |
| How should the version number distinguish additive from breaking? | Major.minor, additive within a major · Single version, exact match only · Bump only on breaking changes | Major.minor, additive within a major |
| Where should the precision table live? | Versioned database table with provenance · Committed versioned file · File seeds the table | Versioned database table with provenance |
| How should provider identity be handled in Phase 1? | Form now, registry in Phase 2 · Pin the initial provider ID · Defer provider_id to Phase 2 | Form now, registry in Phase 2 |
| How is a historical payload resolved against the precision that applied? | Interval-versioned rows, resolved at audit time · Stamp the bar with its precision row · Leave it to Phase 6 | Interval-versioned rows, resolved at audit time |
| How should the effective-config hash behave across a run? | Immutable per process, restart to change · Live reload, hash per payload · Run record only | Immutable per process, restart to change |
| What happens when a provider offers a timeframe outside the enum? | Report unsupported, never substitute · Pass-through member for raw values · Round and flag the substitution | Report unsupported, never substitute |

---

## Local runtime topology

| Question | Options considered | Selected |
|---|---|---|
| How should the local PostgreSQL instance be provided? | Portable pinned binaries, script-managed · Native Windows service install · Docker Desktop | Portable pinned binaries, script-managed |
| What observability should the skeleton ship with? | JSON logs plus local OpenTelemetry traces · Logs only · Collector UI | JSON logs plus local OpenTelemetry traces |
| What should the health surface be? | One health surface that proves the chain · Scaffold only · Placeholder shell | One health surface that proves the chain |
| Should the skeleton depend on or probe MT5 and Ollama? | No dependency, no probe, proven by a test · Probe both at startup · Require both | No dependency, no probe, proven by a test |
| How should an operator start the local stack? | One documented stack command · Manual multi-terminal startup · Windows services | One documented stack command |
| How should loopback-only binding be guaranteed? | Enforced by startup validation, tested both ways · Test after startup · Firewall rule | Enforced by startup validation, tested both ways |
| How many database instances should exist? | Persistent working instance plus per-run test instance · Single shared instance · Temp instance only | Persistent working plus per-run test instance |
| What happens when configuration is missing or invalid? | Fail startup, declare required versus optional · Warn and continue · Lazy validation on first use | Fail startup, declare required versus optional |

---

## Boundary + gate enforcement

| Question | Options considered | Selected |
|---|---|---|
| How is the signals-only boundary proven structurally? | Static scan + dependency allowlist · Read-only adapter wrapper only · Convention and review only | Static scan + dependency allowlist |
| How does the contracts purity gate relate to the other gates? | One gate command runs them all in order · Separate commands per gate · Purity test folded into the test suite | One gate command runs them all in order |
| Where do the gates run, with no remote and no Docker? | Local git hook + the one gate command · Manual run before commit · Defer until a CI provider exists | Local git hook + the one gate command |
| Which checks run on every commit vs the full gate? | Fast subset on commit, full gate on demand · Everything on every commit · Tests only on commit | Fast subset on commit, full gate on demand |

**Notes:** Verified on disk before this area was discussed — no git remote, no `.github/` directory, no `core.hooksPath`, no `.githooks/`, no `.pre-commit-config.yaml`, no `pyproject.toml`, no `tox.ini`. Docker is not installed. This makes the roadmap's "runs in CI" wording (criteria 3 and 5) a conflict, flagged in CONTEXT.md as an unresolved open item rather than a decision.

---

## Repository layout

| Question | Options considered | Selected |
|---|---|---|
| How should the repo be laid out relative to Architecture.md §7? | Adopt §7 with contracts as a top-level package · Adopt §7 exactly · Flatter layout | Adopt §7, contracts as a top-level package |
| How should the Python side be packaged so purity is real? | Independent installable packages · Single distribution, internal subpackage · You decide | Independent installable packages |
| What should the client skeleton be, and how does it consume types? | apps/web minimal skeleton on generated types · apps/web with a fuller app shell · Minimal static client only | apps/web minimal skeleton on generated types |
| Do the ten root documents move under docs/? | Keep the ten docs at the repository root · Move all ten under docs/ · Split: normative at root, process under docs/ | Keep the ten docs at the repository root |

**Notes:** The user asked to explore additional gray areas beyond the four originally selected. Three further areas were offered — error contract vocabulary (C-09), migration lifecycle, and log/trace redaction plus correlation-ID propagation — and were not selected; they are recorded as open in CONTEXT.md's Deferred Ideas rather than being decided or silently dropped.

---

## Agent's Discretion

- The Python build backend / packaging tool (research and planning choose it, subject to D-42).
- Exact pinned versions of PostgreSQL, Pydantic, FastAPI and the frontend stack — deliberately not invented; research locks tested versions.
- The internal module decomposition of the contracts package, and the concrete shape of the static boundary scan.
- Whether the health surface is one endpoint or a small set, provided D-31's chain-proof content is present.

No "You decide" option was selected by the user in any question; the discretion above is what the recorded decisions left open.

## Deferred Ideas

- Freshness thresholds — Phase 2 criterion 5.
- Candle-boundary semantics — Phase 3 criterion 1.
- Timezone conversion policy and provider timezone mapping — Phase 3 criterion 1.
- Retention and backup policy — Phase 6 (write path), Phase 8 criterion 4.
- Instrument vocabulary and provider symbol mapping — Phase 2 (DR-05, criterion 2).
- Provider ID registry — Phase 2.
- Error contract vocabulary (C-09) — offered, not selected; open for planning.
- Migration lifecycle (downgrade, tool pin, per-instance application) — offered, not selected; open for planning.
- Log/trace redaction and correlation-ID propagation — offered, not selected; open for planning.
- **FLAGGED, unresolved:** the roadmap's "runs in CI" wording for criteria 3 and 5 versus a machine with no remote, no CI provider and no Docker.
