# Phase 1: Contracts and Foundation - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers three things and nothing more:

1. A **frozen, machine-checked contract layer** — every Schema.md contract exists as validated, versioned code, and an invalid payload is rejected rather than accepted.
2. A **running, observable local skeleton** — the backend service and client application skeleton run on this machine, the health endpoint answers on loopback only, and configuration is validated at startup.
3. The **research-only boundary enforced structurally from the first commit** — no order-placement, -modification or -closure module, endpoint, tool or broker-trading credential exists, proven by an automated boundary test.

It also stands up the storage and quality-gate scaffolding those three need: the PostgreSQL migration (which must apply and roll back), structured redacted logging, and the check suite whose exact commands and results are recorded.

Out of scope: market data, providers, indicators, strategy logic, LangGraph, LLM calls, news/sentiment, the research console UI, backtesting. Those belong to Phases 2-8. Phase 1 consumes no market data and calls no model.

**Flagged open conflict carried into planning (see also Deferred Ideas):** Phase 1 success criteria 3 and 5 state that the boundary test and the check suite *run in CI*. Verified on this machine during the discussion: there is no git remote, no `.github/` directory, no CI provider, and Docker is not installed. The discussion chose a local git hook plus one gate command. Planning must reconcile the criterion wording with a local runner that a future remote can adopt unchanged, or the criterion is unverifiable as literally written.

</domain>

<decisions>
## Implementation Decisions

### Contract source of truth

- **D-01:** Python-first: Pydantic v2 models are canonical, JSON Schema draft 2020-12 is exported from them, and TypeScript types are generated from that export. Hand-written contracts on both sides were rejected. — **Reversibility:** costly — flipping the source of truth later means re-authoring every contract plus both generators and re-baselining the conformance fixtures.
- **D-02:** One contract-layer version across all contracts, expressed as `major.minor`, alongside the per-artifact behaviour versions Schema.md already defines (`agent_version` in the envelope, `strategy_version`). See D-23 for the semantics. — **Reversibility:** one-way — persisted decisions carry the version they were written with, and Phases 6 and 8 depend on those records staying readable and replayable, so the scheme cannot change once records exist.
- **D-03:** The contract modules live in a standalone importable contracts package that depends only on Pydantic and the standard library — no database, HTTP, provider or model imports. The backend, the type generator and every later phase import it. — **Reversibility:** costly — relocating it later touches the import surface of the backend, the generator and every later phase.
- **D-04:** Validation depth is "contract invariants now, policy later": Pydantic enforces types, nullability, fixed enums and the per-record invariants Schema.md names (for example OHLC ordering). Policy Schema.md does not fix (freshness thresholds, level ordering, risk limits, strategy eligibility) lives in separate deterministic validation modules owned by Phases 2, 3 and 5. Rejection happens in Pydantic and is mapped to the C-09 error contract at the boundary. — **Reversibility:** costly — pulling policy into the frozen layer later re-partitions the package and re-baselines its purity and conformance gates.
- **D-05:** Fail closed on an unknown contract version: a payload with an unknown *major* version, a missing version, or an unparseable version is rejected at the boundary with the C-09 structured error and is never coerced or defaulted. Records already persisted keep the version they were written with and are never silently upgraded on read. — **Reversibility:** costly — this governs the read path for persisted records, so relaxing it later changes how existing evidence is interpreted.
- **D-06:** Contract evidence is a golden conformance suite: Schema.md's two JSON examples must validate exactly as written, plus one accepted example per contract and rejected mutations per contract (wrong enum member, missing required field, null where not nullable, NaN/Infinity, price as a float rather than a Decimal string, unknown extra field). Every named Schema.md invariant gets at least one rejecting case. Phase 8 re-runs it unchanged.
- **D-07:** Contracts stay storage-agnostic and the Phase 1 migration is hand-written. Each contract persists as a validated JSONB document plus promoted columns for queried fields (`run_id`, `agent_name`, `instrument_id`, `created_at`, `status`). A round-trip test loads every accepted conformance fixture into PostgreSQL, reads it back and asserts the instance is unchanged — this is the recorded evidence for criterion 5. — **Reversibility:** one-way — this is the physical persistence shape; changing the document/promotion split after records exist requires a data migration and re-validation of stored payloads.
- **D-08:** Package purity is enforced by an AST import test inside the contracts package that walks every module and fails on any import outside an explicit allowlist (Pydantic and the standard library). The allowlist lives in the test, so adding a dependency is a visible diff. Declarative import linters and convention-only enforcement were rejected.
- **D-09:** Export JSON Schema draft 2020-12 from the Pydantic models, one document per contract, and generate the TypeScript types from those documents with a small generator dev-dependency. The export depends only on the contracts package, never on the web layer. Decimal/UUID/date-time map to declared string formats with format metadata. Generating via the FastAPI OpenAPI document was rejected (it would couple the export to the HTTP layer).
- **D-10:** Commit the exported JSON Schema documents and have the quality gate regenerate them and fail the build if the committed copy differs. Generated TypeScript types are build output and are not committed.
- **D-11:** Decimal values cross the JSON boundary as strings validated against a pattern, with the precision/tick rule declared per instrument and provider in a versioned table. Rationale: JavaScript parses JSON numbers into binary floats, so a numeric price can be rounded client-side; strings make that impossible. Accepted cost: consumers must parse, and JSONB numeric queries need an explicit cast. — **Reversibility:** one-way — the wire format is published; switching to JSON numbers after consumers exist both breaks them and reintroduces client-side precision loss.
- **D-12:** Reject unknown fields on every contract, with the C-09 structured error naming the field. Adding a field is a visible reviewed change on both sides; a breaking one bumps the major per D-23. — **Reversibility:** costly — relaxing to lenient reads later means accepting payloads the boundary has already been rejecting.

### Pin now vs defer (C-11)

- **D-13:** Phase 1 pins the contract-shaping subset of C-11 (identifier scheme, configuration versioning, timeframe enum members, UTC timestamps with explicit offset plus preserved IANA source timezone, the shape of the per-instrument precision table, the quality vocabulary). Deferred with a named owner phase: freshness thresholds → Phase 2; candle-boundary semantics and timezone conversion policy → Phase 3; retention/backup → Phase 6 and Phase 8. No later phase invents its own answer.
- **D-14:** Time-ordered UUIDv7 with a short type prefix (`run_`, `dec_`, `agent_`). The contracts package validates UUID shape using the standard library only, so its Pydantic-only purity holds; generation lives in the app layer. Canonical instrument IDs stay separate and semantic, never a UUID. — **Reversibility:** costly — IDs are persisted in every record, so changing the scheme later requires migrating existing rows.
- **D-15:** A typed settings model validated at startup, carrying its own `config_version`, plus a hash of the effective configuration recorded on every run and decision. Non-secret settings live in the versioned config document; secrets come only from `GOLDMASTERS_`-prefixed environment variables and are never written into it. — **Reversibility:** costly — the hash is recorded on every run and decision, so changing what is hashed invalidates cross-run comparability of past records.
- **D-16:** A closed canonical timeframe enum whose members are taken from the selected provider's documented timeframe list (not from memory), with Phase 2's adapter test asserting each member against capabilities for the selected symbol: supported, or reported unsupported. Provider strings map onto canonical members inside the adapter and never leak outward. Candle-boundary semantics stay deferred to Phase 3 criterion 1. — **Reversibility:** costly — the enum is a published contract; members can only be added, never removed, within a major.
- **D-17:** Fix the form and the separation of instrument IDs, not the vocabulary: `instrument_id` is a documented provider-independent key validated against a strict pattern and forbidden from containing a broker suffix, with `provider_symbol` carried as its own field. The ID-to-symbol mapping for the six instruments is Phase 2 work because it needs verified provider coverage (DR-05, Phase 2 criterion 2).
- **D-18:** Deferred C-11 items are recorded in a pinned-open decisions table in this file (item, why it cannot be answered yet, owning phase, what Phase 1 does instead) and each is also captured into GSD tracking so the owning phase's discussion surfaces it through `cross_reference_todos`.
- **D-19:** Price scale is enforced as form only while the precision table has no rows: a price must be a well-formed decimal string (digits with an optional single dot, no exponent, no NaN/Infinity, no leading plus). No tick multiple and no decimal-place count is enforced until the provider spec exists. The precision table ships with zero rows and its lookup answers *unknown* rather than a default; the conformance suite pins the zero-row case. Phase 2's spec adapter fills the table from `get_instrument_spec`.
- **D-20:** Pin the `quality_status` and `quality_flags` vocabulary by transcribing terms the project already uses (`stale`, `duplicate`, `gap`, `malformed`, `disconnected`, `missing-history`, `unsupported`) plus an explicit not-evaluated/unknown that is never healthy. Phase 1 may only emit the not-evaluated value; thresholds and the computing code stay in Phase 2. — **Reversibility:** costly — the vocabulary is a published contract that only grows, and the never-healthy guarantee is relied on by Phase 7 rendering.
- **D-21:** A closed prefix registry in the contracts package: one enumerated entry per entity type, and each `*_id` field accepts its own prefix only, so a `dec_`-prefixed value is rejected by `run_id` at the boundary with the C-09 error rather than silently joining the wrong record. Adding an entity type is an explicit reviewed change. — **Reversibility:** costly — the per-field prefix binding is part of the published contract.
- **D-22:** The not-evaluated member is distinct from every healthy member of the closed quality enum, no healthy value is ever a default, and the contract rejects a bar that omits quality information rather than filling it in — a producer that cannot evaluate quality must say so explicitly, and a conformance case pins that. Phase 7 criterion 3 owns the rendering rule that unknown is never styled healthy.
- **D-23:** `major.minor`. Adding an enum member or a new optional field bumps the minor and is monotonic within a major (vocabularies only grow); a breaking change (field renamed or retyped, required field added, enum member removed) bumps the major. A reader accepts any `1.x` and rejects anything else, so a decision recorded under `1.2` stays readable and replayable by a build at `1.5` — which Phase 6 immutability and Phase 8 audit depend on. This refines D-05 to mean an unknown *major*, or a missing/unparseable version. — **Reversibility:** one-way — the versioning semantics underwrite replay of persisted evidence.
- **D-24:** The versioned per-instrument precision table lives in PostgreSQL, keyed by instrument and provider, populated by Phase 2 from `get_instrument_spec`, with each row recording its provenance (provider spec version, `retrieved_at`, `superseded_at`). Rows are never silently overwritten. — **Reversibility:** one-way — audit resolution depends on this history existing from the first populated row.
- **D-25:** Pin the form and the rule for provider identity, not the registry: `provider_id` is a stable lowercase snake_case key validated against a pattern, explicitly not a display name and not the provider's own naming. The registry of real provider IDs is created in Phase 2 with the adapters. Provider choice stays explicit and recorded per run per C-04b; no silent fallback.
- **D-26:** Historical payloads are resolved against precision at audit time: each precision row carries `valid_from` and `valid_to`, superseded rows stay on the table, and an audit resolves the row in force at the payload's `retrieved_at`. Nothing is captured at write time, no destructive update happens, and Schema.md's market-data field list is untouched. — **Reversibility:** one-way — the interval history is the only record of what precision applied when.
- **D-27:** Configuration is resolved once at startup into an immutable settings object and hashed once; every run and decision records that hash, so a single run can never straddle two configurations. A change means a restart or an explicit reload that begins a new configuration generation.
- **D-28:** A provider timeframe outside the canonical enum is reported unsupported for that provider — never rounded to a neighbouring member, never passed through under its provider name. A capability report lists what the provider does offer; the operator picks a supported timeframe or the request fails structured. No provider-native string reaches strategy logic.

### Local runtime topology

- **D-29:** Portable pinned PostgreSQL binaries, script-managed: the repo pins an exact PostgreSQL version, and a script provisions, initialises and starts it from a repo-local data directory. Nothing depends on a machine-wide install. Docker Desktop is not used (it is not installed on this machine). A native Windows service install was rejected as machine-coupled. — **Reversibility:** costly — switching to a service or container later changes the stack script, the gates and every developer's setup.
- **D-30:** JSON-structured logs plus local OpenTelemetry traces written to disk, with no collector and no external backend. Both stay local and are readable without provisioning another service.
- **D-31:** The Phase 1 health surface proves the chain: it renders backend status and version, the contract schema version, the effective-config hash and database reachability, so a green reading means the chain is actually wired rather than a scaffold returning 200 unconditionally. A scaffold-only or placeholder shell was rejected.
- **D-32:** No dependency on and no probe of MT5 or Ollama: the backend starts and stays healthy with neither installed, because Phase 1 consumes no market data and calls no model, and a test proves the skeleton runs without them. This keeps Phase 1 independent of tasks T0004-T0006 and of DR-13.
- **D-33:** One documented stack command brings up the database and the backend together, recorded in the run documentation as the single entry point. Manual multi-terminal startup and machine-wide Windows services were rejected.
- **D-34:** Loopback-only binding is enforced by startup validation: the process refuses to start if the effective configuration would bind a non-loopback interface, and the rule is covered by both a negative test (a non-loopback bind is rejected) and an acceptance test (a loopback bind starts and is reachable).
- **D-35:** Two database roles: a persistent working instance holding development data, plus a throwaway per-run test instance that the test run creates and drops, so tests never mutate working data and results are reproducible. A single shared instance and a temp-only instance were both rejected.
- **D-36:** Missing or invalid configuration fails startup: the typed settings model declares every key required or optional, and a missing required key or an invalid value stops the process with a structured error naming the key. `.env.example` is covered by two tests — one asserting it enumerates every required key, one asserting it holds no secret value. Warn-and-continue and lazy validation were rejected.

### Boundary + gate enforcement

- **D-37:** The signals-only boundary is proven by a static source scan plus a dependency allowlist: a test walks the source tree and fails on any forbidden import or call (order-placement APIs and broker mutating methods), and the dependency manifest is checked against an explicit allowlist, so adding any trading capability becomes a visible diff that breaks the build. Convention-and-review alone is not a proof; a read-only adapter wrapper alone only covers code routed through it.
- **D-38:** One gate command runs all gates in order: format check, lint, mypy strict, the full test suite and the contracts purity test. This makes the R-10 "done" criterion one reproducible command rather than several the operator must remember.
- **D-39:** A tracked local git hook (via `core.hooksPath`) runs the fast subset on commit, and the full gate command is the documented step before declaring work done. Nothing depends on a CI provider that does not exist. Verified on disk during this discussion: no git remote, no `.github/` directory, no `core.hooksPath`, no `.githooks/`, no `.pre-commit-config.yaml`, no `pyproject.toml`, no `tox.ini`, and Docker is not installed.
- **D-40:** Fast subset on commit, full gate on demand: the hook runs the format check, lint and mypy over changed files for a quick signal, while the full command (all tests, the purity test and the conformance suite) runs before work is declared done.

### Repository layout

- **D-41:** Adopt the `Architecture.md` §7 proposal for the app and service trees — `apps/web`, `apps/api`, `services/mt5_adapter`, `src/goldmasters/{graph,agents,data,domain,strategies,risk,backtesting,persistence,observability}`, `tests/{unit,integration,contract,security,e2e}` — but lift the contracts package to its own top-level package, because three consumers import it (the backend, TypeScript type generation and every later phase) and it needs an independent lint/type/purity gate rather than living inside a distribution whose other modules legitimately import Pydantic, HTTP and database code. Adopting §7 unchanged was rejected for that reason; a flatter layout was rejected for leaving no home for the gate or the generated client types. — **Reversibility:** costly — moving packages later touches every import path plus both toolchains.
- **D-42:** The Python side is packaged as independent installable packages: the contracts package is its own distribution that `apps/api` and the TypeScript type generator declare a dependency on, so the purity rule surfaces as a declared dependency the AST allowlist test catches, and later phases depend on its published shape rather than reaching in by relative path. — **Reversibility:** costly — merging distributions later touches packaging and every consumer.
- **D-43:** `apps/web` holds a minimal client skeleton that renders the health surface (backend status and version, contract schema version, effective-config hash, database reachability), satisfying criterion 2. The client imports TypeScript types generated from the committed JSON Schema as build output, so it can never drift from the contracts and never imports Python. A fuller app shell was rejected because Phase 7 owns the console design; a static page outside a framework was rejected as deferring the framework decision.
- **D-44:** All ten existing root documents stay at the repository root (`Schema.md`, `Rules.md`, `Prd.md`, `Architecture.md`, `Design.md`, `Debug.md`, `Security.md`, `Memory.md`, `Task.md`, `AGENTS.md`). `canonical_refs` stay root-relative, no existing cross-reference breaks, and no `docs/` migration runs in the same phase that freezes contracts. This also avoids compounding the existing `PRD.md`-versus-`Prd.md` naming inconsistency.

### Agent's Discretion

- The Python build backend / packaging tool is not chosen here; research and planning pick it once the toolchain is fixed, subject to D-42.
- Exact pinned versions of PostgreSQL, Pydantic, FastAPI and the frontend stack are deliberately not invented — research locks tested versions in dependency files.
- The internal module decomposition inside the contracts package, and the concrete shape of the static boundary scan (which AST nodes and forbidden-symbol list), are planning-level.
- Whether the health surface is one endpoint or a small set rendered together is planning-level, provided D-31's chain-proof content is present.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contracts and schema (normative)
- `Schema.md` — canonical names and JSON shapes. C-01..C-11 (C-11 lists the unresolved items this discussion addresses); C-04 defines the market-data field list; C-04b the provider interface; C-09 the error contract. Must be followed exactly.
- `Prd.md` — product requirements; open questions the contracts must satisfy.

### Rules and boundaries
- `Rules.md` — R-01 truth/provenance, R-02 product boundary, R-03 agent boundaries, R-05 workflow, R-07 security, R-09 testing, R-10 DONE criteria.

### Architecture
- `Architecture.md` §2 — proposed stack and boundaries (Python, FastAPI proposed, PostgreSQL, LangGraph, Ollama, provider interface).
- `Architecture.md` §7 — the repository layout proposal adopted by D-41 (with the contracts-package deviation D-41 records).
- `Architecture.md` §8 — quality-gate expectations (contract tests, integration tests, "CI should fail on lint/type/test/schema failures").
- `Architecture.md` §10 — architecture decisions requiring approval, three of which this discussion resolves (PostgreSQL install method, local-only vs LAN, initial symbol/timeframe policy is Phase 2).

### Working documents
- `Design.md` — UI/design direction (Phase 7 primary; Phase 1's client skeleton only needs the health surface per D-43).
- `Security.md` — audit procedure (report first, no edits until approved).
- `Debug.md` — debugging procedure (diagnose → confirm → minimal fix).
- `Task.md` — task ledger; currently stale and disagrees with `Memory.md` (RISK-01/RISK-02).
- `Memory.md` — decision ledger; missing the v1.0 milestone record.
- `AGENTS.md` — session-start rules; contains stale references (a non-existent "Rules R-12", missing `.scratch/`, `docs/adr/`, `GLOSSARY.md`, `docs/agents/*`, and writes `PRD.md` while the file is `Prd.md`).

### Planning
- `.planning/PROJECT.md` — constraints, locked and proposed decisions DR-01..DR-15, open risks RISK-01..RISK-04.
- `.planning/REQUIREMENTS.md` — `REQ-no-trade-execution` and the 12/12 traceability table.
- `.planning/ROADMAP.md` — Phase 1 goal (line 37) and the five success criteria (lines 41-45).
- `.planning/STATE.md` — milestone `v1.0` / "Research Signal Team".

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **None — this is a greenfield repository.** Verified during the discussion: the working tree contains only the ten root Markdown documents plus `.planning/`. There is no `src/`, no `apps/`, no `tests/`, no `pyproject.toml`, no `.env.example`, no `.github/`, and no hook configuration. Nothing exists to reuse.

### Established Patterns
- None in code. The only established constraints are documentary: `Schema.md` names and JSON shapes are canonical and must be followed exactly; `Rules.md` R-01 requires truth and provenance; R-02 fixes the product boundary (research and decision support only, no execution).
- `Architecture.md` §7's proposed tree is a proposal explicitly marked "not an existing tree — adapt only after repository inspection"; D-41 is that adaptation.

### Integration Points
- None yet — Phase 1 creates the first ones: the contracts package → `apps/api` → `apps/web` health surface, the contracts package → the TypeScript type generator, and the hand-written migration → the local PostgreSQL instance.
- Two machine facts already established (probe results, not assumptions) that the skeleton must respect: Docker is not installed and `psql` is not on PATH, so D-29's portable-binaries script is the only viable local PostgreSQL path; Python is 3.14.7, where `uuid7` is in the standard library.

</code_context>

<specifics>
## Specific Ideas

- **Portable pinned binaries over anything machine-wide.** The owner's stated preference: "Portable pinned binaries, script-managed" — the stack must not depend on a machine-wide install or on Docker (which is not installed).
- **One entry point.** "One documented stack command" is the requested operator experience; a multi-terminal manual sequence was explicitly rejected.
- **The health surface must prove the chain**, not merely answer. "One health surface that proves the chain" was the owner's phrasing; a placeholder shell was rejected.
- **The client never imports Python.** Types reach `apps/web` only as generated build output from the committed JSON Schema.
- **Deviate from `Architecture.md` §7 deliberately, in one place:** the contracts package is lifted to its own top-level package rather than living at `src/goldmasters/domain/`.
- **Keep the ten documents at the root.** A `docs/` migration was considered and declined for this phase.
- **Do not pin versions from memory.** `Architecture.md` §5 states it explicitly: exact package versions are intentionally not invented; use current documentation and lock tested versions.

</specifics>

<deferred>
## Deferred Ideas

Carried with a named owner phase so no later phase invents its own answer:

- **Freshness thresholds** (per instrument and timeframe) — owned by Phase 2, Phase 2 criterion 5.
- **Candle-boundary semantics** (which instant a D1 bar opens; session versus UTC day) — owned by Phase 3, Phase 3 criterion 1.
- **Timezone conversion policy and provider timezone mapping** — owned by Phase 3 criterion 1. Representation is already pinned in Phase 1: UTC ISO-8601 with an explicit offset, IANA source timezone preserved.
- **Retention and backup policy** for market data, evidence and journal records — owned by Phase 6 (write path) and Phase 8 criterion 4 (backup/restore test).
- **Instrument vocabulary and provider symbol mapping** for gold, silver, forex, oil, BTC and ETH — owned by Phase 2 (DR-05, Phase 2 criterion 2).
- **Provider ID registry** — owned by Phase 2 (adapters and capability reporting).

Offered as gray areas in this discussion and **not selected** (open for research/planning):

- **Error contract vocabulary (C-09)** — the envelope shape is pinned; the code list and the rule for minting new codes are not. Criterion 1 requires the error contract as validated, versioned code, so planning must settle it.
- **Migration lifecycle** — criterion 5 requires the migration to apply *and roll back*, so the downgrade requirement, the migration tool pin (Alembic per `Architecture.md` §8), and how the same migration is applied to the persistent working instance versus the throwaway per-run test instance must be settled in planning.
- **Log and trace redaction plus correlation-ID propagation** — criterion 4 requires structured, correlation-ID stamped and redacted logs/traces; D-30 pinned the transport but not the redaction rules or the correlation-ID origin and propagation.

**FLAGGED OPEN ITEM (unresolved, not a decision):** Phase 1 success criteria 3 and 5 say the boundary test and the check suite *run in CI*, but this machine has no git remote, no `.github/`, no CI provider and no Docker, while D-39 chose a local git hook plus one gate command. Planning must reconcile the criterion wording with a local runner a future remote can adopt unchanged, or the criterion is unverifiable as written. Do not silently mark this criterion met.

### Reviewed Todos (not folded)
- None — `cross_reference_todos` matched zero pending todos at the time of this discussion.

</deferred>

---

*Phase: 1-Contracts and Foundation*
*Context gathered: 2026-10-13*
