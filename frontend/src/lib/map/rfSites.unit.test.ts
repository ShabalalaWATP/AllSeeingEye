import { expect, it } from 'vitest';
import { parseSiteCoordinate, rfPositionSchema } from './rfSites';
it.each([
  ['51.5', 'latitude', 51.5],
  ['-0.125', 'longitude', -0.125],
  ['51°30′0″N', 'latitude', 51.5],
  ['0 7 30 W', 'longitude', -0.125],
  ['90°0′0″S', 'latitude', -90],
  ['180°0′0″E', 'longitude', 180],
] as const)('parses %s on %s', (text, axis, value) =>
  expect(parseSiteCoordinate(text, axis)).toBeCloseTo(value),
);
it.each([
  '',
  'Infinity',
  '0x10',
  '91',
  '90°0′1″N',
  '51°60′0″N',
  '51°0′60″N',
  '51°0′0″E',
  '-51°0′0″S',
])('rejects ambiguous or invalid latitude %s', (text) =>
  expect(() => parseSiteCoordinate(text, 'latitude')).toThrow(),
);
it('rejects non-finite and out-of-range map coordinates', () => {
  expect(rfPositionSchema.safeParse([0, Infinity]).success).toBe(false);
  expect(rfPositionSchema.safeParse([181, 0]).success).toBe(false);
});
