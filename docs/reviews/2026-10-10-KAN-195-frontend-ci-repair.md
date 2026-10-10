# KAN-195 frontend CI follow-up

The source-policy gate waits for the installation's capabilities before admitting
map sources. Existing infrastructure and Ukraine map tests assumed immediate
admission, so several toggles did nothing and renderer assertions ran before the
map could mount. The military index also correctly withheld country references
until the policy response arrived. Production admission behaviour is unchanged.

The affected tests now use a complete synthetic signed-in session and wait for
the relevant source to be admitted, or for the corresponding control to become
enabled. They retain the original assertions for lazy loading, request abortion,
late response rejection, access changes, selection, attribution and rendering.
Military badges remain off before and after admission; the Ukraine renderer must
not mount while policy is pending. Separate denied-policy tests remain intact.

The Evidence basemap selector now uses the existing `border-control-border`
token, matching the shared form fields and the established contrast gate.

## Evidence

- Starting revision: `8e818074200e2ceb49c9f0520e0e0f17b36601e8` in the isolated
  `codex/KAN-195-commercial-source-policy` checkout.
- Before edits: all 12 reported failures reproduced across seven files, with
  36 tests passing and 48 total. Eleven failures concerned policy readiness; the
  remaining readability failure identified the selector's divider border.
- After the focused changes: 55 tests passed across ten files with two workers.
  This includes the seven failing files, `infrastructurePolicy.test.tsx`,
  `sourcePolicy.test.ts` and `MapFilters.interactions.test.tsx`.
- Independent source review found no remaining issue in the seven-file repair.
- Scoped ESLint and Prettier checks passed, as did the full frontend TypeScript
  checks and production Vite build. Every changed source file is below 350 lines.
- Bundle checks passed: initial JavaScript was 204,310 bytes gzip against a
  245,760-byte budget; additional globe JavaScript was 809,643 bytes gzip against
  an 870,400-byte budget.
- All requests used existing local MSW responses or mocked transports. No backend,
  database, provider traffic or production configuration was used.

Coverage was not measured in this run and thresholds were not changed. This
bounded run does not replace the full
frontend suite or PR CI. No provider permission or commercial release approval is
inferred from these checks.
