import { describe, expect, it } from 'vitest';

import { formatUtc } from './format';

describe('formatUtc', () => {
  it('formats ISO timestamps in UTC with a UK medium date', () => {
    expect(formatUtc('2026-09-04T08:05:00Z')).toMatch(/^4 Sep\w* 2026, 08:05 UTC$/);
  });

  it('returns unparseable input unchanged', () => {
    expect(formatUtc('not a date')).toBe('not a date');
  });
});
