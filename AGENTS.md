# AGENTS.md — GoldMasters (read first, every session)

Project: LangGraph multi-agent trading **signal** team. Signals only. Never place or modify orders.

## Session start (mandatory)
1. Read `Rules.md`, `Memory.md`, `Task.md` (current phase). Open `Schema.md` / `Architecture.md` / `PRD.md` / `Design.md` only for the part needed.
2. Query Supermemory for recent decisions before asking the owner anything.
3. Work only on the next unchecked task in `Task.md`.

## Token saving
- Use **Caveman** and **Ponytail** for working output (after verifying them per Rules R-12). Not for docs, UI copy, or signal reasoning.
- Use **Context7** for library docs instead of reading source or guessing. Use **Graphify**/search instead of reading whole repos.
- Save decisions to **Supermemory** and `Memory.md`; do not re-derive them.
- Do not paste large files back into chat; edit in place.

## Non-negotiables (full list in Rules.md)
- No invented numbers, APIs, or data. No mock/sample data in `src/`. Missing data → `unavailable`, never a guess.
- LLMs never output price levels; code computes levels, SL/TP, R:R.
- Follow `Schema.md` exactly for names and JSON shapes.
- Debug via `Debug.md` (diagnose → confirm → minimal fix). Audit via `Security.md` (report first, no edits until approved).
- Done = tests pass + ruff + mypy strict clean + Task.md and Memory.md updated with evidence.
- Ask one question only when blocked by an **[OPEN]** item; otherwise continue on unblocked work.

## Commands (fill in after T-0.2/T-0.3; do not guess)
Test: (pending) · Lint: (pending) · Type check: (pending) · Run backend: (pending) · Run frontend: (pending)

## Agent skills

### Issue tracker

Local markdown under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context (root `GLOSSARY.md` + `docs/adr/`). See `docs/agents/domain.md`.
