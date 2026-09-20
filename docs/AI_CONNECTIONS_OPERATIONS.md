# Configure AI connections

Administrators configure models under **Administration > AI connections**. A
connection contains the provider, endpoint, model, credential, reasoning setting and
completion allowance. An assignment decides which personal or team workspace uses it.

Read [AI in the app](AI.md) for the data sent to providers and the limits of generated
assessments. You do not need to configure an AI connection to inspect public map data,
but research generation and other model-backed features need a usable connection.

## Add and test a model

1. Select **Add model** and give the connection a recognisable name.
2. Choose the provider and enter its key directly in the password field. Never put
   a key in the endpoint URL, a research question, a screenshot or a source file.
3. Select an account-visible model, or enter its exact ID when discovery is unavailable.
4. Choose supported reasoning and completion settings. A larger output allowance can
   increase cost; reasoning may consume that allowance before a visible answer appears.
5. Select **Test connection**. This saves an inactive draft and makes a small model
   request that can incur a charge.
6. After a successful test, select the audience and **Save and close** to apply it.

The workspace supports up to five text-model connections, including drafts.
Embedding-only connections are managed separately in advanced settings.

Testing and applying are separate actions. Closing after a test leaves a saved draft
in its slot; it does not apply the audience. A successful test proves only that the
selected configuration answered the small test request. It does not validate model
accuracy, photo analysis or every full-report schema.

Keys are encrypted using the server's configured encryption key. Saved connections
show a short hint rather than the full key. Preserve the encryption key with your
backup material: a database backup alone cannot recover encrypted credentials.

## Provider settings

### OpenAI

Use the official API base `https://api.openai.com/v1` and an API key for the intended
account. Select a model available to that account that accepts the application's
structured-output contract. Model names, supported reasoning settings and available
input types depend on the account and provider.

The app uses Chat Completions for its compatible text route. An explicit **Max**
reasoning setting at the official OpenAI endpoint uses Responses. Supported photo
requests use sanitised image input. Native fresh web research also uses Responses,
but requires its own supported model capability and explicit selection in research.

New popup connections start with a 16,000-token completion allowance. The app accepts
configured allowances up to 32,000 tokens; individual stages can impose smaller
limits. These are app limits, not a promise that a particular model accepts them or
finishes within them. An exhausted reasoning budget is reported as such rather than
silently lowering the requested model or effort.

### Custom OpenAI-compatible endpoint

Enter the backend-reachable API base URL and the exact model ID. Remote endpoints
must use HTTPS. Local model servers are supported through local/private addresses,
subject to the same structured-output contract.

Model discovery may not be implemented by the endpoint. Use the exact-ID option and
test the connection. Compatibility with ordinary chat does not establish compatibility
with strict JSON schemas, images, reasoning parameters or embeddings.

A container's `localhost` is the container itself. If the model runs on the host,
use the host address appropriate to your container platform and confirm reachability
from the backend. See [setup](SETUP.md) for the application's local environments.

### Amazon Bedrock

Choose **Amazon Bedrock**, select the AWS region, enter a **Bedrock API key** and
paste the exact model or inference-profile ID permitted in that region. The app
constructs the regional runtime endpoint and calls the native Converse API.

This integration uses bearer authentication. It does not accept an AWS access-key
ID/secret pair, use an instance role or renew short-lived keys. The chosen model
must support Converse structured outputs; image requests additionally require image
support. Reasoning uses provider defaults. Embeddings retain their separate compatible
profile.

Model selection is manual because the app does not call the AWS control-plane model
catalogue. A first use of a structured-output schema can take longer than an ordinary
request. If a test times out, inspect provider availability and permissions before
retrying. A successful small test does not exercise every report schema.

## Assign a connection

Apply a tested global connection first. It supplies personal work and teams that
inherit the default, including administrator work. Then add personal or team overrides
where needed.

| Destination | Resolution |
| --- | --- |
| Personal workspace | Owner's personal assignment, then global default |
| Team workspace | Team assignment, then global default |
| Shared background text work | Global routing |
| Embeddings | Separate global embeddings profile |

Use **Use default** in a matrix row to remove that audience's override. Changing
the global connection preserves other overrides. An administrator working on someone
else's report uses the destination's routing, not their own personal model.

Cards and the assignment matrix represent the same saved configuration. **Manage
access** opens the matrix; **Assign model** on an already tested, unassigned card
returns to audience selection without another paid test. In-flight work retains the
configuration captured when it started.

## Change or remove access

Use the same test-and-apply flow to replace an active connection. Enter an explicit
replacement key when changing the endpoint or provider. Changing request settings
invalidates the old test proof, so test the new configuration before applying it.

The current connection can continue serving work while a replacement draft is tested.
An assigned configuration that becomes unavailable does not silently fall back to a
different audience's provider.

The matrix also offers daily allowance presets and **Blocked**. Model and allowance
edits in a row save together. If another administrator changes the same records,
refresh the workspace, review the new values and retry. See [cost controls](AI_COST_CONTROLS.md)
for how shared limits and temporary overrides interact.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No model available | Global assignment, destination override and whether the assigned configuration is still tested and enabled |
| Model list unavailable | Account permissions, endpoint discovery support, or the exact-ID fallback |
| Small test works but a report fails | Report schema support, completion allowance, provider limits and the saved failure reason |
| Budget exhausted | Reasoning and visible output share the allowance; review the model settings and expected cost before increasing it |
| Allowance reached | Every applicable site, system, user and team policy, including weekly/monthly caps |
| Embeddings unavailable | A separate enabled embeddings profile and a compatible index/model configuration |
| Fresh web search unsupported | Official OpenAI destination and native web-search support; custom endpoints and Bedrock have no automatic fallback |

Use a small representative research question after connection setup and inspect its
collection receipts, evidence and validation findings. Automated tests use controlled
responses; they do not establish a provider's current availability or general factual
accuracy. Evaluation tooling is documented in [backend evaluations](../backend/evaluations/README.md).
