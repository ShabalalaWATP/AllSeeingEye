# KAN-71: admit audited migration cases to isolated workers

The serial native lane contains migration tests which already create and remove
their own UUID databases. This change admits only the 21 original cases in the
rekey-history and two notification-migration modules to the parallel lane.
Shared-database, race and unaudited migration cases remain serial.

Admission checks exact test and helper identities, effective fixture definitions
and literal parameters. It rejects unknown fixtures, changed code, query-bearing
or non-loopback URLs and pre-existing migration service bindings. Each admitted
fixture receives its isolated worker service only for its lifetime, then restores
the environment, including cancellation and failures. Its actual migration
database remains a separate fresh UUID database.

The shard runner explicitly registers the admission plugin in both native lanes.
Ordinary SQLite invocation, production code, migrations, dependency locks,
coverage thresholds and the ordinary template eligibility guard are unchanged.

## Verification

- All 2,895 original native-selected IDs remain selected exactly once. The
  partition changes from 2,506 parallel / 389 serial to 2,527 / 368. Exactly 21
  original cases move, and all 2,163 ordinary template-eligible cases remain so.
- 66 admission, collection and lifecycle regressions pass. The 17 runner tests
  and eight original SQLite/graph cases pass; that last focused run deliberately
  deselected seven native variants, covered by the actual native pair below.
- Scoped Ruff lint/format, diff and source-length checks pass. Independent
  code-quality and security reviews are clear on the final frozen source.
- One bounded serial control and one four-worker candidate each pass the same
  original 21 cases, with no skips, retries or replacement workers. Each arm
  records all 63 successful setup/call/teardown phases, 13 real native child
  database lifetimes, seven SQLite cases and one graph case.
- Both arms observe each native child database before the call and its absence
  after teardown. Complete database catalogues, durability settings and synthetic
  service/peer sentinel column and row hashes match before, between and after.
  Source, interpreter, dependencies and runtime identity match their sealed pins.
- The candidate reports zero template clones, zero schema fallbacks and 21
  template-ineligible cases. The ordinary template safety guard is preserved.
- Both owned process jobs exit zero and close all handles without cleanup errors.
  No production database, model, mail service or real personal data is involved.
- The runtime owner independently confirmed final catalogue/sentinel parity and
  no unexpected clients, then gracefully removed only the owned disposable
  container and empty network. The test port is free and generated credentials
  were removed after verification. Original evidence remains retained.

The native pair uses Python 3.13.3, pytest 9.1.1, pytest-asyncio 1.4.0,
pytest-xdist 3.8.0 and PostgreSQL 16.4 from the pinned CI PostGIS image.
Private preparation SHA-256 is
`908846f7b8d6fcf387388e3a3d0d1bcf69359fb15321fe9f5455baa0beabc738`;
complete result SHA-256 is
`34e48ecb9533e5ad7a298db472ad6dea9c8a5ad7b57e6fea5aa468906e230ec9`.
Credentials and installation connection details are excluded from this document.

The candidate emitted ten assertion-rewrite warnings for early-imported native
isolation/template helpers. Those helpers' assertions still execute. Warnings
are retained; no warning-free result is claimed.

## Remaining acceptance

This is correctness evidence for the bounded admission change. It establishes
neither a matched speedup nor the whole-CI limit of 30 PostgreSQL runner-minutes.
The required five-before/five-after CI comparison, full CI on the published head
and final release verification remain outstanding. Coverage was disabled for
this bounded native check; no new coverage percentage is claimed. KAN-71 remains
open until its whole-runner cost and preservation criteria are satisfied.
