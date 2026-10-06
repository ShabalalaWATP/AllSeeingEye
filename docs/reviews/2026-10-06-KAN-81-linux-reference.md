# KAN-81: one Linux reference observation

This revised protocol is prepared, not executed. It changes the fixed candidate to
the reviewed null-selection traversal guards. No new timing or acceptance result
is claimed. Completed Linux observations `37486974563` (candidate `435cbdf6`) and
`37497054952` (candidate `38c487c9`) remain unchanged: both completed their two arms
with input and cleanup checks, but both candidates missed the targets. This is a
new-source observation, not a rerun or relabelling of either result. The prior
Windows v5 baseline timeout and every earlier negative pair also remain evidence.

## Scope and trigger

The repository owner may deliberately apply `kan81-linux-reference-once` to the
reviewed same-repository PR containing this workflow. It listens only to the label
event, not subsequent pushes. Manual dispatch becomes available after merge.
GitHub reruns (attempt greater than one) are refused. Do not remove/reapply the label
or dispatch another run to obtain a favourable result. A later observation needs a
separately reviewed protocol. Concurrency serialises these jobs without cancellation.

One `ubuntu-24.04` job runs baseline then candidate on the same hosted VM. This pins
the OS family, not a permanent CPU or immutable runner image. The receipt records
image version, kernel, architecture, CPU and memory. Hosted hardware, scheduling,
filesystem warming and fixed arm order limit causal and repeatability claims.

## Frozen application and dependency inputs

- Baseline: `88164eb99150d5d94367f8257569100684f9e619`. Its frontend equals the
  historical `d706c01124d5ff6db443c32f74b9e78c8309fc82` Windows reference.
- Candidate: `e412348d1fa4ef0cfb90255eba67a923b4188e9a`, frontend tree
  `99a185f5f78352591730d2126bcb3eb678a7c60d`. Its only frontend changes since the
  second Linux candidate are exact-null guards in `useDashboardSelection.ts`,
  `ObservationControls.tsx`, `useHazardFilters.ts` and `useFiresFilters.ts`, plus
  three focused selection regressions. The four reviewed conflict-derivation
  files, source-map-js security lock repair and all dependency inputs remain.
- Before overlay or installation, the observer requires the exact clean candidate
  revision, frontend tree and eleven reviewed file hashes: the previous four
  conflict files and the seven selection files. The actual tree/file witness is
  retained as `candidateIdentity` in `inputs.json`. A wrong historical checkout or
  changed helper cannot be labelled as the new candidate.
- Both arms receive the candidate's identical `frontend/package.json` and
  `frontend/pnpm-lock.yaml`. This is a dependency-normalised historical baseline,
  not an unchanged historical whole checkout. The original baseline file map,
  explicit overlay and both resulting tracked frontend maps are retained.
- The original benchmark, stream fixture, Vitest configuration and npm settings
  are pinned. No test, scenario, assertion, source, limit or selection is removed.
- Node is exactly 24.19.0, with the official Linux x64 archive SHA256
  `14b342e71204f811bde6153be8e04b62aef63c236fef92b55f9c83154b409647`.
- pnpm is exactly 11.25.0, with published SHA512 integrity
  `XN6SW08HX3Jetx+64YpC/+eEUkeJ8ZthxzHLhyHsKKruFg4BqNWvT+2ypCzb8wDv4j2zVrDUoXtNY+EfirfJVg==`.

Public downloads are checksum-verified before extraction. Both frozen installs
finish before observation, using separate fresh homes, temporary directories and
package stores. No Actions cache is restored or erased. Installed package manifest
maps and pnpm resolution locks must match. This is not a claim that every installed
payload byte was independently compared. Source maps, inventories and Node/pnpm
entry hashes are checked after observation as well. No provider credentials,
repository credentials, proxies or inherited Node options enter child environments.

## Original measurement and bounds

Each arm uses the same exact command, with the pinned Node binary:

```text
node node_modules/vitest/vitest.mjs run src/features/globe/GlobePage.streamBenchmark.test.tsx --maxWorkers=1 --no-coverage
```

The original 5,000-event fixture and all four scenarios remain unchanged. There is
no warmup, coverage, added profiler, cache clearing, repeated arm or custom timing probe.
The original benchmark's React Profiler and its reported fields remain unchanged.
The original 120-second test deadline remains; each complete invocation has a
180-second process deadline and at most 15 seconds for owned-group cleanup.
Public package installation has a separate 600-second bound per arm. Preparation
and cleanup times are distinct from the benchmark's own scenario metrics.

The Linux helper uses a new process session, keeps its leader unreaped until group
cleanup, and signals only that group. This controls the known Node/Vitest process
tree, not an arbitrary program deliberately escaping its session. Any timeout,
failed test, malformed metrics, drift or uncertain cleanup stops the observation;
candidate does not run after a baseline failure. Original logs and exclusive
receipts remain. A hosted hard kill can prevent a final receipt, which is an
incomplete result, never success. The disposable job VM is the final isolation
boundary. No application servers, Docker resources or real provider calls are used.

`completed` means two valid tests, input readback and owned cleanup passed.
`candidateTargetsMet` separately tests every original median at most 20 ms and
maximum strictly below 50 ms. An unmet target does not turn a valid observation
into missing evidence. No threshold is embedded into the original unit test.

The usual covered/sharded frontend CI and coverage floors remain unchanged. Their
benchmark logs are correctness evidence, not this timing observation. This synthetic
jsdom fixture does not satisfy the separate real-browser trace criterion or prove
responsiveness on every device. No KAN-81 completion claim follows from one pair.

## Sources and validation

Runtime pins come from the [Node checksums](https://nodejs.org/dist/v24.19.0/SHASUMS256.txt)
and [pnpm package metadata](https://registry.npmjs.org/pnpm/11.25.0).
[Hosted runner documentation](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
explains the per-job VM boundary. Focused offline checks exercise failed-baseline
short-circuiting, raw metric validation, strict targets, environment isolation,
source pin refusal, dependency parity and process acknowledgement/cleanup. The
revised binding also tests workflow/ref agreement, candidate tree/content refusal
and rejection before any baseline overlay. Their
actual results must be recorded separately before authorising the one live job.
