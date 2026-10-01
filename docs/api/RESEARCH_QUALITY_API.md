# Research quality read models

Read-only views computed on request from saved reports. Nothing new is stored, no
migration is involved and no score, percentage or reliability number is derived from
the counts. Both views describe what was saved; neither measures research accuracy.

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
| `citation_verdicts` | Always `available: false` until citation verdicts exist (KAN-114). |

Reviews are the latest revision of each visible source-review history whose target is
this source on one of the considered reports. Only the kind, the recorded decision,
the time, the report and whether it is team scoped are returned; reviewer basis text is
not. At most 2,000 candidate review histories are scanned per request.

### Performance

`tests/test_source_track_record_benchmark.py` builds 1,000 visible reports with one
saved version and twelve frozen items each on in-memory SQLite. On the development
machine on 1 October 2026 the service median was about 200 ms (target: under one
second). The test asserts only a loose five second regression ceiling.
