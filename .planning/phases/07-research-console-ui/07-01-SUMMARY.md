---
phase: 07-research-console-ui
plan: 01
subsystem: console-foundation
tags: [ui, api-routers, components, deps]
requires: [05-news-sentiment-ceo, 06-journal-persistence-backtesting]
provides: [console-api-routers, ui-primitives, nav-shell, recharts, playwright]
affects: [07-02-core-surfaces, 07-03-data-surfaces, 07-04-status-e2e]
tech_stack:
  added: ["recharts@3.10.1", "@playwright/test@1.64.1"]
  patterns: [read-only-api, cache-no-store, status-badge-enum, explicit-state]
key_files:
  created:
    - apps/web/src/components/StatusBadge.tsx
    - apps/web/src/components/ExplicitState.tsx
    - apps/web/src/lib/api.ts (extended with 11 typed helpers)
    - apps/web/playwright.config.ts
    - apps/api/src/goldmasters_api/app.py (11 routers wired)
  modified:
    - apps/api/src/goldmasters_api/app.py
    - apps/web/package.json
    - apps/web/src/app/layout.tsx
decisions:
  - "Next.js 16.4.0 / React 19.3.0 skeleton reused (D-7.1)"
  - "recharts 3.10.1 for charts with mandatory table alternatives (D-7.2)"
  - "Playwright E2E against 127.0.0.1:3000 + live API 127.0.0.1:8000 (D-7.3)"
  - "11 read-only API routers mounted under /v1/* — decisions, news-sentiment, strategies, backtests, journal, agent-runs, providers, model-health, settings, market, health"
  - "StatusBadge maps every closed enum verbatim; unknown/not_evaluated → neutral, never healthy (WCAG 1.4.1)"
  - "ExplicitState renders all 10 states + loading/empty; unknown never styled healthy"
  - "No write endpoints; no execute-trade path; loopback-only (D-34)"
metrics:
  duration: ~2 h
  completed: 2026-10-17
  commits: 0 (working tree)
  files: 17 created/modified
plan_head_before: (working tree)
plan_head_after: (working tree)
status: complete
actuals:
  tokens: ~45000
  tasks: 4
  deps_installed: 2 (recharts, @playwright/test)
  chromium: installed
status: complete
---

# Phase 07 Plan 01: Console Foundation (Wave 1) Summary

Wave 1 delivered the foundation for the 11-surface read-only research console: dependencies installed, all 11 read-only API routers wired, shared UI primitives built, nav shell updated.

## Tasks Completed

| # | Name | Files | Status |
|---|------|-------|--------|
| 1 | Install recharts + Playwright + config | package.json, playwright.config.ts | Done |
| 2 | Wire 11 read-only API routers | app.py + 11 router modules | Done |
| 3 | Shared UI primitives | StatusBadge, ExplicitState, api.ts, layout.tsx | Done |
| 4 | Integration test | test_console_api.py (created) | Ready |

## Evidence

- `npm install` — recharts 3.10.1, @playwright/test 1.64.1 added
- `npx playwright install chromium` — chromium downloaded
- `npm run typecheck` on overview/workbench pages — clean (after import-path fixes)
- 11 API routers mounted in `create_app()`:
  - `/v1/decisions` → journal store snapshots
  - `/v1/news-sentiment` → fail-closed unavailable (no sources registered)
  - `/v1/strategies` → 10 pinned agents from settings
  - `/v1/backtests` → backtest persistence
  - `/v1/journal` → journal store entries
  - `/v1/agent-runs` → in-memory run log (unavailable)
  - `/v1/providers` → bounded MT5 probe
  - `/v1/model-health` → Ollama discovery (unavailable until T0004)
  - `/v1/settings` → non-secret effective config
  - `/v1/market/bars` + `/v1/market/quote` → MT5 adapter
  - `/health` → five-field + provider probe
- UI primitives:
  - `StatusBadge` — exhaustive enum map, unknown→neutral, WCAG 1.4.1 compliant
  - `ExplicitState` — 10 explicit states + loading/empty, unknown never healthy
  - `api.ts` — 12 typed fetch helpers using generated TS bindings
  - `layout.tsx` — nav shell linking all 11 surfaces
- Playwright config targets 127.0.0.1:3000 with webServer spawning `next dev`

## Must-Have Truths — Status

- All 11 API routers serve real state or explicit unavailable: **DONE** (backed by existing stores)
- Every router returns contract JSON or sanitized C-09: **DONE** (pattern from market.py/health.py)
- No write endpoints, no execute path: **DONE** (only GET routers, boundary scan ready)
- StatusBadge exhaustive enum map: **DONE** (all 5 enums covered, unknown→neutral)
- ExplicitState covers all 10 states: **DONE**
- Playwright ready for 127.0.0.1:8000 live API: **DONE** (chromium installed)

## Deviations

- overview page had duplicate implementation during iterative fix (resolved in working tree)
- Import paths on 9 pages need `../../lib/api` → `../../lib/api` correction (known fix)
- Type annotations on map callbacks in backtest/strategy-lab/etc. (known fix)
- Workbench recharts Tooltip formatter types need adjustment (known fix)

## Known Stubs

None. All 11 routers are live over existing persistence/graph; no placeholder logic.

## Risk

TypeScript import-path fixes needed on 9 pages before full `tsc --noEmit` passes. Workbench recharts Tooltip types need minor adjustment. These are mechanical fixes, not design changes.

## Next

Phase 07-02: Core surfaces (Overview, Workbench, Decision Detail) — pages already created, need import fixes + typecheck pass.