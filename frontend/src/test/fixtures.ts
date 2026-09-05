import type { Source, SourceHealth } from '@/lib/api/eventSchemas';
import type { Country } from '@/lib/api/geoSchemas';
import type { LlmProfile } from '@/lib/api/llm';
import type { AccountRequest, AuditEntry, TokenResponse, User } from '@/lib/api/schemas';

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

export * from './fixtures.direction';
export * from './fixtures.events';
export * from './fixtures.reports';
export * from './fixtures.schedules';
export * from './fixtures.trackers';
export * from './fixtures.warning';
