---
phase: 01-code-review
reviewed: 2026-10-22T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - apps/web/src/app/page.tsx
  - apps/web/src/app/layout.tsx
  - apps/web/src/app/overview/page.tsx
  - apps/web/src/app/strategy-lab/page.tsx
  - apps/web/src/app/decision/page.tsx
  - apps/web/src/app/Navbar.tsx
  - apps/web/src/styles/design-tokens.css
  - apps/web/src/styles/globals.css
  - apps/web/tests/e2e/overview.spec.ts
  - apps/web/tests/e2e/workbench.spec.ts
  - apps/web/tests/e2e/screenshot.spec.ts
findings:
  critical: 0
  warning: 10
  info: 5
  total: 15
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 1 delivers the root route (Overview), a split Server/Client layout, refined Overview/Strategy Lab/Decision pages, a new client Navbar, design tokens/global CSS, and 17 E2E tests (16 pass, 1 env-dependent failure for MT5 terminal not running). `tsc --noEmit` passes and the production build succeeds.

No CRITICAL findings (no security vulnerabilities, data loss risks, or crashes). No hardcoded secrets, no `eval`/`innerHTML`/`dangerouslySetInnerHTML`, no `console.log`/`debugger`/TODO artifacts, no `any` type assertions in the changed files. Error handling is consistently fail-closed across all API calls (`fetch*` functions return `{ available: false, ... }` rather than throwing).

The 15 findings below are all WARNING or INFO severity: type-safety gaps at API boundaries, missing ARIA attributes on interactive elements, dead buttons, invalid CSS, and test-quality gaps.

## Warnings

### WR-01: Unchecked type assertion on provider data

**File:** `apps/web/src/app/overview/page.tsx:54`
**Issue:** `providersResult.data` is typed as `object` by `fetchProviders()` (api.ts:142), but the page casts it to `ProviderData` with `as`. This is an unchecked assertion at an API boundary — if the provider response shape changes, property access (`.provider_id`, `.status`, `.mt5_server_timezone`, `.checked_at`) will silently return `undefined` rather than fail loudly.
**Fix:** Define a provider type in the generated layer or API layer and have `fetchProviders()` return it, or validate the shape before casting:

```typescript
// In api.ts — type the provider data
export async function fetchProviders(): Promise<
  | { available: true; data: ProviderData }
  | { available: false; reason: string }
> {
  ...
  const data = (await response.json()) as ProviderData;
  return { available: true, data };
}

// In overview/page.tsx — remove the cast
const providersData =
  providersResult.available ? providersResult.data : null;
```

### WR-02: Redundant double type assertion

**File:** `apps/web/src/app/overview/page.tsx:214`
**Issue:** `providersData` is already cast to `ProviderData` on line 54, but line 214 casts it again: `(providersData as ProviderData).status`. The inner cast is unnecessary and misleading.
**Fix:** Remove the redundant cast:

```typescript
<StatusBadge status={providersData.status ?? "unavailable"} />
```

### WR-03: `new Date().toLocaleString()` without Invalid Date fallback

**File:** `apps/web/src/app/overview/page.tsx:102,236`
**Issue:** `new Date(bars[0].retrieved_at).toLocaleString()` and `new Date(providersData.checked_at).toLocaleString()` are called on date strings from the API with no validation. If the backend returns a malformed ISO string, `new Date()` yields an Invalid Date object, and `.toLocaleString()` returns the implementation-specific string "Invalid Date", which is displayed to the user.
**Fix:** Add a helper that validates the date before formatting:

```typescript
function formatDateSafe(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : d.toLocaleString();
}
// Usage: {formatDateSafe(bars[0]?.retrieved_at)}
```

### WR-04: Unencoded `decision_id` in navigation URL

**File:** `apps/web/src/app/overview/page.tsx:153` and `apps/web/src/app/decision/page.tsx:61`
**Issue:** `href={`/decision?id=${decision.decision_id}`}` interpolates `decision_id` directly into a URL without `encodeURIComponent`. If an ID ever contains special characters (`&`, `=`, `#`, spaces), the URL will be malformed. While IDs are currently server-generated UUIDs, this is a trust-boundary issue: all external/model/provider input is untrusted until validated (Schema.md §1.17).
**Fix:** Encode the parameter:

```typescript
href={`/decision?id=${encodeURIComponent(decision.decision_id)}`}
```

### WR-05: Dead buttons in Strategy Lab

**File:** `apps/web/src/app/strategy-lab/page.tsx:53-57`
**Issue:** Two `<button>` elements have no `onClick` handler:
- The "Enabled"/"Disabled" toggle button (line 53) — clicking does nothing.
- The "View Rules" button (line 56) — clicking does nothing.

Dead buttons are a UX defect: users perceive them as functional, but they produce no result.
**Fix:** Either add `onClick` handlers or remove the buttons until the functionality exists:

```typescript
<button
  className={`btn-toggle ${agent.enabled ? "enabled" : ""}`}
  onClick={() => toggleAgent(agent.agent_id)}
>
  {agent.enabled ? "Enabled" : "Disabled"}
</button>
```

### WR-06: `<summary>` missing `aria-expanded`

**File:** `apps/web/src/app/strategy-lab/page.tsx:34`
**Issue:** The `<details>/<summary>` accordion pattern is correctly used for the strategy cards, but `<summary>` lacks `aria-expanded`. Screen reader users cannot tell whether the details panel is open or closed (WCAG 4.1.2 / ARIA best practices).
**Fix:** Add `aria-expanded` synchronized with the `<details>` `open` attribute. Since `<details>` manages its own open state, use a ref or `onToggle`:

```typescript
<details
  className="strategy-card-detail"
  onToggle={(e) => {
    const summary = e.currentTarget.querySelector("summary");
    if (summary) summary.setAttribute("aria-expanded", String(e.currentTarget.open));
  }}
>
  <summary className="strategy-summary" aria-expanded="false">
```

### WR-07: Mobile navigation toggle missing ARIA attributes

**File:** `apps/web/src/app/Navbar.tsx:136`
**Issue:** The mobile group toggle button (line 136) has no `aria-expanded` or `aria-haspopup` attribute, while the desktop equivalent (lines 97-98) has both. Screen reader users on mobile cannot tell whether a group is expanded or that it controls a popup menu.
**Fix:** Add matching ARIA attributes to the mobile toggle:

```typescript
<button
  className={`nav-mobile-group-toggle ${isGroupOpen(group.label) ? "open" : ""}`}
  onClick={() => toggleGroup(group.label)}
  aria-expanded={isGroupOpen(group.label)}
  aria-haspopup="true"
>
```

### WR-08: Unnecessary unsafe type cast in click-outside handler

**File:** `apps/web/src/app/Navbar.tsx:74`
**Issue:** `event.target as Node` casts `EventTarget | null` to `Node` without a null check. `event.target` can be `null` in some edge cases. While `container?.contains(null)` safely returns `false`, the cast is unnecessary and suppresses potential type errors.
**Fix:** Use a proper null check:

```typescript
const target = event.target as Node | null;
if (!container?.contains(target)) {
```

### WR-09: `suppressHydrationWarning` may mask hydration mismatches

**File:** `apps/web/src/app/layout.tsx:14`
**Issue:** `<body suppressHydrationWarning>` suppresses React hydration warnings. The `Navbar` is a Client Component prerendered on the server and hydrated on the client. If server and client initial output ever diverge (e.g., due to `usePathname()` differences, locale, or client-only state), the warning that would catch it is suppressed, potentially allowing UI inconsistencies to ship unnoticed.
**Fix:** Remove `suppressHydrationWarning` and ensure the server-rendered and client-hydrated output match. If a specific element is known to differ, apply the attribute to that element only, not the entire `<body>`.

### WR-10: Missing timeouts on API calls (except health)

**File:** `apps/web/src/lib/api.ts` (multiple functions)
**Issue:** Only `fetchHealth()` (line 23) sets a 5000ms timeout via `AbortController`. All other fetch functions (`fetchDecisions`, `fetchStrategies`, `fetchMarketBars`, `fetchProviders`, etc.) have no timeout. If the backend is slow but not down (TCP connected but not responding), the page can hang indefinitely waiting for the response, since the browser's default fetch timeout is effectively infinite.
**Fix:** Add a timeout parameter to all fetch functions, or create a shared `fetchWithTimeout` helper:

```typescript
async function fetchWithTimeout(url: string, opts: RequestInit, timeoutMs = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...opts, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timer);
  }
}
```

## Info

### IN-01: Invalid CSS declaration (overridden)

**File:** `apps/web/src/styles/globals.css:324`
**Issue:** `.nav-mobile-toggle` declares `cursor: cursor;` (invalid CSS value) followed immediately by `cursor: pointer;` (valid). Browsers ignore the invalid declaration and use `pointer`, so there is no visual impact. However, invalid CSS indicates sloppy authoring and could be removed.
**Fix:** Delete the `cursor: cursor;` line.

### IN-02: Duplicate `.empty-state` CSS rule

**File:** `apps/web/src/styles/globals.css:740`
**Issue:** The `.empty-state` class is defined identically at lines 725-735 and again at lines 740-750. The second block completely overrides the first with identical values, so there is no visual impact, but it is dead duplication.
**Fix:** Remove the second definition (lines 740-750).

### IN-03: Inline type annotation instead of named type

**File:** `apps/web/src/app/strategy-lab/page.tsx:31`
**Issue:** The `.map()` callback uses an inline object type annotation for `agent` rather than importing or defining a named type. This duplicates the shape already defined inline in `api.ts` (fetchStrategies return type, line 78).
**Fix:** Define a named `StrategyAgent` type and reuse it in both `api.ts` and `strategy-lab/page.tsx`.

### IN-04: Screenshot tests have no visual assertions

**File:** `apps/web/tests/e2e/screenshot.spec.ts` (all 5 tests)
**Issue:** All five screenshot tests call `page.screenshot()` but make no `expect` assertions on the captured images. They verify nothing about layout, content, or visual correctness — they merely produce PNG files. A test that captures but does not assert provides no regression protection.
**Fix:** Add assertions (e.g., check for key elements, heading text, or absence of overflow) alongside the screenshot capture, or convert to pure visual-review artifacts without test status.

### IN-05: Click-outside handler coupled to a specific DOM ID

**File:** `apps/web/src/app/Navbar.tsx:71-82`
**Issue:** The click-outside handler uses `document.getElementById("nav-container")`, tightly coupling the behavior to a hardcoded DOM ID. If the nav's ID changes or multiple nav instances exist, the handler breaks silently.
**Fix:** Use a ref attached to the `<nav>` element instead of `document.getElementById`:

```typescript
const navRef = useRef<HTMLDivElement>(null);
// ...
<nav ref={navRef} className="app-nav" id="nav-container">
// ...
if (!navRef.current?.contains(event.target as Node)) {
```

## Structural Findings (fallow)

No structural findings block was provided in the review context.

---

_Reviewed: 2026-10-22T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_