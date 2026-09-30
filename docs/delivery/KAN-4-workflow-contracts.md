# Workflow, contracts and guidance delivery

Jira: KAN-2, KAN-4, KAN-22, KAN-23, KAN-143 and KAN-144.
[PR #88](https://github.com/ShabalalaWATP/AllSeeingEye/pull/88), branch
codex/KAN-4-backlog-delivery, base69696286. Primary checkout edits preserved.

## Behaviour and scope

- KAN-2: shared Jira/parallel instructions and PR template committed. CLAUDE
  directs agents to them. Jira's Development field reports a GitHub draft PR
  for KAN-2, read from integration metadata after PR88 creation.
- KAN-4: reconciled three merged alert/tracker tickets to Done using PR81's
  merge and successful final checks. Corrected stale plan statements about
  merged maintenance and delivered teams/research. The full owned queue has an
  explicit batch register. Remaining batch acceptance is still in progress.
- KAN-22: enabled GitHub private vulnerability reporting and read back enabled.
  SECURITY.md names the public repository's private report form and a best-effort
  response expectation. No test report was sent; owner notification delivery
  remains unverified.
- KAN-23: proposed operator-assisted inventory/procedure, with account-wide
  export/erasure gaps stated. Operator policy selection remains pending.
  A disposable record-level rehearsal verifies supported actions only.
- KAN-143: approval/update roles advertise and accept only user/admin while
  legacy manager remains readable in outputs. Defaults/null updates preserved.
  Team/auth guides now describe membership authority and consent. KAN155's
  sender-list privacy gap remains explicit pending its separate fix.
- KAN-144: maintained translation/social/search guidance replaces contradictory
  phase material. MFA/recovery, Telegram, PDF and model deadlines have named
  current guides. No provider/model/browser acceptance is claimed.

## Verification actually run

- Regression before KAN143 fix: two schema failures and two passing cases,
  confirming advertised input enum included rejected manager.
- Focused role/team/admin suite: 38 passed. Includes invitations, authority,
  reactivation and administrator mutation behaviour.
- Personal-data rehearsal: one passed with disposable SQLite. Three reports
  and versions before, two after own report deletion; another account's report
  could not be exported/deleted; team work survived deactivation and remained
  readable to an authorised member; the old user token was rejected and the
  account row remained, demonstrating deactivation is not erasure.
- Ruff check/format passed for changed Python after formatting repair.
- Mypy: no issues in 1,370 source files. Import-linter: three contracts kept.
- Generated OpenAPI and TypeScript from source; frontend typecheck passed.
- Bandit on the changed runtime schema passed.
- Local Markdown link validation: 226 local targets checked, zero missing.
- Repository file-length check passed, with existing warnings on unchanged
  files. git diff --check passed.
- Independent architecture worker review found no actionable correctness or
  security issue in KAN143's schema, tests, generated unions and authority docs.
  This was static review; it did not repeat the parent's tests.
- Full CI on the latest code commit remains required. No new full-suite coverage
  percentage was measured for this small schema/documentation batch.
- Gitleaks was not available on PATH locally; the required CI secret gate remains.

No database migration, production deploy, real email or credential rotation was
performed. GitHub's reversible reporting setting was the only repository
configuration change. Root policy and remaining live acceptance prevent a
blanket Done claim for the whole batch.
