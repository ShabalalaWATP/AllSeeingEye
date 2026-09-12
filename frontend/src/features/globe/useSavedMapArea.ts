import { useCallback, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { GeoJsonLayer } from '@deck.gl/layers';
import { fetchAois } from '@/lib/api/direction';
import type { Country } from '@/lib/api/geoSchemas';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { geometryBounds } from '@/lib/map/geometryBounds';
import type { LocalGeometry } from '@/lib/map/geoJsonTypes';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** Only a record ID travels in the link; current server access determines its geometry. */
export function useSavedMapArea(
  engine: GlobeEngineHandle,
  countries: Record<string, Country>,
  flat: boolean,
) {
  const [params, setParams] = useSearchParams();
  const id = params.get('area');
  const loader = useCallback(async () => (id ? fetchAois() : []), [id]);
  const resource = useScopedResource(loader);
  const area = resource.data?.find((item) => item.id === id) ?? null;
  const outline = useMemo(() => {
    if (!area) return null;
    const boxes =
      area.kind === 'bbox' && area.bbox
        ? [area.bbox]
        : area.countries.flatMap((iso) => (countries[iso] ? [countries[iso].bounds] : []));
    if (!boxes.length || boxes.length > 250) return null;
    try {
      const features = boxes.flatMap(([west, south, east, north]) => {
        if (west === undefined || south === undefined || east === undefined || north === undefined)
          throw new Error('Incomplete area bounds.');
        return rectangleArea({ west, south, east, north }).features;
      });
      const polygons = features.flatMap(({ geometry }) =>
        geometry.type === 'Polygon'
          ? [geometry.coordinates]
          : geometry.type === 'MultiPolygon'
            ? geometry.coordinates
            : [],
      );
      const geometry: LocalGeometry = { type: 'MultiPolygon', coordinates: polygons };
      return { geometry, bounds: geometryBounds(geometry) };
    } catch {
      return null;
    }
  }, [area, countries]);
  const flyTo = engine.flyTo;
  useEffect(() => {
    if (!outline) return;
    const { west, south, east, north } = outline.bounds;
    const width = east >= west ? east - west : 360 - west + east;
    flyTo({
      center: [((west + width / 2 + 540) % 360) - 180, (south + north) / 2],
      zoom: Math.max(
        0,
        Math.min(12, Math.log2(360 / Math.max(width, (north - south) * 1.5, 0.01)) - 1),
      ),
    });
  }, [outline, flyTo]);
  const layers = useMemo(
    () =>
      outline
        ? [
            new GeoJsonLayer({
              id: 'saved-area-of-interest',
              data: { type: 'Feature', properties: {}, geometry: outline.geometry },
              getFillColor: [121, 216, 235, 25],
              getLineColor: [121, 216, 235, 240],
              getLineWidth: 2,
              lineWidthUnits: 'pixels',
              pickable: false,
              wrapLongitude: flat,
            }),
          ]
        : [],
    [outline, flat],
  );
  return {
    id,
    area,
    layers,
    message: resource.loading
      ? 'Loading saved area…'
      : resource.error || !area
        ? 'This saved area is unavailable or you no longer have access.'
        : !outline
          ? 'Area boundaries are unavailable.'
          : area.kind === 'countries'
            ? 'Country extents are approximate, not national borders.'
            : 'Saved research area',
    close: () => {
      const next = new URLSearchParams(params);
      next.delete('area');
      setParams(next, { replace: true });
    },
  };
}
