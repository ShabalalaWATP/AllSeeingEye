# Processing register

Owner, contact, scope, evidence dates and review cadence are in the
[record index](README.md). Alex Orr determines this installation's purposes and
means where controller duties apply. This inventory records activities supported
by the reviewed code, not a claim that every optional activity has occurred.
The primary context is EU GDPR and Finland's Data Protection Act 1050/2018.

The activity inventory supports the records described in
[GDPR Article 30](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng).
Necessary access/security processing, requested research and correspondence have
distinct purposes. The notice's purpose-specific explanations are not a blanket
lawful basis for all public-source information. KAN-185 owns the corresponding
necessity, balancing, Article 9/10 and Article 14 decisions.

Each activity below inherits the [recipient and transfer register](PROCESSORS_AND_TRANSFERS.md)
and the [retention schedule](RETENTION_SCHEDULE.md). Recipient IDs P1-P9 identify
roles and location limits. Authorised operators and scoped members are recipients
where stated; sharing does not make them contracted infrastructure processors.
Hosting/backups (P1/P9) cover persisted application records across the activities.

## R01: access requests and accounts

Purpose: admit authorised users and maintain access. People: applicants and users.
Data: email, display name, request reason, approval/status, password hash and profile
details, supplied by the person and administrator. Recipients: administrator,
application host (P1), SMTP and recipient mailbox (P3/P4) for account messages.
Safeguards: bounded requests, uniform public responses, password hashing and hashed
activation/reset links. See [account requests](../../backend/src/ase/application/auth/account_requests.py)
and [password hashing](../../backend/src/ase/adapters/security/hasher.py).
Retention: T01-T03; deactivation is not account erasure (KAN-238/KAN-240).

## R02: authentication, MFA and sessions

Purpose: authenticate users, prevent session abuse and recover access. People:
users. Data: credentials/factor secrets, challenge and recovery hashes, refresh
family, IP, user-agent and activity timestamps from authentication requests.
Recipients: application host; email MFA uses P3/P4; authenticator enrolment sends
its secret to the enrolling user's device. Safeguards: encrypted secrets, hashed
tokens, current-user/security-version checks and release fences, described in
[MFA operations](../MFA_OPERATIONS.md) and
[current-session checks](../../backend/src/ase/application/auth/current_session.py).
Retention: T03-T04; expiry and sensitive-material cleanup differ (KAN-238).

## R03: audit, abuse prevention and AI accounting

Purpose: investigate security events, enforce allowances and explain model usage.
People: users/applicants and people named in recorded subjects. Data: actor, action,
time, IP, identifiers, event details, model/token/cost and allowance records.
Recipients: administrator, P1 and recovery custodians. Audit details can include
account email and report title; they are not universally anonymous or content-free.
Safeguards: guarded administration, secret-key log redaction and bounded container
logs. See [audit persistence](../../backend/src/ase/adapters/persistence/audit.py)
and [logging](../../backend/src/ase/infrastructure/logging.py).
Retention: T05-T07/T18; KAN-239 and KAN-241 cover incomplete cleanup.

## R04: teams, directory and shared work

Purpose: consensual team participation and controlled collaboration. People:
users/invitees; data: handles, profile/avatar, roles, invitation receipts and
authored contributions. Recipients: current authorised members/managers and
administrator; directory visibility follows discovery settings. Safeguards:
scope-based [access policy](../../backend/src/ase/application/access.py), current
membership checks, last-manager protection and
[opaque invitation receipts](../INVITATION_PRIVACY.md).
Retention: T01/T11-T12; archive preserves history and restricts ordinary writes.
Shared ownership must be reviewed before removal (KAN-240).

## R05: research, saved reports, briefs and search

Purpose: answer selected questions and retain reviewable evidence. People:
researchers and source subjects, including public figures/private people. Data:
questions, source text, names, locations, allegations, assessments, provenance,
versions, comments, embeddings and usage. Inputs: public sources, users and prior
saved work. Recipients: scoped readers/administrator, selected AI/embedding
provider (P2), requested exports (P9). Safeguards: access checks before and after
external work, structured output, explicit evidence lineage and scoped search.
See [model routing](../../backend/src/ase/application/model_routing.py),
[search](../../backend/src/ase/application/reports/search.py) and
[research operations](../RESEARCH_WORKSPACE_OPERATIONS.md).
Retention: T07/T11-T13/T15. Saved copies need separate necessity review; KAN-185
addresses incidental sensitive/offence data and indirect notice, KAN-240 removal.

## R06: private documents, media and photo analysis

Purpose: analyse user-selected material. People: uploaders and depicted/mentioned
people. Data: filenames/hashes, extracted text, sanitised frames, selected location
hints and hypotheses. Recipients: isolated local parser, selected AI provider
when needed (P2), then report readers if saved. Production Compose selects a
networkless parser with bounded resources; photo transmission requires explicit
confirmation. See [parser wiring](../../backend/src/ase/container/research_inputs.py)
and [photo analysis](../../backend/src/ase/application/research/photo_geolocation.py).
Retention: T11/T14-T15. Receipt expiry does not remove frozen job/report material.
No automated universal sensitive-data detection is claimed (KAN-185/KAN-240).

## R07: alerts, subscriptions, feeds and notifications

Purpose: deliver requested monitoring results. People: users/team members and
subjects of monitored material. Data: rules, alert IDs, preferences, outcomes,
delivery credentials and optional report titles. Recipients: scoped readers,
P3/P4 mailboxes, user-selected feed readers, browser push services and configured
webhooks (P7). Safeguards: authority/preferences rechecked before delivery,
encrypted destination credentials, validated HTTPS push endpoints and opaque
push alert IDs. See [notifications](../NOTIFICATIONS.md), [push](../WEB_PUSH.md)
and [alert routing](../ALERT_ROUTING.md). The separate installation-wide webhook
would copy across scopes if configured; none was observed on 11 October.
Retention: T08-T12/T20; KAN-239/KAN-241/KAN-242 cover conditional or missing cleanup.
Private-feed hashes, preferences and disabled encrypted webhook destinations need
separate lifecycle review/removal under KAN-240.

## R08: enquiries and rights correspondence

Purpose: respond to enquiries and exercise privacy/accessibility rights. People:
correspondents; data: name, email, organisation/role, deployment interests, message,
case decisions and proportionate verification. Enquiries reach administrator/P1
and, if configured, the operator mailbox through P3. Enquiry email contains the
full submitted fields/message. Direct privacy email instead uses Yahoo/P4 and
does not become an application enquiry automatically. Safeguards: bounded,
deduplicated admission, admin-only retrieval and deletion; avoid credentials and
identity documents in ordinary email. See
[enquiries](../../backend/src/ase/application/enterprise_enquiries.py) and
[rights procedure](../PERSONAL_DATA_OPERATIONS.md).
Retention: T16/T19; the enquiry recipient was unconfigured in the dated observation.

## R09: public-source collection and external research

Purpose: obtain relevant public events and selected source evidence. People:
publishers, source subjects and researchers. Data: event text, identity/location,
URLs, search terms and collection metadata. Recipients: publishers/search services
(P5), optionally translation/screening models (P2). A private research plan can
generate provider queries containing selected terms. Safeguards: public-address
fetch restrictions, source/size budgets and bounded public live cache. See
[feed HTTP controls](../../backend/src/ase/adapters/feeds/http.py) and
[source coverage](../02_DATA_SOURCES.md). Commercial source admission establishes
licensing eligibility, not a personal-data processing basis.
Retention: T13/T17; evidence selected into reports follows R05 instead.

## R10: maps, cameras, media and device storage

Purpose: display requested maps/media and preserve user choices. People: visitors,
users and potentially depicted people. Data: browser IP/details, tile locations,
media selections and local preferences. Recipients: direct map/imagery hosts and
selected embeds (P6); Ordnance Survey tiles use the application proxy.
Safeguards: [external-media choices](../EXTERNAL_MEDIA_PRIVACY.md), provider
allowlists and the [storage inventory](../../frontend/src/features/public-policy/storage.json).
Map tile requests are separate from iframe consent. KAN-185 assesses necessity or
consent per storage purpose under Finnish rules; no blanket exemption is asserted.
Retention: browser inventory and T19; external provider copies remain separate.

## R11: archive capture

Purpose: preserve cited public sources for evidence review. People: source subjects
and researchers; data: selected cited public URLs, which may themselves identify
people or reveal interests. Recipient: Internet Archive (P8). Capture can create
an independently retained public copy. The app sends URLs, not report prose.
See [archive use case](../../backend/src/ase/application/reports/archiving.py).
Retention: T19 and archive provider policy. Enabled in the dated observation;
`ASE_ARCHIVE_ENABLED=false` disables attempts. KAN-185 owns source-specific
necessity/disclosure assessment; app deletion cannot recall a capture.

## R12: backup, recovery, logs and rights handling

Purpose: recover service, diagnose failures and honour requests. People/data:
everyone and all categories represented in backed-up records; bounded runtime
diagnostics. Recipients: operator-controlled host/storage and optional remote
custodians/export recipients (P1/P9). Safeguards: encrypted verified scheduled
archives, separately protected keys, scoped exports and explicit restore targets.
See [backup/recovery](../BACKUP_RESTORE.md) and
[scheduled backup](../../scripts/scheduled_backup.py). An archive round-trip drill
alone is not proof of complete database recovery. Retention: T18-T19; KAN-243
tracks reconciliation of later erasure decisions and external-copy reviews.
