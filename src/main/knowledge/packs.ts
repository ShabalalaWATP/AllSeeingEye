import type { ExpertId } from '../../shared/types'
import type { KnowledgePack, KnowledgeSource, SourceStatus } from './types'

const VERIFIED = '2026-07-18'

function source(
  id: string,
  authority: string,
  title: string,
  url: string,
  jurisdiction: string,
  status: SourceStatus = 'official_guidance'
): KnowledgeSource {
  return { id, authority, title, url, jurisdiction, status, lastVerified: VERIFIED }
}

const packs: KnowledgePack[] = [
  {
    expertId: 'cyber_security_privacy',
    label: 'Cyber Security & Privacy',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-10-18',
    jurisdictions: ['global', 'UK', 'EU'],
    remit: 'Model assets, actors, data flows, trust boundaries and credible misuse. Prioritise material security, privacy and resilience gaps, then propose defensive, testable controls.',
    exclusions: ['No offensive exploitation steps', 'No security certification', 'Refer legal duties to Legal'],
    hardTriggers: ['explicit security, privacy, incident or vulnerability question', 'accounts, credentials, permissions or identity boundaries', 'personal, confidential, biometric, health or financial data processing', 'payment processing or financial data', 'internet-facing APIs, uploads, webhooks or agent tools', 'tenant isolation or shared privileged access', 'secrets, code, build or deployment controls'],
    softTriggers: ['fraud', 'impersonation', 'insider risk', 'records handling', 'operational resilience'],
    coRoute: ['legal_regulatory', 'technical_architecture', 'ux_accessibility', 'ethics_societal'],
    rubric: ['Assets, affected parties and reversible versus irreversible harms', 'Entry points, trust boundaries, privileges, tenants and suppliers', 'Authentication, recovery, object/action authorisation and least privilege', 'Input validation, injection, uploads, SSRF and fail-open behaviour', 'Purpose, minimisation, retention, sharing, deletion and DPIA signals', 'Secrets, supported cryptography, dependencies, builds and update integrity', 'AI prompt injection, poisoned context, excessive agency and scoped tools', 'Logging, detection, incident response, recovery and residual risk'],
    sources: [
      source('sec.owasp.tm', 'OWASP', 'Threat Modeling Cheat Sheet', 'https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html', 'global', 'informative'),
      source('sec.owasp.asvs5', 'OWASP', 'Application Security Verification Standard 5.0.0', 'https://owasp.org/www-project-application-security-verification-standard/', 'global', 'voluntary_framework'),
      source('sec.owasp.agentic2026', 'OWASP', 'Top 10 for Agentic Applications 2026', 'https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/', 'global', 'informative'),
      source('sec.nist.csf2', 'NIST', 'Cybersecurity Framework 2.0', 'https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20', 'US/global', 'voluntary_framework'),
      source('sec.ncsc.ai', 'UK NCSC', 'Guidelines for Secure AI System Development', 'https://www.ncsc.gov.uk/collection/guidelines-secure-ai-system-development/about-this-document', 'UK/global'),
      source('sec.ico.design', 'ICO', 'Data protection by design and by default', 'https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/guide-to-accountability-and-governance/data-protection-by-design-and-by-default/', 'UK')
    ],
    disclaimer: 'Defensive issue-spotting, not a penetration test, certification or legal opinion.'
  },
  {
    expertId: 'ux_accessibility',
    label: 'UX, Accessibility & Human Factors',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-10-18',
    jurisdictions: ['global', 'UK', 'EU'],
    remit: 'Judge whether intended users can understand, control and complete their task effectively, efficiently, inclusively and safely.',
    exclusions: ['Do not claim WCAG conformance from a screenshot', 'Do not diagnose disability', 'Refer statutory conclusions to Legal'],
    hardTriggers: ['visible interface, form, workflow or onboarding', 'accessibility or usability question', 'consent, warning or recovery flow', 'user research or persona claims', 'AI output a person must interpret or act on'],
    softTriggers: ['adoption', 'trust', 'content clarity', 'cognitive load', 'behaviour change'],
    coRoute: ['legal_regulatory', 'ethics_societal', 'cyber_security_privacy'],
    rubric: ['User need and end-to-end task outcome', 'Discoverability, mental model and information architecture', 'Interaction cost, cognitive load and interruption', 'Error prevention, reversibility and recovery', 'Keyboard, assistive technology, focus and meaningful semantics', 'Contrast, zoom, reflow, forced colours and reduced motion', 'Plain content, provenance, uncertainty and user control', 'Representative research, inclusion, consent and deceptive patterns'],
    sources: [
      source('ux.wcag22', 'W3C', 'Web Content Accessibility Guidelines 2.2', 'https://www.w3.org/TR/WCAG22/', 'global', 'voluntary_framework'),
      source('ux.aria12', 'W3C', 'WAI-ARIA 1.2', 'https://www.w3.org/TR/wai-aria/', 'global', 'voluntary_framework'),
      source('ux.apg', 'W3C', 'ARIA Authoring Practices Guide', 'https://www.w3.org/WAI/ARIA/apg/about/introduction/', 'global', 'informative'),
      source('ux.coga', 'W3C', 'Making Content Usable for People with Cognitive and Learning Disabilities', 'https://www.w3.org/TR/coga-usable/design_guide.html', 'global', 'informative'),
      source('ux.gov.service', 'UK Government', 'Service Standard: make the service simple to use', 'https://www.gov.uk/service-manual/service-standard/point-4-make-the-service-simple-to-use', 'UK'),
      source('ux.electron', 'Electron', 'Accessibility', 'https://www.electronjs.org/docs/latest/tutorial/accessibility', 'global', 'informative')
    ],
    disclaimer: 'Evidence-bounded UX and accessibility review, not a conformance audit or legal opinion.'
  },
  {
    expertId: 'finance_commercial',
    label: 'Finance & Commercial Viability',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-08-18',
    jurisdictions: ['UK', 'global'],
    remit: 'Challenge the revenue mechanism, pricing, unit economics, cash demands, funding assumptions, market evidence and material payment or fraud exposure.',
    exclusions: ['No personalised investment advice', 'No definitive accounting, tax or regulatory opinion', 'Never invent missing numbers'],
    hardTriggers: ['budget, forecast, price or funding ask', 'revenue, margin, CAC, churn, runway or ROI', 'checkout, subscription, marketplace, lending, wallet, insurance or investment', 'market-size or return claim'],
    softTriggers: ['commercial model', 'cost to serve', 'buyer or distribution', 'business interruption or fraud loss'],
    coRoute: ['legal_regulatory', 'cyber_security_privacy', 'ux_accessibility', 'product_uniqueness'],
    rubric: ['Payer, buyer, value and revenue mechanism', 'Demand evidence, pricing and sales-cycle assumptions', 'Contribution margin, cost to serve and scalability', 'Forecast arithmetic, units, periods and scenario integrity', 'Cash timing, working capital, runway and funding milestones', 'Market definition, acquisition, retention and distribution', 'Payments, fraud, refunds, safeguarding and promotions flags', 'Accounting, tax and regulatory questions requiring specialist review'],
    sources: [
      source('fin.bbb.pitch', 'British Business Bank', 'What makes a good pitch deck for investment', 'https://www.british-business-bank.co.uk/business-guidance/guidance-articles/business-essentials/what-makes-a-good-pitch-deck-for-investment', 'UK', 'informative'),
      source('fin.frc.frs102', 'Financial Reporting Council', 'FRS 102', 'https://www.frc.org.uk/library/standards-codes-policy/accounting-and-reporting/uk-accounting-standards/frs-102/', 'UK', 'mandatory_in_scope'),
      source('fin.hmrc.vat', 'HMRC', 'When to register for VAT', 'https://www.gov.uk/register-for-vat/when-register-for-vat', 'UK', 'mandatory_in_scope'),
      source('fin.fca.promotions', 'FCA', 'Financial promotions and adverts', 'https://www.fca.org.uk/firms/financial-promotions-adverts', 'UK'),
      source('fin.fca.payments', 'FCA', 'Payment Services and E-Money Regulations', 'https://www.fca.org.uk/firms/payment-services-regulations-e-money-regulations', 'UK'),
      source('fin.cma.ucp', 'CMA', 'Unfair commercial practices', 'https://www.gov.uk/government/publications/unfair-commercial-practices-cma207/unfair-commercial-practices', 'UK')
    ],
    disclaimer: 'Commercial critique only, not accounting, tax, audit, legal or personalised financial advice.'
  },
  {
    expertId: 'legal_regulatory',
    label: 'Legal & Regulatory',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-08-01',
    jurisdictions: ['UK', 'GB', 'Northern Ireland', 'EU'],
    remit: 'Identify plausible legal and regulatory issues, determine actor and jurisdiction dependencies, cite current authority and recommend verification or design steps.',
    exclusions: ['Not legal advice and no lawyer-client relationship', 'No definitive legality finding from missing facts', 'No reserved legal activity or deadline calculation'],
    hardTriggers: ['personal or sensitive data, monitoring or automated decisions', 'security testing or ambiguous authorisation', 'consumer prices, terms, subscriptions or marketing claims', 'contracts, liability, IP, licences or brand', 'accessibility, employment or public-sector use', 'regulated or cross-border activity'],
    softTriggers: ['confidentiality', 'AI transparency', 'complaints and redress', 'provider or controller role uncertainty'],
    coRoute: ['cyber_security_privacy', 'finance_commercial', 'ux_accessibility', 'ethics_societal', 'public_policy'],
    rubric: ['Actor, act, jurisdiction, territorial scope and legal threshold', 'Lawful basis, consent, licence, authorisation or contractual right', 'Necessity, minimisation, proportionality, security and human review', 'Pre-contract information, transparency, material claims and price', 'Rights, complaints, accessibility, challenge and non-excludable remedies', 'Vendors, processors, licences, audit rights and change control', 'Current law versus guidance, proposal, future commencement or volatility', 'Smallest safer design plus high-stakes professional escalation'],
    sources: [
      source('law.ukgdpr', 'UK Parliament', 'UK GDPR, revised retained Regulation', 'https://www.legislation.gov.uk/eur/2016/679/contents', 'UK', 'binding'),
      source('law.duaa2025', 'UK Parliament', 'Data (Use and Access) Act 2025', 'https://www.legislation.gov.uk/ukpga/2025/18/contents', 'UK', 'binding'),
      source('law.cma1990', 'UK Parliament', 'Computer Misuse Act 1990', 'https://www.legislation.gov.uk/ukpga/1990/18/contents', 'UK', 'binding'),
      source('law.cra2015', 'UK Parliament', 'Consumer Rights Act 2015', 'https://www.legislation.gov.uk/ukpga/2015/15/contents', 'UK', 'binding'),
      source('law.equality2010', 'UK Parliament', 'Equality Act 2010', 'https://www.legislation.gov.uk/ukpga/2010/15/contents', 'GB', 'binding'),
      source('law.eu.aiact', 'European Union', 'Regulation (EU) 2024/1689, AI Act', 'https://eur-lex.europa.eu/eli/reg/2024/1689/oj', 'EU', 'binding'),
      source('law.eu.omnibus2026', 'Council of the EU', 'AI Omnibus adopted text tracker', 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CONSIL:PE_30_2026_REV_1', 'EU', 'future_or_volatile')
    ],
    disclaimer: 'Legal issue-spotting, not legal advice. Applicability depends on facts and jurisdiction; verify high-stakes decisions with a qualified adviser.'
  },
  {
    expertId: 'public_policy',
    label: 'Public Policy & Governance',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-08-18',
    jurisdictions: ['UK', 'EU', 'global'],
    remit: 'Test public purpose, mandate, institutional fit, accountability, regulatory horizon, procurement, auditability, contestability and public-interest effects.',
    exclusions: ['Do not give definitive legal advice', 'Do not treat policy proposals as current law', 'Refer technical control design to specialist agents'],
    hardTriggers: ['government, regulator, public funds or public service', 'consequential eligibility or essential-service decision', 'policy, legislation or consultation', 'public procurement or strategic supplier', 'democratic process, rights or regulatory sandbox'],
    softTriggers: ['vendor lock-in', 'claims of approval or responsible AI', 'population-scale influence', 'unclear jurisdiction or actor role'],
    coRoute: ['legal_regulatory', 'ethics_societal', 'finance_commercial', 'technical_architecture'],
    rubric: ['Problem evidence, institutional mandate and accountable owner', 'Do-nothing, non-AI, insourced and alternative instruments', 'Public value, distributional effects and excluded stakeholders', 'Current regulation, horizon changes and cross-border uncertainty', 'Audit trail, transparency, meaningful challenge and redress', 'Baseline, counterfactual, theory of change and subgroup evaluation', 'Procurement rights, supplier change, portability, exit and lock-in', 'Stop conditions, monitoring, decommissioning and systemic effects'],
    sources: [
      source('policy.uk.ai', 'UK Government', 'Implementing the UK AI regulatory principles', 'https://www.gov.uk/government/publications/implementing-the-uks-ai-regulatory-principles-initial-guidance-for-regulators', 'UK'),
      source('policy.uk.playbook', 'UK Government', 'AI Playbook for the UK Government', 'https://www.gov.uk/government/publications/ai-playbook-for-the-uk-government/artificial-intelligence-playbook-for-the-uk-government-html', 'UK'),
      source('policy.uk.greenbook', 'HM Treasury', 'The Green Book 2026', 'https://www.gov.uk/government/publications/the-green-book-appraisal-and-evaluation-in-central-government/the-green-book-2026', 'UK'),
      source('policy.uk.atrs', 'UK Government', 'Algorithmic Transparency Recording Standard hub', 'https://www.gov.uk/government/collections/algorithmic-transparency-recording-standard-hub', 'UK', 'mandatory_in_scope'),
      source('policy.eu.aiact', 'European Commission', 'AI Act implementation framework', 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai', 'EU'),
      source('policy.nist.airmf', 'NIST', 'AI Risk Management Framework 1.0', 'https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10', 'US/global', 'voluntary_framework')
    ],
    disclaimer: 'Public-policy and governance critique, not legal advice or a statement of regulator approval.'
  },
  {
    expertId: 'ethics_societal',
    label: 'Ethics & Societal Impact',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-10-18',
    jurisdictions: ['global', 'UK', 'EU'],
    remit: 'Map benefits, power and harm across users, non-users, workers, vulnerable groups, institutions, society and the environment, then test necessity and proportionality.',
    exclusions: ['Do not turn one ethical tradition into universal law', 'Do not invent disparity or environmental metrics', 'Refer legal conclusions to Legal'],
    hardTriggers: ['high-stakes decisions or essential services', 'profiling, surveillance, biometrics or persuasion', 'children or vulnerable groups', 'worker monitoring or automated management', 'deepfakes, political influence or dual use', 'population-scale or public-sector deployment'],
    softTriggers: ['sensitive inferred traits', 'AI replacing professional judgement', 'labour or environmental impact', 'power imbalance'],
    coRoute: ['legal_regulatory', 'ux_accessibility', 'public_policy', 'cyber_security_privacy'],
    rubric: ['Legitimate purpose, necessity and less intrusive alternatives', 'Benefits, burdens, decision power and omitted stakeholders', 'Harm pathways under error, scale, feedback and misuse', 'Dignity, autonomy, real choice and dependency', 'Bias, proxy effects, inclusion and intersectional evidence', 'Transparency, provenance, contestability and remedy', 'Meaningful human authority, competence, time and information', 'Labour, supply chain, lifecycle environment and reversibility'],
    sources: [
      source('ethics.oecd.ai', 'OECD', 'OECD AI Principles, updated 2024', 'https://www.oecd.org/en/topics/ai-principles.html', 'global', 'voluntary_framework'),
      source('ethics.unesco.ai', 'UNESCO', 'Recommendation on the Ethics of Artificial Intelligence', 'https://www.unesco.org/en/legal-affairs/recommendation-ethics-artificial-intelligence', 'global', 'voluntary_framework'),
      source('ethics.nist.airmf', 'NIST', 'AI Risk Management Framework 1.0', 'https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10', 'US/global', 'voluntary_framework'),
      source('ethics.nist.bias', 'NIST', 'SP 1270: Identifying and Managing Bias in AI', 'https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1270.pdf', 'US/global', 'voluntary_framework'),
      source('ethics.uk.framework', 'UK Government', 'Data and AI Ethics Framework', 'https://www.gov.uk/government/publications/data-ethics-framework/data-and-ai-ethics-framework', 'UK'),
      source('ethics.unicef.children', 'UNICEF', 'Guidance on AI and Children v3.0', 'https://www.unicef.org/innocenti/reports/policy-guidance-ai-children', 'global', 'voluntary_framework')
    ],
    disclaimer: 'Ethical decision support, not a legal determination or substitute for affected-stakeholder participation.'
  },
  {
    expertId: 'technical_architecture',
    label: 'Technical Architecture & Reliability',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-10-18',
    jurisdictions: ['global'],
    remit: 'Challenge system boundaries, data contracts, scalability, operability, reliability, AI evaluation, failure containment and lifecycle maintainability.',
    exclusions: ['Do not invent unspecified infrastructure', 'Do not equate a diagram with production evidence', 'Refer law, commercial and ethical judgements'],
    hardTriggers: ['architecture, API, database, queue or cloud design', 'AI model, RAG, agent, tool or evaluation system', 'scale, latency, availability or migration claim', 'integration, dependency or deployment plan'],
    softTriggers: ['data quality', 'observability', 'vendor dependency', 'cost and performance trade-off'],
    coRoute: ['cyber_security_privacy', 'finance_commercial', 'ux_accessibility'],
    rubric: ['Requirements, constraints, quality attributes and measurable SLOs', 'Components, boundaries, contracts, ownership and source of truth', 'Data lifecycle, consistency, schema evolution and recovery', 'Capacity, latency, concurrency, backpressure and cost bounds', 'Failure modes, timeouts, idempotency, retries and graceful degradation', 'Observability, incident ownership, runbooks, rollback and disaster recovery', 'AI evaluation, provenance, prompt injection, drift and human override', 'Dependency lifecycle, portability, test strategy and evolutionary path'],
    sources: [
      source('arch.nist.airmf', 'NIST', 'AI Risk Management Framework 1.0', 'https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10', 'US/global', 'voluntary_framework'),
      source('arch.nist.genai', 'NIST', 'AI 600-1 Generative AI Profile', 'https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf', 'US/global', 'voluntary_framework'),
      source('arch.ncsc.ai', 'UK NCSC', 'Guidelines for Secure AI System Development', 'https://www.ncsc.gov.uk/collection/guidelines-secure-ai-system-development/about-this-document', 'UK/global'),
      source('arch.owasp.agentic', 'OWASP', 'Top 10 for Agentic Applications 2026', 'https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/', 'global', 'informative'),
      source('arch.iso.25010', 'ISO', 'ISO/IEC 25010 systems and software quality models', 'https://www.iso.org/standard/78176.html', 'global', 'informative')
    ],
    disclaimer: 'Architecture review based on supplied evidence, not a load test, production readiness certification or security audit.'
  },
  {
    expertId: 'product_uniqueness',
    label: 'Product & Differentiation',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-08-18',
    jurisdictions: ['UK', 'EU', 'global'],
    remit: 'Test problem evidence, alternatives, meaningful difference, adoption, distribution and defensibility. Challenge novelty and moat claims without making legal IP conclusions.',
    exclusions: ['No patentability, freedom-to-operate or trade-mark clearance conclusion', 'No TAM invented from generic adoption data', 'No absence-of-results claim as proof of uniqueness'],
    hardTriggers: ['product, service, feature or launch proposal', 'unique, first, only, best, moat or defensible claim', 'competitor, substitute, market, positioning or go-to-market', 'product or brand name'],
    softTriggers: ['roadmap', 'switching costs', 'distribution', 'workflow advantage', 'agent orchestration as a moat'],
    coRoute: ['finance_commercial', 'ux_accessibility', 'legal_regulatory', 'technical_architecture'],
    rubric: ['Specific user, trigger, frequency, pain and consequence', 'Direct, adjacent, manual, bundled and do-nothing alternatives', 'Difference in measurable time, quality, risk or cost', 'Independent evidence and falsifiable claims', 'Switching trigger, trust, onboarding and time to value', 'Buyer, discovery, channel, sales cycle and platform dependence', 'Data, evaluation corpus, integration, trust, network and cost advantages', 'IP asset classification, search limits and professional handoff'],
    sources: [
      source('product.cma.market', 'CMA', 'Merger Assessment Guidelines: market and alternatives', 'https://www.gov.uk/government/publications/merger-assessment-guidelines/merger-assessment-guidelines-html-version', 'UK'),
      source('product.eu.market', 'European Commission', '2024 Market Definition Notice', 'https://eur-lex.europa.eu/eli/C/2024/1645/oj/eng', 'EU'),
      source('product.oecd.oslo', 'OECD/Eurostat', 'Oslo Manual 2018', 'https://www.oecd.org/en/publications/2018/10/oslo-manual-2018_g1g9373b.html', 'global', 'voluntary_framework'),
      source('product.gov.userneeds', 'UK Government', 'Start by learning user needs', 'https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs', 'UK'),
      source('product.ukipo.patent', 'UKIPO', 'Search for a patent', 'https://www.gov.uk/search-for-patent', 'UK', 'informative'),
      source('product.ukipo.tm', 'UKIPO', 'Search for a trade mark', 'https://www.gov.uk/search-for-trademark', 'UK', 'informative')
    ],
    disclaimer: 'Product-strategy critique and preliminary IP issue-spotting, not a novelty, patentability, infringement or clearance opinion.'
  },
  {
    expertId: 'writing_editorial',
    label: 'Writing, English Language & Editorial Quality',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-08-18',
    jurisdictions: ['UK', 'global'],
    remit: 'Review English-language prose for correctness, clarity, structure, audience fit and meaning risk. Use contemporary UK English by default while preserving the author\'s intent, voice, names, figures and necessary specialist language.',
    exclusions: ['Not a fact-checker or substantive domain adviser', 'Do not treat valid dialect, terminology or deliberate voice as an error', 'Do not polish raw voice-note disfluency unless editorial review is requested', 'Do not review code, tables or incidental labels as prose'],
    hardTriggers: ['explicit request for grammar, spelling, punctuation, syntax, clarity, tone, wording, editing, proofreading or UK English', 'draft prose explicitly submitted for editorial review', 'concrete ambiguity or language defect that could materially change meaning', 'public, safety-critical, consent or eligibility wording with a concrete reader risk'],
    softTriggers: ['named audience, channel, purpose or house style', 'publication or external submission', 'inconsistent terminology, jargon or unclear call to action', 'long-form prose where structure matters'],
    coRoute: ['evidence_research', 'ux_accessibility', 'legal_regulatory'],
    rubric: ['Grammar, spelling, punctuation and sentence boundaries', 'Syntax, modifier placement, referents, negation and modal ambiguity', 'Clarity, economy, precise verbs and accountable voice', 'Purpose, thesis, information order, paragraphs and transitions', 'Premises, contradictions, logical leaps and counterarguments', 'Claim calibration, qualification and visible evidence needs', 'Audience knowledge, medium, register and call to action', 'Tone, voice, respect and consistency', 'Plain language, expanded acronyms and inclusive wording', 'UK English, terminology, dates, numerals and house style', 'Smallest meaning-preserving revision and author confirmation'],
    sources: [
      source('writing.govuk.style', 'Government Digital Service', 'GOV.UK style guide', 'https://www.gov.uk/guidance/style-guide/a-to-z-of-gov-uk-style', 'UK'),
      source('writing.govuk.ui', 'Government Digital Service', 'Writing for user interfaces', 'https://www.gov.uk/service-manual/design/writing-for-user-interfaces', 'UK'),
      source('writing.cabinet.style', 'Cabinet Office', 'Functional Standards writing style guide', 'https://www.gov.uk/government/publications/handbook-for-standard-managers/functional-standards-writing-style-guide', 'UK'),
      source('writing.govs011', 'Cabinet Office', 'GovS 011: Communication', 'https://www.gov.uk/government/publications/government-functional-standard-govs-011-communication/government-functional-standard-govs-011-communications', 'UK', 'mandatory_in_scope'),
      source('writing.dfe.plain', 'Department for Education', 'Plain Language guidance', 'https://design.education.gov.uk/content-design/plain-language', 'UK'),
      source('writing.w3c.clear', 'W3C WAI', 'Clear Content', 'https://www.w3.org/WAI/curricula/content-author-modules/clear-content/', 'global', 'informative'),
      source('writing.iso24495', 'ISO', 'ISO 24495-1:2023 Plain language', 'https://www.iso.org/standard/78907.html', 'global', 'voluntary_framework')
    ],
    disclaimer: 'Editorial decision support using UK English by default, not fact-checking, legal advice, accessibility conformance or a substitute for an editor familiar with the audience and house style.'
  },
  {
    expertId: 'evidence_research',
    label: 'Evidence, Research & Fact Quality',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-10-18',
    jurisdictions: ['UK', 'global'],
    remit: 'Test whether claims are supported by suitable, traceable evidence and whether methods, uncertainty and limitations justify the conclusion.',
    exclusions: ['Do not invent or retrieve missing sources', 'Do not label a claim false merely because evidence is absent', 'Do not replace sector-specific statistical or scientific review'],
    hardTriggers: ['citation, study, survey, trial, experiment or dataset claim', 'statistics, causal inference, forecast evidence or research proves language', 'explicit fact-check, evidence quality or methodology question'],
    softTriggers: ['unsupported quantified claim', 'benchmark or comparison', 'sample, metric, evaluation or confidence claim'],
    coRoute: ['writing_editorial', 'finance_commercial', 'public_policy', 'product_uniqueness'],
    rubric: ['Exact claim, decision relevance and falsifiability', 'Primary source, provenance, date and traceability', 'Method, design, sampling and comparison group', 'Measurement validity, missing data and researcher degrees of freedom', 'Association versus causation and plausible alternatives', 'Effect size, uncertainty, sensitivity and subgroup stability', 'External validity, recency and population fit', 'Selective reporting, conflicts and publication bias', 'Replication, triangulation and contradictory evidence', 'Proportionate conclusion and smallest decisive validation step'],
    sources: [
      source('evidence.aquabook', 'HM Treasury', 'The Aqua Book: guidance on producing quality analysis for government', 'https://www.gov.uk/government/publications/the-aqua-book-guidance-on-producing-quality-analysis-for-government', 'UK'),
      source('evidence.magentabook', 'HM Treasury', 'The Magenta Book: central government guidance on evaluation', 'https://www.gov.uk/government/publications/the-magenta-book', 'UK'),
      source('evidence.uksa.code', 'UK Statistics Authority', 'Code of Practice for Statistics', 'https://code.statisticsauthority.gov.uk/', 'UK', 'mandatory_in_scope'),
      source('evidence.cochrane.grade', 'Cochrane', 'GRADE and assessing certainty of evidence', 'https://training.cochrane.org/handbook/current/chapter-14', 'global', 'voluntary_framework'),
      source('evidence.gov.analysis', 'Government Analysis Function', 'Analysis Function standards and guidance', 'https://analysisfunction.civilservice.gov.uk/policy-store/', 'UK'),
      source('evidence.greenbook', 'HM Treasury', 'The Green Book 2026', 'https://www.gov.uk/government/publications/the-green-book-appraisal-and-evaluation-in-central-government/the-green-book-2026', 'UK')
    ],
    disclaimer: 'Evidence-quality review only, not independent fact verification, peer review or specialist scientific, statistical, legal or financial advice.'
  },
  {
    expertId: 'health_wellbeing',
    label: 'Health, Sleep & Wellbeing',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-08-18',
    jurisdictions: ['UK', 'global'],
    remit: 'Challenge everyday health and wellbeing choices using proportionate, evidence-aware reasoning, especially sleep, fatigue, caffeine, alcohol, nicotine, symptoms, medicines and supplements. Identify plausible harm without diagnosing, prescribing or turning ordinary low-risk choices into emergencies.',
    exclusions: ['No diagnosis or personalised treatment', 'Never instruct someone to start, stop or alter medication', 'Do not infer pregnancy, disease, bedtime, caffeine dose or sensitivity', 'Distinguish ordinary self-care, pharmacist or GP advice, NHS 111 and 999'],
    hardTriggers: ['sleep timing, insomnia, fatigue or sleep quality', 'caffeine or another named stimulant with a plausible sleep consequence', 'a named symptom, condition, medicine, supplement or pregnancy', 'a request for personalised health or wellbeing guidance', 'a credible urgent health red flag'],
    softTriggers: ['energy and alertness', 'nutrition, alcohol, nicotine or exercise timing', 'recovery and bedtime routine', 'persistent impairment in daily functioning'],
    coRoute: ['evidence_research', 'ethics_societal', 'legal_regulatory'],
    rubric: ['Intended outcome and timing', 'Named food, drink, substance, medicine or behaviour', 'Sleep timing, duration, quality and next-day functioning', 'Dose, frequency and cumulative exposure without inventing quantities', 'Individual modifiers such as age, pregnancy, sensitivity, medicines and conditions', 'Known facts versus assumptions and missing context', 'Lower-risk alternatives, autonomy and reversibility', 'Persistent symptoms or impaired daily functioning', 'Urgent red flags and proportionate escalation', 'Proportionate severity without moralising ordinary choices'],
    sources: [
      source('health.nhs.insomnia', 'NHS', 'Insomnia', 'https://www.nhs.uk/conditions/insomnia/', 'UK'),
      source('health.nhs.fatigue', 'NHS', 'Self-help tips to fight tiredness', 'https://www.nhs.uk/live-well/sleep-and-tiredness/self-help-tips-to-fight-fatigue/', 'UK'),
      source('health.nhs.sleep-better', 'NHS Every Mind Matters', 'Fall asleep faster and sleep better', 'https://www.nhs.uk/every-mind-matters/mental-wellbeing-tips/how-to-fall-asleep-faster-and-sleep-better/', 'UK'),
      source('health.efsa.caffeine', 'European Food Safety Authority', 'Caffeine', 'https://www.efsa.europa.eu/en/topics/topic/caffeine', 'EU'),
      source('health.fsa.caffeine', 'Food Standards Agency', 'FSA and FSS issue guidance on caffeine in food supplements', 'https://www.food.gov.uk/news-alerts/news/fsa-and-fss-issue-guidance-on-caffeine-in-food-supplements', 'UK'),
      source('health.nice.sleepio', 'NICE', 'Sleepio to treat insomnia and insomnia symptoms', 'https://www.nice.org.uk/guidance/htg624/chapter/1-Recommendations', 'UK'),
      source('health.nhs.111', 'NHS', 'Get help for your symptoms', 'https://111.nhs.uk/', 'England'),
      source('health.nhs.999', 'NHS', 'When to call 999', 'https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/', 'UK')
    ],
    knowledge: [
      {
        id: 'health.sleep.caffeine-six-hours',
        statement: 'NHS insomnia guidance advises avoiding tea or coffee for at least six hours before going to bed.',
        sourceRefs: ['health.nhs.insomnia']
      },
      {
        id: 'health.sleep.caffeine-duration',
        statement: 'Caffeine is a stimulant that can disrupt sleep rhythms, and its effects can last for several hours.',
        sourceRefs: ['health.nhs.fatigue', 'health.nhs.sleep-better']
      },
      {
        id: 'health.sleep.caffeine-100mg',
        statement: 'EFSA reports that a single 100 mg caffeine dose may affect sleep duration and patterns in some adults, particularly when consumed close to bedtime.',
        sourceRefs: ['health.efsa.caffeine']
      },
      {
        id: 'health.sleep.variable-dose-sensitivity',
        statement: 'Caffeine content varies between products and people vary in sensitivity, so an exact effect cannot be inferred from the drink name alone.',
        sourceRefs: ['health.efsa.caffeine', 'health.fsa.caffeine']
      },
      {
        id: 'health.sleep.persistent-insomnia',
        statement: 'Persistent insomnia or sleep problems that affect daily life warrant assessment rather than repeated lifestyle guesswork alone.',
        sourceRefs: ['health.nhs.insomnia', 'health.nice.sleepio']
      },
      {
        id: 'health.triage.urgent',
        statement: 'Serious or life-threatening symptoms require urgent clinical help rather than ordinary lifestyle analysis.',
        sourceRefs: ['health.nhs.111', 'health.nhs.999']
      }
    ],
    disclaimer: 'General health and wellbeing decision support, not diagnosis, treatment or personalised medical advice. Seek a pharmacist or clinician for symptoms, pregnancy, conditions or medicines, and urgent help for serious symptoms.'
  },
  {
    expertId: 'delivery_operations',
    label: 'Delivery, Operations & Change',
    version: '2026.07.18', lastVerified: VERIFIED, reviewDue: '2026-10-18',
    jurisdictions: ['UK', 'global'],
    remit: 'Challenge whether a plan can be owned, sequenced, adopted, operated, supported, measured, rolled back and improved under realistic constraints.',
    exclusions: ['Do not invent capacity, dates or dependencies', 'Do not duplicate detailed architecture review', 'Do not certify operational readiness from a plan alone'],
    hardTriggers: ['roadmap, implementation plan, milestones, owners or dependencies', 'rollout, migration, operating model, support or change adoption', 'delivery confidence, readiness, acceptance criteria or rollback question'],
    softTriggers: ['resourcing', 'training', 'handover', 'service management', 'benefits realisation'],
    coRoute: ['technical_architecture', 'finance_commercial', 'ux_accessibility', 'public_policy'],
    rubric: ['Outcome, scope, constraints and explicit non-goals', 'Named owners, decision rights and escalation path', 'Dependencies, critical path, sequencing and lead times', 'Capacity, skills, suppliers and realistic contingency', 'Milestones, acceptance criteria and evidence of done', 'Pilot, rollout, migration, rollback and stop conditions', 'Operating model, support, incident ownership and handover', 'Stakeholder adoption, training, communications and resistance', 'Metrics, benefits, feedback loops and corrective action', 'Decommissioning, residual obligations and lessons learned'],
    sources: [
      source('delivery.govs002', 'UK Government', 'GovS 002: Project delivery', 'https://www.gov.uk/government/publications/project-delivery-functional-standard', 'UK', 'mandatory_in_scope'),
      source('delivery.service.agile', 'Government Digital Service', 'Agile delivery', 'https://www.gov.uk/service-manual/agile-delivery', 'UK'),
      source('delivery.service.reliable', 'Government Digital Service', 'Service Standard point 14: operate a reliable service', 'https://www.gov.uk/service-manual/service-standard/point-14-operate-a-reliable-service', 'UK'),
      source('delivery.orangebook', 'HM Treasury', 'The Orange Book: management of risk', 'https://www.gov.uk/government/publications/orange-book', 'UK', 'voluntary_framework'),
      source('delivery.routemap', 'Infrastructure and Projects Authority', 'Project Routemap', 'https://www.gov.uk/government/collections/improving-infrastructure-delivery-project-routemap', 'UK'),
      source('delivery.service.metrics', 'Government Digital Service', 'Measuring the performance of your service', 'https://www.gov.uk/service-manual/measuring-success/measuring-the-performance-of-your-service', 'UK')
    ],
    disclaimer: 'Delivery and operational challenge based on supplied evidence, not a readiness certification, detailed implementation plan or assurance opinion.'
  }
]

export const KNOWLEDGE_PACKS: ReadonlyMap<ExpertId, KnowledgePack> = new Map(
  packs.map((pack) => [pack.expertId, pack])
)

export function getKnowledgePack(expertId: ExpertId): KnowledgePack {
  const pack = KNOWLEDGE_PACKS.get(expertId)
  if (!pack) throw new Error(`Missing knowledge pack: ${expertId}`)
  return pack
}

export function listKnowledgePacks(): KnowledgePack[] {
  return [...KNOWLEDGE_PACKS.values()]
}
