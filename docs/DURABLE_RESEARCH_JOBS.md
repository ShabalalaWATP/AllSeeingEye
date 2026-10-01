# Durable research jobs

New research submitted from Research, photo research or the map area tool uses
`POST /api/report-jobs`. The request returns an accepted job ID. Open Research
jobs to inspect progress, saved draft sections, the selected model and usage.
Closing the page, logging out or closing the browser does not cancel accepted
work. The worker requires the owner's current account and team access throughout.

## How a report is produced

1. Authorise the request and freeze its scope, exact parent/map/plan references,
   selected private evidence and model assignment. Credentials are never included
   in the saved job. Raw live events remain in memory.
2. Plan and collect evidence, then save the selected evidence packet and collection
   receipts. Evidence labels and original source metadata remain fixed.
3. Write bounded topic sections against that packet. Each completed section is
   schema- and citation-checked before it is saved. A section that exhausts its
   output allowance can be divided into smaller evidence groups, within limits.
4. Save key judgements and assumptions in one small step, then alternatives,
   warnings, gaps and collection recommendations in another. Both steps use the
   original evidence and accepted sections. They cannot rewrite saved reporting
   or turn generated text into a new source. Run the existing complete-report
   validation after combining the sections. A resumed job reuses either saved
   final step, as well as its completed topics.
5. Perform applicable review and claim extraction. Save the report, its version,
   claims and job completion in one authorised transaction.

Saved sections are drafts until the final report is published. A final report can
be marked Needs review. Mechanical citation checks establish valid references,
not that a publisher or an AI interpretation is factually correct.

## Stop, resume and discard

Stop pauses work and preserves saved sections. A provider request already sent
may still incur usage. Resume is explicit: known completed sections are reused;
an interrupted call with an unknown outcome retains its full reserved allowance.
The worker does not automatically retry it after a server restart. Expired work
leases become paused, and abandoned browser requests do not start duplicate jobs.

The browser uses a request UUID for each logical submission. Retrying an uncertain
submission reuses the same UUID and original input. Reusing it with different
input is rejected.

Changing the assigned model, its saved settings or linked input scope stops the
old job. Start new research to use that change. Disabled-source material cannot
be released or reused, including separately stored AI-generated web context.
Paused jobs that cannot resume can be discarded after confirmation. Discard
removes their saved progress and releases capacity; published reports are retained.

## Bounds and operating model

- Two local worker tasks and at most two queued/running jobs per owner.
- At most 20 unfinished jobs per owner and 100 across the application.
- At most 24 provider calls and 256,000 output/reasoning tokens per job over all
  attempts. Input tokens are recorded separately and are not part of this output
  allowance. This is a usage bound, not a currency spending cap.
- Unknown token counts consume the reserved maximum. Known exhausted identical
  requests cannot spend again. Model settings and reasoning are not lowered to
  work around a failure.
- Up to six initial topics, at most twelve topic leaves after splitting, and two
  final synthesis steps. Each job checkpoint is limited to 2 MiB. Admission and
  collection snapshots are independently limited to 768 KiB.
- Leases last 45 seconds and are renewed while work is active. Each worker attempt
  has a 30-minute deadline. Official OpenAI Max topic and synthesis calls receive
  the same bounded 300-second deadline as complete report calls.
- Durable initial query planning has a 120-second deadline. Optional Max
  continuation planning is skipped before dispatch if the remaining collection
  allowance cannot accommodate that deadline. Original planned searches still
  run; receipts disclose that no continuation-model call was made.
- The supported deployment remains one API process, with the existing shared
  source-control guard. Database revision and lease checks fence late writes.
  See [Subscription operations](SUBSCRIPTIONS_OPERATIONS.md) for admission,
  diagnostics and recovery of recurring editions.

Eligible Deep and Advanced durable jobs now plan a bounded post-draft challenge
search against the first saved judgement. Its selected source results and usage
receipt settle together under the job lease, so restart does not repeat a known
completed request. This is not a complete challenge of every report section;
unsupported findings remain subject to the final Needs review gate. Legacy direct
`POST /api/reports` generation and regeneration retain their earlier pipeline.
Subscriptions admit editions into the durable report-job workers rather than
using the former direct schedule producer.

## API and migration

`GET /api/report-jobs` returns small progress summaries, without loading every
evidence packet. `GET /api/report-jobs/{id}` returns authorised saved sections.

The list takes `limit=1..50` (default 20), `status`, `include_briefings`,
`scope` and an opaque `cursor`, and returns `{items, next_cursor}`. `scope=mine`
(the default for every role) lists personal and current-team jobs; only
administrators may pass `scope=all` (see `docs/api/SCOPED_WORK_API.md`). Access scope, status group
and origin are SQL filters applied before the page limit, so hidden or
non-matching jobs never take a page's slots. Status groups map existing states:
`running` is queued or running, `attention` is paused or failed (each row's
`can_resume` separates resumable work from failures that cannot resume) and
`finished` is completed or needs review; `all` applies no status filter. Pages
are ordered by creation time then job ID and continue strictly after the
previous page's last row, so updates and newly admitted jobs cannot repeat or
skip rows. Each job reports `origin`. Daily, economy and cyber briefings
prepared by a workspace visit carry the server-assigned `briefing` origin and
are omitted unless `include_briefings=true`; direct reads by ID are unchanged.
Briefings prepared before this classification have no stored briefing marker in
their frozen scope and remain listed as requested research. Their admission key
is the only reliable provenance; reclassifying them would need a reviewed data
migration, so they are left as they are rather than guessed from titles.
`POST /{id}/pause` and `POST /{id}/resume` control work.
`DELETE /{id}` discards inactive job progress after authorisation.
Protected responses are private and not cacheable; current sessions are checked
again before release.

Migration `0033` adds the report-jobs table and owner/request uniqueness. Take and
verify a backup before applying it to an operator database. Downgrading refuses
to remove a table containing retained jobs. No external queue or new production
dependency is required. The worker runs independently of the live-feed switch.

The two-part synthesis preserves the original topic checkpoint digest. A job
paused during the earlier combined synthesis can resume using its saved topics.
A previously completed combined synthesis also remains reusable.

## Validation

Automated coverage includes section splitting and reuse, uncertain usage,
idempotency, revoked access, disabled sources, lease races, atomic publication,
pause/resume/discard and browser observation. File-backed SQLite integration
tests exercise independent database sessions as used by the local deployment.
Provider fixtures are separate from live model acceptance. See the development
story for the final verification results and remaining limits.
