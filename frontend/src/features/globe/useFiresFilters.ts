import { useEffect, useMemo, useState } from 'react';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import {
  countFires,
  DEFAULT_FIRES_OPTIONS,
  fireKind,
  matchesFires,
  type FiresOptions,
} from '@/lib/hazards';
import { useEventsStore } from '@/stores/events';

/** Remember fire source choices independently of the Fires master switch and hazard refinements. */
export function useFiresFilters(events: readonly LiveEvent[]) {
  const [enabled, setEnabled] = useState(false);
  const [options, setOptions] = useState<FiresOptions>(DEFAULT_FIRES_OPTIONS);
  const updateOptions = (patch: Partial<FiresOptions>) =>
    setOptions((previous) => ({ ...previous, ...patch }));
  const counts = useMemo(() => countFires(events), [events]);
  const filtered = useMemo(
    () => events.filter((event) => matchesFires(event, options, enabled)),
    [events, options, enabled],
  );
  const selectedId = useEventsStore((state) => state.selectedId);
  const select = useEventsStore((state) => state.select);
  useEffect(() => {
    const selected = events.find((event) => event.id === selectedId);
    if (selected && fireKind(selected) !== null && !matchesFires(selected, options, enabled))
      select(null);
  }, [events, selectedId, select, options, enabled]);
  return {
    enabled,
    toggleEnabled: () => setEnabled((previous) => !previous),
    options,
    updateOptions,
    counts,
    filtered,
  };
}
