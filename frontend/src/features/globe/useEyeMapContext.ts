import { useEffect, useRef, useSyncExternalStore } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Camera } from '@/lib/api/cameras';
import {
  registerAssistantMapContext,
  refreshAssistantMapContext,
  type AssistantMapTarget,
} from '@/lib/assistantMapContext';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { InfrastructureSelection } from './infrastructure/useInfrastructure';

/** Chat reads the camera only on demand; live feed updates never rerender the chat panel. */
export function useEyeMapContext(
  engine: GlobeEngineHandle,
  enabled: boolean,
  event: LiveEvent | null,
  cameras: { selected: Camera | null },
  infrastructure: { selected: InfrastructureSelection | null },
  selectSource?: (target: AssistantMapTarget) => boolean,
) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  const selected = cameras.selected
    ? { kind: 'camera' as const, id: cameras.selected.id, title: cameras.selected.title }
    : infrastructure.selected
      ? {
          kind: 'infrastructure' as const,
          id: infrastructure.selected.item.id,
          title: infrastructure.selected.item.name,
        }
      : event
        ? { kind: 'event' as const, id: event.id, title: event.title }
        : null;
  const latest = useRef(selected);
  const id = selected?.id,
    title = selected?.title,
    kind = selected?.kind;
  useEffect(() => {
    latest.current = selected;
  });
  useEffect(() => {
    refreshAssistantMapContext();
  }, [id, title]);
  useEffect(() => {
    if (!enabled) return;
    const userId = useAuthStore.getState().user?.id;
    const current = () =>
      useAuthStore.getState().user?.id === userId && workspaceRevision() === revision;
    return registerAssistantMapContext(
      () => {
        if (useAuthStore.getState().user?.id !== userId || workspaceRevision() !== revision)
          return { bounds: null, selected: null };
        const bounds = engine.getViewportBounds?.();
        return {
          bounds: bounds ? [bounds.west, bounds.south, bounds.east, bounds.north] : null,
          selected: latest.current
            ? { ...latest.current, title: latest.current.title.slice(0, 160) }
            : null,
        };
      },
      (point) => {
        if (current()) engine.flyTo({ center: [point.lon, point.lat], zoom: 6 });
      },
      (target) => (current() ? (selectSource?.(target) ?? false) : false),
    );
  }, [enabled, engine, actor, revision, kind, selectSource]);
}
