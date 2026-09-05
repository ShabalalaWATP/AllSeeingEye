# The All Seeing Eye (code name `ase`)

Self-hosted OSINT fusion app: free feeds on a 3D globe (the default view), graded before an LLM writes doctrine-compliant assessments. The approved design lives in `docs/`. Read in this order when starting work: `docs/00_PROPOSAL_OVERVIEW.md`, `docs/MASTER_IMPLEMENTATION_PLAN.md`, `docs/01_ARCHITECTURE.md`, `docs/07_SECURITY_BY_DESIGN.md`, `docs/DEVELOPMENT_STORY.md`. API contracts live in `docs/api/`.

Phase 5 and Phase 6 features are implemented. See
`docs/PHASE5_PHASE6_OPERATIONS.md` for operator flows and
`docs/security/PHASE6_ASVS_REVIEW.md` for outstanding deployment gates. Do not
equate local tests with public readiness, a live PostgreSQL restore, a real-model
integration or an observed GitHub CI run.

## Layout

```
backend/    Python 3.12+, FastAPI, SQLAlchemy 2 async, Alembic, uv.  src/ase/{domain,application,adapters,api,infrastructure,container}
frontend/   React 19, TypeScript strict, Vite, Tailwind 4, pnpm.     src/{app,features,components,lib,stores}
infra/      Caddyfile, Dockerfiles.  docker-compose.yml at the root.
docs/       Design, ADRs, plan, development story, API contracts.
scripts/    Repo-level checks and safe SQLite/Compose PostgreSQL backup and restore.
```

## Commands

```
Backend:   cd backend && uv sync
           uv run pytest                      (coverage gate 90 percent, SQLite in memory)
           uv run ruff check . && uv run ruff format --check . && uv run mypy src
           uv run ase create-admin --email you@example.com --display-name "You"
           uv run ase export-openapi ../frontend/src/lib/api/openapi.json
           uv run uvicorn ase.main:app --reload --port 8001
Frontend:  cd frontend && pnpm install
           pnpm dev | pnpm test | pnpm lint | pnpm typecheck | pnpm build | pnpm gen:api
Stack:     docker compose up --build          (Docker Desktop must be running)
Checks:    uvx pre-commit run --all-files ; python scripts/check_file_length.py
```

## Conventions (non-negotiable)

- Layering: `domain` imports nothing from other layers; `application` imports `domain` only; `adapters`, `api` and `infrastructure` may import `application` and `domain`. Enforced by `import-linter` in the backend and by review in the frontend (features do not import each other; they share through `components`, `lib` and `stores`).
- Ports are `typing.Protocol` classes under `ase/application/ports/`; adapters implement them. `ase.container` remains a package and the only composition root: `__init__.py` builds shared services and auth/admin factories, `features.py` holds feature factories, `reporting.py` holds report factories, and `repositories.py` builds the session-scoped repository bundle. Mixin dependencies are declared under `TYPE_CHECKING`; keep this shape.
- Routers and React components are thin. Business rules live in use cases (backend) and hooks or stores (frontend).
- File length: 350 lines target, 400 hard maximum (CI fails). Split by responsibility, never by line count.
- Security: follow `docs/07_SECURITY_BY_DESIGN.md`. Never log or echo secrets. Never render HTML from data. Validate at boundaries. Authorisation is checked at object level in the application layer, not only at the route.
- Tests: pytest and vitest. No live network in tests; use fixtures and MSW. Coverage gate 90 percent, higher on auth, grading and validation.
- Types: mypy strict; TypeScript strict. Frontend API types are generated from the backend OpenAPI schema (`pnpm gen:api`); never hand-write DTOs.
- Environment variables use the `ASE_` prefix and are documented in `.env.example`. No secrets in the repo.
- UK English in docs, comments, commit messages and UI copy. No em dashes. Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Do not commit build output, `node_modules`, `.venv`, `data/`, coverage output or IDE files.
- The 3D globe is the default view and the root route. The brand mark is the React Bits Evil Eye component (see `docs/01_ARCHITECTURE.md` section 5.6), never a redrawn imitation.
- Persist reports, frozen report evidence, configuration and the small operational aggregates only. Raw live events remain in the bounded in-memory store. Semantic search uses JSON vectors for at most the latest 1,000 reports and 4,096 dimensions, with SQLite/PostgreSQL parity; no pgvector or live-event index. See ADR 0008.
- Authentication reloads the current user's active state and role from the database for each protected request. Reports and collection plans are shared reads for authenticated users; report/plan mutations require the owner or an admin. Optional administrator TOTP is implemented. Do not describe report reads as owner-private or browser rendering as a DOMPurify Markdown path: reports render structured React text.
- Local development uses port 8001 and the frontend proxy defaults there. Backend `.env` and relative SQLite paths resolve from the backend process working directory; Compose reads the root `.env`.
- Backups are explicit operator commands, documented in `docs/BACKUP_RESTORE.md`. No schedule or automatic deletion is installed. Restore drills target fresh destinations and preserve the encryption key separately unless `.env` inclusion is explicitly selected.
