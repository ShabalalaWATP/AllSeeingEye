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
diagnostic were corrected. Final TypeScript and focused ESLint pass, including
the review repairs. The production build and existing bundle budgets pass
(initial JavaScript 204,839 bytes gzip; additional globe route 808,167 bytes).

All 31 focused tests passed across the enquiry workspace, public site facts,
administration navigation, shell and navigation configuration. The new mobile
case initially used the research navigation labels; it now asserts the actual
administration trigger and dialog labels. Real-browser phone-width reflow,
native-dialog focus, scoped coverage and repository CI remain outstanding.

## Delivery

Depends on KAN-167's administrator API and KAN-166's opt-in enquiry storage.
Final KAN-182 session frontend is integrated and included in the focused run.
Combined API generation remains required before publication.
This branch does not enable the feature, send enquiries,
change production, or grant release approval.
