# Claims register

Status: draft for Alex's approval. Every row was checked on **18 October 2026**
against branch `claude/KAN-170-product-gaps` (`main` at `ea68f65c` plus the
integrated product page work). "Where" paths are relative to
`frontend/src/features/product/`. "Evidence" names the file or document that was
opened for the check; backend paths are relative to `backend/src/ase/`.
Rows whose copy was corrected later on 18 October 2026 (KAN-171, KAN-196) describe the
corrected copy; their caveats say what it replaced. No row is currently Unverified.

Status values:

- **Verified**: the evidence supports the claim as worded.
- **Caveat**: supported, but the wording needs the stated qualification, or the
  claim depends on configuration. Copy fixes are listed in
  [narrative.md](narrative.md#copy-issues-for-review).
- **Unverified**: not supported by the evidence found. Recommendation: cut, or
  reword and re-verify before release.

The review rule in [README.md](README.md#review-rule) applies to every row.

## Hero, metadata and footer

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | 15 map layers | `chapters/HeroChapter.tsx`, `chapters/ObserveChapter.tsx` | `frontend/src/lib/mapLayerDirectory.ts`: 8 "Live events" and 7 "Reference layers"; `content/productContent.unit.test.ts` pins 15 | | 18 Oct 2026 | Verified |
| H2 | "400+ catalogued sources"; orbit core "423 sources" | `chapters/HeroChapter.tsx`, `chapters/SourcesChapter.tsx` | Recount below: 263 live connectors and 160 research specs with no keys configured | The Sources page lists 428 entries on a fresh installation (five optional keyed connector specs are added). Counts change with keys and `ASE_FEEDS_DISABLED` | 18 Oct 2026 | Caveat |
| H3 | 11 intelligence topics; "eleven topics" | `chapters/HeroChapter.tsx`, `chapters/SourcesChapter.tsx` | `domain/events.py` `Category` (11 values); `frontend/src/lib/categories.ts` | | 18 Oct 2026 | Verified |
| H4 | 7 probability bands | `chapters/HeroChapter.tsx`, `content/research.ts` | `domain/doctrine.py` `YARDSTICK` (7 bands); `docs/03_DOCTRINE_AND_REPORTING.md` "Likelihood" | | 18 Oct 2026 | Verified |
| H5 | Self-hosted, on your own infrastructure, with the AI provider you choose | `chapters/HeroChapter.tsx`, `content/chapters.ts` | `README.md` "How AI is used"; `docs/AI.md`; `docs/DEPLOYMENT.md` | Self-hosting does not make cloud model calls local (`docs/AI.md`) | 18 Oct 2026 | Verified |
| H6 | An assessment "shows the selected evidence, grades and doubts behind each judgement" | `chapters/HeroChapter.tsx` | `docs/03_DOCTRINE_AND_REPORTING.md` (selected, frozen evidence; grades; per-judgement confidence and uncertainty) | Reworded on 18 October 2026 from "every source, grade and doubt" | 18 Oct 2026 | Verified |
| H7 | Globe outlines from Natural Earth (public domain) | `ProductStory.tsx` footer | `scenes/landMask.generated.ts` header (generated from Natural Earth 1:110m) | | 18 Oct 2026 | Verified |
| H8 | Scenes, questions and reports are illustrative and use no live data | `ProductStory.tsx` footer, chapter footnotes | `scenes/sceneData.ts`, `scenes/sceneData.generated.json` (seed 20261007); static content modules | | 18 Oct 2026 | Verified |

## Observe, filters and tools

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| O1 | 8 live and 7 reference layers on a 3D globe or flat map | `chapters/ObserveChapter.tsx` | `frontend/src/lib/mapLayerDirectory.ts`; `docs/04_FEATURES_AND_VIEWS.md` ("globe or flat map") | | 18 Oct 2026 | Verified |
| O2 | Each layer has its own filters, as listed in the chips | `content/observe.ts` | Spot check of labels in `features/globe/` (for example `newsFilters.ts`, `ConflictOverviewPanel.tsx`, `cameras/cameraMediaFilters.ts`) | Spot-checked, not every chip. Chips paraphrase panel controls, for example "Wars" and "Tensions" for "War region" and "Tension area" | 18 Oct 2026 | Caveat |
| O3 | Layers carry source details | `chapters/ObserveChapter.tsx` | `docs/04_FEATURES_AND_VIEWS.md` "Open an item to inspect its source, date, grade and location precision" | | 18 Oct 2026 | Verified |
| T1 | 17 map setup and planning tools | `chapters/ToolsChapter.tsx` | `frontend/src/lib/mapLayerDirectory.ts` (8 and 9 entries); unit test pins 17 | | 18 Oct 2026 | Verified |
| T2 | Event time 1 h, 6 h, 24 h, 72 h, 7 d, All, and replay "one hour at a time" | `content/observe.ts`, `chapters/ToolsChapter.tsx` | `features/globe/LayerPanel.tsx` `WINDOWS`; directory "an hour-by-hour replay of the events still retained" | Lead reworded on 18 October 2026 from "event by event" | 18 Oct 2026 | Verified |
| T3 | Location quality, find nation, collection plan, research area, 3D or 2D, daily NASA imagery, day and night | `content/observe.ts` | Directory entries `quality`, `nation`, `plan`, `area`, `imagery`, `style`; "Propagated" and "Not plotted" labels in `features/globe/` | | 18 Oct 2026 | Verified |

## Sources

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 263 scheduled feeds | `chapters/SourcesChapter.tsx`, `content/sources.ts` | Recount below: 263 connectors built with no keys | Matches the live connectors. The Sources inventory classifies 268 as scheduled because five keyed connectors are listed before their keys exist. The 19 September health audit's "263 of 278 healthy" is a different, coincidental figure | 18 Oct 2026 | Caveat |
| S2 | 160 on-demand research connectors | `chapters/SourcesChapter.tsx`, `content/sources.ts` | Recount below: 160 research specs; per-topic on-demand figures all match | Includes the private-file and media input routes and some sources not named on the page | 18 Oct 2026 | Caveat |
| S3 | Per-topic scheduled split (disaster 15, conflict 4, news 97, aviation 7, maritime 2, space 8, cyber 20, social 68, political 11, humanitarian 5, economic 26) | `content/sources.ts` | Recount below (two independent read-only runs agree); `content/productContent.unit.test.ts` pins the split | Counts the live connectors built with no keys. The Sources inventory also lists the five optional keyed connector specs, so it shows one more for conflict, cyber and humanitarian and two more for maritime | 18 Oct 2026 | Verified |
| S4 | Representative providers per topic | `content/sources.ts` | Names found in `adapters/`, `container/` and `resources/` (USGS, GDACS, FIRMS, GVP, UCDP, CelesTrak, SWPC, KEV, MITRE, RDAP, ONS, Bank of England, SEC, GLEIF, UK sanctions, WHO, IFRC, OCHA, IOM DTM, IPC, FCDO and others) | Some need keys or snapshots, for example the UK sanctions list (`ASE_UKSL_SNAPSHOT_PATH`); the page footnote states this | 18 Oct 2026 | Verified |
| S5 | "Each record keeps its source and collection time; licence notes, where a source has them, stay with that source in the catalogue" | `chapters/SourcesChapter.tsx` | `domain/events.py` `Event.source_id`, `observed_at`; `domain/sources.py` `SourceSpec.licence_note` | Reworded on 18 October 2026 from per-record licence notes | 18 Oct 2026 | Verified |
| S6 | Scheduled feeds go into a bounded live store that is never written to the database | `content/sources.ts` | ADR 0003, ADR 0008 (amended), ADR 0010, ADR 0022; `docs/01_ARCHITECTURE.md` "What is stored" | One disposable snapshot file exists for restarts (ADR 0022); it is not the database | 18 Oct 2026 | Verified |
| S7 | On-demand connectors run only when a question needs them | `content/sources.ts` | `container/research_sources.py`; `docs/02_DATA_SOURCES.md` (collection receipts per run) | | 18 Oct 2026 | Verified |
| S8 | Packaged reference data: infrastructure registers, aircraft types, public figures, country boundaries | `content/sources.ts` | `resources/` (`energy_sites.json`, `nuclear_facilities.json`, `reference_aircraft_types.json`, `public_figures.json`, `countries_110m.json`) | | 18 Oct 2026 | Verified |
| S9 | Private TXT, CSV, JSON, PDF, DOCX, images and video keyframes added to a question | `content/sources.ts`, `content/research.ts` | `docs/02_DATA_SOURCES.md` (supplied documents and media, sampled frames) | Bounded, expiring private inputs (`docs/01_ARCHITECTURE.md`) | 18 Oct 2026 | Verified |
| S10 | Some sources need keys, accounts or licence acknowledgements | `content/sources.ts` | `application/source_inventory.py` `RequirementKind`; `container/source_requirements.py` | | 18 Oct 2026 | Verified |

## Ask

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Every run has an explicit scope: places, dates, languages, sources, template, depth | `chapters/AskChapter.tsx` | `domain/research.py` `ResearchQuery` (`since`, `until`, `languages`, `source_ids`, `mode`, `area`, `country_isos`); `api/schemas_reports.py` `TEMPLATES` | | 18 Oct 2026 | Verified |
| A2 | Saved Research Briefs keep explicit requirements for reuse | `chapters/AskChapter.tsx`, `content/research.ts` | `docs/04_FEATURES_AND_VIEWS.md`; `domain/research_brief_values.py` | | 18 Oct 2026 | Verified |
| A3 | Ten report templates, from intelligence summaries to disaster SITREPs | `content/research.ts` | `TEMPLATES` in `api/schemas_reports.py`: 10 keys counted (`intsum` to `disaster_sitrep`) | | 18 Oct 2026 | Verified |
| A4 | Twenty research presets | `content/research.ts` | `resources/research_presets.json`: 20 presets counted | | 18 Oct 2026 | Verified |
| A5 | Area research from a polygon drawn on the map | `content/research.ts` | `docs/AREA_RESEARCH.md` (polygon, rectangle or circle) | | 18 Oct 2026 | Verified |
| A6 | Company, domain, document and media focus | `content/research.ts` | `domain/research.py` `ResearchFocus` | | 18 Oct 2026 | Verified |
| A7 | Query translation and transliteration across languages | `content/research.ts` | `docs/SOURCE_PROVENANCE_OPERATIONS.md`; `docs/AI_COST_CONTROLS.md` (query translation purpose) | Transliterations are operator-supplied variants or model suggestions, not automatic for every term | 18 Oct 2026 | Caveat |
| A8 | Photo geolocation with a sun and shadow check | `content/research.ts`, `content/platform.ts` | `domain/sun_shadow.py`; `docs/DEVELOPMENT_STORY.md` (ShadowFinder method) | Vision depends on the configured model (`README.md`) | 18 Oct 2026 | Caveat |
| A9 | Private inputs are analysed by your configured AI provider | `content/research.ts` | `docs/07_SECURITY_BY_DESIGN.md` "What may leave the installation" | | 18 Oct 2026 | Verified |
| A10 | Basic 750 to 1,350 words and 24 evidence items; Deep 1,800 to 3,000 and 48; Advanced 3,750 to 6,000 and 80 | `content/research.ts` | `application/reports/depth.py` `DEPTHS` | Word ranges are targets, not guaranteed lengths (`docs/04_FEATURES_AND_VIEWS.md`); evidence figures are maximums | 18 Oct 2026 | Caveat |
| A11 | Scope chip "Area: Drawn on the map", carried over from the map | `content/research.ts` | `docs/AREA_RESEARCH.md` | Composite illustration. Area research is a separate flow, not one form with region, countries, languages and template. Copy issue 3 | 18 Oct 2026 | Caveat |
| A12 | "Illustrative request. Nothing is sent from this page." | `chapters/AskChapter.tsx` | Static content; product import boundary (`docs/PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md`, "Implemented controls") | | 18 Oct 2026 | Verified |

## Collect and Assess

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | Each record comes back with its source and a grade; collection receipts record which providers ran, including empty and unavailable ones | `chapters/CollectChapter.tsx` | `docs/01_ARCHITECTURE.md` ("Freeze evidence and collection receipts"); `docs/03_DOCTRINE_AND_REPORTING.md` (receipts include empty responses and unavailable sources) | Reworded on 18 October 2026; receipts are per provider attempt, not per record | 18 Oct 2026 | Verified |
| C2 | Collection receipts shown on the evidence cards | `content/research.ts` | Code comment: "Illustrative collection receipt reference; real receipts record each source task" | Illustrative values; the footnote says so | 18 Oct 2026 | Caveat |
| C3 | Requirements without enough support stay visible as gaps rather than papered over | `chapters/CollectChapter.tsx` | `docs/03_DOCTRINE_AND_REPORTING.md` (requirements without adequate support "should remain visible as gaps") | Reworded on 18 October 2026 from "anything the run could not find" | 18 Oct 2026 | Verified |
| C4 | Copies are grouped, not counted as extra confirmation | `content/research.ts` | `docs/03_DOCTRINE_AND_REPORTING.md` (organisation and possible-copy groups) | Different labels do not prove independent chains | 18 Oct 2026 | Verified |
| C5 | Reliability A to F, credibility 1 to 6; F and 6 cannot be judged | `content/research.ts` | `domain/events.py` `Reliability`, `Credibility`; `docs/03_DOCTRINE_AND_REPORTING.md` | | 18 Oct 2026 | Verified |
| C6 | New research material without an assessed source basis stays unassessed | `content/research.ts` | `docs/03_DOCTRINE_AND_REPORTING.md` ("remains explicitly unassessed") | Reworded on 18 October 2026 from "until reviewed" | 18 Oct 2026 | Verified |
| X1 | Probability language checked against the PHIA yardstick | `content/research.ts` | `docs/03_DOCTRINE_AND_REPORTING.md` (validator); `domain/doctrine.py` | Wording checks cannot interpret every use of language | 18 Oct 2026 | Verified |
| X2 | Confidence high, moderate or low, capped by the evidence | `content/research.ts` | `docs/03_DOCTRINE_AND_REPORTING.md` "Confidence and evidence strength" | | 18 Oct 2026 | Verified |
| X3 | Citation, entailment and contradiction checks | `content/research.ts` | `application/reports/entailment.py`, `contradiction_checks.py`; `docs/03_DOCTRINE_AND_REPORTING.md` | A citation match is not proof of support | 18 Oct 2026 | Verified |
| X4 | Challenge pass and devil's advocacy on the top judgement | `content/research.ts` | `application/reports/production_review.py`, `advocacy.py`; `domain/research.py` `requires_challenge` | Challenge pass runs on Deep and Advanced only; on Basic, devil's advocacy runs only when requested | 18 Oct 2026 | Caveat |
| X5 | Alternative hypotheses, assumptions and information gaps | `content/research.ts` | `docs/03_DOCTRINE_AND_REPORTING.md` (opening section) | | 18 Oct 2026 | Verified |
| X6 | Claims ledger with identities and relationships to review | `content/research.ts` | `domain/claim_ledger.py`; `docs/04_FEATURES_AND_VIEWS.md` (annotation monitors) | Relationships are model-assigned | 18 Oct 2026 | Caveat |
| X7 | Exact calculations with formula receipts | `content/research.ts` | `domain/quantitative_calculations.py` | | 18 Oct 2026 | Verified |
| X8 | Report shows its model line and an AI-assisted label; no bundled model | `content/research.ts` | `README.md` ("model details"); ADR 0024 | | 18 Oct 2026 | Verified |
| X9 | Example status "Ready" | `chapters/AssessChapter.tsx` | `docs/03_DOCTRINE_AND_REPORTING.md` status table | Ready means automated checks passed, not human approval; the page does not say so | 18 Oct 2026 | Caveat |
| X10 | "Maritime activity report · Confidence stated per judgement", with each judgement labelled by likelihood and confidence (Moderate, Moderate, Low) | `content/research.ts`, `chapters/AssessChapter.tsx` | `docs/03_DOCTRINE_AND_REPORTING.md` (confidence is per judgement; the engine "does not give an entire report one confidence level") | Illustrative values. Replaced the report-level "Moderate confidence" on 18 October 2026 | 18 Oct 2026 | Verified |
| X11 | Saved as version 1, follow-up in the same scope, regenerate as version 2 and compare | `content/research.ts` | `docs/04_FEATURES_AND_VIEWS.md`; `application/reports/followup_scope.py`, `comparison.py` | | 18 Oct 2026 | Verified |

## Review

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Version 1 keeps frozen evidence, grades, model details and status | `content/platform.ts` | `docs/03_DOCTRINE_AND_REPORTING.md` "Evidence, versions and exports"; `README.md` | | 18 Oct 2026 | Verified |
| R2 | A follow-up inherits the evidence within the same scope | `content/platform.ts` | `application/reports/followup_scope.py` docstring | | 18 Oct 2026 | Verified |
| R3 | A subscription edition is compared with the last one | `content/platform.ts` | `application/reports/subscription_comparison.py`; `docs/04_FEATURES_AND_VIEWS.md` section 4 | Compared with the previous successful edition where the workflow offers it | 18 Oct 2026 | Caveat |
| R4 | An alert rule fires after its warm-up baseline | `content/platform.ts` | `domain/indicator_baseline.py` (`WARMUP_HOURS` 168) | Warm-up applies to relative rules; threshold rules fire without it | 18 Oct 2026 | Caveat |
| R5 | Version 2 with a deterministic comparison | `content/platform.ts` | `application/reports/comparison.py` docstring | | 18 Oct 2026 | Verified |
| R6 | Forecast resolution kept as append-only history | `content/platform.ts` | `domain/forecast_ledger.py`, `forecast_decisions.py` | | 18 Oct 2026 | Verified |
| R7 | Six ways to keep watching | `content/platform.ts` | `frontend/src/features/watches/watchModel.ts` (six cards) | | 18 Oct 2026 | Verified |
| R8 | In app: live stream and notification bell | `content/platform.ts` | `docs/ALERT_ROUTING.md` (in-app always on); `domain/bell.py` | | 18 Oct 2026 | Verified |
| R9 | Email per alert or a daily digest | `content/platform.ts` | `docs/ALERT_ROUTING.md`; `domain/notification_digest.py` ("daily") | Needs SMTP configured | 18 Oct 2026 | Caveat |
| R10 | Webhook to an HTTPS endpoint you register | `content/platform.ts` | `docs/ALERT_ROUTING.md` "Registered webhooks" | | 18 Oct 2026 | Verified |
| R11 | Web push carries only an opaque identifier | `content/platform.ts` | `docs/WEB_PUSH.md` | Off by default, opt-in per browser | 18 Oct 2026 | Verified |
| R12 | Private Atom feed per account | `content/platform.ts` | `api/routers/private_feed.py`; `domain/notification_feed.py` (`FeedToken` per user) | | 18 Oct 2026 | Verified |
| R13 | PDF, DOCX and Markdown exports | `content/platform.ts` | `domain/report_documents.py` `ExportFormat`; `api/routers/reports.py` (`/markdown`) | | 18 Oct 2026 | Verified |
| R14 | STIX 2.1 with a TLP marking | `content/platform.ts` | `domain/stix.py` docstring; `api/routers/report_stix.py` | | 18 Oct 2026 | Verified |
| R15 | Evidence ZIP with selected and claim evidence | `content/platform.ts` | `docs/RESEARCH_EXPANSION_OPERATIONS.md` "Evidence packages" | Bounded to 1,000 items and 8 MiB | 18 Oct 2026 | Verified |
| R16 | GeoJSON / KML of the live map picture | `content/platform.ts` | `frontend/src/features/globe/useLivePictureExport.ts` | A map export capped at 5,000 events, not a report export; "Take it anywhere" mixes the two | 18 Oct 2026 | Caveat |
| R17 | Personal and team visibility; leaving a team ends access | `content/platform.ts` | `docs/07_SECURITY_BY_DESIGN.md` "Accounts and shared work"; ADR 0010 | Already downloaded copies cannot be recalled | 18 Oct 2026 | Verified |

## Workspaces

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | Trackers for conflict, hazards, aviation, maritime, space and public figures | `content/platform.ts` | `frontend/src/features/trackers/` (Conflict, Hazard, Aviation, Maritime, Space, Figures pages) | | 18 Oct 2026 | Verified |
| W2 | "A daily briefing on the monitor page" (Live monitoring) | `content/platform.ts` | `features/trackers/TrackersPage.tsx` renders `DailyBriefing`; `docs/04_FEATURES_AND_VIEWS.md` ("Read the daily briefing") | Replaced "Per-domain filters" on 18 October 2026 | 18 Oct 2026 | Verified |
| W3 | "Conflict source coverage and health" (Live monitoring) | `content/platform.ts` | `features/trackers/ConflictSourceCoverage.tsx` on the monitor page (Configured, Waiting for data, Healthy, Degraded) | Replaced "Source health beside every feed" on 18 October 2026 | 18 Oct 2026 | Verified |
| W4 | Ops room playlist for wall screens | `content/platform.ts` | Directory entry `ops-room` | | 18 Oct 2026 | Verified |
| W5 | Ukraine: losses and casualties datasets, official channels, cited digest every two weeks | `content/platform.ts` | `docs/UKRAINE_WAR_TRACKER.md`; `resources/ukraine_losses.json`, `ukraine_casualties.json` | The digest needs an assigned AI model | 18 Oct 2026 | Caveat |
| W6 | Cyber: advisories, KEV, ransomware, connectivity, CERT advisories, MITRE ATT&CK, GNSS, cited briefing | `content/platform.ts` | `docs/CYBER_THREAT_INTELLIGENCE.md`; `features/cyber/CyberGnss.tsx`; CERT connectors in the recount | MITRE ATT&CK is reference context, not a live connector (`container/cyber.py`) | 18 Oct 2026 | Verified |
| W7 | Economy: official statistics and central bank series, compared across five countries with explanations of unfamiliar measures; "Five-country comparison", "Market charts after consent" | `content/platform.ts` | `docs/ECONOMY_WORKSPACE.md` (five countries; "explains unfamiliar measures"; TradingView chart loads after provider consent) | Market charts are a third-party embed | 18 Oct 2026 | Verified |
| W8 | Economy: "Briefings over 2 to 14 days" | `content/platform.ts` | `docs/ECONOMY_WORKSPACE.md` "Reporting periods and AI summaries" (2, 5, 7 or 14 days) | Replaced "Briefing for any date window" on 18 October 2026 | 18 Oct 2026 | Verified |
| W9 | Photo geolocation: vision candidates, shadow check, saved assessments | `content/platform.ts` | `docs/04_FEATURES_AND_VIEWS.md` (Geolocation row); `domain/sun_shadow.py` | Vision depends on the configured model | 18 Oct 2026 | Caveat |
| W10 | Map tools: paths, areas, circles, named collections of up to 50 objects, radio studies with assumptions, terrain profiles | `content/platform.ts` | `docs/MAP_WORKSPACE.md`; `domain/map_workspace.py` (50-object limit) | | 18 Oct 2026 | Verified |
| W11 | Teams: board with mentions, invitations, shared research, team AI usage, archived teams readable | `content/platform.ts` | `features/teams/` (`TeamBoard`, `BoardMentionPicker`, `TeamInvitationPanel`, `TeamAiUsage`); `docs/04_FEATURES_AND_VIEWS.md` section 5 | | 18 Oct 2026 | Verified |
| W12 | Workspace screenshot is illustrative, from synthetic fixtures | `chapters/WorkspaceMedia.tsx`, `content/assets.ts` | `content/assets.ts` header (`pnpm capture:assets`) | | 18 Oct 2026 | Verified |

## Trust, Deploy and Contact

| # | Claim | Where | Evidence | Caveats | Verified | Status |
| --- | --- | --- | --- | --- | --- | --- |
| U1 | Treats internet content, feed items and model responses as untrusted | `chapters/TrustChapter.tsx` | `docs/07_SECURITY_BY_DESIGN.md` "Untrusted sources, files and model output" | Cannot eliminate all prompt-injection risk; "every byte" is rhetorical | 18 Oct 2026 | Caveat |
| U2 | Caddy edge with TLS and security headers | `content/platform.ts` | `infra/Caddyfile` header block | HSTS is off until the operator sets `ASE_HSTS_MAX_AGE` | 18 Oct 2026 | Caveat |
| U3 | "A content security policy allowing only same-origin scripts" | `content/platform.ts` | `infra/Caddyfile` CSP (`script-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`) | Replaced "Strict content security policy" on 18 October 2026; the policy still allows inline styles and many camera image hosts | 18 Oct 2026 | Verified |
| U4 | Request size limits per route | `content/platform.ts` | `infra/Caddyfile` `request_body` limits (64 KiB ordinary, 2 MiB avatar, 8 MiB uploads, 12 MiB map image) | | 18 Oct 2026 | Verified |
| U5 | Argon2id passwords | `content/platform.ts` | `docs/07_SECURITY_BY_DESIGN.md` | | 18 Oct 2026 | Verified |
| U6 | MFA by email or authenticator, required for administrators | `content/platform.ts` | `docs/MFA_OPERATIONS.md` | Email MFA needs SMTP; authenticator needs `ASE_ENCRYPTION_KEY` | 18 Oct 2026 | Verified |
| U7 | Rotating refresh tokens with family revocation | `content/platform.ts` | `docs/07_SECURITY_BY_DESIGN.md` (refresh families, rotation, revocation) | | 18 Oct 2026 | Verified |
| U8 | Object-level authorisation for personal and team work | `content/platform.ts` | `docs/07_SECURITY_BY_DESIGN.md`; ADR 0010 | | 18 Oct 2026 | Verified |
| U9 | Sessions re-checked before results are released | `content/platform.ts` | `docs/07_SECURITY_BY_DESIGN.md`; ADR 0021 | A check may be reused for up to `ASE_SESSION_RECHECK_SECONDS` unless a change was signalled | 18 Oct 2026 | Caveat |
| U10 | Append-only audit log | `content/platform.ts` | `domain/audit.py` docstring | Optional bounded expiry exists (`docs/OPERATIONAL_RETENTION.md`, listed in `docs/README.md`) | 18 Oct 2026 | Caveat |
| U11 | Raw live events never written to the database | `content/platform.ts` | ADRs 0003, 0008, 0010, 0022; `docs/01_ARCHITECTURE.md` "What is stored" | | 18 Oct 2026 | Verified |
| U12 | Isolated document parser with no network and no secrets | `content/platform.ts`, `chapters/DeployChapter.tsx` | `docker-compose.yml` (`parser`, `network_mode: none`); `docs/07_SECURITY_BY_DESIGN.md` | Compose only; native development uses an isolated subprocess | 18 Oct 2026 | Verified |
| U13 | Encrypted provider keys, never returned by the API | `content/platform.ts` | `docs/07_SECURITY_BY_DESIGN.md`; `api/schemas_llm.py` (`api_key_hint`) | The API returns a masked hint, never the full key | 18 Oct 2026 | Caveat |
| U14 | Data minimisation sentence (reports, evidence, accounts, teams, configuration, small operational records; bounded memory store; one disposable snapshot) | `content/platform.ts` | `docs/01_ARCHITECTURE.md` "What is stored"; ADR 0022 | Not exhaustive: Research Briefs, subscriptions, jobs, alerts, bounded private inputs and search embeddings are also stored | 18 Oct 2026 | Caveat |
| U15 | OpenAI-compatible endpoints, including models you host | `content/platform.ts` | `docs/AI.md` (providers, local model servers) | A compatible endpoint may not support every feature | 18 Oct 2026 | Verified |
| U16 | Native Amazon Bedrock in your own AWS account and region | `content/platform.ts` | `docs/AI.md`; ADR 0013 | Bedrock API keys only, not access-key pairs or instance roles | 18 Oct 2026 | Caveat |
| U17 | Research tiers and token allowances per person, team and site | `content/platform.ts` | `docs/AI_COST_CONTROLS.md`; ADRs 0019 and 0020 | An allowance is not a monetary cap | 18 Oct 2026 | Verified |
| U18 | No bundled model and no AI account needed to browse the map | `content/platform.ts` | `README.md` "How AI is used" | | 18 Oct 2026 | Verified |
| U19 | Strict typing; layered architecture enforced by import contracts | `content/platform.ts` | `backend/pyproject.toml` (mypy `strict`, `[tool.importlinter]`); `frontend/tsconfig.app.json` (`strict`) | | 18 Oct 2026 | Verified |
| U20 | A 90 percent test coverage gate | `content/platform.ts` | `backend/pyproject.toml` (`--cov-fail-under=90`); `frontend/vitest.config.ts` (lines 90); `.github/workflows/ci.yml` | | 18 Oct 2026 | Verified |
| U21 | Dependency auditing and secret scanning in CI | `content/platform.ts` | `.github/workflows/ci.yml` (pip-audit, pnpm audit, dependency review, gitleaks, Semgrep, Trivy) | | 18 Oct 2026 | Verified |
| U22 | Work to WCAG 2.2 AA accessibility | `content/platform.ts` | `docs/01_ARCHITECTURE.md` (axe checks, "not a WCAG conformance claim") | An aim, not audited; KAN-193 statement unpublished. Kept as an aim. Copy issue 1 | 18 Oct 2026 | Caveat |
| D1 | Docker Compose on a single Linux server: Caddy, API, PostgreSQL, isolated parser | `chapters/DeployChapter.tsx` | `docker-compose.yml` (`web`, `api`, `db`, `parser`); `docs/DEPLOYMENT.md` | | 18 Oct 2026 | Verified |
| D2 | "One server you run" | `chapters/DeployChapter.tsx` | `docker-compose.yml`; `docs/DEPLOYMENT.md` (single Linux server) | Replaced "One command" on 18 October 2026; setup steps are in `docs/SETUP.md` | 18 Oct 2026 | Verified |
| D3 | "Your database stays on it"; questions and selected evidence go to the configured AI provider, cited links to the Internet Archive unless turned off, and email, push and webhooks are optional | `chapters/DeployChapter.tsx` | `docs/07_SECURITY_BY_DESIGN.md` "What may leave the installation" | Replaced "Your data stays put" on 18 October 2026. Feed and map requests and optional fresh web research also leave, as the diagram and that table show | 18 Oct 2026 | Verified |
| D4 | Model calls (questions and selected evidence) go to the AI provider you configure | `chapters/DeployChapter.tsx` | `docs/07_SECURITY_BY_DESIGN.md`; `docs/AI.md` | Optional fresh web research sends the question to a compatible search provider | 18 Oct 2026 | Verified |
| D5 | Optional email service, SMTP with TLS | `chapters/DeployChapter.tsx` | `docs/MFA_OPERATIONS.md` (SMTP, `starttls` default) | | 18 Oct 2026 | Verified |
| D6 | Costs "we will estimate with you"; estimator hidden in production | `chapters/DeployChapter.tsx` | `content/costModel.ts` (`COST_MODEL_STATUS` `'draft'`) | A service commitment that depends on KAN-164 | 18 Oct 2026 | Caveat |
| K1 | Enquiry form appears only when the installation accepts enquiries | `ProductPage.tsx`, `chapters/ContactChapter.tsx` | `docs/PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md` (flags fail closed) | | 18 Oct 2026 | Verified |
| K2 | "We will help you plan the deployment, connect your AI provider and choose sources" | `chapters/ContactChapter.tsx` | ADR 0023 (proposed) | Undecided offer; needs Alex's KAN-164 decision. Copy issue 2 | 18 Oct 2026 | Caveat |

## Source catalogue recount

**Where the catalogue lives.** The Sources inventory (`application/source_inventory.py`,
composed in `container/source_inventory.py`) lists the union of three sets: live feed
connectors (`container.connectors`, built by `container/feed_services.py`), on-demand
research specs (`container.research_sources`, from `container/research_sources.py`
plus specs added in `container/cyber.py` and `container/economy.py`), and five
optional keyed connector specs (`OPTIONAL_CONNECTOR_SPECS` in
`container/source_requirements.py`: AISstream, BarentsWatch, ACLED, ReliefWeb reports
and Cloudflare Radar outages). An entry is scheduled if it is a live connector or is
not a research spec. Topics are `SourceSpec.category`.

**Method (read-only).** A scratch script outside the repository built the container
exactly as the test suite does (`Settings(env=TEST, database_url="sqlite+aiosqlite://")`,
`Container(settings, connectors=None)`), never started it, and counted each set by
category. It was run from `backend/` with
`uv run --no-sync python -I count_catalogue.py`. A second run with `env=DEV` gave the
same totals. An independent second script, written separately with the test suite's
`Settings` arguments (`env=TEST`, in-memory SQLite, no `ASE_` variables), gave the same
per-topic figures on 18 October 2026. No keys were configured and `ASE_FEEDS_DISABLED` was empty.

| Topic | Page scheduled | Live connectors | Inventory scheduled | Page on demand | Research specs |
| --- | --- | --- | --- | --- | --- |
| Disasters | 15 | 15 | 15 | 2 | 2 |
| Conflict | 4 | 4 | 5 | 0 | 0 |
| News | 97 | 97 | 97 | 62 | 62 |
| Aviation | 7 | 7 | 7 | 0 | 0 |
| Maritime | 2 | 2 | 4 | 0 | 0 |
| Space | 8 | 8 | 8 | 1 | 1 |
| Cyber | 20 | 20 | 21 | 28 | 28 |
| Social | 68 | 68 | 68 | 3 | 3 |
| Political | 11 | 11 | 11 | 12 | 12 |
| Humanitarian | 5 | 5 | 6 | 7 | 7 |
| Economic | 26 | 26 | 26 | 45 | 45 |
| **Total** | **263** | **263** | **268** | **160** | **160** |

**Findings.** The totals of 263 scheduled and 160 on-demand match the live connectors
and research specs exactly, so 263 is a catalogue count, not the 19 September healthy
count (`docs/source-audit/deployed-health-2026-09-19.md`), although the numbers
coincide. The page's per-topic scheduled figures originally matched neither set; on
18 October 2026 they were set to the live connector counts, so the "Page scheduled"
column above now equals "Live connectors". Disasters counts 15 live connectors because
both the public and the keyed FIRMS connectors are built when no key exists. On a fresh installation the Sources page shows 428 entries (268 scheduled,
160 on demand). These counts depend on the commit, on keys and on disabled feed IDs.
