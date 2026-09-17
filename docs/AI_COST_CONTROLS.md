# AI cost controls

How the app keeps mechanical model work cheap, what an administrator can control
per person and per team, what the shipped defaults are, and how estimated spend is
shown. Connection setup itself lives in
[AI_CONNECTIONS_OPERATIONS.md](AI_CONNECTIONS_OPERATIONS.md); the allowance ledger
design lives in [adr/0019-ai-usage-allowances.md](adr/0019-ai-usage-allowances.md).

## The measured starting point

Five days of the operator's own ledger, before any of this work:

| Purpose | Calls | Tokens |
| --- | --- | --- |
| Report generation | 117 | 870,000 (about 75 per cent of spend) |
| Conflict screening | 753 | 76,000 |
| Translation | 42 | 23,000 |
| Total | 912 | about 969,000 |

That is roughly 194,000 tokens a day, about 5.8 million a month, costing about
six US dollars a month at GPT-5.6 Luna prices ($0.20 per million input, $1.20 per
million output). Output dominates, and the profile runs at **Max** reasoning, so
reasoning tokens bill as output tokens. Reasoning effort is therefore the largest
single lever on the bill.

## 1. Reasoning effort per purpose

`ase.domain.reasoning` holds the policy. A *purpose* is the request's
`schema_name`, which every request builder already sets and which is the only
purpose identifier that reaches the provider gateway.

Mechanical purposes, capped by default:

`translation`, `query_translation`, `conflict_screening`, `claim_proposals`,
`economy_explainer`, `ukraine_digest`, `connection_test`.

Everything else keeps whatever the operator chose on the connection: reports and
their sections, direction, devil's advocacy, Ask Eye, research planning and
replanning, continuation and photo geolocation.

The cap is applied once, by `MechanicalEffortGateway` in
`ase.adapters.llm.effort`, which wraps the provider gateway in the container. It
rewrites only `reasoning_effort`, and only downwards:

- a connection already set below the cap keeps its own setting;
- a connection with no explicit effort keeps the provider default rather than
  being pushed up to the cap;
- recorded model provenance still reflects the profile the operator configured,
  because the profile is not modified.

Settings (see `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `ASE_AI_MECHANICAL_REASONING_EFFORT` | `medium` | `inherit` disables the cap; otherwise one of the effort names |
| `ASE_AI_MECHANICAL_PURPOSES` | blank | Comma separated schema names replacing the built-in list |

## 2. What an administrator can control

All of this is administrator-only, checked in the application layer, audited, and
never returns a credential or a key hint.

For a named person or a named team, through **Administration > AI access and
usage**:

- **See the effective allowance and spend.** The allowance preview lists every
  policy that would apply to that person, or to that person working for that
  team, with recorded usage and estimated spend for the period.
- **See the effective model.** The same preview names the connection that
  destination would actually use (personal override, team override, global
  connection, or the legacy first-enabled profile), its reasoning effort, and the
  lower effort mechanical work will run at. When no usable connection is assigned
  it shows the routing reason instead of a model.
- **Set or clear a limit.** Requests and tokens, daily, weekly or monthly. One
  target may now carry several periods at once, for example a daily and a monthly
  cap: policy uniqueness is per scope, target **and** period (migration `0060`).
  "Set a limit for this account/team" in the preview opens the policy form with
  that target already chosen, or the existing policy ready to edit. Disabling a
  policy clears the limit.
- **Set or clear a model binding.** Through **Administration > AI connections**:
  apply a tested connection to one person or one team, replace it, or reset that
  audience back to the global connection.
- **Grant a temporary override.** Dated, bounded and revocable, on top of a
  policy, without editing the policy itself.

Team allowances are charged only when work is explicitly assigned to that team,
and a caller who cannot act for a team cannot charge or read it.

## 3. Default policies

Nothing is enforced until a policy exists. With no policy the ledger observes and
records only, and the interface says so in those words. The suggested set is
previewed first and applied deliberately, by one click, in one audited action; a
scope, target and period that already carries an enabled policy is never
overwritten.

The set lives in `ase.domain.ai_defaults`:

| Scope | Period | Tokens | Why |
| --- | --- | --- | --- |
| Everyone | day | 300,000 | A daily ceiling for the whole site |
| Everyone | month | 9,000,000 | Thirty daily budgets |
| System work | day | 100,000 | Unattended background work, about five times the measured 20,000 a day |
| Each active account | day | 300,000 | One account cannot exceed the whole site's day |

**Read the headroom before adopting these.** The site-wide daily figure of
300,000 tokens is about 1.5 times the measured average of 194,000 a day, which is
not a wide margin: a busy day of report generation can reach it and requests will
then be refused until the period resets. The suggestion panel computes and shows
this multiple from the site's own recorded usage, so it stays honest as usage
changes. Raise the figure before applying it if you want real slack.

Per-account policies are created for the accounts that exist when the set is
applied. An account added later has no personal cap until one is created for it;
the site-wide policies still cover it.

## 4. Subscription defaults

New subscriptions default to a **weekly** cadence at **Quick** depth, the cheapest
useful recurring shape (`DEFAULT_CADENCE` and `DEFAULT_RESEARCH_MODE` in
`ase.domain.schedules`). Existing subscriptions are untouched; the default applies
only where no cadence is given.

The subscription form states the running cost of the chosen shape relative to a
weekly Quick subscription, and says plainly that a daily Advanced subscription
costs roughly twenty times a weekly Quick one: it runs seven times as often and
each run does far more model work, because Detailed and Advanced add challenge and
devil's advocate passes. Those weights
(`frontend/src/features/reports/subscriptionCost.ts`) are deliberately rough
guides for the choice being made, not predictions of an invoice.

## 5. Estimated spend

Recorded totals carry an input/output token split, so tokens can be priced. Where
a provider reported no split, the conservative charge is counted as output, the
dearer rate: the split always sums to the token total and an estimate never
understates.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ASE_AI_PRICE_INPUT_PER_MILLION` | `0.20` | GPT-5.6 Luna input price |
| `ASE_AI_PRICE_OUTPUT_PER_MILLION` | `1.20` | GPT-5.6 Luna output price |
| `ASE_AI_PRICE_CURRENCY` | `USD` | Shown beside the figure |

Edit these when the model or its price changes. Set both prices to zero to hide
money and show tokens only.

Every figure is an estimate from recorded tokens at the configured prices and is
labelled as such. It is **not a bill**: providers round, cache input, apply
minimum charges and discounts, and change prices mid-period. The provider's own
account remains the authority on what was charged.

## What the cap was hiding (17 September 2026)

Capping mechanical effort at medium made conflict screening work, and that
concealed the real defect rather than fixing it. Screening asked for at most
4,000 completion tokens whatever the administrator's profile allowed. Reasoning
tokens come out of that same allowance, so a profile set to Max spent the budget
thinking, the provider returned an incomplete response, and screening recorded
the generic "call failed". Over six days that was 740 failures in 906 calls,
every one of them billed. A 45 second stage ceiling cut off most of the rest.

The stages that reason now ask for the administrator's tested budget and keep
their own small ceiling only for a profile that does not reason: conflict
screening, the economy explainer and the Ukraine digest all had the same shape.
Screening also has 240 seconds against the 300 the gateway allows a thinking
stage, and an exhausted budget or a gateway timeout is recorded as itself, with
the tokens the attempt cost.

So the effort cap is now a cost choice rather than a correctness crutch.
Measured on this operator's ledger, the same screening work costs 3,304
completion tokens per call at Max against 1,224 at medium, about 2.7 times, or
roughly 38 pence a day more at 150 calls a day.
`ASE_AI_MECHANICAL_REASONING_EFFORT=inherit` removes the cap; any effort name
restores it.
