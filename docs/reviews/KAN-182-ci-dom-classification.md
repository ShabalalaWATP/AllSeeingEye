# KAN-182: browser-session test classification

Frontend shard 1 failed on both dependent PRs with the same two test errors:

- [PR 183 job 114075363484](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38006171526/job/114075363484)
- [PR 184 job 114076185567](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38006433588/job/114076185567)

The shard jobs use Vitest's blob reporter. Their `frontend-blob-1` artifacts were
downloaded into private ignored output directories and decoded as data. Each
report contains the same failures in `cyberFilters.unit.test.ts`, with no
unhandled errors. Both fail at `applySession`, through `auth.setSession` and
`readCookie`, with `ReferenceError: document is not defined`.

KAN-182 captures the browser CSRF cookie when establishing session authority.
These tests exercise real authentication-store transitions and therefore need
the browser environment. The `.unit.test.ts` suffix selected the Node-only
project, which supplies neither a document nor the standard session cleanup.

The repair renames the file to `cyberFilters.test.ts`, selecting the existing
jsdom project and its cookie/store cleanup. Both original behaviour tests are
retained. An additional regression establishes two cookie-backed accounts in
sequence and checks that replacing the account clears private Cyber selections
and filters while capturing the new cookie authority.

No production code, test-runner configuration, coverage threshold or timeout is
changed. The CI failures provide the failing baseline; this is a classification
repair, not a retry of a timing failure. The source remains covered by the same
whole-frontend coverage policy.

## Validation

- ESLint and Prettier pass for the renamed test file.
- The application TypeScript check and `git diff --check` pass.
- Independent review confirmed the classification and cookie-backed regression,
  including the standard DOM fixture's session and cookie cleanup.
- The reserved focused run passed: two files and ten tests in 5.47 seconds with
  one worker. Command, from `frontend` with Node 24:

  ```text
  pnpm exec vitest run --project dom src/stores/cyberFilters.test.ts src/stores/auth.activityBoundaries.test.ts --maxWorkers=1 --reporter=verbose
  ```

  Vite printed its existing future-native-config-loader advisory; the run passed.
  No browser, full frontend suite or local coverage run was performed for this
  test-only repair. Full shard and dependent-PR confirmation require subsequent CI.
