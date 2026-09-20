import type { Position } from '@/lib/map/geoJsonTypes';
import type { CorridorSimplification } from '@/lib/map/terrainCorridorSimplification';

export function CorridorPathPreview({
  original,
  approximation,
}: {
  original: readonly Position[];
  approximation: CorridorSimplification;
}) {
  const longitude = original.map((point) => point[0]),
    latitude = original.map((point) => point[1]);
  const west = Math.min(...longitude),
    east = Math.max(...longitude);
  const south = Math.min(...latitude),
    north = Math.max(...latitude);
  const series = (points: readonly Position[]) =>
    points
      .map(
        ([lon, lat]) =>
          `${(10 + (280 * (lon - west)) / Math.max(0.000001, east - west)).toFixed(2)},${(130 - (120 * (lat - south)) / Math.max(0.000001, north - south)).toFixed(2)}`,
      )
      .join(' ');
  return (
    <figure className="space-y-2 rounded border border-white/20 p-2">
      <svg
        viewBox="0 0 300 140"
        className="w-full"
        role="img"
        aria-label="Original and simplified route comparison"
      >
        <title>Original route in grey and simplified route in cyan</title>
        <polyline points={series(original)} fill="none" stroke="#a5a9b0" strokeWidth="4" />
        <polyline
          points={series(approximation.points)}
          fill="none"
          stroke="#6ccbff"
          strokeWidth="2"
          strokeDasharray="5 3"
        />
      </svg>
      <figcaption>
        {approximation.originalCount.toLocaleString('en-GB')} original points (grey) →{' '}
        {approximation.points.length} points (cyan). {approximation.lengthKm.toFixed(2)} km. Maximum
        verified original-path deviation bound: {approximation.deviationBoundM} m. This diagram is a
        comparison, not a basemap.
      </figcaption>
    </figure>
  );
}
