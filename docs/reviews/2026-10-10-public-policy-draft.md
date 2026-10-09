# Public policy draft milestone, KAN-165

Prepared in an isolated worktree from `00df4b01`, including the enquiry API and
retention setting, embed consent controls and source licence register. Public
privacy, storage, attribution and request-procedure routes render structured text.
No controller identity, processor details, lawful basis or legal approval was invented.

The approved KAN-23 operator-assisted contact is reused specifically for requests.
The broader notice retains explicit unconfirmed decisions. Source credits include
both primary and additional policies for every catalogue identity. These credits
do not declare providers commercially cleared or reveal deployment enablement.

## Completed evidence

- The missing publication-check module failed its initial regression. A separate
  deployment regression then proved the approval gate was absent before wiring it.
- Eleven Node checks cover declarations, new storage keys/cookies, attribution
  completeness, unknown rights, approval invalidation and preview invalidation.
- Eight Python publication regressions pass. They cover placeholders, malformed
  approval, stale content, invalid dates, exact Git blobs, symlink rejection and
  actual Node/Python content-hash parity. The gate stops before images or backups.
- Existing deployment checks: 41 cases pass, with one existing platform skip.
- Changed publication helper coverage is 92% including branches, above the unchanged
  90% gate. No production controller, database or external provider was used.
- Frontend type checking and production build pass. Bundle budgets pass: initial
  JavaScript 205,358/245,760 gzip bytes; globe route 810,804/870,400.
- Scoped Ruff, Python formatting, Bandit, Prettier and whitespace checks pass.
- Full frontend lint passes, including the existing eight infrastructure tests;
  the eleven added policy checks also pass and are included in the lint command.
  Source-length checking reports existing unrelated warnings only. The touched
  deployment controller remains at 349 lines; new handwritten modules are smaller.
- Independent source review found incorrect enquiry inventory and stale approval
  display. Both were corrected and re-reviewed. Strict date checking and cross-runtime
  hash parity were added; the reviewer reported no further actionable finding.
- `pnpm check:publication` fails deliberately for the missing operator decisions
  and absent approval. This is a release block, not a bypassed quality check.

## Outstanding acceptance

Frontend UI runtime tests, route accessibility execution and browser request capture
have not run because KAN-206 reserves the shared test runtime. Supplied tests cover
anonymous routes, declared storage, live/unavailable retention, keyboard links,
navigation focus and structural accessibility; their presence is not pass evidence.
The coordinator owns execution and integration with KAN-172's public bootstrap and
metadata changes before claiming the whole-App network boundary is verified.

No full frontend coverage or WCAG conformance claim is made here.

Actual legal approval, installation facts, deployment-controller installation and
release remain pending. The operator must review the concrete draft using
[publication instructions](../PUBLIC_POLICY_PUBLICATION.md). Nothing was pushed,
merged, installed on the host or deployed by this milestone.
