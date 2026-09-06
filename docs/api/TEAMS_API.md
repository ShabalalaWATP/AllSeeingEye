# Team management API

Status: implemented, 6 September 2026. All routes use `/api`, bearer
authentication and the [common authentication contract](AUTH_API.md).

## Authority

Account roles are `user`, `manager` and `admin`. Membership designations are
`member` and `manager`. A non-administrator needs both global manager capability
and a manager designation in the target team to manage its ordinary members.
Administrators create teams and assign leadership. Team membership never changes
the global account role.

Users can read their own teams and rosters, including archived teams.
Administrators can read all teams. Managers may add/remove only ordinary user
accounts in teams they lead. They cannot promote leaders, manipulate manager or
administrator memberships, approve accounts, issue reset links or list all users.
Adding a member uses the known email of an active existing account; it sends no
invitation or external message.

## Routes

| Method and path | Request | Success and policy |
|---|---|---|
| `GET /api/teams` | None | 200 `{items: Team[]}` for current memberships; administrators see all |
| `POST /api/teams` | `{name}` | 201 `Team`; administrator only |
| `GET /api/teams/{id}` | None | 200 `{team: Team, members: Member[]}`; own team or administrator |
| `PATCH /api/teams/{id}` | `{name?, is_active?}` | 200 `Team`; administrator only, at least one value required |
| `PUT /api/teams/{id}/members` | `{email, role?: "member" | "manager"}` | 200 `Membership`; adds/updates an eligible account, subject to authority above |
| `DELETE /api/teams/{id}/members/{user_id}` | None | 204; removes an existing membership, subject to authority above |

Names contain 1 to 120 printable characters after trimming. Email is validated
and bounded to 320 characters. Membership inputs reject extra fields. Repeating
an existing membership assignment preserves its original `joined_at` and never
creates a duplicate row. Manager designations require an account with global
manager or administrator capability.

`Team` contains `id`, `name`, `is_active`, `created_by`, `created_at` and
`updated_at`. `Member` contains `user_id`, `email`, `display_name`, `account_role`,
`is_active`, membership `role` and `joined_at`. `Membership` contains `team_id`,
`user_id`, `role` and `joined_at`. Password hashes, tokens and security versions
are not roster fields.

Missing or invisible teams return 404. Insufficient authority within a visible
team returns 403. Invalid names, missing/inactive target accounts, unsupported
leadership assignments and empty updates return 422. Authentication failures
return 401. Membership uniqueness and role constraints also exist in the database.

## Archiving and revocation

Archiving preserves the team, its memberships and historical work. Ordinary
operational writes and all team background jobs stop; read access remains for
current members and administrators. Membership edits require reactivation even
for administrators. Administrators retain a manual override for operational
records, separately from roster management.

Mutations acquire the shared administration guard and reload the actor before
checking membership. Team updates use a no-op update lock that works on SQLite
and PostgreSQL. Removed users lose team work even when they originally authored
it. They retain their personal work. Scope is enforced by the server, not a
selected workspace in the browser.

Audit actions are `team_created`, `team_updated`, `team_member_set` and
`team_member_removed`. Migration `0013` creates empty team/membership tables;
it does not enrol existing accounts automatically. See
[ADR 0010](../adr/0010-teams-and-access.md) for scope migration and trade-offs.
