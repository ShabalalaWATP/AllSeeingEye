# Exact candidate registry routing

Implementation contract, 7 September 2026. This is outstanding work in the full
research expansion, not implemented provider capability. Read-only inspection of
the local adapters and planning pipeline established the boundaries below.

## Verified gap

Supplementary tasks currently replace query terms only. Registry adapters read
the company subject, so an operator candidate identifier cannot select a new
exact registry lookup. Planning also requires a supported baseline and planned
term capability. A company-name baseline consequently hides identifier-only
sources even when an operator candidate supplies a usable identifier.

`ResearchCandidate.identifiers` currently contains untyped strings. Substring
presence in operator context does not establish a registry namespace. Preserve
legacy strings as context; do not silently reinterpret bare digits as either a
SEC CIK or a UK company number.

## Implemented provider inputs to preserve

| Provider | Existing input contract |
| --- | --- |
| GLEIF profile and direct/ultimate parents | Company focus, exact LEI, optional LEI prefix; no name resolution |
| SEC submissions | Company focus, exact CIK; current baseline accepts prefixed or numeric input |
| SEC directory | Company name/ticker candidate discovery; no verified identity match |
| Companies House profile | GB or unrestricted country, company name or number |
| Companies House officers/PSC | Explicit GB or companies-house prefixed number |

Provider availability still depends on selected sources and configured credentials.
No live provider compatibility was established by this inspection.

## Input and routing contract

Keep existing term-search tasks backwards compatible. Add a distinct exact
candidate-identifier route carrying candidate reference, identifier reference,
namespace, original operator text and canonical value. Require explicit namespace
selection or a qualified identifier. Do not select the first compatible candidate
string implicitly. Use explicit namespaces for LEI, SEC CIK and GB company number.

A pure adapter capability validates namespace/value and supplies the canonical
subject. Forward that capability through pacing and source-control wrappers.
Application code must not import adapters to parse identifiers. Determine support
using the routed query, while retaining question, company focus, country, date,
language, area and selected-source constraints. Do not widen general, domain,
private-input or area research into company registry queries.

An exact identifier lookup is disambiguation. It does not become an independent
counterevidence search because a model labels its purpose challenge. Restrict the
new route accordingly and disclose that limitation in its frozen receipt.

## Execution, automatic planning and preservation

Execute the validated effective subject, not only the displayed plan terms. Each
profile, parent, officer or PSC operation consumes its own shared request slot.
Keep quick/detailed request, item, deadline, cancellation, pacing and source
activation checks. No implicit graph traversal, extra pages or hidden lookup
fanout is authorised by an exact task.

Expose compatible operator-supplied identifiers to automatic planning through
server-issued references. A model may select a supplied reference; it must not
invent identifier text or turn a company name into an exact identifier. Selected
identifier sources may be available even when the baseline company name is not
supported. Name-search results remain candidates; automatically chaining them
requires a later evidence-grounded discovery and admission contract.

Preserve route and identifier provenance through API scope serialisation,
regeneration, preview, replanning, actual collection, frozen receipts and exports.
Translation never alters identifiers. Replanning must compare effective routed
subject as well as terms, and cannot replace operator identifier intent. Historical
receipts lacking route fields retain explicit legacy term-route defaults.

The plan editor should identify the lookup clearly, for example Exact LEI lookup,
show its candidate and original identifier, and explain unsupported country/source
conditions. Generated API types must come from the backend schema.

## Required acceptance

- Unsupported company-name baseline plus valid explicit candidate identifier
  executes only the selected eligible registry source.
- Two candidates on one source retain separate effective subjects and receipts.
- Unknown references, malformed/wrong namespaces, ambiguous bare digits, duplicate
  canonical identifiers and model-invented identifiers are rejected explicitly.
- Names and directory results remain unverified candidates; country and focus
  constraints cannot be bypassed through routing.
- Prefix/case/padding canonicalisation preserves original input and provider
  response identity checks.
- Shared request/item/deadline limits, cancellation, pacing and source disablement
  apply before and after lookup; unsupported work produces honest receipts.
- Translation and replanning preserve identity. No hidden traversal or paging.
- API, saved scope regeneration, preview, collection and exported receipt roundtrip
  retains the exact route; old records remain readable with legacy defaults.

The completion evidence must exercise actual task query construction with fixture
providers, not only validate DTO fields or show a route in the editor. Real model
and provider acceptance remain separately disclosed release gates.
