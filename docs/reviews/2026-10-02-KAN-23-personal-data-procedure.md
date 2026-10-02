# KAN-23 personal-data procedure reconciliation, 2 October 2026

[KAN-23](https://alex-orr.atlassian.net/browse/KAN-23) permits an operator-assisted
procedure and requires concrete follow-up scope for unsupported account-wide
operations. It does not require a complete self-service erasure product. This
documentation change corrects that acceptance boundary and adds the notification
data introduced by released PR #96, including the independent operator-controlled
installation webhook copy and the final pre-send boundary. The proposed contact,
handling route and shared-team policy remain pending the operator's actual choice.

## Evidence actually obtained

The private rehearsal used immutable main
`13e9525d904e744e0bc7ea329e8d475234f86f25`, an exact-lock dependency image and
synthetic fixtures. **Eleven cases passed, no skips**, in 16.98 seconds. This is
correctness evidence, not a performance or coverage measurement.

| Scenario | Observed result |
| --- | --- |
| Mixed personal, shared-authored, other-user and hidden-team reports | All pages read; only three versions from two personal records selected. Returned filenames and distinct seeded-version hashes matched; excluded record titles were absent |
| Selected personal report deletion and account deactivation | Five reports/six versions became four/four. Shared and other-user records, the retained personal record and account remained; an authorised team member retained access and the old requester token failed |
| Selected standing work and other-owner positive control | Three schedule rows retained: one paused, one archived, one other-owner enabled. Only the other owner queued a job; no model worker ran or report was generated |
| Existing selected authority/archive regressions | Last-manager replacement/archive, departed-member dispatch refusal, edition-history retention, pending/running cancellation, scoped archive and session-expiry rollback passed |

The two additional scenario tests were held outside the repository, alongside
the immutable source archive. Existing selected tests were
`test_personal_data_procedure.py`, two cases from `test_team_authority.py` and
four cases from `test_schedule_archive.py`, including their parameterised paths.
The additional scenarios extend the evidence, not the application's supported
account-wide operations.

The isolated Linux runner used network mode `none`, no published ports or daemon
socket, no host credentials, read-only source/root mounts, a private temporary
filesystem and per-test SQLite. Runtime compared the installed source lock with
the mounted source lock before pytest. The owned container was removed after
immutable-ID and unique-label verification; the final census was empty, with no
uncertain Docker commands or cleanup errors. No production data or service was
used and no external message was sent.

Independent review caught insufficient proof of the returned export version
and interrupted Docker-creation cleanup in the private rehearsal tooling. Both
were repaired and re-reviewed before execution. The reviewer did not execute
the tests. An earlier stale cached image failed its dependency guard before
pytest; a historical pre-PR96 image was built but not tested. The successful
result above is for the final released revision and its exact lock.

Independent privacy-claims and documentation-quality reviews of this two-file
draft closed an omission about the separate installation webhook copy. Both
rechecks found no remaining actionable issue. All ten local Markdown targets
resolve; whitespace and changed-document length checks passed.

## Retained evidence references

The local private evidence directory is identified by
`codex-kan23-rehearsal-61a7a7b697dc4afe8d44cb44c46f1b36` under the operator's
temporary directory. These are private local references, not repository files
or publicly available artefacts:

- `acceptance.md`, `result-main13.json`, `pytest-main13.stdout.log` and
  `pytest-main13.stderr.log`: execution, before/after assertions and cleanup.
- `hashes-main13.json`: archive, source lock, Dockerfile, scenario tests, launchers
  and result-file hashes.
- `rehearsal/test_operator_rehearsal.py`, `run-rehearsal.sh`, `run_rehearsal.py`:
  exact scenarios, selection and bounded owner-scoped launcher.
- `main13/image-build.log` and `main13/image-context/Dockerfile`: dependency build.

Source lock SHA-256:
`652e2aee4f771e0fe8827a98156cc466264cba195faacb6f80f045bd9e8d189f`.
Runner image ID:
`sha256:d5a8f723c23ce400d6afc1f3674d651913277c674b0579a9f1764d12b07cc66e`.

## Limits and acceptance still open

The eleven cases do not seed notification preferences, Atom tokens, push devices
or delivery outboxes. The new inventory is based on their released source and
channel documentation; it does not claim notification erasure, relay acceptance,
inbox delivery or browser-vendor delivery. Complete account export/erasure,
real requester verification, private file transfer, backup erasure and external
copy recall remain outside this evidence.

The operator must still choose the handling route, private recipient/account
verification responsibility and shared-team stance. This PR remains draft for
that decision. No Jira transition, production operation, retention policy or
separate implementation ticket is created by the documentation change.
