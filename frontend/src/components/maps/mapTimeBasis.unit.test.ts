import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { initialMapState, matchesMapFilters } from './savedMapState';
import { mapEvidenceDay, mapEvidenceTimestamp } from './evidenceGeometry';
import { mapStateSchema } from '@/lib/api/mapViews';

const observation = {
  acquired_at: '2026-09-01T10:00:00Z',
  processed_at: null,
  collection_id: 'sentinel-2-l2a',
  item_id: 'scene',
  limitations: 'Metadata only',
  scene_cloud_cover: null,
};
const scene = {
  ...report.version.evidence[0]!,
  published_at: null,
  observation,
  observed_at: '2026-09-07T10:00:00Z',
};
it('uses acquisition only when explicitly chosen and never uses retrieval', () => {
  expect(mapEvidenceDay(scene, 'publication')).toBeNull();
  expect(mapEvidenceDay(scene, 'acquisition_or_publication')).toBe('2026-09-01');
  expect(
    mapEvidenceTimestamp({ ...scene, observation: null }, 'acquisition_or_publication'),
  ).toBeNull();
});
it('filters the same records according to the frozen basis and preserves inclusive cutoffs', () => {
  const state = {
    ...initialMapState(),
    published_since: observation.acquired_at,
    published_until: observation.acquired_at,
    include_unknown_dates: false,
  };
  expect(matchesMapFilters(scene, state)).toBe(false);
  expect(matchesMapFilters(scene, { ...state, time_basis: 'acquisition_or_publication' })).toBe(
    true,
  );
  expect(
    matchesMapFilters(
      { ...scene, observation: { ...observation, acquired_at: '2026-09-01T10:00:00.001Z' } },
      { ...state, time_basis: 'acquisition_or_publication' },
    ),
  ).toBe(false);
});
it('keeps publication semantics for legacy state and ordinary reporting', () => {
  expect(mapStateSchema.parse({ camera: { longitude: 0, latitude: 0, zoom: 1 } }).time_basis).toBe(
    'publication',
  );
  const reporting = { ...scene, observation: null, published_at: '2026-09-02T10:00:00Z' };
  expect(mapEvidenceDay(reporting, 'acquisition_or_publication')).toBe('2026-09-02');
});
