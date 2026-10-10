# KAN-167: enquiry retention affected-row counts

Checked on 10 October 2026 against `1763c790642529fd1e380f0387a892bcf5073853`
in the isolated KAN-169 worktree. This repair concerns the shared enquiry
repository and can be applied independently of the KAN-169 administration UI.

## CI diagnosis

[PR 189's Semgrep job](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38008132990/job/114081601489)
completed its scan successfully at 00:21:20 UTC, running 456 rules over 3,915
targets. It failed because of one blocking finding, rather than a scanner or
network failure. The uploaded `semgrep-sarif` artefact identifies the sole
unsuppressed result as
`python.sqlalchemy.performance.performance-improvements.len-all-count` at
`backend/src/ase/adapters/persistence/admin_enquiries.py:79`:
`return len(removed.all())`.

The original operation was a bounded `DELETE ... RETURNING id`, followed by
materialisation of the returned identifiers to count them. The finding is a
performance pattern, not evidence of an unbounded query or a security exploit.

## Change and invariants

The repository now executes the same bounded deletion without `RETURNING` and
reads `CursorResult.rowcount`. SQLAlchemy documents this count for a single
`UPDATE` or `DELETE` execution and notes that statements using `RETURNING` may
not provide it. See the
[SQLAlchemy rowcount reference](https://docs.sqlalchemy.org/en/21/core/connections.html#sqlalchemy.engine.CursorResult.rowcount).

- The `created_at < cutoff` predicate, oldest-first ordering and batch limit
  are unchanged. The housekeeping batch remains 100 rows.
- Deletion remains one SQL statement. There is no separate pre-deletion count
  that could race with another transaction.
- `synchronize_session=False` avoids ORM identifier fetching. The caller owns
  the short housekeeping transaction, following the existing usage-pruning
  pattern in this repository.
- The repository does not commit or roll back the caller's transaction.
- No Semgrep rule, suppression or workflow setting was changed.

## Validation

A private environment was installed with `uv sync --frozen --offline --python 3.13`.
Shared database-test environment variables were removed before testing, including
`ASE_ROTATION_TEST_URL`.

The existing behaviour tests were run with:

```text
python -m pytest tests/test_enquiry_retention.py tests/test_admin_enquiries.py tests/test_enquiry_transactions.py --no-cov -q --tb=short --show-capture=no
```

| Database | Result | Scope |
| --- | --- | --- |
| Private in-memory SQLite | 17 passed in 13.53 seconds | Batch counts 100/1/0, strict cutoff, rollback, housekeeping, administrator operations and transaction guards |
| Disposable PostgreSQL/PostGIS | 17 passed in 38.36 seconds | The same test selection and assertions using asyncpg |

The PostgreSQL run used the cached CI-pinned image
`postgis/postgis:16-3.5-alpine@sha256:47e961a569fd52ff31f0fe205ed91eeab17d9f5fff6722e6d7ea6b588748b293`.
Only the new `codex-kan169-retention-20261010` container was used, with a random
test password, synthetic database, automatically allocated loopback port and
temporary in-memory data mount. That exact container was removed after testing.
Existing application containers and databases were not used.

Focused Ruff, formatting, mypy and configured Bandit checks passed. The root
reviewer independently reviewed the production diff and found no actionable
issue with its cutoff, bounds, transaction ownership or row-count semantics.
No new tests were needed because the existing tests exercise the changed driver
behaviour on both supported engines. Coverage was not measured for this repair.

The next CI Semgrep scan remains required; no local scanner rerun or suppression
was used to declare the original blocking result cleared.
