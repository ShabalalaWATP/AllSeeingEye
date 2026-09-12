# Map news and evidence presentation review

Date: 13 September 2026. Scope: the additive news feeds, map/fire/news controls,
research catalogue capacity repair and report-doctrine presentation changes.
This is a focused static/behavioural review, not an exhaustive repository scan.

## Boundaries checked

- New RSS sources use the existing guarded HTTP and defused XML connector,
  response/item caps, source enablement and scheduler backoff. No arbitrary
  user-provided URL or network bypass was introduced.
- New source content is headline/date/attribution/link metadata. Article bodies
  and imagery are not retained. Publisher coverage does not become incident
  coordinates. Source links are untrusted; the UI preserves text while refusing
  unsafe schemes, embedded credentials and malformed external links.
- News snapshots use existing authenticated event access. Current account/access,
  nation and period scope invalidate stale requests and displayed data. Reading
  the list does not enable a map layer or trigger an LLM request.
- Catalogue and receipt capacity changes are metadata bounds. Explicit source
  and task limits, per-run request/item allowances, timeouts and concurrency
  remain unchanged. Unsupported/unselected catalogue rows do not create work.
  Frozen plan and receipt parsers use the matching bounded capacities.
- Reports use saved source, judgement and assessment values. No current source
  registry lookup, model call or retrospective regrading was added. Existing
  object authorisation and export rechecks remain in place.
- Report blocks stay XML-safe and bounded. Long citation sets split into bounded
  runs; compact source tables keep long assessment bases in prose. Word, PDF and
  Markdown share the canonical publication.

## Findings and disposition

Review identified a news-selection scope omission: changing filters could leave
old context details visible. The new guard clears excluded news selections and
their map markers while preserving deliberate inspection with the layer off.

A missing/unsafe headline URL originally suppressed its title. Headlines and
related-source titles now remain plain text, with separate validated links.

The report review identified a partial historical assessment that could lose a
saved confidence preface. Removal now requires the matching saved judgement
assessment; legacy text otherwise remains intact. A regression reproduces this
case, and the reviewer independently checked the fix.

No remaining material finding was reported by the focused news/capacity and
report reviews. The staged Gitleaks scan passed. No dependency, credential,
authentication protocol, database migration or production deployment was added.

## Remaining limits

Feed success is not proof of publisher reliability or factual accuracy. New
publishers stay explicitly unassessed. Shared organisation and possible-copy
grouping do not establish true source independence. Support/opposition remains
model-assigned, with human review needed for consequential assessments. Public
feed access does not establish commercial redistribution rights; source-specific
terms are retained in the catalogue and source coverage guide.
