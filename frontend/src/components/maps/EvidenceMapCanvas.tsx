import { useEffect, useMemo, useRef, useState } from 'react';
import { GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { EvidenceItem } from '@/lib/api/reports';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import type { MapEngine, Projection } from '@/lib/map/MapEngine';
import { hasWebGl2 } from '@/lib/map/webgl';
import { useAuthStore } from '@/stores/auth';
import type { LocalCollection, LocalOverlay } from '@/lib/map/geoJsonTypes';
import { geometryIsPolar } from '@/lib/map/localGeoJson';
import { hasEvidencePoint } from './evidenceGeometry';

export default function EvidenceMapCanvas({
  evidence,
  overlay = null,
  footprints = null,
  projection,
  selected,
  onSelect,
}: {
  evidence: readonly EvidenceItem[];
  overlay?: LocalOverlay | null;
  footprints?: LocalCollection | null;
  projection: Projection;
  selected: string | null;
  onSelect: (label: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const engine = useRef<MapEngine | null>(null);
  const [mapError, setMapError] = useState(false);
  const supported = useMemo(() => hasWebGl2(), []);
  useEffect(() => {
    if (!container.current || !supported) return;
    const map = createMapLibreEngine({ authHeader: () => useAuthStore.getState().accessToken });
    map.mount(container.current);
    map.setLite(true);
    const stopErrors = map.on('error', () => setMapError(true));
    engine.current = map;
    return () => {
      stopErrors();
      map.setLayers([]);
      map.destroy();
      engine.current = null;
    };
  }, [supported]);
  useEffect(() => {
    engine.current?.setProjection(projection);
  }, [projection]);
  useEffect(() => {
    const located = evidence.filter(
      (item) =>
        hasEvidencePoint(item) &&
        (projection === 'globe' || Math.abs(item.lat ?? 0) <= 85.05112878),
    );
    const imported = overlay
      ? [
          new GeoJsonLayer({
            id: 'private-local-geometry',
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
        ]
      : [];
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
    engine.current?.setLayers([
      ...imported,
      ...catalogue,
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
              if (info.object) onSelect(info.object.label);
              return true;
            },
          }),
      ),
    ]);
  }, [evidence, projection, selected, onSelect, overlay, footprints]);
  useEffect(() => {
    const item = evidence.find((entry) => entry.label === selected);
    if (
      item &&
      hasEvidencePoint(item) &&
      (projection === 'globe' || Math.abs(item.lat ?? 0) <= 85.05112878)
    ) {
      engine.current?.flyTo({ center: [item.lon ?? 0, item.lat ?? 0], zoom: 4 });
    }
  }, [selected, evidence, projection]);
  if (!supported)
    return (
      <p role="status" className="p-4 text-sm text-muted">
        WebGL2 is unavailable. Every saved evidence item remains accessible in the list.
      </p>
    );
  return (
    <>
      {mapError && (
        <p role="status" className="p-3 text-sm text-muted">
          The basemap could not load completely. Use the saved evidence list; missing tiles do not
          mean missing evidence.
        </p>
      )}
      <div
        ref={container}
        aria-label={projection === 'globe' ? 'Saved evidence globe' : 'Saved evidence flat map'}
        role="region"
        className="h-96 w-full"
      />
    </>
  );
}
