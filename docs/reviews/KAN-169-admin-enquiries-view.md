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

Frontend runtime checks are deliberately pending the KAN-206 full-suite resource
reservation. Real-browser phone-width reflow and native-dialog focus checks,
coverage and repository CI remain outstanding. No test or
browser acceptance is claimed in this source milestone.

## Delivery

Depends on KAN-167's administrator API and KAN-166's opt-in enquiry storage.
Final KAN-182 session frontend and combined API generation must be integrated
before publication. This branch does not enable the feature, send enquiries,
change production, or grant release approval.
