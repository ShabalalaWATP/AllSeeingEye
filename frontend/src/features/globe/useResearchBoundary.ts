import { useEffect, useMemo, useState } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';
import { researchAreaLayers } from '@/lib/map/researchAreaLayers';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import type { MapDrawing } from './useMapDrawing';

/** An adopted boundary keeps canonical geometry, including holes, without redrawing it. */
export function useResearchBoundary(drawing: MapDrawing, flat: boolean) {
  const [imported, setImported] = useState<LocalCollection | null>(null);
  useEffect(() => {
    const clear = () => setImported(null);
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (
        next.user?.id !== previous.user?.id ||
        next.status !== previous.status ||
        next.user?.role !== previous.user?.role ||
        next.user?.is_active !== previous.user?.is_active
      )
        clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  const boundary = useMemo(() => {
    if (imported) return { area: imported, areaError: null };
    if (drawing.picking || !drawing.anchors.length) return { area: null, areaError: null };
    try {
      return { area: researchAreaGeometry(drawing.shape, drawing.anchors), areaError: null };
    } catch (error) {
      return {
        area: null,
        areaError: error instanceof Error ? error.message : 'Draw a valid area.',
      };
    }
  }, [imported, drawing.picking, drawing.shape, drawing.anchors]);
  const layers = useMemo(
    () =>
      imported
        ? [
            new GeoJsonLayer({
              id: 'research-area-imported',
              data: imported,
              filled: true,
              stroked: true,
              getFillColor: [121, 216, 235, 30],
              getLineColor: [121, 216, 235, 245],
              getLineWidth: 2,
              lineWidthUnits: 'pixels',
              pickable: false,
              wrapLongitude: flat,
            }),
          ]
        : researchAreaLayers(drawing.shape, drawing.displayedAnchors, flat),
    [imported, drawing.shape, drawing.displayedAnchors, flat],
  );
  return {
    ...boundary,
    imported,
    layers,
    adopt: (value: LocalCollection) => {
      const text = JSON.stringify(value);
      if (new TextEncoder().encode(text).length > 16 * 1024)
        throw new Error('Research boundaries must be at most 16 KiB.');
      const parsed = parseLocalGeoJson(text);
      if (
        parsed.vertices > 256 ||
        !parsed.canonical.features.length ||
        parsed.canonical.features.some(
          (feature) =>
            feature.geometry.type !== 'Polygon' && feature.geometry.type !== 'MultiPolygon',
        )
      )
        throw new Error('Choose an area with at most 256 vertices.');
      drawing.setPicking(false);
      setImported(parsed.canonical);
    },
    clear: () => {
      setImported(null);
      drawing.clear();
    },
    discardImported: () => setImported(null),
  };
}
