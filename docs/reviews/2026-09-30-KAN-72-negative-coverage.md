# KAN-72: real authorisation coverage failure

On 30 September 2026, temporarily deleting one parametrised authorisation test
made the actual backend security coverage checker fail. Restoring the exact test
bytes restored the passing result. Only this evidence document is committed.

## Baseline and isolation

- Tested tree: `dc6cb6e1163e5d2c1b83d9e187ac1257583168fb`, the synthetic merge
  checked out by successful [CI run 36696097087](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36696097087).
- Managed branch: `codex/KAN-72-negative-coverage`, with its own frozen virtual
  environment (`uv sync --frozen`), Python 3.13.3 and coverage.py 7.16.0.
- Focused tests used SQLite. External database environment overrides were removed
  from their subprocesses. Each phase wrote a separate fresh coverage database.
- The eight downloaded `sqlite-coverage-0` through `sqlite-coverage-7` artifacts
  supplied the unchanged modules' baseline. The original shard files remained
  untouched. Real recorded arcs were combined after mapping CI source paths to
  this exact checkout; no coverage counts or arcs were invented.

The reconstructed CI report passed `--policy backend-security` with exit 0.
For each local phase, the complete report entry for
`src/ase/application/reports/authorisation.py` was replaced with that phase's
fresh measurement. All other module entries remained identical to the CI
baseline. Aggregate totals were removed and explicit provenance was added to
each checker input. This proves the gate's negative behaviour with a focused
measurement; it is not a fresh local full-suite coverage run.

## Actual measurements

| Phase | Passing tests | Lines | Branches | Checker exit |
| --- | ---: | ---: | ---: | ---: |
| Before omission | 12 | 48/48 (100%) | 22/22 (100%) | 0 |
| Test omitted | 9 | 46/48 (95.83%) | 20/22 (90.91%) | 1 |
| Exact bytes restored | 12 | 48/48 (100%) | 22/22 (100%) | 0 |

Pytest completed in 13.21s, 13.85s and 9.22s respectively. The failing checker
reported exactly:

```text
FAIL application/reports/authorisation.py: branches 90.91% < 95%
```

The temporary deletion removed lines 63-80 of
`backend/tests/test_report_authorisation_boundaries.py`, including the decorator
and complete `test_regeneration_cannot_overwrite_concurrent_report_change`
function. Its three cases were `deleted`, `new_version` and `unchanged`.
The omitted report showed missing lines 88 and 90 and missing branches 87→88
and 89→90: rejecting a deleted report and rejecting a competing saved version
after generation. The other selected tests did not exercise those rejection
branches. All nine remaining tests still passed.

The selected group was:

```text
tests/test_report_authorisation_boundaries.py
tests/test_direction_plans.py::test_a_report_scoped_by_a_plan_skips_the_direction_call
tests/test_reports.py::test_generate_read_export_and_delete
tests/test_reports.py::test_regeneration_adds_a_version_that_must_state_what_changed
tests/test_report_regeneration_briefs.py::test_ordinary_followup_does_not_claim_the_parent_brief
tests/test_map_research_origin.py::test_final_authorisation_rechecks_deleted_origin
```

From `backend`, each phase used the following command shape with that identical
selection appended (`<phase>` was `before`, `omitted` or `restored`):

```text
.venv/Scripts/python.exe -m pytest -o addopts=--strict-markers --cov=ase.application.reports.authorisation --cov-branch --cov-fail-under=0 --cov-report=json:<evidence>/<phase>.json --cov-context=test --record-nodeids=<evidence>/<phase>-nodeids.txt -q --tb=short <selection>
.venv/Scripts/python.exe ../scripts/check_coverage_floors.py <evidence>/<phase>-gate-input.json --policy backend-security
```

The focused pytest invocation bypassed the unrelated global coverage floor for
that invocation only. The repository configuration and checker were unchanged;
the actual 95% security line and branch thresholds governed the checker exits.

## Restoration and retained evidence

A `finally` block restored the original test bytes immediately after the omitted
phase, before the restored run. SHA-256 checks confirmed the original test,
reviewed module and checker were unchanged. A subsequent check confirmed all
1,393 recorded source-file hashes and all eight downloaded shard hashes still
matched. Before and restored node IDs and module summaries matched exactly.
`git status --short` was empty and `git diff --check` passed before this document
was added. No deliberately broken state was committed or pushed.

SHA-256 values:

```text
authorisation.py: f8213e3c863348c720e13589218829510b9d87ecc95a2b1df34a673fdea1b5c0
test_report_authorisation_boundaries.py: 54565d4597430e72a6e370f6815245e08a1f2cbdbf3bcb0c603bbc99e35db88a
check_coverage_floors.py: 193f0087d0ab3f16b6c254d3764ca23091754d8f8f2b7370c790a53a5550c19b
```

Local raw artifacts, exact command arguments and exits, selected node IDs,
coverage databases and JSON, checker output, omission range, source/shard hash
manifests and the disposable runner are retained outside the checkout at
`C:/Users/alexo/.codex/worktrees/kan72-negative-coverage/evidence`.
`result.json` records the measured summaries and restoration hashes;
`ci-artifacts.json` records the immutable GitHub artifact IDs and archive digests.
These generated files are not committed. The evidence runner's SHA-256 is
`15d8416d07ed49f2f9ac93fd3502420a68194eca594f652fcee1f0af73814344`.
