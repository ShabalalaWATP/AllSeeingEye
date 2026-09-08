# Companies House filing discovery and import

8 September 2026. Implementation contract for the outstanding E6 selected filing
requirement. Not implemented or accepted. Build on the combined SEC/provenance
delivery after preserving its acceptance snapshot. Local fixture acceptance does
not establish live credentials, complete registry coverage or reuse permission.

## Operator journey

An operator supplies an exact company number, browses one bounded filing-history
page, selects a document and imports its extractable PDF text into private research.
Existing company-name search remains a separate candidate-discovery step. Show
document availability, processed date and partial coverage before import. Reuse
the existing private-input declaration and report/evidence flows.

## Verified provider contract

- History: `GET https://api.company-information.service.gov.uk/company/{company_number}/filing-history`,
  with `category`, `items_per_page` and `start_index`; no documented date filter.
  [Official history endpoint](https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/filing-history/list?v=latest).
- History `date` means processed date. Preserve its exact canonical raw day as
  `SourceDate(field="date", role="unspecified", calendar="gregorian", basis="source_spec")`.
  Display **Filing processed**; keep exact publication unknown. Never apply SEC
  publication-day qualification to it.
  [Official filing resource](https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/filinghistorylist?v=latest).
- Optional `links.document_metadata` leads to document ID, formats, pages and
  declared lengths. Validate exact official origins, IDs and requested company.
  [Document metadata](https://developer-specs.company-information.service.gov.uk/document-api/resources/documentmetadata?v=latest).
- Content: authenticated `GET https://document-api.company-information.service.gov.uk/document/{document_id}/content`
  with required `Accept`; documented response is 302 Location, or 406 for an
  unsupported format. [Document download](https://developer-specs.company-information.service.gov.uk/document-api/reference/document-location/fetch-a-document).
- HTTP Basic uses the API key as username and an empty password. These reads do
  not need a company filing authentication code. Reuse `ASE_COMPANIES_HOUSE_KEY`.
  [Authentication](https://developer.company-information.service.gov.uk/authentication).
- Provider allowance is 600 requests per five minutes. Share the existing client
  allowance across profiles, officers, PSC and documents; do not create separate
  selected-import allowances that multiply the effective limit.
  [Developer guidelines](https://developer.company-information.service.gov.uk/developer-guidelines/).

## Transport and persistence boundaries

Add focused domain, port, service, API and container modules following SEC filing
selection. Return opaque actor/session-bound choices, never client-supplied URLs.
Retain company number, transaction ID, processed day, category/type, description,
document ID and availability. Recheck the selected filing before retrieval.

The existing authenticated feed client refuses redirects and cannot directly
implement the document contract. Add a narrow operation that captures one
authenticated document-API 302, then downloads that Location without Authorization
or cookies. Bind credentials separately to the exact two official API origins.
The official contract provides no fixed CDN hostname; do not invent one.

Only accept a bounded HTTPS Location returned directly by that authenticated
endpoint. Reject userinfo, fragments, nonstandard ports, IP literals and non-public
or mixed DNS answers. Reuse public-host validation, DNS pinning/TLS handling and
bounded reads. Allow no further redirect. Do not cache, persist, export or expose
signed URLs in errors/logs; retain stable official document links only.

Reuse the isolated document worker and PDF extractor, then attach typed source
provenance to private events. Preserve actual original SHA-256, physical page
references and text offsets. Reuse private slots, opaque expiry, cleanup and final
session checks. Keep originals private and bounded, with inert downloads. Do not
refactor unrelated SEC behaviour or relax its authenticated redirect refusal.

## Application bounds

- One explicit history page, 20 rows, bounded offset and explicit next-page action.
  No background traversal. Date/category filters describe only the fetched page;
  an empty filtered page does not prove no matching filings exist.
- At most two discovery API calls and four import requests: filing recheck,
  metadata, content Location and binary download. No automatic retries.
- Shared total deadline of 30 seconds including extraction, cancellation and
  cleanup. Verify worker deadlines participate in this bound.
- PDF only, 4 MiB streamed original limit. Declared length is an early check,
  never a replacement for actual byte limits. Retain existing parser limits of
  50 pages, 200 passages and 200,000 characters.
- Existing 15-minute selections and private-input admission limits. Enforce
  combined source/operator declaration caps and derived-parent lineage unchanged.

Text-bearing PDFs are supported. Scanned-only documents report no extractable
text and unavailable OCR; mixed documents disclose omitted scanned pages. Do not
claim extraction of annotations, attachments or form fields.

## Acceptance

- [ ] Exact number, malformed/mismatched links and rows, missing document, bounded
      pagination and honest filtered-empty/partial coverage.
- [ ] Missing/invalid key, 401/429 and shared allowance exhaustion before network.
- [ ] Metadata ID/format/size mismatch, required Accept, valid 302, missing Location
      and redirect-chain refusal.
- [ ] No credentials/cookies on binary downloads; no signed URL in caches, logs,
      errors, receipts, reports or exports. DNS rebinding and private/mixed answers
      refused, including malicious metadata links and alternate ports.
- [ ] Real fixture PDFs: text, scanned-only, mixed pages, encryption, malformed,
      oversize/decompression-heavy input, deadline/cancellation and worker cleanup.
- [ ] Foreign owner/family, revoked session at awaited stages, expired selections,
      abandoned requests, slot exhaustion and atomic reservation cleanup.
- [ ] Import, operator declaration, report, reload and ZIP/DOCX preserve processed
      metadata, unknown publication, original hash and page/text anchors.
- [ ] Existing Companies House/SEC behaviour, shared accounting, historical digests,
      generated contracts, UI behaviour, static/security checks and full gates.

## Operational limits

Deterministic fixtures are required: the document API is unavailable in the sandbox.
Live acceptance needs a configured developer application and key.
[Getting started](https://developer.company-information.service.gov.uk/get-started),
[testing environments](https://developer.company-information.service.gov.uk/api-testing).
Free downloads do not establish unrestricted republication rights for every
document. Retain attribution and existing private sharing/use declarations.
[Services](https://www.gov.uk/government/organisations/companies-house/about/about-our-services),
[personal information charter](https://www.gov.uk/government/organisations/companies-house/about/personal-information-charter).
