import type { TerrainStudy } from '@/lib/map/terrainAnalysis';

export function TerrainProfileChart({
  study,
  highlighted,
  onHighlight,
}: {
  study: TerrainStudy;
  highlighted: number;
  onHighlight: (index: number) => void;
}) {
  const samples = study.samples;
  const low = study.minimumM ?? 0,
    high = Math.max(low + 1, study.maximumM ?? 1);
  const distance = samples.at(-1)?.distanceM ?? 1;
  const points = samples.map((sample) =>
    sample.elevationM === null
      ? null
      : `${(30 + (278 * sample.distanceM) / distance).toFixed(2)},${(115 - (95 * (sample.elevationM - low)) / (high - low)).toFixed(2)}`,
  );
  const segments: string[][] = [[]];
  for (const point of points) {
    if (point === null) segments.push([]);
    else segments.at(-1)?.push(point);
  }
  const selected = samples[Math.max(0, highlighted)];
  return (
    <figure className="space-y-2 rounded border border-white/20 p-2">
      <svg
        viewBox="0 0 320 142"
        role="img"
        aria-label="Sampled ground elevation profile"
        className="w-full"
      >
        <title>Ground elevation along the selected geodesic</title>
        <text x="0" y="12" fill="currentColor" fontSize="10">
          {high.toFixed(0)} m
        </text>
        <text x="0" y="128" fill="currentColor" fontSize="10">
          {low.toFixed(0)} m
        </text>
        {segments.map((segment, index) => (
          <polyline
            key={index}
            points={segment.join(' ')}
            fill="none"
            stroke="#6ccbff"
            strokeWidth="2"
          />
        ))}
        {highlighted >= 0 && selected && (
          <line
            x1={30 + (278 * selected.distanceM) / distance}
            x2={30 + (278 * selected.distanceM) / distance}
            y1="15"
            y2="120"
            stroke="#ffdd64"
          />
        )}
        <text x="200" y="138" fill="currentColor" fontSize="10">
          {(distance / 1000).toFixed(2)} km
        </text>
      </svg>
      <label className="block">
        Inspect sample
        <input
          className="w-full"
          type="range"
          min="0"
          max={samples.length - 1}
          value={Math.max(0, highlighted)}
          onChange={(event) => onHighlight(Number(event.target.value))}
        />
      </label>
      {selected && (
        <figcaption>
          {(selected.distanceM / 1000).toFixed(2)} km ·{' '}
          {selected.elevationM === null
            ? 'Unknown elevation'
            : `${selected.elevationM.toFixed(1)} m source elevation`}
          <br />
          {selected.position[1].toFixed(5)}, {selected.position[0].toFixed(5)}
        </figcaption>
      )}
    </figure>
  );
}
