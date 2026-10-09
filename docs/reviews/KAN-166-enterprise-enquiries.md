# KAN-166 implementation evidence

The public enquiry endpoint defaults to disabled, validates bounded structured
fields and returns a uniform receipt for accepted, duplicate and honeypot input.
Client, normalised-email and global rate limits use the existing process-local
limiter. Storage and audit contain no client IP; audit contains only the enquiry
ID. Plain-text email goes to the configured operator, with a fixed subject.

The initial endpoint regression failed with 404 before implementation. An
independent review then identified a first-write SQLite savepoint escaping outer
rollback. The rollback, audit-failure and unrelated-integrity-error regressions
failed before the correction. Direct dialect-specific insert with a conflict
target on the submission key now participates in the caller's transaction. A
two-connection SQLite test confirms one stored duplicate. The reviewer's separate
in-memory probe changed from one retained row after rollback to zero.

Verified checks:

- 62 focused backend tests passed after the transaction correction, including the
  release-fence architecture tests.
- A subsequent coverage run passed 61 tests including the new configuration and
  standalone migration checks. The six new implementation modules measured 99%
  combined line/branch coverage (165/166 statements, 19/20 branches); public route,
  request schema, application, repository and wiring measured 100%.
- Strict mypy passed 1,599 source files; the corrected repository also passed a
  focused strict check. Ruff check/format, three import contracts and targeted
  Bandit passed. File-length and whitespace checks passed, with pre-existing
  length warnings only.
- OpenAPI and TypeScript contracts were regenerated. Ten public-site/product/auth
  frontend tests passed, along with strict frontend type checks and focused
  ESLint/Prettier.

Two attempts to start module-name-scoped pytest coverage hit a NumPy import
initialisation error before test collection. A normal NumPy import succeeded.
Directory-scoped `coverage run --source=src/ase -m pytest ... --no-cov`, followed by
an explicit report include list, ran successfully. No coverage floor was lowered.

Migration 0093's own SQLite upgrade and protected downgrade passed in an empty
disposable database. Its parent 0092 is delivered by KAN-182; full-chain SQLite
and PostgreSQL migration checks must run after that dependency is integrated.
The existing deployment controller treats Alembic changes as manual rollout.
No operator database was migrated or production feature enabled.

The full repository suite/CI, final migration chain and authorised merge remain
outstanding. SMTP was mocked, not contacted. Enabling the feature also requires
the approved privacy/controller information, administrator workflow and retention
from KAN-165/167, and the KAN-168 public form. Failed SMTP leaves the enquiry stored
for administrator follow-up; this endpoint does not automatically retry email.
