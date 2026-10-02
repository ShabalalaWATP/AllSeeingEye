# KAN-71 connector fixture consolidation

## Scope and behaviour

The events, source controls, FIRMS inheritance, replan activation and source-release
tests previously built a second app fixture that dropped and recreated the complete
schema. They now use the existing ordinary app fixture with a fresh fake connector
and `email_sender=None`. This retains normal configured or unavailable email
transport composition. No message is sent by these contract tests.

All original test function bodies, decorators and parameters are unchanged from
`238bace476a4d25a32d445deb2913bb6a2f5e3ce`, verified by AST comparison. The five
eligible modules retain their 26 cases. The modified cache consumer retains its six
cases and its positive independent-database detection, so it remains excluded from
template admission. No eligibility guard, production source, dependency, coverage
floor, selector, authentication parameter or transaction boundary changed.

## Evidence and limitations

The preceding covered diagnostic ran 178 exact existing CI-selected cases, with
zero failures or skips. Its 26 connector cases recorded 26 native schema creates
and 26 drops. These instrumented boundaries are cumulative elapsed observations
across concurrent workers, not predicted runner-minute savings. The 98 independent
storage cases in that diagnostic used SQLite and do not justify broader native
template eligibility.

That diagnostic's original launcher exit 1 and `completed:false` remain retained:
the post-run catalogue query returned `template_postgis`, which it had not excluded.
The catalogue alone does not prove that database's provenance. No owned `ase_*`
database remained, and acknowledged container removal, exact-name absence and an
empty unique-label census were recorded. Independent code and security evidence
audits accepted the completed case and coverage attribution, without rewriting the
failed launcher or running it again for a favourable result.

The new correctness launcher records the complete initial catalogue and requires
exact final equality. Completion is recorded only after successful checks and
verified cleanup.

## Validation checkpoint

- All 38 focused cases passed under SQLite and under private PostgreSQL, with zero
  skips or failures and matching case identities. This includes the original 32
  cases plus six new contract cases.
- PostgreSQL recorded 29 clones, zero schema fallback and nine excluded cases.
  Original release/cancellation and session-revocation assertions remain exercised.
- New cases prove fresh connector/spec/event identity, actual default mailers for
  configured and unconfigured settings, authenticated activation, committed and
  rolled-back rows across sequential sessions, cancelled-write rollback and actual
  engine disposal. They install no SQLAlchemy observers or native-method patches.
- A bounded actual collection regression checks all 32 original IDs, database
  selection and the exact 26-eligible/six-cache-excluded partition.
- The complete collect-only census retains all 2,881 cases from the previous CI
  PostgreSQL selection and all 2,363 historical IDs. Five new database regressions
  bring the selection to 2,886, with 2,500 parallel and 386 serial cases. The sixth
  new case checks collection itself. All eight retained node-ID files are unchanged.
- Both initial and final PostgreSQL catalogues were equal. Fsync, synchronous
  commit and full-page writes remained enabled. Owned container cleanup passed with
  no unresolved operation. The launcher exited 0 after cleanup.
- Ruff, formatting and whitespace checks passed. Independent backend, security and
  coordinator source reviews found no actionable issue before execution.

Raw local records are retained outside Git under the task's
`kan71-73-followup-58c5b2fe/event-fixture-validation` evidence directory. The prior
covered attribution is separately retained in `ineligible-fixture-profile-238bace4`.
The full selection proof is retained in `event-fixture-census`.

## Controlled local comparison

The predeclared control/candidate/candidate/control sequence completed once on
full tracked archives of `238bace4` and `4c0d2102`. Original test-function ASTs,
production bytes, locks and eligibility/isolation guards were identical. Both
arms used the same private Python 3.13.3 dependency installation, four workers,
`--max-worker-restart=0`, real authentication and branch coverage. Equal ordinary-app
warm-ups and two-second cooldowns preceded each measured subprocess. Pytest and
bytecode caches were disabled.

| Arm         | Full pytest subprocess seconds | Original cases | Actual clones |
| ----------- | -----------------------------: | -------------: | ------------: |
| Control 1   |                     58.2849590 |      26 passed |             0 |
| Candidate 1 |                     48.8281401 |      26 passed |            26 |
| Candidate 2 |                     49.2931777 |      26 passed |            26 |
| Control 2   |                     57.0881717 |      26 passed |             0 |

The medians were **57.6865654 and 49.0606589 seconds**, a reduction of
**8.6259065 seconds (14.9531%)** in this local 26-case workload. All 104 measured
case executions and four excluded warm-ups passed with no skips or fallbacks.
No failed observation, replacement worker, retry or discarded arm exists.

All four measured runs retained exactly the same **79,193 normalised `ase` branch
arcs across 1,578 files**. This is partial-suite raw-data parity, not a global
coverage percentage or aggregate coverage-gate claim. Every worker's loaded
application/test file and import-spec origin was checked against its frozen root.
Literal controls pins bound both ZIPs, the manifest and complete extracted file
inventories before and after each arm and at final completion.

Each arm used a fresh owned PostGIS service with two CPUs, 2 GiB RAM and 2 GiB
tmpfs, with all durability flags on. Complete catalogues matched before warm-up,
after warm-up and after measurement. Acknowledged creation/removal, exact-name
absence and empty unique-label census proved cleanup without unresolved operations.
The launcher exited 0 after all four cleanups and final evidence checks. Eleven
offline protocol cases and ten ownership cases passed before execution.

Independent security evidence review recomputed timings and reconciled every
case, phase, import witness, raw coverage database, source/dependency seal and
cleanup record. Records remain in `event-comparison-frozen` and
`event-comparison-results`, outside Git. Publication changes after `4c0d2102` are
documentation only and must preserve its measured source bytes.

The latest completed full CI remains **45.8000 PostgreSQL runner-minutes**.
KAN-71's maximum of 30 and five comparable before/five comparable after runs remain
unmet. These local gains are not added to other diagnostics or extrapolated to
whole-CI cost. Fresh full CI and release approval remain required.
