# ADR 0024: Visible AI disclosure and portable export markers

Date: 16 October 2026. Status: proposed for KAN-191 review.

## Context

Assessments can leave the application as documents without the surrounding UI.
The output should identify AI assistance without implying that source evidence,
human annotations, model accuracy or the hosting organisation have been verified.
The selected saved version already records its model identifier and may retain
the assessment profile's provider connector in its frozen routing record.

## Decision

Use a shared visible disclosure component on the app's AI output surfaces.
Preserve existing review, uncertainty and provenance explanations. Provider
readiness is a separate state: the existing connection-setup notice is unchanged.
Only explicitly recorded machine translations receive the translation label;
operator/source transformations and unknown historical authorship are not guessed.

For PDF and DOCX, add an adapter-owned statement beside the opening title and a
repeated footer. The full model identifier stays in the opening statement and
machine-readable properties; unusually long identifiers are explicitly shortened
in the footer. The canonical publication blocks, saved Markdown, body and evidence
are unchanged. ReportLab font subsetting retains its existing serial lock.

`ReportDocument.ai_disclosure` is presentation metadata derived from the exact
saved version after normal export authorisation. It uses the saved response model
and the matching assessment profile's frozen provider connector. No current profile,
endpoint, client-supplied model, profile identifier, binding or credential is read
or exported. Legacy/mismatched provider provenance remains `unknown`.
The explicit `no_evidence` outcome is a deterministic gap notice, so it receives
`ase:ai-generated=false` and a matching visible explanation, with no claimed model
use. Attempt count or failed status alone cannot establish this: resumed generated
checkpoints may need zero new calls, and generated text can fail later checks.
`openai_compatible` means an API connector, not a verified OpenAI-hosted request;
visible wording explicitly says that the host was not recorded. Unsafe control
characters or oversized saved identifiers fail with a sanitised error.

PDF Info properties contain `ase:ai-generated`, `ase:ai-model`,
`ase:ai-provider` and `ase:ai-scope`; keywords include `AI-generated` and
`AI-assisted assessment`. DOCX includes the same names in typed custom properties
(a boolean plus strings), core keywords and a bounded core description. Full model
details remain in custom properties. Existing title/author/reference, links,
outlines and deterministic output remain. The optional Chromium path receives a
bounded, read-only disclosure file and writes PDF metadata inside its isolated
child; untrusted PDF parsing does not move into the application process.

GeoJSON evidence packages identify their associated report's AI provenance and
explicitly flag model-derived candidate titles in recorded AI visual hypotheses
by JSON Pointer. Fixed application headings are excluded. This is
a partial classification; other source fields retain unknown authorship.
Live GeoJSON and KML likewise declare source observations, no application-generated
assessment fields, and unknown upstream authorship. Neither export currently
contains the generated assessment prose. These distinctions must change if a
future exporter adds generated descriptions; a blanket AI flag would mislabel
the present source data. Feature geometry, source titles, original assets and
evidence hashes are preserved.

## Limits and content credentials

These are self-declared labels and portable metadata, not tamper-resistant
watermarks, a signature, a detector or proof of truth. Other software can remove
or alter them. Do not represent this implementation as complete legal compliance
or as a C2PA credential. Future C2PA adoption needs a separate decision covering
supported text/document formats, interoperable manifests, signing-key custody,
verification, privacy and behaviour when transformations strip credentials.
No signing service, dependency or identity infrastructure is added by this ticket.

The Commission's current [Article 50 guidance](https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations)
distinguishes provider marking duties from deployer disclosure duties. Its
[FAQ](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)
states general application from 2 August 2026 and the limited 2 December 2026
marking transition for qualifying systems placed on the market before 2 August.
That is not a universal postponement or evidence that this installation qualifies.
Applicability, provider/deployer roles, robustness and any further measures require
their own assessment. The implementation is useful disclosure regardless of those
legal conclusions. Sources reviewed 16 October 2026.

## Validation

Read exported PDF text/Info and DOCX paragraphs/core/custom properties back.
Verify every PDF page, both Word footer variants, historical/missing/mismatched
model provenance, literal hostile and long identifiers, deterministic bytes and
preserved body/evidence. Test the isolated child's metadata and tag preservation,
bounded malformed-input rejection, and GeoJSON/KML metadata semantics. Frontend
tests cover the actual AI surfaces as well as the shared component. Retain existing
access-release, package-integrity, renderer isolation and concurrent-font checks.
