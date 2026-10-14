# Quality Gate (D-38/D-39/D-40)

One command is the single meaning of green:

```sh
sh scripts/gate          # full ordered gate (Git for Windows `sh` runs it here)
sh scripts/gate --fast   # commit subset: changed-file format/lint/mypy + security tests
```

Hook wiring (one-time, local only — not run from any plan):

```sh
git config core.hooksPath .githooks
```

## Ordered step list

1. `uv run ruff format --check .`
2. `uv run ruff check .`
3. `uv run mypy --strict .`
4. `uv run pytest` (includes contracts tests, boundary scan, integration)

`--fast` restricts format/lint to `*.py` files changed vs the index and runs
only `pytest tests/security`; mypy still runs workspace-wide (it is fast).

`set -eu` plus `set -o pipefail` semantics: the first failing step stops the
run non-zero and names the step.

## Observed result (first local run, 2026-10-14)

`sh scripts/gate` → `gate: PASS`: format 240 files clean, lint clean,
`mypy --strict` clean over 31 source files, `124 passed` pytest.

## CI reconciliation (honest)

This machine has no git remote, no `.github/` directory and no CI provider,
and Docker is absent so `nektos/act` is not viable. The criterion is satisfied
*structurally* by this recorded build-failing local runner plus the tracked
`.githooks/pre-commit` hook. Hosted-CI *execution* is pending a remote and is
**NOT** claimed as done. No workflow file is invented: an unrunnable
`.github/workflows/` file would be a false claim, not evidence.
