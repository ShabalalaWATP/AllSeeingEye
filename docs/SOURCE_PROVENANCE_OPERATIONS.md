# Source language and date provenance

Status, 8 September 2026: implemented in the isolated source-provenance checkout;
full regression acceptance and integration remain pending. The requirements are
tracked in [the implementation plan](SOURCE_LANGUAGE_DATE_PROVENANCE_PLAN.md).

## Research queries

Keep the original query. A transliteration is a separate operator-supplied variant
linked to its original terms, language/script and stated method. Review its exact
outbound terms in the collection plan. Translation and transliteration can coexist;
neither establishes that two similarly named entities are the same organisation.

Selected term-search tasks execute supported variants within the existing shared
request budget. Exact registry identifiers are not replaced by transliterations.
Unsupported routing is explicit. Saved scope, receipts and regeneration retain
the selected variant and its provenance.

Machine translation records the profile/provider and returned model at execution.
Cached translations retain that execution record. Changing the administrator's
current connection does not relabel earlier translations. Old records without
those details remain unknown rather than acquiring invented provenance.

## Supplied document and media declarations

After importing a private input, load its exact passage targets. Select the source
field and enter a translation, transliteration or explicitly declared source date.
The server binds declarations to the owned input, passage and content digest.
Original text, zero-width characters, citation offsets and the input digest stay
unchanged. The interface renders source text as text.

Prepare the required declarations before applying them. Application creates a
new immutable receipt linked to the original; it does not modify the original
receipt or any saved report. The client verifies that parent link before adopting
the new receipt. Derived receipts can be inspected but cannot be used as the
parent of another declaration chain.

Originals and derivatives share the existing temporary-input capacity: two slots
per user, eight globally, with a fifteen-minute lifetime. Applying declarations
to one retained original consumes the second user slot. Capacity rejection does
not evict another input. If capacity is exhausted, existing temporary inputs must
expire before another original can be imported. Saved report evidence remains
independent of those temporary receipts.

Access invalidation clears private drafts. Cancelling aborts the request and
prevents late responses from replacing the selected input. The backend rechecks
the live session, ownership, security version and expiry before private release.

## Dates and assessment

Publication, occurrence, record validity, modification and unspecified lifecycle
dates have separate roles. A generic Dublin Core date is not a publication date.
Recognised issuance and Atom publication fields use their documented roles;
modification dates cannot displace publication dates during bounded selection.
Capture time remains separate when publication is unknown.

Raw source text, calendar declaration, method, precision and resolution status
remain visible. Date-only conversion preserves day precision; unknown timezone,
invalid input and unsupported conventions do not become invented UTC instants.
The supported Gregorian and explicitly named Solar Hijri convention, bounds and
primary fixtures are documented in [SOURCE_CALENDAR_CONVENTION.md](SOURCE_CALENDAR_CONVENTION.md).

Frozen evidence, JSON packages, readable exports and the interface retain this
provenance. The model receives bounded context marked as unverified source or
operator information. This helps assessment but does not authenticate a date,
prove transliteration equivalence or measure model accuracy.

## Compatibility and verification

Historical records with absent new fields retain their canonical representation.
Fixed pre-feature content/comparison digests are regression fixtures; saved-map
and annotation evidence anchors continue through the canonical evidence encoder.
New calendar-day values can be included in retained comparisons and exports.

The backend passed a 222-case focused group, a 74-case final date/namespace group
and an 11-case translation/export group. These overlap and are not a unique total.
Ruff, formatting, mypy (621 source files), import contracts, file-length checks
and configured Bandit passed. Independent review repairs cover session release,
historical hashes, date roles and receipt lineage. The standalone full run ended
with 3,321 passed, 57 skipped and one failed media assertion, with 94.95% coverage
in 5,120.48 seconds. That assertion equates upload capture time with publication
time; an isolated no-coverage run confirmed it. The adapter correctly retains
capture time separately and leaves unknown publication time absent. The repair
and SEC integration are proceeding together on `codex/source-provenance-sec`,
based on accepted main `99e65d5`. No clean combined backend acceptance is claimed.
Final frontend validation passed 1,034 tests in 201 files, with
95.05% statement, 90.06% branch, 93.53% function and 96.40% line coverage.
All existing ninety per cent gates remain unchanged. Final type checking and
production build passed. Three observed lazy-route test setup races were repaired
by loading the real route modules in the affected test files, without increasing
timeouts. Integration and full backend acceptance remain pending.

No new dependency or migration is required by this feature. No operator database,
provider connection or deployment was changed. Independent semantic evaluation
and the wider research expansion remain open.
