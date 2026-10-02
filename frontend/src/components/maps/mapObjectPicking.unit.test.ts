import { expect, it, vi } from 'vitest';
import type { LocalCollection, LocalOverlay } from '@/lib/map/geoJsonTypes';
import type { MapObjectSelection } from './MapObjectDetails';
import { evidenceMapLayers } from './evidenceMapLayers';
const data: LocalCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      id: 1,
      properties: { label: 'Recorded shape' },
      geometry: { type: 'Point', coordinates: [10, 50] },
    },
  ],
};
const overlay: LocalOverlay = {
  canonical: data,
  display: data,
  source: 'Operator file',
  datasetDate: '2026-09-05',
  attribution: 'Declared credit',
  precision: 'unknown',
  vertices: 1,
};
const empty: LocalCollection = { type: 'FeatureCollection', features: [] };
const options = {
  evidence: [],
  overlays: [overlay],
  aoi: data,
  footprints: data,
  measurement: null,
  projection: 'mercator' as const,
  sourceGeometry: empty,
  selected: null,
  areaMode: false,
  measurementMode: false,
  onSelect: vi.fn(),
  legacyDisplay: false,
};
interface Props {
  pickable: boolean;
  onClick: (info: { object?: unknown }) => boolean;
}
it.each(['mercator', 'globe'] as const)(
  'inspects overlay, AOI and footprint records in %s without selecting unrelated evidence',
  (projection) => {
    const inspect = vi.fn<(value: MapObjectSelection) => void>();
    const layers = evidenceMapLayers({ ...options, projection, onInspect: inspect });
    for (const layer of layers.slice(0, 3)) {
      const props = layer.props as unknown as Props;
      expect(props.pickable).toBe(true);
      props.onClick({ object: data.features[0] });
    }
    expect(inspect.mock.calls.map(([value]) => value.title)).toEqual([
      'Local overlay',
      'Research area',
      'Satellite catalogue footprint',
    ]);
    expect(inspect.mock.calls[0]?.[0].notes.join(' ')).toContain('Declared precision: unknown');
    expect(inspect.mock.calls[2]?.[0].notes.join(' ')).toContain('not the satellite location');
    expect(options.onSelect).not.toHaveBeenCalled();
  },
);
it.each([{ areaMode: true }, { measurementMode: true }, { onInspect: undefined }])(
  'keeps drawing and export-only geometry noninteractive: %j',
  (change) => {
    const inspect = vi.fn<(value: MapObjectSelection) => void>();
    const layers = evidenceMapLayers({ ...options, onInspect: inspect, ...change });
    for (const layer of layers.slice(0, 3)) {
      const props = layer.props as unknown as Props;
      expect(props.pickable).toBe(false);
      props.onClick({ object: data.features[0] });
    }
    expect(inspect).not.toHaveBeenCalled();
  },
);
