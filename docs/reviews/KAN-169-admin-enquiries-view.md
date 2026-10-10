# KAN-169: administrator enquiry workspace

The new `/admin/enquiries` route reuses the authenticated, active-administrator
guards and separate administration shell. Its navigation entry and content require
the public enquiry feature flag. The research navigation remains unchanged.

The generated API client requests one status and 25 records at a time. The server
orders, filters and counts records before pagination. Each card shows the contact,
organisation, deployment interest, expected users and received date. Messages are
expandable React text. Email copying, status changes and confirmed permanent
deletion use the existing accessible controls.

Each keyed result page owns and aborts its requests. Late responses cannot replace
another filter or page. The shared API client also binds responses to the original
login generation. A stable workspace owns success messages and the results focus
target, including when deleting the final result moves back a page. Focus is moved
after the previous native modal closes.

## Review and validation

An independent read-only review identified lost pagination focus and last-page
mutation feedback. Both were repaired, including the native-dialog inertness edge.
Prepared Vitest/MSW cases cover listing, literal markup, copying, filtering,
pagination, status changes, confirmation/cancellation, errors, feature and role
gates, late responses, last-page deletion, axe semantics and mobile navigation.

Initial TypeScript errors in test query options and the asynchronous-load lint
diagnostic were corrected. After the final reflow repairs and dependency merge,
TypeScript, focused ESLint, Prettier, the production build and existing bundle
budgets pass (initial JavaScript 207,872 bytes gzip against 245,760; additional
globe route 808,036 bytes against 870,400). The file-length check and
`git diff --check` pass; existing length warnings concern untouched files.

All 31 initial focused tests passed across the enquiry workspace, public site
facts, administration navigation, shell and navigation configuration. The mobile
case initially used the research navigation labels; it now asserts the actual
administration trigger and dialog labels.

On 10 October, the final enquiry-only run passed all 17 tests in two files with
two workers, after integrating KAN-182's final test classification fix. Five
additional lifecycle cases cover applicable actions, closing contacted records,
missing optional fields, malformed-response recovery, late mutation success and
failure after changing filter, and backwards pagination focus. Scoped V8 coverage
of the page, hook, card and API client is 97.82% statements (90/92), 94.64% branches
(53/56), 100% functions (22/22) and 100% lines (84/84). The existing 90% gates were
not changed. The hook alone has 86.36% branch coverage; the three uncovered guards
concern aborted-success and duplicate-action paths. This is scoped coverage, not
the complete frontend suite.

## Local browser verification

A fresh named Playwright CLI session used the actual routes and administration
shell through a private Vite server on loopback port 5489. Interception was
installed before navigation: every API response was synthetic and every off-origin
destination was blocked. No backend, operator database or real enquiry was used.
The fixture supplied 26 records, including long unbroken contact, organisation,
email and message strings and a final-page singleton.

- At 360 by 800, the first assertion exposed clipped contact details: the implicit
  grid column grew to 792 pixels inside a 279-pixel content area. The confirmation
  dialog also had 1,029 pixels of scrollable width inside 320 pixels. Explicitly
  declaring the mobile grid column and wrapping the confirmation paragraph fixes
  both. The same assertion then found no overflowing card/dialog children. The
  document width remained 360 pixels; 1280 by 900 also passed.
  Independent source review approved these two class changes after inspecting
  the recorded red/green geometry and native focus evidence.
- Native modal Cancel receives initial focus. Escape and keyboard Cancel return
  focus to Delete. Keyboard confirmation of the final result on page two issues
  exactly one synthetic DELETE, returns to page one, preserves the success notice
  and focuses the stable Enquiry results heading after the modal closes.
- Keyboard traversal selected Users, then Enquiries, in the mobile administration
  menu. The menu closed and the Enquiries h1 received focus. No research navigation
  appeared in that menu.
- Expanded message markup remains literal text. Phone and desktop screenshots were
  inspected. Axe reported no WCAG 2 A/AA, 2.1 AA or 2.2 AA violations in either
  view. Phone checks had no incomplete results; desktop colour contrast requires
  manual review because axe marked it incomplete. These checks do not constitute
  a complete WCAG conformance assessment.
- Two initially unhandled synthetic Users-page research-usage requests were
  aborted by the harness and then given a local fixture. No off-origin request
  occurred, and no API request reached a server.

Ignored local evidence lives in `output/playwright/kan-169/`: the interception and
reflow scripts, red/green geometry, focus and network records, axe results and
screenshots. The browser and server were closed before releasing the runtime lane.

## Delivery

Depends on KAN-167's administrator API and KAN-166's opt-in enquiry storage.
Final KAN-182 session frontend and follow-up `2732ff9f` are integrated and included
in the final focused run. Repository CI and final cross-branch API reconciliation
remain the orchestrator's publication checks.
This branch does not enable the feature, send enquiries,
change production, or grant release approval.
