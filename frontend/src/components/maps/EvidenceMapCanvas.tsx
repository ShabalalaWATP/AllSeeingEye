import { useEffect, useEffectEvent, useMemo, useRef, useState } from 'react';
import { GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { EvidenceItem } from '@/lib/api/reports';
import { createMapLibreEngine } from '@/lib/map/MapLibreEngine';
import type { MapBounds, MapCamera, MapEngine, Projection } from '@/lib/map/MapEngine';
import { areaClickPoint } from '@/lib/map/areaGeometry';
import type { MapState } from '@/lib/api/mapViews';
import { hasWebGl2 } from '@/lib/map/webgl';
import { useAuthStore } from '@/stores/auth';
import type { LocalCollection, LocalOverlay, Position } from '@/lib/map/geoJsonTypes';
import { geometryIsPolar } from '@/lib/map/localGeoJson';
import { hasEvidencePoint, hasLegacyEvidencePoint } from './evidenceGeometry';
import { geometryBounds } from '@/lib/map/geometryBounds';

export default function EvidenceMapCanvas({
  evidence,
  overlays = [],
  aoi = null,
  camera,
  onCamera,
  basemap,
  focusRequest,
  footprints = null,
  sourceGeometry,
  legacyDisplay,
  projection,
  selected,
  onSelect,
  areaMode = false,
  onAreaPoint,
  onViewportReady,
}: {
  evidence: readonly EvidenceItem[];
  overlays?: LocalOverlay[];
  aoi?: LocalCollection | null;
  camera: MapState['camera'];
  onCamera: (camera: MapCamera) => void;
  basemap: MapState['basemap'];
  focusRequest: { label: string; sequence: number } | null;
  footprints?: LocalCollection | null;
  sourceGeometry: LocalCollection;
  legacyDisplay: boolean;
  projection: Projection;
  selected: string | null;
  onSelect: (label: string) => void;
  areaMode?: boolean;
  onAreaPoint?: (point: Position) => void;
  onViewportReady?: (read: (() => MapBounds | null) | null) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const engine = useRef<MapEngine | null>(null);
  const [mapError, setMapError] = useState(false);
  const initial = useRef({ camera, projection, basemap });
  const supportsPoint = legacyDisplay ? hasLegacyEvidencePoint : hasEvidencePoint;
  const cameraChanged = useEffectEvent((value: MapCamera) => onCamera(value));
  const viewportReady = useEffectEvent((read: (() => MapBounds | null) | null) =>
    onViewportReady?.(read),
  );
  const areaClicked = useEffectEvent((event: unknown) => {
    if (areaMode) {
      const point = areaClickPoint(event);
      if (point) onAreaPoint?.(point);
    }
  });
  const focusSelection = useEffectEvent(() => {
    const source = sourceGeometry.features.find(
      (feature) => feature.properties.label === focusRequest?.label,
    );
    if (source) {
      if (projection === 'globe' || !geometryIsPolar(source.geometry))
        engine.current?.fitBounds(geometryBounds(source.geometry), { padding: 32, maxZoom: 12 });
      return;
    }
    const item = evidence.find((entry) => entry.label === focusRequest?.label);
    if (
      item &&
      supportsPoint(item) &&
      (projection === 'globe' || Math.abs(item.lat ?? 0) <= 85.05112878)
    )
      engine.current?.flyTo({ center: [item.lon ?? 0, item.lat ?? 0], zoom: 4 });
  });
  const supported = useMemo(() => hasWebGl2(), []);
  useEffect(() => {
    if (!container.current || !supported) return;
    const map = createMapLibreEngine({ authHeader: () => useAuthStore.getState().accessToken });
    map.setProjection(initial.current.projection);
    map.setBaseLayer(initial.current.basemap);
    map.mount(container.current);
    map.setLite(true);
    const stopErrors = map.on('error', () => setMapError(true));
    engine.current = map;
    viewportReady(() => map.getViewportBounds());
    const stopArea = map.on('click', areaClicked);
    const saved = initial.current.camera;
    map.restoreCamera({
      center: [saved.longitude, saved.latitude],
      zoom: saved.zoom,
      bearing: saved.bearing,
      pitch: saved.pitch,
    });
    const stopCamera = map.on('moveend', () => {
      const value = map.getCamera();
      if (value) cameraChanged(value);
    });
    return () => {
      stopErrors();
      stopCamera();
      stopArea();
      viewportReady(null);
      map.setLayers([]);
      map.destroy();
      engine.current = null;
    };
  }, [supported]);
  useEffect(() => {
    engine.current?.setProjection(projection);
  }, [projection]);
  useEffect(() => {
    engine.current?.setBaseLayer(basemap);
  }, [basemap]);
  useEffect(() => {
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
    engine.current?.setLayers([
      ...imported,
      ...catalogue,
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
                if (areaMode) return true;
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
              if (areaMode) return true;
              if (info.object) onSelect(info.object.label);
              return true;
            },
          }),
      ),
    ]);
  }, [
    evidence,
    projection,
    selected,
    onSelect,
    overlays,
    footprints,
    aoi,
    areaMode,
    sourceGeometry,
    supportsPoint,
  ]);
  useEffect(() => {
    if (focusRequest) focusSelection();
  }, [focusRequest]);
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
