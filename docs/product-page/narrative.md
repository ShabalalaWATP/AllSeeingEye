# Narrative and copy

Status: draft for Alex's approval, 18 October 2026. Every quotation below is the
copy as built. Paths are relative to `frontend/src/features/product/`. Where copy
is assembled from data (counts, lists), the rendered result is shown in brackets.

The page order is set in `ProductStory.tsx`: Hero, Observe, Tools, Sources, Ask,
Collect, Assess, Review, Workspaces, Trust, Deploy, Contact, then the footer. The
header navigation (`content/chapters.ts`) links nine of them: Observe, Sources,
Ask, Collect, Assess, Review, Workspaces, Trust and Deploy. The page title is "The
All Seeing Eye · Self-hosted open-source intelligence" and the description "Observe
public signals on a living globe, research bounded questions and keep evidenced,
graded assessments on infrastructure you control." (`content/chapters.ts`).

## 0. Hero: the Eye opens

Source: `chapters/HeroChapter.tsx`.

**Headline:** "The All Seeing Eye." (eyebrow "Open-source intelligence · self-hosted").

**Explanation:** "Watch the world's public signals on a living globe, ask a bounded
question and get an assessment that shows the selected evidence, grades and doubts
behind each judgement. On your own infrastructure, with the AI provider you choose."

**Supporting points** (the "At a glance" counts, computed from content modules):

- "15 map layers" (`STORY_LAYERS.length`).
- "400+ catalogued sources" (`SOURCE_TOTAL` of 423, rounded down to the hundred).
- "11 intelligence topics" (`SOURCE_TOPICS.length`).
- "7 probability bands" (a literal 7).

Calls to action: "Talk to us" (to `#contact`) and "See how it works" (to `#observe`).

## 1. Observe

Source: `chapters/ObserveChapter.tsx`, `content/observe.ts`, labels and
descriptions from `lib/mapLayerDirectory.ts`.

**Headline:** "One picture of a noisy world." (eyebrow "01 · Observe").

**Explanation:** "[8] live layers and [7] reference layers on a 3D globe or flat map,
each with its own filters and source details."

**Supporting points** (the layer list; each row shows the directory description,
an illustrative count and the layer's filters):

- Live layers: Conflict & unrest, Natural hazards, Fires and thermal detections,
  News and context, Cyber incidents, Space, Flights, Boats.
- Reference layers: Public cameras, Technology & communications, Infrastructure,
  Public figures, Conflict regions, GPS and GNSS interference, British National Grid.
- Each row: "[n] illustrative [points, routes, satellites, cells or zones] on this globe".
- Globe label: "An illustrative globe showing each map layer appear in turn.
  Synthetic data." with the chip "Illustrative data".

## 1b. Filters and tools

Source: `chapters/ToolsChapter.tsx`, `content/observe.ts`, `lib/mapLayerDirectory.ts`.

**Headline:** "Cut the picture down to what matters." (eyebrow "Filters and tools").

**Explanation:** "Filter by time, place, location quality or a collection plan, replay
the retained hours one hour at a time, then measure, draw and plan on the same map."

**Supporting points:**

- "Event time": "1 h", "6 h", "24 h", "72 h", "7 d", "All", "Hour by hour replay".
- "Location quality": "Source-reported exact", "Approximate", "Propagated satellite",
  "Not plotted".
- "Focus": "Find nation", "Collection plan requirements", "Research area"; "View":
  "3D globe", "2D map", "Daily NASA imagery", "Day and night".
- 17 tool cards: the eight "Map setup" and nine "Planning tools" entries of the
  directory, from "Map style" to "Nuclear effects (education)".

## 2. Sources

Source: `chapters/SourcesChapter.tsx`, `content/sources.ts`.

**Headline:** "Hundreds of sources, organised by topic." (eyebrow "02 · Sources").

**Explanation:** "[263] scheduled feeds and [160] on-demand research connectors across
eleven topics, from seismology to sanctions. Each record keeps its source and
collection time; licence notes, where a source has them, stay with that source in the
catalogue."

**Supporting points:**

- Orbit core: "[423] sources"; eleven topic rows, each "[n] scheduled · [n] on demand"
  with representative providers. Scheduled figures are the live feed connectors built
  with no keys, recounted on 18 October 2026 (see the
  [recount](claims-register.md#source-catalogue-recount)).
- "Scheduled feeds": "Public feeds and APIs polled on their own cadence into a bounded
  live store that is never written to the database."
- "On-demand research" and "Reference data": "Connectors that run only when a question
  needs them: registries, filings, advisories, multilingual news and more." and
  "Packaged datasets for context: infrastructure registers, aircraft types, public
  figures and country boundaries."
- "Your own material": "Private documents and media (TXT, CSV, JSON, PDF, DOCX, images
  and video keyframes) added to a single question."

Footnote: "Counts describe the catalogue in this release. Some sources need keys,
accounts or licence acknowledgements, and a catalogue entry is not a promise that a
provider is available."

## 3. Ask

Source: `chapters/AskChapter.tsx`, `content/research.ts`.

**Headline:** "Start with a question, not a search box." (eyebrow "03 · Ask").

**Explanation:** "Every run has an explicit scope: places, dates, languages, sources, a
report template and a depth. Scope is what keeps the collection honest and the
assessment checkable. Saved Research Briefs keep explicit requirements for reuse, and
supported private documents and media are another input route."

**Supporting points** (four of the seven ticked features):

- "Ten report templates, from intelligence summaries to disaster SITREPs".
- "Twenty research presets and saved Research Briefs".
- "Area research from a polygon drawn on the map"; "Company, domain, document and
  media focus"; "Query translation and transliteration across languages".
- "Photo geolocation with a sun and shadow check"; "Private documents and media as
  inputs, analysed by your configured AI provider".

Console: the question "What is driving the recent fall in commercial shipping through
the Bab el-Mandeb strait?", six scope chips (Area "Drawn on the map", Region "Red Sea
and Gulf of Aden", Countries "Yemen · Djibouti · Eritrea", Window "Last 14 days",
Languages "English · Arabic", Template "Maritime activity report") and three depths:
"Basic 750 to 1,350 words, 24 evidence items", "Deep 1,800 to 3,000 words, 48 evidence
items", "Advanced 3,750 to 6,000 words, 80 evidence items". Footnote: "Illustrative
request. Nothing is sent from this page."

## 4. Collect

Source: `chapters/CollectChapter.tsx`, `content/research.ts`.

**Headline:** "Evidence with a receipt, and gaps you can see." (eyebrow "04 · Collect").

**Explanation:** "Connectors fan out across the scope. Each record comes back with its
source and a grade. Collection receipts record which providers ran, including empty
and unavailable ones, and requirements without enough support stay visible as gaps
rather than papered over."

**Supporting points:**

- "Similar reports may share one original source, so copies are grouped rather than
  counted as extra confirmation."
- "Source reliability A to F" and "Information credibility 1 to 6".
- "F and 6 mean the source or claim cannot yet be judged. New research material without
  an assessed source basis stays unassessed."
- Six example cards (grades B2, A2, C3, B3, F6 and one "Gap": "No independent satellite
  confirmation found"). Footnote: "Illustrative evidence: example sources, grades and
  receipts."

## 5. Assess

Source: `chapters/AssessChapter.tsx`, `content/research.ts`.

**Headline:** "Judgements you can trace, challenge and defend." (eyebrow "05 · Assess").

**Explanation:** the chapter has no lead paragraph. The example report carries it:
title "Shipping through the Bab el-Mandeb strait", "Maritime activity report ·
Confidence stated per judgement", "Deep research · Model: your configured provider ·
AI-assisted assessment", status "Ready", three judgements, each labelled with its
likelihood and confidence ("Highly likely · Moderate confidence", "Likely · Moderate
confidence" with "Challenged: confidence held at moderate.", "Realistic possibility ·
Low confidence"), the alternative
explanation and the closing chips "Saved as version 1", "Follow-up question in the
same scope", "Regenerate as version 2 and compare". Footnote: "Illustrative report. It
is static text, never generated here."

**Supporting points** (the "Analytic standards" section; four of seven ticks):

- The seven PHIA bands, "Remote chance" to "Almost certain"; "Probability language
  checked against the PHIA yardstick".
- "High, moderate or low confidence, capped by the evidence".
- "Citation, entailment and contradiction checks"; "Challenge pass and devil's
  advocacy on the top judgement".
- "Alternative hypotheses, assumptions and information gaps"; "Claims ledger with
  identities and relationships to review"; "Exact calculations with formula receipts".

## 6. Review

Source: `chapters/ReviewChapter.tsx`, `content/platform.ts`.

**Headline:** "An assessment is the start of the work, not the end." (eyebrow "06 · Review").

**Explanation:** "Saved research keeps its evidence frozen, its versions comparable and
its forecasts accountable, while watches keep collecting in the background."

**Supporting points:**

- Timeline: Day 0 "Assessment saved", Day 2 "Follow-up question", Day 7 "Subscription
  edition", Day 9 "Alert rule fires", Day 10 "Version 2", Day 30 "Forecast resolved".
- "Six ways to keep watching": Subscriptions, Alert rules, Area watches, Collection
  plans, Research Briefs, Annotation monitors.
- Alert channels on the phone: "In app" (live stream and notification bell), "Email"
  (per alert or a daily digest), "Webhook" (HTTPS endpoint you register), "Web push"
  (carries only an opaque identifier), "Atom feed" (private, per account).
- "Take it anywhere": PDF, DOCX, Markdown, "STIX 2.1" with a TLP marking, "Evidence
  ZIP", "GeoJSON / KML" (the live map picture). "Personal or team work": "Access always
  follows current membership: leaving a team ends access to its work."

## 7. Specialist workspaces

Source: `chapters/WorkspacesChapter.tsx`, `content/platform.ts`.

**Headline:** "Specialist workspaces for specialist questions." (eyebrow "07 · Go deeper").

**Explanation:** no lead paragraph; seven numbered panels, each with up to two
sentences, three points and one limit.

**Supporting points** (panel names and bodies):

- "Live monitoring": "Focused trackers for conflict, hazards, aviation, maritime, space
  and public figures." Points: "A daily briefing on the monitor page", "Conflict source
  coverage and health", "Ops room playlist for wall screens". "Ukraine": "A dedicated workspace for the war: datasets, official
  statements and a fortnightly digest."
- "Cyber intelligence": "Exploited vulnerabilities, ransomware claims, advisories and
  connectivity signals with a cited briefing." "Economy": "Official statistics and
  central bank series, compared across five countries with explanations of unfamiliar
  measures." Points: "Five-country comparison", "Market charts after consent",
  "Briefings over 2 to 14 days".
- "Photo geolocation": "Candidate locations from an image, then a sun and shadow check
  against the capture time." (with the only workspace screenshot, captioned
  "Illustrative screenshot").
- "Map tools" (drawing collections, radio studies, terrain profiles) and "Teams":
  "Personal and team scopes, a team board with mentions, invitations and shared research."

Limits on the panels are listed in [honest-limits.md](honest-limits.md#workspace-limits).

## 8. Trust and control

Source: `chapters/TrustChapter.tsx`, `content/platform.ts`.

**Headline:** "Your server. Your model. Your rules." (eyebrow "08 · Trust and control").

**Explanation:** "The All Seeing Eye runs on infrastructure you control, talks to the
AI provider you choose and treats every byte from the internet, every feed item and
every model response as untrusted."

**Supporting points:**

- Four layers: Edge (Caddy, "A content security policy allowing only same-origin
  scripts", request size limits), Identity (Argon2id, MFA,
  rotating refresh tokens), Policy (object-level authorisation, session re-checks,
  append-only audit log), Data (raw live events, isolated parser, encrypted keys).
- Data minimisation footnote: "The database keeps reports, frozen evidence, accounts,
  teams, configuration and small operational records. Raw live events stay in a
  bounded memory store, with one disposable snapshot file for restarts, and never enter
  the database."
- "Bring your own AI": OpenAI-compatible endpoints including self-hosted models, native
  Amazon Bedrock, research tiers and token allowances, "No bundled model and no AI
  account needed to browse the map".
- "Engineered with care": strict typing, import contracts, "A 90 percent test coverage
  gate", dependency auditing and secret scanning, "Work to WCAG 2.2 AA accessibility",
  with the footnote "Practices, not a security certification." Then "What it will not
  pretend" (see [honest-limits.md](honest-limits.md)).

## 9. Deploy

Source: `chapters/DeployChapter.tsx`, `content/platform.ts`.

**Headline:** "One server you run. Your database stays on it." (eyebrow "09 · Deploy").

**Explanation:** "A Docker Compose stack on a single Linux server: Caddy at the edge, the
API, PostgreSQL and an isolated document parser. Questions and selected evidence go to
the AI provider you configure, links cited by saved reports go to the Internet Archive
unless you turn that off, and email, push and webhooks are optional."

**Supporting points:**

- Diagram nodes: Browser, Caddy ("TLS, headers and static app"), API ("FastAPI, feeds
  and research"), PostgreSQL ("Reports, evidence, accounts"), Parser ("Isolated, no
  network"), Public sources, "Your AI provider" ("OpenAI-compatible or Bedrock"),
  "Email service" ("Optional, SMTP with TLS").
- The boundary label "Your server · Docker Compose".
- "What would it cost to run?": in production builds, "Running costs depend on your
  team size, research volume and AI provider. We will estimate them with you, including
  the server and model usage you can expect." Development builds show the draft
  estimator instead.

## 10. Talk to us

Source: `chapters/ContactChapter.tsx`, `enquiry/EnterpriseEnquiryForm.tsx`.

**Headline:** "Bring The All Seeing Eye inside your organisation." (eyebrow "10 · Talk to us").

**Explanation:** "Tell us about your team, where it needs to run and the questions you
need answered. We will help you plan the deployment, connect your AI provider and
choose sources whose terms fit your use."

**Supporting points:** buttons "Request access" (to `/request-account`) and "Sign in";
when the installation accepts enquiries, the form "Enquire about self-hosting" with
"Please do not include passwords or sensitive research." and a privacy notice check.

Footer (`ProductStory.tsx`): "The All Seeing Eye. Self-hosted open-source intelligence."
and "Globe outlines from Natural Earth (public domain). Scenes, questions and reports on
this page are illustrative and use no live data."

## Copy issues for review

Items 1 to 10 of the first review, and the content security policy half of item 11,
were fixed in the copy on 18 October 2026 (hero evidence wording, hour-by-hour replay,
licence notes, the per-topic source split, collection gaps, unassessed material,
per-judgement confidence, the Live monitoring and Economy points, the Deploy headline
and lead, and the CSP line); the claims register shows each row's new status and
`content/productContent.unit.test.ts` keeps the old wording out. These remain open:

1. **Trust, WCAG** (`content/platform.ts`): "Work to WCAG 2.2 AA accessibility" is an
   aim with no conformance audit, and the accessibility statement (KAN-193) is not
   published. Kept as an aim; suggest "Built towards WCAG 2.2 AA; not independently
   audited" if Alex wants it explicit.
2. **Contact, promise of help** (`chapters/ContactChapter.tsx`): "We will help you plan
   the deployment, connect your AI provider and choose sources whose terms fit your
   use" is a service commitment. It depends on Alex's KAN-164 offer decision (ADR 0023,
   proposed).
3. **Ask, area chip** (`content/research.ts`): "Area: Drawn on the map" alongside
   region, countries, languages and template is a composite. Area research is a
   separate flow (`docs/AREA_RESEARCH.md`). Either label the console as a composite or
   drop the area chip.

Lower priority, wording only: "defend" in the Assess headline and "every byte" in the
Trust lead are rhetorical absolutes; the Day 9 timeline beat's "after its warm-up
baseline" applies only to relative alert rules; "Ready" on the example report means
automated checks passed, not human approval; "Take it anywhere" mixes report exports
with the GeoJSON and KML map export. No em dashes were found in the product copy, and
the restricted-source names test (`content/productContent.unit.test.ts`) covers both
the content modules and the chapter files.
