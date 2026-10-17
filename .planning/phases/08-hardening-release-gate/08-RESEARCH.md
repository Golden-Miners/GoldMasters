# Phase 8: Hardening, Data-Integrity Verification and Release Gate - Research

**Researched:** 2026-10-17
**Domain:** Security audit, dependency/secret scanning, failure-injection testing, backup/restore, migration rollback, release suite, operator runbook
**Confidence:** HIGH

## Summary

GoldMasters Phase 8 ("Hardening, Data-Integrity Verification and Release Gate") proves, with recorded evidence, that nothing is fabricated or executable and no claim is untested. The ROADMAP.md defines five success criteria:

1. Repository-wide audit shows no invented/mock/sample market/news/sentiment/backtest/signal data in production paths; every missing value labelled unknown/unavailable; test fixtures labelled and never served as live conditions.
2. Security audit against the real repository with file/line evidence; uninspectable categories marked "Not assessed — evidence unavailable", no fix applied before user approval.
3. Provider outage, model outage, DB outage, timeout and malformed-output paths tested; critical failures demonstrably cannot produce a TRADE.
4. Backup/restore and migration rollback tested; dependencies and secrets scanned; local services bind to loopback only.
5. Release suite runs with exact commands and recorded output; unresolved items listed, not hidden; no claim of "zero hallucinations", "perfect analysis", or "zero errors" anywhere.

Repository inspection confirms: no `order_send`/`order_modify`/`order_close`/`symbol_select`/`login` call names exist anywhere in `src/goldmasters/`, `apps/api/`, `services/` (verified by AST boundary scan `tests/security/_boundary.py`). The only broker-surface call is `trade_allowed` (read-only session assertion, `services/mt5_adapter/terminal.py:215`). MT5 import is lazily confined to `services/mt5_adapter/terminal.py` only. Migrations `0001`–`0003` all ship `downgrade()` paths. Settings enforce loopback bind (`assert_loopback`, `apps/api/src/goldmasters_api/app.py:39-56`) and loopback Ollama host (`settings.py:363-370`).

**Primary recommendation:** Execute Phase 8 in four waves — Wave 0 audit scans (security boundary, dependency/secret scan, fixture scan), Wave 1 failure-injection (provider/model/DB/outage/timeout/malformed → NO_TRADE or INSUFFICIENT_DATA), Wave 2 rollback + backup/restore test, Wave 3 release-suite run with exact command output recorded.

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists in the working directory for Phase 8. Locked decisions come from ROADMAP.md Phase 8 criteria (5 items), Task.md T0801–T0808, Security.md, Rules.md, Schema.md §10 (error contract), and Architecture.md §7/#8 (quality gates).

### Locked Decisions
- Phase 8 must satisfy all five ROADMAP.md success criteria (criteria 1–5 above).
- Task.md T0801–T0808 are the execution items; each has an acceptance criterion.
- Security.md audit rules apply: do not modify code during audit; cite exact file/line; redact secrets; categories that cannot be inspected are marked "Not assessed — evidence unavailable".
- Rules.md §1, §2, §7, §9 apply: no invented data, no order execution, no secrets in source/bundles/logs, all external inputs validated, tests must not depend on live markets unless marked integration.
- Schema.md §1 line 18: no secrets in schemas/logs/traces/examples; Schema.md §10: stable error codes, sanitized messages, correlation IDs.

### the agent's Discretion
- Choice of audit scan tooling (boundary scan already exists via tests/security/_boundary.py).
- Exact failure-injection approach for outage/timeout/malformed paths.
- Release suite command list and ordering.
- Evidence format and runbook structure.

### Deferred Ideas (OUT OF SCOPE)
- No trade execution capability of any kind (V1 is research/decision support only).
- No order placement, modification, closure, copy trading, or broker execution.
- No broker/trading credentials requested or stored beyond read-only MT5 access.
- No LAN/public exposure of MT5 bridge or database by default.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-no-trade-execution | No order placement/modification/closure; boundary scan fails build if execution call names appear | Verified absence: `tests/security/_boundary.py` `FORBIDDEN_CALL_NAMES` lists `order_send`, `order_modify`, `order_close`, etc.; AST scan of `packages`, `apps`, `src`, `services` returns no hits. Only `trade_allowed` read-only check exists (`services/mt5_adapter/terminal.py:215`). |
| REQ-no-fabricated-data | No invented/mock/sample market/news/sentiment/backtest/signal data in production paths; fixtures labelled | Backtest costs are declared placeholders (`src/goldmasters/backtest/fills.py:47-55`, `runner.py:8-9`, `metrics.py:30`); no fixture-as-live pattern found in production code paths. |
| REQ-local-model-support | Ollama loopback-only, runtime model discovery, outage tested | `settings.py:360-370` loops back Ollama host; `src/goldmasters/graph/runtime.py` does `list()` discovery at run start; outage path tested via graph failure policy. |
| REQ-journal-and-backtesting | Immutable snapshots, append-only outcomes, reproducible backtests with declared assumptions | Migrations `0001`–`0003` with `downgrade()` paths; journal `supersedes` column; backtest assumptions JSONB column. |
| REQ-ui-and-reports | Read-only console, no execution action reachable from client | Web app is Next.js read-only over API; `apps/web/package.json` scripts `dev`/`build`/`start` all bind `127.0.0.1`; no trade controls in frontend. |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Security audit & boundary scan | API / Backend | — | AST scan over `packages`, `apps`, `src`, `services`; FastAPI app is the trust boundary (loopback guard, `apps/api/src/goldmasters_api/app.py:39-56`). |
| Dependency & secret scanning | API / Backend | — | `pyproject.toml` manifests + lockfiles scanned; secrets live in env/SecretStr only (`settings.py:135`, `logging.py:22-64`). |
| Failure injection (outage/timeout/malformed) | API / Backend | Browser / Client | Graph nodes return structured failures; frontend shows offline/stale states but no execution control. |
| Backup/restore & migration rollback | Database / Storage | API / Backend | Alembic migrations with `downgrade()` (`0001`–`0003`); throwaway per-run DB fixtures in `tests/conftest.py`. |
| Release suite execution | API / Backend | — | Single local host; commands run from repo root via `uv`, `pytest`, `ruff`, `mypy`, `tsc`. |
| Operator runbook | — | — | Documentation owned by operator; runbook describes setup, operation, troubleshooting, limitations. |

</phase_requirements>

<metadata>
## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified from `pyproject.toml` and `package.json` read this session.
- Architecture: HIGH — traced actual source files this session.
- Pitfalls: HIGH — all findings from direct file reads and grep this session.
- Rollback paths: HIGH — migration `downgrade()` paths read verbatim this session.

**Research date:** 2026-10-17
**Valid until:** 30 days (stable codebase; fast-moving for dependency versions)

</metadata>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.14.7 | Backend runtime | Exact interpreter pin in `pyproject.toml` root and `apps/api/pyproject.toml:9`, `packages/contracts/pyproject.toml:10` [VERIFIED: file read this session] |
| FastAPI | 0.143.0 | API framework | `apps/api/pyproject.toml:12` [VERIFIED: file read this session] |
| Uvicorn | 0.54.0 | ASGI server | `apps/api/pyproject.toml:13` [VERIFIED: file read this session] |
| Pydantic / pydantic-settings | 2.14.1 / 2.15.0 | Typed settings & validation | `packages/contracts/pyproject.toml:15`, `apps/api/pyproject.toml:14` [VERIFIED: file read this session] |
| SQLAlchemy | 2.1.4 | ORM / DB access | `apps/api/pyproject.toml:19` [VERIFIED: file read this session] |
| Alembic | 1.20.0 | Migrations | `apps/api/pyproject.toml:20` [VERIFIED: file read this session] |
| psycopg[binary] | 3.3.6 | PostgreSQL driver | `apps/api/pyproject.toml:21` [VERIFIED: file read this session] |
| LangGraph | 1.2.15 | Graph orchestration | `apps/api/pyproject.toml:25` [VERIFIED: file read this session] |
| Ollama (py) | 0.6.3 | Local LLM client | `apps/api/pyproject.toml:26` [VERIFIED: file read this session] |
| structlog | 26.1.0 | Structured logging + redaction | `apps/api/pyproject.toml:15` [VERIFIED: file read this session] |
| langgraph-checkpoint-sqlite | 3.1.2 | Checkpoint backend | `apps/api/pyproject.toml:27` [VERIFIED: file read this session] |
| Ruff | 0.17.0 | Lint + format | Root `pyproject.toml:22` [VERIFIED: file read this session] |
| Mypy | 2.4.0 | Strict type check | Root `pyproject.toml:23`, `[tool.mypy] strict = true` [VERIFIED: file read this session] |
| Pytest | 9.1.1 | Test framework | Root `pyproject.toml:24` [VERIFIED: file read this session] |
| Next.js | 16.4.0 | Frontend framework | `apps/web/package.json:17` [VERIFIED: file read this session] |
| React | 19.3.0 | UI library | `apps/web/package.json:18` [VERIFIED: file read this session] |
| Playwright | 1.64.1 | E2E browser tests | `apps/web/package.json:23` [VERIFIED: file read this session] |
| MetaTrader5 (py) | not installed | MT5 read-only adapter | Not installed (Memory.md: "MetaTrader5 Python package not installed"); import lazily confined to `services/mt5_adapter/terminal.py` [VERIFIED: file read + Memory.md] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0.3 | YAML config source | `apps/api/pyproject.toml:18` — `config/goldmasters.yaml` |
| OpenTelemetry SDK/API | 1.45.1 | Tracing | `apps/api/pyproject.toml:16-17` — `tracing.py` |
| httpx | 0.28.1 | HTTP client | `apps/api/pyproject.toml:23` — provider health probes |
| tzdata | 2026.5 | IANA timezone data | `packages/contracts/pyproject.toml:16` — Schema.md §1 line 10 |
| recharts | ^3.10.1 | Charting | `apps/web/package.json:20` — UI charts only |
| json-schema-to-typescript | 16.0.0 | TS type generation | `apps/web/package.json:27` — `gen:types` from committed schema JSON |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PostgreSQL (Alembic) | SQLite / TimescaleDB | SQLite lacks production migration parity; TimescaleDB adds unmeasured complexity (Architecture.md §2 line 61) |
| LangGraph | Custom state machine | LangGraph already integrated, tested, bounded (Phase 4 done) |
| Ollama | Cloud LLM | V1 requires local-only model; cloud introduces secret/network surface |

**Installation:**
```bash
uv sync --all-packages          # repo root; do NOT use bare `uv sync` (prunes workspace members, Memory.md line 58)
cd apps/web && npm install      # frontend deps; package-lock.json present
```

**Version verification:** All versions above read from `pyproject.toml` / `package.json` this session. No `[ASSUMED]` package versions remain in this table.

## Package Legitimacy Audit

> Required whenever this phase installs external packages. Phase 8 installs no new packages — all dependencies are existing, pinned in `pyproject.toml` / `package.json` and verified from file reads this session. The gate below applies to any new package the planner might add.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| fastapi | PyPI | 8+ yrs | high | github.com/fastapi/fastapi | OK | Approved (existing pin) |
| sqlalchemy | PyPI | 15+ yrs | high | github.com/sqlalchemy/sqlalchemy | OK | Approved (existing pin) |
| alembic | PyPI | 10+ yrs | high | github.com/sqlalchemy/alembic | OK | Approved (existing pin) |
| psycopg[binary] | PyPI | 10+ yrs | high | github.com/psycopg/psycopg | OK | Approved (existing pin) |
| langgraph | PyPI | 3+ yrs | high | github.com/langchain-ai/langgraph | OK | Approved (existing pin) |
| ollama | PyPI | 2+ yrs | moderate | github.com/ollama/ollama-python | OK | Approved (existing pin) |
| next | npm | 10+ yrs | high | github.com/vercel/next.js | OK | Approved (existing pin) |
| playwright | npm | 5+ yrs | high | github.com/microsoft/playwright | OK | Approved (existing pin) |
| MetaTrader5 | PyPI | N/A | N/A | N/A | — | Not installed; lazy import only in `services/mt5_adapter/terminal.py` |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

Packages discovered via WebSearch or training data that have not been verified against an authoritative source are tagged `[ASSUMED]` and the planner must gate each install behind a `checkpoint:human-verify` task. No new packages are recommended for Phase 8.

## Architecture Patterns

### System Architecture Diagram

```text
[Browser/Client: Next.js on 127.0.0.1:3000]
        | HTTPS loopback only (apps/web/package.json dev/build/start -H 127.0.0.1)
        v
[FastAPI on 127.0.0.1:8000] <-- assert_loopback rejects non-loopback bind (app.py:39-56)
        | CorrelationIdMiddleware mints server-side correlation ID (middleware.py)
        v
[Health /market /decisions /journal /agent-runs /providers /model-health /settings routers]
        |
        +---> [MT5 Terminal Gateway: lazy MetaTrader5 import, read-only only]
        |         | terminal.trade_allowed asserted False (adapter.py:215)
        |         | symbol_select/login/order_send globally forbidden (_boundary.py)
        |
        +---> [LangGraph: ingest -> select -> evaluate -> gate -> finalize]
        |         | Gate fail-closed: no levels -> NO_TRADE / INSUFFICIENT_DATA
        |         | risk_percent_for_idea=None -> gate blocks (gate.py:110-112)
        |
        +---> [PostgreSQL via GOLDMASTERS_DATABASE_URL]
                  | Alembic migrations 0001-0003 with downgrade() paths
                  | Throwaway per-run DB fixtures (tests/conftest.py)
        |
        +---> [Ollama on 127.0.0.1:11434, loopback-only]
                  | Runtime model discovery (runtime.py); no model name assumed
```

Entry point: browser loads a page over loopback -> FastAPI health/API -> data from DB or MT5 probe -> LangGraph run produces a decision -> persisted immutably. Decision points: gate pass/fail, barrier pass/fail, provider connected/disconnected. External dependencies: MT5 terminal (same host), PostgreSQL (local), Ollama (loopback).

### Recommended Project Structure

```
src/goldmasters/        # domain, graph, agents, risk, strategies, data, backtest
services/mt5_adapter/   # read-only MT5 terminal gateway (lazy import only)
apps/api/               # FastAPI app, settings, routers, migrations
apps/web/               # Next.js read-only console
packages/contracts/     # Pydantic models + JSON schema
tests/                  # unit, integration, contract, security
scripts/                # gate, stack, postgres provisioning
```

### Pattern 1: Fail-closed Gate
**What:** `evaluate_gate` returns `passed=False` with reasons whenever any policy input is unset or invalid (gate.py:86-135). `risk_percent_for_idea=None` blocks ("idea risk unknown").
**When to use:** Every path to a TRADE decision must pass through `trade_eligible_levels` (gate.py:138-146), which returns `None` unless `passed`.
**Example:** gate node `make_gate_node` (nodes.py:332-386) runs `evaluate_gate`; `assemble_decision` only emits `Decision.TRADE` when `barrier_passed is True and verdict.passed` (nodes.py:421-443).

### Anti-Patterns to Avoid
- **Mock/live data conflation:** Never present test fixtures as live conditions (Rules.md §1.2). Backtest costs are declared placeholders (`fills.py:47-55`) and stay unconfirmed.
- **Order-execution surface:** No `order_send`/`order_modify`/`order_close`/`symbol_select`/`login` anywhere (enforced by `_boundary.py` AST scan).
- **Secret leakage:** No secrets in schemas, logs, traces, examples (Schema.md §1 line 18); `provider_api_key` is `SecretStr` and excluded from `hash_effective_config` (settings.py:401-414).
- **Non-loopback bind:** `assert_loopback` rejects any non-loopback host (app.py:39-56).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Migration apply/rollback | Custom SQL migration scripts | Alembic `upgrade`/`downgrade` (`0001`–`0003` with `downgrade()`) | Tested round-trip (`tests/integration/test_migration_roundtrip.py`); versioned, reversible |
| Secret redaction in logs | Manual string scrubbing | structlog `_scrub` + `SecretStr` (`logging.py:22-64`, `settings.py:135`) | Nested redaction tested (`test_logging_redaction.py`) |
| Boundary scan for execution calls | Manual grep each release | AST scan `tests/security/_boundary.py` (runs in CI gate) | Machine-checked, negative meta-test prevents rot |
| Per-run DB fixture management | Shared dev database | Throwaway per-run DB created/dropped (`tests/conftest.py:82-108`) | Tests never mutate persistent instance |
| Loopback enforcement | Ad-hoc host checks | `assert_loopback` + `ollama_host` loopback validator (`app.py:39-56`, `settings.py:363-370`) | Fail-closed at startup, not runtime |

**Key insight:** Every deceptively complex concern in this phase (migration reversibility, secret redaction, boundary enforcement, throwaway DBs, loopback binding) already has an implemented, tested pattern in the repo. Phase 8's job is to *audit and record evidence* that they work, not to rebuild them.

## Common Pitfalls

### Pitfall 1: Marking an uninspected security category "clean"
**What goes wrong:** Security.md §5 requires categories that cannot be inspected to be marked "Not assessed — evidence unavailable", not clean. A scanner that can't reach a category (e.g., no MT5 terminal, no Ollama running, no PostgreSQL cluster) must report absence, not a clean bill.
**Why it happens:** Scanner returns exit code 0 because nothing matched, or the category's precondition (live terminal, DB, model) is missing.
**How to avoid:** For each Security.md category (1–12), record whether the precondition exists on this machine. If not, mark "Not assessed — evidence unavailable" with the missing precondition named.
**Warning signs:** Any "clean" conclusion without file/line citation or without the precondition verified present.

### Pitfall 2: Treating placeholder backtest costs as authoritative
**What goes wrong:** `placeholder_costs()` (`fills.py:47-55`) returns zero costs and raises if used for authoritative metrics. Metrics derived through it are explicitly "not authoritative" (`runner.py:8-9`, `metrics.py:30`).
**Why it happens:** Backtest cost values are deferred to operator confirmation (D-6.1); code ships declared placeholders.
**How to avoid:** Phase 8 evidence must state costs are placeholders, never present a backtest metric as proven ROI. Tests assert placeholder behavior, not metric correctness.
**Warning signs:** Any backtest metric presented without its "placeholder per D-6.1" caveat.

### Pitfall 3: Bare `uv sync` pruning workspace members
**What goes wrong:** Bare `uv sync` prunes workspace members from `.venv` (Memory.md line 58), breaking imports across `packages/contracts` and `apps/api`.
**Why it happens:** Workspace root is a virtual project (`pyproject.toml:11-12`).
**How to avoid:** Always use `uv sync --all-packages` in this repo. Document in release suite.
**Warning signs:** `ModuleNotFoundError: goldmasters_contracts` or `goldmasters_api` after sync.

### Pitfall 4: No `.env.example` present
**What goes wrong:** No `.env.example` file exists in the repo root (glob confirmed none). Phase 1 criterion 4 requires `.env.example` contains no real secret values, but the file itself is absent.
**Why it happens:** Never created in earlier phases.
**How to avoid:** Phase 8 must record this as an unresolved item or create `.env.example` with names-only (D-27/D-36 pattern, `config/goldmasters.yaml` exists).
**Warning signs:** Release suite reaches config validation and cannot find `.env.example`.

### Pitfall 5: No hosted CI workflow file exists
**What goes wrong:** Phase 1 plan 01-03 recorded "CI intent recorded as a build-failing local gate; no hosted workflow file" (ROADMAP.md Phase 1 Wave 3). No `.github/workflows/*.yml` exists (glob confirmed none).
**Why it happens:** CI was deliberately local-only (scripts/gate).
**How to avoid:** Phase 8 release suite runs locally with exact commands recorded; if hosted CI is required, that's a separate decision, not part of Phase 8.
**Warning signs:** Looking for `.github/workflows` and finding nothing — document as intentional, not a gap.

### Pitfall 6: Claiming "zero hallucinations" / "perfect analysis" / "zero errors"
**What goes wrong:** ROADMAP Phase 8 criterion 5 forbids these claims anywhere in the project.
**Why it happens:** Marketing-style language in docs or runbook.
**How to avoid:** Grep the whole repo for these phrases before release; none should appear.
**Warning signs:** Any occurrence of "zero hallucinations", "perfect analysis", "zero errors", "guaranteed profit".

## Code Examples

### Boundary scan (verifies no trade-execution surface)
```python
# Source: tests/security/_boundary.py:36-49, 75-78 (read this session)
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
FORBIDDEN_ADAPTER_CALLS: frozenset[str] = frozenset({"symbol_select", "login"})
SCAN_ROOTS: tuple[str, ...] = ("packages", "apps", "src", "services")
```
**Purpose:** AST scan fails the build if any order-execution call name or broker SDK import root appears outside the lazy gateway. Run as part of the release suite.

### Loopback bind guard
```python
# Source: apps/api/src/goldmasters_api/app.py:39-56 (read this session)
def assert_loopback(host: str) -> None:
    candidates: list[str] = [host]
    if host == "localhost":
        infos = socket.getaddrinfo(host, None)
        candidates = sorted({str(info[4][0]) for info in infos})
    for candidate in candidates:
        parsed = ipaddress.ip_address(candidate)
        if not parsed.is_loopback:
            raise ValueError(f"bind_host {host!r} is not a loopback address")
```
**Purpose:** Startup fails if the API would bind to a non-loopback host. Default `bind_host = "127.0.0.1"` (settings.py:129).

### Fail-closed risk gate
```python
# Source: src/goldmasters/risk/gate.py:87-116 (read this session)
if min_risk_reward_ratio is None:
    reasons.append("risk policy unset: GOLDMASTERS_MIN_RISK_REWARD_RATIO is required")
if max_risk_percent_per_idea is None:
    reasons.append("risk policy unset: GOLDMASTERS_MAX_RISK_PERCENT_PER_IDEA is required")
elif risk_percent_for_idea is None:
    reasons.append("idea risk unknown: risk percent must be computed, never guessed")
```
**Purpose:** Unset policy blocks; per-idea risk must be computed, never guessed. `risk_percent_for_idea=None` in graph nodes.py:370 fails closed.

### Migration downgrade path
```python
# Source: apps/api/migrations/versions/0001_contract_document.py:41-46 (read this session)
def downgrade() -> None:
    op.drop_index("ix_contract_document_status", table_name="contract_document")
    op.drop_index("ix_contract_document_created_at", table_name="contract_document")
    op.drop_index("ix_contract_document_instrument_id", table_name="contract_document")
    op.drop_index("ix_contract_document_run_id", table_name="contract_document")
    op.drop_table("contract_document")
```
**Purpose:** Every migration `0001`–`0003` ships a `downgrade()`; rollback test applies `upgrade head` then `downgrade base` and verifies the schema is empty.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual grep for `order_send` | AST boundary scan with negative meta-test | Phase 1 (plan 01-03) | Machine-checked, cannot rot |
| Shared dev DB for tests | Throwaway per-run DB created/dropped | Phase 1 (plan 01-06) | Tests never mutate persistent instance |
| No config validation | Typed Settings with fail-closed startup + effective-config hash | Phase 1 (plan 01-10) | Startup rejects undeclared env vars; config hash on app.state |
| No redaction | structlog `_scrub` + `SecretStr` exclusion from config hash | Phase 1 (plan 01-09) | Secrets never rendered in logs/traces |

**Deprecated/outdated:**
- Bare `uv sync`: prunes workspace members; replaced by `uv sync --all-packages` (Memory.md line 58).
- Hosted CI workflow: none exists; CI intent is local `scripts/gate` only (ROADMAP Phase 1 Wave 3 note).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All five ROADMAP Phase 8 criteria can be satisfied with existing code + test fixtures; no new library needed. | Standard Stack / Release Suite | If a gap is found (e.g., no rollback test runner), Phase 8 execution is blocked until filled. |
| A2 | `.env.example` absence is an unresolved item, not a blocker; Phase 8 records it rather than creating it. | Common Pitfalls | If user requires `.env.example` before release, an extra task is inserted. |
| A3 | No hosted CI workflow is required for Phase 8; local `scripts/gate` + recorded output satisfies criterion 5. | Common Pitfalls | If user requires GitHub Actions, that's out of scope for Phase 8. |
| A4 | MT5 terminal, PostgreSQL cluster, and Ollama are not available on this research machine; outage paths are tested by injection/mock, not live. | Environment Availability | If live services become available, integration tests can be extended but are not required. |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed. (Not the case here; see A1–A4.)

## Open Questions

1. **Does `.env.example` need to exist before release?**
   - What we know: No `.env.example` exists in repo root (glob confirmed). `config/goldmasters.yaml` exists. Phase 1 criterion 4 requires `.env.example` with no real secrets.
   - What's unclear: Whether user wants Phase 8 to create it or record it as unresolved.
   - Recommendation: Record as an open item in the release suite output; ask user.

2. **Is hosted CI (GitHub Actions) required for Phase 8, or is local `scripts/gate` sufficient?**
   - What we know: No `.github/workflows/*.yml` exists. Phase 1 recorded CI intent as local gate only.
   - What's unclear: User's deployment/CI expectations.
   - Recommendation: Treat local gate + recorded output as satisfying criterion 5; flag if user wants hosted CI.

3. **Are live MT5 / PostgreSQL / Ollama available for integration verification?**
   - What we know: Not available on this research machine (Memory.md T0003: MetaTrader5 not installed; no DB cluster running; T0004 Ollama open).
   - What's unclear: Whether Phase 8 should include live integration runs if services appear.
   - Recommendation: Failure-injection tests cover outage paths without live services; mark live integration as optional.

4. **Which `scripts/gate` commands constitute the "release suite"?**
   - What we know: `scripts/gate` exists (file listed). Contents not yet read.
   - What's unclear: Exact command list and expected output format.
   - Recommendation: Read `scripts/gate` during Wave 0; incorporate into release suite command list.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14.7 | Backend, tests | ✓ | 3.14.7 | — |
| uv | Package sync | ✓ | (from `pyproject.toml`) | — |
| PostgreSQL cluster | DB tests, migration rollback | ✗ | — | Migration rollback tested via throwaway DB fixture requires cluster; failure-injection tests use mocks |
| psql / `scripts/postgres/start.ps1` | Cluster start | ✗ | — | Rollback test scripted; requires cluster to be startable |
| MT5 terminal | Provider outage test (live) | ✗ | — | Outage tested via injected `TerminalGateway` double / failure paths |
| Ollama | Model outage test (live) | ✗ | — | Outage tested via graph failure policy / injected errors |
| Node.js >= 22.19 | Frontend build/typecheck | ✗ (not verified) | — | Frontend E2E optional if Node unavailable |
| npx / npm | Frontend deps | ✗ (not verified) | — | — |

**Missing dependencies with no fallback:**
- None blocking: all Phase 8 verification can proceed with failure-injection and static analysis without live services.

**Missing dependencies with fallback:**
- PostgreSQL cluster: required for migration rollback test and DB outage test; fallback is to script the rollback test and mark live DB test as "requires cluster start".
- MT5 terminal / Ollama: outage paths tested via injection, not live.

**Step 2.6 status:** Not skipped — external dependencies identified and documented above.

## Validation Architecture

> `workflow.nyquist_validation` is absent from `.planning/config.json` (read this session: only `workflow.use_worktrees` and `git.allow_default_branch_commits` present), so the section is included per the default-enabled rule.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Pytest 9.1.1 (root `pyproject.toml:24`) |
| Config file | `[tool.pytest.ini_options]` in root `pyproject.toml:27-31`; `testpaths = ["tests", "packages/contracts/tests"]`, `pythonpath = ["."]`, markers include `live_mt5` |
| Quick run command | `uv run pytest tests/security -q` (security subset, <30s) |
| Full suite command | `uv run pytest` (all tests, `tests/` + `packages/contracts/tests`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-no-trade-execution | No `order_send`/`order_modify`/`order_close`/`symbol_select`/`login` in source tree | security (AST scan) | `uv run pytest tests/security -q` | ✅ `tests/security/_boundary.py`, `test_boundary_scan.py` |
| REQ-no-fabricated-data | No mock/sample data in production paths; fixtures labelled | static scan + unit | `uv run pytest tests/unit -q` | ✅ `tests/unit/` (incl. `test_env_example.py`, `test_logging_redaction.py`) |
| REQ-local-model-support | Ollama loopback-only, outage cannot produce TRADE | unit + integration | `uv run pytest tests/unit tests/integration -q` | ✅ `tests/integration/test_ollama_discovery.py`, `test_mt5_health_api.py` |
| REQ-journal-and-backtesting | Migration rollback, immutable snapshots, backtest placeholders | integration + unit | `uv run pytest tests/integration/test_migration_roundtrip.py tests/unit/test_backtest_*.py -q` | ✅ `tests/integration/test_migration_roundtrip.py`, `tests/unit/test_backtest_costs.py`, `test_backtest_leakage.py`, `test_backtest_splits.py` |
| REQ-ui-and-reports | Read-only console, no execution action from client | E2E (Playwright) | `cd apps/web && npx playwright test` | ✅ `apps/web/playwright.config.ts` |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/security -q` (quick run command)
- **Per wave merge:** `uv run pytest` (full suite command)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/security/test_boundary_scan_negative.py` — covers REQ-no-trade-execution negative meta-test (exists ✅)
- [ ] No dedicated migration rollback CLI test beyond `test_migration_roundtrip.py` — verify rollback `downgrade base` path executes cleanly
- [ ] No `.env.example` — release suite must record absence as unresolved item
- [ ] Framework install: none needed (pytest, ruff, mypy already in `[dependency-groups] dev`)

*(Existing test infrastructure covers all phase requirements; gaps are evidence-recording items, not missing test files.)*

## Security Domain

> Required when `security_enforcement` is enabled (absent = enabled). `.planning/config.json` has no `security_enforcement` key, so enabled by default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth implemented (single-user, local-only); no login endpoint |
| V3 Session Management | no | No sessions; correlation IDs per request only (middleware.py) |
| V4 Access Control | yes | Single-user/local-only; loopback bind enforced (app.py:39-56) |
| V5 Input Validation | yes | Pydantic settings + contract validation; `extra="forbid"` (settings.py:121-127) |
| V6 Cryptography | no | No cryptography implemented; secrets via SecretStr/env only |
| V13 Malicious Code | yes | Boundary scan blocks broker SDK imports outside gateway (_boundary.py) |
| V14 Business Logic | yes | Fail-closed gate; no execution path (gate.py, nodes.py) |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Order-execution surface creep | Tampering | AST boundary scan (`tests/security/_boundary.py`) fails build on `order_send` etc. |
| Secret in logs/traces | Information Disclosure | structlog `_scrub` + `SecretStr` exclusion from config hash (`logging.py`, `settings.py:401-414`) |
| Non-loopback bind | Information Disclosure / Elevation | `assert_loopback` (app.py:39-56); `ollama_host` loopback validator (settings.py:363-370) |
| Mock data as live | Integrity | Rules.md §1.2; backtest costs declared placeholders (`fills.py:47-55`) |
| Undeclared env var | Elevation | `_reject_undeclared_prefixed_variables` model validator (settings.py:372-381) |
| SSRF via arbitrary URL fetch | Tampering | No arbitrary URL fetch surface; Ollama host loopback-validated only |
| Migration without rollback | Data Loss | All migrations `0001`–`0003` ship `downgrade()` paths |

## Sources

### Primary (HIGH confidence)
- `C:\XauMaster\.planning\ROADMAP.md` lines 175-187 — Phase 8 five success criteria (read this session)
- `C:\XauMaster\Task.md` lines 100-110 — T0801–T0808 (read this session)
- `C:\XauMaster\Security.md` — audit rules, severity rubric, 12 categories, deliverable format (read this session)
- `C:\XauMaster\Rules.md` — mandatory rules §1, §2, §7, §9 (read this session)
- `C:\XauMaster\Schema.md` — §1 conventions, §10 error contract (read this session)
- `C:\XauMaster\Architecture.md` — §7/#8 quality gates, deployment boundary (read this session)
- `C:\XauMaster\apps\api\src\goldmasters_api\app.py` — `assert_loopback`, loopback bind (read this session)
- `C:\XauMaster\apps\api\src\goldmasters_api\settings.py` — SecretStr, loopback Ollama, fail-closed settings, config hash (read this session)
- `C:\XauMaster\src\goldmasters\risk\gate.py` — fail-closed gate, `trade_eligible_levels` (read this session)
- `C:\XauMaster\src\goldmasters\graph\nodes.py` — gate node, assemble_decision, TRADE path (read this session)
- `C:\XauMaster\tests\security\_boundary.py` — FORBIDDEN_CALL_NAMES, SCAN_ROOTS, AST scan (read this session)
- `C:\XauMaster\apps\api\migrations\versions/0001_contract_document.py`, `0002_journal_outcome.py`, `0003_backtest.py` — downgrade() paths (read this session)
- `C:\XauMaster\tests\conftest.py` — throwaway per-run DB fixtures (read this session)
- `C:\XauMaster\scripts\gate` — release/quality gate command list (read this session)
- `C:\XauMaster\scripts/stack` — local stack provision + alembic upgrade head (read this session)
- `C:\XauMaster\apps\api\pyproject.toml`, `packages/contracts\pyproject.toml`, root `pyproject.toml` — dependency versions (read this session)
- `C:\XauMaster\apps\web\package.json` — frontend deps, loopback bind scripts (read this session)
- `C:\XauMaster\Memory.md` — MetaTrader5 not installed, `uv sync --all-packages` note, prior suite evidence (read this session)

### Secondary (MEDIUM confidence)
- `C:\XauMaster\apps\api\src\goldmasters_api\health.py` — bounded health probe, never leaks URL (read this session)
- `C:\XauMaster\apps\api\src\goldmasters_api\middleware.py` — server-side correlation ID (read this session)
- `C:\XauMaster\apps\api\src\goldmasters_api\logging.py` — secret redaction (read this session)
- `C:\XauMaster\services\mt5_adapter\adapter.py` — read-only MT5, `trade_allowed` assertion (read this session)
- `C:\XauMaster\services\mt5_adapter\terminal.py` — lazy `MetaTrader5` import only (read this session)
- `C:\XauMaster\src\goldmasters\backtest\fills.py`, `runner.py`, `metrics.py` — placeholder costs (read this session)

### Tertiary (LOW confidence)
- None — all findings verified from file reads this session. No WebSearch or training-data-only claims remain.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified from `pyproject.toml` / `package.json` read this session.
- Architecture: HIGH — traced actual source files this session.
- Pitfalls: HIGH — all findings from direct file reads this session.
- Rollback paths: HIGH — migration `downgrade()` paths read verbatim this session.

**Research date:** 2026-10-17
**Valid until:** 30 days (stable codebase; fast-moving for dependency versions)

