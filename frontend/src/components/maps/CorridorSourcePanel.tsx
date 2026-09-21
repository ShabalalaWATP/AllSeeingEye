import { useState } from 'react';
import type { LocalCollection, Position } from '@/lib/map/geoJsonTypes';
import { CorridorResearchPanel } from './CorridorResearchPanel';

export interface CorridorSource {
  id: string;
  label: string;
  points: readonly Position[];
}

/** Source selection is independent of corridor geometry and approximation consent. */
export function CorridorSourcePanel({
  sources,
  onResearchArea,
}: {
  sources: readonly CorridorSource[];
  onResearchArea: (area: LocalCollection) => void;
}) {
  const routePoints = sources.find((source) => source.id === 'route')?.points;
  const defaultId = routePoints ? 'route' : sources[0]?.id;
  const [selection, setSelection] = useState({ id: defaultId, routePoints });
  // A newly calculated route is the current workflow's result. Other source choices
  // remain stable while the route and selected source still exist.
  if (
    selection.routePoints !== routePoints ||
    (selection.id !== defaultId && !sources.some((source) => source.id === selection.id))
  )
    setSelection({ id: defaultId, routePoints });
  const source = sources.find((value) => value.id === selection.id) ?? sources[0];
  if (!source)
    return (
      <p className="map-tool-help">
        Draw or measure a path, or calculate a route, to prepare corridor research.
      </p>
    );
  return (
    <section aria-label="Corridor path selection" className="map-tool-section">
      <label className="map-tool-field">
        <span>Corridor path source</span>
        <select
          className="map-tool-input"
          value={source.id}
          onChange={(event) => setSelection({ id: event.target.value, routePoints })}
        >
          {sources.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <p className="map-tool-help">Research will follow: {source.label}.</p>
      <CorridorResearchPanel points={source.points} onResearchArea={onResearchArea} />
    </section>
  );
}
