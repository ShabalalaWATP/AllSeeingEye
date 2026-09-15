# Teams, profiles and AI usage: implementation plan

Date: 15 September 2026. Status: proposed implementation specification following Alex's approved product direction. Application implementation has not started under this plan.

## 1. Outcome and scope

Any active account can create a team. Its creator becomes a team Manager in the same transaction. Members can collaborate through shared research and a simple message board. Managers maintain membership and leadership. Site administrators retain oversight, protected membership and exclusive control of AI assignments and allowances.

Use two site roles, User and Administrator, and two independent membership roles, Member and Manager. Team leadership does not elevate site privileges. One person can manage several teams and be a Member elsewhere.

Deliver the complete vertical paths below, including persistence, permissions, UI, migrations and tests. A schema or API without a usable screen is not a finished phase. Do not expand this work into a map redesign or a project-management suite.

## 2. Existing implementation to extend

| Area | Existing integration point | Required change |
| --- | --- | --- |
| Account roles | `backend/src/ase/domain/users.py` | Retire global `manager` after compatibility migration |
| Team authority | `application/teams/service.py`, `application/access.py` | Replace dual global/team Manager requirement with team membership authority |
| Membership persistence | `adapters/persistence/teams.py`, `domain/teams.py` | Atomic creator membership, revision checks and last-Manager invariant |
| Team API | `api/routers/teams.py`, `api/team_schemas.py` | Bounded roster, invitations, member-role changes and leave action |
| Team UI | `frontend/src/features/teams/` | Self-service creation and dashboard |
| Model routing | `application/model_routing.py`, `application/admin/llm_connections.py` | Reuse tested global, personal and team assignments; expose effective policy clearly |
| Profiles | `domain/profile.py`, `application/account/profile.py`, `adapters/persistence/profile.py` | Keep private preferences separate from searchable profile fields |
| Report budgets | `application/report_jobs/`, `domain/subscription_monthly_budget.py` | Integrate with an app-wide persistent allowance ledger |
| Existing assistant | `application/assistant/`, saved chat API | Attribute each request to its authorised personal/team context |
| Subscription pipeline | `application/schedules/`, `container/subscription_*` | Charge scheduled work to its frozen destination and enforce current authority |

The current monthly report policy has fixed owner/subscription ceilings. It is not an administrator-configurable allowance covering every LLM entry point. Current model routing already selects personal overrides for personal work and team overrides for team work, with global inheritance. Preserve that behaviour.

Read ADR 0010 and ADR 0012 before implementation. Add a successor ADR for changed team authority; preserve their historical account of earlier decisions. Check the current migration head before choosing new revision numbers. Other Research/Subscriptions work is already in the working tree and must be preserved.

## 3. Permission contract

| Operation | Member | Manager of this team | Site Administrator |
| --- | --- | --- | --- |
| Create a team | Yes | Yes | Yes |
| Read active joined team | Yes | Yes | Any team |
| Create team research/posts | Yes | Yes | Yes, with explicit team destination |
| Edit own contribution | Yes | Yes | Yes |
| Manage others' team contributions | No | Yes, using existing version/history rules | Yes |
| Invite ordinary accounts | No | Yes | Yes |
| Directly add an account | No | No | Yes |
| Promote/demote ordinary team members | No | Yes | Yes |
| Remove ordinary members/Managers | No | Yes | Yes |
| Remove/demote an Administrator membership | No | No | Another Administrator only |
| Rename, describe or archive team | No | Yes | Yes |
| Restore archived team | No | No | Yes |
| Set models or increase allowances | No | No | Yes |
| View team usage | Own attributed usage | Aggregates and member totals | Full administrative usage |
| Change site roles/deactivate accounts | No | No | Yes, existing protected admin rules apply |

An administrator's site access does not require team membership. Membership deletion never deletes a site account. Administrator protection is checked from the target's current site role, not from stale roster data. An Administrator requesting their own removal is directed to another Administrator, following the requested protection rule.

### Invariants and lifecycle

- Team creation and its first Manager membership commit together or neither commits.
- Every active team retains at least one active Manager. Concurrent demotions, removals and self-leave cannot remove the last one. Site administrators have a recovery route but cannot silently leave an active team managerless.
- Before deactivating the last active Manager's account, administrators appoint a replacement or archive affected teams. Preserve protection of the last active site Administrator separately.
- Ordinary Managers can remove or demote peers, including the original creator, provided another active Manager remains. `created_by` records history and is not a permanent ownership privilege.
- Leave is explicit. Team-authored material remains with the team, with attribution intact. Removing a member revokes their access, including to material they authored there.
- Personal content is never moved by changing a workspace selector. Sharing uses existing authorised sharing functionality; where unsupported, implement an explicit reviewed copy retaining origin references. Do not mutate original scope.
- Archive preserves reports, membership and board history as read-only. Stop new jobs, invitations and scheduled dispatches. Recheck authority before releasing an in-flight result. Default to archival; permanent team erasure is a separate future retention design.
- Member removal stops that person's scheduled team dispatches. Managers see an action-needed entry and can create a reviewed replacement subscription. Do not silently impersonate a replacement owner.
- Refresh open clients on membership changes through the existing access-change mechanism. APIs always enforce the same rule independently.

Proposed initial abuse controls: up to five active teams created per ordinary account, 100 members per team and 20 outstanding invitations per team. Site administrators can adjust these independently of AI allowances. Account eligibility means active authenticated account; no new subscription/payment requirement.

## 4. Profiles, directory and invitations

### Profile fields and visibility

Preserve current language, appearance, research and export defaults. Add an independently serialised directory profile:

| Field | Proposed constraint | Visibility |
| --- | --- | --- |
| Username | Unique case-insensitive handle, 3–32 ASCII letters/digits/underscore; reserve system names | Directory when discoverable; exact handle invitation otherwise |
| Display name | Existing 1–120 printable characters | Team roster and permitted directory |
| Avatar | Optional JPEG/PNG/WebP, maximum 2 MB, decode/re-encode and remove metadata | Same as display name |
| Job title / organisation | Optional, each up to 120 characters | Owner-selectable directory fields |
| Biography | Optional plain text, up to 500 characters | Owner-selectable |
| Country | Optional validated country code | Owner-selectable |
| Languages / expertise | Bounded validated languages and up to ten bounded expertise labels | Owner-selectable |
| Timezone | Existing IANA timezone | Private by default; optional roster display |

Organisation and expertise are self-described, not verified affiliations. Never expose login email, MFA state, session history, private interests or individual prompts through directory results. Existing accounts remain excluded from broad directory search until they opt in; assigning or choosing a handle must not disclose their email. Directory visibility is independent of team roster visibility.

Search supports name, exact username and organisation. Use server pagination, 20 results/page and a bounded result window; require at least two characters and rate-limit searches. No anonymous directory or bulk account export. Exact handles can invite a non-discoverable account with a generic submission response. Administrative account search remains separate and audited.

### Invitation flow

1. Manager selects Add people, searches and chooses an account.
2. Send an in-app invitation as Member, with optional short note. Elevate to Manager after acceptance through a separate explicit action.
3. Recipient sees team name, description and inviter; accepts or declines.
4. Acceptance rechecks account/team status and inviter's current authority. A revoked invitation does not grant membership.
5. Managers can withdraw invitations. Default expiry is seven days. Resending is rate-limited and does not create duplicate pending invitations.

States: pending, accepted, declined, withdrawn, expired. Use database uniqueness for pending team/recipient pairs. Acceptance is idempotent and atomic with membership creation. Administrators may add active accounts directly, with an in-app notice and audit event. No external email delivery in the initial release.

## 5. AI assignment and allowance policy

### Assignment resolution

Personal task: individual override, then site default. Team task: team override, then site default. A person's personal model override does not change a team's provider. If an administrator sets a user-level provider restriction incompatible with the team assignment, deny the request with a clear reason rather than falling back silently.

Use existing encrypted connection profiles and configuration test/confirmation flow. Show current effective model, where it was inherited from, and the number of affected accounts/team members. Team Managers can view their allowance and request a change in-app, but cannot edit keys, provider endpoints, models or limits. Basic/Deep/Advanced denote research depth and remain separate from model thinking settings.

Freeze the model configuration and destination for admitted jobs. Normal assignment changes affect new jobs. An administrator's explicit emergency disable blocks future outbound calls even for admitted work. Current membership and active-account checks apply at every stage and before result delivery.

### Administrator controls

Provide Defaults, Users, Teams and Usage sections under AI Access & Usage:

- Daily/monthly task counts, input/output token limits and maximum concurrent tasks.
- Per-task ceilings on provider calls and token reservations, and permitted research depths.
- Feature access for Ask Eye, research, subscriptions, geolocation and other model-backed analysis.
- Personal allowance, shared team allowance and optional member-within-team ceiling.
- Optional global per-person ceiling spanning all teams, preventing team creation from bypassing limits.
- Optional dated temporary overrides, with explicit inheritance, blocked and unlimited states. Zero must never mean unlimited.
- Site-level ceiling and separate system-work budget for shared feeds, global summaries, translation and indexing.

New teams inherit a site-controlled default. Creating more teams must not create unrestricted independent spending pools: every call also checks the site ceiling and the configured cross-team actor ceiling. Do not invent initial production spending amounts. Roll out in observation mode using recorded usage, then let administrators activate limits deliberately.

### Accounting contract

Record one underlying provider-call event with initiating actor, destination owner/team, logical task, feature, provider/profile revision and reservation id. Attribute that same event to the relevant limits without duplicating it in overall usage totals.

One user action is one logical task; each internal model call is a separate provider call. Report both. A retry may make another billable call, but refreshing a page does not create a second task. Subscription attempts retain their original edition identity.

- Reserve estimated input plus maximum completion usage atomically before dispatch. Refuse or queue work before calling the provider if any applicable ceiling is insufficient.
- Use fixed UTC calendar days/months initially, showing exact reset time in the user's timezone. Attribute reservations/calls to dispatch period, even if they settle after reset.
- Release unused reservation on confirmed cancellation before dispatch; settle actual usage once after a completed call.
- Provider timeouts after dispatch remain unknown/pending. Hold the reservation until reconciled or explicitly reviewed. Do not automatically release it or resend uncertain paid work.
- Handle reasoning, cached tokens, image usage and tool charges without double counting. Unknown metrics remain unknown. Hard enforcement requires a supported conservative reservation for that feature/provider, otherwise block under that policy with an explanation.
- Persist reservations and settlement through restarts. Enforce counters with database transactions and deterministic lock ordering across site, actor and team dimensions, including multiple workers.
- Reuse report/subscription ledgers through adapters. Preserve per-job safety ceilings and avoid charging the same report call through both old and new monthly policies.
- Optional cost limits require dated configured prices and explicit currency. Distinguish estimated cost from provider billing. Unpriced models cannot satisfy a claimed hard monetary cap.

At 80% show a discreet warning; at exhaustion show which allowance blocked the action and when it resets. Existing saved outputs remain readable. Scheduled work records allowance-exhausted state and its next eligible action without busy retry loops.

Inventory and integrate every outbound model path: Ask Eye and report Q&A, Research stages/challenge/translation, subscriptions, image geolocation, economy/cyber/live summaries, conflict screening, embeddings/indexing and administrator connection tests. Charge shared unattended tasks and connection tests to explicit system/admin budgets rather than an arbitrary user. No feature is declared covered before its call sites are verified.

## 6. Team dashboard and board

Entry through User menu > My teams and a persistent labelled personal/team selector in relevant workflows. Do not add another permanent global navigation item. Remember selection only as a UI preference; it never grants access or automatically redirects existing personal jobs.

Team header: name, short description, current role, member count, Create research and Invite people when authorised. Four tabs:

| Tab | First-release contents |
| --- | --- |
| Overview | Pinned announcement, five recent shared reports, next five subscription runs, team allowance summary and membership/failed-run actions |
| Research | Paginated reports, briefs and subscriptions with search, owner, topic and status filters; exact-version report links |
| Board | Posts and one-level replies, pinned messages, links to authorised reports/areas and simple unread indicator |
| Members | Paginated directory-style roster, role filter, pending invitations, promotion/demotion/removal and leave |

Manager settings contain team name/description, moderation, archive and an AI policy summary. Administrator-only controls appear in administration and can deep-link to the team's policy editor. Do not expose administration routes or credentials to ordinary accounts.

Board: plain text up to 4,000 characters/post and 2,000/reply; 20 posts/page; up to three pinned posts. Members edit/delete their own posts. Managers can pin or remove any ordinary post with an audit reason. Content moderation is distinct from membership protection: an Administrator's account cannot be removed by a Manager, but team moderation can hide a post under the same moderation policy. Preserve edit timestamps and moderator tombstones; do not claim tamper-proof history. No rich HTML, arbitrary embeds, file attachments, direct messages or live typing in v1.

Internal links recheck destination access when opened; URL previews must not fetch arbitrary external addresses. Archive stops writes. Use visibility-aware bounded polling initially, with no new socket service. Provide empty, loading, retry, revoked-access and permission-conflict states; preserve drafts during refresh.

## 7. Data and API design

Extend existing tables where coherent; keep new responsibilities separate:

- Team: description and monotonic revision. Membership: revision and existing role/join timestamp. Unique `(team_id, user_id)` remains mandatory.
- Directory profile: stable user id, normalised unique username, bounded optional fields, visibility settings and revision. Avatar storage uses the existing local asset mechanism where suitable.
- Invitation: team, recipient, inviter, timestamps, state and revision; indexes for recipient inbox and team pending list.
- Board post/reply: team, author, text, parent id, edit/deletion timestamps and revision. Validate same-team parent. Store unread cursors separately per membership.
- AI policy: scope, immutable revisions, inherited fields, effective/expiry timestamps and actor. Team-member overrides reference membership and cannot survive removal as active authority.
- Usage: immutable call receipts and adjustments, reservations, per-period counters and concurrency leases. Index by period, destination, actor, feature and task. Store metadata only, never keys or prompts.

Proposed API surface, reconciled with existing routes before coding:

| Route | Purpose |
| --- | --- |
| `POST /api/teams` | Create team and Manager membership atomically |
| `GET/PATCH /api/teams/{id}` | Team information and revision-checked updates |
| `GET /api/teams/{id}/members` | Paginated roster |
| `PATCH/DELETE /api/teams/{id}/members/{user_id}` | Explicit role change or removal |
| `POST /api/teams/{id}/leave` | Last-Manager-safe departure |
| `GET/POST /api/teams/{id}/invitations` | List/send; separate withdrawal action |
| `GET /api/me/team-invitations` | Recipient inbox |
| `POST /api/me/team-invitations/{id}/accept-or-decline` | Implement as two explicit action endpoints |
| `GET /api/directory/users` | Bounded authorised discovery |
| `GET/PATCH /api/me/directory-profile` | Owner-controlled searchable fields |
| `GET /api/teams/{id}/dashboard` | Bounded summary without loading all content |
| `GET/POST /api/teams/{id}/board/posts` | Board listing and creation |
| `PATCH/DELETE /api/teams/{id}/board/posts/{post_id}` | Revision-checked edit/moderation |
| `GET /api/me/ai-usage`, `GET /api/teams/{id}/ai-usage` | Authorised totals and effective allowances |
| `/api/admin/ai-policies` | Revisioned scope policy list/create/update and effective preview |

Retain existing tested model connection/assignment endpoints. Deprecate old email-based direct member PUT safely: Manager calls use invitations; direct insertion is Administrator-only. Never leave the old route as a privilege bypass. Use strict bounded schemas, 409 for stale revisions and 404 for inaccessible object ids. Regenerate OpenAPI and clients together.

## 8. Ordered implementation tasks

All tasks below are Pending. Each is a separately reviewable milestone with tests and an execution-log entry.

| ID | Depends on | Work and completion criterion |
| --- | --- | --- |
| T00 | None | Inventory nested guidance, migration heads, team access callers, model call sites and UI routes. Capture baseline failures and add successor authority ADR. No runtime change. |
| T01 | T00 | Implement membership-only management, atomic team creation, last-Manager and protected-Administrator rules. Race and negative-permission tests pass. |
| T02 | T01 | Compatibility migration for global Managers; update API/admin UI role choices. Preserve memberships, invalidate changed-role sessions and resolve managerless legacy teams explicitly. |
| T03 | T01 | Invitations, direct admin addition, self-leave, revocation and archive effects. API and persistence complete with accepted/expired/race tests. |
| P01 | T00 | Profile validation, directory visibility, unique handles, bounded discovery and safe avatar processing. Existing profile preferences remain readable. |
| P02 | T03, P01 | Profile editor, people picker, invitation inbox and roster controls. Keyboard, same-name disambiguation and privacy tests pass. |
| Q01 | T00 | Define task/call accounting, policy precedence and provider usage adapters. Publish model-call coverage inventory and fixtures. |
| Q02 | Q01 | Durable reserve/settle/reconcile ledger, period counters and concurrency leases. Multi-worker overspend and restart tests pass. |
| Q03 | Q02 | Integrate report, subscription, Ask Eye and geolocation dispatch paths; then all shared/system paths. Verify every inventory entry, no double charges. |
| Q04 | Q03 | Administrator policy screens, individual/team assignments, effective-policy preview, temporary overrides and user usage display. Enable observation mode first. |
| D01 | T02, P02 | My teams entry, creation journey, personal/team context and dashboard shell with server-provided capabilities. No client-only permissions. |
| D02 | D01 | Overview and shared Research lists, exact report links and subscription action-needed states. Bounded queries demonstrated on large fixtures. |
| D03 | D01 | Message board API/UI, replies, edit, moderation, pins and unread cursors. Cross-team id and XSS tests pass. |
| D04 | D02, D03, Q04 | Finish usage widgets, archive/restore UX, mobile layouts, focus management and reduced motion. |
| V01 | All above | Full integration, security review, supported-database migration/recovery checks and authenticated browser journeys. Record failures honestly. |
| V02 | V01 | Operator migration checklist, monitoring, rollout switches and bounded live provider smoke. Operational enablement is separately evidenced. |

Implementation lanes can be separated after T00 into team authority, profiles/invitations and usage accounting. Assign explicit file ownership if delegation is used. One integration owner regenerates contracts and resolves migrations after each lane settles.

## 9. Migration and release safety

Use an expand/migrate/contract sequence. Temporarily read legacy global Manager values while authorising from membership. Stop creating new global Manager accounts. Convert existing ones to User while preserving team-manager memberships, bump affected security versions and expire sessions. Remove legacy enum/check constraints only after application compatibility is established.

Inventory legacy active teams with no active Manager. Where the active creator is already a member, explicitly grant Manager under the migration policy and audit it. Otherwise record an administrative remediation requirement; do not infer or add outsiders. Keep those teams in restricted recovery state until repaired.

Test populated SQLite and disposable PostgreSQL upgrades, foreign keys, unique constraints and concurrent transactions. Select migration ids after the current head. Back up before an operator upgrade and rehearse restoration. Prefer rollback by disabling new features with a compatible binary; never drop board/usage records to roll back a release.

Feature switches: self-service team creation, directory, board and allowance enforcement. Usage observation must not imply hard limits are active. Existing quotas remain effective until the replacement covers their paths. No production migration, credential change or external invitation is part of writing this plan.

## 10. Acceptance and security matrix

- Permission matrix for User, Manager, Administrator, inactive user, removed member and archived team, through both old and new endpoints.
- Concurrent creator/member writes, final-Manager leave/demotion, Administrator protection and role changes during external calls.
- Removed membership blocks reports, exports, search, saved report chats, board reads and future subscription dispatch. Clear stale client data.
- Directory hiding, exact-handle invitations, no email/security-field leakage, duplicate names, handle collisions and bounded search.
- Invitation acceptance versus withdrawal/archive/removal races; duplicate accepts create one membership.
- Personal/team provider resolution, inherited policy, stale tested configuration, emergency disable and no destination manipulation.
- Allowance races across workers, input/output reservation, unknown provider outcome, cancellation, duplicate callback, period rollover, temporary override expiry and system attribution.
- Counter reconciliation from immutable receipts; no negative balances or double-counted provider calls. Joining/creating teams cannot bypass actor/site ceilings.
- Board stored XSS, cross-team reply ids, stale edits, moderation and unread pagination. Validate avatar bytes/dimensions and strip metadata.
- Browser: create team, invite/accept, promote peer, leave, run personal/team task, observe allowance block, share authorised report, post/reply and archive. Check narrow layouts, keyboard and screen-reader labels.
- Preserve repository coverage thresholds. Run focused tests per milestone; broad release tests on a settled snapshot. Distinguish deterministic fixtures from live provider tests and measured cost accuracy.

## 11. Handoff and definition of done

Maintain an execution log next to this plan. Each entry records task id, files, contracts/migrations, exact checks, known limitations and next dependency. Update task status only when its completion criterion is met. Update the master plan and development story when implementation milestones land.

Starter instruction: Read this plan, applicable repository guidance and the current worktree. Start at the first incomplete dependency. Preserve other work. Implement one complete vertical milestone, verify negative permissions and restart/race behaviour where applicable, regenerate contracts when changed, and record evidence. Continue through dependencies without treating a backend-only implementation as a finished user feature.

Release complete means ordinary users can create and manage teams, invite people, use the dashboard and board, and understand their AI allowance; administrators can safely control all memberships, model assignments and usage policies; every model path observes the policy and all required acceptance gates have evidence. Future direct messaging, attachments, advanced project management, automatic private-profile disclosure and monetary billing remain outside this release.
