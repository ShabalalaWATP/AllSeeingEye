# KAN-81 browser acceptance, 6 October 2026

The reviewed implementation is `218ce5809a62fb62ea1e7a72c59027611abbc290`.
The remaining browser capture completed on that exact frontend and backend in
Edge, using real MapLibre/deck rendering, ordinary authentication and SSE.

## Acceptance interpretation

[KAN-81](https://alex-orr.atlassian.net/browse/KAN-81) explicitly retains the
20 ms median and under-50 ms maximum figures as targets on the documented
fixture, not unit-test deadlines or promises about every device. Later entries
in the implementation plan incorrectly treated those targets as a closure gate.
This acceptance review therefore does not impose them as additional closure
gates. That is an interpretation of the existing criteria, not a change to Jira.

The required functional changes are already merged through PRs #129, #130,
#131, #132 and #133. Main [CI 37518374646](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37518374646)
passed. Its [merged frontend report](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37518374646/job/112459444381)
records 4,637 passing tests in 845 files and
92.28% branch coverage, with one unrelated optional benchmark skipped.

Existing tests cover stable-control Profiler commits; current filters,
permissions, preferences and clock expiry; coherent mixed batches and quotas;
soft/hard snapshot reconciliation; and renderer, motion, selection and lifecycle
behaviour. These were audited against current main, not inferred from PR titles.

## Documented fixture timings

The retained current-main Windows observation uses the original checked-in
5,000-event fixture. Values below are median/maximum milliseconds.

| Scenario | Current main |
| --- | ---: |
| New IDs | 25.21 / 33.48 |
| Existing IDs | 15.62 / 19.23 |
| Mixed expiry/upsert | 23.50 / 36.02 |
| Controls | 15.39 / 24.22 |

The new-ID and mixed medians remain above target. The historical 58/112 ms
new-ID result is descriptive context, not a controlled causal speedup claim.
Unmerged exploratory variants and negative observations remain retained.

## Completed real-browser observation

The private installation used locked dependencies, the current production build,
a fresh synthetic ordinary user and SQLite database, and disabled external
feeds, providers and delivery channels. It started with the original 5,000-event
mirror. All 80 logical batches at 250 ms cadence completed: 40 bootstrap plus
160 measured transport frames. Delivery completed at 22:17:10.372 UTC.

Aircraft search and map controls were exercised through normal browser UI.
Search entry and settled results were observed during the existing-ID phase.
Zoom was at the final delivery boundary, not proof of an additional mid-batch
interaction. Twelve genuine viewport snapshots returned HTTP 200.
Zooming used the application's genuine bounded geographic refresh; visible
viewport population can therefore change. Server delivery does not prove that
every individual update painted.

Source-attributed main-thread stream-flush tasks in the saved trace were:

| Phase | Observed tasks | Median ms | Maximum ms |
| --- | ---: | ---: | ---: |
| New IDs | 12 | 33.680 | 46.569 |
| Existing IDs | 10 | 10.466 | 26.698 |
| Mixed | 12 | 29.516 | 45.706 |
| Controls | 12 | 33.206 | 43.879 |

One additional tail flush took 27.268 ms. None of these 47 tasks exceeded
50 ms. They are observed coalesced timer tasks, not end-to-end batch or GPU
latencies. The trace does not show an every-batch long-task pattern.

Outliers remain part of the evidence: two separate application scheduler tasks
took 58.536 and 51.161 ms during delivery; two DevTools observation tasks took
67.478 and 60.101 ms. After delivery, MapLibre worker handling took 148.207 ms
and garbage collection took 63.174 ms. Browser EventTiming recorded a zoom-in
click at 239.315 ms and a later click at 473.635 ms. This is bounded evidence of
working interaction, not a claim of uniformly low input-to-paint latency.

The trace completed without reported data loss. Both application processes
exited normally, the real lifespan completed, private job/credential tables
remained empty, and owned processes and listening ports were released.

The first attempt is preserved: an over-restrictive diagnostic guard rejected
a legitimate viewport refresh after 172 frames. Its failing regression and
12 passing repaired-harness checks are retained. The application was unchanged
between attempts. Neither that failed attempt nor post-abort interactions are
substituted for the completed capture.

Raw traces, UI observations, source/build manifests and cleanup receipts remain
in the private `kan81-browser-acceptance-218-20261006` evidence packet. They are
not committed as repository assets. The capture supports the original scoped
acceptance criteria with the timing limitations above explicitly retained.

Evidence SHA-256:

- Trace: `b75ed3717d6fbc08674d230e58426064d0fc197ace24daea9e9f0af35883ce41`.
- UI observations: `ef98d08562d7e5e67a031803b0e292fc3c3bc7282a5fb50f389c7e3a6547a323`.
- Detailed analysis, including all input-duration groups:
  `a71363155f176aa8c0049cafcc3130776a45a5225322e86d73d57db68abfce90`.

An independent acceptance review checked the original Jira wording, complete
delivery and cleanup records, normal viewport responses and interaction timing
boundaries. Its two wording refinements are incorporated above. No further
application changes or test execution were needed for this acceptance record.
