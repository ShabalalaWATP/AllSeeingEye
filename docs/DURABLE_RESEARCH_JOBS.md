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

Detailed durable research reviews the frozen evidence once and states that it
has not performed an additional contrary-source collection pass. Legacy direct
`POST /api/reports` generation, regeneration and existing schedules retain their
earlier pipeline. They are not all converted to durable section jobs by this change.

## API and migration

`GET /api/report-jobs` returns small progress summaries, without loading every
evidence packet. `GET /api/report-jobs/{id}` returns authorised saved sections.
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
