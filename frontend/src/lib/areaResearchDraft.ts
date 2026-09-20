/** One account-scoped map research draft. No coordinates, questions or consent enter storage. */
import { create } from 'zustand';
import type { Profile } from './api/profile';
import { parseLocalGeoJson } from './map/localGeoJson';
import type { LocalCollection } from './map/geoJsonTypes';
import { subscribeWorkspaceAccess } from './workspaceAccess';
import { useAuthStore } from '@/stores/auth';

export type AreaPeriod = 1 | 3 | 7 | 14;
export interface AreaResearchInterval {
  since: string;
  until: string;
}
interface Handoff {
  area: LocalCollection;
  preferences: Profile | null;
}
interface Draft {
  question: string;
  days: AreaPeriod;
  mode: Profile['research_mode'];
  sourceIds: string[] | null;
  interval: AreaResearchInterval | null;
  handoff: Handoff | null;
  setQuestion: (question: string) => void;
  setDays: (days: AreaPeriod) => void;
  setMode: (mode: Profile['research_mode']) => void;
  setSourceIds: (sourceIds: string[] | null) => void;
}
const empty = () => ({
  question: '',
  days: 1 as const,
  mode: 'detailed' as const,
  sourceIds: null,
  interval: null,
  handoff: null,
});
export const useAreaResearchDraft = create<Draft>((set) => ({
  ...empty(),
  setQuestion: (question) => set({ question }),
  setDays: (days) => set({ days, interval: null }),
  setMode: (mode) => set({ mode }),
  setSourceIds: (sourceIds) => set({ sourceIds: sourceIds === null ? null : [...sourceIds] }),
}));

export function prepareAreaResearchHandoff(
  area: LocalCollection,
  interval?: AreaResearchInterval,
  preferences: Profile | null = null,
) {
  const session = useAuthStore.getState();
  if (session.status !== 'authenticated' || !session.user?.is_active)
    throw new Error('Sign in before preparing area research.');
  const text = JSON.stringify(area);
  if (new TextEncoder().encode(text).byteLength > 16384)
    throw new Error('Area research geometry must fit within 16 KiB.');
  const parsed = parseLocalGeoJson(text);
  if (parsed.vertices > 256) throw new Error('Area research is limited to 256 vertices.');
  const geometry = parsed.canonical;
  if (
    !geometry.features.length ||
    geometry.features.some(
      (feature) => !['Polygon', 'MultiPolygon'].includes(feature.geometry.type),
    )
  )
    throw new Error('Area research requires a polygon boundary.');
  const now = Date.now();
  const days = useAreaResearchDraft.getState().days;
  const period = interval ?? {
    since: new Date(now - days * 86400000).toISOString(),
    until: new Date(now).toISOString(),
  };
  const duration = Date.parse(period.until) - Date.parse(period.since);
  if (!Number.isFinite(duration) || duration <= 0 || duration > 14 * 86400000)
    throw new Error('Choose an area research interval of up to 14 days.');
  useAreaResearchDraft.setState({
    handoff: { area: geometry, preferences: preferences ? structuredClone(preferences) : null },
    interval: { ...period },
  });
}
export const readAreaResearchHandoff = () => useAreaResearchDraft.getState().handoff;
subscribeWorkspaceAccess(() => useAreaResearchDraft.setState(empty()));
useAuthStore.subscribe((state, previous) => {
  if (
    state.status !== previous.status ||
    state.user?.id !== previous.user?.id ||
    state.user?.role !== previous.user?.role ||
    state.user?.is_active !== previous.user?.is_active
  )
    useAreaResearchDraft.setState(empty());
});
