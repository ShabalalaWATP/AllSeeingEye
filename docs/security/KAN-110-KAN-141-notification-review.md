# KAN-110 and KAN-141 notification boundary review

Scope: subscription email outbox and private Atom feeds. Review performed against
the implementation and synthetic tests, without live delivery or external probes.

- Opt-in defaults: migration 0071 creates empty preference/token tables. No existing
  user acquires a recipient or feed credential. Account opt-in and subscription
  policy are both checked at dispatch.
- Address ownership: active email MFA enrolment is required for notification
  email. Provisioning an account is not treated as ownership confirmation.
- Authorisation: the dispatcher rebuilds `AccessPolicy` under the administration
  guard, refreshes subscription state and releases locks before SMTP. Personal
  recipients must own the subscription. Team recipients need active membership
  and an active team, including administrators. Pending opt-outs cancel delivery.
- SMTP: certificate-verified TLS; no arbitrary user destination; fixed subject;
  plain text and minimal links. Names are separate opt-in. No SMTP exception or
  recipient is logged. A unique intent and conditional claim prevent concurrent
  ownership, but cannot prove exactly-once SMTP delivery. Unknown acceptance is
  terminal pending operator review.
- Feed credentials: cryptographically random existing token generator, SHA-256
  storage, one token per user, issue/revoke use current bearer session and lock.
  Feed Basic authentication is separate from JWT/session authority. Security-version
  mismatch and account deactivation reject reads. No token appears in the feed URL.
- Feed content: SQL scope before limits, no administrator inspection expansion,
  XML escaping with control-character removal, no summaries or report content,
  generic labels by default, fixed bounded entries and per-token/IP limits.
- Residual exposure: mail/feed providers can retain copied content; revocation
  prevents future access but cannot retract copies. Authorisation is checked
  immediately before external work, without holding account locks over the network.
- Runtime: cancellation leaves an explicit uncertain claim; aged claims are never
  automatically retried. A temporary tick failure is logged without exception text
  and the worker continues. Shutdown owns and cancels the worker before closing DB.

PostgreSQL concurrency and real relay/feed-reader acceptance remain unverified in
this environment. No new crypto implementation or third-party package was added.
