# ADR 0017: Durable AI allowance admission and settlement

Status: accepted for the teams, profiles and AI usage slice

Date: 15 September 2026

## Context

The existing `llm_usage` table is a provider call audit trail. It is written after a
model request and therefore cannot prevent a user or team from exceeding an
administrator-defined allowance. Report jobs also have a separate, job-local budget.
The new team model needs a site-wide policy that can cover personal and explicit team
work without holding a database transaction open while a provider is called.

## Decision

Add a separate policy and ledger bounded by three calendar periods: day, week and
month. Policies can target the site, one user or one team. A policy has independent
request and token ceilings. `None` means unlimited; zero is an explicit deny-all
ceiling and is never interpreted as unlimited.

Admission creates a short-lived reservation in its own transaction. The counter row is
updated with a conditional SQL `UPDATE`, so concurrent reservations cannot both pass a
finite ceiling. The provider call then happens without an open database transaction.
Settlement moves the reservation into used counters exactly once, records known provider
token counts and conservatively charges the reserved amount when counts are unknown.
The existing `llm_usage` record remains the detailed provider audit and is not replaced.

Global and user policies apply to personal work. A team policy applies only when the
caller supplies an explicit, currently joined team destination. This prevents a
personal Ask Eye question from consuming the allowance of every team the account joins.
The destination check belongs in the accounting adapter as well as in higher-level
services, so a future team report path cannot bypass membership by passing an arbitrary
team identifier.

Installations with no enabled policy preserve existing behaviour. Administrators enable
enforcement by creating a policy through the administrative API. Policy deletion is
implemented as a revisioned disable operation so historical reservations remain
auditable.

## Consequences

The admission path is fail-closed when an enabled policy is exhausted and reports a
stable `ai_usage_limit` error. Provider assignment and encrypted credentials remain in
the existing model-routing implementation. Scheduled reports, translation and other
model-backed paths still need to call the accounting service before they are covered by
the shared policy; their existing budgets continue to protect them until that work is
completed.

