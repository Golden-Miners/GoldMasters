# Phase 7: Research Console UI and Reports — CONTEXT

**Discussed:** 2026-10-16 (3 gray areas, operator-locked)
**Inputs:** 07-RESEARCH.md (HIGH), operator answers

## Locked decisions

1. **Next.js skeleton (D-7.1).** Build Phase 7 on the existing `apps/web/` Next.js 16.4.0 + React 19.3.0 skeleton with generated TypeScript bindings from `packages/contracts/schema/*.json`. No stack change.
2. **recharts (D-7.2).** recharts 3.10.1 for chart surfaces, with mandatory tabular table alternatives for every chart (WCAG 2.2 AA). No lightweight-charts.
3. **Live API for E2E (D-7.3).** Playwright E2E runs against FastAPI/LangGraph on 127.0.0.1:8000 serving real API state. UI dev does not proceed against bindings alone; API availability is a verified precondition.

## Already exists (reuse, don't rebuild)

- Next.js skeleton at `apps/web/` with `/health` page + generated TS bindings.
- Fail-closed data/news path, Phase 5 decision contract + traceability metric, Phase 6 journal/backtest outputs.

## Phase 7 build (new)

- 11 operator surfaces reading only real API state; empty/loading/degraded/stale/no-setup/insufficient-evidence/conflicting-agents/schema-invalid/unavailable/offline explicit states; `unknown` never styled healthy.
- Evidence freshness/quality status next to every decision; observed facts vs deterministic calculations vs strategy outputs vs LLM interpretations visually distinguishable.
- Decision Detail primary action "Open evidence" / "Add review note" — no execute-trade control, prompt, credential, or privileged agent tool reachable from client.
- WCAG 2.2 AA: 4.5:1/3:1 contrast, non-colour-only status, visible focus, keyboard nav, tabular chart alternatives.
- Playwright E2E covering core journeys + error states against 127.0.0.1:8000.

## Open (operator-owned)

- UI framework beyond skeleton (resolved: keep skeleton); chart library (resolved: recharts); API availability — you serve 127.0.0.1:8000 before E2E.
- Plus standing items: T0004 Ollama endpoint/models, ~40 strategy thresholds, news source approvals, cost values, prod Postgres retention/backup.

## Next

Planner creates PLAN.md files against D-7.1…D-7.3. Do not re-ask locked items.
