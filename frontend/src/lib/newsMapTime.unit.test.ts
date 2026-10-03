import { expect, it, vi } from 'vitest';
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

it('reuses an immutable record time but reparses a corrected copy with the same id', () => {
  const original = Object.freeze(liveEvent({ id: 'corrected', published_at: date.value }));
  const correction = Object.freeze({ ...original, published_at: '2026-09-13T10:00:00Z' });
  const parse = vi.spyOn(Date, 'parse');

  expect(mapRecordTime(original)).toBe(now - 30 * 60_000);
  expect(mapRecordTime(original)).toBe(now - 30 * 60_000);
  expect(parse).toHaveBeenCalledTimes(1);
  expect(mapRecordTime(correction)).toBe(now - 2 * 3_600_000);
  expect(mapRecordTime(original)).toBe(now - 30 * 60_000);
  expect(parse).toHaveBeenCalledTimes(2);
  expect(filterMapWindow([correction], 1, now)).toEqual([]);
});

it('reuses invalid times without letting the same id hide a later correction', () => {
  const missing = Object.freeze(liveEvent({ id: 'unknown', published_at: null }));
  const invalid = Object.freeze({ ...missing, published_at: 'not a timestamp' });
  const corrected = Object.freeze({ ...missing, published_at: date.value });
  const parse = vi.spyOn(Date, 'parse');

  for (const event of [missing, invalid]) {
    expect(mapRecordTime(event)).toBeNaN();
    expect(mapRecordTime(event)).toBeNaN();
  }
  expect(parse).toHaveBeenCalledTimes(2);
  expect(mapRecordTime(corrected)).toBe(now - 30 * 60_000);
  expect(parse).toHaveBeenCalledTimes(3);
  expect(filterMapWindow([missing, invalid, corrected], 1, now)).toEqual([corrected]);
});

it('rechecks corrected source-date evidence rather than caching by event id', () => {
  const original = Object.freeze({ ...indexed, id: 'source-correction' });
  const originalDates = structuredClone(original.source_dates);
  const changed = Object.freeze({
    ...original,
    source_dates: [{ ...date, value: '2026-09-13T11:00:00Z', raw_text: '20260913110000' }],
  });
  const forged = Object.freeze({
    ...changed,
    source_dates: [{ ...changed.source_dates[0]!, raw_text: '20250913110000' }],
  });
  const parse = vi.spyOn(Date, 'parse');

  expect(mapRecordTime(original)).toBe(now - 30 * 60_000);
  const firstReads = parse.mock.calls.length;
  expect(firstReads).toBeGreaterThan(0);
  expect(mapRecordTime(original)).toBe(now - 30 * 60_000);
  expect(parse).toHaveBeenCalledTimes(firstReads);
  expect(mapRecordTime(changed)).toBe(now - 3_600_000);
  expect(mapRecordTime(forged)).toBeNaN();
  expect(filterMapWindow([original, changed, forged], 0.75, now)).toEqual([original]);
  expect(original.source_dates).toEqual(originalDates);
});

it('expires a cached timestamp as the clock advances without needing another event', () => {
  const event = Object.freeze(liveEvent({ published_at: date.value }));
  const parse = vi.spyOn(Date, 'parse');
  expect(filterMapWindow([event], 1, now)).toEqual([event]);
  expect(filterMapWindow([event], 1, now + 31 * 60_000)).toEqual([]);
  expect(filterMapWindow([event], null, now + 31 * 60_000)).toEqual([event]);
  expect(parse).toHaveBeenCalledTimes(1);
});

it('rechecks same-object timestamp and time-basis corrections', () => {
  const event = liveEvent({ published_at: date.value });
  expect(mapRecordTime(event)).toBe(now - 30 * 60_000);
  event.published_at = '1970-01-01T00:00:00Z';
  expect(mapRecordTime(event)).toBe(0);
  expect(mapRecordTime(event)).toBe(0);
  event.published_at = null;
  expect(mapRecordTime(event)).toBeNaN();

  event.source_id = 'gdelt_news';
  event.category = 'news';
  event.source_dates = [{ ...indexed.source_dates[0]! }];
  expect(mapRecordTime(event)).toBe(now - 30 * 60_000);
  event.category = 'conflict';
  expect(mapRecordTime(event)).toBeNaN();
  event.category = 'news';
  expect(mapRecordTime(event)).toBe(now - 30 * 60_000);
  event.source_id = 'rss';
  expect(mapRecordTime(event)).toBeNaN();
});

it('rechecks source metadata values, eligibility and ordering even when mutated in place', () => {
  const event = liveEvent({ ...indexed, source_dates: [{ ...date }] });
  const metadata = event.source_dates[0]!;
  expect(mapRecordTime(event)).toBe(now - 30 * 60_000);
  metadata.value = '2026-09-13T11:00:00Z';
  expect(mapRecordTime(event)).toBeNaN();
  metadata.raw_text = '20260913110000';
  expect(mapRecordTime(event)).toBe(now - 3_600_000);
  metadata.role = 'publication';
  expect(mapRecordTime(event)).toBeNaN();
  metadata.role = 'unspecified';
  expect(mapRecordTime(event)).toBe(now - 3_600_000);

  // The first eligible declaration remains authoritative, including an unusable value.
  event.source_dates.unshift({ ...indexed.source_dates[0]!, value: 'invalid' });
  expect(mapRecordTime(event)).toBeNaN();
  event.source_dates.reverse();
  expect(mapRecordTime(event)).toBe(now - 3_600_000);
  event.source_dates.splice(0);
  expect(mapRecordTime(event)).toBeNaN();
});

it.each([
  ['field', { field: 'publication_date' }],
  ['method', { method: 'unverified' }],
  ['role', { role: 'publication' as const }],
  ['basis', { basis: 'unresolved' as const }],
  ['status', { status: 'unresolved' as const }],
  ['precision', { precision: 'unknown' as const }],
])('discards a cached indexing time after the %s evidence changes', (_, patch) => {
  const event = liveEvent({ ...indexed, source_dates: [{ ...date }] });
  expect(mapRecordTime(event)).toBe(now - 30 * 60_000);
  Object.assign(event.source_dates[0]!, patch);
  expect(mapRecordTime(event)).toBeNaN();
  expect(filterMapWindow([event], 1, now)).toEqual([]);
  Object.assign(event.source_dates[0]!, date);
  expect(mapRecordTime(event)).toBe(now - 30 * 60_000);
});
