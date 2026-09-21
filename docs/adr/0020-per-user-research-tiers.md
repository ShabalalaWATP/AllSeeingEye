# ADR 0020: Per-user research tiers

Status: accepted

Date: 21 September 2026

## Context

Provider-call allowances measure model work. One research report can need several
calls for planning, drafting, review and optional tools. An account's allowance
of whole research runs therefore needs a separate admission boundary.

## Decision

Every account has one of four tiers: four runs per week, or four, thirteen or
thirty-two runs per day. An absent assignment means Level 1. Periods use UTC
calendar days and Monday-start weeks.

Store assignments and daily/weekly usage separately from provider-call policies,
authentication session data and report contents. Both counters advance for each
admitted run. Changing tiers selects which counter to enforce; it does not reset
either counter. Deleting report content cannot return allowance.

Use one application service behind a narrow persistence port. Enforce it at both
durable report admission and synchronous report generation. Subscriptions charge
their owner at the durable boundary. The durable job and its counter changes
commit together, after duplicate detection and validation. Synchronous admission
commits its counter changes before provider work. No network request runs while
holding allowance or administration locks.

Use the existing administration/account lock order for assignment and admission.
Administrator writes use an expected revision and fresh authority checks. Research
tier changes are separate from role or account-status changes, allowing an
administrator to set their own allowance without weakening account protections.

## Consequences

Admitted runs count even when later cancelled or unsuccessful. Work rejected before
admission does not count. Replaying an existing submission or resuming its job does
not count again; fresh generation does. Subscriptions exhausted at admission wait
for the reset and expose that reason.

Ordinary browsing, collection refreshes, exports and assistant chat do not consume
research runs. Fixed dashboard briefings use a server-selected admission factory
without a research-run charge; the client cannot select that exemption for an
ordinary report or subscription. Existing provider budgets still apply to model
work. The UI names these two kinds of allowance separately and shows the current research limit,
remaining runs and reset time.

The existing report job service grows from 350 to 354 lines for the injected
admission callback. This narrow exception to the 350-line target keeps the charge
inside the existing transaction; the quota rules and storage remain in separate
modules. It remains below the 400-line hard limit.
