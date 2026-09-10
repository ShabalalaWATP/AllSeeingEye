import { useRef, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { searchNavigationPlaces } from '@/lib/api/navigationPlaces';
import type { NavigationPlace } from '@/lib/api/navigationPlaces';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import type { RouteWaypointValue } from './useRoutePlannerState';

interface Props {
  point: RouteWaypointValue;
  index: number;
  title: string;
  mode: 'address' | 'coordinates';
  removable: boolean;
  onChange: (point: RouteWaypointValue) => void;
  onRemove: () => void;
}

export function RouteWaypoint({ point, index, title, mode, removable, onChange, onRemove }: Props) {
  const request = useScopedRequest();
  const query = point.query;
  const addressInput = useRef<HTMLInputElement>(null);
  const located =
    point.lat.trim() !== '' &&
    point.lon.trim() !== '' &&
    Number.isFinite(Number(point.lat)) &&
    Number.isFinite(Number(point.lon)) &&
    Math.abs(Number(point.lat)) <= 90 &&
    Math.abs(Number(point.lon)) <= 180;
  const [results, setResults] = useState<NavigationPlace[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function search() {
    const signal = request();
    setBusy(true);
    setError(null);
    setResults(null);
    try {
      const found = await searchNavigationPlaces(query.trim(), signal);
      signal.throwIfAborted();
      setResults(found);
    } catch (reason) {
      if (!signal.aborted) setError(describeError(reason));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  }
  return (
    <fieldset className="route-waypoint">
      <legend>
        <span className="route-stop-number" aria-hidden="true">
          {index + 1}
        </span>
        <span>{title}</span>
        <span className="route-stop-state" data-ready={located}>
          {located ? 'Located' : 'Choose a stop'}
        </span>
      </legend>
      <div className="route-stop-content">
        {mode === 'address' ? (
          <>
            <label className="map-tool-field">
              Address or place
              <input
                aria-label={`${title} address or place`}
                ref={addressInput}
                value={query}
                maxLength={200}
                placeholder="Street, postcode, city or landmark"
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && query.trim().length >= 3 && !busy) {
                    event.preventDefault();
                    void search();
                  }
                }}
                onChange={(event) => {
                  request();
                  setBusy(false);
                  setResults(null);
                  setError(null);
                  onChange({ ...point, lat: '', lon: '', label: '', query: event.target.value });
                }}
                className="map-tool-input"
              />
            </label>
            <button
              type="button"
              className="map-tool-secondary route-address-search"
              disabled={busy || query.trim().length < 3}
              onClick={() => void search()}
            >
              {busy ? `Searching ${title.toLowerCase()}…` : `Search ${title.toLowerCase()}`}
            </button>
            {located && (
              <p className="route-selected-place" aria-live="polite">
                <svg
                  aria-hidden="true"
                  width="15"
                  height="15"
                  viewBox="0 0 20 20"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="m4 10 4 4 8-8" />
                </svg>
                <span>
                  <span className="route-selected-label">Selected:</span>
                  {point.label || `${point.lat}, ${point.lon}`}
                </span>
              </p>
            )}
            {results && (
              <div className="route-search-results" aria-label={`${title} address results`}>
                <p className="map-tool-help">
                  {results.length
                    ? 'Choose the correct match:'
                    : 'No matches. Add a city or postcode, or use coordinates.'}
                </p>
                <div>
                  {results.map((result, position) => (
                    <button
                      key={position}
                      type="button"
                      className="route-address-match"
                      onClick={() => {
                        onChange({
                          ...point,
                          lat: String(result.lat),
                          lon: String(result.lon),
                          label: result.label,
                          query: result.label,
                        });
                        setResults(null);
                        addressInput.current?.focus();
                      }}
                    >
                      {result.label}
                      <span className="map-tool-help">
                        {result.lat.toFixed(5)}, {result.lon.toFixed(5)}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {error && (
              <Alert tone="error" className="map-tool-notice">
                {error}
              </Alert>
            )}
          </>
        ) : (
          <div className="route-coordinate-fields">
            {(['lat', 'lon'] as const).map((axis) => (
              <label key={axis} className="map-tool-field">
                {axis === 'lat' ? 'Latitude' : 'Longitude'}
                <input
                  aria-label={`Waypoint ${index + 1} ${axis === 'lat' ? 'latitude' : 'longitude'}`}
                  value={point[axis]}
                  inputMode="decimal"
                  maxLength={20}
                  onChange={(event) =>
                    onChange({ ...point, label: '', query: '', [axis]: event.target.value })
                  }
                  className="map-tool-input"
                />
              </label>
            ))}
          </div>
        )}
        {removable && (
          <button
            type="button"
            className="map-tool-text-button route-remove-stop"
            onClick={onRemove}
          >
            Remove waypoint {index + 1}
          </button>
        )}
      </div>
    </fieldset>
  );
}
