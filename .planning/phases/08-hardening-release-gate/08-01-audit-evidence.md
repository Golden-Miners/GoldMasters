# 08-01 Audit Evidence — Wave 0 Security Boundary & Dependency Scan

**Phase:** 08-hardening-release-gate  
**Plan:** 01  
**Executed:** 2026-10-17  
**Executor:** gsd-execute-phase subagent (autonomous)  
**Command:** `uv run pytest tests/security -q` and `uv run pytest tests/unit/test_env_example.py -q`  
**Python:** 3.14.7 via `.venv/Scripts/python` / `uv 0.11.15`  
**Repository:** C:\XauMaster (branch `agent-07-01`)  
**No production code changes made; no fixes applied before user approval** (Security.md rule, Rules.md R-07).

---

## 1. AST Boundary Scan (Task 1)

### Command
```
uv run pytest tests/security -q
```

### Result: 8 passed in 1.46s
- `tests/security/test_boundary_scan.py` — 3 passed
- `tests/security/test_boundary_scan_negative.py` — 5 passed

### Forbidden call names (FORBIDDEN_CALL_NAMES)
Scanned over `packages`, `apps`, `src`, `services` roots. Zero hits.

| Forbidden name | Found in tree? |
|---|---|
| order_send | No |
| order_modify | No |
| order_close | No |
| position_close | No |
| place_order | No |
| submit_order | No |
| cancel_order | No |
| close_order | No |
| modify_order | No |
| send_order | No |

### Forbidden adapter calls (FORBIDDEN_ADAPTER_CALLS)
Scanned over `services/mt5_adapter/` tree. Zero hits.

| Forbidden name | Found in adapter tree? |
|---|---|
| symbol_select | No |
| login | No |

### Forbidden import roots (FORBIDDEN_IMPORT_ROOTS)
Scanned over all scan roots. Zero hits.

| Forbidden root | Found? |
|---|---|
| oanda | No |
| ig_trading | No |
| binance | No |
| ccxt | No |

### Broker-package import scoping (ADAPTER_SCOPED_IMPORT_ROOTS = MetaTrader5, mt5)
`MetaTrader5`/`mt5` imports are permitted only at `services/mt5_adapter/terminal.py` (the gateway allowlist path). Confirmed absent from all other files.

### Only broker-surface call: `trade_allowed`
`trade_allowed` (read-only session assertion, investor vs master session check) occurs at:

| File | Line | Context |
|---|---|---|
| services/mt5_adapter/adapter.py | 11 | Docstring: Terminal-field names (``trade_allowed``, ``select``/``visible``) |
| services/mt5_adapter/adapter.py | 208 | `if terminal is None or not hasattr(terminal, "trade_allowed"):` |
| services/mt5_adapter/adapter.py | 211 | `"terminal descriptor lacks trade_allowed (must-verify-first, RISK-03)",` |
| services/mt5_adapter/adapter.py | 215 | `if bool(terminal.trade_allowed):` → refuse if master session |

**Deviation:** Plan cited `services/mt5_adapter/terminal.py:215` for `trade_allowed`. The file `terminal.py` is only 168 lines and does not contain `trade_allowed`. The actual location is `services/mt5_adapter/adapter.py:215`. No code change — citation correction only, documented here.

### Loopback bind guard (D-34)
`apps/api/src/goldmasters_api/app.py:39-56` — `assert_loopback(host)`:
- Accepts `127.0.0.1`, `::1`, `localhost` (resolves to loopback only)
- Raises `ValueError` for any non-loopback host
- Called at startup in `lifespan` (line 63): `assert_loopback(settings.bind_host)`
- **Confirmed present and correct.**

### Ollama loopback validator
`apps/api/src/goldmasters_api/settings.py:363-370` — `_ollama_host_loopback_only`:
- Field validator on `ollama_host` (mode="after")
- Requires scheme http/https and hostname in `127.0.0.1`, `::1`, `localhost`
- Raises `ValueError` for non-loopback endpoints
- Default: `http://127.0.0.1:11434` (line 358)
- **Confirmed present and correct.**

---

## 2. Security.md Audit Categories 1-12

Each category recorded as assessed-with-evidence or "Not assessed — evidence unavailable" with named missing precondition. No uninspected category marked "clean" (Security.md rule).

| # | Category | Status | Evidence / Missing precondition |
|---|---|---|---|
| 1 | Authentication and session handling | Not assessed — evidence unavailable | No auth routes exist in V1 (signals-only, local-only); no authentication implementation to inspect |
| 2 | Authorization and cross-user access | Assessed with evidence | Single-user/local-only; loopback bind only (app.py:39-56); no multi-user endpoints |
| 3 | Secrets and client-side exposure | Assessed with evidence | `.env.example`: `GOLDMASTERS_PROVIDER_API_KEY=` empty; no secrets in manifests/lockfiles/config (see Section 3) |
| 4 | Injection: SQL, command, XSS, template, SSRF | Assessed with evidence | SQLAlchemy parameterized queries; no shell interpolation; Ollama host loopback-validated (settings.py:363-370); no arbitrary URL fetch surface |
| 5 | API routes and input validation | Assessed with evidence | FastAPI + Pydantic `Settings` with strict validation; `extra="forbid"`; declared config keys only |
| 6 | Rate limiting and abuse protection | Assessed with evidence | Graph node timeout 60s (GOLDMASTERS_GRAPH_NODE_TIMEOUT_SECONDS), max 2 transient retries (GOLDMASTERS_GRAPH_NODE_MAX_RETRIES), concurrency unset (capped at eligible set) |
| 7 | IDOR and object scoping | Not assessed — evidence unavailable | Single-user/local-only deployment; no cross-user object model implemented yet |
| 8 | CORS, headers, cookies, network binding | Assessed with evidence | Loopback bind only (app.py:39-56); bind_host default 127.0.0.1 (.env.example line 4, config line 5) |
| 9 | Dependency vulnerabilities and supply chain | Assessed with evidence | No secret terms in manifests/lockfiles; all deps pinned; no order-capable dependency terms (test_dependencies_match_allowlist passed) |
| 10 | Logging and error disclosure | Not assessed — evidence available but not exhaustively inspected | structlog configured; redaction via `_scrub`; full log audit not in scope of this plan |
| 11 | Trading-specific and agent security | Assessed with evidence | Zero order-execution call names (boundary scan, Section 1); no `order_send`/`order_modify`/`order_close`/etc.; `trade_allowed` read-only assertion fails closed on master session (adapter.py:215) |
| 12 | Data storage, backups, and local deployment | Not assessed — evidence unavailable | PostgreSQL cluster not running on this host; backup/restore not tested in this plan (see 08-03) |

---

## 3. Dependency / Secret Scan (Task 2)

### Command
```
uv run pytest tests/unit/test_env_example.py -q
```
Plus manual manifest/lockfile scan.

### Result: 6 passed

### Manifests and lockfiles scanned
| File | Secret-ish terms (api_key, secret, password, token, private_key) |
|---|---|
| pyproject.toml (root) | None |
| apps/api/pyproject.toml | None |
| packages/contracts/pyproject.toml | None |
| apps/web/package.json | None |
| uv.lock | None |
| package-lock.json (root) | Does not exist |

### .env.example secret field check
| Field | Value | Status |
|---|---|---|
| GOLDMASTERS_PROVIDER_API_KEY | (empty) | EMPTY — placeholder only, no real secret |

All other `.env.example` fields are non-secret configuration (bind host/port, database URL with `CHANGE_ME` placeholder, instrument IDs, timeframes, graph bounds, Ollama host). `CHANGE_ME` appears only in `GOLDMASTERS_DATABASE_URL` as a documented placeholder.

### config/goldmasters.yaml
No `api_key`, `password`, or `secret` values. Declares no required keys (database_url and mt5_server_timezone stay environment-only). `bind_host: 127.0.0.1`, `bind_port: 8000`.

### tests/unit/test_env_example.py assertions (all passed)
- `test_env_example_covers_every_key` — .env.example covers every Settings model field
- `test_env_example_holds_no_real_secret` — `GOLDMASTERS_PROVIDER_API_KEY == ""`
- `test_committed_files_carry_no_real_secret` — no `api_key`/`password`/`secret` in goldmasters.yaml; `.env.example` secret field empty
- `test_document_parses_with_non_secret_defaults_only` — bind_host == "127.0.0.1", bind_port == 8000
- `test_document_supplies_defaults_env_wins` — env overrides document defaults
- `test_document_keys_are_model_subset` — document keys ⊆ Settings model fields

---

## 4. Fixture Scan (Task 2)

Scanned `src/`, `apps/`, `services/`, `packages/` for mock/sample/fixture/placeholder/dummy/fake_data/test_data/hardcoded terms (excluding `tests/` and `__pycache__`).

### Results
| File | Term | Context | Assessment |
|---|---|---|---|
| src/goldmasters/backtest/fills.py | placeholder | Declared placeholder costs (D-6.1); `placeholder_costs()` raises `ValueError` if used unconfirmed | Declared placeholder, fail-closed — not fake data presented as live |
| src/goldmasters/backtest/metrics.py | placeholder | Cost marker `"costs placeholder per D-6.1, not authoritative"` | Declared placeholder marker |
| src/goldmasters/backtest/runner.py | placeholder | Metric definition suffix "; costs placeholder per D-6.1, not authoritative" | Declared placeholder marker |
| src/goldmasters/backtest/__init__.py | placeholder | Exports `placeholder_costs` | Declared placeholder export |
| services/mt5_adapter/validation.py | mock | Comment: "without clock mocking" (unit-testability note) | Not fixture data |
| apps/api/src/goldmasters_api/settings.py | placeholder | Validator names `_empty_placeholder_means_unset`, `_risk_placeholders_positive` | Not fixture data |
| apps/web/src/app/backtest/page.tsx | placeholder | UI text: "placeholder-cost marker (D-6.1)" | UI description of declared placeholder |

**Conclusion:** No mock/sample/fixture market/news/sentiment/backtest/signal data in production paths. All "placeholder" references are declared placeholders (D-6.1) that fail closed (`ValueError` on use) or are UI text describing the marker. Fixtures are confined to labelled tests only.

---

## 5. scripts/gate Command List (Task 2)

Read `scripts/gate` (37 lines, `#!/bin/sh`):

### Full gate (`sh scripts/gate`)
| Step | Command |
|---|---|
| 1 | `ruff format --check .` |
| 2 | `ruff check .` |
| 3 | `mypy --strict .` |
| 4 | `uv run pytest` (full test suite) |

### --fast subset (`sh scripts/gate --fast`)
| Step | Command |
|---|---|
| 1 | `ruff format --check` (changed `.py` files only) |
| 2 | `ruff check` (changed `.py` files only) |
| 3 | `mypy --strict .` (workspace) |
| 4 | `uv run pytest tests/security -q` |

Exit code 0 = PASS; any failure = non-zero exit. Hosted CI not required per operator decision; local `scripts/gate` + recorded output suffices.

---

## 6. Must-Have Truths — Status

| Requirement | Status | Evidence |
|---|---|---|
| Zero order-execution call names | PASS | Boundary scan: 0 hits across packages/apps/src/services |
| Only `trade_allowed` read-only check | PASS | `services/mt5_adapter/adapter.py:215` (plan cited terminal.py:215 — deviation documented) |
| No real secrets in .env.example | PASS | `GOLDMASTERS_PROVIDER_API_KEY=` empty; test_env_example.py 6 passed |
| No real secrets in manifests/lockfiles/config | PASS | Scan of pyproject.toml ×3, package.json, uv.lock — none found |
| No mock/sample data in production paths | PASS | Fixture scan — only declared D-6.1 placeholders, fail-closed |
| Loopback bind guard confirmed | PASS | `app.py:39-56` `assert_loopback` |
| Ollama loopback validator confirmed | PASS | `settings.py:363-370` `_ollama_host_loopback_only` |
| scripts/gate documented | PASS | Full gate + --fast subset recorded |
| Security.md categories 1-12 recorded | PASS | Assessed-with-evidence or "Not assessed — evidence unavailable" |

---

## 7. Deviations from Plan

1. **Citation correction:** Plan states `trade_allowed` at `services/mt5_adapter/terminal.py:215`. Actual location is `services/mt5_adapter/adapter.py:215` (terminal.py is 168 lines). No code change; citation documented here.
2. **package-lock.json:** Plan lists `package-lock.json` as a scan target. No root-level `package-lock.json` exists (only `apps/web/node_modules/package-lock.json`, which is not committed config). Noted for accuracy.
3. **Pre-existing working-tree changes:** `apps/api/src/goldmasters_api/app.py`, `tests/integration/test_console_api.py`, `tests/unit/test_graph_failure_policy.py` show as modified in git status but were not changed by this execution. Not committed as part of this plan.

---

## 8. Known Stubs

None. All boundary scan, secret scan, fixture scan, and gate documentation is complete with recorded evidence.

---

## 9. Self-Check

- `tests/security` → 8 passed ✓
- `tests/unit/test_env_example.py` → 6 passed ✓
- Boundary scan: zero forbidden call names ✓
- `.env.example`: no real secrets ✓
- Fixture scan: no mock/sample data in production paths ✓
- `scripts/gate`: command list documented ✓
- Loopback bind + Ollama loopback: confirmed ✓

**Self-Check: PASSED**
