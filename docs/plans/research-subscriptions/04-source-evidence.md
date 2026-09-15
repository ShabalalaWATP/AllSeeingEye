# Packet 4: source relevance, depth and honest coverage

Goal: get better evidence for the actual question within bounded resource use. Source names, URLs, model agreement and repeated articles are not interchangeable with independent supporting evidence.

## E00: early capability inventory contract

Dependencies: R02. Execute before R03 and E01. Ownership: existing source inventory/requirements contracts and offline capability fixtures only.

Inventory current executable capability IDs, scope/language/date support and readiness without printing credentials. Define typed bundle references for existing capabilities and separate unavailable-gap records for proposed/unimplemented routes. A gap is not an executable provider ID. R03 validates presets against this registry and discloses missing coverage. Do not add connectors, signups or live calls in this task; E03 owns those. Test bundle resolution, unknown-ID rejection, disabled-source handling and capability-versus-origin counts. This separation removes a dependency cycle between presets and source implementation.

## E01: requirement-ranked source allocation

Dependencies: C01, R04, E00. Ownership: `application/research/collection.py`, preview/planning/budget policy, `container/research_feeds.py` integration and tests. Create focused planner modules rather than enlarging the container.

Replace fixed feed-family order with deterministic capability-aware allocation:

1. Filter by current scope, provider support, source enablement, permissions, language/date support and requested source policy before ranking. Preserve reasons for each exclusion.
2. Rank against requirement IDs, subject, geography, language and primary-content/data capability. Use explicit versioned weights and tie-breaking, not an opaque model-only ordering. A model may propose source/tasks from the authorised registry; deterministic rules admit them.
3. Allocate in passes: highest-priority required questions, relevant primary evidence, useful original/local-language evidence, then diversified coverage. Diversity is publisher/origin diversity, not a count of RSS variants.
4. Reserve part of the existing source-operation ceiling for post-draft work: Basic 0, Deep 4, Advanced 6. Reserve at least one suitable primary operation in Basic, two in Deep and three in Advanced if eligible. Local-language coverage gets one/two operations in Deep/Advanced when useful and available. Reservations can satisfy the same requirement and do not exceed the total cap.
5. If a reservation cannot be used, record why and reallocate deterministically. Do not dispatch unrelated official sources merely to satisfy a primary quota.
6. Use bounded concurrency only where the current source guards/rate limits allow it. Initially at most two independent public source requests, one per provider host; selection/receipts must be deterministic regardless of completion order. Never hold DB locks across these requests.

Replace the single absolute monotonic collection deadline with a persisted phase-allocation ledger before adding post-draft collection. Define collection time as elapsed time within active acquisition phases (concurrent calls share that phase's wall clock), excluding model drafting and queue/pause time. Basic gets 45 seconds initially; Deep gets up to 135 seconds initially and 45 reserved for challenge; Advanced gets 180 plus 60. Original retrieval is part of those allocations. Persist cumulative operations/items/active milliseconds across resume; never persist a process-local monotonic timestamp as a resumable deadline. Reserve phase allowance before dispatch, refund only known unused time and conservatively retain an unknown interrupted reservation. The existing bounded worker attempt deadline remains an additional limit. Unused challenge allowance is not a licence to repeat initial acquisition after its budget is exhausted.

Reserve retained collection-item capacity too: Basic's 200-item allowance needs no challenge reservation; Deep reserves at least 8 of its 800 items and Advanced at least 12 of its 1,000. Initial acquisition cannot consume those reserved slots. Final selected-evidence slots are a separate bound defined in E05. Test a completely filled initial allocation followed by successful retention and selection of fresh counterevidence without exceeding either cumulative ceiling.

Account for the existing separate fresh-web discovery path explicitly: its model calls use R04's job ledger, and its tool/network work uses a named bounded web-discovery allocation with receipts under the total execution plan. Generated web results still need E02 acquisition to become evidence. Preview shows this optional allocation separately; it cannot silently reset the main source-operation/time budget.

Receipts need separate counts: catalogue capabilities, eligible operations, planned/attempted operations, transport requests, returned items, retained items, selected items and estimated origin groups. Include requirement coverage, date/language coverage, unsupported/private/disabled/budget/timeout reasons and retrieval timestamps. “Searched all” is prohibited when a budget stopped collection.

Tests: the audited Ukraine/drone fixture admits relevant MOD/primary tasks ahead of unrelated finance/cyber feeds; cyber prioritises relevant CERT/vendor/exploitation data; economy prioritises statistical releases; source exclusion and private terms survive; results/receipts are stable with reversed completion order; reservations do not overspend. Compare against curated expected sources in V01, not only snapshots of the ranking formula.

## E02: permitted original documents and exact passages

Dependencies: E01. Ownership: existing research import/safe-HTTP adapters, frozen evidence metadata, passage extraction and collection integration.

Read `adapters/research/news.py`, `publisher.py`, `application/reports/fresh_web_research.py`, `domain/web_research.py`, and current research import/selected-original/SSRF/isolated-parser modules.

Implement a bounded follow-through tool for selected discovered HTTP(S) pages/documents:

- Input is an admitted provider result/URL with source provenance and requirement IDs, not arbitrary network access chosen by generated text. Validate destination at dispatch and every redirect with the existing public-source transport guard, including DNS rebinding protections. Never use the more permissive administrator LLM endpoint client.
- Enforce existing restrictive request/redirect/time/byte/decompression/content-type caps; introduce tighter defaults where absent, document them in one policy and regression-test boundary values. Use the isolated parser for documents. No executing page scripts, embedded macros or model-generated code.
- Respect source terms, rate limits, robots policy where applicable and permitted retention. No paywall/login bypass. Failed acquisition retains a labelled headline-only record and reason; it must not invent a passage.
- Preserve canonical and requested URL, source/issuer, publication/update/retrieval timestamps with provenance, original language, content hash, document version, licence/retention policy and stable passage IDs with offsets/page references.
- Keep original passages and translated derivatives distinct and linked. Model summaries and generated fresh-web context cannot become original evidence. A discovered web link becomes citable evidence only after actual permitted retrieval and provenance capture.
- Persist selected evidence/passages through existing authorised freezing/original-asset mechanisms. Keep excerpts scoped and byte-bounded; do not add whole-web archiving to report checkpoints.
- Corrections create new source versions linked to previous hashes. Current corrections never silently replace frozen historical passages.

Initial follow-through maxima: 2 documents Basic, 6 Deep, 10 Advanced, included within the total external-operation/time/resource policy. The actual transport request count is metered separately, including redirects. Optional work stops before dispatch if remaining allowance cannot accommodate it. A provider with a stricter limit wins.

Tests: SSRF through direct and redirected local/private addresses, oversized/decompression payload, parser timeout, malicious HTML, missing publication date, repeated URL corrected content, translated passage origin, expired/revoked original and passage citation integrity. Verify original content can be opened from a report only under current access and source-retention rules.

## E03: source capability inventory and structured research bridges

Dependencies: E00, E02. Ownership: source inventory/requirements and typed research adapters. Integrate existing dashboard services through ports, never frontend scraping or unbounded database access.

Create a versioned capability matrix with provider ID, family, scope/date/language support, discovery versus full text/structured content, key/approval/local-dataset requirement, rate/retention policy, freshness, last test and supported briefs. Expose user-relevant readiness without credential values.

The audit found 119 catalogue entries, not 119 independent searched publishers. It checked credential presence, not working access. Recheck current state; do not repeat signups already completed or overwrite stored keys.

| Priority | Work and acceptance |
| --- | --- |
| Existing news/world/UK/regional feeds | Map every current research capability, identify duplicated origins, improve query/time/language coverage and primary follow-through before adding more generic RSS. Retain regional and non-English sources. |
| Cyber/network | Bridge typed current CTI/advisory/exploitation records, ATT&CK reference context, IODA and Cloudflare Radar where available. Preserve interval, geography granularity and metric definitions. No inference from network anomaly to attributed attack. |
| Economy | Bridge existing economic series/filings/news; add missing official ONS and ECB routes after current documentation verification. Reuse supported World Bank/IMF/OECD/national routes rather than duplicating them. Preserve units, frequency, seasonal adjustment, vintage and revision dates. |
| Conflict/humanitarian | Recheck ACLED access, ReliefWeb approved API app identity, existing ReliefWeb RSS/UN/IFRC routes and conflict sources. Differentiate observation, actor claim and coded media signal. |
| Companies/trade/policy | Recheck Companies House, current permitted UK sanctions/OFAC datasets, SEC/registry routes and AidData catalogue setup. Missing dataset registration is different from missing API key. |
| Environment/academic/technical | Reuse OpenAQ, OpenAlex and certificate-transparency capability already configured where relevant. Bridge hazard/space/mobility/infrastructure context through authorised typed adapters with coverage receipts. |
| Connectivity research | Recheck OONI data-use acknowledgement and supported IODA/Cloudflare routes. A dashboard key being present does not make a research adapter exist. |

For each provider: verify official documentation and terms at implementation time; identify current route/auth/limits; add offline contract fixtures; run a minimal read-only smoke test using configured secrets when available; record endpoint/date/status/count/limitations with secrets redacted. Do not store keys or token-bearing URLs in fixtures. Missing credentials create a precise admin setup instruction and an unavailable capability. Continue independent work; do not fabricate a live pass.

Structured result schema: dataset/source/version, series or observation ID, query and retrieval interval, observation time/period, numeric value and unit, geography/precision, dimensions, uncertainty/missing markers, revision history and evidence reference. Validate types/bounds and distinguish null from zero. Only selected records/aggregates are frozen into the report evidence packet. Raw dashboards or model-generated paragraphs are not a substitute.

Done when all twenty preset bundles resolve to usable current capabilities or explicit gaps, and supported structured data can be selected/cited by one-off and scheduled research. “All possible sources” remains an invalid promise.

## E04: incremental history, retention and corrections

Dependencies: S04, E03. Ownership: selected subscription collection store/ports/adapters, scheduled acquisition jobs and retention ADR.

This changes the current mostly transient live-data boundary. Write an ADR before implementation: a bounded, permission-scoped research index for active selected briefs, separate from transient global map events. Do not silently persist the entire global feed stream.

Subscriptions collect eligible new metadata/permitted excerpts between publication dates. Use existing provider polling/caches where possible, with per-source cursors/watermarks, overlap, request budgets and receipt history. Persist enough source versions and references to build longer interval reports, while respecting each source's allowed storage. Long-term content requiring a licence is not cached simply because an annual edition would benefit.

Initial configurable ceilings, evaluated by V02: metadata index target up to 400 days where permitted; 50,000 records and 256 MiB per owner; 2 GiB aggregate app index; permitted extracted content defaults to 30 days unless selected frozen evidence policy authorises longer retention. Whichever limit is reached first wins. Eviction records coverage loss. Historical provider APIs can fill gaps within budgets; an annual report may remain partial if retained content is insufficient.

Acquisition cadence is source-specific and independent of publication cadence. Start at the slower of the source's minimum interval and hourly collection for selected news/updates; use native daily/slower cadence for series releases. Share public provider fetches only where access, licences and query privacy permit it. Never expose one user's private keywords through another user's cache/results or global catalogue metrics. Public immutable document bytes can be deduplicated internally while access grants stay scoped.

Keep incremental acquisition's resource reservations visible alongside publication costs. Cap concurrent acquisition at two operations and honour existing per-source/global quotas. A disabled/paused subscription stops its own future collection; shared public fetches only continue for other authorised consumers.

Store observation/publication/update/first-seen/retrieval dates separately; record cursor advances only after successful persistence. Source outage, restart, duplicate page, correction and late arrival must not silently lose intervals. Fingerprints include source version/origin, so a correction is not dismissed as a repeated URL.

Tests: restart mid-page, atomic cursor persistence, repeat fetch, permitted/forbidden retention, byte/item/age eviction, tenant isolation, source disablement, late reports, content correction, annual requested interval versus retained coverage, and archive cleanup races with authorised report freezing.

## E05: checkpointed gap and counterevidence collection

Dependencies: E01–E04, R04, existing claim IDs. Ownership: durable production/replanning/challenge stages and evidence-expansion schema.

Extend the existing orchestration, not an unbounded agent loop:

1. Initial collection freezes evidence packet v1, its stable IDs, query, requirements and receipts.
2. After initial drafting, review uncovered requirements and consequential judgements. Propose a bounded set of admitted queries specifically capable of disproving/changing those judgements.
3. Use at most one additional collection pass in Deep and Advanced from the reserved 4/6 operations. Basic reviews existing evidence and truthfully reports that it did so. An unavailable provider/budget produces an explicit gap, not a fictional contrary-search receipt.
4. Persist the task plan before dispatch. Known completed collection/model stages are reused on resume. All reservations and unknown results follow S03 and existing job safeguards.
5. Create packet v2 by retaining all v1 IDs and adding stable new IDs. Never renumber old citations or overwrite v1 content. Hash expansion input, parent packet, added passages and source/permission state.
6. Redraft only affected sections/judgements once, then revalidate synthesis and claim support. Do not run repeated debate agents or count their agreement as corroboration.
7. Final quality notes distinguish existing-evidence review, attempted fresh challenge, successful new counterevidence and unresolved gaps. All stages have receipts and stop reasons.

Before v1 selection, reserve final evidence capacity for expansion: Basic 0 additional slots, Deep 8 and Advanced 12, so initial public selection is at most 24/40/68 and final selection remains at most 24/48/80. Any combined wire/decoder limit, including the current 100-item bound where applicable, must still pass validation with private evidence. Do not silently raise it or discard previously cited v1 items to fit additions. If evidence cannot fit, retain the unselected acquisition receipt and explicit assessment gap.

Version checkpoint expansion and reuse explicitly. Current staged fingerprints hash the whole packet, so stable citation IDs alone do not permit section reuse. Give each reusable section a fingerprint of its exact selected inputs, requirement text and policy/model settings plus validated parent-packet lineage. Reuse only unchanged sections; invalidate affected sections and final synthesis. Provide backward readers for existing packet schema versions and test resuming pre-change jobs without rerunning completed paid stages. Initial collection/replanning keeps its existing two-pass limit; post-draft challenge is a separate versioned expansion phase, not an illegal third `ResearchBatch` pass. R04's total stage ledger includes both phases and all redrafting/adjudication.

Keep each checkpoint within existing byte caps by using durable references to authorised frozen packets, not copying every full article into each stage. Any new persistence/reference type must retain source-disable and final-release checks.

Tests: checkpoint resume at every boundary, source failure, same-origin contrary article, genuine disconfirming passage, no relevant counterevidence, exhausted budget, invented task/source ID, prohibited scope expansion, private-term injection and stable v1 citations after v2. Done when a durable Deep/Advanced job actually tests its draft judgements with new eligible evidence and reports accurately when it cannot.
