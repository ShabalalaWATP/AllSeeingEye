import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { cyberActors, cyberBriefing, cyberSnapshot } from '@/test/fixtures.cyber';
import { ensureCyberBriefing, fetchCyberActors, fetchCyberSnapshot, parseCyberDays } from './cyber';

it.each([2, 5, 7, 14] as const)(
  'accepts and requests the %s-day reporting window',
  async (days) => {
    server.use(
      http.get('/api/cyber', ({ request }) => {
        expect(new URL(request.url).searchParams.get('days')).toBe(String(days));
        return HttpResponse.json(cyberSnapshot(days));
      }),
    );
    expect(parseCyberDays(String(days))).toBe(days);
    await expect(fetchCyberSnapshot(days)).resolves.toMatchObject({ window_days: days });
  },
);
it.each([null, '100', 'yesterday', '02'])('defaults unsupported query %s to two days', (value) =>
  expect(parseCyberDays(value)).toBe(2),
);
it('accepts a valid headline with more than thirty actor mentions', async () => {
  const data = cyberSnapshot();
  data.items[0]!.actor_mentions = Array.from({ length: 31 }, (_, i) => ({
    group_id: `G${String(i).padStart(4, '0')}`,
    matched_name: `Actor ${i}`,
  }));
  server.use(http.get('/api/cyber', () => HttpResponse.json(data)));
  expect((await fetchCyberSnapshot(2)).items[0]!.actor_mentions).toHaveLength(31);
});
it.each([
  { window_days: 5 },
  { returned_count: 5 },
  { period_from: '2026-09-11T12:00:00Z' },
  { items: Array(201).fill(cyberSnapshot().items[0]) },
])('rejects inconsistent or oversized cyber snapshots: %j', async (override) => {
  server.use(http.get('/api/cyber', () => HttpResponse.json({ ...cyberSnapshot(), ...override })));
  await expect(fetchCyberSnapshot(2)).rejects.toMatchObject({ code: 'invalid_response' });
});
it('accepts the bounded reference and refuses malformed technique IDs', async () => {
  server.use(http.get('/api/cyber/actors', () => HttpResponse.json(cyberActors)));
  await expect(fetchCyberActors()).resolves.toEqual(cyberActors);
  const invalid = structuredClone(cyberActors);
  invalid.catalogue!.actors[0]!.technique_ids = ['../../bad'];
  server.use(http.get('/api/cyber/actors', () => HttpResponse.json(invalid)));
  await expect(fetchCyberActors()).rejects.toMatchObject({ code: 'invalid_response' });
});
it('validates the durable briefing and refuses relabelled dates', async () => {
  server.use(http.post('/api/cyber/briefing', () => HttpResponse.json(cyberBriefing(14))));
  await expect(ensureCyberBriefing(14, new AbortController().signal)).resolves.toMatchObject({
    window_days: 14,
  });
  await expect(ensureCyberBriefing(2, new AbortController().signal)).rejects.toMatchObject({
    code: 'invalid_response',
  });
});
