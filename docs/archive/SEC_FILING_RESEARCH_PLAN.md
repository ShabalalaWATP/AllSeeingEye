# SEC filing research

Status: implemented and locally checked in an isolated branch. Independent review
and integration with the source-provenance branch remain pending.

## Sources and access

The SEC provides unauthenticated submissions JSON, including references to older
submission files. The application uses these documented resources and exact
primary documents selected from their metadata. It does not discover arbitrary
web pages or follow links embedded in filing HTML.

Official references, checked 8 September 2026:

- [EDGAR application programming interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- [Accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).

No SEC account or API key is required. The operator must configure their real
contact email in `ASE_FEEDS_CONTACT`. The application's placeholder contact is
rejected before any SEC request. Free access is subject to SEC access policy;
availability is not guaranteed. No live filing requests were made during local
acceptance. Network behaviour is tested with owned synthetic responses.

One shared SEC client paces ticker-directory, submissions and document requests
at least 250 milliseconds apart, below the SEC's stated ten requests per second
maximum. Multiple application processes or deployments must share an external
egress rate limit to respect the aggregate upstream limit. Each resource uses
the existing public-address validation and DNS pinning, byte limits and no
redirects. Authentication credentials and private research questions are never
sent to the SEC.

## Automatic collection

An explicit CIK company query retains the existing metadata collector. It reads
recent submissions and at most three matching older files declared in the
issuer's response. The overall collection deadline is twenty seconds, with no
retry and at most twenty returned records. Date filtering uses the SEC filing
day. Older manifests are bounded to 1,000 inspected descriptors and fifty
matching files. Receipts disclose partial history, failed pages and limits.

Accession numbers are validated independently of issuer CIK: an accession prefix
can identify a filing agent. Index metadata remains metadata. A filing's presence
in EDGAR does not independently verify its underlying assertions.

## Explicit selected-document workflow

1. The authenticated operator opens the SEC picker in document research and
   supplies a numeric CIK and inclusive filing-date interval.
2. The server retrieves recent metadata or a validated older submission file.
   The picker displays the company, form, accession and filing day separately
   from document content.
3. Selecting Import supplies only an opaque server-issued selection UUID.
   CIK, accession and primary filename are resolved from the session-owned
   selection. The client cannot provide a URL or override the document identity.
4. Before fetching, the service reserves both an original-byte slot and an
   existing private research-input slot. It retrieves one exact HTML/TXT primary
   document and extracts inert text. Unsupported content fails explicitly.
5. The resulting `ResearchInputOut.id` enters the existing `research_input_id`
   document research pipeline. The input is private to its owner and expires
   under existing private-input policy. It is not added to the global feed store.
6. After import, the same session can download the exact captured bytes as an
   inert attachment until the selection expires. No HTML is rendered inline.

The original access-token expiry, active account, original refresh-token family,
security version, source activation, selection owner and selection lifetime are
checked before private retention. After asynchronous disconnect cleanup, private
HTTP responses perform a fresh guarded session and ownership check. Refresh-family
validation follows the last awaited access-context work; successful release keeps
the transaction until request-session cleanup. No awaited rollback intervenes
between the last family check and synchronous private response reads. Final token
expiry is checked synchronously. A late denial does not pretend an already
authorised retention was rolled back.

## API and bounds

- `POST /api/research/sec/filings`: `SecFilingsSearchIn`, numeric CIK of one to ten
  digits, dates from 1994 through today, interval at most 3,660 days.
- `archive_page=0` selects recent submissions; one through fifty select a
  currently declared older file. The server rereads the issuer manifest.
- `offset` is a multiple of twenty from zero through 9,980. Each upstream file
  contains at most 10,000 rows; responses contain at most twenty choices.
- `SecFilingsPageOut` includes choices, page counts, next offset and limitations.
  A fresh search replaces the same session's unused choices. Imported originals
  keep their original expiry.
- `POST /api/research/sec/filings/{selection_id}/import` returns `ResearchInputOut`.
- `GET /api/research/sec/filings/{selection_id}/original` returns only a captured
  original, with attachment disposition, `application/octet-stream`, `nosniff`,
  sandbox CSP and private no-store caching.
- Selection lifetime: fifteen minutes. Maximum 220 choices globally and 22 per
  user, including imported/reserved choices. Original reservations: two per user,
  eight globally, at most 4 MiB each. Original cache ceiling: 32 MiB per process.
- Twenty search/import actions per user per fifteen minutes. The existing input
  store independently enforces its private slot and extracted-memory limits.
- Retrieval deadline: twenty seconds including shared pacing. Parser cleanup is
  joined before releasing capacity. No retry or background crawling.
- Extraction: 4 MiB original input, 100,000 markup start/end tokens, hidden depth
  128, at most 2,000,000 visible HTML processing characters, 112,000 retained characters
  and eighty passages of at most 1,400 characters. Truncation is explicit.

## Evidence, temporal interpretation and preservation

Imported passages use `research_import` with SEC upstream provenance and the
canonical primary-document URL. Attributes retain issuer CIK, accession, filing
day, original filename/media type/byte count and SHA-256, parser method, text
encoding, extracted-text hash and character range. Characters refer to normalised
extracted text, not HTML bytes, original page numbers or preserved table layout.

Scripts, styles and hidden content are omitted; external resources are never
loaded. UTF-8 and legacy Windows-1252 handling is explicit. Known SEC policy error
responses are rejected. Source reliability and information credibility for
issuer-filed content are unassessed, rather than borrowing the SEC host's rating.

Filing day is not a precise publication instant or the period described in the
document. `published_at` remains absent for both metadata and imported content;
`filing_date` and `date_precision=day` preserve the available fact. Integration
with the independent source-provenance branch must map this date to its typed
calendar-day representation before combined acceptance. Do not copy that
branch's domain types into this older base or invent UTC midnight.

Exact original bytes are preserved only in the bounded transient cache. The
hash alone is not preservation. Once a report retains an imported passage,
existing original-asset attachment controls can accept a hash-matched reupload
using that evidence anchor. This milestone does not silently attach a durable
original before a report exists. The UI must disclose download expiry and
separate durable retention.

## Acceptance

Baseline: existing SEC company records tests passed, 21 cases. New checks cover
declared older-file bounds, date filtering, agent accession prefixes, hostile
document paths, redirects, parser limits, original hashes and citations,
unassessed assertions, private input execution, original download headers,
original refresh-family revocation, cancellation, capacity and cleanup.

Final focused acceptance: **92 passed** in 98.03 seconds, covering all new SEC
cases and affected company, collector, upload API and upload session regressions.
The real report pipeline retains three selected filing passages with exact hashes
and absent publication instants, without public collection. The real shared
collector retains an older filing through the narrow filing-calendar policy.
Three added cases revoke the real session during the final access-context read
and deny listing, imported preview and original bytes. The complete focused run
was repeated after this repair; the earlier 89-case run is pre-repair evidence.

The independent canonical-date prerequisite subsequently reproduced seven
failures before repair, including compact/week dates and non-padded/non-ASCII
provider values. A shared exact ASCII Gregorian parser now covers automatic
records, selected records, archive bounds and the temporary calendar policy.
Malformed rows are skipped independently. The affected group passed 84 tests,
including 31 new date cases; these overlap the earlier group and are not an
additional unique total. Whole-backend Ruff/format, mypy, import contracts and
configured Bandit passed again. Typed date attachment remains unimplemented.

Independent source re-review found no remaining issue in these repaired release
paths. Successful responses retain the transaction through synchronous private
reads and request teardown; failed responses roll back without returning content.
The staged changes passed Gitleaks. These checks do not replace the mandatory
[typed provenance integration gate](SEC_SOURCE_PROVENANCE_INTEGRATION.md), full
combined acceptance or live-provider acceptance.

Final frontend acceptance passed 1,026 tests in 201 files, with 95.11% statement,
90.14% branch, 93.60% function and 96.49% line coverage. Existing gates were not
changed. Type checking, global lint, formatting and production build passed.
Two observed cold globe-route test races were repaired using the already verified
per-file real-module loading pattern, without increasing timeouts or introducing
global preloading. The SEC interactions passed in both full runs.

Whole-backend Ruff and formatting checks passed. Mypy passed for 624 source files;
both import contracts passed; configured Bandit passed; `git diff --check` passed.
Every touched handwritten source file is at most 350 lines. Coverage was not
measured by this focused run. Logs are under the ignored `data/sec-filings-*`
paths. No production credentials, user database, deployment or live-provider
acceptance is implied by mocked tests.
