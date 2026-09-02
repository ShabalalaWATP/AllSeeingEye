# ADR 0007: Sources are graded deterministically before any LLM assessment

Status: Accepted (proposed 2 September 2026, accepted by Alex 3 September 2026)

## Context

Alex wants source grading (NATO/Admiralty style reliability and credibility) applied before AI assessment, with well-structured, cited reports that use the UK probability yardstick. LLMs are poor at consistent grading and are vulnerable to persuasion by the content they grade.

## Options

1. **Deterministic grading engine in code.** Reliability comes from the admin-maintained source registry (with defaults by source type). Credibility is computed per item from corroboration across independent sources, source type, consistency with instrument data, and age. Every grade carries a rationale string. The LLM receives grades as facts and must weight evidence accordingly; it may not change them.
2. **Ask the LLM to grade.** Flexible but inconsistent, unexplainable, and manipulable by injected text.
3. **Hybrid.** Deterministic grades with an optional LLM "second opinion" flagged separately.

## Decision

Option 1 now, with option 3 as a possible later addition that never overrides the deterministic grade. Grading rules are small strategy classes with property-based tests. Independence between sources is modelled through a `parent_org` field in the registry so syndicated copies do not count as corroboration.

## Consequences

- Grades are explainable and stable; the same evidence always gets the same grade.
- Reports must show grades inline with citations and in a sources annex.
- The registry's reliability defaults are an editorial decision that the admin owns; the defaults ship documented in `SOURCES.md`.
