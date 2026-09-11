# Fresh web research

The optional fresh-web switch adds one live OpenAI Responses search to a public
research question. It is separate from the app source picker. Selecting a subset
of app sources does not silently turn the web search on or off.

The report destination's immutable **direction** model profile supplies the model,
reasoning setting and encrypted credential. The connector accepts only an enabled
OpenAI profile with `https://api.openai.com/v1`. It sends the credential only to
`https://api.openai.com/v1/responses`. Bedrock, local and other compatible endpoints
retain their selected configuration; the receipt explains that native fresh web
search is unsupported. There is no cross-team or provider fallback.

The chosen model and account must support the Responses `web_search` tool. The
app does not infer that capability from a model name or mark configuration presence
as a successful connection test. Provider charges can apply to this optional call.

## What the report preserves

`ResearchReceipt.web_research` stores a bounded generated summary, native provider
URL citation annotations and a separate consulted-URL inventory. The main report
draft receives this as untrusted discovery context for gaps, candidate explanations
and verification work. It is never an E-labelled source, a publisher excerpt, or a
contribution to the NATO/PHIA evidence assessment. This prevents an LLM-generated
answer and several links from masquerading as independent corroboration.

The dedicated **Fresh web context** section shows the generated answer and native
citations. Markdown renders linked citation markers; structured report responses
expose bounded text and citation offsets. PDF and Word exports include the context
and citation URLs. Offsets are Unicode codepoint indices into the saved synthesis.

Returned citation annotations and consulted URLs are both provider assertions.
The app does not claim every citation was independently fetched or that every
consulted page is listed. Only the native annotation URLs are eligible for rendered
citation links; URLs written inside generated prose are not promoted to citations.
Citation syntax validation is not permission for a server-side page fetch.

The record freezes the requested and returned models, selected profile ID/revision,
retrieval time, request count, tool-call count and returned usage. Unknown publication
dates remain unknown. Requested countries and area geometry are search context,
not evidence that a result belongs to that location. Historical searches are partial
discovery, not proof of complete coverage for the selected interval.

The search instructions require the model to preserve the actual claimant and
distinguish original event dates from original publication, republication, page
update and search-index dates. Reused historical claims must be background;
unresolved event dates must remain uncertain rather than current-period facts.
These instructions reduce risk but do not verify claims. A completed, cited
response can still misattribute a claim or present old events as new. Operators
must check the original source and event timing before relying on the synthesis.

## Privacy and operational limits

- Public research requires the explicit `research_web_search: true` option.
  Document and media research never sends private uploads or extracted contents to
  this tool. A separate public question can be used for public corroboration.
- The administrator can disable `research-web-search` in source controls. Checks
  before dispatch and after the external call prevent disabled results being admitted.
- One request allows at most three native tool calls and 90 seconds including admission.
  The search instructions plan across all selected countries within two tool calls,
  then require a final cited answer that states any coverage gaps. Three remains
  the hard request and response-validation ceiling, not the intended search count.
  The output allowance uses the selected profile's stage budget: 6,000 tokens by
  default, with configured reasoning headroom up to a hard 16,000-token ceiling.
  This includes reasoning tokens, not just the visible answer. A smaller profile
  budget remains binding. The model and reasoning effort are preserved; the app
  does not retry automatically when the provider exhausts the allowance.
- Response limits remain 12 citation annotations, 20 consulted URLs and 6,000
  characters of generated synthesis, even with a larger reasoning allowance.
- Two concurrent native requests, six attempts per user per hour and 24 attempts
  per process per hour are allowed. These limits assume the documented single API
  worker deployment. They are separate from ordinary feed collection budgets.
- Native `tool_choice: auto` allows the model to finish its cited answer after
  searching; `external_web_access: true` enables live search. The instructions
  explicitly require a real search. Success still requires a completed response,
  at least one completed search action, no unfinished calls, no more than three
  total tool calls and attributable text with native citations. An answer without
  an executed search fails closed, as does a fourth call even if the overall
  provider response says it completed. No generated fallback is admitted.
- Redirects and compressed replies are rejected; streaming response bodies are
  capped at 512 KiB. Errors expose safe status messages, never provider bodies,
  question text or credentials. Cancellation closes the transport.
- Existing usage fields are committed in an isolated session after each native
  attempt. Cancellation records an attempted call with unknown final token usage.
  A three-second shield protects only this database write. A failed or uncertain
  write produces an accounting warning when a report completes. It is not retried
  through report persistence because a commit may have succeeded before the error.
  A database outage and cancelled report can still leave usage unavailable. Final
  report token totals are not doubled.
- `store: false` disables Responses application-state storage for the request. It
  does not assert zero provider retention or override the account's data policy.

## Verification

Deterministic tests cover fixed origin and credential placement, configured model
preservation, profile token limits and reasoning headroom, actual tool execution,
citation and response bounds, incomplete-response usage accounting, private-input
exclusion, selected countries, source disable during a request, cancellation,
durable usage, generated-context persistence and report HTTP read/export. These
tests use synthetic responses and do not establish live provider availability or
measured research quality.

The integration follows the official [web-search guide](https://developers.openai.com/api/docs/guides/tools-web-search)
and its native citations. The [deep research guide](https://developers.openai.com/api/docs/guides/deep-research#best-practices)
documents the `max_tool_calls` request control. The app preserves the selected
model instead of silently switching to a deep research model.
