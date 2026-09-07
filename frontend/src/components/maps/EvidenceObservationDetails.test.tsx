import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';

import { evidenceItemSchema } from '@/lib/api/reports';
import { report } from '@/test/fixtures';
import { EvidenceObservationDetails } from './EvidenceObservationDetails';

const base = report.version.evidence[0]!;
const observation = {
  acquired_at: '2026-09-01T10:00:00Z',
  processed_at: null,
  collection_id: 'sentinel-2-l2a',
  item_id: 'S2_scene',
  limitations: 'Metadata only. No imagery inspected.',
  scene_cloud_cover: 0,
};
const geometry = {
  geometry: {
    type: 'Polygon' as const,
    coordinates: [
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 0],
      ],
    ],
  },
  sha256: 'a'.repeat(64),
  location_role: 'observation_footprint' as const,
  precision: 'Catalogue scene coverage',
  method: 'STAC source geometry',
  source_id: 'research-copernicus-footprints',
  attribution: 'Copernicus',
};

it('preserves observation fields through the response parser and labels source limitations', () => {
  const item = evidenceItemSchema.parse({ ...base, published_at: null, observation, geometry });
  expect(item.geometry?.geometry).toEqual(geometry.geometry);
  expect(item.published_at).toBeNull();
  render(<EvidenceObservationDetails item={item} />);
  expect(screen.getByText('0%')).toBeInTheDocument();
  expect(screen.getByText('Unknown')).toBeInTheDocument();
  expect(screen.getByText('S2_scene')).toBeInTheDocument();
  expect(screen.getByText(/does not establish an event location/)).toBeInTheDocument();
  expect(screen.getByText(observation.limitations)).toBeInTheDocument();
});

it('does not manufacture observation metadata for legacy evidence', () => {
  render(<EvidenceObservationDetails item={{ ...base, geometry: null, observation: null }} />);
  expect(screen.queryByRole('region', { name: 'Source observation' })).not.toBeInTheDocument();
  expect(evidenceItemSchema.parse(base).observation).toBeUndefined();
});

it('shows unknown cloud cover separately from zero and renders source strings as text', () => {
  const limitations = '<img src=x onerror=alert(1)>';
  const { container } = render(
    <EvidenceObservationDetails
      item={{
        ...base,
        observation: { ...observation, scene_cloud_cover: null, limitations },
      }}
    />,
  );
  expect(screen.getAllByText('Unknown')).toHaveLength(2);
  expect(screen.getByText(limitations)).toBeInTheDocument();
  expect(container.querySelector('img')).toBeNull();
});
