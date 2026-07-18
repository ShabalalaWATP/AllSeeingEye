# Expert knowledge base

Last research verification: 18 July 2026

## Purpose

AllSeeingEye uses curated, versioned knowledge packs to give each selected expert a bounded remit, an adversarial rubric, routing signals, exclusions, cross-domain hand-offs, source-linked knowledge notes and an allow-listed source register. The packs are decision-support material, not an automated compliance or certification system.

The runtime registry is [packs.ts](../src/main/knowledge/packs.ts). Its shared schema is [types.ts](../src/main/knowledge/types.ts).

## Pack contents

Each pack records:

- Expert ID and user-facing label.
- Version, last verification and next review date.
- Relevant jurisdictions.
- Remit and explicit exclusions.
- Hard and soft routing signals.
- Co-routing relationships.
- Eight-or-more-part adversarial review rubric.
- Primary-source register with authority, URL, jurisdiction, status and verification date.
- Short factual knowledge notes whose source references must resolve within that pack.
- Domain-specific disclaimer.

Sources are classified as binding, mandatory in scope, official guidance, voluntary framework, informative, or future/volatile. These statuses must never be flattened into a generic claim that something is required.

## Runtime use

1. The observation/router stage sees the raw screenshot or supplied text once.
2. It returns a bounded evidence envelope and normalised, evidence-linked signal IDs. It does not choose the experts.
3. A deterministic TypeScript policy applies confidence thresholds, focus intent, mandatory safety rules and per-expert signal rules. Generic words such as “app”, “AI”, “SaaS”, “cloud”, “data” or “secure funding” cannot establish Cyber relevance.
4. Each selected expert receives only that evidence envelope, the focus question, review lens, source kind and its own pack.
5. Experts use curated knowledge notes plus stable, widely accepted model background knowledge. Volatile, high-stakes and personalised propositions require stronger verification and lower confidence when a suitable note is absent.
6. The expert must cite valid evidence IDs and may cite only source IDs included in its pack. Model-only knowledge cannot receive a pack source reference. Visible evidence is reconstructed locally from valid IDs.
7. Local sanitisation removes fabricated or cross-pack source IDs and pins the real expert ID, pack version and disclaimer.
8. `not_relevant` experts are hidden and excluded before synthesis. An `insufficient_context` specialist appears only when explicitly requested or mandatory.
9. Combined synthesis receives only relevant validated expert results. It cannot retrieve new sources or inspect the original screenshot.

No runtime web retrieval is enabled. This prevents silent source drift and reduces prompt-injection exposure. The cost is that maintainers must refresh packs deliberately.

## Source policy

- Prefer legislation, regulators, standards bodies, governments and intergovernmental organisations.
- Store short human-authored review instructions and source metadata, not indiscriminate copies of whole documents.
- Preserve jurisdiction, binding status, version and effective date.
- Treat visible or pasted content as untrusted data. It cannot amend a pack or its source register.
- Never add user artefacts, extracted evidence or model output to the knowledge store.
- A source reference supports only the proposition for which it is applicable.
- Missing authority turns a legal or regulatory statement into a question or conditional risk, not an invented rule.
- ISO pages in the current registry provide public metadata only. Licensed standard text has not been ingested.

## Domain caveats

- Cyber frameworks guide assurance but do not establish legal compliance.
- WCAG conformance cannot be determined from a screenshot alone.
- Finance output is not accounting, tax, audit, investment or personalised financial advice.
- Legal output is issue-spotting only. UK, GB, Northern Ireland and EU scope must not be treated as interchangeable.
- Policy proposals and future application dates must remain distinct from current obligations.
- Ethics frameworks are not laws and require stakeholder participation for high-impact decisions.
- Architecture review is not a production readiness, load or security certification.
- Product differentiation is not patentability, freedom to operate or trade-mark clearance.
- Writing uses UK English by default, but is not fact-checking and must not become a universal prose reviewer. Voice transcripts require explicit editorial intent before surface grammar or punctuation review.
- Evidence review challenges provenance, method and inference but does not independently retrieve or verify missing sources.
- Health review covers proportionate everyday wellbeing and sleep decisions. It is not diagnosis, treatment, medication advice or emergency triage.
- Delivery review challenges sequencing, ownership, rollout and operations but is not readiness certification.

## Refresh priorities

Review at least monthly:

- UK and EU AI law and implementation timelines.
- ICO data-protection guidance following the Data (Use and Access) Act 2025.
- Financial regulation, tax thresholds, payments and consumer-pricing guidance.
- NHS, NICE, FSA and EFSA health, sleep and caffeine guidance.
- Product substitutes and platform capabilities used for differentiation claims.

Review at least quarterly:

- OWASP, NIST AI and cyber material.
- Accessibility guidance and Electron or Windows platform guidance.
- UK public-policy and procurement material.
- Ethics, child-safety, labour and environmental frameworks.

Review stable ISO, W3C and enduring legislation annually, plus immediately when a source-change monitor detects a material update.

## Current catalogue and planned extensions

The current catalogue contains Cyber Security & Privacy; UX, Accessibility & Human Factors; Finance & Commercial Viability; Legal & Regulatory; Public Policy & Governance; Ethics & Societal Impact; Technical Architecture & Reliability; Product & Differentiation; Writing, English Language & Editorial Quality; Evidence, Research & Fact Quality; Health, Sleep & Wellbeing; and Delivery, Operations & Change.

Later sector packs should be invoked only when their scope is detected, rather than making the core Legal, Policy or Health agents pretend to cover every regulated field. Strong candidates are clinical safety, safeguarding, sustainability, procurement, employment and education. Generic Marketing, Business Strategy, AI and Compliance agents are deliberately deferred because their remits overlap the existing board.
