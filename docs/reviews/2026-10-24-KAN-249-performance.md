# KAN-249: runtime and map responsiveness, 24 October 2026

Implements the four measured bottlenecks in
[KAN-248](https://alex-orr.atlassian.net/browse/KAN-248). Delivery and required
checks are tracked in [KAN-249](https://alex-orr.atlassian.net/browse/KAN-249) and
[PR #229](https://github.com/ShabalalaWATP/AllSeeingEye/pull/229).

## Changes

Social boards and hourly sampling select and aggregate immutable event references
through the existing admitted worker boundary. Keyword matching first rejects
absent literal terms before applying the unchanged escaped word-boundary regex.
This avoids expensive regex scans for each non-matching term without changing
overlapping, Unicode or punctuation matches. SQL reads and current private-term
authority remain on the API loop.

Aviation boards use the same worker boundary for event selection and aggregation.
Mutable interference-map access stays on its owning loop. Translation selects a
bounded candidate batch in a worker, rechecks current content before model work
and merges only into a still-current event. An empty result is reused only while
the store generation is unchanged. Configuring an unavailable translator still
allows existing foreign candidates to be retried; they are not cached as empty.
Completed translations also preserve concurrent provenance and reapply its
four-transformation limit to the current event.

The social response checks visible terms again inside the source release guard.
A monotonic in-process session-change generation detects changes during that last
SQL read, including changes at the same clock tick and after signal-history
eviction. Existing session freshness rules are retained. A rare unrelated account
change in this short phase conservatively produces a retryable response.

Map snapshots publish their primary result before serial supplements finish,
then merge available coverage progressively. The cumulative stream journal wins
at every stage. Cancellation, expiry, source reservations, selection and the
5,000-event mirror remain bounded. An exhaustive viewport page shorter than 2,000
rows skips supplements; global statistics no longer make a complete small
viewport appear truncated. Crowded pages retain supplemental coverage and leave
the second per-user read slot available to another panel.
Partition refreshes retain an existing incomplete-coverage warning until a full
replacement can establish completeness for the rest of the mirror.

Owner labels use only requested IDs and display names, in batches of at most 200.
They are still resolved after record-list authorisation. Current-actor names,
missing owners and names on inactive accounts keep their previous semantics.

## Controlled before/after measurements

`scripts/benchmark_runtime_responsiveness.py` selects the source checkout and
verifies the imported package path. The same fixture measured deployed base
`6c2fd3a4` and runtime candidate `7efd5af3`, serially without coverage or competing
test suites. Each case warms up once, then collects three social or five other
samples. Times below are medians; loop gaps are the median of each sample's
maximum 1 ms heartbeat gap.

| Workload | Before, ms | After, ms | Before loop gap, ms | After loop gap, ms |
| --- | ---: | ---: | ---: | ---: |
| Social, 10,000 posts in the completed hour, 16 terms | 1,458.0 | 210.8 | 1,458.1 | 31.9 |
| Social, 10,000 posts in the completed hour, 32 terms | 2,716.7 | 215.1 | 2,716.8 | 31.9 |
| Social, 10,000 across 24 hours, 32 terms | 232.8 | 122.0 | 232.9 | 31.8 |
| Aviation, 15,000 current aircraft, 22 areas | 63.9 | 61.5 | 64.0 | 30.0 |
| Translation, unchanged all-English store | 66.6 | 0.034 | 67.1 | 16.2 |
| Translation, store changes before each poll | 65.1 | 62.3 | 65.2 | 30.0 |

The busy social fixture is a high-load scenario, not measured production
occupancy. It retains 60,000 events in total, estimated at 315.66 MiB within the
normal 512 MiB store budget. The 32 terms comprise 16 public and 16 actor-owned
terms. The uniform case has 417 posts in the completed hour. Result counts are
unchanged. Service database awaits are stubbed, and no provider/model is called.

The machine was Windows 11, an i9-12900H with 20 logical CPUs and 31.6 GiB RAM,
using Python 3.13.3. Its idle heartbeat gap was about 16 ms. Worker projections
still compete for the Python GIL; these measurements do not promise zero stalls,
production request latency or GPU frame rate. No major garbage collection occurred
in these timed samples. The separate inline keyword microprobe is a deliberate
CPU control, not the new production execution path.

The private SQLite owner fixture changed from 200 SELECTs and approximately
67 ms to one SELECT and approximately 1.5 ms for 200 distinct owners. Timings are
single local observations; deterministic regressions enforce query/parameter
bounds and requested-ID/name semantics. Repeated copies of one ID still need one
query; actor-only and empty requests need none.

Frontend regressions verify early publication while a supplement is deferred,
progressive coverage, a selected vessel, intervening upserts/expiry, late cancelled
responses, partial failures and partition refreshes. Empty and one-row viewports
with crowded global statistics need one event request instead of the former
eight-request path. Exactly 2,000-row pages still load supplements. These are
deterministic request/result checks, not measured network latency.

## Reproduction and release

From `backend`, using an isolated checkout and its existing frozen environment:

```powershell
uv run --frozen python ../scripts/benchmark_runtime_responsiveness.py --skip-worker
```

Pass `--checkout` to point the identical script at another revision. Run CPU
probes serially, without coverage or other suites. Full-mode execution also checks
existing warm worker query/DTO paths. Tests use private synthetic SQLite fixtures;
remove operator database integration hooks as documented in
[parallel development](../PARALLEL_DEVELOPMENT.md#test-and-runtime-separation).

Required CI and independent review evidence belongs to the PR. No thresholds,
retention budgets, read admission limits, dependencies or schemas are changed.
Merge and deployment require the repository's release approval. This record
does not claim a production profile, rollout or live improvement.
