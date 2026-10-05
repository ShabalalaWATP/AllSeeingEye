# KAN-81: current control rendering

## Scope

The first control milestone began from main `91d2034d`. Unchanged tool entries receive
scalar metadata and current callbacks through a memoised component. Event updates
can still replace the active drawer's content without rebuilding those entries.
Navigation callbacks retain their complete dependencies.

The controlled traffic drawer no longer derives unused legacy portal lists.
Standalone portals derive their lists when mounted, using current events,
callbacks and selection guards. News summaries are derived inside the mounted
news drawer. They deliberately retain no array-identity cache, so corrections,
filter changes and expiry remain visible.

The first milestone changed no event store, permission boundary, stream
protocol, dependency, canonical fixture or benchmark. Later milestones include
the stable military-priority partition in the event-store coverage selector,
described below. This is further optimisation alongside the previously merged
stream work.

## First milestone correctness evidence

The unchanged source reproduced three regression failures and one passing
callback case before the implementation. The final focused run passed 69 tests
across 13 files, including navigation history, CCTV, standalone portals, news
workspace invalidation and expiry. Both TypeScript configurations, targeted
ESLint, Prettier and staged diff checks passed. All touched source files are
below 350 lines.

Independent code-quality and defensive security reviews found no actionable
finding in the frozen candidate. Review was static; it does not establish a
performance gain. The source patch SHA-256 is
`7ec1d13b347979677fda1284eb92b56b5eb25f6c46fa73b5f7595f47771c6c96`.

## First milestone canonical measurement

One baseline invocation and one candidate invocation used the unchanged
5,000-record fixture, Node 24.19.0, one Vitest worker and disabled coverage.
Both passed their correctness assertions. Figures are milliseconds.

| Scenario | Main median / maximum | Candidate median / maximum |
| --- | --- | --- |
| New IDs | 67.21 / 105.87 | 71.75 / 113.86 |
| Existing IDs | 44.80 / 55.37 | 47.52 / 66.09 |
| Mixed expiry/upsert | 53.29 / 58.37 | 59.75 / 64.48 |
| Control latency | 42.71 / 51.39 | 40.00 / 59.40 |

This fixed-order pair shows no overall timing improvement. The separate source
trees and frozen installations may have different filesystem cache histories;
one pair establishes neither repeatability nor the cause of each difference.
The negative result is retained without retries or changed thresholds.

## Event scope and engine lifecycle

A subsequent candidate separates the event provider from the page shell. The
shell retains canvas, display, visibility and navigation inputs. The provider
retains one unconditional event, clock, filter, selection and scene pipeline.
Real clock expiry and current access/filter changes remain inside that pipeline.
The combined route and control check passed 76 tests across 14 files before the
engine lifecycle review. That result does not include the repair below.

Review found that child effects could consume a saved view or authorised cyber
focus before the parent engine mounted or synchronised its projection. Real-route
regressions reproduced five failures; focused engine tests reproduced another
seven failures. The repair gives the engine one latest navigation intent and a
generation-aware commit, applying or discarding deferred navigation after
projection synchronisation. New navigation supersedes either intent kind.
Disabled, failed and disposed engines clear pending navigation. Ordinary ready
navigation remains immediate.

The first focused repair check passed 22 tests, including projection-before-camera
ordering, supersession, warm cyber focus and StrictMode replay. The combined run
passed 113 tests across 20 files. Subsequent type/lint corrections passed their
affected checks; the recorded failures are retained.

Independent review then found a re-entrant projection case: the engine still
advertised its old projection while synchronising the new one. Three further
regressions reproduced incorrect camera/focus dispatch during that call. The
narrow repair marks the projection unknown during synchronisation and defers
navigation until it completes. All 27 affected tests, both TypeScript checks,
targeted lint, formatting and diff checks passed. Independent quality and bounded
defensive security reviews cleared the final manifest
`f46ee6b7eb00065ee8212ade1fe0720f0ec465db3084efb698a160a3419f0211`.
The queue holds geometry only; this review does not prove an additional authority
fence for already-read camera coordinates.

## Provider milestone canonical measurement

One new baseline/candidate pair used the same original fixture, command, Node
version and worker count after the substantive event-scope and lifecycle changes.
Both invocations passed the unchanged correctness assertions. No extra warm-up,
profile or retry was included. Figures are milliseconds.

| Scenario | Main median / maximum | Candidate median / maximum |
| --- | --- | --- |
| New IDs | 43.07 / 52.91 | 45.51 / 56.20 |
| Existing IDs | 33.62 / 49.93 | 28.94 / 40.93 |
| Mixed expiry/upsert | 47.05 / 52.79 | 36.49 / 44.59 |
| Control latency | 28.63 / 44.47 | 22.69 / 36.46 |

Existing, mixed and control timings improved in this fixed-order pair. New-ID
timings worsened, and every median still exceeds 20 ms. Three maximums meet the
50 ms bound, but the new-ID maximum does not. The result therefore does not meet
acceptance or establish repeatability. The merge timer also includes synchronous
subscribers and timer dispatch, so it does not isolate store-only cost.

## Separate CPU diagnostic

A repaired private capture completed one unchanged canonical invocation using
the independently reviewed bounded process owner and one-millisecond sampling.
The actual child and launcher exited zero, the test passed and all owned process
handles closed. The raw whole-lifecycle profile contains 5,115 samples and is
retained unchanged. Final hook output confirms successful profile write,
disconnect and receipt close. No latency figures from this invocation are
acceptance evidence because sampling adds overhead.

The original analyser rejected one negative 18-microsecond sample delta. This
exposed a chronological-order assumption in the analyser rather than a capture
failure: [Chromium's CPU profile implementation](https://chromium.googlesource.com/devtools/devtools-frontend/+/9a696c4e723caa3c7e1f78886da353f1f06a79b0/front_end/core/sdk/CPUProfileDataModel.ts)
reconstructs signed cumulative timestamps and sorts timestamp/sample pairs.
The separately reviewed private v3 parser passed eight offline tests and
successfully summarised the retained profile without another application run.
Its 5,115 samples include 1,284 under the delivery ancestry. Inclusive samples
overlap and are not call counts, CPU percentages or recoverable savings.

## Stable military-priority partition

A further isolated change replaces the vessel and aircraft stable boolean
priority sorts with military-first stable partitions of the same geographic
fair sequence. Classification is read from current objects on every rebuild;
there is no classification cache. Reservation quotas, satellite ordering,
remaining allocation, selected-record retention and original slice expressions
are preserved, including unusual numeric limits.

The unchanged source passed 19 new equivalence cases but failed the objective
priority-read budget: 10,496 military-field reads for 5,250 traffic records.
After the partition, the expanded six-file check passes 88 tests, including 25
new cases. Independent quality and security source reviews are clear at source
SHA-256 `3e207481f5e9fc6866a10464adbaed52b161c1118cd5ee7201ec5cbd58aff165`
and test SHA-256
`19096adb788fbb22b9292f95610ac8da9bdb65b220c6c5a4c09ce1a60cb1b4af`.
The test-only no-op callback lint repair was independently reviewed and the
new 25-case file passed again afterwards. All 31 other prior source/protected
input pins match. Scoped ESLint and Prettier pass; both TypeScript configurations
passed before that equivalent test-only repair. The private result receipt has
SHA-256 `4fd9ccb1152978d39a9ef4e029249d40c3c7b6c739b56ea523931f9376ee87ff`.
These focused correctness/static checks used the PATH Node 22.20.0 runtime;
they are not Node 24.19.0 validation. The canonical pair must use the explicitly
pinned 24.19.0 binary and pnpm 11.25.0 dependencies.
At that correctness checkpoint no canonical timing run had been performed for
this partition. The later measurement is recorded below. The unpublished
feature branch was fast-forwarded to
856722f to include PR 127's three non-overlapping paths. Historical freezes
remain intact; all owned source/protected pins were preserved. The existing
clean pagination checkout has the identical Git tree as 856722f, although its
actual pre-squash commit is d706c011. A fresh packet must record this distinction
and verify runtime/dependency readiness before the next paired measurement.

## Single-pass satellite counts

The group-count hook now counts matching NORAD identifiers in one pass, using
fresh per-group sets. It preserves numeric/string identifier equivalence,
fallback identity and current mutable classifications. The actual satellite
filter remains unchanged. On the baseline, the new regression observed 55,000
category reads against a 20,000 bound for 5,000 non-satellite records.

With pinned Node 24.19.0, the final focused checks pass 63 tests across five
files, including the repaired 17-case count file. Scoped ESLint, Prettier,
both TypeScript configurations and diff checks pass. Independent quality and
security reviews are clear on the frozen three-file change. The private result
receipt has SHA-256
`f6ea66aa3c1064ab6df8d7775ed2ced96a8bfda41e21502ba7579fa82e77070a`.
These correctness results do not establish application latency.

## Fresh scene-row preparation

Layer preparation now builds exact, approximate, approximate-icon and traffic
rows in one fresh ordered pass, retaining the first mapped, visible selected
record. Geographic fairness, the 250-row traffic reservation and selected-row
exception, cluster mathematics, layer builders and draw order remain unchanged.
There is no classification cache. A preserved independent old row oracle checks
order, current object/member identity, duplicate selection, zoom/traffic bounds,
corrections, removals and callback behaviour.

The old source failed the objective regression at 15,000 precision reads against
a 10,000 bound. An initial test wrongly treated 250 reserved traffic rows as a
total icon cap; the retained failure exposed the unclustered remainder, and the
test was corrected to preserve the original 251 visible rows and selection at
reserved index 249. Later test-only lint/type repairs retained the assertions and
were independently reviewed. The final candidate passes 70 affected tests and
the final 18-case regression, scoped ESLint/Prettier and both full TypeScript
configurations with Node 24.19.0. Production SHA-256 is
`bd3b784de4e3e9f5bf7aa318438e88256e00fc254809e3d5441601869c8f5558`;
final test SHA-256 is
`a062dd02d0f941ac030ec5c95e5e64e3c7c0ce08bd09084bccf40ff42234af13`.
Quality/security reviews are clear; all 46 other prior pins match. Private result
SHA-256 is `13d2af4f09c0b2f529c034073e71e5e9ee2d5f9487e3a4cfe9aeea8dc2ce7db5`.

## Remaining acceptance

The fresh release-parity canonical pair ran once on each arm with pinned Node
24.19.0 and the unchanged original fixture/benchmark. Both test bodies passed
1/1, source/runtime/protected pins matched before and after, and all owned child
jobs/handles closed cleanly. Candidate median/max milliseconds were: new
70.88/118.03, existing 50.30/59.04, mixed 72.05/92.87 and controls 43.38/51.88.
All original latency limits remain unmet. The private fixed-order packet and
raw logs are preserved under canonical-priority-pair-856-v1. No repeatability,
cache-history equality or causal speedup is claimed from this single pair.

The later v2 pair includes the satellite-count change. Both original benchmark
tests again passed 1/1 with pinned Node 24.19.0. All pre/post pins matched and
owned jobs and handles closed without cleanup errors. Baseline median/max
milliseconds were new 47.99/59.67, existing 32.04/47.28, mixed 39.64/50.66 and
controls 37.85/58.22. Candidate values were new 43.83/66.95, existing
30.21/42.30, mixed 43.23/57.49 and controls 31.01/56.28. Every candidate median
still exceeds 20 ms; new, mixed and control maxima exceed the strictly-under-50-ms
limit. The fixed-order packet and original logs remain privately retained under
canonical-priority-pair-856-v2. This single pair does not establish repeatability,
equal cache history or causal savings. No latency acceptance criterion was changed.

The v3 pair includes fresh scene-row preparation. Both original benchmark tests
pass 1/1 with all pre/post pins and owned cleanup clear. Baseline median/max
milliseconds are new 52.69/68.99, existing 33.65/49.11, mixed 45.40/56.57 and
controls 36.78/69.52; candidate values are new 33.98/48.99, existing 22.85/27.38,
mixed 29.71/38.13 and controls 25.01/34.85. All candidate maxima are below 50 ms
in that invocation, but all medians still exceed 20 ms. Original limits remain
unchanged. Fixed-order import/setup histories differ, and no matched speedup,
equal cache history or repeatability is claimed. The v3 packet and raw outputs
are preserved separately from earlier measurements.

Independent combined quality and defensive security reviews subsequently
verified all 35 source/test pins and 13 shared/protected pins against the v3
manifest. Both reviews found no actionable source issue. They checked the
combined current-data, selection, callback and engine-lifecycle flow, including
the seven newer partition, count and row-preparation paths. These were static
reviews and did not run tests or establish latency acceptance.

Private real-browser preparation retained a failed transport-parity check:
the normal 384 KiB bus estimate rejects the canonical 250-record upsert as a
single frame. Targeted mixed-batch expiry parity passed. A separate diagnostic
using smaller normal transport frames is being prepared; it cannot be labelled
an identical canonical transport measurement. No real browser trace has run.

The broader frontend suite passed 4,547 tests with one skip, across 835 passing
files and one skipped file. Final JSON readback showed that configured Vitest
projects ran the canonical benchmark once under coverage despite the explicit
exclusion flag. The intended exclusion was not achieved. Its passing result is
an incidental instrumented correctness check, not another canonical latency
observation. The raw command, receipts and correction audit are retained.
Statements/branches/functions/lines coverage was
96.26%/92.24%/94.70%/97.42%. The unchanged auth and branch floors, production
build and bundle checks passed. All five check commands exited zero, with no
retry or source edit during the invocation; owned jobs closed cleanly.
Build-time pnpm metadata removed only the empty `ignoredBuilds` entry from
`.modules.yaml`. All 45 checked package identities, installed lock, source and
protected inputs remained pinned. Installation metadata was therefore not
byte-identical, and that difference is retained in the final audit.

The original canonical fixture's median-at-most-20-ms and maximum-under-50-ms
targets remain unchanged and are unmet. A real browser trace remains
outstanding. No real browser performance result is claimed by the focused or
broader tests. This is a correctness-validated milestone; KAN-81 remains open
while further work is assessed.
