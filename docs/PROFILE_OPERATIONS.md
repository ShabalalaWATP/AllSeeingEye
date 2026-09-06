# Personal profile and security

Every active user, manager and administrator has personal settings at `/account`.
The four sections are Profile, Security, Research defaults and Reports. These
settings are private to the current account. Administration and model credentials
remain in the separate administrator workspace.

## Profile and defaults

Users can change their display name, IANA timezone and date format. Email and role
are read-only. This release does not implement verified email changes, avatar
uploads, passkeys or notification preferences. Report creation timestamps and
session renewal times use the selected display timezone; evidence chronology keeps
its recorded UTC context.

Research defaults cover quick/detailed collection, one to eight source languages,
a 1/3/7/14-day window and an optional country. Explicit URL scope and frozen
follow-up settings take precedence. Forms wait for preferences before editing and
do not overwrite in-progress input when preferences refresh. Report preferences
set narrative language, concise briefing/detailed assessment and the preferred
PDF, DOCX or Markdown download. All export formats remain available.

Language and style are presentation instructions, not changes to the evidence
matrix, citations, confidence rules or administrator-selected model. Mechanically
checked judgement statements remain in English. The current PDF renderer cannot
display Arabic or Chinese scripts correctly; affected screens recommend DOCX or
Markdown. Actual language quality still requires evaluation with the configured
model.

## Devices and recovery

Security shows enrolled MFA methods, recovery-code availability, password controls
and active session families. Device text comes from the browser user-agent and is
not verified hardware identity. Times show the latest sign-in or token renewal,
not page activity. The list shows up to 100 sessions, prioritising the current one.
Signing out other devices covers every other live family, including omitted rows.
Signing out the current family returns this browser to sign-in. Individual and
all-other revocations require an explicit confirmation in the page.

Recovery codes require an enrolled MFA method and fresh password plus authenticator
or email verification. Ten single-use codes are shown once, with an explicit local
text download. Store them privately, separately from the device. Replacement
invalidates the preceding set. Password changes/resets, factor changes and other
security-version changes invalidate the set. Codes supplement password-first MFA
sign-in and do not count as an enrolled factor for the administrator requirement.

Only hashes are persisted. Codes are consumed atomically and bound to the account
and its security version. They are never available through an administrator lookup.
Authenticator QR codes are encoded locally; provisioning secrets are not sent to
an external image service. API responses containing enrolment/recovery material
are not cached, and the interface clears private state on account changes.

## Upgrade and verification limits

Back up the intended database, then use the existing migration workflow to apply
`0020` (private preferences) and `0021` (recovery-code hashes), after `0019` (MFA).
Existing users receive defaults without a required profile backfill. Downgrading
`0021` refuses persisted recovery codes; do not discard them silently. Downgrading
`0020` removes saved personal preferences. Neither migration was applied to the
operator's database during development.

Synthetic API, application, persistence and browser checks exercise the features.
Real SMTP delivery, an operator database upgrade and configured-model output
quality remain separate deployment checks. See [MFA operations](MFA_OPERATIONS.md)
and [authentication API](api/AUTH_API.md).
