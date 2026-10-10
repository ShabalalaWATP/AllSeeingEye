# Public enquiry form

KAN-168 adds enquiries to the existing `/enterprise` story. It creates no account,
does not change approved deployment copy and adds no pricing. The generated
`EnquiryIn` contract is submitted to `POST /api/enquiries` through a dedicated
public API client with `auth: false`. A rejected request never starts session
refresh or automatic replay.

## Installation flags

| Product page | Enquiries | `/enterprise` |
| --- | --- | --- |
| Off | Off | Not-found view. |
| On | Off | Existing product story and account links, without the enquiry form. |
| Off | On | Existing product story with the enquiry form. |
| On | On | Existing product story with the enquiry form. |

The public site-facts request fails closed. The backend independently rejects
submissions when enquiries are disabled. A form that receives that response
removes its controls and explains that enquiries are unavailable.

The quiet sign-in link appears beside the desktop and mobile privacy links only
when enquiries are enabled. It targets `/enterprise#contact`; once the lazy,
configuration-gated story mounts, it scrolls to the contact chapter without
animation and focuses its heading. Sign-in form controls and tabs are unchanged.

## Form behaviour

- Name, work email, organisation, deployment interest and expected users are
  required. Role and message are optional. The message is bounded to 2,000
  characters and has an associated counter.
- The required privacy acknowledgement confirms that the notice was read. It is
  not marketing consent and is not added to the API DTO. The same-origin privacy
  notice opens in a labelled new tab so reading it does not discard the draft.
- Drafts live only in the mounted form. No draft enters local or session storage,
  URLs, analytics or account preferences. The draft clears after success and is
  discarded on navigation. The browser's own autofill remains available.
- The website honeypot is visually hidden, hidden from assistive technology and
  excluded from keyboard navigation. The backend decides how to handle it.
- Validation uses labelled controls and associated field errors. Submission
  feedback is announced and receives focus. Success is a fixed confirmation with
  no input echo. Throttling asks the visitor to try again later; other failures do
  not expose arbitrary server messages.
- Duplicate submission is blocked while a request is pending. Navigating away
  aborts the client request. An aborted or failed response does not prove that the
  server did not receive the enquiry; the client performs no automatic retry.

No third-party service, script, frame, dependency or CSP change is introduced.
The product import boundary continues to exclude account stores and app runtimes.

## Acceptance evidence

The source worktree starts at `c02bfdff` (KAN-172 metadata/import controls and the
KAN-166/167 API contract), with KAN-165 public documents (`3865e51a`) and KAN-182
session handling (`0e243da5`) integrated. Regenerating the merged API types produced
no difference. Publication remains subject to the legal/content approval gate;
implementation is not evidence of that approval.

After policy/session integration and the contact-navigation fix, using Node
24.19.0 and pnpm 11.25.0: frozen installation, TypeScript, full ESLint, production
build, formatting and file-length checks passed. The product import guard
traversed 74 source files; all 23 Node tooling/policy tests and all 20 Python
publication/crawler-policy tests passed. The product closure is 23,306 bytes gzip
against its 153,600-byte ceiling, initial JavaScript 209,151 bytes against 245,760
and the additional globe closure 810,682 bytes against 870,400. The integrated
KAN-184 preview-heading repair also passed focused ESLint.

The combined product, policy, public bootstrap, enquiry and style run passed 104
of 106 cases. Its two failures exposed a policy-page heading outside `PageHeader`
and duplicate header/footer navigation landmark names. Both were repaired in
`793524d8`; all 14 checks in the affected files then passed. Enquiry cases passed
for success, client/server validation, throttling, disabled admission, honeypot,
duplicate requests, abort, no public auth retry, draft disposal, accessibility and
all four flag combinations.

Local Chrome 155 browser checks used the compressed production build and a
loopback fixture that never stored or forwarded submitted bodies. The enquiry
form fit 390-pixel and 320-pixel viewports without horizontal page overflow.
The mobile sign-in link focused and scrolled to the contact heading. Empty
submission focused the announced errors; keyboard navigation skipped the
honeypot. Synthetic 429 and 202 responses produced the expected feedback, with
memory-only retention on throttling, no success echo and no browser storage.
Reload discarded the draft. Reduced motion, metadata restoration and same-origin
requests were also checked. Screenshots remain local in `output/playwright/`.

KAN-172 performance acceptance remains open: mobile Lighthouse scored 60 against
the target of 95; desktop scored 99. Both scored 97 for accessibility and 100 for
SEO. See [public product acceptance](PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md) for the
profile and limitations. No live enquiry or production release was performed.
