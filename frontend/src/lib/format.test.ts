import { describe, expect, it } from 'vitest';

import { formatAgo, formatInterval, formatUtc } from './format';

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
