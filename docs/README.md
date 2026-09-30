# Documentation

The All Seeing Eye brings public observations, question-led research and saved
evidence into one workspace. Start with the guide that matches what you need.

| Guide | What it answers |
| --- | --- |
| [App overview](../README.md) | What is the app, and what can I do with it? |
| [Setup](SETUP.md) | How do I run it on Windows 11, macOS or Linux? |
| [Using the app](04_FEATURES_AND_VIEWS.md) | Where do I start, and how do the workspaces connect? |
| [Map workspace](MAP_WORKSPACE.md) | How do I draw, save, research an area and use radio or terrain tools? |
| [Architecture](01_ARCHITECTURE.md) | What is the stack, where is data stored, and how is SOLID applied? |
| [Sources and coverage](02_DATA_SOURCES.md) | Which providers are used, and what does source availability mean? |
| [AI](AI.md) | Which models can I connect, what do they do, and what data leaves the app? |
| [Reporting and assessment](03_DOCTRINE_AND_REPORTING.md) | How should I read grades, confidence, likelihood and citations? |
| [Security and privacy](07_SECURITY_BY_DESIGN.md) | How are accounts, saved work, credentials and external content handled? |

The guides describe supported behaviour; source health and model availability
must be checked in the installation you are using. Screenshots show the real
interface with illustrative local data. Their [capture notes](images/README.md)
explain what is and is not represented.

## Guides: using the workspaces

- [Map layers and planning tools](MAP_TOOLS_AND_LAYERS.md): layer controls, measurement, drawing and planning tools on the globe and map.
- [Area research](AREA_RESEARCH.md): research a drawn boundary and time period with the supported area sources.
- [Research workspace](RESEARCH_WORKSPACE_OPERATIONS.md): ask a question, choose scope and depth, and reuse saved reports, briefs and areas.
- [Fresh web research](FRESH_WEB_RESEARCH.md): the optional live web search step and what it sends to the provider.
- [Eye assistant](EYE_ASSISTANT.md): the Ask Eye companion, its search scope, answers and limits.
- [Map news and evidence](MAP_NEWS_AND_EVIDENCE.md): shared event filters, news layers and evidence assessment on the map.
- [Dashboard context and watches](DASHBOARD_CONTEXT_AND_WATCHES.md): flight and boat lists, context panels and area watches.
- [Saved map image export](SAVED_MAP_IMAGE_EXPORT.md): export an exact saved map revision with its report version.
- [Cyber threat intelligence](CYBER_THREAT_INTELLIGENCE.md): the `/cyber` workspace, its lenses and cited briefing.
- [Economy and personal workspace](ECONOMY_WORKSPACE.md): navigation, markets, indicators and daily cited analysis.
- [Ukraine war tracker](UKRAINE_WAR_TRACKER.md): reported control, belligerent figures, assessments and updates.
- [Public figures tracker](PUBLIC_FIGURES.md): the curated office-holder roster and how markers are placed.
- [Personal profile and security](PROFILE_OPERATIONS.md): account settings, research defaults and report preferences.

## Configure and operate

- [AI connections](AI_CONNECTIONS_OPERATIONS.md): providers, models, credentials, tests and assignments.
- [AI usage and cost controls](AI_COST_CONTROLS.md): research tiers, call and token policies, and estimated spend.
- [Administration](ADMINISTRATION.md): the `/admin` workspace and its areas.
- [Multi-factor authentication](MFA_OPERATIONS.md): enrolment, administrator requirements and upgrade steps.
- [Account email setup](EMAIL_SETUP.md): provider choice, SMTP settings and delivery checks.
- [Self-hosting](DEPLOYMENT.md): requirements and deployment contract for a hosted installation.
- [Automatic deployment](AUTOMATIC_DEPLOYMENT.md): how a merge to `main` is tested and released.
- [Backup and restore](BACKUP_RESTORE.md): explicit operator commands for SQLite and Compose PostgreSQL.
- [Live-map recovery](LIVE_STREAM_RECOVERY.md): the stream resync protocol after incomplete updates.
- [Durable research jobs](DURABLE_RESEARCH_JOBS.md): accepted report jobs, progress and access checks.
- [Subscription operations](SUBSCRIPTIONS_OPERATIONS.md): admission, cadence, fairness and diagnosis for scheduled research.
- [Sources and connections](SOURCES_AND_CONNECTIONS.md): the `/sources` page, collecting sources and missing requirements.
- [Source provenance](SOURCE_PROVENANCE_OPERATIONS.md): original language, transliteration and source dates.
- [Source catalogue browsing](SOURCE_CATALOGUE_BROWSING.md): catalogue grouping, search and filters.
- [NASA FIRMS](FIRMS_OPERATIONS.md): thermal observations, the combined Fires view and credentials.
- [BarentsWatch AIS](BARENTSWATCH_AIS.md): configuring the Norwegian vessel feed.
- [Regional vessel positions](VESSEL_TRAFFIC_OPERATIONS.md): the Fintraffic AIS connector and vessel display.
- [Network connectivity sources](NETWORK_CONNECTIVITY_SOURCES.md): IODA and Cloudflare Radar outage feeds.
- [OpenAQ air-quality research](OPENAQ_RESEARCH.md): key placement and area collection.
- [Translation, social monitoring and semantic search](PHASE5_PHASE6_OPERATIONS.md): the maintained capability guide, including fixed budgets and successor links for former phase guidance.
- [Research expansion operations](RESEARCH_EXPANSION_OPERATIONS.md): collection-plan preview, continuation review, evidence packages and remaining acceptance.

## Reference

Sources and coverage:

- [Aircraft coverage](AVIATION_COVERAGE.md), [ship coverage](MARITIME_COVERAGE.md), [satellite coverage](SATELLITE_COVERAGE.md) and [worldwide coverage](WORLDWIDE_COVERAGE.md): what each layer can and cannot show.
- [Traffic provider readiness](TRAFFIC_PROVIDER_READINESS.md): worldwide aircraft sweep bounds and provider limits.
- [Public camera feeds](CAMERA_FEEDS.md), with regional detail for the [Americas](CAMERA_AMERICAS.md), [Europe](CAMERA_EUROPE.md) and [Asia, Oceania and world](CAMERA_WORLD.md).
- [Conflict coverage](CONFLICT_COVERAGE.md): conflict evidence, counting rules and source limits.
- [Conflict relevance screening](CONFLICT_RELEVANCE_SCREENING.md): model screening of machine-coded conflict signals.
- [Frontlines and unrest](FRONTLINES_AND_UNREST.md): conflict markers, unrest filters and frontline source options.
- [News source coverage](NEWS_SOURCE_COVERAGE.md): verified public news RSS feeds and GDELT geography.
- [Social source coverage](SOCIAL_SOURCE_COVERAGE.md): Mastodon, Reddit and YouTube checks and decisions.
- [Telegram channel coverage](TELEGRAM_CHANNEL_COVERAGE.md): curated public channels and what is not collected.
- [Regional RSS feasibility](SOURCE_FEASIBILITY_2026_09.md): the dated probe record behind the regional feed seeds.
- [Cloudflare Radar attack trends](CYBER_RADAR_ATTACK_TRENDS.md): what the attack distribution snapshot measures.
- [Map infrastructure](MAP_INFRASTRUCTURE.md) and [ground stations](GROUND_STATIONS.md): packaged cable and station snapshots.
- [Reference notes](REFERENCE_NOTES.md): packaged background for aircraft, vessels and aircraft types.
- [Source calendar conversion](SOURCE_CALENDAR_CONVENTION.md): supported calendars and conversion rules.

Research and reports:

- [Report evidence assessment policy](REPORT_EVIDENCE_SCORING.md): the `ase-evidence-v1` scoring dimensions.
- [Report quality checks](REPORT_QUALITY_CHECKS.md): the checks run before a report is frozen.
- [Automatic research planning](AUTOMATIC_RESEARCH_PLANNING.md): candidate and challenge planning before collection.
- [Country subjects in research](COUNTRY_SUBJECT_RESEARCH.md): when a headline can support country relevance.
- [Doctrine references](DOCTRINE_REFERENCES.md): the pinned public doctrine register used by Ask Eye.
- [Structured report HTML](STRUCTURED_REPORT_HTML.md) and [isolated report renderer](ISOLATED_REPORT_RENDERER.md): report document projection and PDF rendering limits.

Map and radio:

- [GNSS interference and map controls](GNSS_AND_MAP_CONTROLS.md): the GNSS layer and where map controls live.
- [Conflict display filters](CONFLICT_DISPLAY_FILTERS.md) and [hazard filters](HAZARD_FILTERS.md): regional overview and hazard subtype filtering.
- [RF reach and coverage](RF_COVERAGE_DISPLAY.md): link and area studies in the RF planner.
- [Radio modelling and terrain evidence](RADIO_MODEL_EVALUATION.md), [radio presets](RADIO_PRESETS.md) and [HF groundwave model](HF_GROUNDWAVE_MODEL.md): models, presets and provenance.

## API

Field details come from the FastAPI schemas and exported OpenAPI document.

- [Authentication and administrator API](api/AUTH_API.md)
- [Automated research API](api/AUTOMATED_RESEARCH_API.md)
- [Research allowance API](api/RESEARCH_ALLOWANCES_API.md): tier assignment, usage and reset information.
- [Saved research schedules](api/RESEARCH_SCHEDULES_API.md)
- [Scoped operational work and reports](api/SCOPED_WORK_API.md)
- [Team management API](api/TEAMS_API.md)

## Architecture decisions

The [ADRs](adr/) record accepted design decisions, one per numbered file. The
architecture guide links the editable [Structurizr model](diagrams/workspace.dsl)
and [diagram maintenance instructions](diagrams/README.md).

## Security

[Security and privacy](07_SECURITY_BY_DESIGN.md) is the current design guide and
[CI and security gates](security/CI_SECURITY_GATES.md) lists the automated checks.
The dated reviews below record the scope and findings at the time:

- [Phase 6 ASVS 5.0 review](security/PHASE6_ASVS_REVIEW.md), 6 September 2026.
- [Improvement security review](security/IMPROVEMENT_SECURITY_REVIEW.md), 6 September 2026.
- [Administrator workspace review](security/ADMIN_WORKSPACE_REVIEW.md), 6 September 2026.
- [AI connection controls review](security/AI_CONNECTIONS_REVIEW.md), 6 September 2026.
- [Native Bedrock review](security/BEDROCK_REVIEW.md), 6 September 2026.
- [Automated research review](security/AUTOMATED_RESEARCH_REVIEW.md), 6 September 2026.
- [Personal MFA review](security/MFA_REVIEW.md), 6 September 2026.
- [Report assessment review](security/REPORT_ASSESSMENT_REVIEW.md), 6 September 2026.
- [API base image triage](security/API_BASE_IMAGE_TRIAGE.md), 6 September 2026.
- [Isolated report renderer review](security/ISOLATED_REPORT_RENDERER_REVIEW.md), 8 September 2026.
- [Report document release checks](security/REPORT_DOCUMENT_RELEASE.md), 8 September 2026.
- [Research workspace review](security/RESEARCH_WORKSPACE_REVIEW.md), 11 September 2026.
- [Map news and evidence review](security/MAP_NEWS_EVIDENCE_REVIEW.md), 13 September 2026.
- [Research and subscriptions review](security/RESEARCH_SUBSCRIPTIONS_IMPLEMENTATION_REVIEW.md), 14 September 2026.

## Engineering records

[Development workflow](DEVELOPMENT_WORKFLOW.md) defines Jira acceptance and
GitHub handoffs. [Parallel development](PARALLEL_DEVELOPMENT.md) defines checkout
and runtime isolation. The [Codex backlog register](delivery/CODEX_BACKLOG_2026_09_30.md)
records the current grouped delivery scope and outstanding operational acceptance.

[CLAUDE.md](../CLAUDE.md) records contributor rules. These documents track how the
app is built; they do not replace checking the current code and tests.

- [Implementation plan](MASTER_IMPLEMENTATION_PLAN.md): the maintained status record and checklist.
- [Development story](DEVELOPMENT_STORY.md): chronological record of the build.
- [Product direction](OSINT_PRODUCT_DIRECTION.md): the automated-research product objective from 6 September 2026.
- [Automated research plan](MASTER_AUTOMATED_RESEARCH_PLAN.md): delivered research milestones and open acceptance items.
- [Research and subscriptions plan](RESEARCH_SUBSCRIPTIONS_IMPLEMENTATION_PLAN.md), with its [task packets and execution log](plans/research-subscriptions/EXECUTION_LOG.md).
- [Performance repair](PERFORMANCE_REPAIR.md), with the [backend](PERF_BACKEND_AUDIT.md) and [rendering](PERF_RENDERING_AUDIT.md) audits.
- [Source audit records](source-audit/), including the [deployed source health check](source-audit/deployed-health-2026-09-19.md), and the [military infrastructure source register](research/MILITARY_INFRASTRUCTURE_SOURCE_REGISTER.md).

## Archive

Finished plans, implementation contracts, dated audits, reviews and the original
proposal are kept in the [archive](archive/README.md). They describe past states of
the app, not current behaviour.
