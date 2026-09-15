# Research and Subscriptions implementation: security check

Date: 14 September 2026. Scope: the uncommitted Research and Subscriptions implementation against the local working tree. This is a bounded review, not a claim that the full product has passed an independent security assessment.

## Checks observed

- `pnpm audit --audit-level high` passed after the transitive `js-yaml` override selected 4.3.2. The lockfile was refreshed. This only covers published frontend dependency advisories known to the audit source.
- `uv run pip-audit` found no published backend dependency advisory. It skipped the unpublished local `ase` package.
- `uv run bandit -r src -q -c pyproject.toml` passed after four findings were reviewed and narrowly annotated. The XML imports in the ECB and camera adapters provide type and exception names; actual untrusted XML parsing uses `defusedxml`. The Chromium `/tmp` path is a private tmpfs in a newly created mount namespace. The worker's `os.execve` launches an adapter-generated command from bounded private IPC without a shell. These annotations do not waive runtime or architecture review.
- Ruff, strict mypy across 1,140 source files, import-layer checks and formatter passed after the forecast-ledger and reviewed-source projection integration.

The X03 ledger review found two low-severity release and integrity gaps. The routes now perform a final synchronous original-token expiry check after the last awaited service operation. The persistence reader now binds decoded forecast claim/version/report identifiers and indicator source citation to the ledger head. Both regressions failed before the fixes; the later ledger run passed 84 tests, and a nine-file report/doctrine/ledger integration run passed 58. A writer with direct database access could still alter both payload and hash, so database access control, backups and operational audit remain necessary.

## Boundaries that require release evidence

The new source-review and ledger APIs must recheck current report/version ownership, team membership and action rights, including correction and historical reads. Frozen report versions must not change when later review history changes. Selected original-page retrieval stays disabled until an explicit reviewed source policy is configured; source URLs and private terms must not be sent to arbitrary endpoints. Deep/Advanced challenge calls require lease-fenced usage accounting and a review gate on unsupported claims.

Pending gates include the full test suites, populated PostgreSQL migration and concurrency exercises, a current-model run, authorised browser journeys, export rendering, and a code review of the final combined diff. No operator database migration, production deployment or live paid model call was part of this check.
