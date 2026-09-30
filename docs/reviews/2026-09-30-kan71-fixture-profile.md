# KAN-71 fixture profiling and template screening

These private local experiments identify a candidate for investigation. They do
not establish Linux CI performance or satisfy the 30-minute runner-cost target.
The last published CI checkpoint, `01838710`, used 45.80 aggregate PostgreSQL
runner-minutes including its merger, with all 2,367 selected cases passing.

## Existing fixture profile

The experiment used `c4751ad2`, whose selected tests, schema helpers and production
Argon2 adapter match `01838710`. Twelve existing selected cases passed against a
private pinned PostGIS 16.4 service with a 2 GiB tmpfs. Database durability flags
remained enabled. Pytest took 23.21 seconds; measured test phases totalled 22.423
seconds wall time and 12.391 seconds Python process CPU. Server CPU is excluded.

| Operation | Calls | Wall seconds | Python process CPU seconds |
| --- | ---: | ---: | ---: |
| Fixed user/admin seed hashes | 15 | 0.573 | 1.844 |
| Production random dummy hashes | 12 | 0.476 | 1.453 |
| Password verification | 18 | 0.695 | 2.156 |
| Changed-password hash | 1 | 0.038 | 0.109 |
| Schema creation/reset | 12 | 8.791 | 1.406 |
| Schema teardown | 12 | 6.039 | 0.672 |

Fixed fixture seed hashing accounts for 2.56% of phase wall time, whereas schema
creation and teardown account for 66.14%. No password cache or cheaper hashing
parameters were introduced. Windows-to-Docker roundtrip costs may inflate the
schema share; this selected serial sample cannot predict concurrent CI savings.
Instrumentation recorded categories, counts and timing, never password/digest
values. All production hash and verification operations executed unchanged.

## Scratch template clone screening

The baseline constructed the real app and used the existing SQLAlchemy schema
reset. The candidate created a new owned database from a disconnected worker
template before app construction. Both paths used fresh engines, checked
readiness and included teardown. Template construction cost 0.790895 seconds once,
excluded from per-case times. One warm-up pair was excluded and three measured
pairs alternated order.

Median cycles were 1.353883 seconds for the existing reset and 0.223028 seconds
for cloning, an 83.53% local reduction. This three-pair screening has no coverage
instrumentation and is not a controlled full-suite CI acceptance measurement.

All 79 application tables matched through Alembic and normalised PostgreSQL
catalogues: 779 columns, 313 constraints, 229 indexes, 13 sequences and one
extension. Actual defaults, foreign-key/check rejection, committed/uncommitted
visibility, rollback and independent rows passed for the baseline and two
clones. One sequence was exercised at runtime; all sequence definitions and
initial states matched. Added DDL hooks, tables and altered columns rejected
clone eligibility and exercised the unchanged SQLAlchemy fallback.

## Integration boundary

Generic `create_schema` and `drop_schema` must retain unmanaged-table and DDL-hook
semantics. A separate explicit ordinary-default-app option may use templates only
within the existing isolated local PostgreSQL owner. Custom settings/apps,
direct-engine fixtures, migrations, races and SQLite keep their existing paths.

A prerequisite must bind one per-test URL before settings construction and every
consumer. Eligibility must be rechecked during app setup and teardown, including
metadata changes and SQLAlchemy instrumentation. Unsupported behaviour requires
fallback. Fresh engines preserve asyncpg caches and real transactions; engines
must close before exact owned database removal. Template databases contain schema
only, with no seeded users. PostgreSQL does not copy database-level grants or
settings during template creation. [PostgreSQL CREATE DATABASE documentation](https://www.postgresql.org/docs/16/sql-createdatabase.html).

Both scratch services and their owned databases/volumes were removed. No FORCE
drop or global connection termination was used. Raw JSON, logs and probe scripts
remain outside Git under the task worktree's `kan71-timing` directory. A guarded
fixture implementation and independent review are in progress; no CI template
option has been enabled or timing acceptance claimed at this checkpoint.
