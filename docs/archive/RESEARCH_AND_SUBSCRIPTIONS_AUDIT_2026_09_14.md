# Research and Subscriptions audit

## Assessment

Research has a substantial foundation for producing analyst-reviewed OSINT reports. It includes public-source collection, private inputs, multilingual query preparation, bounded model planning, preserved evidence, staged report jobs, source grading, probability language, confidence constraints and professional exports. Subscriptions retain useful previous-report context and content fingerprints, and their calendar recurrence handles monthly and annual schedules.

The main weaknesses are relevance allocation, source depth, consistency between execution paths and unattended reliability. Several concrete defects make an unqualified claim that everything works unjustified. Adding more source names or increasing report length would leave those defects intact. The priority is to make the existing collection and assessment machinery work consistently, then improve the breadth of evidence and the usability of the research brief.

This assessment covers the current working tree on 14 September 2026. Findings distinguish reproduced defects, code-confirmed limitations, product recommendations and unverified operational behaviour. Existing unrelated changes were preserved. No application source was changed as part of the audit.

| Question | Assessment |
| --- | --- |
| Is the Research structure good? | Strong technical foundations, but the brief and collection plan need a clearer user journey. |
| Is the search good enough? | Useful for bounded discovery and drafts. An evidence-ranking defect and fixed provider ordering need repair. |
| Is Advanced genuinely deeper? | It has larger collection, evidence and prose allowances. Final analytical structure remains restrictive across all tiers. |
| Does it search every possible source? | No. Registered capability, supported query, connected provider and attempted search are different states. |
| Is everything working? | No. Reproduced defects and execution-path differences are listed below. Full current live-source/model acceptance is also absent. |
| Are Subscriptions as capable as Research? | No. Their configuration and execution have not caught up with the durable Research workflow. |
| Are there enough presets? | No. Existing report formats and three regional shortcuts do not provide a useful topical subscription library. |
| Is the military probability yardstick used? | Yes. PHIA vocabulary and separate confidence grading exist. They do not establish calibrated probabilities or verified claims. |
| Would agentic features help? | Yes, especially targeted collection, contradiction checks and reassessment. The app already contains bounded planning and replanning. |

## 1. Findings to repair first

### 1.1 Exact operator search terms can be lost during evidence ranking

**Confirmed defect, high confidence.** Collection honours the operator's explicit research terms. Final evidence selection instead uses the earlier direction model's terms or original job terms, plus supplementary task terms. It does not reliably use the effective collection query.

A deterministic reproduction placed 30 unrelated records and one direct answer in the candidate pool. The operator and runtime query both requested the direct answer's distinctive term. Basic selected 24 records and excluded that answer. This occurred with stale direction terms and with no direction object.

The fix should preserve the final authorised query through collection, ranking and reporting, including operator terms, accepted revised terms and multilingual variants. A regression should prove that a direct match survives a crowded candidate pool. This is the most immediate Research correctness repair.

Evidence: [collection terms](C:/AlexDev/OSINT/backend/src/ase/application/reports/production_collection.py:58), [final selection terms](C:/AlexDev/OSINT/backend/src/ase/application/reports/production_selection.py:60).

### 1.2 Provider order spends the search allowance before the most relevant sources

**Confirmed limitation, high confidence.** Public feed families are interleaved in a fixed order. Collection executes eligible tasks serially until its allowance is exhausted. Provider eligibility does not imply that the provider will be searched.

For an English-language, general Ukraine/drone question over 30 days, an offline planning probe produced 86 provider tasks, of which 63 supported the scope. The first six supported tasks were Google News, FCDO, BBC World, BBC YouTube, BBC Business and NCSC threat reports. Those six can consume Basic's entire provider allowance before MOD news is reached. This is a probe of source ordering, not a statement about what any live provider returned.

Source choice should be ranked against the question and its intelligence requirements, with reserved capacity for relevant primary sources, local-language coverage and counterevidence. The preview should show what is expected to be searched within the budget. Existing receipts already disclose unsupported, empty, unavailable and budget-exhausted attempts; that transparency should be made easier to understand.

Evidence: [fixed family ordering](C:/AlexDev/OSINT/backend/src/ase/container/research_feeds.py:48), [collection execution](C:/AlexDev/OSINT/backend/src/ase/application/research/collection.py:105).

### 1.3 Interactive Deep and Advanced do not perform fresh post-draft challenge collection

**Code-confirmed execution difference, high confidence.** Interactive Research uses durable jobs and staged report drafting. Its later challenge stage reviews frozen evidence and explicitly records that no additional contrary-source collection occurred. The older synchronous pathway can conduct fresh challenge collection.

There can still be challenge tasks during initial planning. The missing capability is collection directed at the actual judgements made after drafting. An existing source packet may lack the evidence needed to test those judgements.

Add a checkpointed challenge-collection stage, with a reserved allowance and stable evidence identities. Any expanded evidence packet must be versioned before affected judgements are redrafted. Until this exists, the user-facing description should distinguish review of existing evidence from a new counterevidence search.

Evidence: [durable job execution](C:/AlexDev/OSINT/backend/src/ase/container/report_job_execution.py:67), [production branch](C:/AlexDev/OSINT/backend/src/ase/application/reports/production.py:214), [frozen challenge boundary](C:/AlexDev/OSINT/backend/src/ase/application/reports/frozen_challenge.py:17).

### 1.4 A failed report can be recorded as a successful subscription run

**Code-confirmed defect, high confidence.** Report production can return a saved failed version. The subscription producer discards that version's outcome and returns the report ID. The runner then records no error and advances the schedule. The attention filter only considers the schedule error field, so it can miss failed and review-required reports.

Return a structured run outcome and show distinct states: completed, review required, partial coverage, failed and blocked. A report existing in the database must not be sufficient proof of a successful edition.

Evidence: [version status](C:/AlexDev/OSINT/backend/src/ase/application/reports/production_version.py:67), [discarded version](C:/AlexDev/OSINT/backend/src/ase/container/features.py:339), [runner outcome](C:/AlexDev/OSINT/backend/src/ase/application/schedules/runner.py:47), [attention filter](C:/AlexDev/OSINT/frontend/src/features/reports/SchedulesSection.tsx:99).

### 1.5 Subscription retries, missed periods and edits can lose useful work

**Reproduced behaviours, high confidence.**

- A failed annual run on 14 September 2026 books the next normal run for 14 September 2027. There is no separate bounded retry schedule.
- A daily subscription five days overdue still requests a 24-hour window. It does not automatically cover the interval since the last successful edition.
- Renaming an overdue daily subscription recalculates its next run and moves the pending slot to tomorrow.

Preserve the original due slot, separate retry timing from publication cadence, track the last successful evidence cutoff, and support bounded catch-up with deliberate overlap. Name changes should not reschedule work. Offer an explicit choice between a rolling snapshot and changes since the last successful edition.

Evidence: [retry/cadence handling](C:/AlexDev/OSINT/backend/src/ase/application/schedules/runner.py:49), [fixed lookback](C:/AlexDev/OSINT/backend/src/ase/application/schedules/report_request.py:17), [update rescheduling](C:/AlexDev/OSINT/backend/src/ase/application/schedules/manage.py:186).

### 1.6 Scheduled runs bypass the durable Research job system

**Code-confirmed architectural gap.** The subscription runner directly awaits full report production in sequence inside the API process. It lacks a durable subscription-edition identity, claim, lease and checkpoint. An overlap probe invoked production twice. A crash after saving a report but before recording the schedule's completion can also leave work eligible to run again.

The documented deployment supports one API process, so multiworker behaviour is a scaling constraint rather than evidence of a currently deployed multiworker failure. Crash recovery and serial blocking still matter in that supported deployment. The scheduler also starts only when the feed subsystem is enabled.

Reuse the existing durable report-job engine. Each edition should have an idempotent identity based on subscription and due slot, a bounded retry policy, one current job and an immutable run history. Scheduling should enqueue work, leaving collection and drafting to the existing workers.

Evidence: [direct production](C:/AlexDev/OSINT/backend/src/ase/container/features.py:332), [serial runner](C:/AlexDev/OSINT/backend/src/ase/application/schedules/runner.py:41), [late stale check](C:/AlexDev/OSINT/backend/src/ase/adapters/persistence/schedules.py:202), [startup coupling](C:/AlexDev/OSINT/backend/src/ase/main.py:27).

### 1.7 Material review details do not all reach the final report product

**Code-confirmed presentation gap.** The canonical document builder does not project the newer all-judgement challenge or citation-check records. It suppresses the older advocacy section when the newer challenge object exists. These newer details remain available in the supporting workspace, but their substantive concerns can be absent from the main reader and Word/PDF product.

Some model-cited opposing evidence is already presented, so this does not mean every contradiction disappears. The repair is to preserve material contrary arguments and unresolved citation concerns beside their affected judgements. The interactive reader has a review-status banner; exported review-required documents need equally prominent status near the beginning.

Evidence: [advocacy suppression](C:/AlexDev/OSINT/backend/src/ase/application/reports/document.py:110), [canonical section assembly](C:/AlexDev/OSINT/backend/src/ase/application/reports/document.py:193), [supporting analysis](C:/AlexDev/OSINT/frontend/src/features/reports/ReportSupportingWorkspace.tsx:149).

### 1.8 Historical follow-up has a broken user journey

**Code-confirmed defect.** A non-area historical report offers the ordinary follow-up action, but the follow-up request builder rejects recorded-time reports. Retrying the parent load cannot remove that restriction. Disable the unsupported action with an explanation or implement preservation of the historical period.

Follow-ups also bind the latest parent version, even when opened from an older version. This is disclosed on the follow-up screen, so it is a product limitation rather than a hidden version change. An explicit choice between the viewed version and latest version would improve reproducibility.

Evidence: [follow-up action](C:/AlexDev/OSINT/frontend/src/features/reports/ReportPage.tsx:211), [historical restriction](C:/AlexDev/OSINT/frontend/src/features/research/followUpScope.ts:44), [latest-version disclosure](C:/AlexDev/OSINT/frontend/src/features/research/FollowUpSummary.tsx:42).

## 2. What the search actually covers

The local research catalogue exposes **119 entries**: 46 news, 9 social, 22 economic, 23 cyber, 12 political, 1 space, 4 humanitarian and 2 disaster. These are capability entries, including language variants and private-input capabilities, rather than 119 independent publishers or verified live connections.

For a particular question, supported provider tasks are a smaller set. Actually attempted tasks are smaller again. Returned records, retained candidates and the final cited evidence packet are separate counts. The interface should consistently distinguish these stages.

| Evidence route | Current capability | Material limit |
| --- | --- | --- |
| Publisher, official, regional and cyber RSS | Current feed snapshots, local phrase matching, attribution and dates | Predominantly headlines/snippets; no complete historical search or automatic full-article reading |
| Google News | Question-specific multilingual RSS discovery | Undocumented RSS mechanism; first 200 items considered; linked articles are not fetched |
| Retained public feeds | Up to 1,000 live context records for applicable public research | Availability, categories, dates and geography constrain inclusion; this is not a historical archive |
| Company and domain research | SEC metadata, selected SEC filing import, Companies House, GLEIF, RDAP, DNS and certificate transparency | Exact identifiers, credentials, pagination and source-specific limits |
| Scholarly and public records | OpenAlex, Crossref, Parliament, World Bank, procurement | Metadata and bounded datasets; topic/time support varies |
| Geographic research | Retained precise events, USGS, EONET, OpenAQ and selected Copernicus footprints | Unsupported geometry and unknown dates remain gaps; footprints are not analysed imagery |
| Private inputs | Documents, images and limited media extraction | Bounded extraction; originals do not become verified claims merely because they were uploaded |
| Fresh web discovery | Optional native web context with attributed links | Separate bounded context; discovered pages are not automatically turned into checked E-labelled evidence |

Sources: [provider factory](C:/AlexDev/OSINT/backend/src/ase/container/research.py:86), [catalogue](C:/AlexDev/OSINT/backend/src/ase/container/research_sources.py:64), [retained context](C:/AlexDev/OSINT/backend/src/ase/application/reports/research.py:56), [publisher collection](C:/AlexDev/OSINT/backend/src/ase/adapters/research/publisher.py:73), [web evidence boundary](C:/AlexDev/OSINT/backend/src/ase/domain/web_research.py:160).

### Source readiness in the local configuration

A read-only settings probe found credentials present for OpenAlex, OpenAQ and certificate transparency. Companies House was not configured. OONI's use acknowledgement, AidData's catalogue and UK/US sanctions snapshots were absent. The optional ACLED and ReliefWeb reports API settings were also absent. ReliefWeb RSS is a separate route, so missing API access does not mean all ReliefWeb coverage is absent.

These are configuration-presence observations, not successful authentication or uptime tests. Cloudflare Radar and shipping credentials were present, but a dashboard connection does not automatically provide a query-compatible Research adapter. Existing retained events may contribute where eligible; service-specific aggregates and catalogues need explicit retrieval integration.

The most valuable source work is:

1. **Use the relevant existing sources more effectively.** Rank providers by question, entity, geography, language, historical reach and evidence role.
2. **Retrieve important primary content.** Follow selected discovery links through bounded, permitted retrieval. Preserve publication/event dates, exact passages, issuer, hashes and source lineage.
3. **Expose specialist structured datasets through Research.** Make Cyber and Economy data available through typed queries, with clear units, dates, attribution and source limits. Do not convert country-level cyber statistics into incident locations.
4. **Complete useful existing connections.** Prioritise the missing registries, sanctions data and humanitarian reporting according to the selected briefs.
5. **Extend official economic data where needed.** ONS exposes a developer API, and ECB provides statistical data and metadata through SDMX, including revision-aware queries. These are candidates for sourced chart and economic-analysis extensions, rather than substitutes for current market data. [ONS developer hub](https://developer.ons.gov.uk/), [ECB data API](https://data.ecb.europa.eu/help/api/data).

ReliefWeb's API now requires a pre-approved appname, so its connection needs the actual provider approval flow, rather than an arbitrary string. [ReliefWeb API parameters](https://apidoc.reliefweb.int/parameters).

For long-period subscriptions, collection frequency and publication frequency must be separate. An annual report assembled from current RSS feeds cannot reconstruct a year of missing coverage. Collect eligible evidence incrementally, retain it under the relevant source terms, and generate the annual product from that dated record.

## 3. Research depth and report structure

The three tiers have meaningful differences, but their names currently imply more analytical variation than the final schema provides.

| Tier | Provider-operation ceiling | Collection deadline | Collection-item ceiling | Final public evidence packet | Indicative report words |
| --- | ---: | ---: | ---: | ---: | ---: |
| Basic | 6 | 45 seconds | 200 | 24 | 500–900 |
| Deep | 24 | 180 seconds | 800 | 48 | 1,200–2,000 |
| Advanced | 32 | 240 seconds | 1,000 | 80 | 2,500–4,000 |

These are ceilings and targets, not guaranteed output, source independence or total completion time. Retained live context is a separate input, and private-input reports have a different evidence allowance. Model work adds time after collection. Evidence: [collection budgets](C:/AlexDev/OSINT/backend/src/ase/application/research/budget.py:36), [report depth](C:/AlexDev/OSINT/backend/src/ase/application/reports/depth.py:47), [evidence selection](C:/AlexDev/OSINT/backend/src/ase/application/reports/production_selection.py:39).

Staged drafting begins with at most six topics; output exhaustion can split those to twelve. Final synthesis is constrained to two key judgements, two alternatives, four assumptions and four collection recommendations across depths. That can compress a complex Advanced investigation into too few decision-relevant findings. Evidence: [section planning](C:/AlexDev/OSINT/backend/src/ase/application/reports/sections/planning.py:18), [synthesis limits](C:/AlexDev/OSINT/backend/src/ase/application/reports/sections/synthesis_contracts.py:27).

Retain the depth choices, but define them by work performed:

- **Basic:** answer the central question, identify the most important recent facts, explain the main limitation and give a short outlook.
- **Deep:** cover several intelligence requirements, obtain stronger primary evidence, build a sourced timeline, test alternatives and explain contradictions.
- **Advanced:** add multiple explicit hypotheses, structured counterevidence collection, selected quantitative analysis, scenario indicators and a reproducible evidence appendix.

The final reader should remain one coherent product: executive summary, key judgements, sourced findings, implications for the chosen audience, alternatives, outlook and indicators, material limitations and references. Tables and charts should appear when they answer a question. Calculations should be performed by deterministic tools with recorded inputs, units and methods.

A quality state belongs near the top. Significant unresolved citation or challenge problems should survive into the reader and exports in plain language, while operational model details can remain in the supporting workspace.

## 4. Probability, credibility and confidence

The app genuinely implements the PHIA seven-band probability vocabulary, separately from analytical confidence and the A–F / 1–6 source and information grades. Its deterministic evidence policy also groups possible copies, considers opposition and limits confidence. It does not let numerous weak articles automatically outvote a stronger item.

This is a useful foundation, but source grades are not error rates and the model's likelihood label is not a calibrated forecast. The official UK framework distinguishes a proposition's likelihood from confidence in the assessment's foundations. The published standards also require contrary information, auditable reasoning and independence from a preferred conclusion. [PHIA uncertainty guidance](https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment), [PHIA Common Analytical Standards](https://www.gov.uk/government/publications/phia-common-analytical-standards/phia-common-analytical-standards).

Current strengths and limits:

- The vocabulary and evidence-derived confidence ceilings are implemented in code. [Doctrine](C:/AlexDev/OSINT/backend/src/ase/domain/doctrine.py:51), [judgement assessment](C:/AlexDev/OSINT/backend/src/ase/domain/judgement_assessment.py:96).
- Citation membership and literal checks do not establish that a passage supports the claimed meaning. Supporting and opposing relationships are still model-assigned. [Citation checks](C:/AlexDev/OSINT/backend/src/ase/application/reports/citation_checks.py:86).
- Report status is set before later citation-check results are generated. A ready status therefore should not be read as per-claim factual verification. [Version construction](C:/AlexDev/OSINT/backend/src/ase/application/reports/production_version.py:67).
- Generic validation probes accepted a judgement combining “highly likely” with “100% probability”, a confidence explanation consisting of “Because.” and a forecast without an explicit horizon. The staged section contract is stricter in some respects, so these probes demonstrate inconsistent boundaries rather than proving every current Research route accepts each example. [Generic validation](C:/AlexDev/OSINT/backend/src/ase/domain/validation.py:98), [reporting checks](C:/AlexDev/OSINT/backend/src/ase/domain/validation.py:260).
- Source independence is estimated from recorded provenance and text similarity. Reprints, translations and different outlets repeating one original claim can still evade those heuristics.

Extend the existing claim ledger, proposals and evidence review tools into stronger per-claim adjudication. The ledger already exists, but its evidential coverage can remain unknown and its literal citation checks do not establish meaning. Each material judgement should retain its exact claim, time horizon where relevant, supporting passages, counterevidence, source origin groups, likelihood, confidence explanation, assumptions and conditions that would change it. Verification should distinguish supported, partly supported, contradicted and insufficient context. [Existing claim ledger](C:/AlexDev/OSINT/backend/src/ase/domain/claim_ledger.py:78).

Confidence explanations should cover the information base, analytical rigour and the complexity or volatility of the situation. A source-count-derived ceiling is one input to that assessment. Retain conservative limits, but avoid forcing unsupported forecasts simply to populate a probability field.

Review source-grading policy across ingestion paths. Some initial feed grades use broad editorial classifications, while fresh Research publisher items are reset to F6 and live regrading follows another policy. This inconsistency warrants review; the audit did not establish a specific biased report caused by it.

## 5. A shared Research Brief

Research and Subscriptions should use the same versioned brief. A subscription is a brief plus a publication and monitoring policy.

The brief should contain:

| Field | Purpose |
| --- | --- |
| Main question | The decision-relevant question to answer |
| Required questions | A short list of recurring intelligence requirements |
| Countries, entities and area | Explicit scope, with optional map geometry |
| Evidence period and forecast horizon | Separate observed history from forward assessment |
| Analytical lens | Audience and relevance priorities |
| Required themes and exclusions | Control coverage without suppressing contrary evidence |
| Depth and output language | Preserve Research settings when scheduling |
| Source policy | Recommended sources, required primary evidence and language coverage |
| Budget and stopping rules | Bound duration, external requests and model work |
| Indicators and escalation conditions | Define what should trigger attention |

The initial form can stay simple: choose a starter brief or enter a question, set scope and lens, choose depth, then review a concise coverage and duration summary. Advanced source/task controls remain expandable. The same brief should support Run once, Save brief and Subscribe, without re-entering settings.

Currently, Subscriptions default to Basic and English and omit output language/style, query variants, operator hypotheses and planned tasks that one-off Research supports. The saved question can express a perspective informally, but it is not a structured, versioned requirement. Evidence: [Research preferences](C:/AlexDev/OSINT/frontend/src/features/research/ResearchForm.tsx:51), [subscription defaults](C:/AlexDev/OSINT/frontend/src/features/reports/useScheduleForm.ts:68), [schedule request contract](C:/AlexDev/OSINT/backend/src/ase/api/schemas_schedules.py:19).

### Analytical lenses

Useful choices include general situational awareness, UK policy implications, civilian protection, regional security, economic exposure, energy security, supply-chain impact and defensive cyber relevance.

Actor perspectives can also be useful, provided they are clearly framed as analysis of that actor's stated objectives, constraints and claims. For Israel, Gaza and the West Bank, this could include Israeli domestic/security concerns, Palestinian civilian/governance concerns or regional diplomatic implications. The lens should change the questions and relevance of findings, while factual findings and contrary evidence remain visible.

Example brief: “Assess developments affecting civilian protection and aid access in Israel, Gaza and the West Bank over the past seven days. Separate reported events, claims by parties and assessed implications. Explain changes since the previous edition, unresolved contradictions and the indicators most likely to change the outlook.”

## 6. Subscription presets

There are nine report formats, including Cyber summary and Conflict assessment. These are output structures, not a full preset library. The shared regional shortcuts are only Russia, China and Iran. The conflict catalogue contains Israel, Gaza and the West Bank, but there is no corresponding guided subscription brief, and the subscription picker excludes some specialist conflict/hazard templates. Evidence: [report formats](C:/AlexDev/OSINT/backend/src/ase/application/reports/templates.py:41), [regional shortcuts](C:/AlexDev/OSINT/frontend/src/features/research/RegionalPresets.tsx:15), [conflict entry](C:/AlexDev/OSINT/backend/src/ase/resources/conflicts.json:15), [subscription picker](C:/AlexDev/OSINT/frontend/src/features/reports/ScheduleScope.tsx:70).

Start with a small, curated library of editable briefs:

| Group | Initial presets | Required analytical content |
| --- | --- | --- |
| Conflict | Global conflict briefing; Russia–Ukraine; Israel, Gaza and the West Bank; Iran and regional escalation; Taiwan and the Indo-Pacific | Developments, attribution, civilian effects, diplomacy, alternative explanations and indicators |
| Cyber | Global CTI; UK critical sectors; ransomware; selected threat actor; exploitation affecting selected technologies | Claimed versus evidenced activity, affected sectors, exploitation changes, attribution confidence and defensive implications |
| Economy | Global macro; UK; USA; China; Russia; Iran | Official data, revisions, monetary/fiscal policy, trade, sanctions, transmission mechanisms and outlook |
| Cross-cutting | Energy security; shipping and supply chains; disasters and humanitarian conditions; custom area watch | Sourced metrics, dependencies, disruption, geographic coverage and missing data |

Each card should initialise an editable brief, relevant source bundle, language suggestions and output sections. A country title alone is not sufficient. Presets need owners, revision dates and capability tests so unavailable sources do not silently become permanent omissions.

Personal saved briefs and duplication should follow the initial library. A user should be able to turn a useful completed report into a subscription while retaining its exact brief and choosing how future editions differ.

## 7. A dependable subscription control panel

Existing recurrence options are broad enough: daily, weekly, monthly, quarterly, half-yearly and annual. Short-month and leap-year behaviour is already tested. The priority is control and visibility.

Add:

- Generate baseline now, run once now, retry failed edition and pause/resume.
- Current stage, next scheduled slot, last successful edition, coverage cutoff and missed-run count.
- A history of editions and attempts, with report quality and failure reasons.
- Local timezone scheduling with explicit daylight-saving behaviour.
- Source readiness and expected coverage before activation.
- In-app delivery, with optional configured delivery channels and a visible monthly budget.
- Brief duplication, version history and safe edit behaviour that preserves pending work.

The current screen loads once and does not refresh ordinary status while it remains open. It has no Run now or full run history. Errors inside advanced settings can disable submission without a prominent summary, and editing does not reliably bring the form into view. These are straightforward usability repairs. Evidence: [one-shot schedule load](C:/AlexDev/OSINT/frontend/src/features/reports/SchedulesSection.tsx:47), [row controls](C:/AlexDev/OSINT/frontend/src/features/reports/ScheduleRow.tsx:103).

## 8. “What changed?” needs a more precise contract

Subscriptions already do more than deduplicate links. They retain up to 500 fingerprints, prioritise new relevant evidence, supply previous key judgements and ask for strengthened, weakened or reversed assessments. That work should be retained. [History](C:/AlexDev/OSINT/backend/src/ase/adapters/persistence/subscription_history.py:11), [previous judgements](C:/AlexDev/OSINT/backend/src/ase/application/reports/research_inputs.py:113).

The deterministic change comparator, however, mainly checks evidence, support/opposition links, confidence and validation findings. It does not compare judgement probability or meaning. Consequently, changed conclusions with unchanged evidence identifiers and confidence can fail to alert. Evidence churn can also trigger a notification without a meaningful development.

The current phrase “No material change identified” overstates that comparator. Use separate statuses for:

1. No new relevant captured evidence.
2. New evidence, assessment broadly unchanged.
3. Assessment changed, with cited reasons.
4. Significant contradiction or correction.
5. Insufficient coverage to compare.
6. Collection or generation failed.

An optional model can propose materiality and explain a changed judgement, but the decision must refer to exact previous and current claims and evidence. It should remain reviewable. Quiet periods should produce a short honest update instead of a padded full report.

Evidence: [change comparator](C:/AlexDev/OSINT/backend/src/ase/domain/research_changes.py:135), [current UI wording](C:/AlexDev/OSINT/frontend/src/features/reports/ScheduleRow.tsx:39).

## 9. Useful agentic and AI features

The app already performs bounded direction planning, query translation, supplementary task planning, section drafting and at most one guarded continuation/replan. Calling this a blank slate for agents would understate the existing system. [Planning](C:/AlexDev/OSINT/backend/src/ase/application/research/model_planning.py), [continuation](C:/AlexDev/OSINT/backend/src/ase/application/research/continuation_review.py:13).

The highest-value extensions are:

| Feature | Behaviour | Completion criterion |
| --- | --- | --- |
| Brief clarification | Ask only about ambiguities that materially change the search | Accepted question, scope and decision horizon |
| Source planning | Rank eligible providers and allocate collection to each requirement | Every requirement has evidence or an explicit gap |
| Primary-source follow-through | Retrieve selected discovered documents and exact passages | Attributable content with dates and preserved provenance |
| Counterevidence search | Search specifically for evidence that could overturn each key judgement | Recorded contrary searches and reconciled contradictions |
| Claim review | Compare claims, dates, numbers and attribution against passages | Support state for every material claim |
| Quantitative analysis | Calculate changes, trends and charts using typed data tools | Reproducible calculation and labelled units |
| Subscription reassessment | Compare successive claim ledgers and indicators | Explained change with links to both editions |
| Report Q&A | Ask questions against a selected frozen report and its evidence | Answers tied to that report version, with fresh search explicit |

Use an orchestrator with narrow source and analysis tools, persistent checkpoints, bounded expansion and clear stopping conditions. Model suggestions must not manufacture identifiers, enlarge the authorised scope or turn generated text into evidence. Repeated agreement by several model calls is not independent source corroboration.

Specialist cyber, economic or regional analysis stages can help when they have different tools and explicit questions. Running multiple general agents over the same snippets is unlikely to solve missing evidence. First improve acquisition and verification, then evaluate whether specialist stages add measurable value.

Further product features worth adding after the reliability work are an intelligence-requirement coverage matrix, a dated forecast/indicator ledger, entity disambiguation with reviewed aliases, correction tracking, sourced timelines and voluntary organisation/sector profiles for relevance. Existing export and evidence-review features should be exposed through these workflows rather than duplicated.

## 10. Implementation order and acceptance

| Milestone | Scope | Acceptance evidence |
| --- | --- | --- |
| 1. Correctness and truthful states | Effective-query ranking, failed/review subscription outcomes, overdue rename, historical follow-up error and status refresh | Regression reproductions pass; UI shows the actual run outcome |
| 2. One execution system | Subscriptions enqueue durable jobs; due-slot identity, retries, edition history and catch-up | Restart, overlapping execution and missed-period tests; one persisted edition per slot |
| 3. Shared briefs and presets | Reusable versioned brief, report-to-subscription handoff, lenses, output preferences and curated topic library | Round-trip parity between Run once and Subscribe; every preset exercises supported sources |
| 4. Better evidence | Question-ranked collection, primary-content retrieval, specialist structured data and checkpointed counterevidence | Curated source-recall tests, original passages, coverage receipts and bounded costs |
| 5. Better assessment | Extend the claim ledger, harmonised doctrine checks, visible quality state and explainable changes | Human-reviewed claim support, contradictions, date/number tests and change comparisons |
| 6. Operational acceptance | Current provider, model, browser, scheduling and report-export checks | Recorded representative runs, failure recovery and measured latency/cost/quality |

Begin with a representative evaluation set covering cyber, economy, conflict, disaster, company and area research. Include recycled old stories, syndicated articles, ambiguous entities, contradictory official statements, quiet periods and failed providers. The repository already has synthetic cases and an evaluation harness, but independent human labels and actual configured-model results remain a separate requirement.

Measure question coverage, source recall against curated packets, passage support, attribution/date accuracy, preservation of counterevidence, appropriate abstention, subscription novelty and successful recovery. Measure duration and cost alongside these outcomes. A longer report and a higher test count are not evidence of better analytical quality.

## 11. Validation and limits of this audit

Four focused code reviews covered the backend Research pipeline, subscription scheduling, frontend journeys and doctrine/report assessment. Deterministic tests passed:

| Area | Tests passed | Scope |
| --- | ---: | --- |
| Research pipeline | 112 | Collection, depth, replanning, sections, synthesis and fresh-web contracts |
| Subscription backend | 81 | Schedules, calendars, saved options, changes, history and background scope |
| Doctrine and assessment | 89 | Vocabulary, evidence matrix, provenance, integrity, assessment and publication |
| Frontend | 57 | Research configuration, subscription forms, areas, jobs and publication |

Coverage collection was disabled for these focused selections. These figures are reported by suite rather than combined into a full-system coverage claim. Additional offline probes reproduced ranking loss, annual retry timing, overlapping execution, missed-window handling, rename rescheduling and generic validation inconsistencies. Initial sandbox-related dependency access failures were resolved through approved execution; the reported counts are from completed runs.

A content-free, read-only development database probe found five reports: one failed, three needing review and one ready. Eleven saved versions included seven failed versions. Six durable jobs comprised one completed, two needing review and three paused. These records date from 11–12 September and include development attempts; they are not an estimate of present production reliability. The inspected database contained no subscription rows, so there is no locally observed scheduled-run track record to assess.

No paid model requests, live subscription executions, database changes or source onboarding occurred in this audit. Current source credentials were checked for presence only. Browser keyboard and visual acceptance was not performed. Findings based on exact code paths and deterministic reproductions remain valid independently of those unperformed checks.

## References

The inline repository links identify the current implementation supporting each finding. Relevant existing design and acceptance records include:

- [Automatic planning](C:/AlexDev/OSINT/docs/AUTOMATIC_RESEARCH_PLANNING.md).
- [Evidence assessment policy](C:/AlexDev/OSINT/docs/REPORT_EVIDENCE_SCORING.md).
- [Durable research jobs](C:/AlexDev/OSINT/docs/DURABLE_RESEARCH_JOBS.md).
- [Professional report product](C:/AlexDev/OSINT/docs/PROFESSIONAL_REPORT_PRODUCT_PLAN.md).
- [Historical live-model acceptance](C:/AlexDev/OSINT/docs/LIVE_RESEARCH_ACCEPTANCE_2026_09_11.md), which records earlier failures and repairs and is not substituted for current acceptance.
- UK PHIA, [Explaining Uncertainty in UK Intelligence Assessment](https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment), published 24 March 2025.
- UK PHIA, [Common Analytical Standards](https://www.gov.uk/government/publications/phia-common-analytical-standards/phia-common-analytical-standards), published 24 March 2025.
- [ONS developer hub](https://developer.ons.gov.uk/), [ECB data API](https://data.ecb.europa.eu/help/api/data), and [ReliefWeb API parameters](https://apidoc.reliefweb.int/parameters), accessed for proposed data and connection work.
