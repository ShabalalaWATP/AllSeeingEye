import { useSyncExternalStore } from 'react';

export type AssistantBounds = readonly [number, number, number, number];
export interface AssistantMapSelection {
  kind: 'event' | 'camera' | 'infrastructure';
  id: string;
  title: string;
}
export interface AssistantMapContext {
  bounds: AssistantBounds | null;
  selected: AssistantMapSelection | null;
}
type Reader = () => AssistantMapContext;
type Focus = (point: { lon: number; lat: number }) => void;
const listeners = new Set<() => void>();
let reader: Reader | null = null;
let focus: Focus | null = null;
let queuedFocus: { point: { lon: number; lat: number }; at: number } | null = null;
let revision = 0;
const notify = () => {
  revision++;
  for (const listener of listeners) listener();
};

/** Register a tiny on-demand reader, never another copy of map events or a map engine. */
export function registerAssistantMapContext(next: Reader, locate?: Focus) {
  reader = next;
  focus = locate ?? null;
  if (queuedFocus && focus && Date.now() - queuedFocus.at < 5000) focus(queuedFocus.point);
  queuedFocus = null;
  notify();
  return () => {
    if (reader === next) {
      reader = null;
      focus = null;
      notify();
    }
  };
}
export function clearAssistantMapFocus() {
  queuedFocus = null;
}
export function locateAssistantPoint(point: { lon: number; lat: number }) {
  if (
    !Number.isFinite(point.lon) ||
    !Number.isFinite(point.lat) ||
    Math.abs(point.lon) > 180 ||
    Math.abs(point.lat) > 90
  )
    return;
  if (focus) focus(point);
  else queuedFocus = { point, at: Date.now() };
}
export function refreshAssistantMapContext() {
  notify();
}
export function readAssistantMapContext(): AssistantMapContext | null {
  const context = reader?.();
  if (!context) return null;
  const bounds = context.bounds;
  const valid =
    bounds &&
    bounds.every(Number.isFinite) &&
    bounds[0] >= -180 &&
    bounds[0] <= 180 &&
    bounds[2] >= -180 &&
    bounds[2] <= 180 &&
    bounds[1] >= -90 &&
    bounds[3] <= 90 &&
    bounds[3] > bounds[1];
  return { bounds: valid ? bounds : null, selected: context.selected };
}
export function useAssistantMapAvailability() {
  useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    () => revision,
  );
  return readAssistantMapContext();
}
