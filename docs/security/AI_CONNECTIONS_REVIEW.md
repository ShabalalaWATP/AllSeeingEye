# AI connection controls: focused implementation review

Date: 6 September 2026.

This is a scoped manual source review with synthetic regression tests of the
administrator connection change. It is not a new full-repository Codex Security
scan or proof of production readiness. No operator keys or databases were used.

## Boundaries examined

- Administrator authority and original session validity for profile changes,
  model discovery, tests, activation and team reset, including revocation during
  outbound work.
- Encrypted keys, password input, safe returned errors, inherited HTTP client
  credentials, endpoint changes and redirect handling.
- Test proof tied to a saved profile revision and configuration, overlapping
  probes, cancellation and stale activation confirmations.
- Global/team routing, immutable active profiles, in-flight configuration
  capture and separation of shared translation and embedding configuration.

## Findings fixed

1. Deleting and recreating a team assignment could reuse its old revision. A
   durable monotonic assignment counter now prevents an old apply or reset
   confirmation from matching the replacement. The reset/recreate sequence was
   reproduced and both stale actions were verified to reject.
2. Legacy first-enabled selection allowed an administrator to activate a newly
   created text profile without the test/apply workflow. New and edited text
   profiles now remain disabled drafts regardless of requested enabled status.
   Existing enabled legacy text profiles cannot be edited or deleted before a
   tested global replacement is established. Independent ASGI checks verified
   explicit enabled requests remain inactive and migrated profiles remain
   readable and routable but protected from ordinary changes.

Related implementation regressions cover late test success after newer failure,
strict boolean test output, endpoint-key reuse, inherited client authentication,
post-network session changes and mutation rollback. Existing active assignments
retain their original configuration proof when a retest fails; that failure
prevents a new activation without silently rerouting existing work.

## Practical limits

Administrators intentionally select outbound model destinations, including local
OpenAI-compatible services. Model IDs advertised by a provider are not a guarantee
of text/structured-output compatibility. The connection test makes a small
synthetic request and can consume tokens. It does not establish research quality.

Application encryption still depends on protecting the server encryption key and
deployment configuration. This change does not deploy the app, rotate operator
credentials, migrate the operator database or validate a real provider account.
