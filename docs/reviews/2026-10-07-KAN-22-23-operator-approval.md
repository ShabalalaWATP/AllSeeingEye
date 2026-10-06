# KAN-22 / KAN-23: approved contact and personal-data procedure

## Operator decision

On 7 October 2026 (Europe/London), Alex confirmed `alexorr@yahoo.co.uk` and
approved the proposed private contact, one labelled synthetic security-reporting
email and the administrator-assisted personal-data procedure. Shared team work
remains preserved; identity, exact account and selected supported actions must
be agreed before handling a request.

`SECURITY.md` now gives that email as a channel available without repository or
GitHub access, alongside GitHub private vulnerability reporting. The response
expectation remains best effort, normally within one week, without an SLA.

The [personal-data procedure](../PERSONAL_DATA_OPERATIONS.md) records the approved
route and its limits. An active replacement team manager or completed team
archive is required before deactivating a sole active manager. Deactivation is
not erasure, and this decision introduces no legal retention period or complete
account-wide export/removal implementation.

## Evidence and review

The four proposed KAN-23 documents were unchanged between proposal base
`218ce580` and current main `33990205`. The retained eleven-case rehearsal at
`13e9525d` remains historical evidence, with the same relevant report, team,
administration and schedule sources and tests at current main. No production
deletion or new rehearsal is claimed. See the
[original review and later decision](2026-10-02-KAN-23-personal-data-procedure.md).

Independent quality and security reviews found no actionable issue in the five
contact/procedure files. Local Markdown targets resolve, `git diff --check`
passes and the repository file-length check passes with existing warnings.
No application source, dependency, migration or permission setting changed.

## Private reporting test

One authorised synthetic email was submitted through the deployed, TLS-verified
SMTP adapter at `33990205` on 6 October, 23:32:13–23:32:15 UTC (7 October BST).
The result was `sent`, meaning the configured SMTP server accepted it. No retry,
application worker, account change or SMTP configuration change occurred.

The private result receipt has SHA-256
`fb097bd14b242f7caf55bd78d8a93f9edfa27a403c95d7860a496d66326877c0`.
SMTP acceptance alone does not prove receipt in the owner's mailbox. Mailbox
verification remains outstanding at this checkpoint, so KAN-22 remains open.
