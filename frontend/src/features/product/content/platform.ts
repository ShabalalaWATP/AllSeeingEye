/**
 * The Review, Workspaces, Trust and Deploy chapters. Each line maps to merged code or
 * documentation: watches (features/watches), alert routing (docs/ALERT_ROUTING.md,
 * docs/WEB_PUSH.md), exports (domain/report_documents.py, reports/stix.py), security
 * (docs/07_SECURITY_BY_DESIGN.md) and deployment (docs/01_ARCHITECTURE.md).
 */

export interface TimelineBeat {
  when: string;
  title: string;
  body: string;
}

export const REVIEW_TIMELINE: readonly TimelineBeat[] = [
  {
    when: 'Day 0',
    title: 'Assessment saved',
    body: 'Version 1 with its frozen evidence, grades, model details and status.',
  },
  {
    when: 'Day 2',
    title: 'Follow-up question',
    body: 'A new question inherits the evidence within the same scope.',
  },
  {
    when: 'Day 7',
    title: 'Subscription edition',
    body: 'Scheduled research compares the new edition with the last one.',
  },
  {
    when: 'Day 9',
    title: 'Alert rule fires',
    body: 'A watched indicator matches the live picture after its warm-up baseline.',
  },
  {
    when: 'Day 10',
    title: 'Version 2',
    body: 'Regenerated with a deterministic comparison against version 1.',
  },
  {
    when: 'Day 30',
    title: 'Forecast resolved',
    body: 'A reviewer records how the forecast turned out, kept as an append-only history.',
  },
];

export const WATCH_TYPES: readonly string[] = [
  'Subscriptions',
  'Alert rules',
  'Area watches',
  'Collection plans',
  'Research Briefs',
  'Annotation monitors',
];

export const ALERT_CHANNELS: readonly { label: string; detail: string }[] = [
  { label: 'In app', detail: 'Live stream and notification bell' },
  { label: 'Email', detail: 'Per alert or a daily digest' },
  { label: 'Webhook', detail: 'HTTPS endpoint you register' },
  { label: 'Web push', detail: 'Carries only an opaque identifier' },
  { label: 'Atom feed', detail: 'Private, per account' },
];

export const EXPORTS: readonly { format: string; detail: string }[] = [
  { format: 'PDF', detail: 'Formatted assessment' },
  { format: 'DOCX', detail: 'Editable report' },
  { format: 'Markdown', detail: 'Plain text' },
  { format: 'STIX 2.1', detail: 'With a TLP marking' },
  { format: 'Evidence ZIP', detail: 'Selected and claim evidence' },
  { format: 'GeoJSON / KML', detail: 'The live map picture' },
];

export interface Workspace {
  id: string;
  name: string;
  body: string;
  points: readonly string[];
  accent: string;
}

export const WORKSPACES: readonly Workspace[] = [
  {
    id: 'monitoring',
    name: 'Live monitoring',
    accent: '#ff5a5a',
    body: 'Focused trackers for conflict, hazards, aviation, maritime, space and public figures.',
    points: [
      'Per-domain filters',
      'Source health beside every feed',
      'Ops room playlist for wall screens',
    ],
  },
  {
    id: 'ukraine',
    name: 'Ukraine',
    accent: '#f5b53f',
    body: 'A dedicated workspace for the war: datasets, official statements and a fortnightly digest.',
    points: [
      'Reported losses and casualties datasets',
      'Official channels in one place',
      'Cited digest every two weeks',
    ],
  },
  {
    id: 'cyber',
    name: 'Cyber intelligence',
    accent: '#22d3ee',
    body: 'Exploited vulnerabilities, ransomware claims, advisories and connectivity signals with a cited briefing.',
    points: ['National CERT advisories', 'MITRE ATT&CK context', 'GPS and GNSS interference'],
  },
  {
    id: 'economy',
    name: 'Economy',
    accent: '#6ee7b7',
    body: 'Official statistics and central bank series, compared across countries with a plain-English explainer.',
    points: ['Country comparison', 'Market charts', 'Briefing for any date window'],
  },
  {
    id: 'geolocation',
    name: 'Photo geolocation',
    accent: '#a78bfa',
    body: 'Candidate locations from an image, then a sun and shadow check against the capture time.',
    points: ['Vision model candidates', 'Shadow geometry check', 'Saved assessments'],
  },
  {
    id: 'teams',
    name: 'Teams',
    accent: '#ff6f37',
    body: 'Personal and team scopes, a team board with mentions, invitations and shared research.',
    points: [
      'Access follows current membership',
      'Team AI usage and allowances',
      'Archived teams stay readable',
    ],
  },
];

export interface TrustLayer {
  id: string;
  name: string;
  controls: readonly string[];
}

export const TRUST_LAYERS: readonly TrustLayer[] = [
  {
    id: 'edge',
    name: 'Edge',
    controls: [
      'Caddy edge with TLS and security headers',
      'Strict content security policy',
      'Request size limits per route',
    ],
  },
  {
    id: 'identity',
    name: 'Identity',
    controls: [
      'Argon2id passwords',
      'MFA by email or authenticator, required for administrators',
      'Rotating refresh tokens with family revocation',
    ],
  },
  {
    id: 'policy',
    name: 'Policy',
    controls: [
      'Object-level authorisation for personal and team work',
      'Sessions re-checked before results are released',
      'Append-only audit log',
    ],
  },
  {
    id: 'data',
    name: 'Data',
    controls: [
      'Raw live events never written to the database',
      'Isolated document parser with no network and no secrets',
      'Encrypted provider keys, never returned by the API',
    ],
  },
];

export const AI_CHOICES: readonly string[] = [
  'OpenAI-compatible endpoints, including models you host',
  'Native Amazon Bedrock in your own AWS account and region',
  'Research tiers and token allowances per person, team and site',
  'No bundled model and no AI account needed to browse the map',
];

export const ENGINEERING: readonly string[] = [
  'Strict typing on both backend and frontend',
  'Layered architecture enforced by import contracts',
  'A 90 percent test coverage gate',
  'Dependency auditing and secret scanning in CI',
  'Work to WCAG 2.2 AA accessibility',
];

export const LIMITS_TEXT: readonly string[] = [
  'Public sources are incomplete and sometimes delayed, blocked or unavailable.',
  'Country-level locations are not exact event coordinates.',
  'Calculated satellite positions are not direct observations.',
  'Similar reports may share one original source and are not independent confirmation.',
  'A source grade, a model answer or a passing check does not make a claim true.',
];

export const ARCHITECTURE: readonly { id: string; name: string; detail: string }[] = [
  { id: 'caddy', name: 'Caddy', detail: 'TLS, headers and static app' },
  { id: 'api', name: 'API', detail: 'FastAPI, feeds and research' },
  { id: 'db', name: 'PostgreSQL', detail: 'Reports, evidence, accounts' },
  { id: 'parser', name: 'Parser', detail: 'Isolated, no network' },
  { id: 'ai', name: 'Your AI provider', detail: 'OpenAI-compatible or Bedrock' },
];
