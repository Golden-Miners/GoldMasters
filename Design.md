# GoldMasters — Design Brief

**Status:** Draft aligned to PRD v1.0. No implementation or user testing has been claimed.

## 1. Design principles — three rules

1. **Evidence before conclusion.** Every decision headline must expose freshness, provider, timeframe, and evidence completeness before showing the rationale.
2. **Uncertainty is a first-class state.** Use explicit `NO TRADE`, `INSUFFICIENT DATA`, stale, conflicted, and unavailable states. Never use green styling to imply certainty.
3. **Dense, scannable, controlled.** This is a professional research console, not a consumer trading game. Put critical state and primary action first; put technical detail behind expandable panels.

## 2. Visual direction

- **Mood:** restrained research terminal, precise, quiet, high information density, legible for long sessions.
- **Reference qualities:** the hierarchy of an institutional risk dashboard, compact tables from developer tooling, and chart-first analytical workspaces. These are directional qualities, not claims of affiliation or pixel-copying.
- **Avoid:** neon gradients, glassmorphism that harms contrast, decorative candlesticks, fake real-time tickers, arbitrary “AI confidence” gauges, celebratory trade animations, and red/green as the only status channel.
- **Primary layout:** dark-by-default with a deliberate light theme if implementation cost permits. Charts and tables should remain readable in both themes.

## 3. Design tokens

These are proposed product tokens, not existing brand standards.

### Color palette
- `canvas`: `#0B1220` — app background.
- `surface-1`: `#111B2E` — main panels.
- `surface-2`: `#18253A` — nested panels and hover surfaces.
- `border`: `#2A3A52` — separators.
- `text-primary`: `#F3F6FC` — primary text.
- `text-secondary`: `#B5C2D6` — secondary text.
- `accent`: `#67B7FF` — focus, selected controls, links.
- `positive`: `#3BC98A` — positive/valid state, always paired with label/icon.
- `negative`: `#FF6B78` — negative/blocked state, always paired with label/icon.
- `warning`: `#F4C15D` — caution or stale evidence.
- `neutral`: `#9AAAC0` — unknown/inactive.
- `focus`: `#A7D7FF` — visible keyboard focus ring.

Verify actual WCAG contrast ratios programmatically for rendered foreground/background pairs; do not assume a token passes in every use. Do not use status colors alone.

### Typography
- Preferred UI font: **Inter** if licensed/available in the chosen deployment; fallback `system-ui, sans-serif`. Inter's neutral forms suit dense numeric interfaces. Confirm font delivery and licensing before bundling.
- Numeric values: tabular numerals enabled.
- Scale: 12px metadata, 13px dense table, 14px body, 16px emphasized body, 20px section heading, 24px page heading, 30px major decision.
- Line heights: 1.25 headings; 1.45 body; dense tables at least 1.35.

### Spacing, radius, shadows
- Spacing scale: 4, 8, 12, 16, 20, 24, 32, 40, 48px.
- Radius: 4px for inputs/badges; 8px for panels; 12px only for major page containers.
- Shadows: minimal; use border and surface contrast first. If elevation is required, use a subtle shadow with no colored glow.
- Motion: 120–180ms for state changes; respect reduced-motion preferences. No animation for continuously changing market values that distracts from reading.

## 4. Screen inventory

1. **Overview** — global health, active instrument, latest run, decisions needing review.
2. **Instrument Workbench** — chart, timeframe controls, trend/structure, zones, strategy evaluations.
3. **Decision Detail** — decision status, proposed levels, evidence ledger, conflicts, invalidation, risk checks.
4. **News & Sentiment** — sourced news feed, instrument mapping, published/retrieved timestamps, coverage and conflicts.
5. **Strategy Lab** — strategy registry, versions, rule definitions, eligibility and status.
6. **Backtest Results** — assumptions, dataset coverage, splits, metrics, equity/drawdown curves and trade list.
7. **Journal** — immutable decisions, filters, outcome observations and review notes.
8. **Agent Runs** — graph trace, node states, timing, schema validation and sanitized error detail.
9. **Data Providers** — provider setup, symbol mappings, capability and freshness diagnostics.
10. **Settings & Model Health** — Ollama endpoint/model configuration, model availability, timeouts and runtime status.
11. **System Health** — API/database/provider health, queue/graph status, recent errors and audit events.

## 5. Core user flows

### Flow A — Research an instrument
1. Open Instrument Workbench.
2. Select canonical instrument, provider, timeframe, and analysis window.
3. UI displays provider mapping and last data timestamps.
4. Run validation and show missing/stale-data warnings before analysis.
5. Start analysis graph.
6. Review trend, structure, strategy rule checks, news, and sentiment.
7. Open Decision Detail to review CEO outcome and evidence.
8. Save decision snapshot to journal automatically; show persistence status.

### Flow B — Review a candidate signal
1. Open a decision from Overview or Workbench.
2. Confirm decision status and evidence freshness.
3. Inspect proposed entry, stop and targets if present.
4. Inspect strategy rule checks, risk validation, conflicts, and invalidation conditions.
5. If status is `NO_TRADE` or `INSUFFICIENT_DATA`, show specific blocking reasons and missing evidence.
6. User may add a review note; original decision remains immutable.

### Flow C — Investigate news
1. Choose instrument and time window.
2. Review source list and retrieval status.
3. Open a story to see source, title, publication time, retrieval time, URL, and mapping rationale.
4. Review sentiment coverage and disagreement.
5. Return to decision detail; news is context, not a standalone trade trigger.

### Flow D — Evaluate a strategy
1. Select a registered strategy and immutable version.
2. Choose dataset, instrument, timeframe, and date range.
3. Review assumptions and data-quality warnings.
4. Run backtest.
5. Inspect train/validation/out-of-sample separation and costs.
6. Export or save the result; promotion to live registry requires explicit review and tests.

### Flow E — Diagnose system health
1. Open System Health or Agent Runs.
2. Filter by failed node, provider, time, or run ID.
3. Inspect sanitized error, node input/output schema status, and correlation ID.
4. Re-run only after the underlying cause is understood; do not create uncontrolled retry loops.

## 6. Per-screen layout

- **Overview:** top bar with environment/provider status; left main column for latest decisions; right column for data health and recent failed runs. Primary action: `Analyse instrument`.
- **Instrument Workbench:** instrument/timeframe selector; chart area; trend/structure strip; strategy rule-check table; evidence side panel. Primary action: `Run analysis`.
- **Decision Detail:** decision/status header; level card; thesis and invalidation; agent evidence accordion; conflict/risk panel; source links. Primary action: `Open evidence` or `Add review note`, never `Execute trade`.
- **News & Sentiment:** filter bar; chronological news list; detail pane; coverage/status banner. Primary action: `Inspect source`.
- **Strategy Lab:** registry table; selected strategy details; version/rules panel; validation status. Primary action: `Run backtest`.
- **Backtest Results:** assumptions banner; KPI row; equity/drawdown charts; trade table; split/date controls. Primary action: `Compare run`.
- **Journal:** searchable/filterable table; selected record details; append-only review notes. Primary action: `Review outcome`.
- **Agent Runs:** run list; graph topology/trace; node detail; sanitized logs. Primary action: `Inspect failed node`.
- **Data Providers:** provider cards/table; symbol mapping editor; health and freshness. Primary action: `Test connection`.
- **Settings & Model Health:** runtime settings, installed-model discovery, health result and timeout settings. Primary action: `Check Ollama`.
- **System Health:** service status, recent incidents, database/provider health, audit trail. Primary action: `Inspect incident`.

## 7. Component library

- **StatusBadge:** valid, warning, blocked, stale, unavailable, running, completed, failed; label and icon required.
- **DecisionBanner:** TRADE/NO TRADE/INSUFFICIENT DATA; includes status text and top reason.
- **FreshnessIndicator:** latest candle timestamp, retrieval timestamp, policy result.
- **ProviderSelector:** provider, symbol mapping, capability and health state.
- **InstrumentTimeframePicker:** canonical instrument and timeframe with unsupported combinations disabled and explained.
- **EvidenceRow:** claim, source/reference, timestamp, agent, validation state.
- **RuleCheckTable:** pass/fail/unknown/not-applicable plus evidence and reason.
- **PriceLevelPanel:** entry, stop, targets, risk distance, R multiple; hidden or unavailable when not validated.
- **AgentNodeStatus:** queued/running/succeeded/failed/skipped/timed-out with duration and error summary.
- **NewsItemRow:** source, headline, publication/retrieval timestamps, instrument relevance.
- **MetricCard:** value, definition, sample size, period, calculation provenance.
- **DataTable:** sorting, filtering, pagination, empty/loading/error states.
- **ConfirmDialog:** destructive configuration changes only; never used to imply execution capability.
- **InlineNotice:** info, warning, error, success; accessible icon and text.
- **SourceLink:** safe external navigation with source label; external URLs must be validated.
- **TracePanel:** run ID, graph version, node order, schema status, sanitized output.
- **FormField:** label, help text, validation error and keyboard focus state.

Every component needs default, hover, focus-visible, disabled, loading, error, and empty states where applicable.

## 8. Key-screen states

- **Overview:** empty (no runs yet), loading, healthy, degraded provider, API error, offline backend.
- **Workbench:** no instrument selected, unsupported mapping, loading candles, stale/missing candles, analysis running, no setup, completed analysis, failed analysis.
- **Decision Detail:** decision available, insufficient evidence, missing levels, conflicting agents, journal save failure, record not found.
- **News & Sentiment:** no stories, source unavailable, partial coverage, duplicate-heavy coverage, conflicting sentiment, retrieval error.
- **Strategy Lab:** no strategies registered, disabled strategy, schema-invalid config, version conflict, successful validation.
- **Backtest:** no runs, running, completed, invalid assumptions, insufficient history, partial data, failed run.
- **Journal:** empty, loading, no filter matches, outcome pending, write failure, database unavailable.
- **Agent Runs:** no runs, running, partial failure, retry exhausted, output schema failure.
- **Providers:** unconfigured, testing, connected, stale, unsupported symbol, disconnected, permission error.
- **Model Health:** Ollama unavailable, model missing, checking, ready, timeout, schema-invalid output.
- **System Health:** healthy, degraded, unavailable, unknown; unknown must not be styled as healthy.

## 9. Responsive behaviour

- **Desktop (>= 1200px):** three-zone analytical layout where useful; chart and evidence side-by-side; persistent status header.
- **Tablet (768–1199px):** two-column layout; evidence panels become drawers; data tables retain key columns and allow horizontal scrolling.
- **Mobile (< 768px):** single column; chart first, decision status next, details in accordions; sticky primary action only when it does not obscure content. Never compress complex tables until values become unreadable.
- Responsive breakpoints are proposed defaults and should be validated in implementation.
- Support zoom to 200% without loss of core functionality.

## 10. Accessibility

- Target WCAG 2.2 AA.
- Body text contrast target >= 4.5:1; large text >= 3:1; non-text UI indicators >= 3:1 where applicable. Verify actual combinations with automated and manual testing.
- Full keyboard operation; visible focus; logical focus order matching visual order.
- Escape closes dialogs/drawers and returns focus to the trigger.
- Use semantic headings, labels, tables, and buttons; no clickable `div` controls.
- Announce asynchronous run state changes with appropriate live regions without repeatedly announcing changing prices.
- Provide accessible names for charts and a tabular alternative for chart data.
- Status uses text/icon plus color; never color alone.
- Respect reduced motion, browser zoom, screen readers, and OS high-contrast settings.
- Validate ARIA roles/states; avoid redundant or incorrect ARIA.
