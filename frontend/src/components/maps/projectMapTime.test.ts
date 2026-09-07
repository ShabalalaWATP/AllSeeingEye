import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { mapStateSchema } from '@/lib/api/mapViews';
import { initialMapState, matchesMapFilters } from './savedMapState';
import { mapEvidenceDateLabel, mapEvidenceTimestamp, mapTimelineDay } from './evidenceGeometry';

const item = {
  ...report.version.evidence[0]!,
  published_at: '2026-09-01T00:00:00Z',
  project: {
    dataset_id: 'aiddata-geogcdf',
    release_id: 'v3.0.1',
    project_id: '1',
    source_sha256: 'a'.repeat(64),
    recipient_iso3: 'LAO',
    reported_status: 'Completion',
    precision: 'approximate',
    attribution: 'AidData',
    data_licence: 'ODC-By-1.0',
    geometry_licence: 'ODbL-1.0',
    limitations: 'Historical source claim.',
    commitment_year: 2020,
    implementation_year: null,
    completion_year: null,
  },
};
const state = mapStateSchema.parse({
  ...initialMapState(),
  time_basis: 'recorded_time',
  published_since: '2020-06-01T00:00:00Z',
  published_until: '2020-06-02T00:00:00Z',
  include_unknown_dates: false,
});

it('uses year overlap only under the explicitly saved recorded policy', () => {
  expect(matchesMapFilters(item, state)).toBe(true);
  expect(matchesMapFilters(item, { ...state, time_basis: 'publication' })).toBe(false);
  expect(
    matchesMapFilters(item, {
      ...state,
      published_since: '2021-01-01T00:00:00Z',
      published_until: null,
    }),
  ).toBe(false);
  expect(
    matchesMapFilters(item, {
      ...state,
      published_since: null,
      published_until: '2019-12-31T23:59:59Z',
    }),
  ).toBe(false);
});

it('labels a project year without returning a fabricated occurrence timestamp', () => {
  expect(mapEvidenceTimestamp(item, 'recorded_time')).toBeNull();
  expect(mapEvidenceDateLabel(item, 'recorded_time')).toBe(
    'Commitment year 2020, exact date unknown',
  );
  expect(mapTimelineDay(item, 'recorded_time')).toBe('2020-12-31');
});

it('does not substitute publication for an unknown project year', () => {
  const unknown = { ...item, project: { ...item.project, commitment_year: null } };
  expect(matchesMapFilters(unknown, state)).toBe(false);
  expect(matchesMapFilters(unknown, { ...state, include_unknown_dates: true })).toBe(true);
  expect(mapEvidenceDateLabel(unknown, 'recorded_time')).toBe('Commitment year unknown');
});
