import { describe, expect, it } from 'vitest';

import { formatAgo, formatInterval, formatPersonalDate, formatUtc } from './format';

describe('formatUtc', () => {
  it('formats ISO timestamps in UTC with a UK medium date', () => {
    expect(formatUtc('2026-09-04T08:05:00Z')).toMatch(/^4 Sep\w* 2026, 08:05 UTC$/);
  });

  it('returns unparseable input unchanged', () => {
    expect(formatUtc('not a date')).toBe('not a date');
  });
});

describe('formatAgo', () => {
  const now = Date.UTC(2026, 8, 5, 12, 0, 0);

  it('rounds down to the coarsest sensible unit', () => {
    expect(formatAgo('2026-09-05T11:59:30Z', now)).toBe('just now');
    expect(formatAgo('2026-09-05T12:00:30Z', now)).toBe('just now');
    expect(formatAgo('2026-09-05T11:15:00Z', now)).toBe('45m ago');
    expect(formatAgo('2026-09-05T02:30:00Z', now)).toBe('9h ago');
    expect(formatAgo('2026-09-01T12:00:00Z', now)).toBe('4d ago');
  });

  it('returns the raw value when it is not a timestamp', () => {
    expect(formatAgo('soon', now)).toBe('soon');
  });
});

describe('formatInterval', () => {
  it('prefers whole hours, then minutes, then seconds', () => {
    expect(formatInterval(3600)).toBe('1 h');
    expect(formatInterval(300)).toBe('5 min');
    expect(formatInterval(90)).toBe('90 s');
  });
});

describe('formatPersonalDate', () => {
  const timestamp = '2026-09-04T23:05:00Z';
  it('applies timezone rollover and the selected date order', () => {
    expect(formatPersonalDate(timestamp, { timezone: 'Europe/London', date_format: 'iso' })).toBe(
      '2026-09-05 00:05 Europe/London',
    );
    expect(
      formatPersonalDate(timestamp, { timezone: 'Europe/London', date_format: 'day_first' }),
    ).toBe('05/09/2026, 00:05 Europe/London');
    expect(
      formatPersonalDate(timestamp, { timezone: 'America/New_York', date_format: 'month_first' }),
    ).toBe('09/04/2026, 19:05 America/New_York');
  });
  it('keeps safe defaults and handles invalid stored values', () => {
    expect(formatPersonalDate(timestamp)).toBe('04/09/2026, 23:05 UTC');
    expect(formatPersonalDate(timestamp, { timezone: 'Invalid/Zone', date_format: 'iso' })).toBe(
      formatUtc(timestamp),
    );
    expect(formatPersonalDate('invalid')).toBe('invalid');
  });
});
