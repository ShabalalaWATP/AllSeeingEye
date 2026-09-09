import { useEffect, useRef, useState, useSyncExternalStore } from 'react';

import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { calculateNavigationRoute, fetchNavigationCapabilities } from '@/lib/api/navigation';
import type {
  NavigationCapabilities,
  NavigationRequest,
  NavigationRoute,
} from '@/lib/api/navigation';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export interface RoutePlannerPanelProps {
  onRouteChange: (route: NavigationRoute | null) => void;
  initialWaypoints?: NavigationRequest['waypoints'];
}

/** Private route state remounts on an account or workspace authority change. */
export function RoutePlannerPanel(props: RoutePlannerPanelProps) {
  const user = useAuthStore((state) => state.user);
  const status = useAuthStore((state) => state.status);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <Planner key={`${status}:${user?.id}:${user?.role}:${revision}`} {...props} />;
}

function Planner({ onRouteChange, initialWaypoints }: RoutePlannerPanelProps) {
  const request = useScopedRequest();
  const capabilityRequest = useScopedRequest();
  const changed = useRef(onRouteChange);
  useEffect(() => {
    changed.current = onRouteChange;
  }, [onRouteChange]);
  const [waypoints, setWaypoints] = useState(() =>
    (
      initialWaypoints ?? [
        { lat: 0, lon: 0 },
        { lat: 0, lon: 0 },
      ]
    ).map((point) => ({
      lat: initialWaypoints ? String(point.lat) : '',
      lon: initialWaypoints ? String(point.lon) : '',
    })),
  );
  const [mode, setMode] = useState<NavigationRequest['mode']>('driving');
  const [capabilities, setCapabilities] = useState<NavigationCapabilities | null>(null);
  const [route, setRoute] = useState<NavigationRoute | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const signal = capabilityRequest();
    void fetchNavigationCapabilities(signal)
      .then((result) => {
        if (!signal.aborted) setCapabilities(result);
      })
      .catch((reason: unknown) => {
        if (!signal.aborted) setError(describeError(reason));
      });
    return () => changed.current(null);
  }, [capabilityRequest]);

  function clearResult() {
    request();
    setRoute(null);
    changed.current(null);
    setBusy(false);
    setError(null);
  }

  async function calculate() {
    clearResult();
    const points = waypoints.map((point) => ({ lat: Number(point.lat), lon: Number(point.lon) }));
    if (
      waypoints.some((point) => !point.lat.trim() || !point.lon.trim()) ||
      points.some(
        (point) =>
          !Number.isFinite(point.lat) ||
          !Number.isFinite(point.lon) ||
          Math.abs(point.lat) > 90 ||
          Math.abs(point.lon) > 180,
      )
    ) {
      setError('Enter valid latitude and longitude for every waypoint.');
      return;
    }
    const signal = request();
    setBusy(true);
    try {
      const result = await calculateNavigationRoute({ mode, waypoints: points }, signal);
      signal.throwIfAborted();
      setRoute(result);
      changed.current(result);
    } catch (reason) {
      if (!signal.aborted) setError(describeError(reason));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  }

  return (
    <section aria-label="Route planner" className="space-y-3 p-3 text-sm">
      <div>
        <h2 className="font-semibold">Route planner</h2>
        <p className="mt-1 text-xs text-muted">
          Plan a journey between coordinates. This is an estimate, not live navigation.
        </p>
      </div>
      <label className="block space-y-1">
        <span>Travel mode</span>
        <select
          aria-label="Travel mode"
          value={mode}
          onChange={(event) => {
            clearResult();
            setMode(event.target.value as NavigationRequest['mode']);
          }}
          className="w-full rounded border border-line bg-surface-2 p-2"
        >
          <option value="driving">Driving</option>
          <option value="walking">Walking</option>
          <option value="cycling">Cycling</option>
        </select>
      </label>
      {waypoints.map((point, index) => (
        <fieldset key={index} className="rounded border border-line p-2">
          <legend className="px-1 text-xs text-muted">
            {index === 0
              ? 'Start'
              : index === waypoints.length - 1
                ? 'Destination'
                : `Via ${index}`}
          </legend>
          <div className="grid grid-cols-2 gap-2">
            {(['lat', 'lon'] as const).map((axis) => (
              <label key={axis} className="text-xs">
                {axis === 'lat' ? 'Latitude' : 'Longitude'}
                <input
                  aria-label={`Waypoint ${index + 1} ${axis === 'lat' ? 'latitude' : 'longitude'}`}
                  value={point[axis]}
                  inputMode="decimal"
                  maxLength={20}
                  onChange={(event) => {
                    clearResult();
                    setWaypoints((rows) =>
                      rows.map((row, position) =>
                        position === index ? { ...row, [axis]: event.target.value } : row,
                      ),
                    );
                  }}
                  className="mt-1 w-full rounded border border-line bg-surface-2 p-2"
                />
              </label>
            ))}
          </div>
          {waypoints.length > 2 && (
            <Button
              variant="ghost"
              onClick={() => {
                clearResult();
                setWaypoints((rows) => rows.filter((_, position) => position !== index));
              }}
            >
              Remove waypoint {index + 1}
            </Button>
          )}
        </fieldset>
      ))}
      <Button
        variant="secondary"
        disabled={waypoints.length >= 8}
        onClick={() => {
          clearResult();
          setWaypoints((rows) => [...rows.slice(0, -1), { lat: '', lon: '' }, ...rows.slice(-1)]);
        }}
      >
        Add waypoint
      </Button>
      <p className="text-xs text-muted">
        Calculate route sends these coordinates to FOSSGIS. The provider may log requests. No device
        location is requested. Routes are not saved.
      </p>
      {capabilities?.configuration_message && (
        <Alert tone="warning">{capabilities.configuration_message}</Alert>
      )}
      {capabilities?.available && (
        <p className="text-xs text-muted">
          App operator:{' '}
          <a href={`mailto:${capabilities.operator_contact}`} className="underline">
            {capabilities.operator_contact}
          </a>
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button disabled={busy || !capabilities?.available} onClick={() => void calculate()}>
          {busy ? 'Calculating…' : 'Calculate route'}
        </Button>
        <Button variant="ghost" onClick={clearResult}>
          {busy ? 'Cancel' : 'Clear route'}
        </Button>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {route && (
        <div className="space-y-2">
          <p role="status" className="font-medium">
            {route.distance_km.toFixed(1)} km · approximately{' '}
            {Math.ceil(route.duration_seconds / 60)} min
          </p>
          <p className="text-xs text-muted">{route.limitations}</p>
          <details>
            <summary className="cursor-pointer">Directions ({route.steps.length})</summary>
            <ol className="mt-2 max-h-64 list-decimal space-y-2 overflow-auto pl-5">
              {route.steps.map((step, index) => (
                <li key={index}>
                  {step.instruction}
                  <span className="block text-xs text-muted">{step.distance_km.toFixed(2)} km</span>
                </li>
              ))}
            </ol>
          </details>
        </div>
      )}
      <p className="text-xs text-muted">
        Routing: FOSSGIS Valhalla. Data ©{' '}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          OpenStreetMap contributors
        </a>{' '}
        (
        <a
          href="https://opendatacommons.org/licenses/odbl/index.html"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          ODbL
        </a>
        ).{' '}
        <a
          href="https://www.openstreetmap.org/fixthemap"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          Fix the map
        </a>{' '}
        ·{' '}
        <a
          href="https://fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          Provider terms
        </a>
      </p>
    </section>
  );
}
