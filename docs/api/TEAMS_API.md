# Team management API

Current authority follows [ADR 0018](../adr/0018-team-self-service-authority.md).
Paths below have the /api prefix and require bearer authentication under the
[common authentication contract](AUTH_API.md).

## Authority and privacy

Any active authenticated account can create a team. Creation atomically gives
the creator a manager membership. Current manager membership authorises that
team's management; the retired global manager account role is not required.
Team membership never grants global administrator authority.

Members can read their team's roster and saved work, including archived work.
Administrators can inspect all teams. Managers can invite eligible accounts,
promote, demote and remove non-administrator members, and rename or archive
their team. They cannot alter administrator memberships or use global account
administration. An administrator needs another administrator to change their
own administrator membership.

Every active team must retain an active manager. Demotion, removal, self-leave
and account deactivation cannot remove its final active manager. Appoint a
replacement first, or archive the team where appropriate. Inactive managers do
not satisfy the invariant.

Rosters expose user ID, display name, directory username, account role, active
status, membership role and joined_at. They do not expose login email, password
hashes, tokens or security versions. Directory discovery and consent invitations
are separate from authority over existing members.

## Team and membership routes

| Method and path | Request | Success and policy |
| --- | --- | --- |
| GET /teams | None | 200 items; own memberships or all teams for administrators |
| POST /teams | name, optional description | 201 team; active authenticated account |
| GET /teams/{id} | None | 200 team and members; member or administrator |
| PATCH /teams/{id} | name, description, is_active, optional reactivation_manager_id | 200 team; manager/administrator; restoration is administrator-only |
| PUT /teams/{id}/members | email, optional role | 200 membership; administrator-only direct add; other callers refused before email lookup |
| PATCH /teams/{id}/members/{user_id} | role: member or manager | 200 membership; manager/administrator, with target and last-manager safeguards |
| DELETE /teams/{id}/members/{user_id} | None | 204; target and last-manager safeguards |
| POST /teams/{id}/leave | None | 204; cannot leave as final active manager or self-remove administrator membership |
| GET /teams/{id}/ai-usage | None | Members see own usage, managers see aggregates/member totals, administrators may inspect any team |

Names are trimmed printable text of 1 to 120 characters. Descriptions have a
500-character limit; null clears them. Empty updates and extra membership input
fields are rejected. Reassigning membership preserves joined_at. Global role
changes do not create or remove memberships.

## Consent invitations

| Method and path | Purpose |
| --- | --- |
| POST /teams/{id}/invitations | Invite eligible directory recipient_id, with optional note |
| POST /teams/{id}/invitations/by-username | Submit exact username and optional note; generic 202 response |
| GET /teams/{id}/invitations | Manager/administrator sender list |
| DELETE /teams/{id}/invitations/{invitation_id} | Withdraw, optionally checking expected_revision |
| GET /me/team-invitations | Recipient inbox |
| POST /me/team-invitations/{invitation_id}/accept | Consent, optionally checking expected_revision |
| POST /me/team-invitations/{invitation_id}/decline | Refusal, optionally checking expected_revision |

List filters include status, limit (1 to 20) and offset (0 to 1,000). Acceptance
rechecks the current team, recipient and inviter authority before adding a member.
An invitation does not itself grant access. Direct email-based membership writes
are reserved for administrators, not a replacement for manager invitations.

The baseline sender list can expose hidden recipients after exact-handle
submission despite the generic POST response. This gap is tracked in
[KAN-155](https://alex-orr.atlassian.net/browse/KAN-155). This documentation change
does not claim it is repaired. The security batch must replace this paragraph
with the verified opaque-receipt contract when its implementation is integrated.

## Archiving, errors and revocation

Archiving preserves memberships and historical reads. Ordinary operational
writes and background team work stop. Roster mutations and self-leave require
reactivation. Only administrators can restore an archived team, with an active
manager or explicit eligible recovery-manager selection. Administrator manual
oversight of operational records is separate from roster management.

Missing or invisible teams return 404; insufficient authority in a visible team
returns 403; invalid changes return 422; authentication failures return 401.
Mutations take the shared administration guard and team lock, then reload
authority. Removed members lose team access even to earlier contributions,
while keeping personal work. Server-side scope filtering precedes limits/counts.

See OpenAPI for exact response fields and
[scoped operational work](SCOPED_WORK_API.md) for saved-record access.
