# AllSeeingEye expert board implementation plan

Last updated: 18 July 2026

## Objective

Turn AllSeeingEye from one generic reviewer into a routed expert board. The app should inspect the current screen or supplied text, accept an optional specific question, select only the relevant expert domains, and optionally combine their distinct findings without hiding disagreement or provenance.

## Current behaviour and architecture

Before this work, AllSeeingEye used this path:

```text
Eye click, shortcut, context menu or text tab
  -> validated preload IPC
  -> main-process AnalysisController
  -> ephemeral screen capture or pasted text
  -> one OpenAI structured-output call
  -> one RedTeamFinding
  -> compact or expanded React view
```

The app had five prompt lenses, but no agent router, knowledge base, citations, expert identity, combined analysis, or focus question for screen capture. It persisted only preferences. It had no remote backend, database, analysis history, or telemetry.

The Electron main process remains the local backend. A remote service or vector database is not justified for the initial curated packs.

## Target flow

```text
Selected display/window, text or voice note plus optional focus question
  -> voice note only: automatic in-memory transcription after Done
  -> observation model, raw artefact seen once
  -> bounded evidence envelope and typed, evidence-linked signals
  -> deterministic local relevance policy
  -> selected versioned knowledge packs
  -> selected expert calls in parallel
  -> validated findings and citation allow-list checks
  -> Focused: highest-priority selected expert finding
  -> Combined: synthesis over validated expert outputs only
  -> compact primary finding plus Overall-first and selected expert tabs
```

Combined means combine every relevant selected expert. It does not mean run every expert.

## Expert catalogue

The first board contains:

1. Cyber Security & Privacy
2. UX, Accessibility & Human Factors
3. Finance & Commercial Viability
4. Legal & Regulatory
5. Public Policy & Governance
6. Ethics & Societal Impact
7. Technical Architecture & Reliability
8. Product & Differentiation
9. Writing, English Language & Editorial Quality
10. Evidence, Research & Fact Quality
11. Health, Sleep & Wellbeing
12. Delivery, Operations & Change

Candidate follow-on packs are clinical safety, safeguarding, sustainability, procurement, employment, education and other tightly scoped sector packs. Broad overlapping agents are not added without a distinct routing boundary.

## Milestone 1: routed local expert board

Status: implemented in the working tree.

Success criteria:

- The idle surface shows only the eye. Hover, keyboard focus or right-click opens a four-input tray beneath it without replacing the eye.
- Screen and text requests accept a focus question of at most 1,000 characters.
- Focused mode selects one best-fit expert plus mandatory safety overrides.
- Combined mode selects up to four normal relevant experts plus bounded mandatory overrides and synthesises relevant validated outputs.
- The raw screen is sent only to the observation/router stage. Experts receive a bounded evidence envelope.
- Only contributing experts are displayed.
- Findings preserve expert identity, pack version, evidence strength, validation need and allow-listed source IDs.
- User artefacts are not written to the knowledge base, preferences, logs or history.
- If synthesis fails, successful expert findings still produce a deterministic result.
- Overall opens first and only contributing experts receive their own result tabs.
- Display, application-window, text and automatic voice-note inputs are available.

## Milestone 2: capture minimisation and control

Status: display and application-window selection implemented; region/redaction work remains.

Work:

- Add user-selected region capture. Individual application-window capture is implemented.
- Add an optional preview with crop and redaction before transmission.
- Make the capture scope visible before submission.
- Ensure a narrow focus question never implies that unrelated screen areas are excluded.
- Add keyboard-complete region selection or a non-pointer alternative.
- Repeat DPI, multi-monitor, assistive-technology and packaged-app tests.

Success criteria:

- Users can choose an entire display or individual application window; selected region remains pending.
- The payload contains only the selected pixels.
- The UI accurately states what will be transmitted and to which configured provider.

## Milestone 3: evaluation and quality gates

Build a labelled evaluation set with representative screen and text fixtures. Measure separately:

- Router precision and recall per expert.
- Observation omission, especially small text and diagrams.
- Finding groundedness against evidence IDs.
- Citation validity and source-status accuracy.
- Abstention and insufficient-context behaviour.
- Prompt-injection resistance for visible and pasted instructions.
- Combined deduplication and disagreement preservation.
- Severity calibration and false-positive rate.
- Latency and token cost for Focused and Combined modes.

Release gates should be based on measured baselines, not invented thresholds. Every pack needs seeded happy paths, boundary cases, not-applicable cases and adversarial cases.

## Milestone 4: run control and resilience

Work:

- Immutable run IDs are implemented; add complete prompt/model provenance.
- Add cancellation with `AbortController` for dismiss, a new run and quit.
- Use a shared run deadline and explicit per-stage time budgets.
- Surface partial results and failed expert IDs without losing successful findings.
- Bound expert concurrency and retry only transient failures.
- Add stage timing and token usage without logging user content.
- Prevent stale runs from updating current UI state.

## Milestone 5: knowledge lifecycle

The static TypeScript registry is intentionally small and auditable. Before expanding it:

- Add a strict pack schema and build-time validation.
- Store source authority, jurisdiction, binding status, effective dates, version, last verification, review due date and content hash.
- Check links and content hashes on a schedule.
- Quarantine changed, withdrawn or stale sources until human review.
- Keep current law, official guidance, voluntary frameworks and future proposals visibly distinct.
- Retrieve only the relevant topics from larger packs. Do not inject whole document dumps.
- Never ingest user screenshots, prompts or analyses into the public-source knowledge store.

High-volatility legal, policy, tax and financial-regulation sources need shorter review intervals than stable standards. Legal conclusions must remain conditional on jurisdiction, actor role and facts.

## Milestone 6: production hardening

- Introduce an analysis-provider interface before supporting another provider or a managed backend.
- Complete a controller/processor data-flow assessment and DPIA screening before any managed service stores or receives user content.
- Add signed Windows distribution, update integrity and a support policy.
- Add accessibility verification using the packaged app, Narrator, keyboard-only operation, high contrast, forced colours, magnification and reduced motion.
- Add CI for type checks, tests, builds, dependency audit, CodeQL, secret scanning and pack validation.
- Define cost, latency and availability SLOs from measured usage.

## Decision rules

- Every input first receives one short general-model quick take with no routing,
  sources, severity, confidence or knowledge-pack claims.
- Full analysis starts only after an explicit expansion and consumes the same
  short-lived input hand-off exactly once.
- Prefer one selected expert for a normal Focused full review.
- Use Combined only when more than one relevant domain can materially change the decision.
- Never average away high legal, security, rights or safety findings.
- Preserve disagreement when expert recommendations conflict.
- Never claim compliance, legal certainty, patentability, accessibility conformance, security certification or financial suitability from a screenshot.
- Ask for missing jurisdiction, authority, ownership or numerical inputs when they change the conclusion.
- Keep the human responsible for consequential decisions.

## Definition of done for the expert-board release

- All automated checks pass.
- Pack and prompt versions are captured in every report.
- Evaluation gates pass on the labelled fixture set.
- Scoped capture and accurate transmission disclosure ship.
- Cancellation and stale-run protection are implemented.
- Legal and source freshness review is signed off.
- Packaged Windows accessibility and privacy journeys are manually verified.
- Documentation and threat model match actual behaviour.
