# Runtime health and request diagnostics

KAN-41, KAN-42 and KAN-43 add process-local operational diagnostics. Metrics reset
when the process restarts. They do not measure research accuracy or provider coverage.

## Request support references

API responses echo `X-Request-ID`. A caller-supplied identifier is accepted only
when exactly one header contains 8 to 64 ASCII letters, digits or hyphens. Otherwise
the API generates a random identifier. Error envelopes add `error.request_id`;
existing code, message and validation fields remain available. The browser API
client retains the reference as `ApiError.requestId`.

`request.complete` records the reference, method, registered route template, HTTP
status when known, duration and outcome. Unknown paths use `unmatched`. Streams
remain unbuffered and complete on response completion, disconnect, cancellation or
failure. Exceptions after headers cannot produce a replacement response. Request
context belongs to the handling task and is restored afterwards; independently
created background tasks do not inherit its request identifier.

Both standard-library and structlog events use the same production JSON formatter
and bounded recursive sensitive-key redaction. Exception diagnostics retain the
exception class, without provider messages, stack locals or traceback text. API
completion events contain no query strings, bodies, cookies or authorisation
headers. Uvicorn access logging is disabled to avoid duplicate raw-path entries.

`feed.health_transition` uses actual states (`idle`, `healthy`, `degraded`,
`disabled`) and fixed reasons. `circuit_breaker` means a temporary cooldown;
`administrator_disabled` means the configured source control. A recovery emits
`poll_succeeded`. Repeated identical states do not create repeated transitions.

## Readiness and the administrator overview

`/api/health` remains a minimal process liveness response. `/api/ready` checks the
database and returns the existing generic 503 envelope if any registered worker
is overdue or event-loop lag exceeds two seconds. Public responses contain no
worker names, counters, provider errors or configuration.

Workers register only when their configured loop starts. Intentionally disabled
feeds, snapshots and conflict screening are excluded. Completed idle cycles count
as progress. A stalled operation or cancelled loop cannot be kept healthy by the
loop-lag monitor or the report job lease timer. Unexpected completed cycle failures
record only `cycle_failed`; provider/source failures remain in source health.

The allowance is three expected intervals since registration or the last completed
cycle. Current intervals are: scheduler pruning 60 seconds; aviation five minutes;
translation 30 seconds; conflict screening 60 seconds; social sampling five minutes;
schedule admission/acquisition 60 seconds; asset expiry 60 seconds; annotation
monitoring five seconds; report queue admission 12 seconds (including its error
backoff); snapshots use their configured interval. Indicator evaluation uses its
configured interval. Per-source scheduler loops use their next scheduled delay,
with a minimum allowance interval of 180 seconds for bounded fetch/processing work.
Long legitimate work can therefore degrade readiness until its cycle completes;
the interval displayed in the runtime view is authoritative.

Loop lag is measured once per second. The p99 uses the latest 120 samples and also
accounts for an outstanding delayed sample. A severe stall can remain visible in
that window after the loop resumes. Linux RSS is current resident process memory;
unsupported platforms show `Unavailable`.

`GET /api/admin/runtime` requires an administrator and a current release fence.
The overview shows per-worker freshness, fixed error codes, stream subscribers,
cumulative drops (including closed subscriptions), queued messages, store usage
against budget, read-admission rejections, report queue depth, RSS and encoder cache
characters. Refresh overview requests new measurements. Aggregates contain no
private report payloads or provider URLs. The existing Uptime workflow already
uses `curl --fail` against `/api/ready`, so a readiness 503 fails that probe.

## Shutdown and acceptance limits

Application cleanup has an 18-second cooperative budget. It preserves dependency
order: schedule admission, report workers/checkpoints, housekeeping, feed workers,
final snapshot, runtime monitor and shared clients/database. Four seconds are
reserved from earlier phases for the snapshot and final disposal. Each callback is
attempted after an earlier failure, with `shutdown.phase` duration and outcome;
`shutdown.complete` reports completed or failed cleanup without exception content.
Cancellation-resistant native/thread work can exceed a cooperative deadline.

The accompanying deployment change uses a 30-second API stop grace and a
10-second Uvicorn request-drain timeout. Applying those protected deployment
settings requires the normal manual release approval. An old atomic snapshot is
preserved if a final save fails; a completed log alone does not prove snapshot age.

Offline tests exercise request/stream correlation, redaction, actual scheduler
cancellation, the three-interval threshold, admin permissions and cleanup order.
A populated-store Compose stop/start, final snapshot age, deployed log routing and
the public Uptime probe require separate operator acceptance. No production stack
or live provider was changed for these tests.
