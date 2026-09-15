# Public doctrine reference register

Verified on 14 September 2026. This is a pinned methodology reference pack for Ask Eye, not accreditation or evidence that an event occurred. Its four stable identifiers are retained from the existing registry in `application/assistant/catalogues.py`; the typed records now live in `application/assistant/doctrine_references.py`.

| Reference | Verified edition/date | Verification and scope |
| --- | --- | --- |
| [PHIA uncertainty guidance](https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment) | Public guidance, 24 March 2025 | Public HTML read. Approximate likelihood vocabulary and the separate analytical-confidence framework. No internal PHIA evaluation tool is held. |
| [PHIA Common Analytical Standards](https://www.gov.uk/government/publications/phia-common-analytical-standards/phia-common-analytical-standards) | Public guidance, 24 March 2025 | Public HTML read. Analytical practice, auditability, contrary evidence, alternative explanations and independence from preferred policy conclusions. |
| [MOD JDP 2-00 catalogue](https://www.gov.uk/government/publications/jdp-2-00-understanding-and-intelligence-support-to-joint-operations) | Fourth Edition, August 2023 | Current title: Intelligence, Counter-intelligence and Security Support to Joint Operations. The catalogue was created on 1 August 2011 and updated on 17 August 2023. The edition itself specifies the month, not a publication day. |
| [NATO AJP-2.9, official DLA catalogue](https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283399) | Edition B, promulgated 20 August 2025 | Active NATO OSINT publication metadata, verified through the US Defense Logistics Agency. The public record does not state a version number. Controlled text was not retrieved, read or verified. |

The [official MOD PDF](https://assets.publishing.service.gov.uk/media/653a4b0780884d0013f71bb0/JDP_2_00_Ed_4_web.pdf) title, edition and release conditions were checked. Only a short excerpt from the GOV.UK catalogue HTML is stored. The PDF's separate release conditions are not replaced by the website's Open Government Licence. No PDF is added to the repository or runtime context.

The previous NATO reference pointed to the [general GOV.UK AJP collection](https://www.gov.uk/government/collections/allied-joint-publication-ajp), which did not list AJP-2.9 when checked. The precise DLA publication record replaces that link. Its [related STANAG 6522 record](https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283384) independently names Edition B and the same promulgation date. Older mirrored Edition A texts and commercial claims about a version number are not used as verification.

The DLA page's global data-refresh header is not treated as an update date for the individual publication record; that record-level date remains unknown.

## Integrity and reuse

Each immutable record carries publisher, official source URL, edition, date precision and basis, catalogue dates, retrieval date, verification scope, access limits and one attributed excerpt of at most 25 words. PHIA and MOD excerpts come from licensed GOV.UK HTML. The NATO entry retains only the public catalogue's factual title, with no assertion of permission to reproduce NATO doctrine text.

An excerpt SHA-256 covers its exact UTF-8 text without whitespace normalisation. A separate pack SHA-256 covers the ordered records, including metadata, as canonical JSON with sorted keys, compact separators, Unicode text and ISO dates. The registry validates its pinned digest at import. Offline tests detect changed text, dates, edition, URL, record order or duplicate identity. These hashes detect local drift; they do not prove remote authenticity or currentness.

Updates require another official-source review, accurate retrieval and edition metadata, and deliberate replacement of the affected hashes. Do not invent a day for month-only dates or promote catalogue verification to verification of the publication text. Retrieval dates remain separate from event timestamps in Ask Eye.

## Remaining production work

This milestone supplies attributable reference metadata only. It does not change report prompts, judgement scoring, claim adjudication or report publication gates. Production still needs the A02 mappings from specific, verified provisions to typed claim fields, deterministic checks, bounded adjudication proposals and versioned report provenance. Reference presence does not establish that every production path enforces a provision, that generated likelihoods are calibrated, or that the application is officially accredited.
