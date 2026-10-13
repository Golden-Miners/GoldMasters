# Phase 1: Contracts and Foundation - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 55 (new/modified)
**Analogs found:** 0 / 55 — **the repository is greenfield; no source-code analog exists for any file.**

> **This phase has no codebase to copy from.** Verified on disk this session:
> `git ls-files` returns 26 files, every one of them a `.planning/**` Markdown/YAML
> artifact or `ingest-manifest.yaml`. `git status` shows the ten root documents
> (`AGENTS.md`, `Architecture.md`, `Debug.md`, `Design.md`, `Memory.md`, `Prd.md`,
> `Rules.md`, `Schema.md`, `Security.md`, `Task.md`) as untracked (`??`) — they
> exist on disk and are intended to be committed (D-44), but they are **documents,
> not code**. There is no `src/`, `apps/`, `packages/`, `tests/`, `pyproject.toml`,
> `.env.example`, `.githooks/`, `.github/`, or lockfile of any kind.
>
> Therefore the column the format calls "Closest Analog" is, for every file,
> **"none — greenfield"**, and the pattern source for each file is a *documentary*
> source of truth: a `Schema.md` contract section, an `Architecture.md` section,
> or a verified code example in `01-RESEARCH.md`. This file records that honestly
> rather than inventing false positives. Later phases (2-8) will have real analogs
> — Phase 1 is the phase that *creates* them.

---

## File Classification

Because no file has a code analog, "Match Quality" is reported against the nearest
**documentary** source rather than a source file. Quality values:

- `contract` — the file's pattern is a normative `Schema.md` section (must be followed exactly).
- `layout` — the file's pattern is `Architecture.md` §7/§8 (a proposal, adapted by D-41).
- `research-example` — the file's pattern is a verified code example in `01-RESEARCH.md`.
- `decision-only` — no documentary pattern exists; the file's shape comes from a CONTEXT.md decision.

### A. Contracts package — `packages/contracts/` (D-01/D-03/D-08/D-42)

| New File | Role | Data Flow | Closest Analog | Documentary Pattern Source | Quality |
|----------|------|-----------|----------------|----------------------------|---------|
| `packages/contracts/pyproject.toml` | config (packaging) | n/a | none — greenfield | RESEARCH.md:315-316, 332-334; D-42 | decision-only |
| `packages/contracts/src/goldmasters_contracts/__init__.py` | util (barrel) | transform | none — greenfield | RESEARCH.md:317 | decision-only |
| `.../goldmasters_contracts/envelope.py` | model | transform | none — greenfield | `Schema.md` §3 (lines 69-83) | contract |
| `.../goldmasters_contracts/market.py` | model | transform | none — greenfield | `Schema.md` §4 (lines 88-119) | contract |
| `.../goldmasters_contracts/decision.py` | model | transform | none — greenfield | `Schema.md` §6 (lines 140-166) | contract |
| `.../goldmasters_contracts/news.py` | model | transform | none — greenfield | `Schema.md` §7 (lines 168-180) | contract |
| `.../goldmasters_contracts/sentiment.py` | model | transform | none — greenfield | `Schema.md` §7 (lines 182-189) | contract |
| `.../goldmasters_contracts/backtest.py` | model | transform | none — greenfield | `Schema.md` §9 (lines 209-220) | contract |
| `.../goldmasters_contracts/journal.py` | model | transform | none — greenfield | `Schema.md` §6 (immutability, line 166) | contract |
| `.../goldmasters_contracts/errors.py` | model | transform | none — greenfield | `Schema.md` §10 (lines 222-237) | contract |
| `.../goldmasters_contracts/ids.py` | util (validation-only) | transform | none — greenfield | `Schema.md` §11 (line 245); D-14/D-21 | decision-only |
| `.../goldmasters_contracts/enums.py` | model (enums) | transform | none — greenfield | `Schema.md` §2 (lines 20-65); D-16/D-20 | contract |
| `.../goldmasters_contracts/precision.py` | model | CRUD (table shape) | none — greenfield | D-19/D-24/D-26; `Schema.md` §4 line 12 | decision-only |
| `.../goldmasters_contracts/versions.py` | util | transform | none — greenfield | D-02/D-05/D-23 | decision-only |
| `.../goldmasters_contracts/_schema/__init__.py` | util (schema export) | transform | none — greenfield | RESEARCH.md:389-410 (Pattern 2) | research-example |
| `packages/contracts/schema/*.json` | config (committed artifact) | transform | none — greenfield | D-10; RESEARCH.md:326 | decision-only |
| `packages/contracts/tests/test_import_purity.py` | test (AST gate) | batch | none — greenfield | RESEARCH.md:357-386 (Pattern 1, verbatim) | research-example |
| `packages/contracts/tests/test_schema_export.py` | test (drift) | batch | none — greenfield | D-10; RESEARCH.md:330 | decision-only |
| `packages/contracts/tests/conformance/*.json` | test fixtures | batch | none — greenfield | D-06; `Schema.md` §3/§4/§10 | contract |

### B. Backend — `apps/api/` (D-31/D-32/D-34/D-36)

| New File | Role | Data Flow | Closest Analog | Documentary Pattern Source | Quality |
|----------|------|-----------|----------------|----------------------------|---------|
| `apps/api/pyproject.toml` | config (packaging) | n/a | none — greenfield | RESEARCH.md:333; D-42 | decision-only |
| `apps/api/src/goldmasters_api/__init__.py` | util (barrel) | transform | none — greenfield | RESEARCH.md:334 | decision-only |
| `.../goldmasters_api/app.py` | controller (app factory) | request-response | none — greenfield | RESEARCH.md:541-556 (lifespan) | research-example |
| `.../goldmasters_api/settings.py` | config | transform | none — greenfield | RESEARCH.md:515-530 (Pattern 4); D-15/D-27/D-36 | research-example |
| `.../goldmasters_api/logging.py` | middleware (observability) | event-driven | none — greenfield | RESEARCH.md:420-434 (Pattern 5) | research-example |
| `.../goldmasters_api/tracing.py` | provider (observability) | event-driven | none — greenfield | RESEARCH.md:452 (don't-hand-roll row); D-30 | research-example |
| `.../goldmasters_api/health.py` | controller (route) | request-response | none — greenfield | RESEARCH.md:558-591 (health + C-09 handler) | research-example |
| `apps/api/migrations/env.py` | config (migration) | file-I/O | none — greenfield | `Architecture.md` §8 (line 224); D-07 | layout |
| `apps/api/migrations/versions/0001_contract_document.py` | migration | batch | none — greenfield | RESEARCH.md:594-622 (verbatim) | research-example |

### C. Client — `apps/web/` (D-34/D-43)

| New File | Role | Data Flow | Closest Analog | Documentary Pattern Source | Quality |
|----------|------|-----------|----------------|----------------------------|---------|
| `apps/web/package.json` | config | n/a | none — greenfield | RESEARCH.md:336-338; D-43 | decision-only |
| `apps/web/src/app/page.tsx` (+ layout/config) | component (page) | request-response | none — greenfield | D-43; `Design.md` (Phase 7 owns detail) | decision-only |
| `apps/web/src/generated/*.ts` | build output (NOT committed) | transform | none — greenfield | D-10; RESEARCH.md:337-338 | decision-only |

### D. Tooling, scripts and root config (D-29/D-33/D-38/D-39)

| New File | Role | Data Flow | Closest Analog | Documentary Pattern Source | Quality |
|----------|------|-----------|----------------|----------------------------|---------|
| `pyproject.toml` (workspace root) | config | n/a | none — greenfield | RESEARCH.md:200-208, 313 | decision-only |
| `scripts/gate` | util (tooling) | batch | none — greenfield | D-38; RESEARCH.md:412-414 (Pattern 3) | decision-only |
| `scripts/stack` | util (tooling) | batch | none — greenfield | D-33; RESEARCH.md:303 | decision-only |
| `scripts/postgres/VERSION` | config | n/a | none — greenfield | RESEARCH.md:646-653; D-29 | research-example |
| `scripts/postgres/provision.ps1` | util (tooling) | file-I/O | none — greenfield | RESEARCH.md:649 | research-example |
| `scripts/postgres/init.ps1` | util (tooling) | file-I/O | none — greenfield | RESEARCH.md:650 (Pitfall 6) | research-example |
| `scripts/postgres/start.ps1` / `stop.ps1` | util (tooling) | file-I/O | none — greenfield | RESEARCH.md:651-652 | research-example |
| `.githooks/pre-commit` | util (tooling) | batch | none — greenfield | D-39/D-40; RESEARCH.md:824 | decision-only |
| `.github/workflows/ci.yml` | config (inert until remote) | batch | none — greenfield | D-39; RESEARCH.md:825 | decision-only |
| `.env.example` | config | n/a | none — greenfield | D-36; `Schema.md` §11 line 244 | contract |
| `.gitattributes` | config | n/a | none — greenfield | RESEARCH.md:498-500 (Pitfall 8) | research-example |
| `.gitignore` | config | n/a | none — greenfield | D-29 (repo-local PG ignored) | decision-only |

### E. Top-level tests — `tests/` (D-06/D-07/D-35/D-37)

| New File | Role | Data Flow | Closest Analog | Documentary Pattern Source | Quality |
|----------|------|-----------|----------------|----------------------------|---------|
| `tests/conftest.py` | test (fixture) | file-I/O (per-run DB) | none — greenfield | D-35; RESEARCH.md:699 | decision-only |
| `tests/unit/test_settings_startup.py` | test | batch | none — greenfield | D-36; RESEARCH.md:769 | decision-only |
| `tests/unit/test_env_example.py` | test | batch | none — greenfield | D-36; RESEARCH.md:770 | decision-only |
| `tests/unit/test_logging_redaction.py` | test | batch | none — greenfield | criterion 4; RESEARCH.md:771 | decision-only |
| `tests/integration/test_health.py` | test | request-response | none — greenfield | D-31; RESEARCH.md:766 | decision-only |
| `tests/integration/test_loopback_bind.py` | test | request-response | none — greenfield | D-34; RESEARCH.md:767 | decision-only |
| `tests/integration/test_migration_roundtrip.py` | test | batch | none — greenfield | criterion 5; RESEARCH.md:772 | decision-only |
| `tests/integration/test_persistence_roundtrip.py` | test | CRUD | none — greenfield | D-07; RESEARCH.md:773 | decision-only |
| `tests/security/test_boundary_scan.py` | test (static AST) | batch | none — greenfield | RESEARCH.md:624-643 (verbatim) | research-example |
| `tests/security/test_boundary_scan_negative.py` | test (meta-test) | batch | none — greenfield | D-37; RESEARCH.md:762 | decision-only |
| `tests/contract/test_*.py` | test (golden suite) | batch | none — greenfield | D-06; `Schema.md` contract sections | contract |

**Scope note (do not silently narrow):** the illustrative tree in RESEARCH.md:313-351
names only `envelope.py, market.py, errors.py, ids.py, enums.py, precision.py,
versions.py`. ROADMAP.md:41 (criterion 1) requires **every** Schema.md contract —
"agent envelope, market bar/quote, news item, sentiment, decision, journal, backtest,
error" — as validated versioned code. This map therefore includes
`decision.py`, `news.py`, `sentiment.py`, `backtest.py` and `journal.py`. The planner
must reconcile the two; the criterion is authoritative over the illustrative listing.

---

## Pattern Assignments

> Every excerpt below is a **documentary** pattern (a RESEARCH.md verified example or
> a normative `Schema.md`/`Architecture.md` passage), because no code analog exists.
> Line references are to the files named, so the planner can cite them directly in
> PLAN.md actions as "copy the shape from `<file>` lines `<a>-<b>`".

### Contracts package — all model modules (`envelope.py`, `market.py`, `decision.py`, `news.py`, `sentiment.py`, `backtest.py`, `journal.py`, `errors.py`)

**Pattern source:** `Schema.md` contract sections + `01-RESEARCH.md` Pattern 2.

**Module base config** (`01-RESEARCH.md:407-408`) — every model module opens with the
same `ConfigDict`, satisfying D-04/D-12/D-23 (strict, reject-unknown, frozen):
```python
class _M(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
```

**Decimal-as-string field** (`01-RESEARCH.md:393-410`) — the shape every
price/level field must use (D-11/D-19). Note `mode="serialization"` is required on
export (Pitfall 5: the default emits `anyOf[number,string]`):
```python
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, PlainSerializer, WithJsonSchema

_PATTERN = r"^-?\d+(\.\d+)?$"   # form only: no exponent, no leading '+', no NaN/Inf

PriceStr = Annotated[
    Decimal,
    PlainSerializer(lambda d: format(d, "f"), return_type=str),
    WithJsonSchema({"type": "string", "pattern": _PATTERN}),
]
```

**`envelope.py`** — reproduce `Schema.md` §3 (lines 69-83) exactly. Fields:
`schema_version, run_id, agent_name, agent_version, status, created_at, as_of,
input_refs, evidence_refs, limitations, error, result`. `status` is the closed
`Agent/run status` enum (`Schema.md` §2 lines 29-38); `error` is the C-09 object
(`errors.py`) or `null`.

**`market.py`** — reproduce `Schema.md` §4. Per-record invariants (`Schema.md:105-110`)
are the D-04 "contract invariants now" set the Pydantic model must enforce:
`high >= max(open, close, low)` and `low <= min(open, close, high)`, prices finite and
positive, ordered timestamps. `quality_status`/`quality_flags` use the D-20 vocabulary
transcribed in `enums.py`. `volume_type` enum: `tick|exchange|broker|unknown|not_available`.

**`decision.py`** — reproduce `Schema.md` §6 (lines 140-166). Contract invariant to
enforce here: `manual_review_required` must be `true` (`Schema.md:159`); levels
(`entry/stop_loss/take_profits/risk_reward`) stay `null` unless validated
(`Schema.md:148-150, 165`). Level *ordering* policy is Phase 3, not here (D-04).

**`errors.py`** — reproduce the C-09 envelope exactly (`Schema.md:224-237`,
[VERIFIED: Schema.md:224-237]):
```json
{ "code": "STABLE_MACHINE_READABLE_CODE", "message": "Sanitized user-facing description",
  "retryable": false, "correlation_id": "UUID", "details": null }
```
Open gray area: the `code` vocabulary is **not yet settled** (CONTEXT.md Deferred
Ideas; RESEARCH.md Open Question 1). Recommendation to carry into planning: a closed
`ErrorCode` enum with `retryable` as a per-code property, pinning at minimum
`CONTRACT_VALIDATION_FAILED`, `UNKNOWN_CONTRACT_MAJOR`, `CONFIG_INVALID`,
`UNSUPPORTED_*` — flagged for user confirmation because it is a published contract.

**`enums.py`** — transcribe `Schema.md` §2 (lines 20-65): Decision, Agent/run status,
Evidence status, Direction, Trend/regime state. Add the D-20 quality vocabulary
(`stale, duplicate, gap, malformed, disconnected, missing-history, unsupported` plus an
explicit not-evaluated/unknown that is **never healthy**, D-22). Timeframe enum members
come from the *selected provider's documented list*, not memory (D-16) — Phase 1 pins
the closed enum form; exact members are a planning item pending the Phase 2 provider.

**`versions.py`** — D-02/D-05/D-23: accept any `1.x`, reject unknown **major**, missing,
or unparseable; never coerce or default. `major.minor` semantics: enum member / optional
field → minor bump (monotonic within a major); rename/retype/required-add/member-remove
→ major bump.

**`ids.py`** — D-14/D-21: validate UUIDv7 **shape with the standard library only**
(`uuid`) so purity holds; one closed prefix registry entry per entity type
(`run_`, `dec_`, `agent_`, …) and each `*_id` field accepts its own prefix only.
Generation lives in the app layer, never in this package. `Schema.md:245` allows
"UUID or another documented stable identifier".

**`precision.py`** — D-19/D-24/D-26 table shape: keyed by `(instrument_id, provider_id)`,
provenance columns (`provider spec version`, `retrieved_at`, `superseded_at`,
`valid_from`, `valid_to`), rows never overwritten. Ships with **zero rows**; lookup
answers *unknown*, never a default. Phase 2 fills it.

### `packages/contracts/tests/test_import_purity.py` (test, batch)

**Pattern source:** `01-RESEARCH.md:357-386` (D-08) — copy verbatim as the starting point.
The allowlist lives in the test, so adding a dependency is a visible diff:
```python
# packages/contracts/tests/test_import_purity.py
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
D-08 explicitly **rejects** `import-linter`/`deptry`/`flake8-tidy-imports`/`pytest-archon`
as *the* mechanism (they may only ever complement this test).

### `apps/api/src/goldmasters_api/settings.py` (config, transform)

**Pattern source:** `01-RESEARCH.md:515-530` (D-15/D-27/D-36):
```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GOLDMASTERS_", env_file=".env", extra="forbid", frozen=True)
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    database_url: str
    provider_api_key: SecretStr | None = None   # secret: env only
    config_version: str = "1.0"
```
Missing/invalid config must **fail startup naming the key** (D-36). The config hash
(D-15/D-27) is computed once over the deterministic, sorted-key, non-secret
serialisation with `SecretStr` excluded — see RESEARCH.md Open Question 5.

### `apps/api/src/goldmasters_api/app.py` (controller, request-response)

**Pattern source:** `01-RESEARCH.md:541-556`. Use `lifespan` — `@app.on_event` is
deprecated (Pitfall/State-of-the-Art):
```python
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
Loopback guard (`01-RESEARCH.md:533-539`, D-34) — accept `127.0.0.1`/`::1`, reject
everything else (RESEARCH.md Open Question 4 on `localhost`):
```python
import ipaddress
def assert_loopback(host: str) -> None:
    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError(f"refusing to bind non-loopback address: {host!r}")
```

### `apps/api/src/goldmasters_api/health.py` (controller, request-response)

**Pattern source:** `01-RESEARCH.md:558-591`. The health surface must *prove the chain*
(D-31), not return 200 unconditionally:
```python
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
C-09 error mapping from Pydantic `ValidationError` (`01-RESEARCH.md:573-591`) — reuse
the same `correlation_id` the logging middleware bound:
```python
@app.exception_handler(ValidationError)
async def validation_handler(request, exc: ValidationError):
    errs = exc.errors()
    return JSONResponse(status_code=422, content={
        "code": "CONTRACT_VALIDATION_FAILED",
        "message": "Payload failed contract validation.",
        "retryable": False,
        "correlation_id": current_correlation_id(),
        "details": [{"loc": ".".join(map(str, e["loc"])), "type": e["type"]} for e in errs],
    })
```

### `apps/api/src/goldmasters_api/logging.py` (middleware, event-driven)

**Pattern source:** `01-RESEARCH.md:420-434` (D-30/criterion 4). `merge_contextvars`
must be first so every JSON line carries the bound correlation ID; add a redaction
processor (redaction rules are an open gray area — RESEARCH.md Open Question 3;
`Schema.md:234` and §1 line 18 forbid secrets/SQL/stack traces/paths/tokens):
```python
import structlog
structlog.configure(processors=[
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.JSONRenderer(),
])
```

### `apps/api/migrations/versions/0001_contract_document.py` (migration, batch)

**Pattern source:** `01-RESEARCH.md:594-622` (D-07 + criterion 5). Hand-written; the
`downgrade()` must drop exactly what `upgrade()` created, in reverse (Pitfall 7):
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_contract_documents"
down_revision = None

def upgrade() -> None:
    op.create_table("contract_document",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("run_id", sa.Text, nullable=True),
        sa.Column("agent_name", sa.Text, nullable=True),
        sa.Column("instrument_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("document", postgresql.JSONB, nullable=False))
    op.create_index("ix_contract_document_run_id", "contract_document", ["run_id"])

def downgrade() -> None:
    op.drop_index("ix_contract_document_run_id", table_name="contract_document")
    op.drop_table("contract_document")
```
Gate proof (criterion 5): `alembic upgrade head` → `downgrade base` → `upgrade head`
against the throwaway per-run DB (D-35).

### `tests/security/test_boundary_scan.py` (test, batch) + `.py` negative meta-test

**Pattern source:** `01-RESEARCH.md:624-643` (D-37, REQ-no-trade-execution). The scan
must be a **test** so it runs in the gate; the negative meta-test proves it has teeth
(RESEARCH.md:762):
```python
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
The dependency-manifest allowlist check runs alongside it (both are tests).

### `scripts/gate` + `.githooks/pre-commit` + `.github/workflows/ci.yml` (tooling, batch)

**Pattern source:** D-38/D-39/D-40; `01-RESEARCH.md:412-414` (Pattern 3) and 819-829
(CI Reconciliation). One ordered list, two invocation sites:
```bash
# scripts/gate (D-38) — the single meaning of "green"
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict .
uv run pytest          # includes the purity test and the boundary scan
```
- `scripts/gate` runs the whole list; `.githooks/pre-commit` (tracked via
  `git config core.hooksPath .githooks`) runs the fast subset — format/lint/mypy over
  changed files (D-40).
- `.github/workflows/ci.yml` invokes `scripts/gate` **present-but-inert** until a
  remote exists (D-39). `nektos/act` is **explicitly not viable** — it needs Docker,
  which is absent (RESEARCH.md:829). Do not propose `act`.

### `scripts/postgres/*` (tooling, file-I/O) + `.env.example` (config)

**Pattern source:** `01-RESEARCH.md:646-653` (D-29). Repo-local, script-managed,
pinned; binaries + data dir are git-ignored:
```
scripts/postgres/
  VERSION            # e.g. "18.6"  (pinned)
  provision.ps1      # curl -L the EDB no-installer zip, record resolved URL + sha256
  init.ps1           # initdb -D <repo-local data dir> -U goldmasters -A scram-sha-256 --pwfile ...
  start.ps1          # pg_ctl -D <datadir> -o "-p 5432 -h 127.0.0.1" start
  stop.ps1           # pg_ctl -D <datadir> stop
```
Pitfall 6: `initdb` default auth is `trust` — pass an explicit auth method + `--pwfile`.
`.env.example` enumerates every required key and holds **no secret value** (D-36;
`Schema.md` §11 line 244 — `GOLDMASTERS_...` prefix, never a committed secret).
Assumptions A2/A3 (Windows-10 runnability; `initdb` elevation) require a falsification
probe before the plan depends on them.

---

## Shared Patterns

These cross-cut many files. Because no analog exists, each is a *documentary*
pattern the planner should attach to every relevant plan's action.

### Contract base configuration (D-04/D-12)
**Source:** `01-RESEARCH.md:407-408` · **Apply to:** every model module in
`packages/contracts`. Every contract model: `ConfigDict(strict=True, extra="forbid",
frozen=True)`; unknown fields rejected with the C-09 error naming the field.

### Decimal-as-string on the wire (D-11/D-19)
**Source:** `01-RESEARCH.md:393-410` · **Apply to:** every monetary/price/level field
and its Pydantic validators. Export with `mode="serialization"` (Pitfall 5). Form-only
while the precision table is empty: digits + optional single dot; reject exponent, `+`
prefix, NaN, Infinity (Pitfall 4 — Pydantic's default decimal pattern allows `E`).

### C-09 error envelope (Schema.md §10)
**Source:** `Schema.md:224-237` [VERIFIED] · **Apply to:** the boundary handler, the
health surface, and every rejection path. Shape is fixed:
`{code, message, retryable, correlation_id, details}`; `retryable` is determined by
code, not judgement; `message`/`details` are sanitized/redacted.

### Purity allowlist (D-08)
**Source:** `01-RESEARCH.md:362-366` · **Apply to:** the contracts package only.
Adding any dependency outside `{pydantic} ∪ stdlib` must be a visible diff in
`test_import_purity.py`, never a silent `pyproject.toml` change.

### Correlation ID (criterion 4 / D-30)
**Source:** `01-RESEARCH.md:420-434, 573-591` · **Apply to:** request middleware, all
log lines, OTel spans, and the C-09 error body. Mint a UUID per request; bind via
`bind_contextvars`; `merge_contextvars` first in the processor chain.

### Loopback-only binding (D-34 / R-07)
**Source:** `01-RESEARCH.md:468-471, 533-539` · **Apply to:** the API startup and the
client launch. Backend: `assert_loopback` on the resolved host at startup. Client:
`next dev` **must** pass `-H 127.0.0.1` (Pitfall 2 — the default is `0.0.0.0`).

### Version acceptance (D-02/D-05/D-23)
**Source:** `Schema.md:16` (add `schema_version`) · **Apply to:** every persisted or
exchanged payload. Accept `1.x`; reject unknown major / missing / unparseable by
failing closed. Records keep the version they were written with.

### One gate, one meaning of green (D-38/R-10)
**Source:** `Rules.md:112` ("A task is DONE only with evidence") · **Apply to:** every
plan's verification. The gate is `scripts/gate`; a passing pipeline proves only the
checks it runs (`Architecture.md:230`).

---

## No Analog Found

Every file in this phase has no code analog — the repository is greenfield (verified
this session: 26 tracked files, all `.planning/**` + `ingest-manifest.yaml`; no source
tree of any kind). The table below names the *reason* per file group, so the planner
uses the documented pattern source instead of searching for a codebase pattern.

| Files | Role | Data Flow | Reason no analog exists |
|-------|------|-----------|-------------------------|
| All of `packages/contracts/**` | model / util / test | transform, batch | No Python package, `pyproject.toml`, or Pydantic model exists anywhere in the repo. Use `Schema.md` §2-§11 + RESEARCH.md Patterns 1-2. |
| All of `apps/api/**` | controller / config / middleware / provider / migration | request-response, event-driven, batch | No backend, no FastAPI app, no Alembic tree exists. Use RESEARCH.md Patterns 3-5 and the lifespan/health/C-09/migration excerpts. |
| All of `apps/web/**` | component / config | request-response | No `package.json`, no Next.js app, no React component exists. Use D-43 (health surface) + RESEARCH.md client notes; Phase 7 owns console design. |
| `scripts/**`, `.githooks/**`, `.github/**` | util / config | batch, file-I/O | No scripts, hooks or workflows exist. Use D-29/D-33/D-38/D-39 and RESEARCH.md CI Reconciliation. |
| `tests/**` | test | batch, request-response, CRUD, file-I/O | No `tests/` tree, no `conftest.py`, no pytest config exists. Use D-06/D-07/D-35/D-37 and RESEARCH.md Validation Architecture. |
| `.env.example`, `.gitattributes`, `.gitignore`, root `pyproject.toml` | config | n/a | No root tooling config exists. Use D-36, Pitfall 8, and RESEARCH.md:313. |

**Nearest documentary sources of truth (use these instead of a codebase search):**

| Documentary source | What it fixes |
|--------------------|---------------|
| `Schema.md` §2 (lines 20-65) | All enums (Decision, Agent/run status, Evidence status, Direction, Trend/regime) |
| `Schema.md` §3 (69-83) | Agent envelope fields |
| `Schema.md` §4 (88-119) | Market bar/quote fields + validation invariants (105-110) |
| `Schema.md` §6 (140-166) | Decision contract + immutability invariant |
| `Schema.md` §7 (168-189) | News item + sentiment contracts |
| `Schema.md` §9 (209-220) | Backtest contract |
| `Schema.md` §10 (222-237) | C-09 error envelope [VERIFIED] |
| `Schema.md` §11 (239-248) | Naming/formatting, env prefix, IDs, JSON rules |
| `Architecture.md` §2 (34-81) | Stack and boundaries (Python/FastAPI/PostgreSQL/Next) |
| `Architecture.md` §7 (186-219) | Repo layout proposal (adapted by D-41) |
| `Architecture.md` §8 (221-231) | Quality gates |
| `Rules.md` R-02/§9/§10 (16-23, 95-112) | Boundary, testing, DONE-with-evidence |
| `.planning/ROADMAP.md` (41-45) | Phase 1 success criteria (authority over the illustrative tree) |
| `.planning/phases/01-contracts-and-foundation/01-RESEARCH.md` | Verified code examples (Patterns 1-5, Code Examples) |

---

## Metadata

**Analog search scope:** repository root and all subdirectories (`git ls-files`,
recursive glob). Expected search locations — `src/`, `apps/`, `packages/`, `services/`,
`tests/`, `scripts/`, `.github/`, `.githooks/` — **do not exist**.
**Files scanned:** 26 tracked files (all `.planning/**` Markdown/YAML +
`ingest-manifest.yaml`); 10 root Markdown documents present but untracked.
**Code analogs found:** 0.
**Pattern extraction date:** 2026-10-13.

### Source-tracking note (tracked-source gate #3645)

No analog path is emitted in this document as a build target, so the mirror-path
hazard is not in play: there is no gitignored install/runtime mirror anywhere in this
repository to accidentally name. For completeness:

- The **documentary** sources cited above (`Schema.md`, `Architecture.md`, `Rules.md`)
  exist on disk but are currently **untracked** (`git status` shows `?? Schema.md` etc.).
  They are not gitignored and are slated to be committed (D-44). Their untracked state
  is a known bookkeeping item (`Memory.md`/`Task.md` drift, RISK-01/RISK-02), not a
  mirror. The planner should have them committed before the phase's first commit so
  `canonical_refs` resolve in history.
- `01-RESEARCH.md`, `01-CONTEXT.md` and `01-VALIDATION.md` are git-tracked under
  `.planning/phases/01-contracts-and-foundation/`. **Verified:** `git ls-files --` prints
  each of them.
- No path under `.gsd/capabilities/**` or any plugin mirror exists in this repo.

### Honesty statement

This PATTERNS.md deliberately records **"no existing analog — greenfield"** for every
file rather than manufacturing false positives. The correct action for the planner is
to treat the documentary sources above as the pattern library, and to expect Phases 2-8
to gain real code analogs as Phase 1 lands.
