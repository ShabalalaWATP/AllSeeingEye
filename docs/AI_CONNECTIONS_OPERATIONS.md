# Configure an AI connection

Administrator connection controls are implemented. A real account connection
still requires entering its key and testing it through the app.

## OpenAI GPT-5.6 Luna

Sign in as an administrator and open **Models** in the administrator navigation.
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

## Provider and model changes

An active connection is replaced through the same test-and-apply flow. This
keeps the current connection available while the replacement is being tested.
Use an explicit new key when changing the destination endpoint. A provider's
model catalogue is the account-visible list, not a guarantee that every listed
model supports the application's text and structured-output requirements.

For a compatible endpoint without model discovery, enter its exact model ID and
use the connection test. Provider-specific APIs that do not implement the
OpenAI-compatible contract require a separate adapter.

Luna does not replace an embeddings model. Semantic-search embeddings keep a
separate profile and existing index compatibility rules. Shared live-feed
translation follows the global text connection, rather than a particular team.

## Existing installations

This change adds Alembic migration `0017`. Back up the intended database and its
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
Human review and the wider representative evaluation remain necessary; the
two replay cases do not measure general factual accuracy or live retrieval.

See [evaluation instructions](../backend/evaluations/README.md) and
[connection design](AI_CONNECTIONS_PLAN.md).
