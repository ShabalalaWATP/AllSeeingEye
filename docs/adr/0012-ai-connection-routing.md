# ADR 0012: tested AI connections with explicit scope

Status: accepted and implemented; real-account acceptance remains outstanding.
Date: 6 September 2026.

## Context

Administrators need to select a provider, model, reasoning effort and API key for
the whole app or a particular team. Selecting the first enabled model by creation
order does not express that policy. Editing an active profile also changes where
future requests send material before the replacement has been tested.

The user selected OpenAI `gpt-5.6-luna` at `max` reasoning. The existing gateway
uses Chat Completions with structured outputs, without model tool calls. That
endpoint supports the selected model; a Responses migration is not required for
this workflow. Provider discovery returns account-visible identifiers, not a
universal compatibility guarantee.

## Decision

Keep encrypted connection profiles, but separate configuration from activation.
A successful connection test records the exact tested configuration. Activation
requires that test still to match. Bound profiles are immutable through ordinary
editing and deletion; an administrator prepares and tests a replacement instead.

A global binding selects the default text-generation connection. A team binding
overrides it only for work owned by that team. The requesting administrator's own
memberships do not determine where another team's report is processed. Resetting
a team binding explicitly returns it to global inheritance. Invalid configured
bindings fail closed, rather than silently changing provider.

Resolve and copy the selected profiles before outbound work. A switch affects new
work; it does not mix providers within an already-running research pipeline or
rewrite historical reports. Shared live-feed translation uses the global policy.
Embedding models retain their separate role and index compatibility constraints.

Keep credential handling on the server. Discovery and tests use bounded calls,
do not follow redirects and expose sanitised failures. A changed endpoint cannot
silently inherit a saved credential. Recheck current administrator authority and
the original request session after outbound work, then apply mutations under the
existing administration guard. Audit identifiers and outcomes, never key values.

## Consequences

The normal workflow is configure, test, confirm scope, apply. Active connections
cannot be repaired by editing their fields in place; replacement makes the
change explicit and leaves the previous connection available while testing.
Legacy deployments without bindings retain their existing role selection until
an administrator deliberately applies the new policy.

New and edited text profiles are disabled drafts, even if an API caller requests
enabled status. Before the first global activation, existing enabled legacy text
profiles cannot be edited or deleted. This preserves the migrated selection and
prevents ordinary profile CRUD from bypassing the connection test. Embeddings-only
profiles keep their separate enable-on-save workflow. Establish the global default
before creating a team override.

Each activation receives a durable, monotonically increasing assignment revision.
Deleting and recreating a team override cannot reuse an old confirmation revision.
Each connection test also receives a generation number: a late result cannot
overwrite a newer test. Starting or failing a retest clears eligibility for a new
activation; an existing binding retains its own proof of the configuration that
was originally applied.

Report versions retain non-secret model-routing metadata for each text stage.
Historical versions without that metadata remain readable. The API exposes it;
prose exports do not yet include a model-configuration appendix.

Max reasoning shares a bounded completion budget with the visible answer and can
increase latency and token use. The connection test proves only that the selected
account/model/settings can complete a small structured-output request. Research
quality still needs representative evaluation and human review.
