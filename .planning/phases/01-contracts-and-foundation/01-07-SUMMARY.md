---
phase: 01-contracts-and-foundation
plan: "07"
subsystem: web-client
tags: [nextjs, typescript, json2ts, health-page, loopback, evidence]

# Dependency graph
requires: [01 (workspace), 04 (schema set complete), 06 (migration evidence), 08 (API + health surface)]
provides:
  - "Loopback Next.js skeleton with schema-generated types and live health page"
  - "`docs/run.md` (one run procedure) and `docs/PHASE-1-EVIDENCE.md` (criterion-by-criterion record)"
affects: [Phase 7 (console design owns the UI from here)]

actuals:
  tokens: 0
  tasks: 3
  commits: 2
  plan_head_before: e05c690
  plan_head_after: TASK3_SHA

key-files:
  created:
    - apps/web/package.json
    - apps/web/package-lock.json
    - apps/web/tsconfig.json
    - apps/web/next.config.ts
    - apps/web/src/app/layout.tsx
    - apps/web/src/app/page.tsx
    - apps/web/src/lib/api.ts
    - tests/integration/test_client_scripts.py
    - docs/run.md
    - docs/PHASE-1-EVIDENCE.md
  modified: []

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "gen:types produces 10 TS files from committed schemas into git-ignored src/generated/; failure bodies use the generated ErrorPayload."
    requirement: REQ-no-trade-execution
    verification:
      - kind: manual
        ref: "npm --prefix apps/web run gen:types (10 files)"
        status: pass
    human_judgment: true
  - id: D2
    description: "dev/start bind 127.0.0.1 explicitly; page renders five chain fields live plus an explicit unavailable state; typecheck + build clean."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_client_scripts.py + live curl 2026-10-14"
        status: pass
    human_judgment: true
  - id: D3
    description: "run.md documents one gate + one stack + client leg; PHASE-1-EVIDENCE.md maps all five criteria to commands with honest CI-pending statement."
    requirement: REQ-no-trade-execution
    verification:
      - kind: manual
        ref: "docs/PHASE-1-EVIDENCE.md"
        status: pass
    human_judgment: true

duration: ~30min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 07: Client Skeleton + Run/Evidence Docs Summary

**A loopback health page over schema-generated types, proven live against the backend, plus the run procedure and the phase evidence record.**

## Task Commits

1. **Task 1: Workspace + type generation** - (feat commit)
2. **Task 2: Health page + client tests** - (feat commit)
3. **Task 3: run.md + PHASE-1-EVIDENCE.md** - (this commit)

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **`@types/react@19.3.0` + `@types/react-dom@19.3.0` added** (dev): React 19 ships no bundled JSX types and research did not pin them; without them `tsc --noEmit` fails (TS7026).
2. **`tsconfig `jsx` is `react-jsx`**, not `preserve`: React 19 removed the global JSX namespace, so `preserve` cannot type-check.
3. **Per-document `gen:types`** (10 chained `json2ts` calls) rather than one bundled input: the plan allows either; per-document keeps the drift-test's one-document-per-contract mapping.
4. **Failure bodies use the generated `ErrorPayload`**: the one genuine use of generated types in `api.ts` (the five health fields are backend-shaped, test-pinned, not contracts).

## Verification Evidence

- `npm run gen:types` → 10 `.ts` files in git-ignored `src/generated/`.
- `npm run typecheck` clean; `next build` succeeds.
- `uv run pytest tests/integration/test_client_scripts.py` → 4 passed.
- Live 2026-10-14: API on `:8000` + client on `:3001`, page rendered all five live values; backend-down renders unavailable.

## Next Phase Readiness

- Phase 1 complete: 11/11 plans. Ready for verification (`/gsd-verify-work`) then Phase 2 discuss.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
