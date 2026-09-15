# V01 offline verification, 14 September 2026

The saved result is [2026-09-14-contracts.json](baselines/2026-09-14-contracts.json).
It records 60/60 passing synthetic cases and 194/194 passing contract checks against
manifest SHA-256 `b198d962358da225395db2c86d02610750bac12a47d9fa38a81e0dd23d9b54d5`.
All 60 packets and their expected source passages pass manifest/version validation.
These are assistant-authored expectations, with human review pending.

Final focused verification:

- `test_evaluation_v01_contracts.py` and `test_evaluation_v01_integrity.py`: 98 passed.
- Coverage over the six new V01 Python modules: 98.54%, including branch coverage.
  The existing 90% gate was retained. The coverage data file was isolated in the
  local temporary directory, outside the shared repository coverage output.
- Ruff lint and formatting: passed for the new modules and dedicated tests.
- Strict mypy with `MYPYPATH=src`: passed for the eight Python source/test files.
- Bandit over `evaluations/v01`, using the repository configuration: passed.
- No application production module, shared router or shared documentation changed.
  No dependency added, model/provider call made, operator configuration read,
  database migration performed, commit created or push attempted.

All pytest commands used process-local in-memory SQLite overrides and cleared
token-race/PostgreSQL test URL overrides before invocation. Contract tests also
deny socket and HTTP requests. Input checks cover bounded local paths and sizes,
version/reference mismatches, duplicate identities, false human/captured-evidence
labels, partial dates and inconsistent shared editions. This is scoped security
reasoning and static checking, not a repository-wide security audit.

An earlier compatibility run including the three existing evaluation test modules
reported 132 passes and one failure. The existing
`test_detailed_replay_runs_collection_redraft_and_all_judgement_review` expected two
initial provider calls, whereas current production planning produced three before
the challenge calls. This was reported to the composition/planning owner; the new
V01 harness does not modify that replay or its production path. That broader run
is not recorded as passing.

The corpus also found a mixed-evidence classification regression: an edition with
both novel and syndicated evidence incorrectly reported `syndicated_duplicates_only`.
The owner of the production change classifier restored the conditional reason and
added a focused regression. V01 retained the original honest expected outcome.

Unverified gates remain human-reviewed semantic support and accuracy, real curated
retrieval recall, model-generated required-question coverage, counterevidence
retention, analytical abstention and material-change quality. Current provider/model
acceptance and full privacy, authorisation, budget and publication integration gates
remain separate. A visible synthetic held-out split is not independent human review.
