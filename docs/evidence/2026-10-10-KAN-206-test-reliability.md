# KAN-206: globe fixture and Brief navigation test reliability

The change is test-only, based on `d9bb9ac9` (KAN-222 and KAN-227).
Primary-checkout instructions in `AGENTS.md`, `CLAUDE.md`,
`docs/DEVELOPMENT_WORKFLOW.md` and `docs/PARALLEL_DEVELOPMENT.md` were read
without changing them. Dependencies and runtime outputs stayed in this
ticket's isolated worktree. Checks used Node 24 and at most two Vitest workers.

## Diagnosis and repairs

PR 168, run `38000496098`, job `114057114544`, contained two distinct signals:

- The passing globe performance test supplied only longitude and latitude to
  the cluster click handler. Production cluster picking also requires the
  cluster identity and metadata. The test asserted camera movement but missed
  the route error caused by `undefined.startsWith` in `useMapPicking.ts`.
  Adding an inspector-survival assertion reproduced the failure before the
  fix. The test now clicks a real cluster from the layer's generated data and
  checks that the inspector remains visible with the expected item count.
- The failing KAN-222 navigation test queried the outgoing Brief editor after
  save, while the route was remounting the saved revision. Both this test and
  the existing Brief workspace save test now wait for the outgoing editor's
  removal before querying the replacement. No production guard was changed.

`BriefRemount.stress.test.tsx` executes 30 consecutive scenarios. Each holds the
saved-revision response until the original editor unmounts, then checks the
replacement identity, focus, clean unload state, dirty-navigation cancellation,
cancelled edits and exact-revision run request. It uses synthetic MSW responses
and explicit state transitions, with no sleeps or live provider requests.

## Validation

The new globe assertion failed before the fixture repair: 1 failed and 18
passed tests across the three existing affected files. After the repair, the
same files plus the new stress file passed: 4 files, 49 tests, 77.82 seconds.

One serialised full-suite coverage run included all 30 stress scenarios:

```text
pnpm exec vitest run --coverage --maxWorkers=2 --reporter=default --reporter=json --outputFile.json=coverage/kan-206-results.json
```

It completed in 2,159.90 seconds with **879 passed, 2 failed and 1 skipped files**
and **4,840 passed, 2 failed and 1 skipped tests**. All 49 tests in the four
original changed files passed, including the 30 stress scenarios and the
previously failing KAN-222 save test. This was one full-suite execution with
30 scenario iterations, not 30 separate entire-suite executions.

| Coverage   | Result | Existing threshold |
| ---------- | ------ | ------------------ |
| Statements | 96.35% | 90%                |
| Branches   | 92.32% | 90%                |
| Functions  | 94.86% | 90%                |
| Lines      | 97.50% | 90%                |

The two full-suite failures were investigated before any rerun:

- The categorical-text-colour source scan in `labelContrast.test.tsx` timed
  out at its 15-second test limit while reading the full production source
  tree under coverage on Windows. Its unchanged assertion now has a bounded
  30-second allowance for this filesystem work. Global timeouts and coverage
  thresholds are unchanged.
- The tracker assessment flow failed while waiting for the generated-report
  form, before its scope or submission assertions. Its setup preloaded the
  tracker route modules but left the destination research and report chunks
  cold. Setup now also preloads those destination modules, through the shared
  `researchRoutes` test helper to preserve feature boundaries. Existing form,
  scope, submission and query-timeout assertions are unchanged.

The targeted follow-up command passed all 16 tests in 2 files, in 15.11 seconds:

```text
pnpm exec vitest run src/features/trackers/trackers.test.tsx src/styles/labelContrast.test.tsx --maxWorkers=2
```

This follow-up ran before extracting the identical destination imports into
the shared helper. The full suite was not rerun after the two follow-up repairs;
a clean full-suite result remains for CI verification. Coverage figures above
belong to the recorded full run, which exited with two test failures.

The complete frontend lint command passed for the original four-file repair.
Final changed-file ESLint, Prettier and TypeScript checks passed for the follow-up
repairs and shared helper. `git diff --check` passed, and every changed source
file remains below 350 lines. Independent parent code and security review covered
the fixture contract, editor remount sequencing and bounded timing repairs.
The change adds no production behaviour, persistent state or security boundary.
