# KAN-73 controlled frontend comparison

The predeclared full-suite pair at `38d3ff677d57fb8bfcdb3b6ab42f3d6d4081606c`
saved **88.0644 seconds**, meeting the required 70 seconds. Both phases passed
4,394 cases with one skipped case, across 821 passing files and one skipped file.
Exact test identities, outcomes and counts matched. The earlier 63.8143-second
result remains a valid failed measurement for its earlier source revision.

| Phase        | UTC start on 2 October 2026 |  Wall seconds |
| ------------ | --------------------------- | ------------: |
| DOM baseline | 09:10:12.878195             | 1,186.0590225 |
| Node project | 09:30:38.134684             | 1,097.9945845 |

The same frozen full-repository archive and private frozen dependencies ran in
the same Docker container, capped at two CPUs, 6 GiB and two Vitest workers.
Node was 24.21.0 and pnpm was 11.25.0. The image was
`node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1`.
The baseline changed only the unit project's environment, jsdom URL and setup
file. Pool, per-file isolation, reset hooks, source, cases, exclusions and
thresholds stayed identical. The Node phase used the committed configuration.

Each phase warmed the same five infrastructure cases, then restored the same
empty Vite/Vitest cache roots captured before any tests, followed by a ten-second
cooldown. Filesystem module caching was disabled. Source and installed lock
hashes were verified before and after each phase. Other local heavy checks were
held; the separately authorised native 24-hour audit continued periodic light
HTTP requests. This is one complete matched pair, with no selected reruns.

| Coverage   | DOM covered / total | Node covered / total | Change, percentage points |
| ---------- | ------------------: | -------------------: | ------------------------: |
| Lines      |     23,467 / 24,102 |      23,467 / 24,102 |                         0 |
| Statements |     26,438 / 27,478 |      26,438 / 27,478 |                         0 |
| Branches   |     23,225 / 25,205 |      23,225 / 25,205 |                         0 |
| Functions  |       8,678 / 9,169 |        8,679 / 9,169 |                +0.0109063 |

All coverage differences are within the required 0.05 percentage points. Node
branch coverage is 92.14%. The unchanged frontend auth 95% and global branch
92%/eligible-file 70% checks separately passed on the complete Node report.
The owned container was stopped after preserving the evidence.

Reproduction inputs and raw evidence are outside Git at
`C:/Users/alexo/.codex/scratch/kan71-73-followup-58c5b2fe/frontend-screen/`:

- `manifest.json`, `installation.json`, `tracked-file-sha256.json` and both
  `vitest.benchmark-*.config.ts` files identify the exact inputs.
- `run-phase.py` records each warm-up, restored cache, cooldown and full coverage
  command. `dom-result.json` and `node-result.json` contain timestamps and exits.
- `dom-tests.json`, `node-tests.json`, both logs and both `coverage-*/` directories
  retain test outcomes, JSON coverage and LCOV. `compare.py` produced
  `paired-result.json`, checking identities, hashes, counts, time and coverage.
- Archive SHA-256:
  `dc7862c1ff9ea655962685843bfcd070abc35663997c16e2b991eae4bfabd3c9`.
- Lock SHA-256:
  `7e23bffc5aedab515a89752d4a911db7fe38be83ce2456f812d5add1f40c01f6`.
- Fixed cache-state SHA-256:
  `4586d769eff0c51b723397663430aa9dd3955c3648f44679054a19308a35f097`.

The implementation comprises eleven further headless test moves, including two
pure fixture extractions with compatible MSW re-exports. Assertions and production
source are unchanged. Focused tests, both TypeScript configurations, lint and
format checks passed before timing; independent quality and security reviews
found no actionable issues. Fresh integration CI remains required. This frontend
result makes no claim about KAN-71's separate PostgreSQL runner-minute target.
