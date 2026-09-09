# Map rendering performance audit

## Scope and evidence

This audit addresses the reported freezes after map-tool additions. It covers camera clustering, layer data reuse and camera-view subscriptions. Event-store/SSE reconciliation and server runtime work are recorded separately. No browser or GPU profiling was performed because browser access was unavailable under the existing policy. Unit tests and CPU timings do not establish end-to-end frame rates or prove all freezes are resolved.

The reproducible CPU benchmark is `frontend/src/features/globe/rendering.benchmark.test.ts`: 5,000 located events and 75,000 deterministic worldwide camera positions, five successive runs, camera zoom 13 and global bounds. Run with `pnpm exec vitest run src/features/globe/rendering.benchmark.test.ts --maxWorkers=1`. It reports timings rather than enforcing machine-dependent timing thresholds.

| Camera clustering implementation | Five observed times (ms) | Median (ms) |
| --- | --- | --- |
| Original full adaptive passes | 1412.95, 1199.43, 1178.63, 1388.03, 1094.30 | 1199.43 |
| Early pass rejection | 191.59, 105.10, 93.93, 152.00, 175.62 | 152.00 |
| Packed cached vectors | 91.18, 109.25, 115.06, 117.50, 81.09 | 109.25 |
| Numeric cell keys as well | 26.74, 8.88, 8.84, 8.00, 7.33 | 8.84 |

These are local CPU measurements, affected by JIT warm-up and concurrent host load. The event-layer median changed from 37.94 ms to 6.52 ms across the same benchmark runs, despite no comparable event-construction algorithm change. Consequently the exact camera speed-up ratio is not a portable guarantee. The deterministic operation-count regression supplies independent evidence that redundant work was removed.

## Causes and repairs

Camera aggregation previously scanned every camera at each candidate resolution, even after the occupied-cell count had exceeded the 2,000-marker budget. A fine worldwide view repeatedly allocated and populated grids that were certain to be rejected. A pass now stops immediately when it exceeds the budget. Cell count cannot decrease within a pass, so the accepted final resolution and full coverage remain intact.

Spherical vectors now use a packed `Float64Array`, weakly keyed by the immutable catalogue array. Panning no longer allocates 75,000 vector objects or recalculates their trigonometry. Replaced catalogues can be garbage collected with their buffers. Three quantised coordinates use an exact numeric key, avoiding repeated coordinate-string allocation. The minimum supported cell size keeps packed values below 2^48, within JavaScript's exact-integer range.

Camera grouping is memoised separately from picking callbacks and projection styling. Changing measurement/drawing ownership or projection alone reuses grouping. View changes remain debounced until 150 ms after movement stops, equal viewports are ignored, and disabled CCTV does not subscribe to map movements. Selected-camera lookup is memoised instead of scanning the catalogue on unrelated event updates.

Event icons and scatter layers now provide an immutable-row comparator. Selecting an object or changing a callback can allocate a new wrapper array without forcing Deck to invalidate every position attribute. Changed row objects, ordering or count still invalidate data; selection size/colour triggers remain active. The installed Deck implementation honours this comparator in `@deck.gl/core/src/lifecycle/props.ts`.

## Regression guarantees and limits

- All 75,000 cameras contribute to individual markers or cluster counts, including a selected individual, within the existing 2,000-marker budget.
- The high-zoom worldwide fixture performs fewer than 500,000 coordinate quantisations. Previously every rejected grid performed another complete 225,000 quantisations.
- Batched drag notifications perform no regrouping until the camera settles; an identical viewport causes no additional grouping.
- Gesture/projection changes reuse grouping; changed catalogue coordinates rebuild vector data.
- Row comparisons preserve unchanged buffers and invalidate changed positions, order and length.
- Existing dateline, viewport culling, selection and layer tests remain part of validation.

The global live-event budget remains 5,000. No feeds, cameras or geographic coverage were removed. These changes do not resolve upstream availability, network queues, GPU-driver faults or all possible heavy overlays. Final integrated validation and runtime observation remain necessary.

## Informational response-decoding benchmark

`responseParsing.benchmark.test.ts` is opt-in through `ASE_PARSE_BENCHMARK=1`; it does not change the API client. Three runs separate synchronous JSON parsing from Zod response validation:

| 2,000-row fixture | UTF-8 wire size | JSON parsing (ms) | Schema validation (ms) |
| --- | --- | --- | --- |
| Representative aviation records, ten scalar attributes | 1.41 MiB | 11.30, 9.57, 9.08 | 54.20, 27.22, 12.23 |
| Metadata-heavy records | 109.48 MiB | 206.74, 174.49, 169.20 | 82.42, 52.95, 47.39 |

The heavy fixture uses domain limits of 300 title characters, 2,000 summary characters, 40 attributes of 500 characters each, four transformations with 2,000-character original and translated strings, and four source-date records. Multibyte source text contributes to wire size. It is a valid stress case, not an observed live response or a claim that ordinary aircraft carry this much metadata. Its combined synchronous work can block for roughly 200–290 ms. This supports considering a response byte budget separately from row limits if real traffic approaches these sizes; it does not justify removing validation. The opt-in guard avoids allocating this large fixture in routine CI.
