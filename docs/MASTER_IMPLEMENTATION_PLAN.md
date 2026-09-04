# Master Implementation Plan

Maintained by the implementation-plan keeper. Phases follow `05_ROADMAP.md`; decisions of record are in `00_PROPOSAL_OVERVIEW.md` and `adr/`.

## Current status

Phase 0 (Foundation) started 3 September 2026 after Alex approved the plan with two amendments: the 3D globe is the default view, and the logo is specifically the React Bits Evil Eye component.

Environment facts: Windows 11 host; git 2.51, Python 3.13, uv 0.11, Node 22, npm 11 and the Docker CLI are installed; pnpm is provisioned through corepack; `just` and `pre-commit` are not installed (use `uvx pre-commit` and plain commands, or `uv tool install rust-just`); the Docker daemon was not running during the first build session, so PostgreSQL via compose is unverified locally and tests run against SQLite.

## Phase 0: Foundation

### Backend
- [ ] `backend/pyproject.toml` with uv, ruff, mypy strict, pytest, coverage gate 90 percent, import-linter contracts
- [ ] Layered skeleton `ase/{domain,application,adapters,api,infrastructure}` and `ase/container.py`
- [ ] Settings (`ASE_` prefix), structured logging with redaction, `/api/health`, `/api/ready`
- [ ] SQLAlchemy 2 async models and Alembic migration 0001 (users, account_requests, refresh_tokens, password_tokens, audit_log)
- [ ] Password hashing (argon2id), password policy with the 10,000 most common passwords deny list (checked on the whole password and on its core without trailing digits and punctuation, because no entry in the top 1,000 reaches the 12-character minimum)
- [ ] Access tokens (JWT HS256, 15 min), refresh token rotation with family reuse detection, CSRF double-submit
- [ ] Rate limiting (in-memory sliding window) and account lockout
- [ ] Auth endpoints: login, refresh, logout, request-account, forgot-password, set-password, me
- [ ] Admin endpoints: account requests (list, approve, reject), users (list, patch, reset-link), audit log
- [ ] Security headers middleware and the error envelope
- [ ] CLI: `ase create-admin`, `ase export-openapi`
- [ ] Tests covering every endpoint and every security rule, coverage at or above 90 percent

### Frontend
- [ ] Vite + React 19 + TypeScript strict + Tailwind 4 + pnpm, eslint (typescript-eslint strict, jsx-a11y, react-hooks), prettier, vitest with coverage gate 90 percent
- [ ] Dark theme tokens (obsidian ground, ember accent #FF6F37, cyan data, amber warnings)
- [ ] Evil Eye component copied from the React Bits registry (`EvilEye-TS-TW`) with licence header and `THIRD_PARTY_NOTICES.md`; `BrandMark` wrapper (small, frame-capped, pauses when hidden, static under reduced motion)
- [ ] Auth pages: login, request account, forgot password, set password (activation and reset), all with the full-bleed Evil Eye
- [ ] Auth store: access token in memory, silent refresh with CSRF header, 401 retry once, logout
- [ ] App shell: left rail (Globe, Map, Trackers, Direction, Reports, Admin), top bar, brand mark
- [ ] Globe page as the root route: MapLibre GL JS 6, OpenFreeMap dark style, `globe` projection, atmosphere; Map mode toggle to Mercator; WebGL2 fallback message
- [ ] Admin pages: account requests (approve with role, reject, show activation link), users (role, active, reset link), audit log
- [ ] Generated API types from the exported OpenAPI schema (`pnpm gen:api`) and a typed fetch client
- [ ] Tests with Testing Library and MSW for every page and the auth store

### Infrastructure and repo
- [ ] `.gitignore`, `.env.example`, `README.md` quick start
- [ ] `docker-compose.yml` (api, web via Caddy, db postgis), `infra/Caddyfile`, non-root read-only Dockerfiles
- [ ] `justfile`, `.pre-commit-config.yaml` (ruff, ruff-format, gitleaks, prettier, eslint, file-length check)
- [ ] `scripts/check_file_length.py` (warn at 350, fail at 400)
- [ ] GitHub Actions CI: backend lint, type, test with coverage (SQLite job and PostgreSQL service job); frontend lint, typecheck, test, build; security (pip-audit, npm audit, bandit, gitleaks)
- [ ] `SECURITY.md` at the root, `docs/DEVELOPMENT_STORY.md`

### Acceptance
- [ ] A visitor requests an account; an admin approves it and receives an activation link; the user sets a password, logs in and lands on the 3D globe
- [ ] Code quality review and security review completed with findings fixed
- [ ] All checks green locally; coverage at or above 90 percent on both sides

## Later phases

See `05_ROADMAP.md`: Phase 1 fusion core and globe data, Phase 2 grading and reports, Phase 3 trackers, Phase 4 direction and warning, Phase 5 social and languages, Phase 6 hardening.

## Blockers

- Docker Desktop was not running; the compose stack and the PostgreSQL migration path are unverified until it is started (`docker compose up --build`).
