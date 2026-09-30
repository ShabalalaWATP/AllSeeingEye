import { expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { filterMapWindow, mapRecordTime } from './newsMapTime';

const now = Date.parse('2026-09-13T12:00:00Z');
const date = {
  field: 'DATEADDED',
  method: 'gdelt-dateadded-utc-v1',
  role: 'unspecified' as const,
  basis: 'source_spec' as const,
  status: 'resolved' as const,
  precision: 'instant' as const,
  calendar: 'gregorian' as const,
  value: '2026-09-13T11:30:00Z',
  raw_text: '20260913113000',
  limitations: ['Indexing time only'],
};
const indexed = liveEvent({
  source_id: 'gdelt_news',
  category: 'news',
  published_at: null,
  source_dates: [date],
});

it('uses indexing time only for a GDELT map record with matching source metadata', () => {
  expect(mapRecordTime(indexed)).toBe(Date.parse(date.value));
  expect(indexed.published_at).toBeNull();
  expect(filterMapWindow([indexed], 1, now)).toEqual([indexed]);
  expect(filterMapWindow([indexed], 0.25, now)).toEqual([]);
  expect(filterMapWindow([indexed], null, now)).toEqual([indexed]);
});

it('never supplies recency from collection time, guesses or forged metadata', () => {
  for (const event of [
    { ...indexed, source_id: 'rss' },
    { ...indexed, category: 'conflict' as const },
    { ...indexed, source_dates: [] },
    { ...indexed, source_dates: [{ ...date, raw_text: 'bad' }] },
    { ...indexed, source_dates: [{ ...date, raw_text: '20250913113000' }] },
    { ...indexed, source_dates: [{ ...date, role: 'publication' as const }] },
  ]) {
    expect(mapRecordTime(event)).toBeNaN();
    expect(filterMapWindow([event], 1, now)).toEqual([]);
  }
  const ordinary = liveEvent({ published_at: date.value });
  expect(mapRecordTime(ordinary)).toBe(Date.parse(date.value));
});
