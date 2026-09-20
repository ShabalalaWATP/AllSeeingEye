import { useState } from 'react';
import type { LocalCollection, Position } from '@/lib/map/geoJsonTypes';
import { createResearchCorridor } from '@/lib/map/terrainCorridor';
import {
  simplifyCorridorPath,
  type CorridorSimplification,
} from '@/lib/map/terrainCorridorSimplification';
import { CorridorPathPreview } from './CorridorPathPreview';

export function CorridorResearchPanel({
  points,
  onResearchArea,
}: {
  points: readonly Position[];
  onResearchArea: (area: LocalCollection) => void;
}) {
  const [width, setWidth] = useState('1');
  const [error, setError] = useState<string | null>(null);
  const [deviation, setDeviation] = useState('250');
  const [simplified, setSimplified] = useState<{
    source: readonly Position[];
    result: CorridorSimplification;
  } | null>(null);
  const [accepted, setAccepted] = useState(false);
  const approximation = simplified?.source === points ? simplified.result : null;
  const researchPoints = approximation && accepted ? approximation.points : points;
  return (
    <section className="map-tool-workspace" aria-label="Corridor research">
      <p>Create a research boundary around a drawn path or measured route.</p>
      <p>
        {points.length.toLocaleString('en-GB')} available path points. Boundaries use 2–32 points
        and a path no longer than 200 km.
      </p>
      {points.length > 32 && (
        <div className="space-y-2 rounded border border-white/20 p-2">
          <p>
            This route needs simplification. Review the approximation and choose whether to use it.
            The original route is unchanged.
          </p>
          <label className="block">
            Allowed route deviation (m)
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              type="number"
              min="50"
              max="5000"
              step="50"
              value={deviation}
              onChange={(event) => {
                setDeviation(event.target.value);
                setSimplified(null);
                setAccepted(false);
              }}
            />
          </label>
          <button
            type="button"
            className="rounded border border-white/20 px-3 py-2"
            onClick={() => {
              setAccepted(false);
              setSimplified(null);
              setError(null);
              try {
                setSimplified({
                  source: points,
                  result: simplifyCorridorPath(points, Number(deviation)),
                });
              } catch (failure) {
                setError(
                  failure instanceof Error ? failure.message : 'Could not simplify this route.',
                );
              }
            }}
          >
            Prepare simplified route preview
          </button>
          {approximation && (
            <>
              <CorridorPathPreview original={points} approximation={approximation} />
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(event) => setAccepted(event.target.checked)}
                />
                Use this approximate path for the corridor
              </label>
              <p className="text-muted">
                The deviation is an upper bound along the original geodesic path, not a
                location-accuracy claim. Simplification can change which observations the boundary
                includes.
              </p>
            </>
          )}
        </div>
      )}
      <label className="block">
        Distance on each side (km)
        <input
          className="mt-1 w-full rounded border border-white/20 bg-black p-2"
          type="number"
          min="0.01"
          max="20"
          step="0.1"
          value={width}
          onChange={(event) => {
            setWidth(event.target.value);
            setError(null);
          }}
        />
      </label>
      <p className="text-muted">
        The approximate boundary follows the path with rounded ends. Corners can extend beyond the
        chosen distance. Review the polygon before generating a report. Crossing or sharply turning
        paths may need a smaller width.
      </p>
      <button
        type="button"
        className="rounded border border-cyan/50 px-3 py-2 disabled:opacity-40"
        disabled={researchPoints.length < 2 || researchPoints.length > 32}
        onClick={() => {
          setError(null);
          try {
            if (!width.trim()) throw new Error('Enter the distance on each side.');
            const area = createResearchCorridor(researchPoints, Number(width));
            const feature = area.features[0];
            if (feature && approximation && accepted)
              feature.properties.label = `Approximate corridor, ${width} km each side; route deviation bound ${approximation.deviationBoundM} m`;
            onResearchArea(area);
          } catch (failure) {
            setError(failure instanceof Error ? failure.message : 'Could not create the corridor.');
          }
        }}
      >
        Preview corridor for research
      </button>
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
    </section>
  );
}
