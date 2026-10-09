# Scoped operational work and reports

Status: current implementation, 6 September 2026. Every route below requires
bearer authentication. Request/response fields are defined by FastAPI and the
exported OpenAPI schema. See [authentication](AUTH_API.md) and
[team management](TEAMS_API.md) for identity and membership operations.

## Scope rules

AOIs, collection plans, reports, indicators and schedules carry nullable
`team_id`. Omitting it on creation creates personal work owned by the actor.
Personal work is visible to its creator and administrators. Team work is visible
to current members of that team and administrators, including historical versions.
An author removed from a team loses access to its team work and keeps personal work.

Current members create team contributions and manage their own. A global
`manager` with that team's manager designation can manage other contributions.
Administrators have explicit operational access to all scopes. Archived teams
remain readable; ordinary writes stop, while administrators retain a manual
operational override. Team background work always requires an active team and
current owner membership, including administrator-owned jobs.

Linked AOIs/plans/reports must share a team, or the same owner when personal.
Administrator capability does not waive link compatibility. Content updates do
not transfer records between scopes. Invalid links require repair, rather than
silently copying another owner's configuration or widening access. Lists apply
visibility in SQL before limits. Direct ids outside the read scope return 404;
insufficient write authority over a visible record returns 403.

Protected operational responses use `Cache-Control: no-store`; document downloads
retain `private, no-store`. These controls do not recall a document already
downloaded by a previously authorised user.

## Direction, warning and schedules

| Resource | Routes | Scope details |
|---|---|---|
| AOIs | `GET/POST /api/direction/aois`; `DELETE /api/direction/aois/{id}` | Country or bounding-box area; list is scoped |
| Plans | `GET/POST /api/direction/plans`; `GET/PUT/DELETE /api/direction/plans/{id}` | Creation/update validates linked AOI scope; direct read includes matched live evidence |
| Indicators (alert rules) | `GET/POST /api/warning/indicators`; `PUT/DELETE /api/warning/indicators/{id}` | Linked plans must share scope; background evaluation rechecks eligibility. `PUT` edits, pauses or resumes and needs `expected_updated_at` (409 when stale, one conditional update); removing every location, category or keyword restriction needs `confirm_wider_scope`; country codes and keywords over 60 characters are rejected, never truncated. A resumed rule counts only items published after it resumed (`resumed_at`, migration 0079) |
| Alerts | `GET /api/warning/alerts`; `POST /api/warning/alerts/{id}/ack` | Persisted creator/team scope survives indicator deletion; acknowledgement is authorised separately |
| Schedules | `GET/POST /api/schedules`; `PUT/DELETE /api/schedules/{id}` | Linked plans must share scope; generated reports retain the originating scope |

Alert listing accepts `hours` from 1 to 720 and `limit` from 1 to 200, defaulting
to seven days and 50 results. `unacknowledged` counts the returned visible page,
not all alerts in the system.

### Ownership scope for alert and research progress lists

`GET /api/warning/alerts` and `GET /api/report-jobs` take `scope=mine|all`. The
default, `mine`, is the caller's personal records plus records of teams they
currently belong to, for every role, administrators included. Only administrators
may request `all` (others receive 403); it restores the broad administrative view.
The scope is a SQL filter applied before limits, cursors and counts, so another
person's records cannot displace the caller's. It selects a view and grants
nothing: direct reads and acknowledgement keep the existing object-level checks.
List rows for personal records carry `owner_name`, the owner's display name, and
research jobs carry `owner_id`; team rows are identified by `team_id`. The shell's
notification bell never requests `all`. In the interface, the administrator's
choice is kept in the address as `?scope=all`, and acknowledging another user's
personal alert first names the owner and explains that acknowledgement is shared. Any current member of an active team may acknowledge
its alerts; this shared triage action does not require ownership or leadership.
Personal alerts require the owner or administrator. Archived teams remain
read-only for ordinary users. Missing-indicator legacy alerts with no known owner
are administrator-only. Public feed events stay shared and transient; the app
does not persist a separate raw feed per team.

## Reports and versions

| Method and path | Request | Result |
|---|---|---|
| `GET /api/reports/templates` | None | Available report templates |
| `GET /api/report-methodology` | None | Current versioned contribution matrix, rules, grade labels, PHIA bands and doctrine references |
| `GET /api/reports` | `limit=1..200` (default 50), `offset>=0`, optional `origin=research/subscription/geolocation/briefing` or `group=requested` (not both) | `{items, limit, offset, has_more}`; each item carries its effective `origin`. Current access and origin filters apply in SQL before pagination. Missing or unrecognised legacy origins use the report's original classification fallback. `briefing` marks daily, economy and cyber briefings prepared automatically by a workspace visit; the server assigns it and its `scope.briefing` kind, and request bodies cannot. `group=requested` lists research, subscription and geolocation reports only (never briefings) and covers only the caller's latest 1,000 matching reports. |
| `POST /api/reports` | Template, optional `team_id`, `plan`, country/question and supported template options | 201 report and saved version |
| `POST /api/reports/{id}/versions` | None | 201 regenerated version in the original report scope |
| `GET /api/reports/{id}` | Optional positive `version` | Current or requested historical version, subject to current report access |
| `GET /api/reports/{id}/markdown` | Optional positive `version` | Stored Markdown for the authorised version |
| `GET /api/reports/{id}/export/pdf` | Optional positive `version` | Local PDF download |
| `GET /api/reports/{id}/export/docx` | Optional positive `version` | Local DOCX download |
| `GET /api/reports/{id}/diff` | Positive `from_version` and `to_version` | Structural comparison of two versions of that report |
| `DELETE /api/reports/{id}` | None | 204 after authorised deletion |
| `GET /api/reports/{id}/versions/{n}/team-copy-preview` | `team_id` | Disclosure preview: private-input evidence, omitted references, linked personal records not copied, content digest and any existing copy |
| `POST /api/reports/{id}/versions/{n}/team-copies` | `{team_id, disclosed_evidence_labels}` | 201 new team report, or 200 with the existing copy on retry |
| `GET /api/reports/{id}/team-copy-provenance` | None | Who copied this team report, from which version and when; 404 when it is not a copy |

Report production validates the linked plan/AOI both before outbound model work
and before the final save. It ends read snapshots before the external call,
reacquires the shared authority guard afterwards and refuses a changed plan,
lost membership or conflicting regeneration. PDF/DOCX rendering happens off the
event loop and rechecks current report access before releasing its bytes.
Historical exports inherit current access, not membership at creation time.

A team copy publishes one finished personal version to an active team without a
model call or research allowance. Only the report's owner may copy it, and only to
a team they currently belong to; administrators have no override, because a copy
widens access to personal work. The copy keeps the body and figures, findings,
frozen evidence with its content hashes, quality and assessment values under new
report and version identities, and rebinds the frozen source assessment to the new
version (or records it as unavailable if it cannot be rebound exactly). The Research
Brief link, claim generation receipt, retained original passages and identity-bearing
scope keys are omitted; claims, retained originals, reviewed snapshots and saved map
views stay with the personal version. Evidence from uploaded inputs is copied only
when the request confirms exactly the listed labels. Access is checked again under
the administration guard before the copy, its provenance and the audit entry commit
together. One copy exists per source version and team. The provenance endpoint
reveals the personal original's identifier only to its owner or an administrator.

New versions expose their own `period_from`, `period_to` and `data_cutoff`.
Older versions without saved period metadata return null for those fields; the
current report's dates must not be presented as a known historical period.
Frozen evidence and mechanical validation are provenance, not proof of truth or
human review. The exact document rendering limitations and live-model evaluation
gates remain in the current implementation plan and operations guide.

New versions also expose nullable `assessment`. This typed, engine-authored object
records `method_version`, frozen item contributions, per-judgement supporting and
opposing groups, confidence limits/final confidence, explanations, improvement
suggestions, tallies and validation counts. It is not part of the model's response
schema. Legacy absence returns null and does not invoke current scoring. Saved
assessment JSON is decoded strictly; malformed scores are not silently coerced.

Assessment generation occurs after optional advocacy. PDF/DOCX/Markdown and
archiving use the saved assessment; structural comparisons include it. The
methodology endpoint describes current policy without changing historical values.
Its PHIA bands include `range_description`, preserving approximate wording and
the exclusive 0/50/100 boundaries. Numerical bounds remain descriptive vocabulary,
not calculated report probabilities. See [the policy](../REPORT_EVIDENCE_SCORING.md).

## Source reviews and reviewed snapshots

Base path: `/api/reports/{report_id}/versions/{number}`. Responses use
`Cache-Control: private, no-store`.

| Method and path | Purpose |
| --- | --- |
| `GET /source-reviews?label&judgement_id&subject&kind` | Bounded history (at most 100 revisions) for one exact target. |
| `POST /source-reviews` | Record a review or a correction (`previous_id` must name the current revision). |
| `GET /source-assessment-snapshots` | Snapshots of this exact version in the report's scope, newest first, at most 20. Release-fenced. |
| `POST /source-assessment-snapshots` | Freeze current reviews for this version; `subjects` names one subject per key judgement. |
| `GET /source-assessment-snapshots/{id}` | One snapshot, only for its own version and scope. |

- Each kind has its own identity: reliability applies to a source and subject across the
  personal or team scope; credibility to one capture and one judgement's claim;
  authenticity to one capture and its issuer. A credibility review of one claim is never
  shown as a source-wide grade.
- Reading needs current read access. Recording needs write access to the report (owner,
  team manager or administrator) in an active team; a correction to another reviewer's
  history needs that reviewer, a team manager or an administrator. Archived teams are
  read-only.
- A stale `previous_id` returns 409. A full 100-revision history returns 422 with an
  explicit limit message; no revision is discarded and there is no continuation cursor.
- Report reads and exports (`GET /api/reports/{id}`, `/markdown`, `/export/{format}`)
  apply a snapshot only when `version` and `source_snapshot_id` are both given. Without
  one, the original frozen report, grading, likelihood and export content are returned.
- The report reader offers these reviews inside each evidence item and lists snapshots
  in the Sources view. Nothing is selected automatically: the reader chooses a snapshot
  before viewing its reviewed grades or exporting with it.

## Semantic search

| Method and path | Request | Result |
|---|---|---|
| `GET /api/report-search` | None | `{available, indexed, total, limit, batch_size}` |
| `POST /api/report-search/index` | None | Explicit bounded indexing and updated status |
| `POST /api/report-search/query` | `{query: 1..500 characters, limit?: 1..20}` | `{items: [{report, score}], indexed, total}` |

`indexed` and `total` refer to the caller's visible library, bounded to its latest
1,000 reports. `limit` is the shared storage bound of 1,000 vector rows;
`batch_size` is eight. These counts reveal neither another team's report count
nor its index contents. A usable administrator-configured embeddings profile is
required; unavailable configuration returns an explicit state or 409 `no_model`.

The shared index admits free slots before model calls and does not evict another
team's vectors to fit the caller's library. A full index returns 422
`invalid_request` for new slots; already indexed reports remain searchable.
Global maintenance removes orphaned/superseded rows independently of the caller.
Profile fingerprints and version numbers determine whether a stored vector can
be searched. Model calls are limited to 30 per account and 300 per process per
hour; a refusal by either limit spends neither. Indexing runs one operation at a
time per process. Each account may run one query at a time, with at most four
concurrent queries per process. Busy/rate-limited operations return 429. Search rechecks visibility after its outbound call;
indexing rechecks authority/version before saving. No raw live event is indexed.

## Streams, private terms and upgrade

`GET /api/stream` carries shared public events/source health and scoped alerts.
The server rechecks the session and membership before each delivery and every
15 seconds while idle, subject to service scheduling. `access.changed` has an
empty object payload and requires the client to invalidate scoped data and linked
choices. `bye` reports `session_revoked` or `token_expired`.

The social board shows private collection terms only to their personal owner,
current team members and administrators. Background social sampling and Google
News queries ignore inactive owners, revoked owner memberships and archived
teams. Enabled Google News collection sends its terms to Google; resulting
public stories remain shared without private plan/PIR identifiers.

Migration `0014` preserves identifiers, authorship, historical links and frozen
evidence. Existing roots remain personal. Alert ownership is copied from a
surviving indicator; otherwise it remains unknown and administrator-only.
`legacy_scope_conflict` audit entries identify missing or cross-owner links using
ids and reason codes. They do not silently repair links or grant team membership.
No operator database was migrated during development; apply the upgrade to a
backed-up intended database and review those entries before using affected work.
