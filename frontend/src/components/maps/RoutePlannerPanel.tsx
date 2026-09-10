import { useEffect, useRef, useState, useSyncExternalStore } from 'react';

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
import { MapToolIntro } from './MapToolIntro';
import { RouteTravelMode } from './RouteTravelMode';
import { RoutePlannerResult, RouteProviderDetails } from './RoutePlannerResult';
import './routePlanner.css';

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
    <section aria-label="Route planner" className="map-tool-workspace route-planner">
      <MapToolIntro
        title="Route planner"
        description="Choose your stops and travel mode, then calculate the route."
        status={busy ? 'Calculating' : route ? 'Route ready' : 'Plan a journey'}
        statusActive={busy || !!route}
      />
      <RouteTravelMode
        value={mode}
        onChange={(value) => {
          clearResult();
          setMode(value);
        }}
      />
      <section className="map-tool-section" aria-label="Route stops">
        <div className="route-stop-heading">
          <h3 className="map-tool-section-title">Stops</h3>
          <span className="route-stop-count">{waypoints.length} / 8</span>
        </div>
        <label className="map-tool-field">
          <span>Enter stops using</span>
          <select
            aria-label="Enter stops using"
            value={inputMode}
            onChange={(event) => setInputMode(event.target.value as typeof inputMode)}
            className="map-tool-input"
          >
            <option value="address">Addresses and places</option>
            <option value="coordinates">Coordinates</option>
          </select>
        </label>
        {inputMode === 'address' && (
          <p className="map-tool-help route-search-privacy">
            Search sends the entered place to Photon (komoot). Only press Search for public
            locations; avoid confidential addresses. Nothing is sent while typing.
          </p>
        )}
        <div className="route-waypoint-list">
          {waypoints.map((point, index) => (
            <RouteWaypoint
              key={`${point.id}:${inputMode}`}
              point={point}
              index={index}
              title={
                index === 0
                  ? 'Start'
                  : index === waypoints.length - 1
                    ? 'Destination'
                    : `Via ${index}`
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
        </div>
        <div className="map-tool-actions route-stop-actions">
          <button
            type="button"
            className="map-tool-secondary"
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
          </button>
          <button
            type="button"
            className="map-tool-text-button"
            onClick={() => {
              clearResult();
              setWaypoints((rows) => [...rows].reverse());
            }}
          >
            Reverse stops
          </button>
        </div>
      </section>
      <section className="map-tool-section route-submit" aria-label="Calculate route">
        <p className="map-tool-help">
          Calculate route sends these coordinates to FOSSGIS. The provider may log requests. No
          device location is requested. Routes are not saved.
        </p>
        {capabilities?.configuration_message && (
          <Alert tone="warning" className="map-tool-notice">
            {capabilities.configuration_message}
          </Alert>
        )}
        {capabilities?.available && (
          <p className="map-tool-help route-provider-contact">
            App operator:{' '}
            <a href={`mailto:${capabilities.operator_contact}`} className="underline">
              {capabilities.operator_contact}
            </a>
          </p>
        )}
        <div className="map-tool-actions">
          <button
            type="button"
            className="map-tool-primary"
            disabled={busy || !capabilities?.available}
            onClick={() => void calculate()}
          >
            {busy ? 'Calculating…' : 'Calculate route'}
          </button>
          <button type="button" className="map-tool-text-button" onClick={clearResult}>
            {busy ? 'Cancel' : 'Clear route'}
          </button>
        </div>
        {error && (
          <Alert tone="error" className="map-tool-notice">
            {error}
          </Alert>
        )}
      </section>
      {route && <RoutePlannerResult route={route} />}
      <RouteProviderDetails />
    </section>
  );
}
