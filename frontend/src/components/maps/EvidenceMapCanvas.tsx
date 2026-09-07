import { useEffect, useEffectEvent, useMemo, useRef, useState } from 'react';
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
import { evidenceMapLayers } from './evidenceMapLayers';

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
  measurement = null,
  measurementMode = false,
  onMeasurementPoint,
  captureEnabled = false,
  onCaptureReady,
}: {
  captureEnabled?: boolean;
  onCaptureReady?: (capture: ((signal: AbortSignal) => Promise<Blob>) | null) => void;
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
  measurement?: MapState['measurement'];
  measurementMode?: boolean;
  onMeasurementPoint?: (point: Position) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const engine = useRef<MapEngine | null>(null);
  const [mapError, setMapError] = useState(false);
  const initial = useRef({ camera, projection, basemap });
  const supportsPoint = legacyDisplay ? hasLegacyEvidencePoint : hasEvidencePoint;
  const captureReady = useEffectEvent((capture: ((signal: AbortSignal) => Promise<Blob>) | null) =>
    onCaptureReady?.(capture),
  );
  const cameraChanged = useEffectEvent((value: MapCamera) => onCamera(value));
  const viewportReady = useEffectEvent((read: (() => MapBounds | null) | null) =>
    onViewportReady?.(read),
  );
  const areaClicked = useEffectEvent((event: unknown) => {
    if (measurementMode) {
      const point = areaClickPoint(event);
      if (point) onMeasurementPoint?.(point);
      return;
    }
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
    const map = createMapLibreEngine({
      captureEnabled,
      authHeader: () => useAuthStore.getState().accessToken,
    });
    map.setProjection(initial.current.projection);
    map.setBaseLayer(initial.current.basemap);
    map.mount(container.current);
    map.setLite(true);
    const stopErrors = map.on('error', () => setMapError(true));
    engine.current = map;
    if (captureEnabled) captureReady((signal) => map.captureImage(signal));
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
      captureReady(null);
      map.setLayers([]);
      map.destroy();
      engine.current = null;
    };
  }, [supported, captureEnabled]);
  useEffect(() => {
    engine.current?.setProjection(projection);
  }, [projection]);
  useEffect(() => {
    engine.current?.setBaseLayer(basemap);
  }, [basemap]);
  useEffect(() => {
    engine.current?.setLayers(
      evidenceMapLayers({
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
      }),
    );
  }, [
    evidence,
    projection,
    selected,
    onSelect,
    overlays,
    footprints,
    aoi,
    areaMode,
    measurement,
    measurementMode,
    sourceGeometry,
    supportsPoint,
    legacyDisplay,
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
        className={captureEnabled ? undefined : 'h-96 w-full'}
        style={captureEnabled ? { width: 1200, height: 800, pointerEvents: 'none' } : undefined}
      />
    </>
  );
}
