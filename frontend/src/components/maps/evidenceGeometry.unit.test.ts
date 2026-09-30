import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { publicationDay } from './evidenceGeometry';

it('keeps unknown map publication dates unlocated on the time axis', () => {
  const item = report.version.evidence[0]!;
  expect(publicationDay({ ...item, published_at: null })).toBeNull();
  expect(publicationDay({ ...item, published_at: 'invalid' })).toBeNull();
  expect(publicationDay({ ...item, published_at: '2026-09-07T00:00:00Z' })).toBe('2026-09-07');
});
