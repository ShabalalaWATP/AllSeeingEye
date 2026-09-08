import { useEffect, useState } from 'react';
import { fetchJamMap, type JamMap } from '@/lib/api/aviation';
export function useInterference(enabled: boolean) {
  const [map, setMap] = useState<JamMap>({ cells: [], updated_at: null });
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const load = () => {
      void fetchJamMap().then(
        (value) => {
          if (!cancelled) setMap(value);
        },
        () => undefined,
      );
    };
    load();
    const timer = window.setInterval(load, 5 * 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [enabled]);
  return map;
}
