import { expect, it } from 'vitest';
import { researchMapState } from './researchMapState';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';

it('restores the report area and centres the evidence map on its dateline crossing', () => {
  const geometry = researchAreaGeometry('rectangle', [
    [179, -2],
    [-179, 2],
  ]);
  const state = researchMapState('acquisition_or_publication', {
    geometry: { ...geometry },
    sha256: 'a'.repeat(64),
  });
  expect(state.aoi).toEqual(geometry);
  expect(state.time_basis).toBe('acquisition_or_publication');
  expect(state.camera.longitude).toBe(-180);
  expect(state.camera.latitude).toBe(0);
  expect(state.camera.zoom).toBeGreaterThan(4);
});

it('keeps ordinary reports and malformed legacy area metadata readable', () => {
  const state = researchMapState('publication');
  expect(state.aoi).toBeNull();
  expect(researchMapState('publication', { geometry: {}, sha256: 'a'.repeat(64) })).toEqual(state);
  expect(
    researchMapState('publication', {
      geometry: {
        type: 'FeatureCollection',
        features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [0, 0] } }],
      },
      sha256: 'a'.repeat(64),
    }),
  ).toEqual(state);
});
