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
against its 153,600-byte ceiling, initial JavaScript 209,134 bytes against 245,760
and the additional globe closure 810,693 bytes against 870,400. The integrated
KAN-184 preview-heading repair also passed focused ESLint.

Prepared Vitest/MSW cases cover success, client and server validation, throttling,
admission being disabled, the honeypot, duplicate requests, abort, no public auth
retry, draft disposal, accessibility and all four flag combinations. Runtime tests
and browser checks are queued behind the shared frontend reservation. No browser
score, screenshot, live submission or production release is claimed here.

The final combined KAN-165/168/172 acceptance run must measure phone-width reflow,
keyboard and focus behaviour, enabled-only sign-in links, network origins, the
production route budget and the Lighthouse targets recorded in
[public product acceptance](PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md).
