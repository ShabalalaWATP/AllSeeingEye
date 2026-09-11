# Research workspace security review

Date: 11 September 2026. Scope: multi-country/history selection, native web
discovery, private photo geolocation, recurring research and their UI/API wiring.
This records a manual scoped review and deterministic regressions, not a complete
repository scan, provider security assessment or public-deployment approval.

## Reviewed boundaries

- Country lists are bounded and validated before collection. Legacy scalar scope
  must agree with plural scope. Malformed or unsupported scope cannot become a
  worldwide query. Follow-ups preserve countries and fixed dates.
- Photo access checks the input owner, active request session and destination
  membership before and after external work. Administrators do not inherit access
  to another account's temporary upload. Deletion only follows same-owner receipt
  lineage and cannot remove saved reports.
- The vision request contains a fixed-format sanitised PNG preview and explicit
  user context, without original filename, EXIF or extracted OCR. Input consent,
  byte bounds, expiry, concurrency and deadlines are enforced. Output candidates
  and coordinates remain unverified, with unknown an accepted result.
- Browser receipt cleanup retains only bounded identifiers and expiry metadata.
  Account/access changes clear references. Replacement and reanalysis discard
  obsolete receipts; pending report holds protect input until a request settles.
  Unmounting does not race a report by deleting its input.
- Fresh web discovery requires opt-in and the intended destination's immutable
  supported OpenAI profile. Its credential is confined to the official origin;
  redirects, oversized/compressed responses and provider error-body disclosure
  are rejected. No cross-team or alternate-provider fallback is introduced.
- Private document/media contents cannot enter public web discovery. Source
  admission is checked before dispatch and after completion. Required native
  tool execution, independent budgets and transport cancellation are covered.
- Generated web context remains outside E-labelled evidence and corroboration
  scoring. Citation offsets and URLs are bounded; the frontend renders React text
  and safe links rather than provider HTML. Citation URLs do not grant server fetch
  permission or establish the truth of a claim.
- Native-search usage has a single isolated persistence writer. A bounded shield
  protects only its database write during cancellation. Uncertain commits are not
  retried through final report saving, avoiding duplicate accounting.
- Recurring runs retain active-owner/team authorisation, saved source/country
  options and stale-snapshot rejection. Private expiring inputs cannot recur.
  Administration remains a separate guarded route tree.

## Review results and limits

Independent correctness/security review found no outstanding confirmed finding
after the photo receipt lifecycle, recurring subject validation and web-usage
accounting fixes. Its final targeted recheck passed 36 tests across those paths.
The combined backend integration selection passed 196 tests, including ownership,
session expiry, cancellation, input lineage, web transport/usage, country/date
scope and monthly scheduling. The final workspace checklist records broader
static and frontend results.

Native parsers retain the existing service-user filesystem/network boundary; the
upload worker is not a full operating-system sandbox. Rate limits assume one API
worker. A database failure during cancelled web work can leave final usage
unavailable. `store: false` does not guarantee zero provider retention. No new
dependency, database migration or production deployment was introduced.

Actual model quality remains unmeasured: the saved local OpenAI profile is disabled
and its credential cannot be decrypted without the original server encryption key.
Known-location photo and native web-search evaluation must follow restoration of a
working connection. Software fixtures cannot establish geographical accuracy,
complete historical coverage, citation truth or the selected model's capabilities.
