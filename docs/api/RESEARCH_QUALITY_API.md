# Research quality read models

Read-only views computed on request from saved reports, plus the human citation
verdicts reviewers record on saved versions (KAN-114, the only stored addition). No
score, percentage or reliability number is derived from the counts. These views
describe what was saved and what reviewers said; neither measures research accuracy.

## Source track record (KAN-116)

`GET /api/sources/{source_id}/track-record`

- Authentication: any signed-in account. The route takes the release fence
  (`FenceDep`) and responds with `Cache-Control: private, no-store`.
- `source_id`: 1 to 120 characters, `[A-Za-z0-9][A-Za-z0-9_.:-]*`. Other values return
  422. An identifier that no saved report cites returns zero counts, not 404.
- Shown in the signed-in catalogue at `/sources` as a collapsed "Track record" panel
  that loads only when opened. The administration copy at `/admin/catalogue` does not
  offer it.

### Population

1. Visibility first: the caller's current `AccessPolicy` visibility (own personal
   reports, reports of teams the caller currently belongs to, or every report for an
   administrator, which existing read access already allows).
2. Then the bound: the latest 1,000 of those reports by creation time
   (`report_bound`, `reports_considered`), with `visible_reports` giving the full
   visible count so the page can state "the latest 1,000 of your N visible reports".
3. Then each report's latest saved version only. Earlier versions are not counted.

### Counts

| Field | Meaning |
| --- | --- |
| `reports_citing` | Reports whose latest version froze at least one item from the source. |
| `frozen_items` | Frozen evidence items from the source across those versions. |
| `roles.supporting_judgements` | Key judgements citing a source item as supporting. |
| `roles.contradicting_judgements` | Key judgements citing a source item as contradicting. |
| `roles.items_cited_elsewhere` | Source items cited only outside key judgements. |
| `roles.items_not_cited` | Source items frozen but not cited anywhere in the body. |
| `reports_by_status` | Citing reports by saved status (Ready, Needs review, Failed). |
| `judgements_by_status` | Citing key judgements by the saved status of their version. |
| `reliability`, `credibility` | Frozen item counts per recorded grade letter and digit. |
| `entries` | Up to 25 citing reports, newest first; `entries_total` gives the full count. |
| `reviews` | Up to 25 current reviewer decisions; `reviews_total` gives the full count. |
| `citation_verdicts` | Each reviewer's latest verdict on this source's key-judgement citations in the considered versions: counts per verdict, `current_verdicts`, `superseded_verdicts`, `reviewers`, and `citations_with_verdicts` out of `citations`. At most 5,000 visible verdicts are scanned. |

Reviews are the latest revision of each visible source-review history whose target is
this source on one of the considered reports. Only the kind, the recorded decision,
the time, the report and whether it is team scoped are returned; reviewer basis text is
not. At most 2,000 candidate review histories are scanned per request.

### Performance

`tests/test_source_track_record_benchmark.py` builds 1,000 visible reports with one
saved version and twelve frozen items each on in-memory SQLite. On the development
machine on 1 October 2026 the service median was about 200 ms (target: under one
second). The test asserts only a loose five second regression ceiling.

## Administrator research-quality scorecard (KAN-117)

`GET /api/admin/research-quality?window_days=90`

- Authorisation: administrators only. Like every administrator route, the session must
  be MFA verified: a password-only administrator session is rejected as unauthenticated
  (401) by the current-session check, and other roles receive 403. The route takes the
  release fence with `admin_only`, and the service checks the administrator role again
  in the application layer. Responses use `Cache-Control: private, no-store`.
- `window_days`: 7, 30, 90 (default) or 365. Other values return 422.
- Page: `/admin/quality`, listed as "Research quality" under Research services in the
  administration navigation. It is not part of the overview page.

### Authorised population

Existing rules already let an administrator read every report and every report job
(`AccessContext.require_read` returns early for administrators and the visibility
predicate is unrestricted). The scorecard therefore grants no new right to private
report content. It still releases counts, status values, template identifiers and
titles, research depth values, model connection names, validator rule codes and
severities, collection receipt statuses, token counts and safe job failure codes only.
It never returns report or job titles, report identifiers, report text, finding
messages, reviewer text or anything that drills down to a single record.

### Populations, bounds and missing values

| Population | Membership | Bound | Dimensions |
| --- | --- | --- | --- |
| Saved versions | Every saved report version whose save time falls in the window. Each version counts once, by its own saved status. | Newest 1,000 (`counted`), with `in_window` and `bound_reached`. | Report template, research depth (`scope.research_mode`), model connection (`profile_id`). |
| Report jobs | Every report job created in the window, counted once by job status. Failed jobs are split into `failed_without_version` and `failed_with_version`, so failures that never saved a version are not omitted. | Newest 1,000, reported the same way. | Frozen template, frozen research depth and recorded model name. |

The populations are never added together: a run that saved a version appears once in
each, as a version outcome and as a job outcome. A missing or overlong template, a
missing or unrecognised depth, and a missing connection or model are grouped under
`not_recorded` ("Not recorded"). A model
connection whose profile has since been deleted is labelled "Connection no longer
configured".

### Metrics and denominators

- Ready, Needs review and Failed counts per group, out of the group's version count.
- Up to five commonest validator findings per group, as versions affected out of the
  group's versions plus total occurrences.
- Collection receipts: attempts by status (completed, empty, unavailable, other
  unsuccessful), versions with an empty or unavailable receipt out of versions with
  receipts, and versions without a research receipt.
- Model usage: total prompt and completion tokens and the rounded mean per version, out
  of versions with recorded token counts.
- Job statuses per group and up to five failure codes out of failed jobs.
- Citation-check outcomes: human citation verdicts recorded in the window (newest
  5,000, with `in_window`, `counted` and `bound_reached`), each reviewer's latest
  verdict per citation counted by value out of `current_verdicts`, plus
  `citations_with_verdicts` and `superseded_verdicts`. Reviewer notes are dropped
  before counting and never returned.

No accuracy figure, quality percentage or single rating is computed, and nothing is
persisted (the optional weekly aggregate was not built).

## Human citation verdicts (KAN-114)

Base path: `/api/reports/{report_id}/versions/{number}/citation-verdicts`. Every route
takes the release fence and responds with `Cache-Control: private, no-store`.

| Method and path | Purpose |
| --- | --- |
| `GET ""` | Verdicts on this exact version (oldest first, at most 500), `can_record`, `note_limit` and the human-opinion notice. |
| `POST ""` | Record one verdict. Body: `judgement_id`, `label`, `relation` (`supporting` or `contradicting`), `verdict` (`supports`, `partly_supports`, `does_not_support`, `cannot_tell`) and an optional `note` of 1 to 300 characters. Unknown fields return 422. |
| `GET /export` | `application/x-ndjson` labelled set for this version. |

- A verdict is anchored to the exact saved version, judgement id, citation label and
  the relation the model assigned. The citation must exist in the frozen judgement,
  otherwise 422. Regeneration creates a new version and leaves earlier verdicts on
  their own version.
- Verdicts are append-only. A later verdict by the same reviewer on the same citation
  supersedes the earlier one for counting; both are kept. At most 50 verdicts per
  citation and 500 per version are stored; further attempts return 422.
- Reading needs current read access to the report (owner, current team member or
  administrator). Recording also needs the existing write authority for the report's
  scope: the personal owner, a current member of an active team, or an administrator
  (manual override, including archived teams). Archived-team members can read but not
  record (403). Other accounts receive 404. Verdicts whose stored scope no longer
  matches the report are not released.
- Verdicts never change the frozen report, its grades, confidence or citation checks.
  Each write is audited as `citation_verdict_recorded` with the report id, version
  number and verdict value only; the note is never written to the audit log.
- The export starts with a header row (`record: "header"`, dataset
  `ase-report-citation-verdicts-v1`, version identity, row count and notice). Each
  verdict row repeats the frozen judgement statement, the citation's source and event
  identifiers, the frozen excerpt and its hash when a citation check recorded one, the
  reviewer id, whether the row is current, and `binding_sha256` over the exact-version
  and excerpt fields. Read it with
  `uv run python -m evaluations verdicts --export <file.jsonl> --out <metrics.json>`
  (see `backend/evaluations/README.md`).
