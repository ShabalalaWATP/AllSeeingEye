# Continuous browser regressions

KAN-231 adds a bounded Chromium lane against the production frontend build.
It supplements the existing Vitest, backend, coverage, contract, bundle and
security gates. The existing frontend aggregate also requires the browser job.

## Journeys

| Journey              | Observable regression boundary                                                                                                                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity transition  | Logout removes a private draft immediately. Replacement sign-in waits for the pending logout response, retains its own cookie, and survives refresh.                                                                |
| Dirty Research Brief | The native confirmation dialog preserves cancelled edits, permits explicit departure, and history navigation cannot recover discarded private input.                                                                |
| Frozen edition       | Subscription history links version 1 while version 2 exists. Navigation, reload and Back retain the chosen version and its distinct finding.                                                                        |
| Notifications        | An acknowledgement remains pending until the synthetic server confirms the exact alert. The count, focus and item then update. Opening another alert separately checks its destination and does not acknowledge it. |

The tests use normal sign-in, links, buttons and browser history. They do not
inject authentication stores, stub React components or replace native dialogs.
Generated contract types and existing pure data fixtures constrain the synthetic
responses. Assertions cover browser/client behaviour, not backend authentication,
provider delivery, Web Push, live research or measured model accuracy.

## Isolation and determinism

- Each test has a fresh browser context, cookies and profile. Browser binaries
  live inside this worktree's ignored dependency installation.
- The preview server binds only `127.0.0.1:41731`, refuses a busy port and is owned
  and stopped by Playwright. It serves the build with a separate configuration
  that has no API proxy. No backend, database or provider service is started.
- Browser-context routing provides every API response. Unknown APIs, incorrect
  fixture account authority, unexpected external requests and WebSockets fail the test.
  Service workers are blocked so they cannot bypass interception.
- The identity journey briefly enters the normal globe home. Its exact OpenFreeMap
  style URL receives an empty synthetic style, and the known EOX raster tile path
  is always aborted and recorded. No provider receives a browser request.
- The browser clock has a fixed date while timers still run. Waits use UI
  conditions or explicit response barriers; there are no fixed sleeps or
  `networkidle` assumptions. Deferred responses are released during cleanup.
- One Chromium worker runs the lane, with no retries, a 30-second test limit and
  a three-minute suite limit. The CI job has a ten-minute ceiling including
  dependency/browser installation and the production build.

## Local commands

From an isolated `frontend` directory with the repository's supported Node and
pnpm versions:

```text
pnpm install --frozen-lockfile
pnpm test:browser:install
pnpm build:ci
pnpm test:browser
```

On Linux, install browser system dependencies with
`pnpm test:browser:install --with-deps`. Coordinate runtime reservations before
running alongside large frontend suites. Reserve port 41731; do not reuse another
process or point these fixtures at a deployed installation.

Playwright retains failure traces and screenshots under `output/playwright/`,
which is ignored by Git. The HTML/JSON reports and synthetic API request inventory
include test timing and the exact failed step. CI uploads this directory for
seven days, including on failure. The data and unsigned continuity tokens are
synthetic; do not replace them with real account data or credentials.

## Evidence and limits

On 10 October 2026, the final local production-build run passed all four journeys
in **11.354 seconds**, using one Chromium worker and no retries or skipped tests:

| Journey              | Test duration |
| -------------------- | ------------: |
| Dirty Research Brief |       2.220 s |
| Frozen edition       |       1.876 s |
| Identity transition  |       2.465 s |
| Notifications        |       1.126 s |

The remaining suite time includes runner/browser setup and teardown. These are
local observations, not a CI performance guarantee. The preview listener and
private browser processes were absent after completion.

The browser regression exposed a real notification obstruction: the top bar's
backdrop filter created a stacking context behind positioned report content.
The header now has an explicit stacking level. Acknowledgement also exposed a
zero-delay focus timer running before React removed the focused row. Focus now
follows the DOM commit; rule muting requests that restoration after its deferred
refresh removes rows. Native modal dialogs retain their top-layer priority.

The notification click failure was reproduced after correcting supporting API
fixtures. A separate deterministic mute regression failed with focus on the body
before the callback ordering fix. The final four-file notification group passed
19 tests. TypeScript, typed ESLint, formatting, production build, bundle budgets,
file-length checks, frozen offline installation and dependency audit passed.
The dependency audit reported no advisories. Coverage was not remeasured locally;
the existing required coverage gates remain unchanged.

The workflow writes elapsed browser seconds to its job summary and preserves the
JSON reporter's per-test durations. Representative validation passed on
[PR #190's browser job](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38008488527/job/114082737780)
at `7c913b7be333d42bd4f87cc26bfedf54030f022c` on 10 October 2026. All four tests
passed in 9.9 seconds without retries or skips. The complete hosted job took
64 seconds, from 00:23:01 to 00:24:05 UTC, including dependency/browser installation
and the production build. The remaining workflow gates and final combined branch
still require their own results; this is one observed run, not a runtime guarantee.

[KAN-81's completed manual browser acceptance](reviews/2026-10-06-KAN-81-browser-acceptance.md)
remains historical evidence. This lane does not reopen that work, replace its
real map/rendering observation, or make a new performance claim.

The development dependency is exactly pinned to Microsoft Playwright 1.64.0.
The setup follows the official [installation](https://playwright.dev/docs/intro),
[API mocking](https://playwright.dev/docs/mock),
[managed web server](https://playwright.dev/docs/test-webserver) and
[CI](https://playwright.dev/docs/ci-intro) guidance. Package metadata and the
Microsoft repository origin were checked before adding the dependency.
