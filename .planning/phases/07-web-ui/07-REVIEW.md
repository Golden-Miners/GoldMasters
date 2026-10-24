---
phase: 07-web-ui
reviewed: 2026-10-22T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - apps/web/src/app/page.tsx
  - apps/web/src/app/layout.tsx
  - apps/web/src/app/overview/page.tsx
  - apps/web/src/app/workbench/page.tsx
  - apps/web/src/app/strategy-lab/page.tsx
  - apps/web/src/app/decision/page.tsx
  - apps/web/src/app/news-sentiment/page.tsx
  - apps/web/src/app/Navbar.tsx
  - apps/web/src/styles/design-tokens.css
  - apps/web/src/styles/globals.css
  - apps/web/tests/e2e/overview.spec.ts
  - apps/web/tests/e2e/workbench.spec.ts
  - apps/web/tests/e2e/screenshot.spec.ts
findings:
  critical: 1
  warning: 14
  info: 4
  total: 19
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-10-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 7 (Web UI) implements the Overview, Workbench, Strategy Lab, Decision, News & Sentiment pages plus a shared Navbar, design tokens, and global styles, with three E2E test files. The code follows the project's dark "quant terminal" design system and uses explicit empty/loading/offline states throughout. However, there is one **Critical** blocker: the `src/generated/` directory referenced by every page's type imports does not exist, so TypeScript compilation will fail. There are 14 Warnings covering type-safety gaps, unhandled nulls, missing timeouts, and React anti-patterns, plus 4 Info items for cleanup.

Supporting files read during review (not in changed list but imported by changed files):
- `apps/web/src/lib/api.ts` — data fetch layer used by all pages
- `apps/web/src/components/StatusBadge.tsx` — shared status badge component
- `apps/web/src/components/ExplicitState.tsx` — shared empty/loading/offline state component

## Critical Issues

### CR-01: Missing generated types directory breaks TypeScript compilation

**File:** `apps/web/src/lib/api.ts:1-5`, `apps/web/src/app/overview/page.tsx:10-11`, `apps/web/src/app/decision/page.tsx:5`, `apps/web/src/app/workbench/page.tsx` (indirect via api.ts)

**Issue:** Every page and the API lib import types from `../../generated/decision`, `../../generated/market`, `../generated/error`, `../generated/decision`, `../generated/backtest`, `../generated/journal`, `../generated/market`. The `apps/web/src/generated/` directory does not exist (confirmed via glob — zero files match `generated/**/*`). With `tsconfig.json` set to `"strict": true` and `"noEmit": true`, TypeScript will fail to compile with "Cannot find module" errors for every one of these imports. The entire frontend build is broken until these types exist.

**Fix:** Create the missing type definition files under `apps/web/src/generated/` matching the imported shapes, or generate them from the backend API contracts. Minimum required files:

```
src/generated/decision.ts   -> DecisionRecord (per Schema.md §6)
src/generated/market.ts     -> MarketBar (per Schema.md §4)
src/generated/error.ts      -> ErrorPayload (per Schema.md §10)
src/generated/backtest.ts   -> BacktestRecord (per Schema.md §9)
src/generated/journal.ts    -> JournalEntry (per Schema.md persistence contract)
```

Example for `decision.ts`:
```typescript
export interface DecisionRecord {
  decision_id: string;
  run_id: string;
  instrument_id: string;
  timeframe: string;
  decision: "TRADE" | "NO_TRADE" | "INSUFFICIENT_DATA";
  direction: "long" | "short" | "neutral" | null;
  created_at: string;
  data_as_of: string;
  strategy_id: string | null;
  strategy_version: string | null;
  entry: number | null;
  stop_loss: number | null;
  take_profits: number[] | null;
  risk_reward: number | null;
  thesis: string;
  invalidation_conditions: string[];
  risk_factors: string[];
  reasons_for_rejection: string[];
  evidence_refs: string[];
  agent_statuses: Record<string, string>;
  conflicts: string[];
  data_quality_status: string;
  limitations: string[];
  manual_review_required: boolean;
}
```

## Warnings

### WR-01: `any` type used for news items (type safety bypass)

**File:** `apps/web/src/app/news-sentiment/page.tsx:51`

**Issue:** The `.map()` callback types the item parameter as `any`: `(item: any, index: number)`. This bypasses all TypeScript checking on news item properties (`source_id`, `published_at`, `content`, `summary`, `retrieved_at`, `limitations`), defeating the purpose of strict mode and allowing runtime property-access errors to go undetected.

**Fix:** Define a `NewsItem` interface and use it:

```typescript
interface NewsItem {
  source_id: string | null;
  canonical_url: string;
  title: string;
  published_at: string | null;
  retrieved_at: string | null;
  content: string | null;
  summary: string | null;
  limitations: string[];
}
// ...
{data.items.map((item: NewsItem) => (
```

### WR-02: Array index used as React key

**File:** `apps/web/src/app/news-sentiment/page.tsx:52`

**Issue:** `key={index}` is used when rendering news items. Using the array index as a React key causes bugs when items are inserted, removed, or reordered (stale state, wrong animations, mismatched component identity). News items from the API have stable identifiers (`source_id`, `canonical_url`) that should be used instead.

**Fix:** Use a stable identifier from the item:

```typescript
{data.items.map((item: NewsItem) => (
  <div className="news-item" key={item.canonical_url ?? item.source_id}>
```

### WR-03: CandlePoint `c` field typed as string but assigned a number

**File:** `apps/web/src/app/workbench/page.tsx:22,48-51`

**Issue:** The `CandlePoint` interface declares `c: string` (line 22), but line 51 assigns `c: bar.close` which is a `number` per the `MarketBar` type. Under TypeScript strict mode this is a type error. The value is later rendered directly in the table at line 189 (`{c.c}`), which works at runtime but the type contract is wrong.

**Fix:** Change the interface field type to `number`:

```typescript
interface CandlePoint {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
}
```

### WR-04: `Number()` conversion without NaN validation

**File:** `apps/web/src/app/workbench/page.tsx:48-50`

**Issue:** `Number(bar.open)`, `Number(bar.high)`, `Number(bar.low)` are called without checking for `NaN`. If the API returns a non-numeric string or `null`, `Number()` returns `NaN`, which is then rendered in the chart and table as "NaN". No validation guards against malformed numeric data from the provider.

**Fix:** Validate before converting:

```typescript
const parsePrice = (v: unknown): number | null => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
// ...
o: parsePrice(bar.open) ?? 0,
h: parsePrice(bar.high) ?? 0,
l: parsePrice(bar.low) ?? 0,
c: bar.close,
```

### WR-05: `health.config_hash.slice(0, 12)` without null/undefined check

**File:** `apps/web/src/app/overview/page.tsx:202`

**Issue:** `health.config_hash.slice(0, 12)` is called directly on `config_hash`. If `config_hash` is `undefined`, `null`, or not a string, this throws a runtime TypeError and crashes the page. The `HealthBody` type declares it as `string` but the API response is not validated at runtime, so the field could be absent or malformed.

**Fix:** Guard before slicing:

```typescript
<span className="status-dd num">
  {typeof health.config_hash === "string"
    ? health.config_hash.slice(0, 12) + "…"
    : "—"}
</span>
```

### WR-06: `bars[0].quality_status` may be undefined when passed to StatusBadge

**File:** `apps/web/src/app/overview/page.tsx:92`

**Issue:** `StatusBadge status={bars[0].quality_status}` — `quality_status` on `MarketBar` is a required field per Schema.md §4, but the runtime API response is not validated, so it could be `undefined`. `StatusBadge` expects a `string` and uses `map[status]` with a fallback to `{ label: status, tone: "neutral" }`. If `status` is `undefined`, `map[undefined]` returns `undefined`, the fallback gives `{ label: undefined, tone: "neutral" }`, and `aria-label` becomes `"undefined (undefined)"`.

**Fix:** Provide a fallback value:

```typescript
<StatusBadge status={bars[0].quality_status ?? "not_evaluated"} />
```

### WR-07: `decision.strategy_version` can be null, producing "@null" in UI

**File:** `apps/web/src/app/decision/page.tsx:68-69`

**Issue:** `{decision.strategy_id}@{decision.strategy_version}` interpolates `strategy_version` which is nullable per Schema.md §6. When null, the UI renders "agent_01@null" — misleading and unprofessional. Same pattern exists in `overview/page.tsx:163`.

**Fix:** Conditionally render the version:

```typescript
{decision.strategy_version
  ? `${decision.strategy_id}@${decision.strategy_version}`
  : decision.strategy_id}
```

### WR-08: `item.published_at` is nullable but passed to `new Date()` without null check

**File:** `apps/web/src/app/news-sentiment/page.tsx:56`

**Issue:** Per Schema.md §7, `published_at` is nullable. `new Date(item.published_at)` with `null` returns an Invalid Date object, and `.toLocaleString()` on it returns the string "Invalid Date", which is rendered to the user.

**Fix:** Guard the date formatting:

```typescript
<time dateTime={item.published_at ?? ""} className="news-time">
  {item.published_at ? new Date(item.published_at).toLocaleString() : "—"}
</time>
```

### WR-09: `event.target` cast to `Node` without null check

**File:** `apps/web/src/app/Navbar.tsx:74`

**Issue:** `document.getElementById("nav-container")?.contains(event.target as Node)` — `event.target` can be `null` per the TypeScript DOM type for `MouseEvent`. The `as Node` assertion suppresses the type error but does not protect against a null target at runtime, which would throw when passed to `.contains()`.

**Fix:** Add a null guard:

```typescript
const handleClick = (event: MouseEvent) => {
  const container = document.getElementById("nav-container");
  if (!container || !event.target) {
    setOpenGroups(new Set());
    setMobileOpen(false);
    return;
  }
  if (!container.contains(event.target as Node)) {
    setOpenGroups(new Set());
    setMobileOpen(false);
  }
};
```

### WR-10: Missing `type="button"` on button elements in Navbar

**File:** `apps/web/src/app/Navbar.tsx:94-102, 135-141`

**Issue:** `<button>` elements default to `type="submit"`. If the Navbar is ever placed inside a `<form>`, clicking these buttons would trigger form submission instead of their intended click handler. The desktop dropdown triggers and mobile group toggles are all plain `<button>` without explicit `type="button"`.

**Fix:** Add `type="button"` to all non-submit buttons:

```typescript
<button type="button" className={`nav-dropdown-trigger ...`} ...>
```

### WR-11: `suppressHydrationWarning` on `<body>` hides real hydration mismatches

**File:** `apps/web/src/app/layout.tsx:14`

**Issue:** `<body ... suppressHydrationWarning>` suppresses React hydration warnings on the body element. This can mask genuine SSR/client rendering mismatches (e.g., date formatting differences, locale-dependent output from `toLocaleString()` used throughout the pages). Suppressing rather than fixing the root cause hides real bugs.

**Fix:** Remove `suppressHydrationWarning` and ensure server-rendered output matches client-rendered output. If date/time formatting differs between server and client, render dates client-side or use a consistent formatting function.

### WR-12: `fetchProviders` returns `response.json()` with implicit `any` type

**File:** `apps/web/src/lib/api.ts:150`

**Issue:** `const data = await response.json();` has no type assertion. `response.json()` returns `Promise<any>`, so `data` is implicitly `any`. The function's return type declares `data: object`, but the actual value is unchecked `any`, bypassing type safety.

**Fix:** Add an explicit type assertion or define a ProviderData interface:

```typescript
const data = (await response.json()) as object;
```

### WR-13: Most fetch calls lack request timeouts

**File:** `apps/web/src/lib/api.ts:23-42 (fetchHealth has timeout; all others do not)`

**Issue:** Only `fetchHealth` uses an `AbortController` with a timeout (line 24-25). All other fetch functions (`fetchDecisions`, `fetchNewsSentiment`, `fetchStrategies`, `fetchProviders`, etc.) have no timeout. If the backend hangs or is slow, the browser tab can wait indefinitely, leaving the user with a permanently loading page and no way to recover except refreshing.

**Fix:** Add a reusable timeout wrapper or AbortController to each fetch:

```typescript
const fetchWithTimeout = async (url: string, timeoutMs = 5000) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timer);
  }
};
```

### WR-14: Empty catch block silently swallows fetch errors

**File:** `apps/web/src/app/workbench/page.tsx:55-57`

**Issue:** `catch { setState("unavailable"); }` catches all errors from `fetchMarketBars` and sets state to "unavailable" without logging, reporting, or surfacing the error reason. Per Rules.md §6.7 ("Never catch and ignore errors"), this hides failures from operators. The user sees "MT5 terminal not connected" regardless of the actual cause (network error, 500, malformed JSON, timeout).

**Fix:** Log the error and surface a more specific reason:

```typescript
} catch (error) {
  console.error("Workbench fetch failed:", error);
  setState("unavailable");
}
```

## Info

### IN-01: Duplicate `.empty-state` class definition

**File:** `apps/web/src/styles/globals.css:725-735` and `740-750`

**Issue:** The `.empty-state` CSS class is defined twice with identical properties (lines 725-735 and 740-750). The second definition overrides the first, but this is dead/duplicated code that indicates a copy-paste error and creates confusion about which definition is authoritative.

**Fix:** Remove one of the two identical `.empty-state` blocks.

### IN-02: `"use client"` on Strategy Lab page that only fetches data

**File:** `apps/web/src/app/strategy-lab/page.tsx:1`

**Issue:** `strategy-lab/page.tsx` is marked `"use client"` but performs only data fetching and rendering — no browser APIs, event handlers, or client-only features. This creates an unnecessary client component boundary, forcing client-side hydration for a page that could be a Server Component, increasing JavaScript bundle size and time-to-interactive.

**Fix:** Remove `"use client"` and make this an async Server Component (like `overview/page.tsx` and `decision/page.tsx`).

### IN-03: Redundant `as ProviderData` type casts

**File:** `apps/web/src/app/overview/page.tsx:54, 214`

**Issue:** `providersResult.data as ProviderData` is cast on line 54, then cast again on line 214 (`(providersData as ProviderData).status`). Since `providersData` is already typed as `ProviderData` after the first cast, the second cast is redundant noise.

**Fix:** Remove the second cast:

```typescript
<StatusBadge status={providersData.status ?? "unavailable"} />
```

### IN-04: Inline object type instead of named interface

**File:** `apps/web/src/app/strategy-lab/page.tsx:31`

**Issue:** The `.map()` callback uses an inline anonymous type `{ agent_id: string; enabled: boolean; instruments: string[]; timeframes: string[]; regimes: string[]; min_bars: number }`. This type is also defined in `api.ts`'s `fetchStrategies` return type. Duplicating the type inline creates drift risk if the API type changes.

**Fix:** Import and reuse the type from `api.ts`, or define a shared `StrategyAgent` interface.

---

_Reviewed: 2026-10-22T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_