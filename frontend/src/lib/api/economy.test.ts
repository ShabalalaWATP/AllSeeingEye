import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { economyNews, economySnapshot } from '@/test/fixtures.economy';
import { fetchEconomy, fetchEconomyNews } from './economy';

it('accepts bounded dated series including genuine missing observations', async () => {
  server.use(http.get('/api/economy', () => HttpResponse.json(economySnapshot)));
  expect(await fetchEconomy()).toEqual(economySnapshot);
});
it('rejects an oversized response instead of rendering an unbounded chart', async () => {
  server.use(
    http.get('/api/economy', () =>
      HttpResponse.json({ ...economySnapshot, fx: Array(100).fill(economySnapshot.fx[0]) }),
    ),
  );
  await expect(fetchEconomy()).rejects.toMatchObject({ code: 'invalid_response' });
});
it('accepts twelve indicators and rejects a thirteenth', async () => {
  const region = {
    ...economySnapshot.regions[0]!,
    series: Array.from({ length: 12 }, (_, index) => ({
      ...economySnapshot.regions[0]!.series[0]!,
      id: `metric-${index}`,
    })),
  };
  server.use(
    http.get('/api/economy', () => HttpResponse.json({ ...economySnapshot, regions: [region] })),
  );
  expect((await fetchEconomy()).regions[0]!.series).toHaveLength(12);
  region.series.push({ ...region.series[0]!, id: 'too-many' });
  await expect(fetchEconomy()).rejects.toMatchObject({ code: 'invalid_response' });
});
it('validates news region and publisher provenance', async () => {
  server.use(http.get('/api/economy/news', () => HttpResponse.json(economyNews)));
  expect(await fetchEconomyNews()).toEqual(economyNews);
  server.use(
    http.get('/api/economy/news', () =>
      HttpResponse.json({
        ...economyNews,
        items: [{ ...economyNews.items[0], viewpoint: 'verified_fact' }],
      }),
    ),
  );
  await expect(fetchEconomyNews()).rejects.toMatchObject({ code: 'invalid_response' });
});
