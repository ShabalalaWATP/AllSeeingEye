# Configure an AI connection

Administrator connection controls are implemented. A real account connection
still requires entering its key and testing it through the app.

## OpenAI GPT-5.6 Luna

Sign in as an administrator and open **Administration > AI connections**.
Create an OpenAI connection using:

| Setting | Value |
| --- | --- |
| API base URL | `https://api.openai.com/v1` |
| Model | `gpt-5.6-luna` |
| Reasoning | Max |
| Completion budget | 16,000 tokens, including reasoning |
| API key | Enter directly into the password field in the app |

The key goes to the application server and is encrypted using the existing
server encryption configuration. It is never returned by the API; an existing
connection shows only a short hint. Do not put the key in a model URL, source
file, evaluation profile JSON or chat message.

Save the replacement configuration, load the provider's model list if needed,
and test the connection. The test sends a small synthetic structured-output
request with the selected model and reasoning setting, not saved research.
It can consume API tokens. A successful test establishes connectivity and a
small output contract, not the quality of a full research assessment.

At the official OpenAI base URL, an explicit **Max** reasoning setting uses
`/v1/responses`. This preserves the selected model and reasoning level instead of
silently lowering them when Chat Completions rejects `max`. Structured output uses
strict `text.format` JSON schema; sanitised photo analysis uses native `input_image`
content. The request sets `store: false`, which does not override the provider's
account-level retention policy. Other reasoning settings and custom compatible
endpoints retain the existing Chat Completions route.

Official OpenAI **Max** report drafts have a five-minute request deadline by
default. Full drafts can need several minutes; the longer deadline does not
guarantee completion. Other gateway requests retain their two-minute default,
and shorter stage deadlines still apply. An explicitly configured gateway timeout
overrides these defaults. Admission waiting, HTTP transfer and response parsing
all count towards the selected deadline. The whole report remains bounded by its
ten-minute production deadline, and the existing retry limit is unchanged.
Cancellation, concurrency and response-size limits still apply to both routes.
Incomplete responses, refusals and malformed response bodies fail the connection
test rather than being treated as successful answers. The official
[Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
lists `max` reasoning, image input and structured outputs. The request shape follows
the [structured output guide](https://developers.openai.com/api/docs/guides/structured-outputs)
and [image input guide](https://developers.openai.com/api/docs/guides/images-vision).

Full report schemas require every declared property, including nullable values.
For example, each new key judgement includes `change_from_previous: null` when
there is no previous judgement to compare. The new-output validator enforces
this contract; existing saved reports that omitted the field remain readable.
Recursive local tests cover the actual schemas used by drafting, planning,
review, translation, conflict screening and photo analysis. These checks prevent
missing-required-field errors but do not establish full provider compatibility.

Direction questions guide coverage; they do not establish that requested checks
were performed. Related supported questions can share a cited assessment section.
Unsupported questions are recorded as named intelligence gaps, with missing
evidence and future collection recommendations kept separate from completed work.

Apply the tested connection to the global default or a selected team. Global
applies to personal work and teams that inherit it, including administrators'
work. An explicit team override stays in place when the global default changes.
In-flight research keeps the configuration with which it started.

Set the global default first. To return a team to it, choose the team's inheritance
action and confirm. Resetting a team does not change other teams' overrides.
Choose **Use for another scope** on an active connection to apply the same saved
configuration to another team or the global default. This does not require
re-entering its key or remove its existing assignments. A current successful test
and explicit scope confirmation are still required.

## Amazon Bedrock

Open **Administration > AI connections**, create a connection and choose
**Amazon Bedrock**. Select the AWS region, enter a Bedrock API key in the password
field and paste the exact model or inference-profile ID from the AWS console.
The app builds the regional endpoint, for example
`https://bedrock-runtime.us-east-1.amazonaws.com`.

This connection uses the native Converse API with bearer authentication. Enter
a **Bedrock API key**, not an AWS access-key ID or secret access key. AWS documents
how to obtain [Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html).
The key is encrypted on the application server using the same storage as other
connections. Its permissions and the selected model must allow inference in the
chosen region. Short-term keys expire; this version does not renew credentials
or use an IAM role, AWS credential chain or SigV4 signing.

Choose a model that supports native Converse structured outputs, such as the
documented model ID `openai.gpt-oss-120b-1:0`, subject to your account and regional
availability. This is an example, not an automatically selected model. A direct
OpenAI model name and reasoning setting cannot be assumed to work on Bedrock.
See [Bedrock structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
and the [model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-oss-120b.html).

Model selection is manual. The app does not enumerate the AWS model catalogue,
which requires a separate control-plane integration. Bedrock supports text and
sanitised image requests through Converse, subject to the selected model accepting
those inputs, with provider-default reasoning and temperature from 0 to 1. Embeddings retain their separate OpenAI-compatible profile. The app accepts
model and inference-profile identifiers up to 2,048 characters; AWS still checks
the identifier, model access and model-specific token budget during the test.
The configured completion budget applies to every native text stage, including
provider reasoning. Larger budgets can increase inference cost.

Save, **Test connection**, then review and confirm the global or team assignment.
The test is a small billable structured-output request. It establishes that the
saved connection can answer that request, not that every research task will
succeed. Changing region or provider clears any typed key; a replacement needs
its own explicit key. Existing connections continue serving work while a
replacement is tested, and in-flight work retains its captured provider.

AWS may take several minutes to compile a new structured-output schema. The app
keeps a 120-second request deadline, so a first attempt can time out; retry the
saved connection test after checking AWS availability. A different report schema
may need its own first compilation even after the small connection test succeeds.

## Provider and model changes

An active connection is replaced through the same test-and-apply flow. This
keeps the current connection available while the replacement is being tested.
Use an explicit new key when changing the destination endpoint. A provider's
model catalogue is the account-visible list, not a guarantee that every listed
model supports the application's text and structured-output requirements.

For a compatible endpoint without model discovery, enter its exact model ID and
use the connection test. Provider-specific APIs that do not implement the
OpenAI-compatible contract require a separate adapter; Bedrock has its own native
Converse adapter.

Luna does not replace an embeddings model. Semantic-search embeddings keep a
separate profile and existing index compatibility rules. Shared live-feed
translation follows the global text connection, rather than a particular team.

## Existing installations

The connection workflow adds migration `0017`; native Bedrock adds `0018`.
Back up the intended database and its
encryption configuration using the existing [backup procedure](BACKUP_RESTORE.md),
then run `uv run ase migrate` from `backend` against that explicitly selected
database and restart the application. Development checks use disposable databases;
they do not migrate an operator installation.

Migration preserves existing encrypted keys and enabled legacy profiles without
automatically choosing a global or team connection. The existing role selection
continues until the first tested global replacement is applied. Until then,
enabled legacy text profiles are protected from editing and deletion. New text
profiles are saved as inactive drafts. An embeddings-only profile can still be
enabled separately when saved.

Downgrading `0017` is refused while connection assignments or explicit reasoning
settings exist, rather than silently discarding the selected routing policy.

Migration `0018` defaults existing profiles to OpenAI-compatible without changing
their encrypted keys, successful test hashes or assignments. It expands encrypted
credential storage and model identifiers, including saved report model IDs.
Downgrade is refused while native Bedrock profiles, values exceeding the former
storage bounds or provider-bearing frozen report routing records remain. The old
reader cannot interpret those new records. Do not remove historical reports merely
to force a downgrade.

## Research quality evaluation

The chosen public configuration is provided in
`backend/evaluations/openai-luna-profile.json`. It contains no credential.
For a deliberate standalone evaluation, set `ASE_EVAL_API_KEY` in the process
environment using your normal secret-management workflow, then run from backend:

```powershell
uv run python -m evaluations run --profile evaluations/openai-luna-profile.json --cases-dir evaluations/research_cases --out ../data/luna-research-eval --max-calls 24
```

The output directory must be new. This makes actual API calls against synthetic
research scenarios. The harness deliberately does not decrypt saved app keys.
This standalone evaluator currently uses the OpenAI-compatible adapter; it does
not accept a native Bedrock configuration.
Human review and the wider representative evaluation remain necessary; the
two replay cases do not measure general factual accuracy or live retrieval.

See [evaluation instructions](../backend/evaluations/README.md) and
[connection design](AI_CONNECTIONS_PLAN.md).
