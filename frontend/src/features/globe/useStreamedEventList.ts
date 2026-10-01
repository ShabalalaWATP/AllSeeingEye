import { startTransition, useEffect, useState } from 'react';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { useEventsStore } from '@/stores/events';

/**
 * The mirror's event list for the map's derived views. Ordinary stream deltas re-render
 * through a transition, so React can pause that rebuild for clicks, typing and control
 * changes. Every delta still reaches the view: a newer list replaces a pending one, and the
 * store itself is never held back. Clearing the mirror, and the first records after a clear,
 * apply at once, so a stream gap or access change never leaves stale records on screen.
 */
export function useStreamedEventList(): LiveEvent[] {
  const [list, setList] = useState(() => useEventsStore.getState().list);
  useEffect(() => {
    const show = (next: LiveEvent[], previous: LiveEvent[]) => {
      if (next.length === 0 || previous.length === 0) setList(next);
      else
        startTransition(() => {
          setList(next);
        });
    };
    const unsubscribe = useEventsStore.subscribe((state, previous) => {
      if (state.list !== previous.list) show(state.list, previous.list);
    });
    // Catch a change between the first render and this subscription; an unchanged list
    // bails out without rendering.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setList(useEventsStore.getState().list);
    return unsubscribe;
  }, []);
  return list;
}
