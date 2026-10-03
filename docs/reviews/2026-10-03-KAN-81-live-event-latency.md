# KAN-81 live-event latency investigation, 3 October 2026

The current candidate does **not** establish an overall latency improvement and
does **not** meet the ticket's median target. This is a tested correctness and
measurement checkpoint, not acceptance evidence for closing KAN-81. A real
browser trace is still outstanding.

## Scope and correctness

The starting revision was `e22c599a3e8db8fdbc1ea44747040dcc3cdfdd7e`.
The candidate caches map timestamp parsing with witnesses of the actual parsing
inputs. It reselects eligible GDELT indexing metadata on each call, preserving the
distinction between indexing and publication dates. Replacement records and
in-place corrections invalidate the cache; invalid dates remain invalid.

The retention path reuses sort records, checks both timestamp fields before
reuse, and collects its four disjoint source categories in one pass. It retains
the complete freshness comparator, geographic ordering, stable military and
catalogue priorities, quota order, selected-record exception and output order.
The remaining-capacity scan stops once full, including zero capacity. Unusual
numeric limits retain the previous filter/slice behaviour.

The regression suite also records actual React Profiler commits inside the
stable control boundaries. An unrelated batch produces no control commits while
the event count and layer update. A relevant control change still commits.

Validation performed on this candidate:

- 144 focused tests across 21 files passed, covering the event store, batching,
  retention, replay, map timestamps and control rendering.
- Targeted coverage of the two changed production files was 100%: 93 statements,
  77 branches, 20 functions and 77 lines. This is not global coverage.
- Both TypeScript configurations, owned-file ESLint, Prettier and `git diff
--check` passed. Every changed handwritten file has fewer than 350 lines.
- With the original timestamp implementation, five new repeated-parsing
  assertions failed. The tests also assert actual dates, invalid-date rejection,
  replacement, nested metadata correction and clock-driven expiry.
- With the original retention implementation, both in-place timestamp correction
  regressions failed. The candidate matches an independent uncached reference
  for ordered keys and retained object identities, including 13 quota boundaries,
  invalid dates, zero capacity, selected records and mixed expiry/replacement.
- Independent read-only review of the exact retention patch found no actionable
  correctness or test-gap issue. No permissions, transport, dependencies,
  telemetry or external-service behaviour changed.

## Unchanged measurement protocol

The canonical fixture and benchmark were not edited:

- `frontend/src/test/streamFixture.ts`: SHA-256
  `42fee34436e2a0a4d98d20ba85af9ca16ab5c7ae41bac9ad4f0b676b8e509786`.
- `frontend/src/features/globe/GlobePage.streamBenchmark.test.tsx`: SHA-256
  `55b6fd786cbcc10998a801adcc0626c108b483eb9a9b8d351e6a8e2ce2bdc254`.

The real React route runs under jsdom with fake MapLibre, deck.gl and stream
adapters. It maintains 5,000 mixed located events and measures 20 batches in each
scenario: 250 new IDs, replacements of the latest 250 generated IDs, and expiry
of the retained list's oldest 50 records together with 200 new records. The
control scenario alternates map/globe mode during 20 further batches.

The original batch timer starts after message emission and measures buffer flush
plus the React commit. It excludes message decoding and validation. The control
timer starts after synchronous batch flush and calls the mode store directly;
it is not a browser click-to-paint measurement. The ticket's documented targets
are median at most 20 ms and maximum below 50 ms on this fixture. A browser trace
must separately cover the real transport, renderer and input queue.

Each source state received one discarded warm-up followed by five separate
single-worker runs without coverage. The same private installation was used:
Node 24.19.0, pnpm 11.19.0, frozen lockfile with SHA-256
`e3e131820f6e38dc5ceb69881963df08544313d3897637dc9a34febb7619ed2b`.
The available pnpm executable was older than the repository's declared 11.25.0;
the frozen installation succeeded without changing the lockfile.

The coordinator reserved quiet local CPU windows. Baseline runs finished at
00:27:43 UTC; timestamp-only measurements ran 00:41:56–00:43:56; combined
measurements ran 01:03:01–01:05:01. These were sequential blocks, not randomised
or interleaved trials. All 15 measured runs passed, with one React commit per
batch. Warm-ups and diagnostic profiles are excluded below.

## Results

Each cell reports the median of five per-run medians, followed by the largest
individual batch maximum across those runs, in milliseconds. The per-run
medians are included below to expose the variability.

| Scenario             |      Baseline | Timestamp cache | Combined candidate |
| -------------------- | ------------: | --------------: | -----------------: |
| New IDs              | 44.18 / 73.17 |   46.26 / 67.90 |      46.15 / 84.15 |
| Existing IDs         | 34.99 / 64.12 |   34.22 / 62.80 |      32.14 / 66.79 |
| Mixed expiry/new IDs | 41.04 / 59.96 |   39.60 / 61.00 |      40.79 / 61.32 |
| Mode switch          | 25.37 / 48.97 |   27.24 / 44.33 |      28.37 / 49.30 |

| State / scenario     | Five per-run medians (ms)         |
| -------------------- | --------------------------------- |
| Baseline / new       | 48.00, 44.18, 42.65, 41.53, 51.17 |
| Baseline / existing  | 34.99, 36.36, 32.93, 30.32, 40.17 |
| Baseline / mixed     | 42.63, 41.04, 35.01, 46.83, 38.99 |
| Baseline / mode      | 23.61, 24.37, 28.79, 35.87, 25.37 |
| Timestamp / new      | 43.03, 41.25, 46.26, 47.97, 48.57 |
| Timestamp / existing | 30.77, 38.44, 28.03, 38.11, 34.22 |
| Timestamp / mixed    | 39.60, 37.71, 39.40, 44.59, 49.80 |
| Timestamp / mode     | 26.66, 27.35, 27.24, 31.96, 24.51 |
| Combined / new       | 51.47, 46.15, 48.90, 43.86, 38.60 |
| Combined / existing  | 38.31, 29.23, 36.76, 32.14, 30.57 |
| Combined / mixed     | 43.11, 39.03, 40.18, 40.79, 46.21 |
| Combined / mode      | 28.37, 27.93, 31.29, 26.44, 30.65 |

The ranges overlap substantially. Existing-ID medians were lower, while new-ID
and control medians were higher. The results do not support a total-speed win.
All scenario medians remain above 20 ms, and each event scenario has an observed
maximum above 50 ms.

## Separate diagnostic profile

The same canonical test was profiled separately through Node's inspector CPU
profiler. The candidate profile finished at approximately 01:05:50 UTC. Its
timings are not included in the comparison. Sampled inclusive time under the 60
event-delivery call stacks was:

| Function             | Baseline (ms) | Combined (ms) |
| -------------------- | ------------: | ------------: |
| `boundedEvents`      |       466.550 |       420.526 |
| `buildEventLayers`   |       415.779 |       369.875 |
| `useDashboardEvents` |       436.416 |       352.324 |
| `toList`             |       165.927 |       130.998 |
| `clusterEvents`      |       179.044 |       166.738 |

These values overlap through nested calls and must not be added. Each is one
sampled diagnostic run, not a statistically established improvement. Delivery
stacks also include work before the original timer. Retention, dashboard
derivation and layer construction remain concrete places to investigate.

## Receipts and remaining work

The correctness checkpoint was committed as `4cea89d8` and normally integrated
with main `8c0b93cf` at `85274aa5`. The same 144 focused cases and both TypeScript
configurations passed after that merge. The frontend manifest, lockfile,
canonical benchmark and fixture did not change through the integration.

A subsequent narrow candidate in `events.batch.ts` keeps a replacement record
in its previous sort position only when both its ID and `published_at` are
unchanged. It retains the strict order validation and full-sort fallback, uses
current replacement identities, and inspects every dictionary value before
returning a sequence with no new positions to merge. Expiry, correction and
last-update-wins semantics remain covered.

Before this change, the deterministic 5,000-record/250-latest-replacement test
made 5,248 comparisons and failed the bound of 5,000; its order and identity
checks already passed. The candidate passes all 158 focused cases in 22 files,
both TypeScript configurations and owned lint/format checks. Targeted coverage
of all three changed production files is 100%: 138 statements, 112 branches,
27 functions and 115 lines. This validates correctness and bounded work only;
independent read-only review of the exact source and test patch found no
actionable issue. The candidate's canonical timings are pending. The diagnostic `toList` sample
suggests a modest opportunity, about 2 ms per batch, not enough by itself to
support the ticket's 20 ms target.

Raw logs, JSON run receipts, exact timestamps, source hashes, CPU profiles and
summary scripts are retained privately at
`C:/Users/alexo/.codex/worktrees/kan81-live-event-latency/evidence`. Files include
`baseline.json`, `timestamp-cache.json`, `combined.json`, `comparisons.json`,
`combined-profile-receipt.json`, and the two profile directories. These local
artefacts are not committed build output and are not assumed to be available to
another checkout. The benchmark can be reproduced from `frontend` with:

```text
node node_modules/vitest/vitest.mjs run src/features/globe/GlobePage.streamBenchmark.test.tsx --maxWorkers=1 --no-coverage
```

Measured combined source hashes are `a274e21b...9285ba2be` for `newsMapTime.ts`
and `4c979666...0fd069116` for `events.coverage.ts`; full hashes are in each run
receipt. Historical negative measurements in `PERFORMANCE_REPAIR.md` remain
unchanged. Broader validation, an evidenced latency improvement and the real
browser trace remain required before publication or acceptance.
