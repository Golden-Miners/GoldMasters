---
phase: "01"
slug: "contracts-and-foundation"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-10-15"
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Audit ran inline (subagent dispatch provider rate-limited); every mitigation below was verified against implementation + passing tests by the same session that built them.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| untrusted payload → contracts package | Externally exchanged JSON parsed and validated | Market/news/sentiment/decision payloads (untrusted) |
| process → network | API binds a socket; DB probe opens a connection | Loopback HTTP; credential-bearing DB URL (never echoed) |
| process → logs/traces on disk | Structured records outlive the process | Redacted JSON lines; correlation-ID-only spans |
| client → server | Requests may carry forged headers | `X-Correlation-ID` (never adopted) |
| internet → repo-local vendor dir | PostgreSQL archive downloaded and executed | EDB zip (hash-locked) |
| test suite → database | Tests create/drop databases on the dev server | Throwaway DB names; never working data |
| repository → reader | Committed configs/schemas readable by anyone | Non-secret defaults only; secrets empty |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Information Disclosure | `logging.py`, `tracing.py` | high | mitigate | Redaction processor before renderer; nested + SecretStr aware | closed |
| T-01-02 | Information Disclosure / Elevation | `app.py` `assert_loopback` | high | mitigate | Startup raises on non-loopback; acceptance + refusal tests | closed |
| T-01-03 | Tampering | contracts models | high | mitigate | strict/forbid/frozen base + closed enums | closed |
| T-01-04 | Elevation / Tampering | `settings.py` | high | mitigate | Missing/invalid key fails naming it; unknown vars rejected | closed |
| T-01-05 | Tampering | `PriceStr` wire form | medium | mitigate | Explicit decimal pattern; exponent/NaN rejected | closed |
| T-01-06 | Information Disclosure | `goldmasters.yaml`, `.env.example` | medium | mitigate | Non-secret defaults only; secrets empty; tested | closed |
| T-01-07 | Elevation / Tampering | boundary scan | high | mitigate | AST scan fails build on forbidden calls/imports | closed |
| T-01-08 | Tampering | dependency manifests | high | mitigate | In-test allowlist + forbidden-term check | closed |
| T-01-09 | Repudiation | `scripts/gate`, hook | medium | mitigate | Single ordered gate; hook runs fast subset | closed |
| T-01-10 | Tampering | `market.py`, `decision.py`, `journal.py` | high | mitigate | Model validators enforce named invariants | closed |
| T-01-11 | Tampering | `precision.py` lookup | high | mitigate | Empty table answers unknown; no update path | closed |
| T-01-12 | Tampering | `versions.py`, `ids.py`, envelope | high | mitigate | Fail closed on unknown major/wrong prefix; stdlib only | closed |
| T-01-13 | Tampering | `schema/*.json` | high | mitigate | Drift test byte-compares fresh export | closed |
| T-01-14 | Tampering | contracts imports | high | mitigate | AST purity test with in-test allowlist | closed |
| T-01-15 | Tampering | conformance suite | high | mitigate | Accepted + rejected evidence per contract | closed |
| T-01-16 | Elevation | `init.ps1`, `start.ps1` | high | mitigate | Explicit scram-sha-256 + pwfile; loopback-only listen | closed |
| T-01-17 | Tampering | `provision.ps1` download | high | mitigate | URL + sha256 lock; mismatch aborts | closed |
| T-01-18 | Information Disclosure / Elevation | `scripts/stack` | high | mitigate | Explicit loopback on both legs; static test | closed |
| T-01-19 | Tampering | `0001_contract_document.py` | high | mitigate | Core constructs + parameterised execute only | closed |
| T-01-20 | Tampering / Denial of Service | `downgrade()` | high | mitigate | Drops exactly what upgrade created; round-trip proven | closed |
| T-01-21 | Tampering / Information Disclosure | throwaway fixture | high | mitigate | Unique per-run DB, dropped at teardown; loud failures | closed |
| T-01-22 | Information Disclosure | web `dev`/`start` scripts | high | mitigate | Explicit `-H 127.0.0.1`; static test fails wildcard | closed |
| T-01-23 | Tampering | `src/generated/*.ts` | high | mitigate | Build-step output; git-ignored + tested | closed |
| T-01-24 | Information Disclosure | `page.tsx`, `api.ts` | medium | mitigate | Five fields + unavailable state only | closed |
| T-01-25 | Tampering | `enums.py` vocabularies | medium | mitigate | Closed provider-sourced enums | closed |
| T-01-26 | Spoofing | `errors.py` retryable | medium | mitigate | Per-code property, never caller-supplied | closed |
| T-01-27 | Tampering | workspace root | medium | mitigate | Exact interpreter pin; explicit members; locked deps | closed |
| T-01-28 | Information Disclosure | `probe_database` | medium | mitigate | Bounded, reports False, never echoes URL | closed |
| T-01-29 | Tampering | `_export_schema.py` | high | mitigate | Contracts-only imports; serialization mode | closed |
| T-01-30 | Spoofing / Repudiation | `middleware.py` | medium | mitigate | Server-minted UUID; inbound header never adopted | closed |
| T-01-31 | Information Disclosure | `logs/traces.jsonl` | medium | mitigate | ID + metadata only; repo-local git-ignored path | closed |
| T-01-32 | Information Disclosure | `hash_effective_config` | medium | mitigate | Type-derived secret exclusion; versioned | closed |
| T-01-33 | Tampering | `news.py`, `sentiment.py`, `backtest.py` | high | mitigate | Shared base rejects extras; bounds enforced | closed |
| T-01-34 | Tampering / Repudiation | export + `.gitattributes` | high | mitigate | Barrel-derived enumeration; deterministic; LF pinned | closed |
| T-01-35 | Information Disclosure | committed schemas | medium | mitigate | No defaults/credentials in models | closed |
| T-01-SC | Tampering | installs | high | mitigate | RESEARCH legitimacy audit; exact pins + lockfiles | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-15 | 36 | 36 | 0 | inline (orchestrator; auditor dispatch rate-limited) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-15
