# KAN-71 fixture performance follow-up

Base: `58c5b2fe6c10ded7a2d2ae3b79f6fa4d5f434238`. KAN-71's whole-job target of
less than 30 PostgreSQL runner-minutes remains unverified for this follow-up.
The earlier 39.50-minute result did not meet it. The local measurements below
must not be added together or substituted for fresh complete CI measurements.

## Removed repeated setup

Commit `a81dab4f` removed four preflight HTTP fixture OpenAPI rebuilds and the
fallback that registered a missing router inside the test. The production router
must now serve the real authenticated requests. An autouse guard rejects an
already-built schema and fails on schema construction during those HTTP cases;
it failed against the former setup before removal. Brief/preset path assertions
moved into the existing OpenAPI export contract, which also checks preflight.
Access, validation, release fencing, private caching and no-provider-work
assertions remain intact. Thirteen affected SQLite cases passed; the final
preflight/schema assertions separately passed five cases.

Commit `1dbd2114` uses one fresh PostgreSQL dialect per fingerprint invocation.
No schema state is cached across calls. On current 99-table/148-index metadata,
63 mutation/restoration/listener comparisons matched. Twelve alternating
five-call blocks measured median wall time of 20.34805 ms before and 17.17485 ms
after, saving 3.1732 ms per call. Dialect construction fell from 247 to one.
Twenty-six new tests preserve fresh identity and mutable schema/observer checks.

## Exact report-job fixture admission

The original `job_settings` wrapper returns the identical settings object on
PostgreSQL. Its SQLite branch still uses a private file for independent worker
transactions. Template admission now recognises only the original ordered
default-settings/job-settings chain, original app and original temporary-path,
template, isolation and worker prerequisites. It compares raw function identity,
scope, arguments and parameterisation, including indirect callspec parameters.
Dynamic worker definitions are inspected before fixture acquisition. No candidate
function is unwrapped, and duplicate registration cannot replace either trusted
registry. An unrelated pure test without the app/settings closure stays excluded.

Pinned pytest resolves dependencies before the async app's setup hook. The
template/settings prerequisites are synchronous, so direct function identity is
available at the actual decision point. Overrides, wrappers, inserted or reordered
definitions, changed contracts and special postgres/migration/race lanes are
rejected. Existing independent-factory detection, fingerprint/observer fallback,
owned database validation, cancellation bookkeeping and non-forced cleanup remain.
There is no outer rollback transaction or changed PostgreSQL durability setting.

Validation on the final fixture code:

- 127 guard, fingerprint and lifecycle cases passed, including 78 new exact-chain
  cases using collected real `FixtureDef` objects and hostile substitutions.
- 102 cases across all 15 job-importer modules plus ordinary/job clone probes
  passed on a private PostgreSQL service. All 70 previously selected importer
  cases used clones, alongside four clone probes: 74 clones, zero schema
  fallbacks, 28 pure cases ineligible. This includes worker shutdown, lost cancel
  callbacks, stale leases, before/after-commit interruption, admission rollback,
  concurrent quota and overlapping subscription admission.
- An evidence-only plugin verified per-case lease/database release, URL
  restoration and worker task completion. Both committed/uncommitted visibility
  and rollback were checked using independent real sessions. Seven further native
  clone, observer, connection-refusal and cleanup regressions passed. Each process
  left zero owned databases. The owned service was removed.
- Collection selects 2,831 database cases, retaining all previous 2,829 and adding
  only two new job clone regressions. The eight existing untracked census files
  are unchanged. Ruff, formatting, whitespace and file-length checks passed.
- A read-only review found no remaining actionable issue after registration
  exception-safety and wrapped-default bypass regressions were added.

## Bounded mechanism comparison

The predeclared order was disabled/enabled/enabled/disabled, with the same 12
original access/owner/admission cases, two pytest workers, and a private PostgreSQL
service capped at two CPUs and 2 GiB. `fsync`, `synchronous_commit` and
`full_page_writes` stayed on. The image was
`postgis/postgis:16-3.4-alpine@sha256:681931a625df344215e9b8998bf34daf146b6a395ceacee4439eb9c85869239f`.

A private evidence plugin replaced only the new chain predicate with `False` in
the control. Both modes otherwise used identical source, installed dependencies,
case identities, isolation, real commits and cleanup. The pytest cache provider
was disabled; each arm ran the same parameterised guard warm-up and two-second
cooldown. Other local heavy checks were held; the authorised light HTTP audit
continued. This compares the admission mechanism, not complete CI or main.

| Arm        | Wall seconds | Actual clones | Result    |
| ---------- | -----------: | ------------: | --------- |
| Disabled 1 |   27.1881301 |             0 | 12 passed |
| Enabled 1  |   19.8112648 |            12 | 12 passed |
| Enabled 2  |   19.5231812 |            12 | 12 passed |
| Disabled 2 |   27.9230797 |             0 | 12 passed |

Median wall time fell from 27.5556049 to 19.6672230 seconds, saving 7.8883819
seconds (28.63%) for these 12 cases. All arms left zero owned databases. An
initial plugin import-path failure occurred before case collection; its logs are
preserved separately. Only that private harness path was corrected, then the
complete predeclared sequence restarted. No executed measurement was discarded.

Raw evidence is outside Git at
`C:/Users/alexo/.codex/scratch/kan71-73-followup-58c5b2fe/`: `job-guard-tests.log`,
`job-app-real.log`, `job-clone-cases.json`, `job-lifecycle-real.log`,
`job-postgres-results.json`, `job-census-comparison.json`, and `job-screen-*`
manifests, source/dependency/plugin hashes, four logs/JUnit files and result JSON.
The separate [controlled frontend comparison](2026-10-02-KAN-73-controlled-frontend-pair.md)
meets KAN-73's 70-second criterion. Fresh integrated CI, independent immutable
review and comparable whole PostgreSQL job measurements remain required here.
