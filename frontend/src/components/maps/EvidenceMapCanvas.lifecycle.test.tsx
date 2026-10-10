import { act, fireEvent, render, screen } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { beforeEach, expect, it, vi } from 'vitest';
import type { MapEngine, MapEngineEvent, MapEngineHandler } from '@/lib/map/MapEngine';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import type { LocalCollection, LocalFeature } from '@/lib/map/geoJsonTypes';
import { mockWebGl2 } from '@/test/env';
import { report } from '@/test/fixtures';
import EvidenceMapCanvas from './EvidenceMapCanvas';
import { evidenceMapLayers } from './evidenceMapLayers';
import { initialMapState } from './savedMapState';
import { useCapabilitiesStore } from '@/stores/capabilities';

vi.mock('@/lib/map/MapLibreEngine', () => ({ createMapLibreEngine: vi.fn() }));
vi.mock('./evidenceMapLayers', () => ({ evidenceMapLayers: vi.fn(() => []) }));
const events = new Map<MapEngineEvent, MapEngineHandler>();
const stopped: ReturnType<typeof vi.fn>[] = [];
const map = {
  mount: vi.fn(),
  setProjection: vi.fn(),
  setBaseLayer: vi.fn(),
  setLite: vi.fn(),
  onCursor: vi.fn(() => vi.fn()),
  spin: vi.fn(),
  getZoom: vi.fn(() => 1),
  getCamera: vi.fn<MapEngine['getCamera']>(() => null),
  restoreCamera: vi.fn(),
  getViewportBounds: vi.fn(() => ({ west: 0, south: 0, east: 1, north: 1 })),
  fitBounds: vi.fn(),
  flyTo: vi.fn(),
  setLayers: vi.fn(),
  on: vi.fn((name: MapEngineEvent, handler: MapEngineHandler) => {
    events.set(name, handler);
    const stop = vi.fn();
    stopped.push(stop);
    return stop;
  }),
  captureImage: vi.fn(() => Promise.resolve(new Blob(['image'], { type: 'image/png' }))),
  destroy: vi.fn(),
} satisfies MapEngine;
const empty: LocalCollection = { type: 'FeatureCollection', features: [] };
const feature: LocalFeature = {
  type: 'Feature',
  id: 1,
  geometry: { type: 'Point', coordinates: [10, 50] },
  properties: { label: 'E1' },
};
const collection: LocalCollection = { type: 'FeatureCollection', features: [feature] };
const props = (): ComponentProps<typeof EvidenceMapCanvas> => ({
  evidence: [],
  camera: initialMapState().camera,
  onCamera: vi.fn(),
  basemap: initialMapState().basemap,
  focusRequest: null,
  sourceGeometry: empty,
  legacyDisplay: false,
  projection: 'mercator',
  selected: null,
  onSelect: vi.fn(),
});
const fire = (name: MapEngineEvent, value: unknown = {}) => act(() => events.get(name)?.(value));
const layers = () => vi.mocked(evidenceMapLayers).mock.lastCall![0];

beforeEach(() => {
  useCapabilitiesStore.setState({ loaded: true, commercialUse: false });
  mockWebGl2(true);
  events.clear();
  stopped.length = 0;
  map.getCamera.mockReturnValue(null);
  vi.mocked(createMapLibreEngine).mockReturnValue(map);
});

it('keeps a denied saved basemap unchanged and does not mount or offer image capture', () => {
  useCapabilitiesStore.setState({ commercialUse: true, sourceLicences: {} });
  vi.mocked(createMapLibreEngine).mockClear();
  const onCaptureReady = vi.fn();
  const saved = { ...props(), basemap: 'satellite' as const };
  render(<EvidenceMapCanvas {...saved} captureEnabled onCaptureReady={onCaptureReady} />);
  expect(screen.getByRole('status')).toHaveTextContent('licence terms');
  expect(createMapLibreEngine).not.toHaveBeenCalled();
  expect(onCaptureReady).not.toHaveBeenCalled();
  expect(saved.basemap).toBe('satellite');
});

it('applies the current scene when policy arrives after the evidence', () => {
  useCapabilitiesStore.setState({ loaded: false, loading: true, commercialUse: null });
  const saved = props();
  const { rerender } = render(<EvidenceMapCanvas {...saved} sourceGeometry={collection} />);
  expect(createMapLibreEngine).not.toHaveBeenCalled();
  rerender(<EvidenceMapCanvas {...saved} basemap="light" sourceGeometry={collection} />);
  act(() => useCapabilitiesStore.setState({ loaded: true, loading: false, commercialUse: false }));
  expect(map.mount).toHaveBeenCalledOnce();
  expect(map.setBaseLayer).toHaveBeenLastCalledWith('light');
  expect(map.setLayers).toHaveBeenCalled();
  expect(layers().sourceGeometry).toBe(collection);
});

it('exposes a capture function only for export and releases callbacks and renderer on unmount', async () => {
  const onCaptureReady = vi.fn();
  const onViewportReady = vi.fn();
  const { unmount } = render(
    <EvidenceMapCanvas
      {...props()}
      captureEnabled
      onCaptureReady={onCaptureReady}
      onViewportReady={onViewportReady}
    />,
  );
  const signal = new AbortController().signal;
  const capture = onCaptureReady.mock.calls[0]![0] as MapEngine['captureImage'];
  expect((await capture(signal)).type).toBe('image/png');
  expect(map.captureImage).toHaveBeenCalledWith(signal);
  const read = onViewportReady.mock.calls[0]![0] as MapEngine['getViewportBounds'];
  expect(read()).toEqual({ west: 0, south: 0, east: 1, north: 1 });
  expect(layers().onInspect).toBeUndefined();
  expect(screen.getByRole('region')).toHaveStyle({ width: '1200px', height: '800px' });
  unmount();
  expect(onCaptureReady).toHaveBeenLastCalledWith(null);
  expect(onViewportReady).toHaveBeenLastCalledWith(null);
  expect(map.setLayers).toHaveBeenLastCalledWith([]);
  expect(map.destroy).toHaveBeenCalledOnce();
  expect(stopped.every((stop) => stop.mock.calls.length === 1)).toBe(true);
});

it('ignores invalid clicks and absent camera snapshots while routing measurement and area points', () => {
  const base = props();
  const onAreaPoint = vi.fn();
  const onMeasurementPoint = vi.fn();
  const { rerender } = render(<EvidenceMapCanvas {...base} areaMode onAreaPoint={onAreaPoint} />);
  fire('click');
  expect(onAreaPoint).not.toHaveBeenCalled();
  fire('click', { lngLat: { lng: 190, lat: 20 } });
  expect(onAreaPoint).toHaveBeenCalledWith([-170, 20]);
  rerender(
    <EvidenceMapCanvas
      {...base}
      areaMode
      measurementMode
      onAreaPoint={onAreaPoint}
      onMeasurementPoint={onMeasurementPoint}
    />,
  );
  fire('click', { lngLat: { lng: 1, lat: 91 } });
  fire('click', { lngLat: { lng: 1, lat: 2 } });
  expect(onMeasurementPoint).toHaveBeenCalledExactlyOnceWith([1, 2]);
  expect(onAreaPoint).toHaveBeenCalledOnce();
  rerender(<EvidenceMapCanvas {...base} measurementMode onMeasurementPoint={onMeasurementPoint} />);
  fire('click', { lngLat: { lng: 3, lat: 4 } });
  expect(onMeasurementPoint).toHaveBeenLastCalledWith([3, 4]);
  fire('moveend');
  expect(base.onCamera).not.toHaveBeenCalled();
  const camera = { center: [1, 2] as [number, number], zoom: 3, bearing: 4, pitch: 5 };
  map.getCamera.mockReturnValue(camera);
  fire('moveend');
  expect(base.onCamera).toHaveBeenCalledWith(camera);
  fire('error');
  expect(screen.getByRole('status')).toHaveTextContent('The basemap could not load completely');
  rerender(<EvidenceMapCanvas {...base} />);
  fire('click', { lngLat: { lng: 5, lat: 6 } });
  expect(onAreaPoint).toHaveBeenCalledOnce();
  expect(onMeasurementPoint).toHaveBeenCalledTimes(2);
});

it('focuses polar source geometry only on the globe and ignores missing or unlocated evidence', () => {
  const base = props();
  const polar: LocalCollection = {
    type: 'FeatureCollection',
    features: [{ ...feature, geometry: { type: 'Point', coordinates: [10, 89] } }],
  };
  const { rerender } = render(
    <EvidenceMapCanvas
      {...base}
      sourceGeometry={polar}
      focusRequest={{ label: 'E1', sequence: 1 }}
    />,
  );
  expect(map.fitBounds).not.toHaveBeenCalled();
  rerender(
    <EvidenceMapCanvas
      {...base}
      sourceGeometry={polar}
      projection="globe"
      focusRequest={{ label: 'E1', sequence: 2 }}
    />,
  );
  expect(map.fitBounds).toHaveBeenCalledWith(
    { west: 10, south: 89, east: 10, north: 89 },
    { padding: 32, maxZoom: 12 },
  );
  rerender(<EvidenceMapCanvas {...base} focusRequest={{ label: 'missing', sequence: 3 }} />);
  const located = {
    ...report.version.evidence[0]!,
    label: 'E1',
    lat: 89,
    lon: 10,
    geo_confidence: 'exact',
  };
  rerender(
    <EvidenceMapCanvas
      {...base}
      evidence={[located]}
      focusRequest={{ label: 'E1', sequence: 4 }}
    />,
  );
  expect(map.flyTo).not.toHaveBeenCalled();
  rerender(
    <EvidenceMapCanvas
      {...base}
      evidence={[located]}
      legacyDisplay
      projection="globe"
      focusRequest={{ label: 'E1', sequence: 5 }}
    />,
  );
  expect(map.flyTo).toHaveBeenCalledWith({ center: [10, 89], zoom: 4 });
});

it.each(['aoi', 'footprints'] as const)(
  'shows details for current %s geometry and closes them on selection',
  (kind) => {
    const base = props();
    const { rerender } = render(<EvidenceMapCanvas {...base} {...{ [kind]: collection }} />);
    act(() =>
      layers().onInspect?.({ feature, title: 'Selected geometry', notes: ['Source declared'] }),
    );
    expect(screen.getByRole('region', { name: 'Selected map object' })).toHaveTextContent(
      'E1 / Point',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Close map object details' }));
    expect(screen.queryByRole('region', { name: 'Selected map object' })).not.toBeInTheDocument();
    act(() => layers().onInspect?.({ feature, title: 'Selected geometry', notes: [] }));
    act(() => layers().onSelect('E2'));
    expect(base.onSelect).toHaveBeenCalledWith('E2');
    expect(screen.queryByRole('region', { name: 'Selected map object' })).not.toBeInTheDocument();
    act(() => layers().onInspect?.({ feature, title: 'Selected geometry', notes: [] }));
    rerender(<EvidenceMapCanvas {...base} />);
    expect(screen.queryByRole('region', { name: 'Selected map object' })).not.toBeInTheDocument();
  },
);
