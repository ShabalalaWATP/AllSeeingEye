import { create } from 'zustand';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { CyberKindFilter } from '@/lib/cyber';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from './auth';
import { useEventsStore } from './events';

export function cyberAuthority(): string {
  const { status, user } = useAuthStore.getState();
  return `${status}:${user?.id}:${user?.role}:${user?.is_active}:${workspaceRevision()}`;
}

interface CyberMapFocus {
  authority: string;
  country: string | null;
  event: LiveEvent | null;
}

interface CyberFilters {
  kind: CyberKindFilter;
  query: string;
  countryContext: boolean;
  pending: CyberMapFocus | null;
  setKind: (kind: CyberKindFilter) => void;
  setQuery: (query: string) => void;
  setCountryContext: (shown: boolean) => void;
  consumeFocus: () => void;
  reset: () => void;
}

// The Cyber master layer still starts off. Enabling it must show the available
// country references without requiring a second, hidden opt-in.
const defaults = { kind: 'all' as const, query: '', countryContext: true, pending: null };

/** Session-only filters shared by the cyber workspace and both map projections. */
export const useCyberFiltersStore = create<CyberFilters>()((set) => ({
  ...defaults,
  setKind: (kind) => set({ kind }),
  setQuery: (query) => set({ query }),
  setCountryContext: (countryContext) => set({ countryContext }),
  consumeFocus: () => set({ pending: null }),
  reset: () => set(defaults),
}));

useAuthStore.subscribe((next, previous) => {
  if (
    next.status !== previous.status ||
    next.user?.id !== previous.user?.id ||
    next.user?.role !== previous.user?.role ||
    next.user?.is_active !== previous.user?.is_active
  )
    useCyberFiltersStore.getState().reset();
});
subscribeWorkspaceAccess(() => useCyberFiltersStore.getState().reset());

/** Prepare an explicit map visit without publishing page snapshots into the live mirror. */
export function prepareCyberMap({
  country = null,
  days = 2,
  kind = 'all',
  query = '',
  event,
}: {
  country?: string | null;
  days?: number;
  kind?: CyberKindFilter;
  query?: string;
  event?: LiveEvent;
} = {}): '/' {
  const events = useEventsStore.getState();
  events.setCountry(country);
  events.setWindow(Math.min(14, Math.max(1, days)) * 24);
  if (events.hidden.includes('cyber')) events.toggleCategory('cyber');
  useCyberFiltersStore.setState({
    kind,
    query,
    countryContext: true,
    pending: { authority: cyberAuthority(), country, event: event ?? null },
  });
  return '/';
}
