# AI usage and cost controls

The app records model attempts and token usage, checks allowance policies before
calls, and shows estimated spend. A report can use several calls for planning,
drafting, review and optional tools. A call limit is therefore not a report limit,
and a token allowance is not a guaranteed monetary cap.

Configure models through [AI connections](AI_CONNECTIONS_OPERATIONS.md). Assign
research tiers under **Administration > Users**. Provider-call and token policies
remain under **Administration > AI connections > Advanced limits and embedding
connections**; the model assignments matrix also provides daily provider presets.

## Research tiers

Each account has one research tier. A research run is one accepted request to
produce a report, including a new report version or a subscription edition.
The internal model calls needed to produce that report do not each use another
research run.

| Tier | Research allowance | Reset |
| --- | ---: | --- |
| Level 1 | 4 runs per week | Monday, 00:00 UTC |
| Level 2 | 4 runs per day | 00:00 UTC |
| Level 3 | 13 runs per day | 00:00 UTC |
| Level 4 | 32 runs per day | 00:00 UTC |
| Level 5 | Unlimited research runs | No research allowance reset |

Accounts without an assignment, including new accounts, use Level 1.
Administrators can change another account's tier or their own research tier.
This does not change account roles, model assignments or provider budgets.
Level 5 removes the research-run cap for both manual research and subscriptions.
It does not remove provider-call, token, subscription budget or queue limits.

Manual and scheduled research share the owner's allowance. A subscription run
uses its owner's allowance even when a team manager starts it. Team research
uses the initiating account's research allowance as well as any applicable
provider budgets. Ordinary page loads, map actions, feed refreshes, reading or
exporting saved reports, and assistant chat do not consume research runs.
Fixed briefings generated automatically by dashboard pages also do not consume
research runs. Assistant chat, dashboard briefings and other model features still
have provider-call and token limits.

Usage is saved when a run is admitted. Invalid requests rejected before admission
do not count. An admitted run counts even if it later fails or is cancelled.
Resuming the same job, automatically retrying its stages or repeating its existing
submission does not use another run. Starting fresh research or regenerating a
report does. Deleting a report or discarding a job does not return an allowance slot.

Changing tiers does not reset usage: the app retains both daily and weekly counts.
Unlimited runs are recorded too. Moving a Level 5 account to a capped tier uses
its existing counts for that day or week. Level 5 shows today's recorded usage
instead of a remaining allowance or allowance reset.
Usage and the next reset are visible alongside research and in account settings.
An exhausted subscription waits for allowance to become available. The scheduler
rechecks blocked subscriptions at five-minute intervals. After a reset or tier
increase, work can resume on the next eligible scheduler pass.

Research tiers limit whole runs. The provider allowances below also apply, so a
run can still be stopped by a shared token limit or a provider error before it
finishes. A research allowance is not a guaranteed monetary budget.

## Provider-call allowances

Policies can limit requests, tokens or both over daily, weekly and monthly UTC
periods. Several periods can apply to one target at the same time.

| Scope | What it covers |
| --- | --- |
| Everyone | Shared site usage across accounts and purposes |
| System work | Unattended background work, alongside the site allowance |
| Person | That person's personal and team requests |
| Team | Work explicitly assigned to that team, alongside applicable person and site limits |

All applicable policies must permit the call. Setting a generous user limit does not
increase a shared site or team limit. A user must be authorised for a team to charge
work to it. Temporary overrides are dated and revocable; resolve active or future
overrides before changing an underlying daily preset.

A fresh installation starts with these protective token policies:

| Scope | Period | Tokens |
| --- | --- | ---: |
| Everyone | Day | 300,000 |
| Everyone | Month | 9,000,000 |
| System work | Day | 100,000 |

Initial policy seeding preserves installations that already have policy records.
Administrators can change or disable policies. If no enabled policy applies, usage
is observed without that allowance restriction, and the interface says so.

The suggested-policy action previews the set before applying it and can add a daily
300,000-token policy for each active account. It does not overwrite an existing
enabled policy for the same scope, target and period. Accounts created later do not
automatically gain those personal policies, although shared site limits still apply.
Choose limits against the installation's expected workload rather than assuming
these defaults suit every team.

## Daily presets

The AI connections matrix offers:

| Preset | Calls per day | Tokens per day |
| --- | ---: | ---: |
| Light | 50 | 100,000 |
| Standard | 250 | 500,000 |
| Intensive | 1,000 | 2,000,000 |
| Power | 2,500 | 5,000,000 |

**Blocked** sets both daily limits to zero. **Inherit** removes that target's daily
policy, leaving other applicable policies in force. Weekly and monthly caps continue
to apply. A team preset is a shared allowance, not an allowance for each member.

## Reasoning and output budgets

Analytical stages use the model connection's configured reasoning setting. Mechanical
stages can use a lower effort cap to avoid spending report-level reasoning on short
transformations and classifications.

The built-in capped purposes are translation, query translation, conflict screening,
claim proposals, economy explainers, Ukraine digests and connection tests. Report
analysis, planning, review, Ask Eye and photo analysis retain the configured effort.

| Setting | Default | Meaning |
| --- | --- | --- |
| `ASE_AI_MECHANICAL_REASONING_EFFORT` | `medium` | Cap explicit reasoning effort for mechanical purposes; `inherit` removes the cap |
| `ASE_AI_MECHANICAL_PURPOSES` | Built-in list | Optional comma-separated replacement list of purpose names |

The policy only lowers an explicit setting. A profile already below the cap stays
there; a profile using the provider's default is not assigned a new effort. Providers
still control which settings their models support. The effective-model preview shows
the configured model effort and applicable mechanical effort separately.

Reasoning can consume the completion allowance before visible output is produced.
Increasing that allowance can improve headroom and increase cost, but cannot guarantee
completion or a valid report. Failed and cancelled requests can still be billed.
Inspect recorded failures before repeating them.

## Recurring research

New subscriptions default to **weekly** at **Basic** depth. More frequent runs and
Deep or Advanced research create more collection and model work. The subscription
form's relative-cost indicator is a rough comparison between choices, not an invoice
forecast.

Start with a cadence that matches how quickly the subject changes. Inspect a completed
edition's coverage and usage before increasing frequency or depth. Pausing stops
further scheduled admissions; it does not refund work already sent to a provider.

## Estimated spend

The app estimates spend using recorded input/output tokens and operator-configured
rates:

| Setting | Purpose |
| --- | --- |
| `ASE_AI_PRICE_INPUT_PER_MILLION` | Estimated price per million input tokens |
| `ASE_AI_PRICE_OUTPUT_PER_MILLION` | Estimated price per million output tokens |
| `ASE_AI_PRICE_CURRENCY` | Display currency |

Set these rates for the intended comparison and update them when pricing changes.
They are installation-level estimates, so a mixture of differently priced models
will not produce an exact provider-by-provider bill. Set both prices to zero to
hide monetary estimates and display token usage instead.

When a provider does not supply a usable split, accounting can retain a conservative
charge rather than inventing exact input/output counts. The provider can apply cached
input rates, tool charges, discounts, minimums and other adjustments that this estimate
does not reproduce. Its account billing remains the authority on actual spend.

Allowances reduce exposure to unplanned usage but are not a substitute for provider
account limits. Review both the app's policies and the provider's own usage controls.

## Implementation boundaries

Allowance admission and accounting live in application services, separate from
provider transport. They cover text requests, native web-search requests and charged
embedding work. Policy changes are administrator-only and audited. The design and
reservation behaviour are documented in [the usage allowance ADR](adr/0019-ai-usage-allowances.md).
