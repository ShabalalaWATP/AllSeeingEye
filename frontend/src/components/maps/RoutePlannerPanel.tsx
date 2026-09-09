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
import { RouteWaypoint } from './RouteWaypoint';
import { createRouteDraft } from './useRoutePlannerState';
import type { RoutePlannerDraft } from './useRoutePlannerState';

export interface RoutePlannerPanelProps {
  onRouteChange: (route: NavigationRoute | null) => void;
  initialWaypoints?: NavigationRequest['waypoints'];
  draft?: RoutePlannerDraft | null;
  onDraftChange?: (draft: RoutePlannerDraft) => void;
  result?: NavigationRoute | null;
}

/** Private route state remounts on an account or workspace authority change. */
export function RoutePlannerPanel(props: RoutePlannerPanelProps) {
  const user = useAuthStore((state) => state.user);
  const status = useAuthStore((state) => state.status);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <Planner key={`${status}:${user?.id}:${user?.role}:${revision}`} {...props} />;
}

function Planner({
  onRouteChange,
  initialWaypoints,
  draft: savedDraft,
  onDraftChange,
  result,
}: RoutePlannerPanelProps) {
  const request = useScopedRequest();
  const capabilityRequest = useScopedRequest();
  const changed = useRef(onRouteChange);
  useEffect(() => {
    changed.current = onRouteChange;
  }, [onRouteChange]);
  const [localDraft, setLocalDraft] = useState(() => createRouteDraft(initialWaypoints));
  const draft = savedDraft ?? localDraft;
  const { waypoints, inputMode, mode } = draft;
  const nextWaypointId = useRef(Math.max(8, ...waypoints.map((point) => point.id + 1)));
  const controlled = onDraftChange !== undefined;
  function updateDraft(patch: Partial<RoutePlannerDraft>) {
    const next = { ...draft, ...patch };
    setLocalDraft(next);
    onDraftChange?.(next);
  }
  const setWaypoints = (
    change: (rows: RoutePlannerDraft['waypoints']) => RoutePlannerDraft['waypoints'],
  ) => updateDraft({ waypoints: change(waypoints) });
  const setMode = (mode: RoutePlannerDraft['mode']) => updateDraft({ mode });
  const setInputMode = (inputMode: RoutePlannerDraft['inputMode']) => updateDraft({ inputMode });
  const [capabilities, setCapabilities] = useState<NavigationCapabilities | null>(null);
  const [localRoute, setRoute] = useState<NavigationRoute | null>(null);
  const route = result === undefined ? localRoute : result;
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
    return () => {
      if (!controlled) changed.current(null);
    };
  }, [capabilityRequest, controlled]);

  function clearResult() {
    request();
    setRoute(null);
    changed.current(null);
    setBusy(false);
    setError(null);
  }

  async function calculate() {
    clearResult();
    onDraftChange?.(draft);
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
      setError(
        inputMode === 'address'
          ? 'Search and select a match for every stop, or choose Coordinates.'
          : 'Enter valid latitude and longitude for every waypoint.',
      );
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
          Search for your start and destination, choose each match, then calculate your route.
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
      <label className="block space-y-1 text-xs">
        <span>Enter stops using</span>
        <select
          aria-label="Enter stops using"
          value={inputMode}
          onChange={(event) => setInputMode(event.target.value as typeof inputMode)}
          className="w-full rounded border border-line bg-surface-2 p-2"
        >
          <option value="address">Addresses and places</option>
          <option value="coordinates">Coordinates</option>
        </select>
      </label>
      {inputMode === 'address' && (
        <p className="text-xs text-muted">
          Search sends the entered place to Photon (komoot). Only press Search for public locations;
          avoid confidential addresses. Nothing is sent while typing.
        </p>
      )}
      {waypoints.map((point, index) => (
        <RouteWaypoint
          key={`${point.id}:${inputMode}`}
          point={point}
          index={index}
          title={
            index === 0 ? 'Start' : index === waypoints.length - 1 ? 'Destination' : `Via ${index}`
          }
          mode={inputMode}
          removable={waypoints.length > 2}
          onChange={(value) => {
            clearResult();
            setWaypoints((rows) => rows.map((row) => (row.id === point.id ? value : row)));
          }}
          onRemove={() => {
            clearResult();
            setWaypoints((rows) => rows.filter((row) => row.id !== point.id));
          }}
        />
      ))}
      <Button
        variant="secondary"
        disabled={waypoints.length >= 8}
        onClick={() => {
          clearResult();
          const id = nextWaypointId.current++;
          setWaypoints((rows) => [
            ...rows.slice(0, -1),
            { id, lat: '', lon: '', label: '', query: '' },
            ...rows.slice(-1),
          ]);
        }}
      >
        Add waypoint
      </Button>
      <Button
        variant="ghost"
        onClick={() => {
          clearResult();
          setWaypoints((rows) => [...rows].reverse());
        }}
      >
        Reverse stops
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
