/** One pending handoff, in memory only. Never put coordinates in URLs or browser storage. */
import { useSyncExternalStore } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from './workspaceAccess';
import { validateAreaBounds } from './map/areaGeometry';
import type { WatchAreaInput } from './map/areaWatchGeometry';
import { parseLocalGeoJson } from './map/localGeoJson';

export interface AreaWatchDraft extends WatchAreaInput {
  id: number;
  actor: string;
}
let pending: AreaWatchDraft | null = null;
let sequence = 0;
const listeners = new Set<() => void>();

function actorKey() {
  const { user, status } = useAuthStore.getState();
  return status === 'authenticated' && user?.is_active
    ? `${user.id}:${user.role}:${workspaceRevision()}`
    : null;
}
function notify() {
  for (const listener of listeners) listener();
}
export function clearAreaWatchDraft(id?: number) {
  if (pending && (id === undefined || pending.id === id)) {
    pending = null;
    notify();
  }
}
export function readAreaWatchDraft(): AreaWatchDraft | null {
  return pending?.actor === actorKey() ? pending : null;
}
export function prepareAreaWatch(input: WatchAreaInput) {
  const actor = actorKey();
  if (!actor) throw new Error('Sign in before preparing an area indicator.');
  const bounds = validateAreaBounds(input.bounds);
  if (!['rectangle', 'sketch-envelope', 'viewport', 'shape'].includes(input.source))
    throw new Error('Choose a supported area.');
  const geometry = input.geometry
    ? parseLocalGeoJson(JSON.stringify(input.geometry)).canonical
    : undefined;
  if (
    input.source === 'shape' &&
    (geometry?.features.length !== 1 ||
      !['Polygon', 'MultiPolygon'].includes(geometry.features[0]?.geometry.type ?? ''))
  )
    throw new Error('An exact watch needs one polygon boundary.');
  pending = Object.freeze({
    ...input,
    ...(geometry ? { geometry } : {}),
    bounds: Object.freeze(bounds),
    id: ++sequence,
    actor,
  });
  notify();
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export const useAreaWatchDraft = () => useSyncExternalStore(subscribe, readAreaWatchDraft);

subscribeWorkspaceAccess(() => clearAreaWatchDraft());
useAuthStore.subscribe((state, previous) => {
  if (
    state.status !== previous.status ||
    state.user?.id !== previous.user?.id ||
    state.user?.role !== previous.user?.role ||
    state.user?.is_active !== previous.user?.is_active
  )
    clearAreaWatchDraft();
});
