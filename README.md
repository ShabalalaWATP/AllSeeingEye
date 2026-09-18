# The All Seeing Eye

An AI-assisted open-source intelligence (OSINT) fusion application: a 3D globe of live, graded events from free sources, with LLM-written intelligence products that follow UK and NATO assessment doctrine.

Status: Phase 5 social/language features and Phase 6 features are implemented alongside the globe, trackers, collection plans, warning and report pipeline. Phase 6 adds optional administrator TOTP, PDF/DOCX export, version comparison, bounded semantic search of saved reports, performance and accessibility changes, and backup/restore tools. Remaining verification and deployment gates are tracked in [the implementation plan](docs/MASTER_IMPLEMENTATION_PLAN.md) and [the Phase 6 security review](docs/security/PHASE6_ASVS_REVIEW.md). This is a self-hosted LAN application; public exposure requires the remaining review gates.

Start with [the approved proposal](docs/00_PROPOSAL_OVERVIEW.md), [current architecture](docs/01_ARCHITECTURE.md) and [feature operations](docs/PHASE5_PHASE6_OPERATIONS.md). Contributor conventions are in [CLAUDE.md](CLAUDE.md).

## Quick start (development)

Prerequisites: Python 3.12 or later, [uv](https://docs.astral.sh/uv/), Node 22.12 or later, pnpm, and Docker Desktop for the full stack.

Run the setup commands from the repository root. For a new development setup,
copy the example into the backend working directory. Preserve an existing `.env`:

```powershell
Copy-Item .env.example backend/.env
```

Backend (SQLite, no Docker needed):

```powershell
cd backend
uv sync
uv run ase migrate
uv run ase create-admin --email you@example.com --display-name "You"
uv run uvicorn ase.main:app --reload --port 8001
```

Frontend, in a second terminal starting at the repository root:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open [the development app](http://localhost:5173), sign in with the administrator you created, and you land on the globe. With the backend commands above, the default SQLite file is `backend/data/ase.db`.

The frontend proxy defaults to API port 8001. To use another port, set `ASE_DEV_API_TARGET` in `frontend/.env.local` (ignored by git). Live feeds start with the API; `ASE_FEEDS_DISABLED` can exclude source ids. Report archiving attempts to preserve cited URLs through the Wayback Machine; set `ASE_ARCHIVE_ENABLED=false` to disable that outbound step.

Configure `ASE_ENCRYPTION_KEY` before saving model profiles or enrolling TOTP.
Profiles have separate roles for reporting, translation and embeddings. Semantic
search is explicitly indexed from saved reports; it never stores raw live events.
No real LLM endpoint is configured on the current development host, so model
integration is tested with scripted adapters rather than a live provider.

## Full stack with Docker Compose

For a new Compose setup, copy `.env.example` to `.env` at the repository root.
Set `POSTGRES_PASSWORD` to a unique random value and configure `ASE_JWT_SECRET`.
Preserve an existing `.env`, its database password and `ASE_ENCRYPTION_KEY`.
Changing the password in an existing `.env` alone does not change the PostgreSQL
role password in its persistent volume; rotate that role explicitly before
updating the app configuration. From the repository root:

```powershell
docker compose up --build -d
```

Caddy serves [the local app](https://localhost) with an internal certificate and proxies `/api` to the FastAPI service, which runs its migrations on start. Create the first administrator inside the container:

```powershell
docker compose exec api ase create-admin --email you@example.com --display-name "You"
```

Keep the API and PostgreSQL ports unpublished. The API intentionally uses one
process: live data, rate limits, model admission and search coordination are
process-local. Public exposure requires the remaining security review gates.

To run the same stack on a server rather than this machine, [deployment](docs/DEPLOYMENT.md)
is the step-by-step runbook: hardening, certificates, the first administrator, backups and
the gates to close first. `ASE_TLS` and `ASE_HSTS_MAX_AGE` switch Caddy between the
internal certificate used here and real ones for a public domain.

The web image builds the standard Caddy release with locked, patched Go
dependencies. Its [build and update notes](infra/caddy-build/README.md) cover
rebuilding, module checks and scanning the resulting image.

## Recovery and verification limits

[Backup and restore](docs/BACKUP_RESTORE.md) covers consistent SQLite snapshots,
Compose PostgreSQL dumps, hash verification and restoration into new destinations.
Actual `.env` files require explicit opt-in. No backup schedule or automatic
retention deletion is installed. Real CLI recovery drills passed on temporary
SQLite and PostgreSQL 17 databases, including all 19 migrated tables and secret
decryption. Repeat the drill with the operator's storage and key handling before
depending on a backup.

The repository has no configured remote, so GitHub CI results have not been
observed. Local test results and the remaining real-model, load and
staging security checks are recorded in the implementation plan.

## Checks

Run each block from the repository root:

```powershell
uv run --project backend pytest backend/tests
uv run --project backend ruff check backend
uv run --project backend mypy --config-file backend/pyproject.toml backend/src
```

```powershell
cd backend
uv run lint-imports
```

```powershell
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend build
python scripts/check_file_length.py
```

A `justfile` wraps these (`just check`, `just test`, `just dev-api`, `just dev-web`).
