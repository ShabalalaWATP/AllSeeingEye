import { expect, it } from 'vitest';
import { annotationComparison as result } from '@/test/fixtures.comparisons';
import { annotationComparisonSchema } from './annotationComparisons';
it('validates frozen domain geometry without substituting a current map rendering', () => {
  const geometry = {
    source_geometry: '{"type":"Point","coordinates":[30,40]}',
    location_role: 'registered_office',
    precision: 'city',
    method: 'source-reported',
    source_id: 'registry',
    attribution: 'Source attribution',
  };
  const value = {
    ...result,
    before: { ...result.before, evidence: [{ ...result.before.evidence[0], geometry }] },
  };
  expect(annotationComparisonSchema.parse(value).before.evidence[0]?.geometry).toEqual(geometry);
  expect(
    annotationComparisonSchema.safeParse({
      ...value,
      before: {
        ...value.before,
        evidence: [
          {
            ...value.before.evidence[0],
            geometry: { geometry: { type: 'Point', coordinates: [30, 40] }, sha256: 'hash' },
          },
        ],
      },
    }).success,
  ).toBe(false);
});
it('rejects missing frozen grade dimensions and invalid comparison proof', () => {
  const evidence = { ...result.before.evidence[0], reliability: undefined };
  expect(
    annotationComparisonSchema.safeParse({
      ...result,
      before: { ...result.before, evidence: [evidence] },
    }).success,
  ).toBe(false);
  expect(
    annotationComparisonSchema.safeParse({ ...result, comparison_sha256: 'unverified' }).success,
  ).toBe(false);
});
