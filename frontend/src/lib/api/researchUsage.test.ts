import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { subscribeResearchUsage } from '@/lib/researchUsageEvents';
import { adminUser } from '@/test/fixtures';
import { researchAllowance, researchUsagePage } from '@/test/fixtures.researchUsage';
import { server } from '@/test/server';

import { getMyResearchUsage, getAdminResearchUsage, setUserResearchTier } from './researchUsage';

describe('research allowance API', () => {
  it('loads default assignments and tier choices from the server', async () => {
    expect(await getMyResearchUsage()).toEqual(researchAllowance());
    expect(await getAdminResearchUsage()).toEqual(researchUsagePage());
  });

  it.each([{ tier: 5 }, { remaining: -1 }, { period: 'month' }, { revision: -1 }])(
    'rejects an invalid allowance instead of displaying invented limits: %j',
    async (invalid) => {
      server.use(
        http.get('/api/research-usage/me', () =>
          HttpResponse.json({ ...researchAllowance(), ...invalid }),
        ),
      );
      await expect(getMyResearchUsage()).rejects.toMatchObject({ code: 'invalid_response' });
    },
  );

  it('updates the level with optimistic concurrency and invalidates visible usage', async () => {
    let body: unknown;
    const refreshed = vi.fn();
    const unsubscribe = subscribeResearchUsage(refreshed);
    const result = {
      ...researchUsagePage().items[0],
      tier: 4,
      label: 'Level 4',
      period: 'day',
      limit: 32,
      revision: 1,
    };
    server.use(
      http.put('/api/admin/users/:id/research-tier', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(result);
      }),
    );
    try {
      expect(await setUserResearchTier(adminUser.id, { tier: 4, expected_revision: 0 })).toEqual(
        result,
      );
      expect(body).toEqual({ tier: 4, expected_revision: 0 });
      expect(refreshed).toHaveBeenCalledOnce();
    } finally {
      unsubscribe();
    }
  });
});
