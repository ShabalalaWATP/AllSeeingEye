# KAN-234 MFA refresh regression

## CI evidence

PR #166 head `0187325d` failed the authentication coverage gate in
[job 114076971841](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38005774382/job/114076971841).
All four test shards passed: 884 files passed, one skipped, with 4,892 tests
passed and one skipped. The aggregate reported:

```text
FAIL features/auth/useTotpSettings.ts: branches 91.30% < 95%
```

The uploaded coverage artifact, ID `11652015185`, records 21 of 23 branches.
The uncovered paths were the MFA completion guard rejecting a changed session
generation and the subscription retaining state when the generation is unchanged.
Existing lifecycle tests already cover replacement-account and replacement-login
responses being rejected by the API client before MFA completion.

## Focused repair

Two parameterised hook regressions cover authenticator and email enrolment through
a real auth-store refresh with MSW responses. They verify that the same login keeps
its generation, pending enrolment or challenge, and entered code. Confirmation
then uses the rotated bearer token, sends the original proof, signs out and clears
the setup state. This covers the previously untested ordinary-refresh subscription
path. No production code, coverage threshold or test timeout changed.

## Validation

- Two test files, 17 tests passed in 16.62 seconds with one worker.
- Hook-only V8 coverage: 100% lines, statements and functions; 95.65% branches
  (22 of 23). The command explicitly required at least 95% branches.
- Strict ESLint, Prettier and application TypeScript checks passed.
- `git diff --check` passed. The touched test file is 212 lines.
- The coordinator independently reviewed the test-only diff and found no issue.

```text
pnpm exec vitest run --project dom src/features/auth/useTotpSettings.lifecycle.test.tsx src/features/auth/TotpSettingsPage.test.tsx --maxWorkers=1 --coverage --coverage.include=src/features/auth/useTotpSettings.ts --coverage.thresholds.branches=95 --coverage.reporter=text-summary --coverage.reporter=json-summary --coverage.reportsDirectory=../output/playwright/kan234-ci/focused-coverage
```

The full suite and combined authentication coverage gate were not rerun locally.
They remain CI checks after publication. Tests use synthetic accounts and MFA
proofs; no external provider or live authentication service was contacted.
