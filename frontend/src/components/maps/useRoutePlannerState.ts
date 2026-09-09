import { useEffect, useState } from 'react';
import type { NavigationRequest, NavigationRoute } from '@/lib/api/navigation';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export interface RouteWaypointValue {
  id: number;
  lat: string;
  lon: string;
  label: string;
  query: string;
}
export interface RoutePlannerDraft {
  waypoints: RouteWaypointValue[];
  mode: NavigationRequest['mode'];
  inputMode: 'address' | 'coordinates';
}

export function createRouteDraft(initial?: NavigationRequest['waypoints']): RoutePlannerDraft {
  return {
    mode: 'driving',
    inputMode: initial ? 'coordinates' : 'address',
    waypoints: (
      initial ?? [
        { lat: 0, lon: 0 },
        { lat: 0, lon: 0 },
      ]
    ).map((point, id) => ({
      id,
      lat: initial ? String(point.lat) : '',
      lon: initial ? String(point.lon) : '',
      label: '',
      query: '',
    })),
  };
}

/** The coordinator keeps form and overlay together while a tool panel is closed. */
export function useRoutePlannerState() {
  const [draft, setDraft] = useState<RoutePlannerDraft | null>(null);
  const [route, setRoute] = useState<NavigationRoute | null>(null);
  useEffect(() => {
    const clear = () => {
      setDraft(null);
      setRoute(null);
    };
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (
        next.user?.id !== previous.user?.id ||
        next.status !== previous.status ||
        next.user?.role !== previous.user?.role
      )
        clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  return { draft, setDraft, route, setRoute };
}
