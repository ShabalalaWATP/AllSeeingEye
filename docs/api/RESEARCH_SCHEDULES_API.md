# Saved research schedules

Schedules save an explicit question and admit each due run as a durable report
job and immutable edition. A completed run saves a report under the same access
rules as one-off research. Optional monitoring compares frozen consecutive
versions and creates an in-app event when the configured condition is met.
There are no email, webhook or desktop-host notifications.

`/api/schedules` create, list and update retain personal/team visibility and
management rules. `DELETE` now archives the subscription, stops future admission
and retains its editions, index and reports. Pause/resume and edition controls
are separate. The earlier `0015` fields include:

| Field | Bounds and default |
|---|---|
| `notify_on_change` | Boolean, defaults to false; requires question or collection plan |
| `question` | Nullable, at most 1,000 characters; whitespace-only input rejected |
| `research_mode` | Null for existing live evidence, `quick`, `detailed` or `advanced` |
| `research_languages` | One to eight language codes; defaults to `en`; duplicates removed |
| `research_focus` | `general`, `company`, `domain`, `document` or `media`; defaults to `general` |
| `research_subject` | Nullable, at most 300 characters; required for company/domain |
| `country_isos` | Up to eight ISO2 codes; legacy `country_iso` must agree |
| `research_web_search` | Strict boolean, false by default, requires public research mode |
| `research_source_ids` | Optional app source selection, independent of web opt-in |
| `monthday` | Monthly day 1..31, clamped to each shorter month |

`ask` requires a saved question or a linked same-scope collection plan. Selecting
research mode always requires an explicit saved question. With a non-general
research focus, the subject defines scope and a nation filter is rejected.
Language codes are lower-cased before deduplication. Cadence supports daily,
weekdays, weekly, monthly, quarterly, semiannual and annual schedules, with
saved local-time rules and UTC due-slot identity. Ordinary research lookback
supports 1..17,520 hours. Private document/media schedules are unsupported.
Requested languages and focus are collection instructions, not a
guarantee that a provider supports them or that matching evidence exists.

The scheduler snapshots these fields into a durable edition and report job after
checking current owner, team and source authority. Edits cannot rewrite an
accepted edition. Configured public providers and the assessment model may receive
the saved question and subject each run. Bounded collection, source receipts,
frozen evidence, usage reservations and report access rules apply. The selected
research packet and report evidence are persisted under those bounds.

Migration `0015`, following `0014`, adds nullable `question` and
`research_options` columns to schedules. The JSON now stores plural countries,
monthly day, source IDs and web choice alongside mode, languages, focus and subject.
These additive fields need no new migration. Legacy null values map to the defaults
above. Downgrading drops
these settings while preserving the older schedule columns; a research question
cannot survive that downgrade. Back up the intended database before upgrading.
Development checks used synthetic databases, not an operator database.

Subscriptions offers question, depth, scope and sources. Saved settings
remain reviewable after creation; pause/resume preserves all options. Monthly
day 31 clamps in February and returns to day 31 in March, without drift.

## Evidence-change monitoring

With `notify_on_change=true`, the first usable report establishes a baseline
without an alert. Subsequent runs compare frozen version-one reports using source
and event IDs, content hashes, recorded source flags, engine-assessed supporting
and opposing relationships and confidence, and validation rule/severity counts.
Citation renumbering, evidence order and model prose alone do not trigger alerts.
Changing the saved research scope or toggling monitoring resets the baseline.
A failed saved report retains the preceding usable baseline. A deleted baseline
cannot be reconstructed and the next usable report establishes another baseline.

The schedule exposes nullable `last_change` (bounded status, counts, reason codes,
previous/current report and version IDs, and baseline version ID) and a readable
`last_change_summary`. Status is `baseline`, `unchanged`, `changed` or `unavailable`.
The comparison adds no separate raw evidence corpus. The existing `last_report_id` still points to
the most recent successful scheduled output regardless of changes.

These four values are a compatibility summary. Authorised
`GET /api/schedules/{id}/editions` history also carries the newer six-state
comparison, which separates failure, inadequate coverage, significant correction,
assessment change, new evidence without a broad assessment change and no captured
relevant change. Ambiguous claim mapping is classified as inadequate coverage for
review, not a verified assessment change. Neither comparison proves real-world truth.

Change alerts are labelled **Evidence changed**. They inherit schedule author
and team visibility and can be acknowledged through the existing warning API.
The shell's existing 60-second scoped polling shows them. Authority and the exact
schedule snapshot are rechecked immediately before saving the summary and alert
in the same transaction; replaying a stale run cannot insert a duplicate alert.

These are deterministic differences, not verified important changes. Evidence
may disappear because it aged out of the time window or a provider changed its
coverage. Hash changes do not establish a correction or retraction; missing hashes
limit detection. Source flags are compared only when recorded. Model-assigned
support/opposition relations and evidence-limited engine confidence remain
unverified. Semantic claim changes without a structural difference are not detected.

Migration `0016` adds monitoring configuration and summaries plus nullable
`alerts.schedule_id`; `indicator_id` becomes nullable with exactly one origin
required. Existing orphan-indicator provenance is preserved. Like indicator IDs,
schedule IDs are provenance references and remain after the origin is deleted;
copied author/team fields continue to control access. A downgrade refuses while
schedule-origin alerts exist, preventing silent deletion or fake indicator IDs.
There is no new cloud service or raw-event archive.
