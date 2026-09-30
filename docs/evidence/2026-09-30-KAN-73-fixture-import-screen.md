# KAN-73: remove incidental browser imports from Node tests

Two existing Node tests loaded browser infrastructure to obtain small helpers:

- `aiUsagePresentation.unit.test.ts` imported `team` from `fixtures.teams.ts`,
  which also imported Testing Library, user-event, MSW, the server and TeamsPage.
- `cyberFilters.unit.test.ts` imported `applySession` from `render.tsx`, which
  also imported Testing Library, user-event and the application's route table.

Team data now lives in `fixtures.teamData.ts`, and session setup lives in
`session.ts`. The old modules re-export their existing interfaces for DOM
consumers. The two Node tests import the focused helpers directly. Fixture
values, helper behaviour, assertions and production source are unchanged.

The investigation found no redundant project-level browser setup to remove.
The resolved Node project has no setup files. Vitest 5 shares the Vite server
between these inline projects, lazily imports jsdom only for that environment,
and disables module prewarming for its built-in Node environment. The V8
provider deliberately disables Node's compile cache to preserve precise source
positions, so that setting was preserved too.

## Correctness checks

Both TypeScript configurations, targeted ESLint, Prettier and whitespace checks
passed. The first Windows test run passed 41 of 42 cases, but LoginPage's
authenticated-route case exceeded its unchanged 15-second timeout while
TypeScript was running concurrently. That failure was retained in the report.

On the isolated Linux runtime, the unchanged frozen LoginPage baseline passed
all 10 cases. The candidate then passed all 42 cases across LoginPage, both
TeamsPage suites and the two affected Node test files. No timeout or reset
behaviour was changed.

## Controlled unit-project screen

The baseline is `c76d944087df1f45396b0f3104478e9a06cab55b`. The candidate differs
only in the six test/helper files described above. Both arms used the same
frozen lockfile, original configuration, Node 24.21.0 image, two-CPU and 6 GiB
container limits, two workers, process isolation and mock restoration/clearing.
The same five fixture cases warmed each arm. The fixed empty Vitest cache state
was restored after warm-up, followed by a ten-second cooldown. All 4,947 baseline
source files, and the candidate's two additional helper files, were hash-checked.

| Arm | UTC start | Wall seconds | Test outcomes |
| --- | --- | ---: | --- |
| Baseline | 2026-09-30 11:56:21.891284 | 31.4753 | 796 passed, one existing skip |
| Candidate | 2026-09-30 11:57:08.602010 | 30.2378 | 796 passed, one existing skip |

Both arms selected 113 files, with identical case identities and outcomes.
The observed saving is **1.2375 seconds**. This bounded result does not establish
the required 70-second whole-suite saving or justify adding it arithmetically
to a previous whole-suite result.

Both commands exited 1 because this unit-only subset does not meet the unchanged
global coverage floors. There were no failed test cases. Coverage denominators
were identical across all 1,038 reported production modules. Incidental import
execution disappeared from 55 files: covered lines fell from 3,527 to 3,328,
statements from 3,976 to 3,775, functions from 830 to 817, and branches from
3,324 to 3,318. The six branches are in the route table, preferences and profile
initialisation. Both directly tested production modules retained exactly the
same covered locations, including all 41 combined branches.

Fresh whole-suite coverage is still needed to establish aggregate equivalence.
KAN-73's most recent valid whole-suite saving remains 63.8143 seconds, below the
70-second criterion. No full suite was repeated for this small candidate.

Raw logs, source hashes, scripts, test identities and LCOV reports are kept
outside Git under
`C:/Users/alexo/.codex/worktrees/kan73-node-expansion/helper-screening/`.
The owned benchmark container was restored to the frozen baseline, verified and
stopped after the screen. Earlier benchmark evidence was preserved.

## Fresh full-suite coverage check

The frontend shard/coverage jobs pass in CI run `36712872629` at `83bbc802`.
Combined branches remain 20,266/21,988 (92.16%); lines are 19,981/20,538,
statements 22,461/23,357 and functions 7,323/7,765. No file with at least 20
branches falls below 70%, and the reviewed auth floors pass. Independent LCOV
totals match JSON across 1,038 modules. The LCOV SHA-256 is
`98b6f9256153223672dc32b3a931d931073a76b4ff42e8ea182cb0e9168ef397`.

Against the frozen unsharded pair, covered counts and line/statement/branch
denominators match. The function denominator is one lower, changing its exact
percentage by +0.012144 points. All four deltas remain within the 0.05-point
criterion. This establishes fresh aggregate coverage after helper extraction;
it does not supply a new controlled whole-suite timing pair. The overall CI run
failed backend fixture cases, so it is not a complete green checkpoint.
