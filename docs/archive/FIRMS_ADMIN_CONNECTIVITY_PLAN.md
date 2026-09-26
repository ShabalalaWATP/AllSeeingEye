# FIRMS administrator connectivity implementation

This slice adds a global NASA FIRMS credential editor inside Administration >
Sources. It does not introduce team-specific credentials or a general URL editor.
The fixed NASA origin, NOAA-20 product, one-day Area API request, protected secret
URL transport, parser bounds and thermal-observation interpretation remain intact.

## Workflow and authority

- Read masked configuration metadata. No key suffix, ciphertext, URL containing a
  key, proof-family identifier or secret fingerprint is returned.
- Save a candidate encrypted with the existing `ASE_ENCRYPTION_KEY` cipher. The
  active credential remains unchanged. Candidate validity is 15 minutes.
- Test the saved candidate with a bounded NASA request, without publishing,
  retaining or grading test observations. Test attempts invalidate earlier proof
  before network I/O; cancellation leaves no activation proof.
- Confirm only the current candidate revision and successful test generation.
  Proof is scoped to the administrator, refresh family, security version,
  configured area and 15-minute lifetime. Confirmation advances a monotonic
  active generation, including when the same key is later activated again.
- Removal clears database active and candidate credentials. Existing public
  observations retain their ordinary retention policy.
- Current administrator/MFA session checks apply before access and after awaited
  preparation. Private responses receive no-store headers. Audit entries contain
  action, actor, source and time, without credential or upstream response text.

## Runtime and operator policy

A stable `ManagedFirmsConnector` is registered at startup even without a key.
Unconfigured polls are idle rather than circuit-breaker failures. Each new poll
resolves the effective credential, allowing confirmed database keys to take
effect without restarting the application. Confirmation resumes a tripped
FIRMS circuit; it does not turn on a separately disabled source.

A fetched batch carries an internal generation. Scheduler publication holds the
source admission guard, then the shared database administration lock, rechecks
source activation and the current generation, and retains those guards through
publication. Clearing/replacing a key or disabling collection prevents an old
successful batch from publishing. Failure and timeout health updates must use
that same generation boundary, preventing an old request from poisoning a new
connection's health or backoff.

`ASE_FIRMS_MAP_KEY` takes precedence over database credentials. The editor reports
an environment-managed connection and refuses database mutation while that
setting is present; it never copies or silently overwrites the environment key.
`ASE_FEEDS_DISABLED` remains an operator veto. `ASE_FIRMS_AREA` remains an operator
setting and is included in candidate validity; this slice does not add an area
editor. No actual operator settings, keys or database have been read during
implementation.

## Files and migration

- `domain/firms_credentials.py`: bounded singleton state and draft validity.
- `application/admin/firms_credentials.py`: masked draft/test/confirm lifecycle.
- `application/ports/firms_credentials.py`: persistence and probe boundaries.
- `adapters/persistence/firms_credentials.py`: encrypted database fields.
- `adapters/feeds/firms_runtime.py`: fixed-source probe and runtime resolver.
- `application/ports/feed_release.py`: optional guarded feed publication contract.
- `application/feeds/scheduler.py`: success and failure release checks.
- `api/schemas_firms_credentials.py`, `api/routers/admin_firms_credentials.py`:
  bounded commands under `/api/admin/sources/firms_viirs_noaa20/connection`.
- `container/admin.py`, `container/__init__.py`: wiring and stable registration.
- Migration `0032_firms_credentials` follows inventory migration 0031. It refuses
  downgrade while retained connection state exists. Migration 0031 is integrated
  into the base and both database migration paths have passed acceptance.

## Acceptance and remaining work

Acceptance on the isolated implementation checkout:

- Final full backend acceptance on the inventory-integrated base passed 3,328
  tests, with 84 skips and 95.05% coverage in 6,522.28 seconds. The original
  process exited successfully; source and tests remained frozen throughout.
- Final frontend acceptance passed 1,042 tests in 201 files with no skips:
  95.15% statements, 90.31% branches, 93.56% functions and 96.49% lines.
  Type checking, lint, production build and repository hooks passed.

- 38 focused workflow/runtime/source-control cases passed, followed by 23
  runtime/source-control cases after the final cleanup/expiry review repair.
- 62 existing FIRMS transport, HTTP-boundary and scheduler regressions passed.
- 10 independent PostgreSQL concurrency cases passed with distinct connections
  and observed database lock waits, including competing mutations, publication
  versus configuration changes, test generations and actual logout.
- Eight real migration cases passed across SQLite and PostgreSQL 17.10. They
  preserve existing reports/acknowledged alerts, verify schema parity, exercise
  clean roundtrips and refuse retained active/draft/cleared-history loss.
- Direct test-deadline and rate-limit regressions passed. Tests use synthetic
  data; test observations never enter the live store.
- Production mypy, Ruff/format, both import contracts and configured Bandit
  passed, including final checks after integration of the accepted inventory base.

Acceptance logs are kept in ignored `data/` paths: `firms-runtime-final-focused.log`,
`firms-release-final.log`, `firms-transport-regression.log`,
`firms-credentials-concurrency-postgres.log` and `firms-migration-final.log`.
Disposable PostgreSQL databases, containers and their owned volumes were removed
and absence verified. No operator database, actual credential or deployment was
used. Session checks are repeated around awaited work; the implementation does
not claim that an entire network response is atomic with concurrent logout.

Real NASA compatibility, live coverage and key onboarding remain separate
operator acceptance. No NASA request, account registration or deployment is
performed by these synthetic tests.
