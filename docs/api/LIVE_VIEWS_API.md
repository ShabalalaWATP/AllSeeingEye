# Saved live views and ops-room playlists

Status: current implementation, 1 October 2026 (KAN-120, KAN-124). Both are map
workspace documents under `/api/map/workspaces`, alongside drawing collections and
radio studies. Every route requires bearer authentication and returns
`Cache-Control: no-store`. Field shapes are defined by the exported OpenAPI schema.

## Scope, revisions and audit

Documents carry the standard personal or team scope described in
[scoped work](SCOPED_WORK_API.md). Lists filter by visibility in SQL before
limits. Direct reads outside the caller's scope return 404, so a stale or unshared
link cannot reveal whether a view exists. Updates send `expected_revision`; a
mismatch returns 409 and nothing is overwritten. Archived teams stay readable and
reject ordinary writes. Each create, update and delete records a
`map_workspace_changed` audit entry with the document kind and revision.

Each personal or team scope may hold 50 live views and 10 playlists, counted
separately from the shared 100-document allowance for drawings and radio studies.

## `kind: "live_view"`

A view stores configuration only, never live events:

| Field | Meaning |
| --- | --- |
| `version` | Always `1`. |
| `projection` | `globe` or `map`. |
| `camera` | `center` `[longitude, latitude]`, `zoom` 0 to 22, `bearing` -180 to 180, `pitch` 0 to 85. |
| `base_layer` | One of the known base maps. |
| `layers` | Visible layer ids: event categories plus `aircraft`, `vessels`, `firms`, `fires`, `interference`, `terminator`. |
| `window_hours` | Positive hours up to one year, or `null` for the whole retained window. |
| `nation` | Upper-case ISO country code or `null`. |
| `filters` | Known filter ids only (location quality, traffic, GNSS, cyber and conflict display filters). |
| `plan_id` | Optional collection plan filter. |

The server rejects unknown keys, layer ids, filter ids and values. A linked plan must
be readable and share the view's scope, even for administrators. The browser drops
ids retired after a view was saved and names them in a notice.

`/?view=<id>` carries only the ID. Opening it re-reads the document under the
viewer's current access, removes the ID from the address and shows "unavailable"
when the read fails. Views open only when chosen; nothing is restored at sign-in.

## `kind: "ops_playlist"`

`{"version": 1, "entries": [...]}` with 1 to 8 entries. Each entry has `kind`
(`view` or `area`), `id`, `caption` (up to 120 characters) and `dwell_seconds`
(5 to 3,600). Each linked live view or saved area must be readable and share the
playlist's scope. An area entry only focuses that saved area.

The ops room re-reads the playlist at the start of every cycle and each entry when
it comes round. Unavailable entries are skipped with a visible notice. Time counts
only while the tab is visible and nobody is interacting. Leaving the ops room or
any change of account or team access stops the rotation. No new authentication
mechanism, kiosk token or longer session is involved.
