import type { EconomyNews, EconomySeries, EconomySnapshot } from '@/lib/api/economy';

export const economySeries: EconomySeries = {
  id: 'gdp',
  name: 'GDP',
  unit: 'Current US dollars',
  frequency: 'annual',
  provider: 'World Bank',
  source_url: 'https://data.worldbank.org/indicator/NY.GDP.MKTP.CD',
  status: 'available',
  note: 'Annual observations, not forecasts.',
  updated_at: '2026-09-12T12:00:00Z',
  source_updated_at: '2026-09-01',
  points: [
    { date: '2023', value: 3_100_000_000_000 },
    { date: '2024', value: null },
    { date: '2025', value: 3_300_000_000_000 },
  ],
};
export const economySnapshot: EconomySnapshot = {
  fetched_at: '2026-09-12T12:00:00Z',
  refresh_after: '2026-09-12T12:05:00Z',
  regions: [
    ['WORLD', 'Worldwide'],
    ['GB', 'United Kingdom'],
    ['US', 'United States'],
    ['RU', 'Russia'],
    ['CN', 'China'],
    ['IR', 'Iran'],
  ].map(([id, name]) => ({
    id: id!,
    name: name!,
    series: [
      { ...economySeries },
      {
        ...economySeries,
        id: 'growth',
        name: 'GDP growth',
        unit: '% annual change',
        points: [
          { date: '2024', value: -1.1 },
          { date: '2025', value: 1.25 },
        ],
      },
      {
        ...economySeries,
        id: 'inflation',
        name: 'Consumer price inflation',
        unit: '% annual change',
        points: [{ date: '2025', value: 2.6 }],
      },
      {
        ...economySeries,
        id: 'unemployment',
        name: 'Unemployment',
        unit: '% of labour force',
        status: 'unavailable',
        points: [],
      },
    ],
  })),
  fx: ['GBP', 'USD', 'CNY', 'RUB', 'IRR'].map((currency) => ({
    ...economySeries,
    id: currency,
    name: `${currency} per euro`,
    unit: `${currency} per EUR`,
    frequency: 'daily',
    provider: 'European Central Bank',
    source_url:
      'https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html',
    status: currency === 'RUB' || currency === 'IRR' ? 'unavailable' : 'available',
    points:
      currency === 'RUB' || currency === 'IRR'
        ? []
        : [
            { date: '2026-09-10', value: 0.8531 },
            { date: '2026-09-11', value: 0.8547 },
          ],
  })),
};
export const economyNews: EconomyNews = {
  as_of: '2026-09-12T12:00:00Z',
  window_hours: 48,
  coverage_note: 'Connected economic feeds only; publisher remit is not a geolocation claim.',
  items: [
    {
      id: 'uk-news',
      title: 'UK economic release updates the growth outlook',
      url: 'https://www.bankofengland.co.uk/news',
      source_id: 'boe',
      source_name: 'Bank of England',
      organisation: 'Bank of England',
      published_at: '2026-09-12T10:00:00Z',
      region_codes: ['GB'],
      viewpoint: 'official_issuer',
    },
    {
      id: 'iran-news',
      title: 'Iran reports new trade figures',
      url: 'https://www.tehrantimes.com/economy',
      source_id: 'tehran',
      source_name: 'Tehran Times',
      organisation: 'Tehran Times',
      published_at: '2026-09-12T09:00:00Z',
      region_codes: ['IR'],
      viewpoint: 'state_aligned',
    },
  ],
};
