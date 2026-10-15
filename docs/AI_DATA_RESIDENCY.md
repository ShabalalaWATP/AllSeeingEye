# AI regions and data residency

This guide describes controls reviewed on **14 October 2026**. The application
routes requests; it does not certify provider location, enforce an installation-wide
residency policy, or negotiate contracts. Finland hosting and standard API terms do
not establish EU-only processing or zero retention. Record actual choices in the
[processor register](compliance/PROCESSORS_AND_TRANSFERS.md).

## Inventory every AI route

| Route                             | What must be checked                                                                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Text, translation and assessment  | Global connection plus every personal/team override. Shared background work uses global routing.                                                  |
| Embeddings and evidence reranking | Separate global embeddings profile, independent of text assignments. It receives selected report text, search queries or bounded evidence.        |
| Fresh web research                | Currently requires exact global OpenAI endpoint; regional/custom/Bedrock profiles return unsupported without fallback.                            |
| Private documents and images      | Extracted text and inline sanitised images can leave the host even though these adapters do not upload provider Files/vector stores.              |
| Queued/in-flight work             | Work already using captured settings can complete with the earlier provider. Changing a default does not relocate prior requests or saved copies. |

Source: [routing](../backend/src/ase/application/model_routing.py),
[embeddings](../backend/src/ase/adapters/llm/embeddings.py),
[fresh web admission](../backend/src/ase/application/reports/fresh_web_research.py)
and [image limits](../backend/src/ase/domain/llm.py).

## Regional OpenAI connection

According to [OpenAI's current data controls](https://developers.openai.com/api/docs/guides/your-data),
non-US residency requires approval for abuse-monitoring controls and a Modified
Retention amendment. Eligible projects/keys must use supported models, endpoints
and modalities. Europe covers the EEA and Switzerland, not Finland alone. System
data and third-party services have separate treatment. Standard abuse-monitoring
logs can persist up to 30 days, subject to exceptions; `store: false` does not
remove that retention. Image/file safety exceptions can also apply under Zero
Data Retention. Check the operative provider terms before making a commitment.

1. Obtain the required account approval and project settings; record their scope
   privately. The installation's confirmed standard terms do not establish them.
2. Open **Administration > AI connections** and select **Custom OpenAI-compatible**.
   The ordinary **OpenAI** preset fixes the global URL. Enter
   `https://eu.api.openai.com/v1` with the appropriate project key, eligible model
   and supported Chat Completions settings. Never put a key in the URL.
3. Test the inactive connection and representative required text/image workflows.
   The small connection probe can incur a charge and proves neither geographic
   processing nor every report schema.
4. Apply the global assignment and inspect every personal/team override. Configure
   embeddings separately. Verify the effective destinations without logging content
   or credentials; retain provider-side eligibility evidence as well.
5. Keep fresh web research unused for a regional-only policy. This app currently
   offers neither regional native web search nor regional native Responses.
6. Plan outstanding work and prior stored data explicitly before claiming cutover.

The [Responses adapter](../backend/src/ase/adapters/llm/openai_responses.py)
activates only for exact global `https://api.openai.com/v1` with Max reasoning.
Regional URLs use Chat Completions; regional Max support is unverified. Native
Responses sends `store: false`; ordinary compatible Chat Completions omits `store`.
Endpoint validation checks URL safety, not residency or account eligibility.

## Amazon Bedrock alternative

Bedrock is supported by the code but was not a verified provider of the installation.

1. Select a source region and exact model or inference profile supporting Converse
   and strict structured outputs, plus images where required. Confirm model access,
   applicable terms and narrowly scoped `bedrock:InvokeModel`/Bearer permissions.
   See [AWS prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.html)
   and [structured output support](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).
2. Inspect every profile's destinations using `GetInferenceProfile` from each
   intended source region and its `models[].modelArn` values. A regional endpoint
   can route through a geographic or global inference profile. The app does not
   check those destinations. See [profile routing](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)
   and [global inference](https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.html).
3. Verify model/account/region [retention settings](https://docs.aws.amazon.com/bedrock/latest/userguide/data-retention.html)
   and [invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html).
   Enabled logging can copy inputs/results/images to CloudWatch/S3; inspect their
   retention and replication too. The app does not configure these controls.
4. Choose **Amazon Bedrock**, enter the region, matching Bearer API key and exact
   model/profile ID. Leave reasoning at provider default, test, then assign all
   intended audiences. Native Bedrock profiles cannot supply embeddings; configure
   their independent route or leave embedding features unconfigured.
5. Resolve credential renewal. The adapter supports neither SigV4/instance roles
   nor automatic renewal. AWS recommends short-term keys for production; these
   last no longer than the originating session, up to 12 hours. Manual replacement
   remains necessary in this integration. See [API key guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html).

Implementation: [Bedrock endpoint contract](../backend/src/ase/domain/bedrock.py)
and [native adapter](../backend/src/ase/adapters/llm/bedrock.py).
For a local/custom compatible model, verify the actual backend endpoint, upstream
forwarding, model licence, logs and backups. A local-looking URL alone is not proof
that requests stay on the machine.

## Separate disclosures and acceptance evidence

AI routing does not relocate email, browser push, source/search queries, map/media
requests, exports or backups. Wayback capture is separate; set
`ASE_ARCHIVE_ENABLED=false` if the assessed policy excludes it. A downloaded report
creates a recipient-controlled copy without requiring another model request.
Review optional remote rendering and off-site backups as separate destinations.

Before a regional claim, record: approved provider/account/project scope; effective
URLs/models/profile destinations for every route; representative test results;
log/storage settings; queued-work disposition; separate recipients; and dated
operator acceptance. Keep credentials and research content out of this evidence.
No provider changes, live model tests, new agreements or regional cutover were
performed in preparing this guide.
