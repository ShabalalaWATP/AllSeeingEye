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

## Configure and operate

- [AI connections](AI_CONNECTIONS_OPERATIONS.md) and [AI cost controls](AI_COST_CONTROLS.md), including per-user research tiers.
- [Sources and connections](SOURCES_AND_CONNECTIONS.md), [source provenance](SOURCE_PROVENANCE_OPERATIONS.md) and [catalogue browsing](SOURCE_CATALOGUE_BROWSING.md).
- [Account security and MFA](MFA_OPERATIONS.md) and [administration](ADMINISTRATION.md).
- [Account email setup](EMAIL_SETUP.md): provider choice, SMTP settings and delivery checks.
- [Self-hosting](DEPLOYMENT.md), [automatic releases](AUTOMATIC_DEPLOYMENT.md) and [backup and restore](BACKUP_RESTORE.md).

## Go deeper

- [Map tools and layers](MAP_TOOLS_AND_LAYERS.md), [radio modelling and terrain evidence](RADIO_MODEL_EVALUATION.md), [map news and evidence](MAP_NEWS_AND_EVIDENCE.md) and [saved map image export](SAVED_MAP_IMAGE_EXPORT.md).
- [Research workspace](RESEARCH_WORKSPACE_OPERATIONS.md), [subscriptions](SUBSCRIPTIONS_OPERATIONS.md), [area research](AREA_RESEARCH.md) and [fresh web research](FRESH_WEB_RESEARCH.md).
- [Aviation](AVIATION_COVERAGE.md), [maritime](MARITIME_COVERAGE.md), [satellites](SATELLITE_COVERAGE.md), [cyber intelligence](CYBER_THREAT_INTELLIGENCE.md), [economy](ECONOMY_WORKSPACE.md) and [Ukraine](UKRAINE_WAR_TRACKER.md).

## Work on the code or docs

[CLAUDE.md](../CLAUDE.md) records contributor rules. The [API contracts](api/)
and [architecture decisions](adr/) explain individual interfaces and design choices.
The [research allowance API](api/RESEARCH_ALLOWANCES_API.md) covers tier assignment,
usage and reset information.
The architecture guide links the editable [Structurizr model](diagrams/workspace.dsl)
and [diagram maintenance instructions](diagrams/README.md).

Screenshots show the real interface with illustrative local data. Their
[capture notes](images/README.md) explain what is and is not represented.
The guides above describe supported behaviour; source health and model availability
must be checked in the installation you are using.
