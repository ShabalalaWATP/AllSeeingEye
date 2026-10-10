# Public route integration: CI follow-up

The final public route split at `9b472541` exposed three tests that acted before
the lazy application or sign-in shell mounted. PR #191's Vitest artefacts identify
`opsRoom.test.tsx`, `MotionToggle.test.tsx` and `reportAskEye.test.tsx`. The ops-room
failure was also reproduced locally: one failed and four passed in 15.40 seconds.

Each test now awaits its existing visible control before acting. The ops-room
case waits for primary navigation before sending its shortcut; the other cases
await the sign-in motion control and Ask Eye button. Original pointer exit,
account preference isolation and exact report-edition assertions remain intact.
No timeout, mock or production navigation behaviour changed.

The stylesheet invariant also identified 11 literal colour declarations in the
new public policy stylesheet. Its fixed palette now has nine named custom
properties, with all 11 uses retaining their exact original colours. Selectors,
layout and focus styling are unchanged. The existing invariant permits named
fixed palettes; no exception or weaker rule was added.

The broader shell group passed 38 cases in six files (39.57 seconds). The colour,
motion, report-assistant and public-policy group passed 19 cases in five files
(18.06 seconds). Scoped ESLint and Prettier checks and all 11 public-policy
tooling checks passed. Independent read-only review found no actionable issue.
These are focused groups, not a full-suite result. Final hosted CI is pending.

Publication approval remains absent. Changing the stylesheet changes the policy
content hash; the existing gate still requires actual approval of the exact
content and complete operator facts before publication.
