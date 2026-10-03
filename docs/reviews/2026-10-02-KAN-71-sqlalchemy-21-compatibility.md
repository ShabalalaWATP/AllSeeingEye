# KAN-71: SQLAlchemy 2.1 compatibility for PR 108

Base: Dependabot PR 108, `32ebda6281712b90cf4859a70d9d9e3843ba67ba`.
Implementation uses an isolated `codex/KAN-71-sqlalchemy-compat` worktree and
the unchanged frozen dependency lock, including SQLAlchemy 2.1.1.

The dependency CI exposed 20 mypy errors in six persistence modules and a
PostgreSQL migration test passing the removed `async_fallback` driver option.
SQLAlchemy 2.1 uses individual result types in `Select`, replacing the former
single tuple type. The push-device and invitation annotations now follow that
contract, and source-track report IDs have their explicit UUID collection type.
No query, scope predicate, ordering or before-limit filtering changes.

Three nullable database result types now have explicit rejection branches:
an active original without stored bytes, a missing coalesced receipt total and
a missing failure reason despite its SQL filter. Valid results behave as before;
invalid results cannot become empty asset bytes or understated token usage.
These guards add no casts, type ignores or authentication exceptions.

The migration test now performs its existing synchronous reflection and data
assertions through `AsyncConnection.run_sync`, with a fresh async engine disposed
after each operation. Alembic still runs outside those event loops. It retains
the populated 0034-to-0035 upgrade, original job payload/digest/length checks,
unknown legacy coverage, refusal to downgrade retained editions, and subsequent
permitted downgrade. The SQLite seed wrapper remains available to the research
brief migration test. No migration source or driver dependency changes.

## Validation

- Three new null-result regressions failed on the unchanged production code,
  then passed after the explicit guards.
- Focused 13-file suite: **64 passed, 2 skipped**, 40.03 seconds. The two skips
  require explicit PostgreSQL URLs: the migration and web-push concurrency tests.
- The previously failing PostgreSQL migration case then passed on a fresh private
  PostGIS 16 database: **1 passed**, 2.47 seconds. Its pinned image was
  `postgis/postgis:16-3.4-alpine@sha256:681931a625df344215e9b8998bf34daf146b6a395ceacee4439eb9c85869239f`.
  `fsync`, `synchronous_commit` and `full_page_writes` were all `on`.
  The complete initial/final database catalogues matched, including
  `template_postgis`. The acknowledged container was removed, exact absence and
  an empty unique-owner census verified, with no unresolved operation.
- Full mypy: **1,578 source files passed**. Changed-file Ruff and formatting,
  all three import contracts, scoped Bandit and whitespace checks passed.
- Independent read-only quality/lifecycle and defensive reviews found no
  actionable issues. Both checked the preserved SQL scope and migration
  assertions; reviewer inspection is separate from the executed checks above.
- No coverage measurement or full-suite result is claimed here. Fresh PR CI
  must validate the integrated dependency update before merge.

This is dependency compatibility evidence, not a KAN-71 timing result. Runtime
passwords, private test URLs and local result artefacts are excluded from Git.

## Main integration, 3 October 2026

A normal merge incorporates main `45381b2c18ddf3e80674528caee2e14fd492f500`,
including the reviewed dependency updates in PRs 119 and 120. The sole conflict
was adjacent SQLAlchemy and SSE requirements in `uv.lock`. The resolution keeps
SQLAlchemy 2.1.1 and main's SSE 3.5.0, Ruff 0.16.9 and fonttools 4.66.0.
All 120 package identities remain. Against main, only the SQLAlchemy package
record and application requirement metadata differ; the other 118 package
records match exactly. The six production compatibility fixes and two test files
remain unchanged from `063136ec`.

`uv lock --check --offline` and `uv sync --frozen` passed. The expanded focused
14-file suite passed **71 tests, with 2 PostgreSQL-only skips**, in 66.06 seconds.
The explicit native subscription migration test then passed separately:
**1 passed in 3.25 seconds**, on the same pinned PostGIS 16 image and a fresh
private UUID database. All three durability settings remained enabled, the
complete database catalogue matched before and after, and acknowledged container
removal, exact absence and an empty owner census were verified.

Changed-file Ruff and formatting, full mypy over **1,578 source files**, all
three import contracts and scoped Bandit passed. An independent read-only
integration review confirmed the dependency union and unchanged compatibility
behaviour. No benchmark, full-suite or coverage result is claimed. Fresh CI must
validate the resulting PR head before merge.

## Subsequent dependency integration, 3 October 2026

A second normal merge incorporates main
`e22c599a3e8db8fdbc1ea44747040dcc3cdfdd7e`, after PRs 109, 104 and 117.
The sole conflict was adjacent requirements in `pyproject.toml`; the resolution
retains Uvicorn 0.54.0 and SQLAlchemy 2.1.1. The lockfile merged cleanly. All 120
package identities remain, and the other 118 package records match this main
revision exactly. The six production compatibility modules and two test files
remain byte-for-byte unchanged from `063136ec`; frontend files match main.

The offline lock check and frozen dependency sync passed. The focused suite,
now including SSE shutdown and session-pool regressions, passed **75 tests with
2 PostgreSQL-only skips**, in 71.87 seconds. The native subscription migration
passed separately: **1 passed in 3.59 seconds**. Its fresh private database used
the same pinned PostGIS image, all three durability settings enabled, complete
initial/final catalogue equality and acknowledged resource removal with exact
absence and an empty owner census.

Full mypy over **1,578 source files**, changed-file Ruff and formatting, all three
import contracts and scoped Bandit passed. Independent read-only review confirmed
the dependency union, unchanged compatibility paths and exact incoming frontend.
These are correctness checks, not a
performance measurement or full-suite result. Fresh combined-head CI and the
preceding main CI remain release gates owned by the coordinator.
