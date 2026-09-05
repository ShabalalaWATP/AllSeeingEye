# The All Seeing Eye

An AI-assisted open-source intelligence (OSINT) fusion application: a 3D globe of live, graded events from free sources, with LLM-written intelligence products that follow UK and NATO assessment doctrine.

Status: Phase 0 (foundation and authentication). Start with [docs/00_PROPOSAL_OVERVIEW.md](docs/00_PROPOSAL_OVERVIEW.md) and [docs/MASTER_IMPLEMENTATION_PLAN.md](docs/MASTER_IMPLEMENTATION_PLAN.md). Conventions for contributors and coding agents are in [CLAUDE.md](CLAUDE.md).

## Quick start (development)

Prerequisites: Python 3.12 or later, [uv](https://docs.astral.sh/uv/), Node 22, pnpm, and Docker Desktop for the full stack.

```bash
cp .env.example .env
```

Backend (SQLite, no Docker needed):

```bash
cd backend
uv sync
uv run ase migrate
uv run ase create-admin --email you@example.com --display-name "You"
uv run uvicorn ase.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:5173, sign in with the administrator you created, and you land on the globe.

If port 8000 is already taken, start the API on another port (`--port 8001`) and tell the dev server where it is with `ASE_DEV_API_TARGET=http://127.0.0.1:8001` in `frontend/.env.local` (ignored by git). Live feeds poll from the moment the API starts; set `ASE_FEEDS_DISABLED` to a comma-separated list of source ids to leave some out.

## Full stack with Docker Compose

Set `POSTGRES_PASSWORD` and `ASE_JWT_SECRET` in `.env`, then:

```bash
docker compose up --build -d
```

Caddy serves the app on https://localhost (internal certificate) and proxies `/api` to the FastAPI service, which runs its migrations on start. Create the first administrator inside the container:

```bash
docker compose exec api ase create-admin --email you@example.com --display-name "You"
```

## Checks

```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy src && uv run lint-imports
cd frontend && pnpm test && pnpm lint && pnpm typecheck
python scripts/check_file_length.py
```

A `justfile` wraps these (`just check`, `just test`, `just dev-api`, `just dev-web`).
