# Packet 2: one durable execution system

Goal: schedules enqueue the existing report jobs, preserve one edition identity per due slot and recover without duplicating paid work. Keep the supported one-API-process topology; test database fencing without claiming multi-process deployment support.

## S01: edition ledger and additive migration

Dependencies: C02. Ownership: schedule domain/ports/persistence/migrations. Reuse existing report-job identifiers and contracts.

Read `backend/src/ase/domain/schedules.py`, `domain/report_jobs.py`, `application/ports/schedules.py`, `application/ports/report_jobs.py`, `adapters/persistence/schedules.py`, `adapters/persistence/report_jobs.py` and their models/codecs.

Proposed persistent contracts, validated with Pydantic at API boundaries and immutable domain types inside:

| Record | Required fields and invariants |
| --- | --- |
| Subscription revision | Subscription ID, revision, owner/team, current request snapshot, later brief revision, recurrence policy, collection policy, activation state, created time. Published revision immutable. |
| Edition | ID, subscription ID, trigger kind, scheduled due slot or manual request UUID, frozen revision, requested start/end, effective intervals and gaps, baseline version ID, job ID, workflow state, report quality, coverage state, report/version IDs, safe reason, created/updated times and revision fence. |
| Attempt | Edition/job ID, attempt number, stage, start/end, outcome, next retry time, lease/revision reference and bounded usage reservation/actuals. No credentials or raw exception bodies. |
| Delivery outbox | Edition ID, channel, destination reference, event kind, idempotency key, state and bounded attempts. Store destination secrets elsewhere. |

Unique scheduled identity: `(subscription_id, due_at_utc)` for scheduled editions. Manual baseline/run-now requests use `(subscription_id, trigger_kind, request_uuid)`. Do not include brief revision in scheduled uniqueness: editing a brief must not create a second edition for the same slot.

Derive the report job's request key deterministically from the immutable edition UUID using one fixed documented namespace. Do not copy the caller's manual UUID into it: existing job uniqueness is owner plus request key, whereas edition deduplication also includes subscription/trigger. Test the same caller UUID used for two different subscriptions and reject different payloads reusing one logical edition key.

Maintain two separate baseline concepts: exact analytical comparison version, and actually covered observation intervals/watermarks. Accepting a partial report as an analytical baseline never declares its unsearched dates covered. Store a compatibility fingerprint of question/requirements, geography/entities/AOI, source policy and analytical lens. Cosmetic edits preserve lineage; substantive changes require a fresh baseline or an explicitly limited comparison with the incompatibilities recorded.

Separate axes instead of a combinatorial status enum:

- Workflow: pending, queued, running, retry_wait, paused, blocked, completed, failed, cancelled, skipped.
- Report quality: absent, ready, needs_review, failed, mapped from existing versions.
- Coverage: complete_for_plan, partial, insufficient, unknown. “Complete for plan” never means exhaustive world coverage.

Expose a derived simple user label: Running, Ready, Needs review, Partial coverage, Waiting to retry, Paused, Blocked or Failed. Always retain the underlying axes.

Map editions onto existing job states explicitly; new edition states are not automatically new `ReportJobStatus` values:

| Edition state | Underlying job | Worker eligibility | Holds subscription active guard | Retained job capacity |
| --- | --- | --- | --- | --- |
| pending | Not yet admitted | Admission only | Yes | No job slot yet |
| queued/running | queued/running | Existing worker rules | Yes | Existing open/active limits |
| retry_wait | failed or paused with known retryable stage | Only after retry deadline/admission | Yes | Retained until retry/retirement |
| paused/blocked | paused, or no admitted job if preflight blocked | No automatic paid work | Yes, especially unknown calls | Retain existing job reservation if present |
| completed | completed/needs_review | No | No | Existing completed retention policy |
| failed, retries exhausted | failed, known resolved usage | No | No after terminal retirement | Remove from open-job quota only through audited retirement; retain edition/history/usage |
| cancelled/skipped | No job, or paused/terminal known job | No | No only after safe terminal retirement | Same retirement rule |

Current open-job counts include failed/paused jobs. Add explicit terminal retirement/archival bookkeeping rather than changing those counts globally or deleting audit history. An unknown paid outcome cannot be retired to obtain fresh budget; it keeps the admission guard and reserved usage until the existing explicit resolution/resume process is satisfied. Test many known failed editions so quota does not leak forever, while unknown ones remain protected.

Migration requirements: additive schema; preserve old cadence, hour_utc, due slots, history and report links; mark backfilled coverage unknown; do not invent historical editions or success cutoffs. Keep a schema-versioned adapter from old request snapshots. Allocate the next real Alembic revision and test upgrade with old populated SQLite and PostgreSQL fixtures. Destructive downgrade must refuse retained new records. Index due/status lookups and paginated histories.

Backward readers must preserve existing queued, paused, failed and uncertain-call job payloads, request digests, section packet digests and usage reservation hashes without rewriting frozen input. If an old payload cannot be safely decoded, pause it with an actionable compatibility reason. Never regenerate it silently under a new schema. Include those retained-job states in populated migration fixtures.

Tests: uniqueness across independent DB sessions, manual UUID reuse/conflict, old-row backfill, malformed outcome rejection and optimistic revision conflict. Done when a due slot has a stable retrievable identity before any provider call.

## S02: enqueue and publish atomically

Dependencies: S01. Ownership: schedule runner, container bridges, report-job completion and persistence transactions.

Read `application/schedules/runner.py`, `container/features.py`, `container/report_job_execution.py`, `container/report_job_worker.py`, `container/report_job_checkpoints.py` and the existing final report-publication transaction.

Flow:

1. Select the due slot and prepare a candidate outside admission locks without paid work. In a short database transaction, recheck account/team authority and the exact subscription revision, create or claim its unique edition, and admit/create the corresponding existing report job. Persist both links atomically. A uniqueness conflict returns the existing edition/job.
2. A queue-capacity rejection leaves the edition pending with a safe capacity reason and a future admission check; it does not consume a generation attempt or paid allowance.
3. Release DB/source-control locks before network or model work. Workers use the current lease, scope guards, checkpoints and usage ledger. Subscription jobs consume the same per-owner/global capacity as manual jobs.
4. Extend final publication so report/version, job outcome, edition outcome and baseline eligibility are committed consistently. Retries of completion reconcile existing published identifiers, never generate another report.
5. Recheck current authorisation before dispatch, checkpoint reuse, completion and response/delivery release. Revoked team membership, disabled users/sources and changed model assignments produce an explicit blocked/paused reason according to existing job rules.
6. Remove direct long-running schedule generation from the runner. Retain a legacy schema adapter, not a second execution engine.

Required admission seam: current `application/report_jobs/service.py` creation rolls back preparation reads and commits admission itself, so it cannot be called unchanged inside an outer edition transaction. Extract reusable prepared-candidate validation and a caller-owned, commit-free admission operation. Preserve lock order: source-control guard before administration locks; preparation/freezing before admission locks; authority/revision revalidation inside the final transaction. The existing one-off public method can wrap the same operation in its own transaction. Test no nested commit/rollback loses edition state and no lock is held during a paid call.

Required scheduled codec work before removing the direct path: extend existing report-job `snapshots.py` and `request_snapshot.py` with versioned freezing/restoration of `Job.subscription_baseline`, exact authorised previous report/version references, bounded seen fingerprints and previous-judgement context. Update strict metadata allowlists deliberately. Reauthorise baseline/source scope on reuse, preserve current byte caps and do not copy an unrestricted historical report corpus into the job. Run a second subscription edition through the actual durable freeze/restore path and prove novelty/change context survives a restart.

Baseline eligibility: only a completed, ready report whose required-source/requirement coverage is acceptable may automatically advance the compatible covered intervals and contiguous successful cutoff. Needs-review/partial editions remain visible but do not silently become the comparison baseline. A later explicit accept-as-baseline action can authorise a usable partial/review edition for analytical comparison, retaining its limitations and audit record; it does not fill unsearched intervals or move a complete-coverage watermark across a gap. Failure never advances the cutoff. Fingerprints are associated with admitted/accepted evidence and their intervals rather than using baseline acceptance to erase gaps.

Tests: overlapping ticks, crash before/after job creation, crash before/after final commit, expired lease late write, revoked authority mid-run, disabled input, failed/review/partial outcomes, and capacity contention. Assert one stored edition/report version per logical execution; assert no repeated completed model stage. Do not claim exactly-once external network effects.

## S03: retries, uncertainty and budgets

Dependencies: S02. Ownership: retry policy, job admission/usage integration and failure presentation.

Initial policy, kept in one versioned domain policy module and configurable downward by existing budgets:

| Failure | Action |
| --- | --- |
| Known transient connection failure before dispatch, explicit retryable response | Up to three retries after the initial attempt: 5 minutes, 30 minutes, 2 hours. Stable small jitter derived from edition ID. Honour a longer valid Retry-After within the retry horizon. |
| Known failed source, enough other evidence | Complete as partial or needs-review under the quality gate; record failed coverage. Do not retry the whole report just for padding. |
| Authentication, missing capability, revoked scope | Block with actionable reason; no periodic paid retry. |
| Ambiguous paid-call outcome or expired active-call lease | Pause for explicit resume; retain full reserved allowance and existing non-replay safeguards. Never silently issue the same uncertain model call again. |
| Validation failure with a known saved draft | Use only the bounded repair/checkpoint rules within that job's remaining budget; otherwise needs-review or failed. |
| Budget or queue capacity exhausted | Budget blocks; capacity waits. Neither changes publication cadence. |

The automatic retry horizon is 24 hours from the first failed attempt. Retry deadlines and due slots are separate. Future cadence slots remain based on the calendar anchor. Permit at most one active edition per subscription; pending newer slots coalesce under S04 rather than flooding the queue. Explicit Retry references the same edition and known checkpoints. A genuinely new run has a new manual request UUID and clearly consumes a new budget.

Keep existing durable bounds unless explicitly revised by measured R04/V01 evidence: two local workers, per-owner queue limits, checkpoint size limits, provider-call and token accounting, 45-second renewable leases and bounded worker deadlines. Distinguish the existing 24 LLM-call job cap from fresh-source operation budgets. Job attempts share a total budget, not a fresh budget per retry.

Add subscription monthly usage limits using existing usage records, not a second financial ledger. Snapshot a currency estimate only when pricing/currency/model version is known; otherwise show tokens and requests with “cost unavailable”. Never promise a hard currency cap from incomplete pricing. Reserve atomically to prevent concurrent manual and scheduled work exceeding limits.

Budget policy: enforce provider/model request counts and output/reasoning token reservations in a UTC calendar month for accounting, with UTC boundaries shown alongside local scheduling time. Charge reservation to dispatch month; later reconciliation adjusts that original month and never double-charges the current month. Unknown reservations remain charged across month rollover and continue to hold the edition guard; a new month cannot reset the job's lifetime budget. A resumed stage dispatched in a new month uses that month's remaining allowance as well as the job's lifetime allowance. Baseline/run-now/retry actions for a subscription consume both its budget and the owner's aggregate budget. Unrelated one-off jobs consume the owner budget only. Incremental acquisition is attributed to benefiting subscriptions by a documented deterministic allocation, while a shared physical fetch is charged once to aggregate app/provider counters. Tests must cover rollover, unknown outcomes and shared-fetch attribution.

Tests: annual run failure retries promptly without moving next year's anchor; jitter deterministic; unknown call paused; successful checkpoints reused; retry exhaustion; Retry-After; overlapping manual/admission budget reservations; no fresh budget on each retry.

## S04: time, missed slots and catch-up

Dependencies: S03. Ownership: recurrence domain, request windows, revision editing and interval receipts.

Add IANA timezone plus local hour/minute to new subscriptions; migrate old UTC schedules to `UTC` with unchanged times. For a nonexistent local DST time use the first valid time after the gap; for a repeated time use its earlier occurrence once. Preserve intended day-of-month through short months and leap years. Display the next three local and UTC occurrences before activation.

Explicit policies:

- `rolling_snapshot`: requested interval ends at the original due slot and starts at due minus the configured lookback, even when execution is late. Historical source limitations must be disclosed.
- `since_last_success`: end is the due slot; start is the last accepted successful cutoff minus overlap. A first run uses the brief's initial baseline lookback.
- Select only a compatible baseline/cutoff no later than the edition's end. If a newer manual baseline already covers an old pending slot, explicitly mark that slot covered/skipped with the covering edition link; never create an inverted interval. Start from unresolved coverage intervals even if a partial report was accepted for analytical comparison.
- For an ordinary positive since-last-success interval, overlap is `min(6 hours, (end - compatible_cutoff) / 4)`, calculated before subtracting it. First-run/rolling windows use `min(6 hours, baseline_window / 4)` where overlap applies. Deduplicate by preserved content/origin, not only URL. Late arrivals retain both observed and first-seen dates.
- When multiple cadence slots were missed, create one bounded catch-up edition for the latest due slot, record earlier slots as coalesced/skipped with links, and record requested versus retrievable coverage. Do not generate one paid report per missed day by default.
- If an older capacity-pending edition already holds the active guard, coalescing may atomically mark it skipped, release that guard and create/link the latest catch-up edition only when it has no admitted job, external attempt or usage reservation. Never supersede admitted, running, paused-with-unknown-outcome or other paid work. Otherwise finish/resolve the existing edition first and defer catch-up. Test capacity rejection followed by a five-day outage so immutable dates and the active guard do not deadlock recovery.
- If archive/history supports the full interval, query it within the normal job budget. If it does not, preserve the full requested dates but explicitly list unsearched intervals and do not advance a complete-coverage baseline. Never silently turn an annual interval into today's RSS.
- Limit automatic recovery to one catch-up job per subscription at a time. Extensive historical retrieval uses the retained archive or a separately requested backfill, with previewed cost/capacity.
- Edition creation is the freeze point for revision, baseline choice and requested dates, including a capacity-pending edition with no job yet. Retry never recalculates its interval. Brief edits affect only slots without an edition. Name/description changes preserve pending work. Cadence/time edits explicitly choose `preserve_pending` (default) or `cancel_unstarted`, with a preview. Running or uncertain-paid work cannot be cancelled and recreated at another due timestamp to bypass its budget/guard. Deleting old history is never an edit side effect.

Covered intervals/watermarks advance monotonically within a compatible lineage, including out-of-order completions. An older edition may add missing coverage but cannot move the current cutoff backwards. Test manual baseline finishing after an older pending slot, overlapping editions, incompatible lens/scope changes and a partial accepted baseline with remaining gaps.

Use timezone-aware UTC comparisons in storage, half-open observation intervals `[start, end)`, and separate event/publication/retrieval dates. A provider timestamp cannot silently become the event date.

Tests: daily five-day outage, annual interval, DST gaps/folds, month-end, leap day, late publication, failed baseline, overlap deduplication, rename and scope/cadence edits while queued/running.

## S05: controls, history and delivery

Dependencies: S02–S04. Ownership: schedule service/API/contracts and outbox adapter.

Extend existing `/api/schedules` rather than introducing competing subscriptions routes. Proposed actions: `/preview`, `/{id}/run-now`, `/{id}/editions`, `/{id}/editions/{edition_id}/retry`, `/pause`, `/resume`, `/duplicate` and an audited accept-baseline action. Reuse current equivalent routes where present. Mutations require current auth/CSRF, object authority and an idempotency UUID where repetition can create work. Use revision preconditions for edits and consistent 409 conflict responses.

Run now does not shift cadence. Baseline now is an explicit trigger; activation can choose it, with the next normal slot shown. Pausing prevents new dispatch and requests a checkpoint-safe pause of active work; an already sent provider call may finish and consume usage. Resume presents missed-window policy. Duplicate defaults to disabled and preserves content/settings without copying edition history or another user's inaccessible inputs.

History is paginated and contains exact edition/version links, attempts, quality, coverage, safe failure reason, stage, duration and usage summary. Summary lists never load entire evidence packets.

The default delivery channel is in-app, subject to the notification policy below. Reuse configured notification adapters for optional verified channels; do not auto-send email or invent webhook destinations. Outbox dispatch rechecks authority and destination configuration, uses bounded retries and an idempotent key. A delivery failure does not turn a generated report into a generation failure. External exactly-once delivery is not guaranteed if the provider lacks deduplication; disclose unknown delivery and avoid blind replay.

Define explicit event kinds: edition_available, material_change, correction, needs_attention and delivery_failure. Notification policy is none, changes_only or every_edition, plus an independent attention opt-in. Preserve existing `notify_on_change=true` as changes_only and existing false as no new report notifications unless a current separate setting establishes otherwise. Do not silently subscribe old users to baseline, quiet-period or failure messages. New subscriptions default to in-app changes_only with attention enabled, visibly editable. Source/collection failure changes row state regardless of notification preference. Deduplicate one event per edition/type/channel; a corrected edition can legitimately create a new correction event.

Tests: all controls, permission revocation, IDOR, repeated UUID, duplicate scope safety, double delivery dispatch, notification preference, partial report attention and pagination bounds.

## S06: lifecycle and operation

Dependencies: S05. Ownership: `backend/src/ase/main.py`, scheduler container lifecycle, summary metrics and operating docs.

Start the scheduling admission loop independently of `feeds_enabled`, as durable workers already are. Shutdown stops admission, releases/finishes bounded work through current worker rules and leaves recoverable state. Apply fair per-owner scheduling and bounded DB batches so a single subscription cannot starve interactive jobs. Poll pending capacity at a bounded interval, not a busy loop.

Expose administrator diagnostics: oldest due lag, active/blocked/retry counts, last successful dispatch, queue saturation, unknown paid calls and source failure categories. User screens show only their authorised summaries. Logs contain IDs and safe codes, never full questions/private passages/secrets.

Done when feed-disabled startup still schedules an eligible fixture edition, repeated startup/shutdown creates one loop, recovery tests pass, and the operations guide explains the supported single-process topology and unresolved deployment limits.
