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

A frozen, controlled comparison of only the original 26 cases is still pending at
this checkpoint. The latest completed full CI remains 45.8000 PostgreSQL
runner-minutes. KAN-71's maximum of 30 and five comparable before/five comparable
after runs remain unmet. No whole-CI or release acceptance is claimed here.
