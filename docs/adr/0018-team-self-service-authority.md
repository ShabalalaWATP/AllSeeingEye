# ADR 0018: Team self-service and membership authority

Status: accepted, 15 September 2026. Supersedes the team-authority portions of
[ADR 0010](0010-teams-and-access.md). The earlier decision remains the record
of the original global Manager capability and its migration history.

## Context

The original team API allowed only site Administrators to create teams. It also
required a non-administrator to hold both the legacy global `manager` account
role and a `manager` membership in the selected team. That made the account
role an unnecessary second authority source and prevented an ordinary user
from creating a useful team. Membership changes could also remove the only
Manager and leave an active team without a person able to administer it.

## Decision

Any active authenticated account may create a team. The creator is inserted as
an active `manager` membership in the same database transaction as the team
row. A failed membership insert or audit/commit failure therefore cannot leave
a successfully created team without its initial Manager.

For team operations, a current `manager` membership is the authority boundary.
The legacy global `manager` account role is retained temporarily for migration
and account compatibility, but it is no longer required for team leadership.
Team membership never grants the global Administrator capability. A team
Manager may add, promote, demote and remove non-administrator accounts in that
team. A site Administrator may manage any membership. An Administrator account
cannot be modified by a team Manager, even if it is already in the roster.

Every active team must retain at least one active Manager. Demotion, removal and
self-leave of the final active Manager are rejected. Mutating use cases acquire
the existing administration guard and the team row lock before checking the
current membership and manager count, so concurrent supported mutations use the
same lock order. Administrators may appoint another Manager first, then remove
the previous one. Account deactivation workflows remain responsible for
preserving the same invariant when they change active status.

Team Managers may rename or archive their active team. An archived team keeps
its memberships and historical records readable, but roster mutations, new
membership changes and member self-leave are blocked until an Administrator
reactivates it. A Manager cannot restore an archived team. Self-leave is an
explicit `POST /api/teams/{id}/leave` action; an Administrator must ask another
Administrator to remove an Administrator membership.

## Migration and compatibility

Migration `0047` adds a `(team_id, role)` index and ensures that each existing
team whose creator is an active account has that creator as a Manager. It adds a
membership when absent and promotes an existing creator membership when needed.
Inactive creators are left for explicit administrator review; the migration does
not invent a replacement or silently widen access. The backfilled memberships
are valid data and are retained if the migration is downgraded, while the
supporting index is removed.

The existing email-based member endpoint remains available during the
invitation migration. Its application service still enforces the same
membership and Administrator protection rules. Invitation-only writes,
directory discovery and team board features are separate follow-up milestones.

## Consequences and verification

- Team creation is immediately visible to its creator through the ordinary
  membership-scoped list and roster APIs.
- A global role change no longer revokes team management while the account has
  a current Manager membership. Membership revocation still takes effect on
  the next protected operation.
- The manager count joins current user state, so inactive accounts do not keep
  an active team looking managed.
- Tests cover self-service creation, automatic membership, manager promotion
  and demotion, protected Administrator accounts, archive behaviour, self-leave,
  final-Manager rejection, migration backfill and concurrent authority
  revocation. These checks do not certify production migration or deployment
  readiness.
