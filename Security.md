# GoldMasters — Security Review Plan

**Status:** Audit specification only. No source repository or codebase was supplied for inspection. Therefore no actual findings, file paths, line numbers, exploitability claims, or “clean” category conclusions can truthfully be reported yet.

## Audit rules

- Do not modify code during the audit. Report findings and wait for explicit approval before applying fixes.
- Findings must cite exact repository-relative file and line numbers, a reproducible attack path, impact, and a minimal fix.
- If a category cannot be inspected, mark it **Not assessed — evidence unavailable**, not clean.
- Do not use mock findings, guessed paths, invented line numbers, or speculative vulnerability claims.
- Do not print secrets in reports. Identify secret type and location with redacted values.
- Run tests and scanners only within authorized repository scope; record tool/version, command, result, and date.
- Distinguish confirmed vulnerability from potential risk and false positive.

## Severity rubric

- **Critical:** unauthenticated or broadly exploitable compromise, remote code execution, major secret compromise, or high-impact data loss.
- **High:** material data exposure, privilege escalation, or exploitable control bypass with limited prerequisites.
- **Medium:** meaningful security weakness requiring specific conditions or offering constrained impact.
- **Low:** limited impact hardening issue.
- **Informational:** observation or recommendation without a demonstrated vulnerability.

Severity must follow demonstrated impact and exploitability, not scanner labels alone.

## Required audit categories

### 1. Authentication and session handling
Inspect authentication boundaries, session generation/rotation/revocation, expiry, cookie attributes, CSRF protections where applicable, password handling if present, and local-only assumptions.
- Exploit proof: show the route/state transition an attacker can use without valid credentials or with a stolen/reused session.
- Fix: only prescribe after exact implementation is inspected.
- Current status: **Not assessed — source code unavailable.**

### 2. Authorization and cross-user access
Although V1 is intended for personal use, verify whether APIs and storage are actually single-user/local-only. If multiple users or network access are possible, enforce authorization at every object access.
- Test object-ID substitution and direct endpoint access.
- Current status: **Not assessed — source code unavailable.**

### 3. Secrets and client-side exposure
Search source, git history where authorized, build artifacts, environment examples, browser bundles, logs, and deployment configuration for credentials, API tokens, database URLs, and broker credentials.
- Redact secrets in all evidence.
- Never place provider credentials in frontend code or logs.
- Current status: **Not assessed — source code unavailable.**

### 4. Injection: SQL, command, XSS, template, SSRF
Inspect query construction, shell/process calls, rendering of news content, markdown/HTML handling, URL fetching, and any user-controlled file paths.
- Verify parameterized SQL and safe argument arrays; avoid shell interpolation.
- Sanitize/render untrusted news as text; use a restrictive content security policy.
- SSRF review must restrict schemes, hosts, redirects, private-network destinations, and DNS rebinding risks where arbitrary URLs can be fetched.
- Current status: **Not assessed — source code unavailable.**

### 5. API routes and input validation
Inventory all routes and methods; check authentication, authorization, request size limits, schema validation, content types, error handling, and state-changing operations.
- Reject unknown or malformed fields where appropriate; enforce numeric bounds and canonical instrument/provider identifiers.
- Current status: **Not assessed — source code unavailable.**

### 6. Rate limiting and abuse protection
Inspect expensive analysis/backtest routes, login routes if any, provider polling, news ingestion, and model inference endpoints.
- Apply concurrency limits, request timeouts, quotas, and bounded graph retries.
- Local-only deployment reduces exposure but does not replace controls if bound to a LAN or public interface.
- Current status: **Not assessed — source code unavailable.**

### 7. IDOR and object scoping
Try replacing run IDs, journal IDs, backtest IDs, and provider configuration IDs in routes and queries. Confirm ownership/scope is checked server-side.
- Current status: **Not assessed — source code unavailable.**

### 8. CORS, headers, cookies, network binding
Inspect allowed origins, methods, headers, credentials, security headers, cookie flags, TLS assumptions, and host binding.
- Do not use wildcard CORS with credentials.
- Bind local services to loopback by default unless LAN exposure is explicitly required.
- Current status: **Not assessed — source code unavailable.**

### 9. Dependency vulnerabilities and supply chain
Inspect lockfiles and manifests; run ecosystem-native audit tools and a software composition analysis scanner. Verify findings against advisory sources and actual dependency usage.
- Pin direct dependencies appropriately; use lockfiles; avoid blindly upgrading without tests.
- Current status: **Not assessed — dependency files unavailable.**

### 10. Logging and error disclosure
Inspect exceptions, tracing, model prompts/outputs, provider responses, request logs, and browser-visible errors.
- Redact credentials, tokens, personal data, and sensitive configuration.
- Return stable public error codes; keep detailed sanitized diagnostics server-side.
- Current status: **Not assessed — source code unavailable.**

### 11. Trading-specific and agent security
- Ensure no order-placement modules, broker trade permissions, or execution endpoints exist in V1.
- Treat news pages, tool output, retrieved documents, and model responses as untrusted input; prompt injection must not alter system policy or trigger tools outside declared capabilities.
- Enforce typed schemas and deterministic risk/data gates outside the LLM.
- Ensure a model cannot change provider credentials, arbitrary URLs, filesystem paths, or application configuration.
- Prevent data leakage between provider contexts and prevent stale evidence from being represented as current.
- Current status: **Not assessed — source code unavailable.**

### 12. Data storage, backups, and local deployment
Inspect database permissions, filesystem permissions, backup encryption, retention, migration safety, and network exposure. Ensure market/news content and journal notes cannot become executable code.
- Current status: **Not assessed — source code unavailable.**

## Audit deliverable format

For each confirmed finding:

```text
ID: SEC-###
Title:
Severity: Critical | High | Medium | Low | Informational
Confidence: Confirmed | Likely | Needs validation
Category:
File and line: path/to/file.ext:line-line
Preconditions:
Reproduction steps:
Observed impact:
Evidence:
Exact minimal fix:
Regression test:
Status: Open | Approved | Fixed | Verified | Accepted risk
```

## Final report ordering

1. Critical
2. High
3. Medium
4. Low
5. Informational
6. Explicitly clean categories — only after sufficient evidence and tests
7. Not assessed categories and limitations

## Pre-launch checklist

- [ ] Repository commit and branch recorded.
- [ ] Dependency manifests and lockfiles inventoried.
- [ ] Routes and trust boundaries inventoried.
- [ ] Secret scanning completed without disclosing values.
- [ ] Static analysis and dependency scanning results reviewed.
- [ ] Authentication/authorization tests completed where applicable.
- [ ] Input validation and injection tests completed.
- [ ] CORS, headers, cookies, and network binding inspected.
- [ ] Logs and exception responses checked for sensitive data.
- [ ] Agent tool permissions and prompt-injection boundaries tested.
- [ ] No execution capability present in V1.
- [ ] Findings reviewed with user; no fixes applied before approval.
- [ ] Retests and final disposition recorded.
