import { describe, expect, it } from 'vitest';

import { formatAgo } from './timeAgo';

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
