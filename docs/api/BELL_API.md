# Notification bell API

Status: current implementation, 1 October 2026 (KAN-98). FastAPI schemas and the
exported OpenAPI document are authoritative for field details. This document explains
the scope and safety contract.

## Scope and window

- Every route requires a bearer token and takes the release fence (`FenceDep`).
  Responses carry `Cache-Control: no-store`.
- The bell is always **Mine and my teams**: the caller's own personal records and the
  records of teams they currently belong to. Administrators keep broad access on other
  pages, but their bell never counts other people's personal records or teams they have
  not joined (KAN-90's default ownership contract).
- Alerts use the same seven-day window as the Alerts page (`window_days`). Alerts older
  than that are not listed and are never described as acknowledged.
- Filtering by scope, window, acknowledgement and muted rules happens in SQL before the
  limit and the count.

## Preferences

Preferences change only the caller's in-app bell and badge. They never pause rule
evaluation (the rule's Enabled switch is separate), acknowledge anything or affect another
account. Out-of-app delivery is a separate opt-in layer and does not read them, so it can
be added without changing this contract.

- `muted_kinds`: any of `alerts`, `research`, `mentions`. A muted kind returns an empty
  section with `muted: true` and adds nothing to the badge.
- Muted rules: at most 100 per account, removed with the account or the rule. A rule can
  be muted only while the caller can read it. The muted list shows only rules the caller
  can still read, so a hidden rule's name never leaks; unmuting is always allowed.

## Endpoints

| Method and path | Body | Success | Errors |
|---|---|---|---|
| `GET /api/bell` | none | 200 `{window_days, alerts: {items, total, muted}, preferences}`; at most five alert items, newest first, each with `team_name` and `can_acknowledge` | 401 |
| `GET /api/bell/alerts/{alert_id}/destination` | none | 200 `{kind: "report" \| "transition" \| "alerts", available, report_id, monitor_id, transition_id, message}`. Identifiers are present only while the caller can read the destination now; otherwise `available: false` with an explanation | 404 for an unknown or out-of-scope alert (indistinguishable) |
| `POST /api/bell/alerts/acknowledge` | `{alert_ids: [uuid]}` (1 to 20) | 200 `{acknowledged: [uuid], failed: [{alert_id, message}]}`. Each identifier is authorised and audited separately through the shared acknowledgement use case; repeats are harmless | 422 |
| `PUT /api/bell/preferences` | `{muted_kinds: [kind]}` | 200 preferences | 422 for an unknown kind |
| `PUT /api/bell/muted-rules/{indicator_id}` | none | 200 preferences; idempotent | 404 for an unreadable rule; 422 `invalid_request` at the cap |
| `DELETE /api/bell/muted-rules/{indicator_id}` | none | 200 preferences; idempotent undo | 401 |

Acknowledging a team alert is shared: it clears the alert for everyone in that team.
Archived teams are read-only, so their alerts report `can_acknowledge: false` and an
acknowledgement attempt fails with that reason.

## Live updates

After a committed change the server publishes a content-free `bell.changed` bus message.
The live stream delivers it as an empty `{}` frame only to the named recipients, or, for an
acknowledgement, to readers whose bell scope includes that record after a fresh access
read. The browser then refetches `GET /api/bell`; no title, snippet or count travels on
the stream. Stream `alert` frames also prompt a refetch, and the bell still polls every
minute while the page is visible.

## Board mentions (KAN-138)

Team board posts are plain text. A token such as `@analyst` is a mention when it matches a
directory username (3 to 32 letters, digits or underscores) and is not part of a longer
word or an email address. Mentions are never rendered as markup.

- Resolution uses only the team's current roster: active members with a directory
  username. Global directory discovery and its opt-in are not consulted. The author is
  never notified, and unknown or outside handles are treated as plain text, so a response
  never reveals whether an outside account exists.
- A post may name at most ten different handles. More is refused with 422
  `invalid_request` and `fields.text`, before anything is written.
- Each mention is stored with the recipient's stable user id and the handle as written, in
  the same transaction as the post write. A failed or stale write leaves no notice. Later
  handle changes or reuse never redirect a stored mention.
- Editing keeps unchanged mentions as they are (no repeat alert, read state kept), removes
  mentions whose handle was deleted and notifies only newly added teammates. Removing or
  moderating a post deletes its mentions.
- `POST` and `PATCH` on `/api/teams/{team_id}/board/posts` return the post plus
  `notified: [{user_id, display_name}]`: the teammates that write newly notified.

A recipient sees a mention only while the post is live, the team is active and their
current membership began no later than the mention. Leaving a team or archiving it hides
pending mentions; rejoining does not bring back mentions from an earlier membership. Read
state belongs to each recipient.

| Method and path | Body | Success | Errors |
|---|---|---|---|
| `GET /api/bell` | none | also returns `mentions: {items, unread, muted}`: at most five unread notices `{post_id, thread_id, team_id, team_name, author_name, snippet, created_at}` with a plain-text snippet, and an unread count capped at 100 | 401 |
| `POST /api/bell/mentions/{post_id}/open` | none | 200 `{team_id, post_id, thread_id}` after re-checking access; marks the caller's notice read | 404 when the post or access is gone |
| `POST /api/bell/mentions/read` | `{post_ids: [uuid]}` (1 to 20) | 200 `{unread}`; only the caller's own notices change | 422 |

Mention rows are small operational records (migration 0081): at most ten per post,
removed with the post, the recipient account or the team. Email or other out-of-app
delivery of mentions is not part of this contract.
