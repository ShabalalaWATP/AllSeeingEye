# Native Bedrock: focused implementation review

Date: 6 September 2026.

This manual review covers the native Bedrock working-tree change, including
credential handling, administrator controls, provider dispatch, frozen report
metadata and migration `0018`. It is not a full repository scan or production
certification. Tests used synthetic credentials, HTTP transports and disposable
SQLite databases with `.env` loading disabled. No operator database, real key or
live model endpoint was used.

## Finding fixed

**Low, operator-triggered availability: downgrade could leave unreadable report
history.** The original `0018` downgrade checked live profiles and column lengths
but omitted the new `provider` field in
`report_versions.analysis.model_routing.profiles`. The previous release's strict
reader rejects that field, even for short OpenAI-compatible identifiers. An
operator could therefore downgrade successfully and lose application access to
those historical records. No remote trigger was established.

The failure was reproduced with the actual previous-release codec and a current
OpenAI routing record. Migration
[`0018_llm_providers.py`](../../backend/alembic/versions/0018_llm_providers.py)
now checks history in bounded 100-row keyset pages and refuses incompatible or
unreadable routing before any DDL. It does not rewrite immutable history. Tests
verify legacy history can still downgrade, while new OpenAI history, native
history without a live native profile, and unreadable history refuse unchanged.
A separate check verified refusal for a record on the second page.

No other concrete security vulnerability remained in the reviewed change.

## Boundaries checked

| Boundary | Source and observed behaviour |
| --- | --- |
| Credential destination | `domain/bedrock.py` accepts canonical regional HTTPS runtime roots. The adapter validates again, encodes the entire model identifier as one path segment, supplies per-request bearer credentials, overrides inherited authentication and forbids redirects. |
| Saved keys and authority | Profile input limits keys to 16,384 characters; ciphertext uses text storage. Provider or credential destination changes require an explicit replacement key. Existing administrator, original-session, post-network authorisation and revision-bound test/apply checks remain in place. Native discovery rejects before decryption or HTTP. |
| Provider and scope | Explicit dispatch has no provider fallback. Every text request captures its profile's provider. Team/global assignment rules and separate embeddings remain unchanged. Native embeddings and explicit reasoning settings reject. |
| Untrusted responses | A two-request semaphore, total deadline, 4 MiB streamed response cap and JSON depth limit bound processing. Redirect and compressed responses reject before body reads. Refused, incomplete or unsupported content rejects; reasoning blocks are discarded. Transport/status errors do not echo keys, URLs or response bodies. |
| Structured output | `bedrock_schema.py` projects a copy, bounds traversal and rejects references and unsupported additional-properties schemas. Original application schemas and output validators remain authoritative; a production-path regression repairs invalid model output. |
| Compatibility | Default OpenAI configuration hashes retain their previous bytes and tested bindings. Frozen metadata contains provider identity, without credentials or endpoints. Old providerless metadata decodes as OpenAI-compatible without rewriting stored JSON. Native model identifiers fit the expanded profile and report columns. |

## Verification and limits

The reviewer ran ten focused test modules covering native wire behaviour, limits,
production generation, profiles, key boundaries, frozen persistence, routing
codecs, propagation and migrations: **105 passed, 9 skipped**. The skips were
PostgreSQL variants. The final second-page SQLite regression also passed. Coverage
was not measured in this run. The persistence worker separately reported all 18
SQLite/PostgreSQL migration cases passing on its disposable PostgreSQL server.
An independent endpoint check accepted three canonical roots and rejected 13
malformed or alternate destinations. No new SAST, dependency or container scan
was performed as part of this focused review.

The ADR and operator instructions match the reviewed implementation. AWS documents
[bearer API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html),
the [Converse contract](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
and a [structured-output subset](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).
Real account permissions, regional/model availability, expiry and complete
research-schema compatibility still need the operator's deliberate test. The app
does not renew credentials, discover native models or provide SigV4. The standalone
evaluation harness remains OpenAI-compatible only. Existing deployment and
server encryption-key protection requirements continue to apply.
