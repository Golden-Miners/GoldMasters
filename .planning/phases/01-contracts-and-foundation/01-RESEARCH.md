# Phase 1: Contracts and Foundation - Research

**Researched:** 2026-10-13
**Domain:** Python-first contract layer (Pydantic v2 → JSON Schema 2020-12 → TypeScript), local Python/Node skeleton, portable pinned PostgreSQL, structural signals-only boundary enforcement, local quality gate
**Confidence:** MEDIUM-HIGH (versions and library APIs verified this session; three machine-specific behaviours remain `[ASSUMED]` and are listed in the Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Contract source of truth

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

#### Pin now vs defer (C-11)

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

#### Local runtime topology

- **D-29:** Portable pinned PostgreSQL binaries, script-managed: the repo pins an exact PostgreSQL version, and a script provisions, initialises and starts it from a repo-local data directory. Nothing depends on a machine-wide install. Docker Desktop is not used (it is not installed on this machine). A native Windows service install was rejected as machine-coupled. — **Reversibility:** costly — switching to a service or container later changes the stack script, the gates and every developer's setup.
- **D-30:** JSON-structured logs plus local OpenTelemetry traces written to disk, with no collector and no external backend. Both stay local and are readable without provisioning another service.
- **D-31:** The Phase 1 health surface proves the chain: it renders backend status and version, the contract schema version, the effective-config hash and database reachability, so a green reading means the chain is actually wired rather than a scaffold returning 200 unconditionally. A scaffold-only or placeholder shell was rejected.
- **D-32:** No dependency on and no probe of MT5 or Ollama: the backend starts and stays healthy with neither installed, because Phase 1 consumes no market data and calls no model, and a test proves the skeleton runs without them. This keeps Phase 1 independent of tasks T0004-T0006 and of DR-13.
- **D-33:** One documented stack command brings up the database and the backend together, recorded in the run documentation as the single entry point. Manual multi-terminal startup and machine-wide Windows services were rejected.
- **D-34:** Loopback-only binding is enforced by startup validation: the process refuses to start if the effective configuration would bind a non-loopback interface, and the rule is covered by both a negative test (a non-loopback bind is rejected) and an acceptance test (a loopback bind starts and is reachable).
- **D-35:** Two database roles: a persistent working instance holding development data, plus a throwaway per-run test instance that the test run creates and drops, so tests never mutate working data and results are reproducible. A single shared instance and a temp-only instance were both rejected.
- **D-36:** Missing or invalid configuration fails startup: the typed settings model declares every key required or optional, and a missing required key or an invalid value stops the process with a structured error naming the key. `.env.example` is covered by two tests — one asserting it enumerates every required key, one asserting it holds no secret value. Warn-and-continue and lazy validation were rejected.

#### Boundary + gate enforcement

- **D-37:** The signals-only boundary is proven by a static source scan plus a dependency allowlist: a test walks the source tree and fails on any forbidden import or call (order-placement APIs and broker mutating methods), and the dependency manifest is checked against an explicit allowlist, so adding any trading capability becomes a visible diff that breaks the build. Convention-and-review alone is not a proof; a read-only adapter wrapper alone only covers code routed through it.
- **D-38:** One gate command runs all gates in order: format check, lint, mypy strict, the full test suite and the contracts purity test. This makes the R-10 "done" criterion one reproducible command rather than several the operator must remember.
- **D-39:** A tracked local git hook (via `core.hooksPath`) runs the fast subset on commit, and the full gate command is the documented step before declaring work done. Nothing depends on a CI provider that does not exist. Verified on disk during this discussion: no git remote, no `.github/` directory, no `core.hooksPath`, no `.githooks/`, no `.pre-commit-config.yaml`, no `pyproject.toml`, no `tox.ini`, and Docker is not installed.
- **D-40:** Fast subset on commit, full gate on demand: the hook runs the format check, lint and mypy over changed files for a quick signal, while the full command (all tests, the purity test and the conformance suite) runs before work is declared done.

#### Repository layout

- **D-41:** Adopt the `Architecture.md` §7 proposal for the app and service trees — `apps/web`, `apps/api`, `services/mt5_adapter`, `src/goldmasters/{graph,agents,data,domain,strategies,risk,backtesting,persistence,observability}`, `tests/{unit,integration,contract,security,e2e}` — but lift the contracts package to its own top-level package, because three consumers import it (the backend, TypeScript type generation and every later phase) and it needs an independent lint/type/purity gate rather than living inside a distribution whose other modules legitimately import Pydantic, HTTP and database code. Adopting §7 unchanged was rejected for that reason; a flatter layout was rejected for leaving no home for the gate or the generated client types. — **Reversibility:** costly — moving packages later touches every import path plus both toolchains.
- **D-42:** The Python side is packaged as independent installable packages: the contracts package is its own distribution that `apps/api` and the TypeScript type generator declare a dependency on, so the purity rule surfaces as a declared dependency the AST allowlist test catches, and later phases depend on its published shape rather than reaching in by relative path. — **Reversibility:** costly — merging distributions later touches packaging and every consumer.
- **D-43:** `apps/web` holds a minimal client skeleton that renders the health surface (backend status and version, contract schema version, effective-config hash, database reachability), satisfying criterion 2. The client imports TypeScript types generated from the committed JSON Schema as build output, so it can never drift from the contracts and never imports Python. A fuller app shell was rejected because Phase 7 owns the console design; a static page outside a framework was rejected as deferring the framework decision.
- **D-44:** All ten existing root documents stay at the repository root (`Schema.md`, `Rules.md`, `Prd.md`, `Architecture.md`, `Design.md`, `Debug.md`, `Security.md`, `Memory.md`, `Task.md`, `AGENTS.md`). `canonical_refs` stay root-relative, no existing cross-reference breaks, and no `docs/` migration runs in the same phase that freezes contracts. This also avoids compounding the existing `PRD.md`-versus-`Prd.md` naming inconsistency.

### Agent's Discretion

- The Python build backend / packaging tool is not chosen here; research and planning pick it once the toolchain is fixed, subject to D-42.
- Exact pinned versions of PostgreSQL, Pydantic, FastAPI and the frontend stack are deliberately not invented — research locks tested versions in dependency files.
- The internal module decomposition inside the contracts package, and the concrete shape of the static boundary scan (which AST nodes and forbidden-symbol list), are planning-level.
- Whether the health surface is one endpoint or a small set rendered together is planning-level, provided D-31's chain-proof content is present.

### Deferred Ideas (OUT OF SCOPE)

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

**Reviewed Todos (not folded):** None — `cross_reference_todos` matched zero pending todos at the time of this discussion.

</user_constraints>

## Summary

Phase 1 builds four interlocking things on a greenfield repository: (1) a frozen Pydantic-first contract package that exports JSON Schema draft 2020-12 and generates TypeScript types from that export; (2) a running local skeleton — FastAPI backend plus Next.js client — bound to loopback only, with startup-validated configuration, structured redacted logs, correlation IDs and local OpenTelemetry traces; (3) a portable, script-managed pinned PostgreSQL with a hand-written Alembic migration that applies *and* rolls back; and (4) a structural, from-the-first-commit enforcement of the research-only boundary via an AST import test and a static forbidden-symbol scan.

The single most consequential technical finding is that the toolchain is **`uv` 0.11.15** (already installed, was not mentioned in the phase brief) [VERIFIED: `uv --version` this session]. It makes D-42's "independent installable packages" straightforward via `[tool.uv.sources]` workspace wiring, pins the interpreter, and runs the whole gate fast enough that D-39's local-git-hook decision is workable without CI. The second is that **`next dev` defaults its hostname to `0.0.0.0`** [CITED: nextjs.org/docs/app/api-reference/cli/next] — it must be started with `-H 127.0.0.1` or it silently violates D-34/R-07. The third is that **`tzdata` must be an explicit dependency**: a clean `uv` venv on this Windows machine raised `ZoneInfoNotFoundError: 'No time zone found with key Europe/London'` (verbatim probe output in Assumptions Log A6), and Schema.md §1 line 10 requires IANA source timezones to be preserved [VERIFIED: Schema.md:10].

**Primary recommendation:** Build the contracts package first as its own `uv` workspace distribution (Pydantic-only + stdlib), then generate committed JSON Schema and uncommitted TypeScript from it, then wire the FastAPI backend and Next.js client against the generated artifacts, then stand up portable PostgreSQL via a provisioning script, then write the migration and the gate. Solve the flagged CI wording by shipping one `scripts/gate` command list that a local hook runs on commit *and* a present-but-inert `.github/workflows/ci.yml` invokes identically, so "runs in CI" becomes true the day a remote exists, and is honestly documented as *not yet executed in CI* until then (see **CI Reconciliation** below).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-no-trade-execution | The V1 boundary is structural: no order capability exists anywhere in the codebase. [VERIFIED: .planning/REQUIREMENTS.md:43] | D-37 implementation: an AST import/call scan over the whole source tree plus a dependency-manifest allowlist check, both runnable inside the single gate command. The scan and the allowlist must be *tests* (pytest), so they run in the gate and are re-runnable unchanged. Phase 1 additionally proves the negative by a test that the scan fails on a synthetic forbidden module. No API for orders is generated anywhere because the contract set (Schema.md §3-§10) contains no order entity. |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Contract definitions and validation (Schema.md §3-§10) | Contracts package (pure Python library) | — | D-01/D-03: Pydantic models are the single source of truth; the package imports only Pydantic + stdlib so it can be consumed by backend, TS generator and every later phase without dragging HTTP/DB deps. |
| JSON Schema export (draft 2020-12) | Contracts package (export script) | — | D-09: export depends only on the contracts package, never the web layer; generating via FastAPI OpenAPI was rejected. |
| TypeScript type generation | Build tooling (Node dev-dependency) | Contracts package (consumes its JSON output) | D-09/D-10: generator reads committed JSON Schema; output is build artifact, not committed. |
| Health surface (status, version, contract schema version, config hash, DB reachability) | API / Backend | Browser / Client (renders it) | D-31/D-43: the chain-proof content is computed server-side (needs DB + settings); the client only renders. |
| Configuration load + validation + hashing | API / Backend | — | D-15/D-27/D-36: settings must be resolved once at startup server-side; the client never sees secrets. |
| Loopback-only binding enforcement | API / Backend | — | D-34/R-07: enforced by startup validation in the server process; a client cannot enforce it. |
| Structured logging + correlation ID | API / Backend | — | D-30: correlation ID originates per request in the backend; structlog contextvars propagate it. |
| Local OpenTelemetry traces to disk | API / Backend | — | D-30: traces emitted by the server process to a local file, no collector. |
| Contract persistence (JSONB + promoted columns) | Database / Storage | API / Backend (writes) | D-07: promotion columns and JSONB document live in PostgreSQL; backend is the only writer. |
| Portable PostgreSQL provisioning + lifecycle | Local scripts (host tooling) | Database / Storage | D-29/D-33: binaries are repo-local and script-managed; nothing machine-wide. |
| Boundary enforcement (no-order-capability proof) | Build/quality gate (static analysis test) | — | D-37: a static source + manifest scan is the proof; it is a test so it runs in the gate. |
| Client skeleton rendering | Browser / Client | — | D-43: minimal Next.js app; imports generated TS types only, never Python. |

## Standard Stack

> **Provenance note for this section.** Version strings below were read this session from the official registries (PyPI JSON API `pypi.org/pypi/<pkg>/json`, npm `registry.npmjs.org`). Because the automated `package-legitimacy check` seam could not retrieve PyPI download counts and returned a `SUS` verdict for *every* package as an artifact (see **Package Legitimacy Audit**), registry-existence tags here are written `[CITED: pypi.org/...]` / `[CITED: registry.npmjs.org/...]` rather than the stricter `[VERIFIED: … registry]` form the provenance rules reserve for an `OK` verdict. Library *API behaviour* claims carry `[CITED: Context7 …]` where a Context7 fetch this session confirmed them.

### Core — Python (contracts + backend runtime)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.14.1 [CITED: pypi.org/pypi/pydantic/json] | Canonical contract models + validation (D-01) | The lock's chosen source of truth; v2 is the current line, and `model_json_schema` is the documented 2020-12 export path [CITED: Context7 pydantic — JSON schema generation]. |
| pydantic-settings | 2.15.0 [CITED: pypi.org/pypi/pydantic-settings/json] | Typed settings model, `GOLDMASTERS_` prefix, startup validation (D-15/D-27/D-36) | Official companion to Pydantic; `env_prefix`, `env_file`, `settings_customise_sources` all confirmed [CITED: Context7 pydantic-settings]. |
| fastapi | 0.143.0 [CITED: pypi.org/pypi/fastapi/json] | Backend HTTP surface + health endpoint (D-31) | `Architecture.md` §2 proposes FastAPI; current release; `lifespan` is the current startup hook and `@app.on_event` is explicitly deprecated [CITED: Context7 fastapi]. |
| uvicorn | 0.54.0 [CITED: pypi.org/pypi/uvicorn/json] | ASGI server bound to loopback (D-34) | Standard ASGI runner; `--host 127.0.0.1` is the loopback bind. |
| sqlalchemy | 2.1.4 [CITED: pypi.org/pypi/sqlalchemy/json] | DB engine + Core constructs for the migration (D-07) | `Architecture.md` §8 names Alembic alongside it; `postgresql+psycopg` is the current sync psycopg3 dialect string [CITED: Context7 sqlalchemy]. |
| alembic | 1.20.0 [CITED: pypi.org/pypi/alembic/json] | Hand-written apply/rollback migration (criterion 5) | Named by `Architecture.md` §8; `op.create_table`/`op.execute`, `upgrade head`/`downgrade base` confirmed [CITED: Context7 alembic]. |
| psycopg | 3.3.6 [CITED: pypi.org/pypi/psycopg/json] | PostgreSQL driver (sync) | psycopg3 is the current driver behind `postgresql+psycopg`; pure-Python path exists. |
| psycopg-binary | 3.3.6 [CITED: pypi.org/pypi/psycopg-binary/json] | Prebuilt driver wheel | Has a `cp314-cp314-win_amd64` wheel verified this session, avoiding a local libpq build on Windows. |
| structlog | 26.1.0 [CITED: pypi.org/pypi/structlog/json] | JSON log pipeline + correlation-ID contextvars (D-30/criterion 4) | `merge_contextvars` + `bind_contextvars` + `JSONRenderer` is the documented correlation-ID pattern [CITED: Context7 structlog]. |
| opentelemetry-sdk | 1.45.1 [CITED: pypi.org/pypi/opentelemetry-sdk/json] | Local trace pipeline (D-30) | Stable SDK; `ConsoleSpanExporter(out=<file>)` + `BatchSpanProcessor` writes local traces with no collector and no beta dependency [CITED: Context7 opentelemetry-python]. |
| opentelemetry-api | 1.45.1 [CITED: pypi.org/pypi/opentelemetry-api/json] | Tracing API surface | Paired with the SDK. |
| tzdata | 2026.5 [CITED: pypi.org/pypi/tzdata/json] | IANA tz database for `zoneinfo` on Windows | **Required**, not optional — see Assumptions Log A6: a clean venv on this machine cannot resolve `Europe/London` without it, and Schema.md:10 requires source timezones to be preserved. |
| pyyaml | 6.0.3 [CITED: pypi.org/pypi/pyyaml/json] | Read the versioned non-secret config document (D-15) | Standard YAML reader for the committed config artifact. |

### Supporting — Python tooling (dev)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uv | 0.11.15 [VERIFIED: `uv --version` this session] | Workspace, interpreter pinning, lockfile, runner (D-39/D-42) | Whole Python side: `uv sync`, `uv run`, `[tool.uv.sources]` workspace wiring. Already installed. |
| hatchling | 1.32.4 [CITED: pypi.org/pypi/hatchling/json] | Build backend for the installable packages (D-42) | Build backend for the contracts + api distributions. |
| ruff | 0.17.0 [CITED: pypi.org/pypi/ruff/json] | Format check + lint (D-38) | Gate steps 1-2. Already installed at 0.15.10 on PATH — pin 0.17.0 in the lockfile, don't rely on PATH. |
| mypy | 2.4.0 [CITED: pypi.org/pypi/mypy/json] | Strict type check (D-38) | Gate step 3. Note: mypy has moved to 2.x — a major-version jump from the 1.x line; pin exactly. |
| pytest | 9.1.1 [CITED: pypi.org/pypi/pytest/json] | Test runner (D-38) | Gate step 4. |
| pytest-cov | 7.1.0 [CITED: pypi.org/pypi/pytest-cov/json] | Coverage reporting | Optional; record coverage in gate output. |
| time-machine | 3.5.1 [CITED: pypi.org/pypi/time-machine/json] | Deterministic clock in tests | Needed so UUIDv7/timestamp conformance cases don't depend on wall clock. |

**Deliberately NOT used** (D-08 explicitly rejects them as the purity mechanism):
- `import-linter` 2.15, `deptry` 0.25.1, `flake8-tidy-imports` 4.12.0, `pytest-archon` 0.0.7 — all verified to exist, but D-08 requires a stdlib-`ast` test *inside* the contracts package with the allowlist living in the test. These may only ever *complement* that test, never replace it.

### Core — Node / TypeScript (client + type generation)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.4.0 [CITED: registry.npmjs.org/next/16.4.0] | Client skeleton (D-43) | Current major; requires Node ≥20.9.0 (`engines`); `next dev` host defaults to `0.0.0.0` → must pass `-H 127.0.0.1` [CITED: nextjs.org/docs/app/api-reference/cli/next]. |
| react | 19.3.0 [CITED: registry.npmjs.org/react/latest] | UI runtime | Peer of Next 16. |
| react-dom | 19.3.0 [CITED: registry.npmjs.org/react-dom/latest] | DOM renderer | Peer of Next 16. |
| typescript | 7.0.2 [CITED: registry.npmjs.org/typescript/latest] | TS compiler | Current major; ships native per-platform binaries (`@typescript/typescript-win32-x64`) — install tolerates this. `engines.node >= 16.20.0`. |
| json-schema-to-typescript | 16.0.0 [CITED: registry.npmjs.org/json-schema-to-typescript/latest] | Generate TS types from committed JSON Schema (D-09/D-10) | CLI `json2ts`; requires Node ≥22.19 (we have 24.21). **Read the limitations in Pitfalls — D-09/D-11 interactions are not free.** |

### Supporting — Node tooling

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @types/node | 26.6.5 [CITED: registry.npmjs.org/@types/node/latest] | Node typings | With TypeScript. |
| concurrently | 10.0.6 [CITED: registry.npmjs.org/concurrently/latest] | Run DB + backend together for the one stack command (D-33) | Only if the stack script is Node-driven; a PowerShell/shell script is the alternative. |
| wait-on | 9.5.1 [CITED: registry.npmjs.org/wait-on/latest] | Wait for loopback health before proceeding | In the stack script, so "bring up" truly waits. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uv` | pip + venv + pip-tools / Poetry | `uv` is already installed, is far faster, and its workspace feature directly satisfies D-42's independent-package requirement. Choosing pip would mean building the workspace wiring by hand. |
| hatchling | setuptools, pdm-backend, uv-build (`uv_build`) | `uv-build` 0.13.0 exists and pairs with `uv`, but is newer/less battle-tested. Hatchling is the safe default for a multi-distribution workspace. |
| `psycopg[binary]` | pure-python psycopg + local libpq | There is no libpq on this machine (no `psql`), so the binary wheel is the only no-build path. |
| `ConsoleSpanExporter(out=file)` | `opentelemetry-exporter-otlp-json-file` 0.66b1 (`FileSpanExporter`) | The beta exporter gives a purpose-built local file sink but is a **beta** dependency; the stable SDK already writes to any stream. Prefer stable unless the beta's JSON shape is required. |
| `json-schema-to-typescript` | `openapi-typescript` 7.13.0 | `openapi-typescript` would require generating via the FastAPI OpenAPI document — explicitly rejected by D-09 (couples export to HTTP). |

**Installation (shape, not yet locked — planning finalises pins in the lockfile):**

```bash
# Python workspace (D-42): contracts package + apps/api, wired via [tool.uv.sources]
uv sync --all-packages
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict .
uv run pytest

# Node (client + type generation)
npm install
npx json2ts -i "packages/contracts/schema/**/*.json" -o "apps/web/src/generated/" --no-format
```

**Version verification:** Every version in the tables above was read this session from the official registry (`pypi.org/pypi/<pkg>/json`) or `npm view <pkg> version`. `tzdata` moved from 2026.4 (earlier probe) to **2026.5** between probes — a reminder to pin exactly. Dates of publication were not separately recorded; the registry `version` field is the current release at research time (2026-10-13).

## Package Legitimacy Audit

> Run via the seam: `gsd_run query package-legitimacy check --ecosystem pypi <pkgs…>`.

**Result: the check returned `SUS` for every package submitted, with reasons `too-new` and/or `unknown-downloads` (and `no-repository` for structlog).** The checker could not obtain PyPI download counts and treated each package's newest release date as "too-new", so the verdicts are **artifacts of the checker's data access, not signals about the packages.** Each package below was therefore independently confirmed against its official documentation/Context7 and its known upstream repository. This is stated honestly rather than blindly recording `SUS`; the planner should treat these as approved but should still pin exact versions in the lockfile.

| Package | Registry | Upstream repo (independently confirmed) | Seam verdict | Disposition |
|---------|----------|------------------------------------------|--------------|-------------|
| pydantic | PyPI | github.com/pydantic/pydantic | SUS (artifact) | Approved — confirmed via Context7 official docs |
| pydantic-settings | PyPI | github.com/pydantic/pydantic-settings | SUS (artifact) | Approved — Context7 |
| fastapi | PyPI | github.com/fastapi/fastapi | SUS (artifact) | Approved — Context7 |
| uvicorn | PyPI | github.com/encode/uvicorn | SUS (artifact) | Approved — official docs |
| sqlalchemy | PyPI | github.com/sqlalchemy/sqlalchemy | SUS (artifact) | Approved — Context7 |
| alembic | PyPI | github.com/sqlalchemy/alembic | SUS (artifact) | Approved — Context7 |
| psycopg / psycopg-binary | PyPI | github.com/psycopg/psycopg | SUS (artifact) | Approved — official docs |
| structlog | PyPI | github.com/hynek/structlog | SUS (artifact, `no-repository`) | Approved — Context7; `no-repository` is a metadata gap, the repo exists |
| opentelemetry-sdk / -api | PyPI | github.com/open-telemetry/opentelemetry-python | SUS (artifact) | Approved — Context7 |
| opentelemetry-exporter-otlp-json-file | PyPI | github.com/open-telemetry/opentelemetry-python | SUS (artifact) | Approved but **beta (0.66b1)** — planning should prefer the stable `ConsoleSpanExporter(out=file)` path |
| tzdata | PyPI | github.com/python/tzdata | SUS (artifact) | Approved — **required** (probe A6) |
| pyyaml | PyPI | github.com/yaml/pyyaml | SUS (artifact) | Approved |
| hatchling | PyPI | github.com/pypa/hatch | SUS (artifact) | Approved — build backend |
| ruff | PyPI | github.com/astral-sh/ruff | SUS (artifact) | Approved |
| mypy | PyPI | github.com/python/mypy | SUS (artifact) | Approved — pin exactly (2.x major jump) |
| pytest / pytest-cov | PyPI | github.com/pytest-dev/pytest | SUS (artifact) | Approved |
| time-machine | PyPI | github.com/adamchainz/time-machine | SUS (artifact) | Approved |
| next | npm | github.com/vercel/next.js | n/a (npm) | Approved — official docs |
| react / react-dom | npm | github.com/facebook/react | n/a (npm) | Approved |
| typescript | npm | github.com/microsoft/TypeScript | n/a (npm) | Approved |
| json-schema-to-typescript | npm | github.com/bcherny/json-schema-to-typescript | n/a (npm) | Approved — README read this session |

**Packages removed due to `SLOP` verdict:** none.
**Packages flagged as suspicious `SUS`:** none on independent review — every `SUS` is a checker artifact, explained above.

**Postinstall check (Node.js):** verify `npm view <pkg> scripts.postinstall` before committing the client lockfile. Next/React/TypeScript are long-lived official packages; no third-party runtime dependency beyond these is proposed for Phase 1.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────────────────────────────────────┐
                         │  packages/contracts  (pure Python, Pydantic) │
                         │  models ──► model_json_schema()              │
                         │  D-01/D-03/D-08: stdlib + pydantic ONLY      │
                         └───────────────┬──────────────────────────────┘
                                         │
              ┌──────────────────────────┼───────────────────────────┐
              │ (import)                 │ (export script)           │ (AST purity test)
              ▼                          ▼                           ▼
   ┌────────────────────┐    ┌────────────────────────┐   ┌────────────────────────┐
   │  apps/api          │    │ packages/contracts/    │   │ test_import_purity.py  │
   │  FastAPI + settings│    │   schema/*.json        │   │ allowlist = {pydantic, │
   │  lifespan startup  │    │   (COMMITTED, D-10)    │   │  stdlib} — D-08        │
   │  loopback only     │    └───────────┬────────────┘   └────────────────────────┘
   │  structlog + OTel  │                │
   └─────┬───────┬──────┘                │ json2ts (dev-dep, build output, NOT committed)
         │       │                       ▼
         │       │            ┌────────────────────────┐
         │       │            │ apps/web/src/generated │
         │       │            │  *.ts types            │
         │       │            └───────────┬────────────┘
         │       │                        │ (import)
         │       │                        ▼
         │       │            ┌────────────────────────┐
         │       │            │ apps/web (Next.js)     │
         │       │            │  renders health surface│
         │       │            │  next dev -H 127.0.0.1 │
         │       │            └────────────────────────┘
         │       │
         │ (SQLAlchemy)                 (static scan, D-37)
         ▼                                       ▼
  ┌───────────────────────┐            ┌──────────────────────────────┐
  │ PostgreSQL (repo-local│            │ boundary test: forbidden     │
  │  portable binaries,   │            │  imports/calls + dependency  │
  │  D-29) working DB +   │            │  manifest allowlist          │
  │  throwaway test DB    │            └──────────────────────────────┘
  │  D-35                 │
  └───────────┬───────────┘
              │ alembic upgrade head / downgrade base
              ▼
  ┌───────────────────────┐
  │ hand-written migration│
  │ JSONB + promoted cols │
  │ D-07                  │
  └───────────────────────┘

  Entry: `scripts/stack` (D-33) ─► provisions/starts PG ─► starts api on 127.0.0.1
  Gate:  `scripts/gate`  (D-38) ─► format → lint → mypy → pytest → purity + boundary
                                   ^ run by local hook (D-39) AND by .github/workflows/ci.yml
```

Trace the primary use case: a developer runs `scripts/stack` → portable PG starts on loopback → Alembic applies the migration → FastAPI starts on `127.0.0.1` with validated settings and a recorded config hash → the client fetches the health surface over loopback → the surface renders backend status/version, contract schema version, config hash and DB reachability. Separately, `scripts/gate` runs the contract conformance suite, the AST purity test and the boundary scan.

### Recommended Project Structure

```
XauMaster/
├── packages/
│   └── contracts/                 # D-42: its own installable distribution
│       ├── pyproject.toml         # deps: pydantic + stdlib only (D-03/D-08)
│       ├── src/goldmasters_contracts/
│       │   ├── envelope.py        # Schema.md §3
│       │   ├── market.py          # Schema.md §4 (bar, quote)
│       │   ├── errors.py          # C-09 error contract (Schema.md §10)
│       │   ├── ids.py             # D-14 UUIDv7 prefix registry (validation only)
│       │   ├── enums.py           # Schema.md §2 + D-20 quality vocabulary
│       │   ├── precision.py       # D-19/D-24 table shape
│       │   ├── versions.py        # D-02/D-23 major.minor accept/reject
│       │   └── _schema/           # GenerateJsonSchema subclass (D-09/D-11)
│       ├── schema/*.json          # COMMITTED export (D-10)
│       └── tests/
│           ├── test_import_purity.py    # D-08 AST allowlist test
│           ├── conformance/             # D-06 golden suite
│           └── test_schema_export.py    # D-10 drift check
├── apps/
│   ├── api/                       # FastAPI, settings, observability, migration owner
│   │   ├── pyproject.toml         # depends on goldmasters-contracts
│   │   ├── src/goldmasters_api/{app,settings,logging,tracing,health}.py
│   │   └── migrations/            # alembic env.py + versions/
│   └── web/                       # Next.js skeleton (D-43)
│       ├── package.json
│       └── src/generated/         # json2ts output — build artifact, not committed (D-10)
├── src/goldmasters/               # D-41: graph,agents,data,domain,strategies,risk,
│   └── ...                        #      backtesting,persistence,observability (Phase 2+)
├── services/mt5_adapter/          # D-41 placeholder (Phase 2+)
├── tests/{unit,integration,contract,security,e2e}   # D-41
├── scripts/                       # stack script, gate script, PG provisioning
│   ├── gate                       # D-38 one command
│   ├── stack                      # D-33 one entry point
│   └── postgres/                  # D-29 provision/init/start/stop, pinned version
├── .githooks/pre-commit           # D-39 via core.hooksPath
├── .github/workflows/ci.yml       # present, inert until a remote exists (see CI Reconciliation)
├── .env.example                   # D-36 (no secrets)
└── (ten root docs stay here — D-44)
```

### Pattern 1: Purity-gated contracts package as a separate distribution (D-03/D-08/D-42)
**What:** The contract models live in their own distribution whose declared dependencies are only `pydantic` (+ stdlib). Purity is *enforced* by an AST test that walks every module and fails on any import outside an in-test allowlist.
**When to use:** Always, for this package — it is the mechanism, not a suggestion.
**Example (the AST test — stdlib only):**
```python
# packages/contracts/tests/test_import_purity.py
# Source: D-08 (CONTEXT.md); stdlib ast walk
import ast, pathlib

ALLOWED_TOP_LEVEL = {"pydantic", "typing", "decimal", "datetime", "enum",
                     "uuid", "re", "json", "zoneinfo", "collections", "abc",
                     "functools", "dataclasses", "__future__", "warnings",
                     "goldmasters_contracts"}  # self-package

def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots

def test_no_forbidden_imports():
    root = pathlib.Path(__file__).parents[1] / "src"
    offenders = {}
    for py in root.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        bad = _imported_roots(tree) - ALLOWED_TOP_LEVEL
        if bad:
            offenders[str(py)] = sorted(bad)
    assert not offenders, f"purity violation: {offenders}"
```

### Pattern 2: Decimal-as-string with a serialization-mode JSON Schema (D-11/D-19)
**What:** Prices cross JSON as strings validated against a decimal pattern; the exported schema must say `string`, which is the **serialization** JSON-schema mode.
**When to use:** Every monetary/price field.
**Example:**
```python
# Source: Context7 pydantic — JSON schema serialization mode + WithJsonSchema
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, PlainSerializer, WithJsonSchema

_PATTERN = r"^-?\d+(\.\d+)?$"   # form only: no exponent, no leading '+', no NaN/Inf

PriceStr = Annotated[
    Decimal,
    PlainSerializer(lambda d: format(d, "f"), return_type=str),
    WithJsonSchema({"type": "string", "pattern": _PATTERN}),
]

class _M(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
```
Emit the export with `model_json_schema(mode="serialization")`. **Note:** `mode="validation"` (the default) emits `anyOf: [{type: number}, {type: string}]` for `Decimal`; `mode="serialization"` emits `{type: string}` — D-11 requires the latter [CITED: Context7 pydantic].

### Pattern 3: One gate command, two invocation sites (D-38/D-39)
**What:** `scripts/gate` is the single ordered list (format → lint → mypy --strict → pytest → purity+boundary). The local hook runs a fast subset; `.github/workflows/ci.yml` runs the whole list.
**When to use:** Always; this is how the CI criterion is honoured without CI today.

### Pattern 4: Startup-validated settings resolved once and hashed (D-15/D-27/D-36)
**What:** A `pydantic-settings` model with `env_prefix="GOLDMASTERS_"`, required keys enforced, resolved into an immutable object inside FastAPI's `lifespan`, hashed once, and the hash exposed on the health surface.
**Why:** Guarantees the process refuses to start on missing/invalid config, and that a run cannot straddle two configurations.

### Pattern 5: Correlation ID via structlog contextvars (criterion 4)
**What:** A middleware binds `correlation_id` (UUID) with `bind_contextvars` at the start of each request; `merge_contextvars` is first in the processor chain so every JSON log line carries it; the same ID is attached to the OTel span and returned in the C-09 error body.
**Example:**
```python
# Source: Context7 structlog
import structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
)
```

### Anti-Patterns to Avoid
- **Generating the TS types through FastAPI's OpenAPI document** — rejected by D-09; couples the export to the HTTP layer.
- **Omitting `-H 127.0.0.1` from `next dev`** — the default host is `0.0.0.0`, a silent loopback violation.
- **Relying on the system Python's `tzdata`** — the system interpreter has it, a clean venv does not (probe A6). Declare it.
- **Using `import-linter`/`deptry` as *the* purity gate** — D-08 rejects declarative linters as the mechanism.
- **Committing generated TS types** — D-10: they are build output.
- **Using `@app.on_event`** — deprecated in FastAPI; use `lifespan`.
- **Setting `initdb -A trust` without thought** — the default auth is `trust`; document the choice (see Pitfalls).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema generation from Python types | A custom schema serializer | Pydantic `model_json_schema()` + a `GenerateJsonSchema` subclass | Handles `$defs`, `anyOf`, refs, formats, and dialect; a custom writer would drift from the models it must mirror. |
| Decimal→string JSON coercion | Manual `str()` in every model's serializer | `PlainSerializer` + `WithJsonSchema` (Pattern 2) | Applies uniformly and appears correctly in the exported schema; ad-hoc `json_encoders` doesn't fix the *schema* mode. |
| TS type generation from JSON Schema | A home-grown schema→TS translator | `json-schema-to-typescript` (`json2ts`) | Already handles `$defs`/`$ref`/`anyOf`/`const`/`enum`; a bespoke translator is a maintenance sink. (But respect its gaps — Pitfalls.) |
| Correlation-ID propagation | Passing an ID argument through every function | `structlog.contextvars.bind_contextvars` + `merge_contextvars` | Context-local storage propagates automatically through async call stacks. |
| Local trace export | A bespoke file writer for spans | `ConsoleSpanExporter(out=<file stream>)` (stable SDK) | The SDK already serialises spans to JSON; no collector needed. |
| PostgreSQL provisioning on Windows | A custom installer/downloader | Official EDB no-installer binaries + `initdb` via a script (D-29) | `initdb`/`pg_ctl` are the supported path; reinventing them is error-prone. |
| Windows tz database | A vendored tz file or hard-coded offsets | `tzdata` package | It is the maintained IANA database for `zoneinfo` on Windows. |
| Gate orchestration | A hand-rolled shell pipeline per developer | One `scripts/gate` list invoked from both the hook and CI | One list = one meaning of "green". |

**Key insight:** In this phase the "don't hand-roll" risk is concentrated in the *contracts → schema → types* chain and in *PostgreSQL on Windows*. Both have official, maintained paths; every hand-rolled shortcut reintroduces exactly the drift the phase exists to prevent.

## Common Pitfalls

### Pitfall 1: The exported TypeScript does not enforce what Pydantic enforces (D-09/D-11 trap)
**What goes wrong:** `json-schema-to-typescript` has **no `format` → TypeScript equivalent** — `date-time`, `uuid` and the Decimal-string `pattern` all collapse to plain `string`. Arrays using `prefixItems` degrade to `unknown[]`. `$dynamicRef`/`$anchor`/`unevaluated*` are unsupported. So the generated TS types are structurally looser than the Python contract.
**Why it happens:** TypeScript's type system cannot express regex/format constraints, and the tool does not emit branded types by default.
**How to avoid:** Treat the server (Pydantic) as the sole enforcement point; document that generated types are *shape* only. Where a client-side guarantee is wanted, map formats explicitly via the `formatTypes` option (e.g. `--formatTypes.date-time=Date`) or introduce branded string types deliberately. Never claim the TS types "validate" the contract.
**Warning signs:** A field typed `string` in TS that carries a `pattern` in JSON Schema; an array typed `unknown[]`.

### Pitfall 2: `next dev` binds `0.0.0.0` by default → loopback violation (D-34/R-07)
**What goes wrong:** The client dev server listens on all interfaces, so the health surface is reachable off-host.
**How to avoid:** Always run `next dev -H 127.0.0.1 -p 3000`; the same for the API's uvicorn `--host`. Add the negative test of D-34 on the backend and assert the launch flags in the stack script.
**Warning signs:** `next dev` output shows `Network: http://<lan-ip>:3000`.

### Pitfall 3: `tzdata` missing in a clean venv (Windows) — probe A6
**What goes wrong:** `ZoneInfo("Europe/London")` raises `ZoneInfoNotFoundError` even though the *system* Python resolves it, because the system interpreter has tzdata installed globally and a fresh venv does not.
**How to avoid:** Declare `tzdata` as a runtime dependency of whichever package touches IANA zones; add a test that resolves a named zone.
**Warning signs:** Works locally on the system interpreter, fails in `uv run`/CI.

### Pitfall 4: Pydantic's default Decimal pattern permits exponent notation (D-19)
**What goes wrong:** Pydantic's built-in `get_decimal_pattern()` builds a pattern that **allows `E`/`e` exponents**, which D-19 forbids.
**How to avoid:** Do not rely on the default; attach an explicit `pattern` via `WithJsonSchema` (Pattern 2) and/or a `field_validator` regex that rejects exponents, `NaN`, `Infinity` and a leading `+`. Add the D-06 rejecting cases for each.
**Warning signs:** `1E+2` validates as a price.

### Pitfall 5: `model_json_schema()` defaults to validation mode → `Decimal` becomes `anyOf[number,string]`
**What goes wrong:** The exported schema contradicts D-11 (which requires a string with a pattern).
**How to avoid:** Export with `mode="serialization"` and pin a drift test (D-10) so a regression fails the gate.

### Pitfall 6: `initdb` default auth is `trust`
**What goes wrong:** A repo-local cluster initialised without `-A` allows any local user to connect with no password.
**Why it happens:** PostgreSQL documents the `trust` default and warns "Do not use unless you trust all local users."
**How to avoid:** Pass an explicit auth method (`--auth=scram-sha-256` or `--auth-local=peer`-equivalent on Windows) and set a password via `--pwfile`; because the instance is loopback-only and repo-local, document the choice explicitly. Whether `initdb` needs elevation on Windows is **not stated in the docs** → Assumption A3.
**Warning signs:** `pg_hba.conf` containing `trust`.

### Pitfall 7: Alembic `downgrade` is an afterthought
**What goes wrong:** Criterion 5 requires rollback; a hand-written `upgrade()` with an empty `downgrade()` applies but cannot roll back.
**How to avoid:** Write `downgrade()` to drop exactly what `upgrade()` created (tables, indexes, enum types) in reverse order, and prove it with a test that runs `upgrade head` → `downgrade base` → `upgrade head` against the throwaway DB (D-35).
**Warning signs:** `alembic downgrade base` errors, or leaves objects behind.

### Pitfall 8: Mixed line endings / generated-file churn on Windows
**What goes wrong:** CRLF/LF churn in committed JSON Schema makes the D-10 drift check flap.
**How to avoid:** Add `.gitattributes` with `* text=auto` and force `*.json text eol=lf`; the drift check must compare canonicalised output (stable key order, trailing newline).

### Pitfall 9: Interpreter drift — `uv venv --python 3.14` picks a uv-managed 3.14.5, not the system 3.14.7
**What goes wrong:** A test passes under `python` and fails under `uv run`, or vice versa, because the two are different patch builds.
**How to avoid:** Pin the interpreter exactly in the uv config and record it; ensure the whole gate runs under one interpreter.
**Warning signs:** `uv python list` showing two 3.14 installs.

### Pitfall 10: `mypy` is now 2.x
**What goes wrong:** A requirement written as `mypy>=1` tracks a stale major; strict-mode flags may differ.
**How to avoid:** Pin `mypy==2.4.0` in the lockfile and run `mypy --strict` in the gate.

## Code Examples

Verified patterns from official sources / Context7. These are *shapes*; planning finalises exact naming.

### Startup-validated settings, loaded once and hashed (D-15/D-27/D-36)
```python
# Source: Context7 pydantic-settings; D-15/D-27/D-36
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GOLDMASTERS_", env_file=".env", extra="forbid", frozen=True
    )
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    database_url: str
    provider_api_key: SecretStr | None = None   # secret: env only, never in the config doc
    config_version: str = "1.0"
```

### Loopback-only startup validation (D-34)
```python
# Source: stdlib ipaddress; D-34
import ipaddress
def assert_loopback(host: str) -> None:
    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError(f"refusing to bind non-loopback address: {host!r}")
```

### FastAPI lifespan with resolved-once settings (Context7 fastapi)
```python
# Source: Context7 fastapi — lifespan (on_event is deprecated)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()                 # validated at startup; raises on bad config
    assert_loopback(settings.bind_host)
    app.state.settings = settings
    app.state.config_hash = hash_effective_config(settings)
    yield

app = FastAPI(lifespan=lifespan)
```

### Health surface proving the chain (D-31/D-43)
```python
# Source: D-31 — status, version, contract schema version, config hash, DB reachability
@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "contract_schema_version": CONTRACT_VERSION,      # D-02/D-23
        "config_hash": app.state.config_hash,             # D-27
        "database": probe_database(),                     # {"reachable": bool}
    }
```

### C-09 error mapping from Pydantic `ValidationError` (D-04/D-12 + Schema.md §10)
```python
# Source: Schema.md §10 [VERIFIED: Schema.md:224-237]; Context7 pydantic ValidationError.errors()
from fastapi.responses import JSONResponse
from pydantic import ValidationError

@app.exception_handler(ValidationError)
async def validation_handler(request, exc: ValidationError):
    errs = exc.errors()   # [{'type','loc','msg','input','url'}, ...]
    return JSONResponse(
        status_code=422,
        content={
            "code": "CONTRACT_VALIDATION_FAILED",       # stable, machine-readable
            "message": "Payload failed contract validation.",
            "retryable": False,
            "correlation_id": current_correlation_id(),
            "details": [{"loc": ".".join(map(str, e["loc"])), "type": e["type"]} for e in errs],
        },
    )
```
The C-09 shape is fixed: `{code, message, retryable, correlation_id, details}` [VERIFIED: Schema.md:224-237]. The **code vocabulary is the unselected gray area** — planning must settle it (see Open Questions).

### Hand-written Alembic migration that applies AND rolls back (D-07 + criterion 5)
```python
# Source: Context7 alembic — op.create_table / op.execute; D-07
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_contract_documents"
down_revision = None

def upgrade() -> None:
    op.create_table(
        "contract_document",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("run_id", sa.Text, nullable=True),
        sa.Column("agent_name", sa.Text, nullable=True),
        sa.Column("instrument_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("document", postgresql.JSONB, nullable=False),   # validated payload
    )
    op.create_index("ix_contract_document_run_id", "contract_document", ["run_id"])

def downgrade() -> None:
    op.drop_index("ix_contract_document_run_id", table_name="contract_document")
    op.drop_table("contract_document")
```
Gate proof: `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head` against the throwaway per-run DB (D-35).

### Boundary scan — forbidden order/broker capability (D-37, REQ-no-trade-execution)
```python
# Source: D-37 — static scan over the source tree + dependency allowlist
import ast, pathlib

FORBIDDEN_CALLS = {  # illustrative; planning fixes the exact list
    "order_send", "order_modify", "order_close", "position_close",
    "place_order", "submit_order", "cancel_order",
}
def scan_forbidden(tree: ast.AST) -> set[str]:
    hits = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name in FORBIDDEN_CALLS:
                hits.add(name)
    return hits
```
The dependency-manifest allowlist check runs alongside it; both are tests, so both run in the gate.

### Portable PostgreSQL provisioning shape (D-29)
```
scripts/postgres/
  VERSION            # e.g. "18.6"  (pinned; see Sources for the supported-major list)
  provision.ps1      # curl -L the EDB no-installer zip, record resolved URL + sha256
  init.ps1           # initdb -D <repo-local data dir> -U goldmasters -A scram-sha-256 --pwfile ...
  start.ps1          # pg_ctl -D <datadir> -o "-p 5432 -h 127.0.0.1" start
  stop.ps1           # pg_ctl -D <datadir> stop
```
Binaries and data directory are **repo-local and git-ignored**; nothing is machine-wide (D-29).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip` + `venv` + `pip-tools`/Poetry | `uv` workspaces with `[tool.uv.sources]` | uv 0.5+ workspace support (2024-2025) | Makes D-42's independent installable packages clean and fast; ideal for a contracts-package + api-package split. |
| FastAPI `@app.on_event("startup")` | `lifespan` async context manager | Deprecated in FastAPI | Must use `lifespan`; `on_event` carries an explicit `@deprecated` marker. |
| OpenAPI-first / FastAPI-generated schemas as contract source | Pydantic-first with direct `model_json_schema()` export | Pydantic v2 (`GenerateJsonSchema`, dialect support) | D-01/D-09 pick the direct export to avoid the HTTP coupling. |
| `mypy` 1.x | `mypy` 2.4.0 | 2.x major line | Pin exactly; strict-mode defaults may differ from 1.x. |
| JSON numbers for money | Decimal-as-string on the wire | — (D-11, deliberately chosen) | Avoids JS float rounding; cost is explicit parsing + JSONB casts. |
| Windows app installers / machine services for PostgreSQL | Portable no-installer binaries, script-managed per repo | EDB zip archives | D-29; nothing machine-wide. |
| `zoneinfo` relying on OS tz data | Explicit `tzdata` dependency | PEP 615 / Windows gap | Required on Windows; probe A6. |

**Deprecated/outdated:**
- FastAPI `@app.on_event` — use `lifespan`.
- `json_encoders` in Pydantic v2 — use `PlainSerializer`/`WithJsonSchema`; `json_encoders` does not affect the generated schema mode.
- `suspend`, `on_event`-style hooks, and pre-1.0 `opentelemetry-sdk` exporters — use `ConsoleSpanExporter`/`BatchSpanProcessor`.
- PostgreSQL ≤13 — unsupported; pin a supported major (see Sources).

## Assumptions Log

> Claims tagged `[ASSUMED]` — the planner and discuss-phase should confirm these before they become locked decisions.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `httpx` (a transitive FastAPI/TestClient dependency) works on Python 3.14. | Standard Stack | `httpx` 0.28.1 declares `requires_python >=3.8` but ships **no `Programming Language :: Python :: 3.14` classifier**; per the absent-evidence rule this is unverified. If it fails on 3.14, `TestClient`-based API tests break. Mitigation: verify at first `uv sync`; `httpx` has no native wheel dependency, so a pure-Python 3.14 install is likely fine. |
| A2 | EDB's no-installer PostgreSQL binaries run on this Windows **10** machine. | Environment Availability / D-29 | EDB's platform table lists PG 18 as tested on Windows **2025/2022** only, with a note that installers "can generally be expected to run on other comparable versions, for example, desktop releases of Windows". This machine is Windows 10 22H2. Expectation, not certification. **Positive falsification attempt required**: provision and `initdb` on this machine before the plan depends on it. |
| A3 | `initdb`/`pg_ctl` run without elevation on Windows. | Pitfall 6 / D-29 | The PostgreSQL docs state `initdb` refuses to run as *root* (Unix wording); Windows admin-privilege behaviour is **not documented**. If elevation is required, the "one stack command" experience is degraded (UAC prompt) — must be probed. |
| A4 | The EDB download file IDs / URLs are stable enough for a script that also records the resolved URL + sha256 at provision time. | Standard Stack / Sources | The EDB file IDs change per version and are not documented as stable. Mitigation is built into the script (record resolved URL + hash); if the URL moves, the script must be updated. |
| A5 | `json-schema-to-typescript`'s experimental `--imports` cross-file `$ref` support is sufficient for one-document-per-contract generation. | Pitfall 1 | `--imports` is marked **experimental**, requires an output directory, and is incompatible with `--cwd`. If it proves unusable, generate types from a single bundled schema or accept duplicated per-file types. |
| A6 | `tzdata` is required (verified by probe, but listed here because the *deliverable* assumption is that research adds it). | Standard Stack | **Actually verified**, not assumed: clean venv raised `ZoneInfoNotFoundError: 'No time zone found with key Europe/London'` and `ModuleNotFoundError: No module named 'tzdata'`. Listed to make explicit that the plan MUST declare `tzdata`. |
| A7 | PostgreSQL 18.6 is the right pin. | Environment Availability | 18 is the newest supported major; 19 was in beta at research time. Pinning 18.6 avoids a beta. If stability risk is judged high, 17.11 is the conservative alternate. |
| A8 | A Node-driven stack script (`concurrently` + `wait-on`) is acceptable on PowerShell-first Windows, or a PowerShell script is preferred. | Recommended Project Structure | Not decided; both work. Planning should pick one and document it (D-33 requires *one* documented entry point). |

## Open Questions

1. **C-09 error-code vocabulary and minting rule** (unselected gray area; criterion 1 needs it as versioned code)
   - What we know: the envelope is fixed — `{code, message, retryable, correlation_id, details}` [VERIFIED: Schema.md:224-237]; `retryable` is determined by code, not model judgement.
   - What's unclear: the actual code list and the rule for adding codes; whether codes are a closed enum or a namespaced string pattern.
   - Recommendation: define a closed `ErrorCode` enum in the contracts package as part of the frozen version (bumping minor to add codes per D-23), with `retryable` as a per-code property, and pin conformance cases for the codes Phase 1 itself can emit (`CONTRACT_VALIDATION_FAILED`, `UNKNOWN_CONTRACT_MAJOR`, `CONFIG_INVALID`, `UNSUPPORTED_*`). Flag for user confirmation since it is a published contract.

2. **Migration lifecycle mechanics** (unselected gray area; criterion 5)
   - What we know: Alembic is the tool (Architecture.md §8); the migration must apply and roll back; two DB roles exist (D-35).
   - What's unclear: how the same migration is applied to the persistent working DB vs. the throwaway per-run test DB, and where the test DB is created/dropped.
   - Recommendation: `alembic upgrade head` against the working DB via the stack script; a pytest fixture that creates a per-run database, runs `upgrade head → downgrade base → upgrade head`, asserts schema state, then drops it. Pin Alembic ≥1.20.

3. **Redaction rules + correlation-ID origin** (unselected gray area; criterion 4)
   - What we know: transport is structlog + OTel-to-disk (D-30); Schema.md §10 forbids secrets/SQL/stack traces/paths/tokens in `message`, and §1 line 18 forbids secrets in logs/traces.
   - What's unclear: exactly which fields are redacted, the redaction marker, and where the correlation ID is minted (per HTTP request; per background run?).
   - Recommendation: mint a UUID correlation ID in request middleware, bind via `bind_contextvars`, propagate to spans and to the C-09 body; add a structlog processor with a redaction allowlist/denylist and a test asserting a known secret never appears in a captured log line.

4. **Loopback host representation**
   - What we know: D-34 requires a non-loopback bind to be rejected.
   - What's unclear: whether `localhost` (a name) is accepted alongside `127.0.0.1`/`::1`, and how IPv6 loopback is treated.
   - Recommendation: accept `127.0.0.1` and `::1` explicitly; resolve `localhost` via `ipaddress`/stdlib and reject everything else.

5. **Where the config hash is computed and what it covers**
   - What we know: D-15/D-27 require the hash recorded on every run/decision.
   - What's unclear: the exact canonicalisation (which fields, ordering, secrets excluded).
   - Recommendation: hash the deterministic JSON serialisation of the resolved non-secret settings object with sorted keys; exclude `SecretStr` fields; version the hash algorithm alongside `config_version`.

## Environment Availability

> Probed directly on this machine this session.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything (Python) | ✓ | 3.14.7 (system, `C:\Users\wasim\AppData\Local\Programs\Python\Python314`) | uv-managed 3.14.5 also present — must be reconciled (Pitfall 9) |
| uv | Workspace, lockfile, runner (D-42) | ✓ | 0.11.15 | pip + venv (slower, loses workspace feature) |
| Node.js | Client + TS generation | ✓ | v24.21.0 | — |
| npm | Node deps | ✓ | 11.19.0 | — |
| git | Hook, commits (D-39) | ✓ | 2.55.0.windows.3 | — |
| PowerShell | Scripts on Windows | ✓ | 7.6.6 | — |
| ruff | Gate (format/lint) | ✓ | 0.15.10 on PATH (pin 0.17.0 in lockfile) | — |
| mypy | Gate (strict typing) | ✗ | — | Install via `uv sync` (pin 2.4.0) — **not on PATH** |
| pytest | Gate (tests) | ✗ | — | Install via `uv sync` (pin 9.1.1) — **not on PATH** |
| PostgreSQL binaries | DB (D-29) | ✗ | — | Provision portable EDB no-installer bundle (D-29) — **the required path** |
| psql | DB admin | ✗ | — | `pg_ctl`/`initdb` from the portable bundle |
| Docker | — | ✗ | — | **Not used, and not usable**: `nektos/act` (local CI) requires Docker |
| ollama.exe | DR-13 / Phase 4 | ✓ (client) | client 0.34.4 (server not running) | **Phase 1 must not depend on it** (D-32) |
| Python `uuid7` | ID scheme (D-14) | ✓ | stdlib (`uuid.uuid7()` works) | — |
| `tzdata` (as a *venv* dep) | IANA zones | ✗ in clean venv | — | Declare `tzdata` explicitly (probe A6) |

**Missing dependencies with no fallback:**
- **PostgreSQL** — must be provisioned from the portable bundle; there is no `psql`, no service, and no Docker. This is the single blocking environment item for criterion 5.
- **`mypy` and `pytest`** — not installed system-wide; the plan must install them into the uv-managed environment (the gate cannot rely on PATH).

**Missing dependencies with fallback:**
- **Docker** — absent, but not needed; D-29/D-30 avoid containers entirely. Consequence: any CI tool that emulates GitHub Actions locally via Docker (`act`) is **not available** (see CI Reconciliation).
- **Ollama server** — client present, server not running; irrelevant to Phase 1 by D-32 (a test must prove the skeleton runs without it).

## Validation Architecture

> `workflow.nyquist_validation` is not set to `false` in `.planning/config.json` (treated as enabled) — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 [CITED: pypi.org/pypi/pytest/json] (+ pytest-cov 7.1.0, time-machine 3.5.1) |
| Config file | none yet — Wave 0 creates `pyproject.toml` `[tool.pytest.ini_options]` and per-package test config |
| Quick run command | `uv run pytest -q --no-header -x` |
| Full suite command | `uv run pytest` (plus `ruff format --check`, `ruff check`, `mypy --strict`) via `scripts/gate` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-no-trade-execution | No forbidden order/broker import or call anywhere; dependency manifest matches allowlist | unit (static AST scan) | `uv run pytest tests/security/test_boundary_scan.py -x` | ❌ Wave 0 |
| REQ-no-trade-execution | Scan *fails* on a synthetic forbidden module (proves the scan has teeth) | unit (meta-test) | `uv run pytest tests/security/test_boundary_scan_negative.py -x` | ❌ Wave 0 |
| (criterion 1) | Every Schema.md contract validates accepted + rejects mutations | contract (golden suite) | `uv run pytest tests/contract -x` | ❌ Wave 0 |
| (criterion 1) | Purity: no import outside the Pydantic+stdlib allowlist | unit (AST) | `uv run pytest packages/contracts/tests/test_import_purity.py -x` | ❌ Wave 0 |
| (criterion 1) | Committed JSON Schema matches regenerated export (drift) | unit | `uv run pytest packages/contracts/tests/test_schema_export.py -x` | ❌ Wave 0 |
| (criterion 2) | Health endpoint answers on loopback with chain content | integration | `uv run pytest tests/integration/test_health.py -x` | ❌ Wave 0 |
| (criterion 2) | Non-loopback bind is rejected; loopback bind starts | integration (negative + acceptance) | `uv run pytest tests/integration/test_loopback_bind.py -x` | ❌ Wave 0 |
| (criterion 3) | Boundary test runs (green) | unit | (same as REQ-no-trade-execution above) | ❌ Wave 0 |
| (criterion 4) | Missing/invalid config stops startup naming the key | unit | `uv run pytest tests/unit/test_settings_startup.py -x` | ❌ Wave 0 |
| (criterion 4) | `.env.example` enumerates every required key, holds no secret | unit (two tests) | `uv run pytest tests/unit/test_env_example.py -x` | ❌ Wave 0 |
| (criterion 4) | Log line is JSON, carries correlation ID, redacts a known secret | unit | `uv run pytest tests/unit/test_logging_redaction.py -x` | ❌ Wave 0 |
| (criterion 5) | Migration applies, rolls back, re-applies against throwaway DB | integration | `uv run pytest tests/integration/test_migration_roundtrip.py -x` | ❌ Wave 0 |
| (criterion 5) | Accepted fixtures round-trip through PostgreSQL unchanged | integration | `uv run pytest tests/integration/test_persistence_roundtrip.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** fast subset via hook — `ruff format --check` + `ruff check` + `mypy --strict` over changed files (D-40).
- **Per wave merge:** `scripts/gate` (full: format, lint, mypy, full pytest, purity + boundary).
- **Phase gate:** full `scripts/gate` green, `alembic upgrade head → downgrade base → upgrade head` green, and the recorded command list + results captured as evidence before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `pyproject.toml` (`[tool.pytest.ini_options]`, mypy strict, ruff config) — none exists.
- [ ] `tests/conftest.py` — throwaway-DB fixture (create/drop per run, D-35).
- [ ] `tests/contract/` — golden conformance fixtures for every Schema.md contract (D-06).
- [ ] `tests/security/` — boundary scan + negative meta-test (D-37).
- [ ] `packages/contracts/tests/test_import_purity.py` — purity AST test (D-08).
- [ ] Framework install: `uv sync` (adds pytest, mypy, time-machine, etc.).
- [ ] `.env.example` and its two tests (D-36).

## Security Domain

> `security_enforcement` is not set to `false` — section included. Phase 1 is not an auth/session system; its security surface is input validation, secret handling, local-boundary enforcement and the signals-only guarantee.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in Phase 1 (loopback-only local skeleton). |
| V3 Session Management | no | No sessions in Phase 1. |
| V4 Access Control | partial | The *access-control*-shaped control here is the **signals-only boundary** (D-37) — no order capability exists — and loopback-only binding (D-34). |
| V5 Input Validation | yes | Pydantic v2 with `strict=True`, `extra="forbid"`, closed enums, `Decimal`-string patterns (D-04/D-11/D-12/D-19). |
| V6 Cryptography | no (minimal) | No crypto is hand-rolled. Secrets are held as `SecretStr` and read only from `GOLDMASTERS_` env vars (D-15); nothing is encrypted at rest in Phase 1. **Never hand-roll crypto** — if any is later needed, use a vetted library. |
| V7 Error Handling & Logging | yes | C-09 error contract (Schema.md §10): sanitized `message`, redacted `details`, `retryable` by code; structured redacted logs (criterion 4). |
| V8 Data Protection | yes | No secrets in logs/traces/schemas/examples (Schema.md §1 line 18); `.env.example` must contain no real secret (D-36). |
| V14 Configuration | yes | Startup-validated typed settings; missing/invalid config fails startup, naming the key (D-36). |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/untrusted external payload accepted as valid | Tampering | Pydantic strict validation + `extra="forbid"` + conformance reject-cases (D-04/D-06/D-12). |
| Secret leaked into logs/traces/error message | Information Disclosure | `SecretStr`; redaction processor; Schema.md §10 forbids secrets/SQL/stack traces/paths/tokens in `message`; test asserting a known secret never appears in a captured log. |
| Service reachable off-host (dev convenience) | Information Disclosure / Elevation | Loopback-only startup validation with negative + acceptance tests (D-34); `next dev -H 127.0.0.1` (Pitfall 2). |
| Local PostgreSQL cluster open to any local user (`trust` auth) | Elevation | Explicit auth method on `initdb` + password via `--pwfile` (Pitfall 6). |
| Silent addition of a trading capability | Elevation / Tampering | Static forbidden-import/call scan + dependency-manifest allowlist, both as tests (D-37). |
| Precision loss / value tampering on the wire | Tampering | Decimal-as-string with pattern (D-11/D-19). |
| SQL injection in the migration/persistence layer | Tampering | SQLAlchemy Core / parameterised `op.execute`; never string-concatenated SQL. |
| Dependency supply-chain (slopsquatting) | Tampering | Package Legitimacy Audit above; pin exact versions in the lockfile. |

## CI Reconciliation (Flagged Open Item)

Phase 1 success criteria 3 and 5 state the boundary test and the check suite *run in CI*. **Verified on this machine: there is no git remote, no `.github/` directory, no CI provider, and Docker is not installed.** D-39 therefore chose a local git hook (`core.hooksPath`) plus one gate command. The criterion is **not met as literally written today** and must not be silently marked met. Recommended resolution:

1. **One command list, two invocation sites.** Create `scripts/gate` as the single ordered list (D-38): `ruff format --check` → `ruff check` → `mypy --strict` → `uv run pytest` (which includes the contracts purity test and the boundary scan). The local hook runs a fast subset; the *same script* is what a CI job runs.
2. **Track a local hook** via `git config core.hooksPath .githooks` with a checked-in `.githooks/pre-commit` that calls the fast subset (D-39/D-40).
3. **Add `.github/workflows/ci.yml` that invokes `scripts/gate`** — present from the first commit but **inert until a remote exists**. The day a remote is pushed, "runs in CI" becomes true with no change to the command list.
4. **Record the exact commands and their results** as Phase 1 evidence (criterion 5's wording), executed locally via `scripts/gate`, with an explicit note that the CI job has not yet executed because no remote exists.
5. **State the reconciliation honestly** in the phase summary and in the plan: criteria 3 and 5 are satisfied *structurally* (the runner exists, is a single reproducible command, and a CI workflow invokes it identically) but the CI *execution* is pending a remote — a future-remote-adoptable local runner, exactly as CONTEXT.md's flagged item allows.

**Explicitly NOT viable:** `nektos/act` (run GitHub Actions locally) **requires Docker**, which is not installed (and D-29 avoids installing it). Do not propose `act` as the CI-substitute. A `pre-commit` framework hook (`.pre-commit-config.yaml`) was not chosen by D-39; the tracked `core.hooksPath` hook is the decision.

## Sources

### Primary (HIGH confidence)
- Context7 fetches this session: uv workspaces / `tool.uv.sources`; Pydantic JSON Schema generation (validation vs serialization mode, `GenerateJsonSchema`, `get_decimal_pattern`, `WithJsonSchema`); pydantic-settings (`env_prefix`, `env_file`, `settings_customise_sources`, `SecretStr`); FastAPI (`lifespan`, exception handlers, `on_event` deprecation); Alembic (`op.create_table`, `op.execute`, `upgrade head`/`downgrade base`); SQLAlchemy 2.0 (`postgresql+psycopg`, `JSONB`); OpenTelemetry Python (`ConsoleSpanExporter`, `TracerProvider`, `BatchSpanProcessor`); structlog (`merge_contextvars`, `bind_contextvars`, `JSONRenderer`); Next.js CLI (`-H/--hostname` default `0.0.0.0`).
- Schema.md (read this session): §1 line 10 (timezone preservation), §2 enums, §3 envelope, §10 error contract [VERIFIED: Schema.md:224-237], §11, §12.
- Official registries read this session: `pypi.org/pypi/<pkg>/json` (all Python versions in Standard Stack); `registry.npmjs.org` / `npm view` (TypeScript 7.0.2, Next 16.4.0, React 19.3.0, json-schema-to-typescript 16.0.0).
- Official docs read this session: postgresql.org/support/versioning (supported majors: 18.6, 17.11, 16.15, 15.19, 14.24; 19 Beta); postgresql.org/download/windows; enterprisedb.com/download-postgresql-binaries; postgresql.org/docs/18/app-initdb.html; github.com/bcherny/json-schema-to-typescript README.
- Local probes this session: `uv --version` 0.11.15; `python --version` 3.14.7; `node --version` v24.21.0; `uuid.uuid7()` works; clean-venv `tzdata` failure (A6); `docker`/`psql` not found; `git remote -v` empty.

### Secondary (MEDIUM confidence)
- Package legitimacy audit rationale (upstream repos confirmed by name; the seam's `SUS` verdicts explained as checker artifacts).

### Tertiary (LOW confidence)
- Windows-10 runnability of EDB PG 18 binaries and Windows elevation behaviour of `initdb` — **`[ASSUMED]`**, require a falsification probe (A2/A3).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version read from the official registry this session; the only caveats are the `tzdata` requirement (verified by probe) and `httpx` on 3.14 (A1, needs a `uv sync` check).
- Architecture: HIGH — the contract→schema→types and settings/lifespan/health patterns are confirmed against Context7 docs and the locked decisions.
- Pitfalls: MEDIUM-HIGH — the `next dev` host default, Pydantic Decimal-serialization-mode behaviour, Decimal-pattern exponent allowance, `json-schema-to-typescript` limitations, and the `tzdata` gap are all verified; the Windows-specific PostgreSQL behaviours (A2/A3) remain assumptions needing a probe.
- Environment: HIGH for what is present/absent (directly probed); the PostgreSQL provisioning *runnability* is the remaining unknown.

**Research date:** 2026-10-13
**Valid until:** ~2026-11-12 (30 days; the stack is stable, but versions move — re-check pins at plan execution, especially `tzdata`, `mypy` 2.x, and the Node toolchain).

