# ADR 0010: Explicit teams and authoritative operational access

Status: implemented, 6 September 2026. Replaces earlier shared-read assumptions
in the architecture and refines [ADR 0008](0008-bounded-report-search.md).

## Context

The initial account model had user/admin roles and shared operational reads.
Adding manager accounts without object-level scope would expose personal/team
requirements, reports, alerts, exports and search results. Long-lived access JWTs
and streams also needed to observe logout, credential changes and membership
revocation. Raw public feed events must remain a single bounded in-memory pool.

## Decision

Keep global account capability separate from team membership. Roles are `user`,
`manager` and `admin`; memberships are `member` or `manager`. Non-administrator
leadership requires both global manager capability and that team's manager
designation. Administrators approve accounts, change global roles, create/archive
teams and assign leadership. Managers maintain ordinary members only in managed
teams and receive no global directory, credential or reset-link authority.

Durable operational roots carry nullable `team_id`. Null means personal creator
access; a team id means current member access. Administrators have explicit
cross-scope access. Current members manage their own contributions; designated
managers manage the team's contributions. Linked records must have identical
team scope or, when personal, identical ownership. Editing content cannot transfer
scope. Historical versions, exports, comparisons and search inherit the report's
current access policy. Alerts preserve creator/team scope after indicator deletion.
Any current member of an active team may acknowledge its alerts as shared triage;
personal alerts require their owner or an administrator.

`AccessPolicy` reloads identity and memberships rather than trusting JWT roles or
client workspace selection. Its visibility value feeds shared SQL predicates
before list limits and counts. Unreadable direct ids return 404. Mutations acquire
the administration guard before user locks and revalidation; no-op updates give
effective transaction locking on SQLite and PostgreSQL. Administrator changes
use stable account lock ordering and prohibit self-modification, preserving an
active administrator across concurrent supported changes.

No authority lock or stale read snapshot spans outbound model work. Generation,
search/indexing and background persistence recheck current scope after external
work. Exports recheck access after rendering. Background jobs require an active
owner and, for team work, current membership of an active team, even when the
owner is an administrator. Archived teams stay readable and retain history;
ordinary writes stop. Administrators retain a deliberate manual operational
override, while roster changes require reactivation.

Access JWTs bind to a refresh family (`sid`) and account security version (`sv`).
Every protected request checks a live family, active account and matching version.
Logout ends its family; credential, TOTP and role/status transitions end affected
sessions. Old JWTs without these claims are refused; a valid existing refresh
cookie can rotate into the new format. Streams recheck before each delivery and
on idle intervals of at most 15 seconds, subject to service scheduling. Alert
delivery is scoped; `access.changed` tells clients to discard stale scoped state.

Migration `0013` introduces empty teams/memberships. Migration `0014` keeps all
existing roots personal and preserves their ids, authorship, links and frozen
evidence. Existing alerts inherit a surviving indicator's owner; orphan alerts
remain administrator-only. `legacy_scope_conflict` audit entries inventory
missing or cross-owner links without copying content. The migration does not
guess team assignments, widen visibility or silently rewrite provenance.

Semantic indexing retains one shared 1,000-vector storage cap. Each caller sees
up to their latest 1,000 authorised reports and scoped counts. Capacity is checked
before embedding calls. Indexing one team never deletes another team's entries;
global maintenance removes orphaned/superseded rows. New slots are refused at
capacity, while existing indexed reports remain searchable. The process-local
lock and rate budgets retain the single-API-process deployment assumption.

Public source events remain shared and never enter the database. Private plan
terms remain owner/team/admin-visible; background eligibility follows current
owner/team state. Enabled Google News collection sends query terms upstream and
adds resulting public articles to the common live pool without private plan ids.

## Consequences and verification

- Tightening legacy shared reads is a deliberate compatibility change. Review
  the migration conflict inventory and repair incompatible links explicitly.
- Membership revocation also removes access to work authored in that team.
  Already downloaded documents cannot be recalled by server-side revocation.
- The shared administration guard simplifies cross-database race guarantees but
  serialises short operational mutations. It must not surround network calls.
- Administrators remain trusted operators with cross-scope access and manual
  archive overrides; team isolation is not isolation from the administrator.
- Deterministic tests cover cross-scope ids, lists, linked records, archival,
  revocation during work, session transitions and index retention. Test evidence
  is recorded in the current improvement plan; this ADR is not an ASVS certificate
  or evidence of real-model quality, production deployment or operator recovery.
- Operator databases and real `.env` files were not migrated during development.
  Back up and migrate the intended deployment deliberately before running new code.
