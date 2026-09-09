import { useState } from 'react';
import { Button } from '@/components/ui/Button';
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
    <fieldset className="rounded-lg border border-line bg-surface-2/40 p-3">
      <legend className="px-1 text-xs font-semibold text-accent">{title}</legend>
      {mode === 'address' ? (
        <>
          <label className="block text-xs">
            Address or place
            <input
              aria-label={`${title} address or place`}
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
              className="mt-1 w-full rounded border border-line bg-surface-2 p-2.5"
            />
          </label>
          <Button
            variant="secondary"
            disabled={busy || query.trim().length < 3}
            onClick={() => void search()}
          >
            {busy ? `Searching ${title.toLowerCase()}…` : `Search ${title.toLowerCase()}`}
          </Button>
          {point.lat && point.lon && (
            <p className="mt-2 text-xs text-accent">
              Selected: {point.label || `${point.lat}, ${point.lon}`}
            </p>
          )}
          {results && (
            <div className="mt-2 space-y-1" aria-label={`${title} address results`}>
              <p className="text-xs text-muted">
                {results.length
                  ? 'Choose the correct match:'
                  : 'No matches. Add a city or postcode, or use coordinates.'}
              </p>
              {results.map((result, position) => (
                <button
                  key={position}
                  type="button"
                  className="w-full rounded border border-line p-2 text-left text-xs hover:border-accent focus-visible:outline-accent"
                  onClick={() => {
                    onChange({
                      ...point,
                      lat: String(result.lat),
                      lon: String(result.lon),
                      label: result.label,
                      query: result.label,
                    });
                    setResults(null);
                  }}
                >
                  {result.label}
                  <span className="block text-muted">
                    {result.lat.toFixed(5)}, {result.lon.toFixed(5)}
                  </span>
                </button>
              ))}
            </div>
          )}
          {error && <Alert tone="error">{error}</Alert>}
        </>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {(['lat', 'lon'] as const).map((axis) => (
            <label key={axis} className="text-xs">
              {axis === 'lat' ? 'Latitude' : 'Longitude'}
              <input
                aria-label={`Waypoint ${index + 1} ${axis === 'lat' ? 'latitude' : 'longitude'}`}
                value={point[axis]}
                inputMode="decimal"
                maxLength={20}
                onChange={(event) =>
                  onChange({ ...point, label: '', query: '', [axis]: event.target.value })
                }
                className="mt-1 w-full rounded border border-line bg-surface-2 p-2.5"
              />
            </label>
          ))}
        </div>
      )}
      {removable && (
        <Button variant="ghost" onClick={onRemove}>
          Remove waypoint {index + 1}
        </Button>
      )}
    </fieldset>
  );
}
