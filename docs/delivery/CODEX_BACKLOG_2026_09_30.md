# Codex backlog delivery, 30 September 2026

Jira is authoritative for acceptance and status. Alex requested the remaining
Codex backlog in PRs of around eight related tickets. This explicitly expands
the initial ready queue and allows grouped PRs. Smaller feature groups keep
substantial related work reviewable. Ticket count is not an effort estimate.

## Verified baseline

- Fetched `origin/main`: `69696286c45a905937f666f4056768c6f8087475`.
- No open GitHub PRs at the initial preflight.
- Jira returned 63 non-epic tickets and 12 coordinating epics assigned to Codex
  outside Done, including three already implemented tickets.
- KAN-146, KAN-148 and KAN-147 were reconciled to Done after verification of
  merged [PR #81](https://github.com/ShabalalaWATP/AllSeeingEye/pull/81),
  commit `d1455d7b`, successful final CI and recorded independent reviews.
  This does not assert live deployment/provider validation.
- The primary checkout's uncommitted workflow/history edits were preserved.
  Each batch starts in a separate managed worktree with private dependencies
  and test outputs. Prepared primary-checkout instruction files were read
  before work began.

## Batch register

The following are assigned scopes, not completion claims. Each delivery record
must map its ticket criteria to actual checks, unresolved acceptance and a PR.

| Batch | Tickets | Branch |
| --- | --- | --- |
| Workflow, contracts and guidance | [KAN-2](https://alex-orr.atlassian.net/browse/KAN-2), [KAN-4](https://alex-orr.atlassian.net/browse/KAN-4), [KAN-22](https://alex-orr.atlassian.net/browse/KAN-22), [KAN-23](https://alex-orr.atlassian.net/browse/KAN-23), [KAN-143](https://alex-orr.atlassian.net/browse/KAN-143), [KAN-144](https://alex-orr.atlassian.net/browse/KAN-144) | `codex/KAN-4-backlog-delivery` |
| Backend performance | [KAN-28](https://alex-orr.atlassian.net/browse/KAN-28), [KAN-31](https://alex-orr.atlassian.net/browse/KAN-31), [KAN-33](https://alex-orr.atlassian.net/browse/KAN-33), [KAN-34](https://alex-orr.atlassian.net/browse/KAN-34), [KAN-35](https://alex-orr.atlassian.net/browse/KAN-35), [KAN-37](https://alex-orr.atlassian.net/browse/KAN-37), [KAN-38](https://alex-orr.atlassian.net/browse/KAN-38), [KAN-39](https://alex-orr.atlassian.net/browse/KAN-39) | `codex/KAN-28-performance-batch` |
| CI and test quality | [KAN-69](https://alex-orr.atlassian.net/browse/KAN-69), [KAN-70](https://alex-orr.atlassian.net/browse/KAN-70), [KAN-71](https://alex-orr.atlassian.net/browse/KAN-71), [KAN-72](https://alex-orr.atlassian.net/browse/KAN-72), [KAN-73](https://alex-orr.atlassian.net/browse/KAN-73), [KAN-74](https://alex-orr.atlassian.net/browse/KAN-74), [KAN-75](https://alex-orr.atlassian.net/browse/KAN-75), [KAN-76](https://alex-orr.atlassian.net/browse/KAN-76) | `codex/KAN-69-ci-test-batch` |
| Security and operations | [KAN-16](https://alex-orr.atlassian.net/browse/KAN-16), [KAN-17](https://alex-orr.atlassian.net/browse/KAN-17), [KAN-18](https://alex-orr.atlassian.net/browse/KAN-18), [KAN-19](https://alex-orr.atlassian.net/browse/KAN-19), [KAN-21](https://alex-orr.atlassian.net/browse/KAN-21), [KAN-153](https://alex-orr.atlassian.net/browse/KAN-153), [KAN-154](https://alex-orr.atlassian.net/browse/KAN-154), [KAN-155](https://alex-orr.atlassian.net/browse/KAN-155) | `codex/KAN-153-security-operations` |
| Architecture and startup | [KAN-6](https://alex-orr.atlassian.net/browse/KAN-6), [KAN-7](https://alex-orr.atlassian.net/browse/KAN-7), [KAN-8](https://alex-orr.atlassian.net/browse/KAN-8), [KAN-9](https://alex-orr.atlassian.net/browse/KAN-9), [KAN-11](https://alex-orr.atlassian.net/browse/KAN-11), [KAN-12](https://alex-orr.atlassian.net/browse/KAN-12), [KAN-13](https://alex-orr.atlassian.net/browse/KAN-13), [KAN-44](https://alex-orr.atlassian.net/browse/KAN-44) | `codex/KAN-6-architecture-batch` |
| Sources and exports | [KAN-130](https://alex-orr.atlassian.net/browse/KAN-130), [KAN-131](https://alex-orr.atlassian.net/browse/KAN-131), [KAN-132](https://alex-orr.atlassian.net/browse/KAN-132), [KAN-133](https://alex-orr.atlassian.net/browse/KAN-133), [KAN-134](https://alex-orr.atlassian.net/browse/KAN-134), [KAN-139](https://alex-orr.atlassian.net/browse/KAN-139), [KAN-140](https://alex-orr.atlassian.net/browse/KAN-140) | `codex/KAN-130-sources-exports` |
| Opt-in notifications | [KAN-110](https://alex-orr.atlassian.net/browse/KAN-110), [KAN-111](https://alex-orr.atlassian.net/browse/KAN-111), [KAN-112](https://alex-orr.atlassian.net/browse/KAN-112), [KAN-113](https://alex-orr.atlassian.net/browse/KAN-113), [KAN-141](https://alex-orr.atlassian.net/browse/KAN-141) | `codex/KAN-110-notification-delivery` |
| Forecasts and alert feedback | [KAN-125](https://alex-orr.atlassian.net/browse/KAN-125), [KAN-126](https://alex-orr.atlassian.net/browse/KAN-126), [KAN-127](https://alex-orr.atlassian.net/browse/KAN-127), [KAN-128](https://alex-orr.atlassian.net/browse/KAN-128), [KAN-129](https://alex-orr.atlassian.net/browse/KAN-129) | `codex/KAN-125-forecast-feedback` |
| Runtime observability | [KAN-41](https://alex-orr.atlassian.net/browse/KAN-41), [KAN-42](https://alex-orr.atlassian.net/browse/KAN-42), [KAN-43](https://alex-orr.atlassian.net/browse/KAN-43) | `codex/KAN-41-runtime-observability` |
| Operator-only prerequisites | [KAN-45](https://alex-orr.atlassian.net/browse/KAN-45), [KAN-46](https://alex-orr.atlassian.net/browse/KAN-46) | `No implementation branch` |

## Shared contracts and integration

The coordinator owns this register and the master plan/development story.
Workers own their batch's code and dedicated evidence record. Shared changes
remain narrow: container factories, settings, lifecycle hooks, CLI registration,
generated OpenAPI and client types. Each PR must work against its own base.
Later PRs require updating from the resulting reviewed main and rerunning
combined checks. No branch may erase another batch's changes.

Reserved migration identifiers: security 0067, performance 0068, forecasts
0069/0070 and notifications 0071. Initially independent branches have the
existing 0066 predecessor; these are not an approved combined migration graph.
Integrate serially, adjust each later branch's predecessor to the merged head,
and test upgrade/downgrade and the combined schema before release. Never deploy
a combined set with accidental multiple heads.

Keep the required CI check identities. Run focused tests independently and
coordinate full coverage/performance runs to avoid invalid timing evidence.
Do not lower coverage thresholds. Real SMTP, model calls, production databases
and operator credentials are excluded from software verification.

## Explicit external acceptance

- KAN-45 needs the approved SSH destination, monitoring recipient/service,
  retention and cost choices, then approved live configuration and an isolated
  recovery from the off-host copy. Existing helper tests cannot satisfy this.
- KAN-46 requires the operator to replace and revoke three provider keys and
  verify production use without copying key values into chat or tickets.
- KAN-22 private vulnerability reporting was enabled and read back as enabled
  through GitHub. A private report was not submitted; recipient notification
  delivery is not yet verified.
- KAN-23's operator-assisted policy and shared-team retention stance need the
  operator's choice. Documented limitations must not imply account-wide erasure.
- KAN-131 requires a real 24-hour translation measurement. Source probes and
  deterministic tests cannot substitute for this elapsed workload evidence.
- Local Compose/PostgreSQL, browser, reference-host timing and live provider
  requirements remain per-ticket acceptance until actually exercised.
- KAN-2's development-panel linkage must be observed, not inferred solely from
  Jira keys in branch/PR names.

All new implementation tickets remain open until their checks, independent
reviews, acceptance criteria and authorised merge are complete. Epics remain
open while their children do. Opening a PR is not production release approval.

