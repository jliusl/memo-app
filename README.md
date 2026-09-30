# Memo app, and the Playwright harness that tests it

This repository is a Playwright test harness. Its **System Under Test** is the memo application
under `src/` — a React + TypeScript frontend, a FastAPI backend, and PostgreSQL. The harness and
the app live together on purpose, so tests can rely on the app's own DOM and reset its data
instead of scraping somebody else's website. That decision and its consequences are in
[docs/adr/0001](docs/adr/0001-memo-app-is-the-system-under-test.md).

## What's here

| Path | What it is |
| --- | --- |
| `src/frontend/` | React 19 + TypeScript + Tailwind, built by Vite |
| `src/backend/` | FastAPI + SQLAlchemy + Alembic, on PostgreSQL |
| `src/backend/tests/` | API tests (pytest), run against a real database |
| `tests/` | Browser tests (Playwright), in TypeScript |
| `scripts/postgres.sh` | Runs a local PostgreSQL from official binaries, nothing installed |
| `docker-compose.yml` | The same PostgreSQL as a container, for machines that can run Docker |
| `CONTEXT.md` | The domain language: Memo, User, Pin, Edit, and what is deliberately absent |
| `docs/adr/` | Decisions that are expensive to reverse, with the reasoning |

## Prerequisites

- **Python 3.13+** and [uv](https://docs.astral.sh/uv/)
- **Node.js 22+**
- **PostgreSQL 17** — any one of the three routes below

## 1. Database

All three routes create the same two databases, `memo_dev` and `memo_test`, with the same
credentials, so nothing downstream knows which one you picked. `memo_test` is defined once, in
`docker/initdb/01-create-test-db.sql`, and every route reads it from there.

**Local binaries** (no installer, no service, no administrator rights — this is what the
development machine here uses, with the binaries in `D:/pgsql`):

```bash
./scripts/postgres.sh init     # once: create the cluster, the role, both databases
./scripts/postgres.sh start    # afterwards
./scripts/postgres.sh status   # or: psql | logs | stop
```

**Docker**:

```bash
docker compose up -d postgres
```

**CI** uses a `postgres:17` service container — see [.github/workflows/ci.yml](.github/workflows/ci.yml).

## 2. Backend

```bash
cd src/backend
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000 --loop app.loop:selector_event_loop
```

The `--loop` flag is not decoration. Windows gives asyncio a `ProactorEventLoop`, which psycopg
refuses to run its async mode on, so the server cannot reach PostgreSQL without a selector loop.
uvicorn builds the event loop *before* it imports the app, so this cannot be fixed from inside
the app — it has to be on the command line. On Linux it is a no-op. See
[src/backend/app/loop.py](src/backend/app/loop.py).

Configuration comes from the `.env` at the repository root (copy `.env.example`); real
environment variables win over it.

## 3. Frontend

```bash
cd src/frontend
npm ci
npm run dev      # http://localhost:5173, proxying /api to the backend on 8000
```

The proxy is what makes the session cookie a first-party cookie in development, so dev and
production are the same shape.

## 4. Tests

**API tests** — pytest against a real PostgreSQL, no mocking:

```bash
cd src/backend && uv run pytest
```

**Browser tests** — Playwright starts both servers itself, including building the frontend, so
this one command is the whole recipe:

```bash
npx playwright test                    # all three browsers
npx playwright test --project=chromium # just one
```

The suite resets the database before each test through `POST /api/__test__/reset`, a route that
only exists while `ENV=test`. `src/backend/tests/test_support_routes.py` asserts that the route
is absent otherwise, so it cannot quietly ship.

## Troubleshooting

- **`npm` fails with `Permission denied` on its cache directory.** Pass a writable one:
  `npm ci --cache "$LOCALAPPDATA/npm-cache"`.
- **Port 8000 stays busy after stopping the server.** `uvicorn --reload` runs a reloader process
  and a worker, and the worker inherits the socket, so killing the one you can see may leave the
  port held. Find the real owner with `netstat -ano | grep ':8000 '` and kill that PID.
- **`Psycopg cannot use the 'ProactorEventLoop'`.** The `--loop` flag above is missing, or a
  script is calling `asyncio.run` without first calling `use_selector_event_loop()`.
