import type { ResearchAllowance, ResearchUsagePage } from '@/lib/api/researchUsage';

import { adminUser, plainUser } from './fixtures';

export function researchAllowance(overrides: Partial<ResearchAllowance> = {}): ResearchAllowance {
  return {
    tier: 1,
    label: 'Level 1',
    limit: 4,
    period: 'week',
    used: 1,
    remaining: 3,
    period_start: '2026-09-21T00:00:00Z',
    resets_at: '2026-09-28T00:00:00Z',
    revision: 0,
    ...overrides,
  };
}

export function researchUsagePage(): ResearchUsagePage {
  return {
    tiers: [
      { tier: 1, label: 'Level 1', limit: 4, period: 'week' },
      { tier: 2, label: 'Level 2', limit: 4, period: 'day' },
      { tier: 3, label: 'Level 3', limit: 13, period: 'day' },
      { tier: 4, label: 'Level 4', limit: 32, period: 'day' },
    ],
    items: [adminUser, plainUser].map((user) => ({
      user_id: user.id,
      ...researchAllowance(),
    })),
  };
}
