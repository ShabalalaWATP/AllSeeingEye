# ADR 0013: native Amazon Bedrock connections

Status: accepted, 6 September 2026.

## Decision

Add an explicit `bedrock` provider alongside the existing `openai_compatible`
protocol. Keep the administrator configure, test and confirm workflow, encrypted
credentials and global/team assignments. Dispatch each captured request by its
provider. Never infer a protocol from a hostname or fall back to another provider
after failure.

Use the regional native Converse endpoint with a Bedrock bearer API key. Restrict
the destination to canonical HTTPS `bedrock-runtime.<region>.amazonaws.com` roots.
Encode the selected model or inference-profile identifier as one URL path segment.
No AWS SDK, IAM credential discovery, role assumption or credential renewal is
introduced. Model entry is manual because native catalogue discovery is a separate
AWS control-plane capability.

Send structured outputs using Converse `outputConfig.textFormat`, with a projected
copy of the application's schema that removes constraints AWS does not support.
Keep original schemas and application output validation authoritative. Reject
unsupported response blocks, incomplete output and malformed usage. Discard native
reasoning blocks rather than storing them. Retain bounded response size, concurrency
and deadlines, explicit credentials, no redirects and sanitised errors.

Bedrock text profiles use provider-default reasoning and temperature 0 to 1.
All native text stages honour the configured completion budget, capped at 32,000
tokens, because provider-default reasoning can consume it even without an explicit
effort setting. Small legacy stage caps must not silently replace the tested budget.
Embeddings remain separate. Model compatibility is account-specific and requires
the administrator's saved-configuration test. A successful small probe is not a
research-quality evaluation or proof that every larger schema fits every model.

## Compatibility and consequences

Migration `0018` defaults legacy profiles to OpenAI-compatible. Their configuration
hash bytes must remain unchanged so previously tested assignments continue to
resolve. Bedrock hashes include a provider marker. Frozen report routing records
include the provider; historical records without it decode as OpenAI-compatible.

Encrypted credentials use text storage with a 16,384-character application input
bound. AWS model identifiers allow up to 2,048 characters, including inference-profile
ARNs, so both profile and report columns expand. OpenAI-compatible profile inputs
retain their previous 120-character limit. Downgrade refuses incompatible provider
rows, values that cannot fit the previous schema, or new provider-bearing frozen
routing records that the previous strict reader cannot decode. All refusal checks
precede column changes; immutable report history is never rewritten for downgrade.

Operators must renew expiring Bedrock keys themselves through a replacement
connection and the test/apply flow. Existing account model access, regional support,
permissions and inference charges remain AWS concerns. Development uses synthetic
HTTP responses and disposable databases; a live AWS test is a separate operator step.

## References

- [Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Inference settings](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InferenceConfiguration.html)
- [API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
- [Operator flow](../AI_CONNECTIONS_OPERATIONS.md)
