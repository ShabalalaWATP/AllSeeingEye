# Master Implementation Plan

Maintained by the implementation-plan keeper. Phases follow `05_ROADMAP.md`; decisions of record are in `00_PROPOSAL_OVERVIEW.md` and `adr/`.

## Current status

Phase 0 (Foundation) was built on 3 and 4 September 2026 after Alex approved the plan with two amendments: the 3D globe is the default view, and the logo is specifically the React Bits Evil Eye component. The acceptance flow has been exercised end to end in a browser: a visitor requested an account, the administrator approved it and received the activation link, the new user set a password, signed in and landed on the 3D globe. Both reviews (code quality and security) ran and their findings are fixed and committed.

Environment facts: Windows 11 host; git 2.51, Python 3.13, uv 0.11, Node 22, npm 11 and the Docker CLI are installed; pnpm 11 is installed at user level through npm (corepack cannot write its shims without administrator rights); `just` and `pre-commit` are not installed (use `uvx pre-commit` and plain commands, or `uv tool install rust-just`); the Docker daemon was not running during the build sessions, so PostgreSQL via compose and the container images are unverified locally, and tests run against SQLite (CI has a PostgreSQL job).

Check results at the last run (4 September 2026): backend 87 tests passing, coverage 98.4 percent, ruff, mypy strict, import-linter, bandit and pip-audit clean; frontend 86 tests passing, coverage 96.5 percent statements and 95.8 percent branches, eslint and tsc clean, production build succeeds; file-length check passes.

## Phase 0: Foundation

### Backend
- [x] `backend/pyproject.toml` with uv, ruff, mypy strict, pytest, coverage gate 90 percent, import-linter contracts
- [x] Layered skeleton `ase/{domain,application,adapters,api,infrastructure}` and `ase/container.py`
- [x] Settings (`ASE_` prefix), structured logging with redaction and tracebacks, `/api/health`, `/api/ready`
- [x] SQLAlchemy 2 async models and Alembic migration 0001 (users, account_requests, refresh_tokens, password_tokens, audit_log)
- [x] Password hashing (argon2id, parameters pinned), password policy with the 10,000 most common passwords deny list (checked on the whole password and on its core without trailing digits and punctuation, because no entry in the top 1,000 reaches the 12-character minimum)
- [x] Access tokens (JWT HS256, 15 min), refresh token rotation with family reuse detection, CSRF double-submit
- [x] Rate limiting (in-memory sliding window, LRU bounded) and account lockout
- [x] Auth endpoints: login, refresh, logout, request-account, forgot-password, set-password, me
- [x] Admin endpoints: account requests (list, approve, reject), users (list, patch, reset-link), audit log
- [x] Security headers middleware, request body cap (413), the error envelope
- [x] CLI: `ase create-admin`, `ase export-openapi`, `ase migrate`
- [x] Tests covering every endpoint and every security rule, coverage at or above 90 percent

### Frontend
- [x] Vite + React 19 + TypeScript strict + Tailwind 4 + pnpm, eslint (typescript-eslint strict, jsx-a11y, react-hooks), prettier, vitest with coverage gate 90 percent
- [x] Dark theme tokens (obsidian ground, ember accent #FF6F37, cyan data, amber warnings)
- [x] Evil Eye component copied verbatim from the React Bits registry (`EvilEye-TS-TW`) with licence header and `THIRD_PARTY_NOTICES.md`; `BrandMark` wrapper (small, frame-capped, pauses when hidden, static under reduced motion)
- [x] Auth pages: login, request account, forgot password, set password (activation and reset), all with the full-bleed Evil Eye
- [x] Auth store: access token in memory, silent refresh with CSRF header, 401 retry once, logout
- [x] App shell: left rail (Globe, Map, Trackers, Direction, Reports, Admin), top bar, brand mark
- [x] Globe page as the root route: MapLibre GL JS 6, OpenFreeMap dark style with palette overrides, `globe` projection, atmosphere; Map mode toggle to Mercator; WebGL2 fallback message
- [x] Admin pages: account requests (approve with role, reject, show activation link), users (role, active, reset link), audit log
- [x] Generated API types from the exported OpenAPI schema (`pnpm gen:api`) and a typed fetch client with zod validation at the boundary
- [x] Tests with Testing Library and MSW for every page and the auth store
- [x] Static brand assets captured from the component (favicon, apple touch icon, PWA icons, web manifest) and linked from `index.html`

### Infrastructure and repo
- [x] `.gitignore`, `.env.example`, `README.md` quick start
- [x] `docker-compose.yml` (api, web via Caddy, db postgis), `infra/Caddyfile`, non-root read-only Dockerfiles
- [x] `justfile`, `.pre-commit-config.yaml` (ruff, ruff-format, gitleaks, file-length check, frontend lint and typecheck)
- [x] `scripts/check_file_length.py` (warn at 350, fail at 400)
- [x] GitHub Actions CI: backend lint, type, test with coverage (SQLite job and PostgreSQL service job); frontend lint, typecheck, test, build; security (pip-audit, bandit, pnpm audit, gitleaks); semgrep; trivy image scans; actions pinned to commit SHAs
- [x] `SECURITY.md` at the root, `docs/DEVELOPMENT_STORY.md`

### Acceptance
- [x] A visitor requests an account; an admin approves it and receives an activation link; the user sets a password, logs in and lands on the 3D globe (verified in the embedded browser and in Chrome on 4 September 2026)
- [x] Code quality review and security review completed with findings fixed (see `DEVELOPMENT_STORY.md`)
- [x] All checks green locally; coverage at or above 90 percent on both sides

## Known follow-ups carried into Phase 1

- Replace the hand-rolled `useResource` and `useAuditLog` hooks with TanStack Query (the architecture's choice for server state); two lint suppressions mark the spots.
- The bootstrap session refresh fires even when no CSRF cookie exists, producing a harmless 403 in the console on first visit; skip the call when the cookie is absent.
- Run the compose stack once Docker Desktop is running: confirm the PostgreSQL migration path, the Caddy headers on API and SPA routes, and the image builds.
- Push to GitHub to get a first CI run; several workflow steps (semgrep, trivy, the PostgreSQL job) have never executed.
- Consider a JSON depth limit alongside the body size cap, and a challenge instead of a hard lockout before any public exposure.

## Later phases

See `05_ROADMAP.md`: Phase 1 fusion core and globe data, Phase 2 grading and reports, Phase 3 trackers, Phase 4 direction and warning, Phase 5 social and languages, Phase 6 hardening.

## Blockers

- Docker Desktop was not running; the compose stack and the PostgreSQL migration path are unverified until it is started (`docker compose up --build`).
- No git remote yet, so CI has not run.
