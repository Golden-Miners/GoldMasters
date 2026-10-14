# GoldMasters — Debugging Protocol

**Purpose:** Diagnose one verified failure at a time. Do not write a fix before the cause is confirmed.

## Required bug report

```text
Bug ID:
Observed error / unexpected behaviour:
Expected behaviour:
Actual behaviour:
Reproduction steps:
Relevant files or code:
Environment and versions:
Run ID / correlation ID:
Logs (secrets redacted):
What has already been tried:
Last known working revision:
```

If the user has not supplied enough evidence, ask for the smallest missing piece rather than guessing.

## Workflow

### Step 1 — Restate
Restate the observed problem in testable terms. Separate confirmed facts from assumptions. Ask the user to confirm if the restatement changes the meaning.

### Step 2 — Rank root causes
List 3–5 plausible causes only when evidence supports them. For each:
- Probability ranking (qualitative unless measured).
- Evidence supporting and contradicting it.
- Affected component/boundary.
- What evidence is missing.

Do not manufacture numerical probabilities.

### Step 3 — One fast diagnostic per cause
For each cause, provide one minimal check: a log statement, assertion, command, request inspection, or focused test. Diagnostics must not change production behaviour or expose secrets. Prefer existing observability over broad logging.

### Step 4 — Stop
Stop and wait for diagnostic results. Do not edit code, refactor, or offer a shotgun patch.

### Step 5 — Minimal fix after confirmation
Only after the evidence confirms the cause:
1. State the confirmed cause and evidence.
2. Propose the smallest change limited to the affected behaviour.
3. Explain why it fixes the observed failure.
4. Add or update a regression test.
5. List exact verification commands and expected outcomes.
6. Record files changed and any unresolved risks.
7. Update `Task.md` and `Memory.md` only after verification succeeds.

## GoldMasters-specific diagnostic checklist

- **Market data:** terminal state, selected provider, symbol mapping, timeframe, last tick/bar time, timezone, missing history, OHLC integrity.
- **LangGraph:** run ID, node entry/exit, state schema validation, edge condition, retry count, timeout, partial failure and final decision status.
- **Ollama:** configured endpoint, model availability, request latency, timeout, response parse/schema result. Do not log secrets or unrestricted prompts.
- **News:** source status, publication vs retrieval time, canonical URL, deduplication result, instrument mapping and parsing errors.
- **Strategy:** strategy ID/version, input candle window, each rule result, parameters and deterministic calculation values.
- **Risk/signal:** level source, tick size, level ordering, risk distance, reward/risk computation, blocking rule.
- **Backtest:** dataset hash, date split, timezone, fill model, transaction costs, missing bars, look-ahead checks.
- **Persistence:** transaction boundary, migration version, unique constraints, rollback behaviour, duplicate request handling.
- **Frontend/API:** request ID, status code, schema validation, loading/error state, safe error response.

## Debugging prohibitions

- No unrelated refactors.
- No disabling tests, validation, security controls, or risk gates to “make it work.”
- No fake market data to mask a provider failure.
- No catching and ignoring exceptions.
- No infinite retries.
- No claims that a bug is fixed until regression tests and the reproduction case pass.
