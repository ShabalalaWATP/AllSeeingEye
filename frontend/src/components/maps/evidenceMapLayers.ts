import { GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { EvidenceItem } from '@/lib/api/reports';
import type { MapState } from '@/lib/api/mapViews';
import type { LocalCollection, LocalOverlay } from '@/lib/map/geoJsonTypes';
import { geometryIsPolar } from '@/lib/map/localGeoJson';
import { hasEvidencePoint, hasLegacyEvidencePoint } from './evidenceGeometry';
import { measurementLayers } from '@/lib/map/measurementLayers';

export function evidenceMapLayers({
  evidence,
  overlays,
  aoi,
  footprints,
  measurement,
  projection,
  sourceGeometry,
  selected,
  areaMode,
  measurementMode,
  onSelect,
  legacyDisplay,
}: {
  evidence: readonly EvidenceItem[];
  overlays: LocalOverlay[];
  aoi: LocalCollection | null;
  footprints: LocalCollection | null;
  measurement: MapState['measurement'];
  projection: MapState['projection'];
  sourceGeometry: LocalCollection;
  selected: string | null;
  areaMode: boolean;
  measurementMode: boolean;
  onSelect: (label: string) => void;
  legacyDisplay: boolean;
}): Layer[] {
  const supportsPoint = legacyDisplay ? hasLegacyEvidencePoint : hasEvidencePoint;
  const located = evidence.filter(
    (item) =>
      supportsPoint(item) && (projection === 'globe' || Math.abs(item.lat ?? 0) <= 85.05112878),
  );
  const imported: Layer[] = overlays.map(
    (overlay, index) =>
      new GeoJsonLayer<{ label: string }>({
        id: index === 0 ? 'private-local-geometry' : `private-local-geometry-${index}`,
        data: {
          type: 'FeatureCollection' as const,
          features: overlay.display.features.filter(
            (feature) => projection === 'globe' || !geometryIsPolar(feature.geometry),
          ),
        },
        pickable: false,
        stroked: true,
        filled: overlay.precision === 'exact',
        getFillColor: [80, 200, 195, 40],
        getLineColor: [80, 200, 195, 220],
        lineWidthUnits: 'pixels',
        getLineWidth: 2,
        pointRadiusUnits: 'pixels',
        getPointRadius: 7,
      }),
  );
  if (aoi)
    imported.push(
      new GeoJsonLayer({
        id: 'saved-research-area',
        data: {
          ...aoi,
          features: aoi.features.filter(
            (feature) => projection === 'globe' || !geometryIsPolar(feature.geometry),
          ),
        },
        pickable: false,
        stroked: true,
        filled: false,
        getLineColor: [255, 255, 255, 220],
        lineWidthUnits: 'pixels',
        getLineWidth: 2,
      }),
    );
  const catalogue = footprints
    ? [
        new GeoJsonLayer({
          id: 'copernicus-acquisition-footprints',
          data: {
            type: 'FeatureCollection' as const,
            features: footprints.features.filter(
              (feature) => projection === 'globe' || !geometryIsPolar(feature.geometry),
            ),
          },
          pickable: false,
          stroked: true,
          filled: false,
          getLineColor: [182, 130, 255, 240],
          lineWidthUnits: 'pixels',
          getLineWidth: 2,
        }),
      ]
    : [];
  return [
    ...imported,
    ...catalogue,
    ...(measurement
      ? measurementLayers(measurement.points, measurement.mode, projection === 'mercator')
      : []),
    ...(sourceGeometry.features.some(
      (feature) => projection === 'globe' || !geometryIsPolar(feature.geometry),
    )
      ? [
          new GeoJsonLayer({
            id: 'frozen-evidence-geometry',
            data: {
              ...sourceGeometry,
              features: sourceGeometry.features.filter(
                (feature) => projection === 'globe' || !geometryIsPolar(feature.geometry),
              ),
            },
            pickable: true,
            stroked: true,
            filled: false,
            getLineColor: [230, 162, 74, 240],
            lineWidthUnits: 'pixels',
            getLineWidth: (feature: { properties: { label?: unknown } }) =>
              feature.properties.label === selected ? 4 : 2,
            pointRadiusUnits: 'pixels',
            getPointRadius: 8,
            onClick: (info: { object?: { properties?: { label?: unknown } } }) => {
              if (areaMode || measurementMode) return true;
              const label = info.object?.properties?.label;
              if (typeof label === 'string' && evidence.some((item) => item.label === label))
                onSelect(label);
              return true;
            },
            updateTriggers: { getLineWidth: [selected] },
          }),
        ]
      : []),
    ...[true, false].map(
      (exact) =>
        new ScatterplotLayer<EvidenceItem>({
          id: exact ? 'frozen-evidence-exact' : 'frozen-evidence-approximate',
          data: located.filter((item) => (item.geo_confidence === 'exact') === exact),
          filled: exact,
          stroked: true,
          pickable: true,
          radiusUnits: 'pixels',
          lineWidthUnits: 'pixels',
          lineWidthMinPixels: 2,
          getPosition: (item) => [item.lon ?? NaN, item.lat ?? NaN],
          getRadius: (item) => (item.label === selected ? 12 : exact ? 6 : 9),
          getFillColor: [230, 162, 74, 200],
          getLineColor: (item) =>
            item.label === selected ? [255, 255, 255, 255] : [230, 162, 74, 220],
          onClick: (info: { object?: EvidenceItem }) => {
            if (areaMode || measurementMode) return true;
            if (info.object) onSelect(info.object.label);
            return true;
          },
        }),
    ),
  ];
}
