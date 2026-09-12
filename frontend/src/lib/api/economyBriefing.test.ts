import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { reportJob } from '@/test/reportJobFixture';
import { economyNews } from '@/test/fixtures.economy';
import { fetchEconomyNews } from './economy';
import { ensureEconomyBriefing, parseEconomyDays } from './economyBriefing';

const briefing = {
  job: reportJob(),
  window_days: 2,
  period_from: '2026-09-10T12:00:00Z',
  period_to: '2026-09-12T12:00:00Z',
  next_refresh_at: '2026-09-13T12:00:00Z',
  coverage_note: 'Available sources only.',
};

it.each([null, '1', '3', '365', 'hello', '02'])(
  'defaults unsupported URL period %s to 2 days',
  (value) => {
    expect(parseEconomyDays(value)).toBe(2);
  },
);
it.each([2, 5, 7, 14] as const)('accepts the supported %s-day URL period', (value) => {
  expect(parseEconomyDays(String(value))).toBe(value);
});
it('accepts exact frozen bounds, including supported ISO time offsets', async () => {
  server.use(
    http.post('/api/economy/briefing', () =>
      HttpResponse.json({ ...briefing, period_from: '2026-09-10T13:00:00+01:00' }),
    ),
  );
  await expect(ensureEconomyBriefing(2, new AbortController().signal)).resolves.toMatchObject({
    window_days: 2,
  });
});
it.each([
  { window_days: 5 },
  { period_from: '2026-09-11T12:00:00Z' },
  { period_to: 'yesterday' },
  { period_to: '2026-09-09T12:00:00Z' },
])('rejects mismatched, invalid or reversed report bounds: %j', async (override) => {
  server.use(
    http.post('/api/economy/briefing', () => HttpResponse.json({ ...briefing, ...override })),
  );
  await expect(ensureEconomyBriefing(2, new AbortController().signal)).rejects.toMatchObject({
    code: 'invalid_response',
  });
});
it('rejects news for a different period instead of relabelling it', async () => {
  server.use(http.get('/api/economy/news', () => HttpResponse.json(economyNews)));
  await expect(fetchEconomyNews(14)).rejects.toMatchObject({ code: 'invalid_response' });
});
