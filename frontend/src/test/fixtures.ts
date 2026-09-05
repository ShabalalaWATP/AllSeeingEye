import type { LiveEvent, Source, SourceHealth, StoreStats } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import type { LlmProfile } from '@/lib/api/llm';
import type { Report, ReportSummary, ReportTemplate } from '@/lib/api/reports';
import type { AccountRequest, AuditEntry, TokenResponse, User } from '@/lib/api/schemas';
import type { ConflictCard, ConflictDetail, HazardCard, HazardDetail } from '@/lib/api/trackers';

export const ADMIN_TOKEN = 'admin-access-token';
export const USER_TOKEN = 'user-access-token';
export const CSRF_VALUE = 'csrf-test-value';
export const ADMIN_PASSWORD = 'correct-horse-battery-staple';
export const USER_PASSWORD = 'another-long-passphrase';
export const ACTIVATION_LINK = 'http://localhost:3000/activate?token=activation-token-123';
export const RESET_LINK = 'http://localhost:3000/reset-password?token=reset-token-456';
export const GOOD_TOKEN = 'good-token';
export const BAD_TOKEN = 'bad-token';
export const WEAK_PASSWORD = 'password12345';
export const WEAK_PASSWORD_REASON = 'This password is among the most common and cannot be used.';

export const adminUser: User = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'admin@example.com',
  display_name: 'Ada Admin',
  role: 'admin',
  is_active: true,
  created_at: '2026-09-01T10:00:00Z',
  last_login_at: '2026-09-04T09:00:00Z',
};

export const plainUser: User = {
  id: '22222222-2222-4222-8222-222222222222',
  email: 'user@example.com',
  display_name: 'Uma User',
  role: 'user',
  is_active: true,
  created_at: '2026-09-02T10:00:00Z',
  last_login_at: null,
};

export function tokenFor(user: User): TokenResponse {
  return {
    access_token: user.role === 'admin' ? ADMIN_TOKEN : USER_TOKEN,
    token_type: 'bearer',
    expires_in: 900,
    user,
  };
}

export const pendingRequests: AccountRequest[] = [
  {
    id: '33333333-3333-4333-8333-333333333333',
    email: 'newcomer@example.com',
    display_name: 'Nia Newcomer',
    reason: 'Analyst on the regional desk.',
    status: 'pending',
    created_at: '2026-09-03T12:00:00Z',
  },
  {
    id: '44444444-4444-4444-8444-444444444444',
    email: 'second@example.com',
    display_name: 'Sam Second',
    reason: null,
    status: 'pending',
    created_at: '2026-09-03T13:00:00Z',
  },
];

export function auditEntry(id: number, action: string): AuditEntry {
  return {
    id,
    at: '2026-09-04T08:00:00Z',
    actor_user_id: adminUser.id,
    action,
    subject: 'user@example.com',
    ip: '127.0.0.1',
    details: id % 2 === 0 ? {} : { note: `entry ${id}` },
  };
}

export const auditPageOne: AuditEntry[] = [
  auditEntry(120, 'login_succeeded'),
  auditEntry(119, 'user_updated'),
  auditEntry(118, 'account_request_approved'),
];

export const auditPageTwo: AuditEntry[] = [
  auditEntry(50, 'logout'),
  auditEntry(49, 'login_failed'),
];

/** A located, graded live event; override fields per test. */
export function liveEvent(overrides: Partial<LiveEvent> = {}): LiveEvent {
  return {
    id: 'e1',
    source_id: 'usgs_earthquakes',
    category: 'disaster',
    subtype: 'earthquake',
    title: 'M4.2 near Somewhere',
    summary: 'Depth 10 km.',
    url: 'https://example.com/e1',
    published_at: '2026-09-05T00:00:00Z',
    observed_at: '2026-09-05T00:01:00Z',
    language: 'en',
    title_en: null,
    point: { lon: 10, lat: 50 },
    geo_confidence: 'exact',
    country_iso: 'DE',
    tags: ['earthquake'],
    severity: 0.5,
    reliability: 'A',
    credibility: 2,
    grade: 'A2',
    grade_rationale: 'Instrument data',
    story_id: null,
    attributes: { magnitude: 4.2 },
    ...overrides,
  };
}

export const liveEvents: LiveEvent[] = [
  liveEvent(),
  liveEvent({
    id: 'e2',
    source_id: 'cisa_kev',
    category: 'cyber',
    subtype: 'kev',
    title: 'CVE-2026-0001 added to KEV',
    summary: null,
    url: null,
    point: null,
    geo_confidence: 'none',
    published_at: '2026-09-04T12:00:00Z',
    tags: [],
    severity: null,
    reliability: 'B',
    credibility: 1,
    grade: 'B1',
    attributes: {},
  }),
];

export const storeStats: StoreStats = {
  total: 2,
  estimated_bytes: 4096,
  budget_bytes: 1_048_576,
  per_category: [
    {
      category: 'disaster',
      count: 1,
      oldest: '2026-09-05T00:00:00Z',
      newest: '2026-09-05T00:00:00Z',
    },
    { category: 'cyber', count: 1, oldest: '2026-09-04T12:00:00Z', newest: '2026-09-04T12:00:00Z' },
  ],
};

export const countries: Country[] = [
  {
    iso2: 'GB',
    iso3: 'GBR',
    name: 'United Kingdom',
    bounds: [-7.6, 49.9, 1.8, 58.6],
    centroid: [-2.9, 54.3],
  },
  {
    iso2: 'UA',
    iso3: 'UKR',
    name: 'Ukraine',
    bounds: [22.1, 44.4, 40.2, 52.4],
    centroid: [31.2, 48.4],
  },
  {
    iso2: 'RU',
    iso3: 'RUS',
    name: 'Russia',
    bounds: [-180, 41.2, 180, 81.9],
    centroid: [97.7, 61.5],
  },
];

export function sourceHealth(overrides: Partial<SourceHealth> = {}): SourceHealth {
  return {
    source_id: 'usgs_earthquakes',
    status: 'healthy',
    last_success: '2026-09-05T00:00:00Z',
    last_error: null,
    last_error_at: null,
    consecutive_failures: 0,
    items_last_poll: 12,
    last_latency_ms: 210,
    next_poll_at: '2026-09-05T00:05:00Z',
    polls: 3,
    ...overrides,
  };
}

export function source(overrides: Partial<Source> = {}): Source {
  return {
    id: 'usgs_earthquakes',
    name: 'USGS earthquakes',
    organisation: 'USGS',
    category: 'disaster',
    kind: 'geojson',
    url: 'https://earthquake.usgs.gov/feed.geojson',
    reliability: 'A',
    poll_interval_seconds: 300,
    language: 'en',
    licence_note: 'Public domain',
    homepage: 'https://earthquake.usgs.gov',
    requires_key: false,
    instrument: true,
    flags: [],
    health: sourceHealth(),
    ...overrides,
  };
}

export const sources: Source[] = [
  source(),
  source({
    id: 'gdacs',
    name: 'GDACS disaster alerts',
    organisation: 'EC JRC and UN OCHA',
    kind: 'rss',
    poll_interval_seconds: 600,
    instrument: false,
    health: sourceHealth({
      source_id: 'gdacs',
      status: 'degraded',
      last_success: '2026-09-04T22:00:00Z',
      last_error: 'HTTP 503 from https://www.gdacs.org/xml/rss.xml',
      last_error_at: '2026-09-05T00:01:00Z',
      consecutive_failures: 3,
      items_last_poll: 0,
      last_latency_ms: null,
      polls: 9,
    }),
  }),
  source({
    id: 'tass_en',
    name: 'TASS English',
    organisation: 'TASS',
    category: 'news',
    kind: 'rss',
    reliability: 'C',
    poll_interval_seconds: 1800,
    instrument: false,
    flags: ['state_controlled'],
    health: sourceHealth({
      source_id: 'tass_en',
      status: 'idle',
      last_success: null,
      items_last_poll: 0,
      last_latency_ms: null,
      next_poll_at: null,
      polls: 0,
    }),
  }),
];

export const llmProfiles: LlmProfile[] = [
  {
    id: '55555555-5555-4555-8555-555555555555',
    name: 'Local Llama',
    base_url: 'http://localhost:11434/v1',
    model: 'llama3.1:8b',
    api_key_hint: '1234',
    roles: ['assessment', 'direction'],
    max_output_tokens: 2000,
    temperature: 0.1,
    enabled: true,
    created_at: '2026-09-05T01:00:00Z',
    updated_at: '2026-09-05T01:00:00Z',
  },
];

export const reportTemplates: ReportTemplate[] = [
  {
    id: 'intsum',
    title: 'Intelligence summary',
    purpose: 'A periodic summary of what happened in the scope and what it means.',
    needs_country: false,
    needs_question: false,
    needs_conflict: false,
    needs_hazard: false,
    window_hours: 48,
  },
  {
    id: 'ask',
    title: 'Ask the Eye',
    purpose: 'A free-form question answered from the live evidence, judgements first.',
    needs_country: false,
    needs_question: true,
    needs_conflict: false,
    needs_hazard: false,
    window_hours: 72,
  },
  {
    id: 'conflict_assessment',
    title: 'Conflict assessment',
    purpose: 'One curated conflict: recent activity, assessed courses of action and warning.',
    needs_country: false,
    needs_question: false,
    needs_conflict: true,
    needs_hazard: false,
    window_hours: 168,
  },
  {
    id: 'disaster_sitrep',
    title: 'Disaster SITREP',
    purpose: "One hazard's current picture.",
    needs_country: false,
    needs_question: false,
    needs_conflict: false,
    needs_hazard: true,
    window_hours: 72,
  },
];

export const reportSummary: ReportSummary = {
  id: '88888888-8888-4888-8888-888888888888',
  template: 'intsum',
  title: 'Intelligence summary: Ukraine',
  scope: { country: 'UA', categories: [], question: null, window_hours: 48 },
  period_from: '2026-09-03T01:00:00Z',
  period_to: '2026-09-05T01:00:00Z',
  status: 'ready',
  created_by: plainUser.id,
  created_at: '2026-09-05T01:00:00Z',
  latest_version: 1,
};

export const report: Report = {
  report: reportSummary,
  version: {
    number: 1,
    status: 'ready',
    body: {
      key_judgements: [
        {
          id: 'KJ1',
          statement: 'We assess it is highly likely that fighting around Kharkiv will intensify.',
          probability: 'highly_likely',
          confidence: 'moderate',
          confidence_statement: 'Two independent organisations; volatile front.',
          supporting_evidence: ['E1', 'E2'],
          contradicting_evidence: [],
          assumptions: ['A1'],
          change_from_previous: null,
          indicators: ['Reinforcements on the northern road'],
        },
      ],
      reporting: [
        {
          theme: 'Ground activity',
          items: [{ text: 'Shelling was reported overnight.', evidence: ['E1'], grade: 'B2' }],
        },
      ],
      assessment: [{ heading: 'Trajectory', text: 'The front is active.', evidence: ['E1'] }],
      assumptions: [{ id: 'A1', text: 'Supply lines stay open.', lynchpin: true }],
      alternative_hypotheses: [
        { text: 'A local pause.', why_less_likely: 'No mediator is active.', evidence: ['E2'] },
      ],
      indicators_and_warning: { watch_condition: 'elevated', changes: ['More hotspots'] },
      gaps: [{ text: 'No reporting on the eastern road.', eei: 'EEI-1' }],
      collection_recommendations: ['Task FIRMS review.'],
      sourcing_statement: 'Two independent organisations; syndicated copies counted once.',
    },
    findings: [
      {
        rule: 'citation',
        severity: 'warning',
        location: 'KJ1',
        message: 'Unknown evidence E9 removed',
      },
    ],
    evidence: [
      {
        label: 'E1',
        event_id: 'e1',
        source_id: 'bbc_world',
        source_name: 'BBC News World',
        category: 'conflict',
        title: 'Shelling in Kharkiv',
        summary: 'Overnight shelling.',
        url: 'https://example.org/e1',
        published_at: '2026-09-04T22:00:00Z',
        grade: 'B2',
        grade_rationale: 'Corroborated by Al Jazeera English (40 min later)',
        country_iso: 'UA',
        flags: [],
        archive_url: 'https://web.archive.org/web/20260905000000/https://example.org/e1',
      },
      {
        label: 'E2',
        event_id: 'e2',
        source_id: 'tass_en',
        source_name: 'TASS English',
        category: 'news',
        title: 'Ministry statement',
        summary: null,
        url: 'javascript:alert(1)',
        published_at: '2026-09-04T20:00:00Z',
        grade: 'C3',
        grade_rationale: 'State-controlled outlet, uncorroborated',
        country_iso: 'RU',
        flags: ['state_controlled'],
        archive_url: null,
      },
    ],
    quality: { items: 2, confidence_ceiling: 'moderate' },
    markdown: '# Intelligence summary: Ukraine\n\n## Key judgements',
    model: 'llama3.1:8b',
    prompt_tokens: 1200,
    completion_tokens: 600,
    latency_ms: 8123.4,
    attempts: 1,
    created_at: '2026-09-05T01:00:00Z',
    direction: null,
    devils_advocacy: null,
  },
};

const quake = liveEvent({ id: 'q1', title: 'M6.1 quake', severity: 0.9, country_iso: 'JP' });

export const hazardCard: HazardCard = {
  hazard: 'earthquake',
  title: 'Earthquakes',
  activity: { last_24h: 1, last_7d: 3, previous_7d: 1, trend: 3.0 },
  red_alerts: 1,
  max_severity: 0.9,
  countries: ['JP', 'ID'],
  latest: quake,
  top: quake,
};

export const hazardDetail: HazardDetail = {
  card: hazardCard,
  timeline: Array.from({ length: 14 }, (_, index) => ({
    day: `2026-08-${String(23 + index).padStart(2, '0')}`.replace('2026-08-32', '2026-09-01'),
    count: index === 13 ? 3 : 0,
    max_severity: index === 13 ? 0.9 : null,
  })),
  events: [quake, liveEvent({ id: 'q2', title: 'M4.5 quake', severity: 0.3, country_iso: 'JP' })],
};

const shelling = liveEvent({
  id: 'k1',
  source_id: 'gdelt_events',
  category: 'conflict',
  subtype: 'battle',
  title: 'Shelling in Kharkiv',
  point: { lon: 36.2, lat: 49.9 },
  country_iso: 'UA',
  grade: 'C3',
  severity: 0.7,
});

export const conflictCard: ConflictCard = {
  conflict: {
    id: 'ukraine',
    name: "Russia's war in Ukraine",
    status: 'war',
    countries: ['UA'],
    bbox: [22, 44, 41, 52.5],
    belligerents: ['Russia', 'Ukraine'],
    keywords: ['Ukraine', 'Kharkiv'],
    summary: 'Full-scale war since February 2022.',
  },
  activity: { last_24h: 2, last_7d: 12, previous_7d: 20, trend: 0.6 },
  reporting_7d: 5,
  fatalities_7d: 4,
  max_severity: 0.9,
  latest: shelling,
  top: shelling,
};

export const conflictDetail: ConflictDetail = {
  card: conflictCard,
  timeline: hazardDetail.timeline,
  events: [shelling, liveEvent({ id: 'n1', category: 'news', title: 'Talks in Kyiv', url: null })],
};
