import { useCallback } from 'react';

import { listAnnotationMonitors } from '@/lib/api/annotationMonitors';
import { fetchPlans } from '@/lib/api/direction';
import type { ApiError } from '@/lib/api/errors';
import { fetchBriefs } from '@/lib/api/researchBriefs';
import { fetchSchedules } from '@/lib/api/schedules';
import { fetchIndicators } from '@/lib/api/warning';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import {
  WATCH_GROUPS,
  summariseAlertRules,
  summariseAreaWatches,
  summariseBriefs,
  summariseMonitors,
  summarisePlans,
  summariseSubscriptions,
  type WatchGroupInfo,
  type WatchKind,
  type WatchSummary,
} from './watchModel';

export interface WatchGroupState extends WatchGroupInfo {
  readonly summary: WatchSummary | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

interface Loaded<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => Promise<void>;
}

function view<T>(resource: Loaded<T>, summarise: (data: T) => WatchSummary) {
  return {
    summary: resource.data === null ? null : summarise(resource.data),
    loading: resource.loading,
    error: resource.error,
    retry: () => void resource.reload(),
  };
}

/**
 * Loads every kind of standing watch the signed-in user can see, each through its own
 * existing list endpoint, so one failing list never hides the others. Area watches and
 * alert rules share the indicator list and split it by whether a rule has an area.
 */
export function useWatches(): readonly WatchGroupState[] {
  const { label } = useWorkspaces();
  const beginBriefs = useScopedRequest();
  const beginMonitors = useScopedRequest();
  const loadBriefs = useCallback(() => fetchBriefs(beginBriefs()), [beginBriefs]);
  const loadMonitors = useCallback(
    () => listAnnotationMonitors(0, beginMonitors()),
    [beginMonitors],
  );
  const schedules = useScopedResource(fetchSchedules);
  const indicators = useScopedResource(fetchIndicators);
  const plans = useScopedResource(fetchPlans);
  const briefs = useScopedResource(loadBriefs);
  const monitors = useScopedResource(loadMonitors);

  const views: Record<WatchKind, Omit<WatchGroupState, keyof WatchGroupInfo>> = {
    subscriptions: view(schedules, (rows) => summariseSubscriptions(rows, label)),
    alertRules: view(indicators, (rows) => summariseAlertRules(rows, label)),
    areaWatches: view(indicators, (rows) => summariseAreaWatches(rows, label)),
    plans: view(plans, (rows) => summarisePlans(rows, label)),
    briefs: view(briefs, (page) => summariseBriefs(page, label)),
    monitors: view(monitors, (page) => summariseMonitors(page, label)),
  };
  return WATCH_GROUPS.map((group) => ({ ...group, ...views[group.kind] }));
}
