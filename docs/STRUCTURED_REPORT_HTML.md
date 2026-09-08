# Structured report HTML projection

The internal HTML adapter projects a bounded frozen report into escaped semantic HTML. It is not a public export format or a browser renderer. PDF, DOCX and language capability flags retain their current behaviour.

Immutable DocumentInline runs carry text and explicit auto/LTR/RTL direction. They reproduce block text exactly, capped at 256 runs per block. The builder applies its existing XML-compatible character filtering to both projections. Existing renderers continue using block text.

Structured citation groups, judgement IDs, evidence labels/grades, report references, saved period headers, evidence timestamps, source/event IDs, hashes and safe source/archive URLs are isolated. Source names and arbitrary prose use automatic direction. Citation-like text inside prose is never recognised or rewritten. Specialised assessment/research/challenge annexes still supply plain paragraphs and require further structured projection.

HTML uses fixed semantic tags, escaped values, bdi runs, print CSS and restrictive CSP. URLs are inert text. No scripts, external fonts, links, images or browser executables are used. Limits: 300,000 block characters, 16,000 per block/title/reference, 2,000 blocks and 4 MiB encoded HTML.

Next: a cancellable asynchronous PDF worker, verified packaged fonts and a pinned browser runtime. Hold admission until every descendant is reaped. Add OS-level egress denial and aggregate process memory limits; CSP and browser flags alone are insufficient. Preserve final report/session authority checks before releasing bytes.

This establishes text-preserving HTML structure only. Browser rendering, native-speaker acceptance, faithful PDF search/copy, screen-reader order and PDF accessibility conformance remain unverified. The isolated Chromium proof remains separate evidence with unresolved extraction limitations.
