# Phase 7: Research Console UI and Reports - Research

**Researched:** 2026-10-16
**Domain:** Read-only Next.js research console over real FastAPI/LangGraph API state; 11 operator surfaces; explicit evidence states; WCAG 2.2 AA; Playwright E2E coverage; no trade execution
**Confidence:** HIGH

## Summary

Phase 7 delivers the read-only research console described in ROADMAP.md §156-168 and Prd.md §6.7. The console reads **only** real API state (Next.js App Router skeleton already exists at `apps/web/`, with generated TypeScript bindings from the committed JSON Schema contracts under `packages/contracts/schema/` and a `/health` page at `apps/web/src/app/page.tsx`) and offers **no execution action**. The operator reviews instruments, decisions, news/sentiment, strategies, backtests, journal, agent runs, providers, and model/system health across eleven surfaces.

The governing constraints are locked and non-negotiable: (1) all eleven surfaces render live API state, never placeholder/sample data presented as live; (2) evidence freshness and quality status appear next to every decision; (3) observed facts, deterministic calculations, strategy outputs, and LLM interpretations are visually distinguishable; (4) the ten explicit states render (empty, loading, degraded, stale, no-setup, insufficient-evidence, conflicting-agents, schema-invalid, unavailable, offline) and `unknown` is never styled healthy; (5) a provider outage shows no market data; (6) the Decision Detail primary action is "Open evidence" or "Add review note" — no execute-trade control, prompt, credential, or privileged agent tool is reachable from the client; (7) keyboard navigation, visible focus, non-colour-only status, tabular chart alternatives, and WCAG 2.2 AA contrast are verified; (8) Playwright covers core journeys and error states. Phase 7 depends on Phase 6 (journal/backtest persistence) and Phase 5 (CEO decision contract + traceability metric), both of which exist as contracted code this session.

**Primary recommendation:** Build the eleven surfaces on the existing Next.js 16.4.0 / React 19.3.0 App Router skeleton using Server Components for data fetching (fetch with `cache: "no-store"` so live state is never cached as "fresh") and `'use client'` boundaries only for interactive widgets; reuse the closed contract vocabularies (Decision, AgentRunStatus, EvidenceStatus, QualityStatus, Direction) as the single source of truth for every status badge; add `recharts` 3.10.1 (MIT, legitimacy `OK`) as the standard chart library with a mandatory tabular data-table alternative for every chart; add Playwright `@playwright/test` 1.64.1 for E2E coverage of core journeys and error states; gate every package install behind a `checkpoint:human-verify` because package names originating outside authoritative docs are `[ASSUMED]` even when registry-verified. The UI framework/stack choice beyond the skeleton is **operator-owned** (Memory.md open decision) until the user confirms it.

## User Constraints

No `*-CONTEXT.md` exists for Phase 7 (only phases 01 and 05 carry one), so there are no discuss-phase locked decisions to copy verbatim. The constraints below are drawn from ROADMAP.md, Prd.md, Design.md, Rules.md, and Schema.md — all read this session — and are treated as locked, non-negotiable requirements for this phase:

- **Research-only boundary (locked):** V1 is research and decision support only; no order placement, modification, or closure; no broker-trading credentials; a `TRADE` result is a qualified research candidate requiring manual review, not an order [VERIFIED: Prd.md §3, §6.7; Rules.md R-02; ROADMAP.md criterion 4].
- **Eleven surfaces (locked):** Overview, Instrument Workbench, Decision Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health, System Health — all reachable, all rendering live API state [VERIFIED: Prd.md §6.7 line 159; Design.md §4 lines 52-62; ROADMAP.md criterion 1].
- **No placeholder/live confusion (locked):** Never render placeholder, mock, fixture, or sample market/news/sentiment/backtest/signal data as live; missing data is labelled `unknown`/`unavailable` [VERIFIED: Prd.md §3 non-goal 3, §6.7 line 162; Rules.md R-01 lines 1-2, 8; ROADMAP.md criterion 2].
- **Freshness/quality next to every decision (locked):** Evidence freshness and quality status appear next to every decision [VERIFIED: Prd.md §6.7 line 160; Design.md principle 1; ROADMAP.md criterion 2].
- **Four data kinds visually distinguishable (locked):** Observed facts, deterministic calculations, strategy outputs, and LLM interpretations are visually distinguishable [VERIFIED: Prd.md §6.7 line 161; Rules.md R-01 line 4; Schema.md §1 line 14].
- **Explicit states (locked):** empty, loading, degraded, stale, no-setup, insufficient-evidence, conflicting-agents, schema-invalid, unavailable, offline all render explicitly; `unknown` is never styled healthy [VERIFIED: Design.md §8 lines 143-153; ROADMAP.md criterion 3; Schema.md enums.py QualityStatus `not_evaluated` is not a healthy value].
- **Provider outage shows no market data (locked):** A provider outage shows no market data; fail-closed, never synthesised [VERIFIED: src/goldmasters/data/news/base.py `fetch_coverage` fail-closed lines 194-217; apps/web/src/app/page.tsx shows "No market data is shown because the backend cannot be reached" lines 10-14; ROADMAP.md criterion 3].
- **Read-only Decision Detail (locked):** Primary action is "Open evidence" or "Add review note" — never "Execute trade"; no execute-trade control, prompt, credential, or privileged agent tool reachable from the client [VERIFIED: Prd.md §6.7 line 162; Design.md §6 line 109; ROADMAP.md criterion 4; Rules.md R-02].
- **Accessibility (locked):** WCAG 2.2 AA; body text >= 4.5:1, large text >= 3:1, non-text indicators >= 3:1; full keyboard operation with visible focus and logical focus order; status uses text/icon plus colour (never colour alone); charts have accessible names and tabular alternatives; respect reduced motion, zoom to 200%, high contrast [VERIFIED: Design.md §10 lines 163-173; W3C WCAG 2.2 quickref criteria 1.4.1/1.4.3/1.4.11/2.1.1/2.4.7/2.4.13].
- **Playwright E2E (locked):** Playwright coverage of core journeys and their error states; test error states, not just the happy path [VERIFIED: ROADMAP.md criterion 5; Design.md §10; Rules.md R-08 line 4; Architecture.md §8 line 240].
- **Bindings read only real API state (locked):** Next.js skeleton + TypeScript generation from committed schema + health page; the client must not call MT5 or Ollama directly from the browser [VERIFIED: apps/web/src/lib/api.ts `fetchHealth`; Architecture.md §2 Frontend lines 53-54].
- **UI framework/stack beyond skeleton is operator-owned (open):** Marked unresolved in Memory.md; researcher recommendation only, not a locked decision [VERIFIED: Memory.md open decisions].
- **No invented numbers/APIs/data (locked):** Never invent market prices, candles, volume, news, sentiment, backtest results, test output, file paths, APIs, package versions, or tool availability [VERIFIED: Rules.md R-01 lines 1, 7].

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Eleven console surfaces (Overview … System Health) | Browser / Client | Frontend Server (SSR) | React components render in the browser; pages are served by the Next.js App Router on loopback [VERIFIED: apps/web/src/app/layout.tsx, page.tsx; Architecture.md §2 Frontend] |
| Live data fetching + health | Frontend Server (SSR) | API / Backend | Server Components fetch `http://127.0.0.1:8000` via `fetch` with `cache: "no-store"`; the API owns orchestration/persistence [VERIFIED: apps/web/src/lib/api.ts; Architecture.md §2 Backend] |
| Chart rendering (Workbench, Backtest Results) | Browser / Client | — | Client-side SVG/canvas charts; every chart paired with a tabular alternative for WCAG [RECOMMENDATION — see Standard Stack] |
| Status / enum vocabularies | API / Backend | Browser / Client | Closed enums (Decision, AgentRunStatus, EvidenceStatus, QualityStatus, Direction) defined in `goldmasters_contracts`; generated TS bindings consumed by the UI [VERIFIED: packages/contracts/src/goldmasters_contracts/enums.py; apps/web/src/generated/*.ts] |
| Decision record construction | API / Backend | — | `assemble_decision` (graph/nodes.py) is the sole constructor; UI only displays it [VERIFIED: src/goldmasters/graph/nodes.py:389-467] |
| Traceability metric display | API / Backend (log line) | Browser / Client | Phase 5 `log_traceability` emits operator-visible log line; console surface for the metric is Phase 7 [VERIFIED: src/goldmasters/graph/traceability.py:112-128; ROADMAP.md Phase 5 criterion 5] |
| Journal / backtest read | API / Backend | Database / Storage | Append-only journal store + BacktestRecord persisted by Phase 6; UI reads via API [VERIFIED: src/goldmasters/journal/store.py; src/goldmasters/backtest/runner.py] |
| Provider / model / system health | API / Backend | Browser / Client | Health endpoint + provider/model status surfaces; UI reads API state only [VERIFIED: apps/web/src/app/page.tsx; src/goldmasters/graph/role_nodes.py] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.4.0 | App Router framework; Server Components, routing, API consumption | Already the pinned skeleton stack; `engines.node >= 22.19`; loopback-only dev server [VERIFIED: apps/web/package.json:7, 17; `npm view next@16.4.0 version` → 16.4.0] |
| React | 19.3.0 | UI library; client/server component boundary via `'use client'` | Pinned in skeleton; React 19 server/client reference confirmed [VERIFIED: apps/web/package.json:18-19; `npm view react@19.3.0 version` → 19.3.0] |
| TypeScript | 7.0.2 | Static typing; generated contract bindings | Pinned devDependency; `tsc --noEmit` typecheck script [VERIFIED: apps/web/package.json:26] |
| json-schema-to-typescript | 16.0.0 | Generate TS from committed JSON Schema (`gen:types` script) | Already wired into `package.json` `gen:types` over `packages/contracts/schema/*.json` [VERIFIED: apps/web/package.json:14, 25] |
| recharts | 3.10.1 | Charting (Workbench candles/lines, Backtest equity/drawdown) | React-native SVG (DOM nodes, keyboard/screen-reader friendly), MIT, 54.9M weekly downloads, legitimacy `OK` [ASSUMED package name — discovered via training, not authoritative doc; version/license/repo [VERIFIED: npm view recharts → 3.10.1 MIT, repo github.com/recharts/recharts, 54,913,675 wk downloads]; legitimacy gate [VERIFIED: gsd package-legitimacy → OK]] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Playwright / @playwright/test | 1.64.1 (latest) | E2E tests for core journeys and error states | Criterion 5 coverage; not yet installed in `apps/web/node_modules` [VERIFIED: `npm view playwright version` → 1.64.1; probe of `apps/web/node_modules` → playwright absent] |
| chart.js + react-chartjs-2 | 4.5.1 / 5.3.1 | Canvas charting alternative | If the operator prefers a canvas/financial library; harder to make WCAG-accessible than SVG; tabular alternative still required [ASSUMED names; version/license [VERIFIED: npm view → chart.js 4.5.1 MIT, react-chartjs-2 5.3.1 MIT]; legitimacy [VERIFIED: gsd gate → OK for both]] |
| lightweight-charts | 5.2.1 | Financial candlestick alternative | TradingView-native candlesticks for the Instrument Workbench; canvas-based (accessibility risk — pair with table alternative); Apache-2.0 [ASSUMED name; version/license [VERIFIED: npm view → 5.2.1 Apache-2.0]; legitimacy [VERIFIED: gsd gate → OK]] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| recharts (SVG) | chart.js + react-chartjs-2 (canvas) | Canvas needs extra ARIA + a11y work; SVG is closer to WCAG 2.2 AA out of the box |
| recharts | lightweight-charts | Native candlesticks suit price charts, but canvas = weaker keyboard/screen-reader support |
| Playwright E2E | hand-rolled browser automation | Hand-rolled lacks auto-wait, tracing, parallelism, error-state reliability [VERIFIED: context7 /microsoft/playwright key capabilities] |
| Contract-generated TS bindings | hand-written TS interfaces | Hand-written bindings drift from `packages/contracts/schema/*.json`; `gen:types` pins them [VERIFIED: apps/web/package.json:14] |

**Installation:**
```bash
# Run inside apps/web/
npm install recharts
npm install -D playwright @playwright/test
npx playwright install --with-deps chromium
```

**Version verification:** `next@16.4.0` and `react@19.3.0` confirmed on npm registry [VERIFIED: npm view]. `recharts` 3.10.1 MIT confirmed [VERIFIED: npm view]. Playwright 1.64.1 confirmed [VERIFIED: npm view]. All other package names are `[ASSUMED]` until operator confirmation.

## Package Legitimacy Audit

> Required because this phase installs external packages. The Package Legitimacy Gate was run before this section.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| recharts | npm | ~9 yrs (first publish older; latest 2026-07-25) | 54.9M/wk | github.com/recharts/recharts | OK | Approved (name `[ASSUMED]` — gate OK) |
| chart.js | npm | ~10 yrs (latest 2025-10-13) | 12.7M/wk | github.com/chartjs/Chart.js | OK | Alternative — Approved (name `[ASSUMED]`) |
| react-chartjs-2 | npm | ~8 yrs (latest 2025-10-27) | 4.6M/wk | github.com/reactchartjs/react-chartjs-2 | OK | Alternative — Approved (name `[ASSUMED]`) |
| lightweight-charts | npm | ~6 yrs (latest 2026-08-12) | 1.25M/wk | github.com/tradingview/lightweight-charts | OK | Alternative — Approved (name `[ASSUMED]`) |
| playwright | npm | ~9 yrs (latest 1.64.1) | — | github.com/microsoft/playwright | OK | Dev dependency — Approved (name `[CITED: context7 /microsoft/playwright]`) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Note:** `recharts`, `chart.js`, `react-chartjs-2`, `lightweight-charts` names originate from training/non-authoritative sources, so each is tagged `[ASSUMED]` per the package-name provenance rule even though `npm view` + legitimacy gate returned `OK`. The planner must insert a `checkpoint:human-verify` task before each install. No `postinstall` network/filesystem signals were flagged [VERIFIED: gsd package-legitimacy signals `postinstall: null` for all four].

## Architecture Patterns

### System Architecture Diagram

```
Browser / Client (React, Next.js App Router, loopback 127.0.0.1:3000)
        |
        | fetch /health  (cache: no-store)
        v
Frontend Server (SSR)  --->  API / Backend (FastAPI, 127.0.0.1:8000)
        |                          |
        |                          v
        |                   LangGraph run (typed state, per-node status)
        |                          |
        |                          v
        |                   PostgreSQL (journal, backtest, decisions)
        |
        v  (display only)
Eleven surfaces: Overview | Workbench | Decision Detail | News & Sentiment |
Strategy Lab | Backtest Results | Journal | Agent Runs | Data Providers |
Settings/Model Health | System Health
        ^
        v
[read-only display: facts / calculations / strategy outputs / LLM interpretations,
 each with freshness + quality status; no execute-trade control]
```

Data flow: the operator opens a surface → Next.js Server Component fetches real API state via `fetch` (`cache: "no-store"`) → the API returns contract-shaped JSON (generated TS bindings) → the UI renders facts/calculations/strategy outputs/LLM interpretations with freshness + quality badges. No write path, no trade path, no direct MT5/Ollama access from the browser [VERIFIED: apps/web/src/lib/api.ts; Architecture.md §2 Frontend lines 53-54].

### Recommended Project Structure

```
apps/web/
├── src/
│   ├── app/                    # Next.js App Router pages (11 surfaces + health)
│   │   ├── layout.tsx          # EXISTING — metadata, shell
│   │   ├── page.tsx            # EXISTING — /health page
│   │   ├── overview/, workbench/, decision/, news-sentiment/,
│   │   │   strategy-lab/, backtest/, journal/, agent-runs/,
│   │   │   data-providers/, settings/, system-health/
│   ├── generated/              # EXISTING — TS from contracts schema (gen:types)
│   ├── lib/                    # EXISTING — api.ts (fetchHealth)
│   │   └── api.ts              # thin typed fetch wrapper; no hand-rolled client
│   ├── components/             # NEW — StatusBadge, DecisionBanner, FreshnessIndicator,
│   │   │                         RuleCheckTable, PriceLevelPanel, EvidenceRow,
│   │   │                         ChartWithTable, DataTable, TracePanel, SourceLink
│   ├── hooks/                  # NEW — useApi, usePoll (bounded, no fake real-time)
│   └── tests/                  # NEW — Playwright e2e (core journeys + error states)
├── playwright.config.ts        # NEW
├── package.json                # EXISTING — add recharts, playwright devDeps
└── tsconfig.json               # EXISTING
```

### Pattern 1: Read-only API fetch with `cache: "no-store"`

**What:** Every page fetches API state with `fetch(..., { cache: "no-store" })` so the UI never presents cached/stale data as live; the `/health` page already models this (abort after 5s, "API unreachable" → "No market data is shown") [VERIFIED: apps/web/src/app/page.tsx lines 3-16, 10-14; apps/web/src/lib/api.ts lines 23-42; Context7 Next.js fetch `cache` options [CITED: context7 /vercel/next.js]].
**When to use:** All eleven surfaces; never `force-cache` for decision-relevant data.
**Example:**
```tsx
// Source: apps/web/src/lib/api.ts:23-42 (adapted pattern)
export async function fetchHealth(timeoutMs = 5000): Promise<HealthResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      const failure = (await response.json().catch(() => null)) as ErrorPayload | null;
      return { available: false, reason: `API answered ${response.status}${failure?.message ? `: ${failure.message}` : ""}` };
    }
    return { available: true, health: (await response.json()) as HealthBody };
  } catch {
    return { available: false, reason: "API unreachable" };
  } finally {
    clearTimeout(timer);
  }
}
```

### Pattern 2: Status badge — text + icon + colour (never colour alone)

**What:** Map each closed enum verbatim to a labelled badge; colour is supplementary only [VERIFIED: packages/contracts/src/goldmasters_contracts/enums.py:37-128; Design.md §7 `StatusBadge` line 121; Design.md §10 line 172 "never colour alone"; W3C WCAG 1.4.1 Use of Color [CITED: https://www.w3.org/WAI/WCAG22/quickref/]].
**When to use:** Every decision freshness/quality badge, agent status, provider health, model health.
**Enum values used verbatim** [VERIFIED: enums.py lines shown]:
- `Decision`: `TRADE`, `NO_TRADE`, `INSUFFICIENT_DATA` [VERIFIED: enums.py:37-43]
- `AgentRunStatus`: `queued`, `running`, `ok`, `no_setup`, `insufficient_data`, `skipped`, `error`, `timed_out`, `cancelled` [VERIFIED: enums.py:45-56]
- `EvidenceStatus`: `valid`, `stale`, `missing`, `conflicted`, `invalid`, `unavailable` [VERIFIED: enums.py:59-67]
- `QualityStatus`: `ok`, `stale`, `duplicate`, `gap`, `malformed`, `disconnected`, `missing-history`, `unsupported`, `not_evaluated` [VERIFIED: enums.py:97-113]
- `Direction`: `long`, `short`, `neutral`, `unknown` [VERIFIED: enums.py:70-77]

**Example:**
```tsx
// Conceptual: badge keyed off verbatim enum value; `unknown`/`not_evaluated`
// renders neutral, never `positive`/`green`.
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; tone: "valid" | "warning" | "blocked" | "neutral" }> = {
    ok: { label: "OK", tone: "valid" },
    valid: { label: "Valid", tone: "valid" },
    stale: { label: "Stale", tone: "warning" },
    unavailable: { label: "Unavailable", tone: "blocked" },
    unknown: { label: "Unknown", tone: "neutral" },
    not_evaluated: { label: "Not evaluated", tone: "neutral" },
    // ... every enum member mapped; default = neutral
  };
  const entry = map[status] ?? { label: status, tone: "neutral" };
  return (
    <span data-testid={`badge-${status}`} aria-label={`${entry.label} (${status})`}>
      {entry.label}
    </span>
  );
}
```

### Pattern 3: Chart with mandatory tabular alternative

**What:** Every chart renders with an adjacent `<table>` (or visually-hidden data table) containing the same points, plus `role="img"` + `aria-label` on the chart container [W3C WCAG 1.1.1 Situation B — charts need short + long text alternatives; G95/G73/G74/G92 [CITED: https://www.w3.org/WAI/WCAG22/quickref/]; Design.md §10 line 171 "tabular alternative for chart data"].
**When to use:** Instrument Workbench price chart, Backtest Results equity/drawdown curves.
**Example:**
```tsx
// Source: pattern derived from W3C WCAG 1.1.1 Situation B + Design.md §8/§10
<section aria-labelledby="workbench-chart-heading">
  <h2 id="workbench-chart-heading">Price — {instrument} ({timeframe})</h2>
  <ChartContainer role="img" aria-label="Price chart; data in the table below">
    <LineChart data={candles} />   // recharts
  </ChartContainer>
  <table>
    <caption>Price data table (accessible alternative to the chart)</caption>
    <thead><tr><th>Time</th><th>Open</th><th>High</th><th>Low</th><th>Close</th></tr></thead>
    <tbody>{candles.map(c => <tr key={c.bar_open_time}>{...}</tr>)}</tbody>
  </table>
</section>
```

### Pattern 4: Explicit state rendering (never `unknown` as healthy)

**What:** Each surface renders one of empty / loading / degraded / stale / no-setup / insufficient-evidence / conflicting-agents / schema-invalid / unavailable / offline; `unknown` maps to `neutral`, never a healthy tone; provider outage → no market data [VERIFIED: Design.md §8 lines 143-153; ROADMAP.md criterion 3; Schema.md QualityStatus `not_evaluated` is not healthy].

### Anti-Patterns to Avoid

- **Placeholder/mock data as live:** violates R-01 and ROADMAP criterion 2; fixtures confined to labelled tests only [VERIFIED: Rules.md R-01 lines 1-2, 8].
- **Colour-only status:** violates WCAG 1.4.1; always pair colour with text + icon [VERIFIED: Design.md §10 line 172; W3C WCAG 1.4.1].
- **`unknown` styled healthy:** `unknown`/`not_evaluated` → neutral only [VERIFIED: Design.md §8 line 153; Schema.md enums.py].
- **Synthesised candles/quotes on provider outage:** fail-closed, show unavailable [VERIFIED: data/news/base.py `fetch_coverage`; page.tsx].
- **Execute-trade control in client:** violates the research-only boundary [VERIFIED: Rules.md R-02; Prd.md §3 non-goals].
- **Hand-rolled API client drifting from schema:** use `gen:types` bindings + thin `api.ts` wrapper [VERIFIED: apps/web/package.json:14].
- **Calling MT5/Ollama from browser:** Architecture.md §2 Frontend forbids it [VERIFIED: Architecture.md lines 53-54].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Price/equity/drawdown charts | Custom SVG/canvas drawing | recharts (standard) or chart.js (alternative) + mandatory table | Accessibility, data density, interactions already solved [VERIFIED: Architecture.md §2 line 52 — check licence, data density, accessibility, interactions] |
| E2E browser tests | Hand-rolled automation (selenium-ish, sleeps) | Playwright `@playwright/test` | Auto-wait, web-first assertions, tracing, test isolation, parallelism [VERIFIED: context7 /microsoft/playwright key capabilities] |
| API response types | Hand-written TS interfaces | `gen:types` from `packages/contracts/schema/*.json` | Bindings stay aligned with the frozen contract; no drift [VERIFIED: apps/web/package.json:14] |
| Status/freshness vocabulary | Invented status strings | Closed contract enums (`Decision`, `AgentRunStatus`, `EvidenceStatus`, `QualityStatus`, `Direction`) | "No magic status strings outside enums" [VERIFIED: Schema.md §1 line 15; enums.py] |
| Data fetch / health client | Custom HTTP retry/cache layer | Thin `api.ts` wrapper + `cache: "no-store"` | Keeps the research-only read boundary; existing skeleton pattern [VERIFIED: apps/web/src/lib/api.ts] |

**Key insight:** Phase 7 is primarily a **presentation and verification** phase over contracts and state that already exist (Phases 4–6). The new code is thin: page shells, presentational components, status mappings, chart+table pairs, and Playwright journeys. Nothing in Phase 7 computes prices, levels, risk/reward, or backtest metrics — those come from deterministic backend code [VERIFIED: Rules.md R-01 line 4; src/goldmasters/risk/levels.py; src/goldmasters/backtest/metrics.py].

## Common Pitfalls

### Pitfall 1: Presenting cached or placeholder data as live
**What goes wrong:** A Server Component uses `force-cache` or a fixture, so the operator sees "fresh" data that is stale or invented.
**Why it happens:** Next.js `fetch` defaults to `force-cache` in some contexts; `gen:types` bindings make it tempting to populate with example values.
**How to avoid:** Use `cache: "no-store"` on every decision-relevant fetch; never import fixture data into a production page [VERIFIED: apps/web/src/lib/api.ts `cache: "no-store"`; Rules.md R-01 line 2; Context7 Next.js `cache` options [CITED: context7 /vercel/next.js]].
**Warning signs:** Health page shows data while `/health` is unreachable; decision timestamps don't advance.

### Pitfall 2: Colour-only status
**What goes wrong:** A badge is green/red with no text or icon, failing WCAG 1.4.1 and excluding colour-blind users.
**Why it happens:** Design tokens assign `positive`/`negative` colours without a label requirement.
**How to avoid:** Every status badge pairs colour with text and icon; `StatusBadge` component enforces it [VERIFIED: Design.md §7 line 121; §10 line 172; W3C WCAG 1.4.1].
**Warning signs:** A status renders as a coloured dot with no accessible name.

### Pitfall 3: `unknown` / `not_evaluated` styled as healthy
**What goes wrong:** Missing evidence is shown with a positive/valid tone, misleading the operator.
**Why it happens:** A default case in a status map maps anything unrecognised to "valid".
**How to avoid:** Exhaustively map every enum member; default to `neutral`; `unknown` is never healthy [VERIFIED: Design.md §8 line 153; Schema.md enums.py `not_evaluated` docstring "never a healthy value"].
**Warning signs:** A provider with no data shows a green badge.

### Pitfall 4: Synthesising market data on provider outage
**What goes wrong:** The UI shows a candle or quote when the provider is offline/disconnected.
**Why it happens:** A fallback renderer kicks in when `fetch` fails instead of showing unavailable.
**How to avoid:** Fail-closed — outage → "unavailable"/"offline" state, no market data [VERIFIED: data/news/base.py `fetch_coverage` fail-closed; page.tsx "No market data is shown"; ROADMAP criterion 3].
**Warning signs:** A price appears while the provider health is `disconnected`/`unavailable`.

### Pitfall 5: Execute-trade affordance leaking into the client
**What goes wrong:** A "Place order" button or trading credential field appears on Decision Detail.
**Why it happens:** Copying patterns from execution platforms.
**How to avoid:** Decision Detail primary action is "Open evidence" or "Add review note" only; boundary scan confirms no order module/endpoint/credential [VERIFIED: Prd.md §6.7 line 162; Design.md §6 line 109; ROADMAP criterion 4; Rules.md R-02].
**Warning signs:** Any client-side reference to order placement, modification, or closure.

### Pitfall 6: No Playwright coverage of error states
**What goes wrong:** E2E tests only cover the happy path, so offline/degraded/schema-invalid behaviour is unverified.
**Why it happens:** Error states are harder to drive than success states.
**How to avoid:** Use Playwright to force API failures (offline backend, 500, malformed JSON) and assert each explicit state renders [VERIFIED: ROADMAP criterion 5; Rules.md R-08 line 4; context7 Playwright test isolation/auto-wait [CITED: context7 /microsoft/playwright]].
**Warning signs:** E2E suite passes but never exercises a failure branch.

## Code Examples

Verified patterns from official/in-repo sources:

### Health page — read-only, no market data on outage
```tsx
// Source: apps/web/src/app/page.tsx:1-36 (read this session)
import { fetchHealth } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function HealthPage() {
  const result = await fetchHealth();

  if (!result.available) {
    return (
      <main>
        <h1>GoldMasters Research Console</h1>
        <p role="status">API unavailable: {result.reason}</p>
        <p>No market data is shown because the backend cannot be reached.</p>
      </main>
    );
  }

  const { health } = result;
  return (
    <main>
      <h1>GoldMasters Research Console</h1>
      <dl>
        <dt>Backend status</dt>
        <dd>{health.status}</dd>
        <dt>Backend version</dt>
        <dd>{health.version}</dd>
        <dt>Contract schema version</dt>
        <dd>{health.contract_schema_version}</dd>
        <dt>Effective-config hash</dt>
        <dd>{health.config_hash}</dd>
        <dt>Database reachable</dt>
        <dd>{health.database.reachable ? "yes" : "no"}</dd>
      </dl>
    </main>
  );
}
```

### Contract-generated TypeScript bindings (no hand-written types)
```bash
# Source: apps/web/package.json:14 — gen:types script
json2ts -i ../../packages/contracts/schema/decision.json -o src/generated/decision.ts --no-format
# ... repeated for envelope, market, quote, precision, journal, news, sentiment, backtest, error
```
Generated `DecisionRecord` fields [VERIFIED: packages/contracts/src/goldmasters_contracts/decision.py:41-67]:
`decision_id`, `run_id`, `instrument_id`, `timeframe`, `decision` (enum), `direction` (nullable), `created_at`, `data_as_of`, `strategy_id`/`strategy_version`, `entry`/`stop_loss`/`take_profits`/`risk_reward` (nullable), `thesis`, `invalidation_conditions`, `risk_factors`, `reasons_for_rejection`, `evidence_refs`, `agent_statuses`, `conflicts`, `data_quality_status`, `limitations`, `manual_review_required` (always `true` in V1).

### recharts chart with tabular alternative (recommendation — `recharts` name `[ASSUMED]`)
```tsx
// Source: pattern for W3C WCAG 1.1.1 Situation B + Design.md §8/§10; recharts API is [ASSUMED]
<section aria-labelledby="equity-heading">
  <h2 id="equity-heading">Equity curve — {strategyId}</h2>
  <div role="img" aria-label="Equity curve; values are in the table below">
    <LineChart data={equityPoints}>
      <Line type="monotone" dataKey="equity" stroke="#67B7FF" />
    </LineChart>
  </div>
  <table>
    <caption>Equity data table (accessible alternative to the chart)</caption>
    <thead><tr><th>Time</th><th>Equity</th><th>Drawdown</th></tr></thead>
    <tbody>{equityPoints.map(p => <tr key={p.t}><td>{p.t}</td><td>{p.equity}</td><td>{p.drawdown}</td></tr>)}</tbody>
  </table>
</section>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No UI (docs-only phase) | Next.js 16.4.0 / React 19.3.0 App Router skeleton with generated contract bindings | Phase 1 (complete 2026-10-15) | `apps/web/` exists: `layout.tsx`, `page.tsx` (`/health`), `lib/api.ts`, `src/generated/` TS from schema [VERIFIED: apps/web/] |
| Undecided chart library | recharts recommended (SVG, MIT, WCAG-friendly) + table alternative | Phase 7 (this research) | Accessibility-aligned charting; chart.js/lightweight-charts as alternatives [recharts name `[ASSUMED]`] |
| No E2E tool | Playwright `@playwright/test` 1.64.1 | Phase 7 (this research) | Criterion 5 coverage of core journeys + error states [playwright `[CITED: context7 /microsoft/playwright]`] |

**Deprecated/outdated:** None in-scope; no UI existed before Phase 7.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `recharts` 3.10.1 is the standard chart library (name `[ASSUMED]` — not from authoritative doc; gate `OK`) | Standard Stack | Operator may prefer canvas/candlestick library; recharts accessibility still needs explicit `aria-label` + table |
| A2 | `chart.js`/`react-chartjs-2`/`lightweight-charts` are acceptable alternatives (names `[ASSUMED]`) | Standard Stack | Chosen alternative may fail WCAG without extra work |
| A3 | Playwright 1.64.1 is the E2E framework (name `[CITED: context7 /microsoft/playwright]`; not yet installed) | Standard Stack | Install step missing → criterion 5 cannot be verified |
| A4 | UI framework/stack beyond skeleton is operator-owned and unresolved | User Constraints | Planner may build on an unconfirmed stack; user must confirm |
| A5 | Backend API (`127.0.0.1:8000`) is reachable for UI development | Environment Availability | UI cannot render live state without the API running |

## Open Questions

1. **UI framework/stack choice beyond the skeleton**
   - What we know: skeleton is Next.js 16.4.0 / React 19.3.0 / TypeScript; `apps/web/` exists with health page + generated bindings [VERIFIED: apps/web/].
   - What's unclear: whether the operator confirms this stack or wants a different component library/approach (marked operator-owned in Memory.md).
   - Recommendation: treat as `checkpoint:human-verify`; proceed with the skeleton stack unless the operator objects.

2. **Chart library final choice**
   - What we know: `recharts` 3.10.1 MIT `OK`; chart.js + react-chartjs-2 and lightweight-charts also `OK` [VERIFIED: npm view + legitimacy gate].
   - What's unclear: candlestick support (recharts lacks native candlesticks) vs accessibility (canvas libraries need more ARIA work).
   - Recommendation: default to `recharts` + table alternative; `lightweight-charts` only if native candlesticks are required and the operator accepts the accessibility tradeoff.

3. **Backend availability for UI development**
   - What we know: API expected at `127.0.0.1:8000` (`GOLDMASTERS_API_BASE_URL` default) [VERIFIED: apps/web/src/lib/api.ts:3].
   - What's unclear: whether the FastAPI backend is runnable on this machine in this session.
   - Recommendation: probe the API health endpoint; if unavailable, develop UI against the contract bindings and mark E2E as blocked until API runs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Next.js dev/build, typecheck | ✓ | v24.21.0 [probe this session] | — |
| npm | Package install | ✓ | 12.2.0 [probe this session] | — |
| Next.js | App Router pages | ✓ | 16.4.0 [installed in `apps/web/node_modules`] | — |
| React | UI components | ✓ | 19.3.0 [installed in `apps/web/node_modules`] | — |
| TypeScript | `tsc --noEmit` | ✓ | 7.0.2 [package.json] | — |
| Playwright (`@playwright/test`) | E2E criterion 5 | ✗ | 1.64.1 latest [npm view]; absent from `apps/web/node_modules` [probe] | `npm install -D playwright @playwright/test` + `npx playwright install` |
| FastAPI backend (`127.0.0.1:8000`) | Live state for all surfaces | [unprobed] | — | Develop against contract bindings; E2E blocked until API reachable |
| recharts | Charts | [not installed] | 3.10.1 [npm view] | `npm install recharts` |

**Missing dependencies with no fallback:** none identified (all installable via npm).
**Missing dependencies with fallback:** Playwright (installable; blocks criterion 5 verification until installed); backend API (develop against bindings, E2E blocked until reachable).

## Validation Architecture

> `workflow.nyquist_validation` is absent from `.planning/config.json`, so it is treated as enabled — this section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright `@playwright/test` (E2E), version 1.64.1 latest [VERIFIED: npm view]; not yet installed |
| Config file | `apps/web/playwright.config.ts` — does not exist yet (Wave 0 gap) |
| Quick run command | `npx playwright test` (after install) |
| Full suite command | `npx playwright test` |
| Backend contract tests | pytest (existing `tests/unit`, `tests/integration`, `tests/contract` layout) — layout confirmed via glob, runner config not re-read this session [ASSUMED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-ui-and-reports (11 surfaces live) | Each surface reachable, renders API state | E2E (Playwright) | `npx playwright test --grep "surfaces"` | ❌ Wave 0 |
| REQ-ui-and-reports (freshness/quality next to decisions) | Badge shows enum + label per decision | E2E | `npx playwright test --grep "freshness"` | ❌ Wave 0 |
| ROADMAP criterion 3 (explicit states incl. offline) | offline/degraded/stale/unavailable render; `unknown` neutral | E2E (force API failure) | `npx playwright test --grep "offline\|degraded\|unavailable"` | ❌ Wave 0 |
| ROADMAP criterion 4 (no execute-trade) | Decision Detail has no order control | E2E + audit | assert no order/button/credential in client | ❌ Wave 0 |
| ROADMAP criterion 5 (WCAG + keyboard + Playwright) | Keyboard nav, visible focus, non-colour-only, table alternatives | E2E + axe/manual | `npx playwright test --grep "a11y\|keyboard"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Playwright quick run of affected journey (`npx playwright test <file> -x`)
- **Per wave merge:** Full Playwright suite + `tsc --noEmit` + `npm run build`
- **Phase gate:** Full suite green before `/gsd-verify-work`; ruff/mypy strict clean for any shared contract changes

### Wave 0 Gaps
- [ ] `apps/web/playwright.config.ts` — Playwright config
- [ ] `apps/web/tests/e2e/*.spec.ts` — core journeys (all 11 surfaces) + error states (offline, degraded, schema-invalid, provider outage)
- [ ] `npm install -D playwright @playwright/test` + `npx playwright install --with-deps chromium`
- [ ] Component-level status-badge / table-alternative tests (unit, framework TBD — operator-owned stack decision A4)

*(If no gaps: "None — existing test infrastructure covers all phase requirements") — not applicable here; gaps listed above.*

## Security Domain

> `security_enforcement` is absent from `.planning/config.json`, so it is treated as enabled — this section is included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single local operator, loopback; no auth in V1 [VERIFIED: Prd.md §3 non-goals; Requirements.md out of scope] |
| V3 Session Management | no | No sessions in V1 |
| V4 Access Control | partial | Read-only client; no write/mutation endpoints reachable from browser; no order capability [VERIFIED: Rules.md R-02; Architecture.md §2 Frontend lines 53-54] |
| V5 Input Validation | yes | API payloads validated via `goldmasters_contracts`; UI sends no trusted data; fetch restricted to loopback API base [VERIFIED: apps/web/src/lib/api.ts `API_BASE_URL` default 127.0.0.1:8000; Schema.md §10 error contract] |
| V6 Cryptography | no | No secrets in UI; hashes (`dataset_hash`, `parameter_hash`) are integrity labels, not security controls [VERIFIED: Phase 6 research; backtest.py] |

### Known Threat Patterns for Next.js read-only console

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Placeholder/mock data presented as live | Integrity | R-01; fixtures confined to labelled tests; never in production paths [VERIFIED: Rules.md R-01] |
| Colour-only status (a11y/exclusion) | Repudiation / integrity of state | Text + icon + colour; `StatusBadge` [VERIFIED: Design.md §10; W3C WCAG 1.4.1] |
| XSS via news titles/sentiment content | Tampering | News items stored verbatim, never executed/cleaned; sanitize on render; source terms respected [VERIFIED: data/news/base.py security notes lines 7-12] |
| SSRF via fetch | Tampering | `API_BASE_URL` locked to loopback default; no user-supplied fetch targets [VERIFIED: apps/web/src/lib/api.ts:3] |
| `unknown` styled healthy | Integrity | Exhaustive enum mapping; default neutral [VERIFIED: Design.md §8 line 153] |
| Provider outage showing market data | Integrity | Fail-closed; no data on outage [VERIFIED: data/news/base.py; page.tsx] |

## Sources

### Primary (HIGH confidence — read from source this session)
- `.planning/ROADMAP.md` Phase 7 goal + criteria 1-5 (lines 156-168) — read this session
- `.planning/REQUIREMENTS.md` REQ-ui-and-reports acceptance (lines 34-35) — read this session
- `Prd.md` §6.7 UI and reports (lines 157-163) — read this session
- `Design.md` §4 screens, §7 components, §8 states, §9 responsive, §10 accessibility (lines 50-173) — read this session
- `Architecture.md` §2 Frontend (lines 50-54) — read this session
- `Task.md` Phase 7 T0701-T0710 (lines 88-98) — read this session
- `Schema.md` §1 conventions, §2 enums (enums.py lines 37-128 mirror Schema §2) — read this session
- `Rules.md` R-01, R-02 — read this session
- `Memory.md` open decision (UI framework/stack operator-owned) — read this session
- `apps/web/package.json`, `src/app/layout.tsx`, `src/app/page.tsx`, `src/lib/api.ts`, `src/generated/*.ts` — read this session
- `packages/contracts/schema/*.json` and `src/goldmasters_contracts/{decision,backtest,enums}.py` — read this session
- `src/goldmasters/journal/store.py`, `src/goldmasters/backtest/{metrics,runner}.py`, `src/goldmasters/graph/{traceability,nodes,builder,role_nodes,barriers,state}.py`, `src/goldmasters/risk/{gate,levels}.py`, `src/goldmasters/data/news/base.py` — read this session

### Secondary (MEDIUM confidence — official documentation via Context7)
- Context7 `/vercel/next.js` — Next.js App Router fetch `cache` options, Server Components, `no-store`/`force-cache` [CITED: context7 /vercel/next.js] — MEDIUM (classify-confidence: MEDIUM)
- Context7 `/react/react` — `'use client'` / `'use server'` server-client boundary [CITED: context7 /react/react] — MEDIUM
- Context7 `/microsoft/playwright` — `test`/`expect`, page fixture, `getByRole`, auto-wait, test isolation, tracing [CITED: context7 /microsoft/playwright] — MEDIUM

### Tertiary (LOW confidence — authority, not source-verified this session)
- W3C WCAG 2.2 Quick Reference — criteria 1.4.1 Use of Color, 1.4.3 Contrast Minimum (4.5:1/3:1), 1.4.11 Non-text Contrast, 2.1.1 Keyboard, 2.4.7 Focus Visible, 2.4.13 Focus Appearance, 1.1.1 Situation B chart alternatives (G95/G73/G74/G92) [CITED: https://www.w3.org/WAI/WCAG22/quickref/] — MEDIUM source, not re-classified this session
- `npm registry` versions: next 16.4.0, react 19.3.0, playwright 1.64.1, recharts 3.10.1, chart.js 4.5.1, react-chartjs-2 5.3.1, lightweight-charts 5.2.1 — [VERIFIED: npm view]
- Package names `recharts`, `chart.js`, `react-chartjs-2`, `lightweight-charts` discovered via training — `[ASSUMED]` (registry existence alone does not confer verified status)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH for Next.js/React/TypeScript (package.json read + npm view confirmed); MEDIUM for recharts/Playwright recommendations (package names `[ASSUMED]`/`[CITED]`, gate `OK`, versions confirmed).
- Architecture: HIGH — all reuse targets and contract vocabularies read from source; responsibility map derived from read files.
- Pitfalls: HIGH — grounded in existing validators, skeleton code, and W3C criteria.

**Research date:** 2026-10-16
**Valid until:** 30 days (stable domain; in-repo contracts change only by reviewed migration; Next.js/Playwright versions re-verify before install)
