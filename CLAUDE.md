# CLAUDE.md

## Run the tests before you commit

A commit lands only with every test that covers your change passing. Run them, then commit.

| You changed | Run |
| --- | --- |
| `src/backend/` | from `src/backend/`: `uv run ruff format . && uv run ruff check .`, then `uv run pytest` |
| `src/frontend/`, `tests/`, `playwright.config.ts` | `npx playwright test` |
| both | both columns |

Prose and comment edits alone - `*.md`, `docs/`, a comment inside a config file - commit
without the suite. Anything that changes what the code does, a test included, runs it.

Both suites want PostgreSQL running first. README.md has the three routes to it.

## The app under `src/` is the System Under Test

Not a demo, and its test hooks are load-bearing - see `docs/adr/0001`.

- Browser tests reach controls by role and accessible name, so every control needs a real
  `<label>`.
- `POST /api/__test__/reset` registers only under `ENV=test`, and
  `src/backend/tests/test_support_routes.py` fails if it ever appears elsewhere.

## An edit is a content change

`updated_at` moves when a Memo's title or body actually change, and nothing else. The router
sets it explicitly, so leave `onupdate` off the column. `docs/adr/0002` explains why pinning
must not reorder the list.

## Models and migrations move together

Changing `src/backend/app/models.py` means generating its migration in the same commit:

    cd src/backend && uv run alembic revision --autogenerate -m "what changed"

CI fails on drift between the models and `alembic/`, a failure nothing local reports.

## Words

`CONTEXT.md` is the glossary, and it is binding: Memo, User, Owner, Pin, Edit, Delete. Use
those words in code, tests and commits; each entry's "Avoid" line names the synonyms to reach
past.

## `sandbox/` is spent

Throwaway tests from before the memo app existed, and untracked local scratch - leave it be.
New tests go in `tests/` (browser) or `src/backend/tests/` (API).
