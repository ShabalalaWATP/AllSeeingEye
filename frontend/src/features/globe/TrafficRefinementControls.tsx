import { useId } from 'react';
import {
  TRAFFIC_QUERY_LIMIT,
  type TrafficKind,
  type TrafficRefinementsState,
  type AircraftGroundFilter,
} from './trafficRefinements';
import '@/components/maps/mapTool.css';

export function TrafficRefinementControls({
  kind,
  state,
}: {
  kind: TrafficKind;
  state: TrafficRefinementsState;
}) {
  const id = useId();
  return (
    <fieldset className="space-y-3 border-t border-line pt-3">
      <legend className="text-xs text-muted">Refine the map and list</legend>
      <label className="map-tool-field" htmlFor={`${id}-query`}>
        Search {kind}
        <input
          id={`${id}-query`}
          type="search"
          value={state.query}
          onChange={(event) => state.setQuery(event.target.value)}
          maxLength={TRAFFIC_QUERY_LIMIT}
          placeholder={kind === 'aircraft' ? 'Callsign, registration or ICAO' : 'Name, MMSI or IMO'}
          className="map-tool-input"
        />
      </label>
      <label className="map-tool-field" htmlFor={`${id}-source`}>
        Position source
        <select
          id={`${id}-source`}
          value={state.source}
          onChange={(event) => state.setSource(event.target.value)}
          className="map-tool-input"
        >
          <option value="">All loaded sources</option>
          {state.source && !state.sources.includes(state.source) && (
            <option value={state.source}>{state.source} (not currently loaded)</option>
          )}
          {state.sources.map((source) => (
            <option key={source} value={source}>
              {source}
            </option>
          ))}
        </select>
      </label>
      {kind === 'aircraft' && (
        <label className="map-tool-field" htmlFor={`${id}-ground`}>
          Reported aircraft status
          <select
            id={`${id}-ground`}
            value={state.ground}
            onChange={(event) => state.setGround(event.target.value as AircraftGroundFilter)}
            className="map-tool-input"
          >
            <option value="all">Any status</option>
            <option value="airborne">Airborne</option>
            <option value="ground">On ground</option>
            <option value="unknown">Unknown status</option>
          </select>
        </label>
      )}
      <p className="text-2xs leading-relaxed text-muted">
        Searches loaded positions in the current time and geographic scope. Source choices remain
        available while other filters change.
        {kind === 'aircraft' && ' Unknown means the feed supplied no usable ground-status flag.'}
      </p>
      {state.searching && (
        <p role="status" className="text-xs text-muted">
          Updating traffic results…
        </p>
      )}
    </fieldset>
  );
}
