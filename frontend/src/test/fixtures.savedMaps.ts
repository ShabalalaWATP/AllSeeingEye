/** Synthetic map fixture shared by focused map behaviour tests. */
import { plainUser, report } from '@/test/fixtures';
import { initialMapState } from '@/components/maps/savedMapState';
import type { SavedMapView } from '@/lib/api/mapViews';

const geometry = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      id: 0,
      properties: { label: 'Reference' },
      geometry: { type: 'Point', coordinates: [40, 30] },
    },
  ],
};
export const savedMapFixture: SavedMapView = {
  view: {
    id: 'view-1',
    report_id: report.report.id,
    created_by: plainUser.id,
    team_id: null,
    latest_revision_id: 'revision-1',
    created_at: '2026-09-01T00:00:00Z',
    archived: false,
  },
  revision: {
    id: 'revision-1',
    view_id: 'view-1',
    number: 1,
    title: 'Saved geography',
    report_version_id: 'version-1',
    report_version_number: 1,
    state: {
      ...initialMapState(),
      display_transform: 'ase-geojson-display-v1',
      camera: { longitude: 40, latitude: 35, zoom: 6, bearing: 25, pitch: 20 },
      projection: 'mercator',
      basemap: 'light',
      source_ids: [report.version.evidence[0]!.source_id, 'second'],
      published_since: '2025-01-01T00:00:00Z',
      published_until: '2027-01-01T00:00:00Z',
      include_unknown_dates: false,
      selected_evidence: 'E1',
      overlays: [
        {
          geometry,
          source: 'First source',
          dataset_date: '2026-09-01',
          attribution: 'Synthetic',
          precision: 'unknown',
          visible: false,
        },
        {
          geometry,
          source: 'Second source',
          dataset_date: '2026-09-02',
          attribution: 'Synthetic second',
          precision: 'approximate',
          visible: true,
        },
      ],
      aoi: {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            id: 0,
            properties: { label: 'Area' },
            geometry: {
              type: 'Polygon',
              coordinates: [
                [
                  [0, 0],
                  [2, 0],
                  [2, 2],
                  [0, 2],
                  [0, 0],
                ],
              ],
            },
          },
        ],
      },
    },
    evidence_sha256: 'e'.repeat(64),
    content_sha256: 'c'.repeat(64),
    created_by: plainUser.id,
    created_at: '2026-09-01T00:00:00Z',
  },
};
export const mapEvidence = [
  {
    ...report.version.evidence[0]!,
    label: 'E1',
    title: 'Located record',
    geo_confidence: 'exact',
    lon: 10,
    lat: 50,
    published_at: '2026-01-01T12:00:00Z',
  },
];
