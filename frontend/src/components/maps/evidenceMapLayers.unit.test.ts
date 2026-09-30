import type { Layer } from '@deck.gl/core';
import { describe, expect, it, vi } from 'vitest';

import type { EvidenceItem } from '@/lib/api/reports';
import type { LocalCollection, LocalFeature, LocalOverlay } from '@/lib/map/geoJsonTypes';
import { report } from '@/test/fixtures.reports';

import { evidenceMapLayers } from './evidenceMapLayers';

const point = (latitude: number, label = 'E1'): LocalFeature => ({
  type: 'Feature',
  id: latitude,
  properties: { label },
  geometry: { type: 'Point', coordinates: [1, latitude] },
});
const collection = (...features: LocalFeature[]): LocalCollection => ({
  type: 'FeatureCollection',
  features,
});
const item = (changes: Partial<EvidenceItem> = {}): EvidenceItem => ({
  ...report.version.evidence[0]!,
  label: 'E1',
  lat: 10,
  lon: 1,
  geo_confidence: 'exact',
  geometry: null,
  ...changes,
});
const overlay = (changes: Partial<LocalOverlay> = {}): LocalOverlay => ({
  canonical: collection(point(10)),
  display: collection(point(10)),
  vertices: 1,
  source: '',
  datasetDate: '',
  attribution: '',
  precision: 'exact',
  ...changes,
});

function build(changes: Partial<Parameters<typeof evidenceMapLayers>[0]> = {}) {
  const onSelect = vi.fn();
  const onInspect = vi.fn();
  const layers = evidenceMapLayers({
    evidence: [item()],
    overlays: [],
    aoi: null,
    footprints: null,
    measurement: null,
    projection: 'globe',
    sourceGeometry: collection(),
    selected: null,
    areaMode: false,
    measurementMode: false,
    onSelect,
    onInspect,
    legacyDisplay: false,
    ...changes,
  });
  return { layers, onSelect, onInspect };
}

interface Props {
  data: LocalCollection | EvidenceItem[];
  pickable: boolean;
  filled: boolean;
  onClick: (info: { object?: unknown }) => boolean;
  getRadius: (item: EvidenceItem) => number;
  getPosition: (item: EvidenceItem) => number[];
  getLineColor: (item: EvidenceItem) => number[];
  getLineWidth: (feature: LocalFeature) => number;
}
function props(layers: Layer[], id: string): Props {
  const layer = layers.find((candidate) => candidate.id === id);
  expect(layer, id).toBeDefined();
  return layer!.props as unknown as Props;
}

describe('evidence map layer selection', () => {
  it('keeps polar features on the globe and omits them from every flat geometry layer', () => {
    const geometry = collection(point(10), point(89));
    for (const projection of ['globe', 'mercator'] as const) {
      const { layers } = build({
        projection,
        overlays: [overlay({ display: geometry }), overlay({ precision: 'approximate' })],
        aoi: geometry,
        footprints: geometry,
        sourceGeometry: geometry,
        evidence: [item(), item({ label: 'E2', lat: 89 })],
      });
      for (const id of [
        'private-local-geometry',
        'saved-research-area',
        'copernicus-acquisition-footprints',
        'frozen-evidence-geometry',
      ]) {
        expect((props(layers, id).data as LocalCollection).features).toHaveLength(
          projection === 'globe' ? 2 : 1,
        );
      }
      expect(props(layers, 'frozen-evidence-exact').data).toHaveLength(
        projection === 'globe' ? 2 : 1,
      );
      expect(props(layers, 'private-local-geometry-1').filled).toBe(false);
    }
    expect(
      build({ projection: 'mercator', sourceGeometry: collection(point(89)) }).layers.map(
        (layer) => layer.id,
      ),
    ).not.toContain('frozen-evidence-geometry');
  });

  it('uses captured source points only for explicit legacy display', () => {
    const evidence = [
      item({
        geometry: {
          geometry: { type: 'Point', coordinates: [1, 10] },
          sha256: 'frozen',
          location_role: 'observation_footprint',
          precision: 'Scene coverage',
          method: 'STAC',
          source_id: 'catalogue',
          attribution: 'Catalogue',
        },
      }),
    ];
    expect(props(build({ evidence }).layers, 'frozen-evidence-exact').data).toHaveLength(0);
    expect(
      props(build({ evidence, legacyDisplay: true }).layers, 'frozen-evidence-exact').data,
    ).toHaveLength(1);
  });

  it.each([{ areaMode: true }, { measurementMode: true }])(
    'blocks geometry and point selections during editing: %j',
    (mode) => {
      const { layers, onSelect, onInspect } = build({
        ...mode,
        overlays: [overlay()],
        sourceGeometry: collection(point(10)),
      });
      const imported = props(layers, 'private-local-geometry');
      expect(imported.pickable).toBe(false);
      expect(imported.onClick({ object: point(10) })).toBe(true);
      props(layers, 'frozen-evidence-geometry').onClick({ object: point(10) });
      props(layers, 'frozen-evidence-exact').onClick({ object: item() });
      expect(onSelect).not.toHaveBeenCalled();
      expect(onInspect).not.toHaveBeenCalled();
    },
  );

  it('inspects local provenance, tolerates empty hits and supports absent inspection callbacks', () => {
    const { layers, onInspect } = build({
      overlays: [
        overlay(),
        overlay({ source: 'Operator', datasetDate: '2026-09-01', attribution: 'Local' }),
      ],
    });
    props(layers, 'private-local-geometry').onClick({});
    expect(onInspect).not.toHaveBeenCalled();
    props(layers, 'private-local-geometry').onClick({ object: point(10) });
    expect(onInspect).toHaveBeenCalledWith(
      expect.objectContaining({ notes: expect.arrayContaining(['Source: Not recorded']) }),
    );
    props(layers, 'private-local-geometry-1').onClick({ object: point(10) });
    expect(onInspect).toHaveBeenLastCalledWith(
      expect.objectContaining({
        notes: expect.arrayContaining([
          'Source: Operator',
          'Dataset date: 2026-09-01',
          'Attribution: Local',
        ]),
      }),
    );
    const noInspector = props(
      build({ overlays: [overlay()], onInspect: undefined }).layers,
      'private-local-geometry',
    );
    expect(noInspector.pickable).toBe(false);
    expect(noInspector.onClick({ object: point(10) })).toBe(true);
  });

  it('selects only labels belonging to frozen evidence and distinguishes selected geometry', () => {
    const { layers, onSelect } = build({ sourceGeometry: collection(point(10)), selected: 'E1' });
    const geometry = props(layers, 'frozen-evidence-geometry');
    for (const info of [
      {},
      { object: {} },
      { object: { properties: {} } },
      { object: point(10, 'unknown') },
    ])
      geometry.onClick(info);
    expect(onSelect).not.toHaveBeenCalled();
    geometry.onClick({ object: point(10) });
    expect(onSelect).toHaveBeenCalledWith('E1');
    expect(geometry.getLineWidth(point(10))).toBe(4);
    expect(geometry.getLineWidth(point(10, 'E2'))).toBe(2);
  });

  it('styles exact and approximate points and guards empty point hits', () => {
    const exact = item();
    const approximate = item({ label: 'E2', geo_confidence: 'city' });
    const { layers, onSelect } = build({
      evidence: [exact, approximate],
      selected: 'E1',
      measurement: {
        mode: 'distance',
        method: 'wgs84-geographiclib-2.2.0-v1',
        points: [
          [1, 10],
          [2, 10],
        ],
      },
    });
    const exactLayer = props(layers, 'frozen-evidence-exact');
    const approximateLayer = props(layers, 'frozen-evidence-approximate');
    expect(exactLayer.getRadius(exact)).toBe(12);
    expect(exactLayer.getRadius(approximate)).toBe(6);
    expect(approximateLayer.getRadius(approximate)).toBe(9);
    expect(exactLayer.getPosition(exact)).toEqual([1, 10]);
    expect(exactLayer.getPosition(item({ lat: null, lon: null }))).toEqual([NaN, NaN]);
    expect(exactLayer.getLineColor(exact)).toEqual([255, 255, 255, 255]);
    expect(exactLayer.getLineColor(approximate)).toEqual([230, 162, 74, 220]);
    exactLayer.onClick({});
    expect(onSelect).not.toHaveBeenCalled();
    approximateLayer.onClick({ object: approximate });
    expect(onSelect).toHaveBeenCalledWith('E2');
    expect(layers.some((layer) => layer.id === 'measurement-path')).toBe(true);
  });
});
