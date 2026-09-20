# The All Seeing Eye (code name `ase`)

Self-hosted OSINT fusion app: free feeds on a 3D globe (the default view), graded before an LLM writes mechanically validated assessments. The approved design lives in `docs/`. Read in this order when starting work: `docs/MASTER_AUTOMATED_RESEARCH_PLAN.md`, `docs/OSINT_PRODUCT_DIRECTION.md`, `docs/01_ARCHITECTURE.md`, `docs/07_SECURITY_BY_DESIGN.md`, `docs/DEVELOPMENT_STORY.md`. `docs/MASTER_IMPLEMENTATION_PLAN.md` preserves the earlier Phase 0 to 6 delivery history; `docs/00_PROPOSAL_OVERVIEW.md` is the original proposal. API contracts live in `docs/api/`.

Phase 5 and Phase 6 features are implemented. See
`docs/PHASE5_PHASE6_OPERATIONS.md` for operator flows and
`docs/security/PHASE6_ASVS_REVIEW.md` for outstanding deployment gates. Do not
equate local tests with public readiness, recovery of the operator's backups,
a real-model integration or an observed GitHub CI run. A prior synthetic
SQLite/PostgreSQL 17 recovery through migration `0011` is recorded separately;
the earlier improvement plan preserves identity/team delivery history. The active
automated-research plan tracks the current, unfinished collection/input/follow-up
milestone. Its focused tests do not establish final integration or model quality.

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
           uv run ase migrate                 (explicitly target the intended database)
           uv run ase create-admin --email you@example.com --display-name "You"
           uv run ase export-openapi ../frontend/src/lib/api/openapi.json
           uv run uvicorn ase.main:app --reload --port 8001
Frontend:  cd frontend && pnpm install
           pnpm dev | pnpm test | pnpm lint | pnpm typecheck | pnpm build | pnpm gen:api
Stack:     docker compose up --build          (Docker Desktop must be running)
Checks:    uvx pre-commit run --all-files ; python scripts/check_file_length.py
```

## Conventions (non-negotiable)

- Layering: `domain` imports nothing from other layers; `application` imports `domain` only; `adapters`, `api` and `infrastructure` may import `application` and `domain`. Enforced by `import-linter` in the backend. API modules must not import persistence adapters except the named legacy subscription projections in `pyproject.toml`. Frontend ESLint resolves and rejects cross-feature imports; features share through `components`, `lib` and `stores`.
- Ports are `typing.Protocol` classes under `ase/application/ports/`; adapters implement them. `ase.container` remains a package and the only composition root: `__init__.py` builds shared services and admin factories, `auth.py` holds authentication factories, `features.py` holds feature factories, `reporting.py` holds report factories, and `repositories.py` builds the session-scoped repository bundle. Mixin dependencies are declared under `TYPE_CHECKING`; keep this shape.
- Routers and React components are thin. Business rules live in use cases (backend) and hooks or stores (frontend).
- Import the reusable application factory from `ase.app_factory`; `ase.main:app` is the ASGI instance entry point. `ase.app_lifecycle` owns worker startup and cleanup, including partial-startup unwinding. Report stages are assembled in the container; subscription admission executes through application services and a transaction port.
- File length: 350 lines target, 400 hard maximum (CI fails). Split by responsibility, never by line count.
- Security: follow `docs/07_SECURITY_BY_DESIGN.md`. Never log or echo secrets. Never render HTML from data. Validate at boundaries. Authorisation is checked at object level in the application layer, not only at the route.
- Tests: pytest and vitest. No live network in tests; use fixtures and MSW. Coverage gate 90 percent, higher on auth, grading and validation.
- Types: mypy strict; TypeScript strict. Frontend API types are generated from the backend OpenAPI schema (`pnpm gen:api`); never hand-write DTOs.
- Environment variables use the `ASE_` prefix and are documented in `.env.example`. No secrets in the repo.
- UK English in docs, comments, commit messages and UI copy. No em dashes. Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Do not commit build output, `node_modules`, `.venv`, `data/`, coverage output or IDE files.
- The 3D globe is the default view and the root route. The brand mark is the React Bits Evil Eye component (see `docs/01_ARCHITECTURE.md` section 5.6), never a redrawn imitation.
- Administration is a separate guarded workspace under `/admin`. Only administrators see its research-navigation entry or mount its shell. Default administrator sign-in lands on `/admin`; explicit requested routes are preserved, and other accounts keep the globe default. Keep administrator navigation separate from research controls, including on mobile.
- Persist reports, frozen evidence, accounts/teams, configuration and small operational aggregates only. Raw public events remain shared in the bounded in-memory store and never enter the database. Semantic search stores at most 1,000 JSON vectors of at most 4,096 dimensions globally, checks capacity before model calls, and never evicts another team's vectors to index one caller's work. Queries and counts cover up to the caller's latest 1,000 visible reports. No pgvector or live-event index. See ADRs 0008 and 0010.
- CelesTrak GP orbital inputs are a narrow cache exception to the live-event rule: four bounded replace-in-place files and request cooldowns under `ASE_SATELLITE_CACHE_DIR`, for one feed worker. Do not persist generated map positions or orbital history. See `docs/SATELLITE_COVERAGE.md`.
- Authentication checks the current active user, security version and live refresh family on every protected request. JWTs require `sid` and `sv`; old-format access JWTs fail, while valid existing refresh cookies may rotate. All users can enrol email or authenticator MFA; administrators require an MFA-verified session and mandatory enrolment when no factor exists. See docs/MFA_OPERATIONS.md. Streams recheck before delivery and every 15 seconds while idle, filter alerts by scope and emit `access.changed` for client invalidation.
- Roles are user/manager/admin. Non-admin team leadership needs both global manager capability and that team's manager designation. Personal operational records are creator/admin-visible; team records require current membership or admin. Scope applies to lists, direct reads, historical versions, exports, comparisons, search, alerts and background work. SQL filtering precedes limits/counts. Linked records must share the same personal owner or team, even for admin operations.
- Use `AccessPolicy` for current authorisation. Mutations take the shared administration guard before account locks and fresh checks; never hold it across model/network work. Recheck after external work before persistence and after document rendering before download. Archived teams remain readable; ordinary writes stop, admins retain manual operational override, and roster writes require reactivation. Background team work requires an active owner, active team and current membership even for admins.
- Migration `0014` preserves old roots as personal, logs legacy scope conflicts, and leaves orphan alerts admin-only. No operator database or real `.env` was migrated during development. Review the conflict inventory; never guess team assignments or silently widen access. Reports render structured React text, not HTML from Markdown or DOMPurify.
- Local development uses port 8001 and the frontend proxy defaults there. Backend `.env` and relative SQLite paths resolve from the backend process working directory; Compose reads the root `.env`.
- Backups are explicit operator commands, documented in `docs/BACKUP_RESTORE.md`. No schedule or automatic deletion is installed. Restore drills target fresh destinations and preserve the encryption key separately unless `.env` inclusion is explicitly selected.
