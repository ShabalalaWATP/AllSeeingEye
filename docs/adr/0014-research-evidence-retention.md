# ADR 0014: selected evidence, scoped geometry and reference releases

Status: accepted implementation direction, 6 September 2026.

## Decision

Raw public events remain in the bounded, ephemeral live store. Research preserves
only selected evidence and bounded collection receipts with each report version.
No historical event database or global people graph is introduced.

Geometry derived from private evidence inherits the report's personal or team
scope. It never enters the public event bus or shared browser event store. A saved
map revision must resolve frozen evidence identifiers, time filters, canonical
geometry and explicit source release versions. Editing a view creates a new
revision. Export resolves one revision and rechecks access after rendering.

Original geometry and precision are retained. Display simplification is a
derivative with a recorded tolerance. Country-only findings are not incident
points. Missing coordinates remain missing, including in exports.

Public reference datasets use a separate, versioned and bounded cache when their
licence permits local use. A cached release records its source URL, retrieval and
release dates, content digest, licence, precision and coverage. Unavailable old
releases are reported explicitly; current data must not replace them silently.

Selected original assets require deliberate retention, a permitted-use record,
per-user/team and global quotas, bounded parsing and lifecycle records. Package
exports include only authorised selected assets and disclose absent originals.
Capturing an excerpt or hash does not authenticate or preserve an entire source.

## Consequences

Report JSON extensions can remain backward compatible, with absent legacy fields
shown as unknown. Independent saved-view, annotation or asset lifecycles require
scoped persistence and tested migrations before delivery. Database changes are
not implied by this ADR, and no operator database was migrated when it was written.

Map history is limited to retained live coverage, frozen reports and available
reference releases. Complete historical replay is intentionally not promised.
