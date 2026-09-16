/**
 * Development-only fixture data for /dev/admin-preview. Invented accounts and
 * services only; nothing here mirrors a real deployment or credential.
 */
import type { AiPolicy, AiUsagePreview } from '@/lib/api/aiUsage';
import type { FirmsConnection } from '@/lib/api/firmsConnection';
import type { LlmConnection, LlmProfile } from '@/lib/api/llm';
import type { Profile } from '@/lib/api/profile';
import type { AccountRequest, AuditEntry, User } from '@/lib/api/schemas';
import type { TeamDetail } from '@/lib/api/teams';
import {
  adminUser,
  llmProfiles,
  pendingRequests,
  plainUser,
  source,
  sourceHealth,
  sources as baseSources,
} from '@/test/fixtures';

const hoursAgo = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString();

export const previewUsers: User[] = [
  { ...adminUser, last_login_at: hoursAgo(0.2) },
  {
    ...adminUser,
    id: '66666666-6666-4666-8666-666666666661',
    email: 'ops@example.com',
    display_name: 'Omar Ops',
    last_login_at: hoursAgo(30),
  },
  { ...plainUser, last_login_at: hoursAgo(3) },
  {
    ...plainUser,
    id: '66666666-6666-4666-8666-666666666662',
    email: 'rhea@example.com',
    display_name: 'Rhea Researcher',
    last_login_at: hoursAgo(50),
  },
  {
    ...plainUser,
    id: '66666666-6666-4666-8666-666666666663',
    email: 'legacy@example.com',
    display_name: 'Leo Legacy',
    role: 'manager',
    last_login_at: hoursAgo(400),
  },
  {
    ...plainUser,
    id: '66666666-6666-4666-8666-666666666664',
    email: 'former@example.com',
    display_name: 'Fern Former',
    is_active: false,
  },
];

export const previewRequests: AccountRequest[] = [
  ...pendingRequests.map((item, index) => ({ ...item, created_at: hoursAgo(index * 5 + 1) })),
  {
    id: '77777777-7777-4777-8777-777777777777',
    email: 'desk.lead@example.com',
    display_name: 'Dana Desk-Lead',
    reason: 'Leading the maritime watch rota and need access to shared team reports.',
    status: 'pending',
    created_at: hoursAgo(26),
  },
];

const ACTIONS = [
  'account_request_approved',
  'llm_connection_applied',
  'source_disabled',
  'user_updated',
  'login_succeeded',
  'ai_usage_policy_created',
  'team_created',
  'login_failed',
];

export const previewAudit: AuditEntry[] = Array.from({ length: 40 }, (_, index) => ({
  id: 400 - index,
  at: hoursAgo(index * 1.7 + 0.1),
  actor_user_id: index % 5 === 4 ? null : adminUser.id,
  action: ACTIONS[index % ACTIONS.length] ?? 'login_succeeded',
  subject: index % 3 === 0 ? 'rhea@example.com' : index % 3 === 1 ? 'Northern desk' : null,
  ip: index % 5 === 4 ? null : '192.0.2.10',
  details: index % 2 === 0 ? { note: `Preview entry ${400 - index}` } : {},
}));

export const previewSources = [
  ...baseSources,
  source({
    id: 'opensky',
    name: 'OpenSky aircraft states',
    organisation: 'OpenSky Network',
    category: 'aviation',
    reliability: 'B',
    poll_interval_seconds: 60,
    health: sourceHealth({ source_id: 'opensky', items_last_poll: 5120, last_latency_ms: 880 }),
  }),
  source({
    id: 'aisstream',
    name: 'AISStream ship positions',
    organisation: 'AISStream',
    category: 'maritime',
    kind: 'websocket',
    requires_key: true,
    environment_disabled: true,
    enabled: false,
    test_available: false,
    health: sourceHealth({
      source_id: 'aisstream',
      status: 'disabled',
      last_success: null,
      items_last_poll: 0,
      last_latency_ms: null,
      polls: 0,
    }),
  }),
  source({
    id: 'reliefweb',
    name: 'ReliefWeb reports',
    organisation: 'UN OCHA',
    category: 'news',
    kind: 'json',
    enabled: false,
    health: sourceHealth({ source_id: 'reliefweb', status: 'disabled', items_last_poll: 0 }),
  }),
].map((item) =>
  item.health.last_success === null
    ? item
    : { ...item, health: { ...item.health, last_success: hoursAgo(0.3) } },
);

const bound: LlmProfile = {
  id: '88888888-8888-4888-8888-888888888888',
  name: 'OpenAI Luna',
  base_url: 'https://api.openai.com/v1',
  model: 'gpt-5.6-luna',
  reasoning_effort: 'medium',
  is_tested: true,
  tested_revision: 1,
  tested_at: hoursAgo(12),
  tested_config_hash: 'preview-hash',
  is_bound: true,
  roles: ['direction', 'assessment', 'devil', 'translation'],
  provider: 'openai_compatible',
  api_key_hint: '9f3a',
  max_output_tokens: 32000,
  temperature: 0.2,
  enabled: true,
  revision: 1,
  created_at: hoursAgo(300),
  updated_at: hoursAgo(12),
};

export const previewProfiles: LlmProfile[] = [bound, ...llmProfiles];

export const previewTeam: TeamDetail = {
  team: {
    id: '44444444-4444-4444-8444-444444444444',
    name: 'Northern desk',
    is_active: true,
    created_by: adminUser.id,
    created_at: hoursAgo(200),
    updated_at: hoursAgo(20),
    description: 'Arctic and Baltic maritime monitoring.',
  },
  members: [
    {
      user_id: plainUser.id,
      display_name: plainUser.display_name,
      username: 'uma_user',
      account_role: 'user',
      is_active: true,
      role: 'manager',
      joined_at: hoursAgo(150),
    },
  ],
};

export const previewConnections: LlmConnection[] = [
  {
    team_id: null,
    user_id: null,
    profile_id: bound.id,
    profile_revision: 1,
    tested_config_hash: 'preview-hash',
    activated_at: hoursAgo(11),
    activated_by: adminUser.id,
    revision: 2,
  },
  {
    team_id: previewTeam.team.id,
    user_id: null,
    profile_id: bound.id,
    profile_revision: 1,
    tested_config_hash: 'preview-hash',
    activated_at: hoursAgo(9),
    activated_by: adminUser.id,
    revision: 1,
  },
];

export const previewPolicy: AiPolicy = {
  id: '99999999-9999-4999-8999-999999999999',
  scope: 'global',
  target_id: null,
  period: 'month',
  request_limit: 5000,
  token_limit: 4_000_000,
  enabled: true,
  revision: 3,
  created_at: hoursAgo(300),
  updated_at: hoursAgo(40),
};

export function previewUsage(): AiUsagePreview {
  const periodEnd = '2026-10-01T00:00:00Z';
  return {
    items: [
      {
        policy: previewPolicy,
        period_start: '2026-09-01T00:00:00Z',
        period_end: periodEnd,
        request_limit: 5000,
        token_limit: 4_000_000,
        override: null,
        used_requests: 3120,
        reserved_requests: 12,
        remaining_requests: 1868,
        used_tokens: 3_380_000,
        reserved_tokens: 20_000,
        remaining_tokens: 600_000,
      },
    ],
    observed: {
      period_start: '2026-09-01T00:00:00Z',
      period_end: periodEnd,
      used_requests: 842,
      used_tokens: 612_400,
      unknown_requests: 2,
      used_input_tokens: 92_400,
      used_output_tokens: 520_000,
      estimated_cost: '0.6425',
    },
    unknown_calls: 2,
    prices: {
      input_per_million: 0.2,
      output_per_million: 1.2,
      currency: 'USD',
      configured: true,
    },
    model: null,
  };
}

export const previewFirms: FirmsConnection = {
  revision: 4,
  active_revision: 4,
  configured: true,
  credential_origin: 'database',
  environment_disabled: false,
  encryption_available: true,
  area: '-180,-90,180,90',
  draft_present: false,
  draft_expires_at: null,
  tested_at: null,
  test_generation: 0,
  test_ok: false,
};

export const defaultProfileForPreview: Profile = {
  display_name: adminUser.display_name,
  timezone: 'UTC',
  date_format: 'day_first',
  research_mode: 'quick',
  research_languages: ['en'],
  research_window_days: 3,
  research_country: null,
  report_language: 'en',
  report_style: 'assessment',
  export_format: 'pdf',
  appearance_theme: 'obsidian',
  reduced_motion: false,
};
