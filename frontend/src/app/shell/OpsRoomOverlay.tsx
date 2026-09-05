import { useEffect, useState } from 'react';

import { BrandMark } from '@/components/brand/BrandMark';
import { fetchAlerts } from '@/lib/api/warning';
import type { Alert } from '@/lib/api/warning';
import { useGlobeStore } from '@/stores/globe';

const POLL_MS = 60_000;
const SHOWN = 3;

/** What the wall screen carries over the turning globe: the brand, an exit hint and live alerts. */
export function OpsRoomOverlay() {
  const lite = useGlobeStore((state) => state.lite);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const page = await fetchAlerts(24);
        if (!cancelled) setAlerts(page.items.filter((item) => item.acknowledged_at === null));
      } catch {
        // The strip simply stays as it was; the warning page shows the error.
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <>
      {alerts.length > 0 && (
        <aside
          aria-label="Unacknowledged alerts"
          className="pointer-events-none absolute top-3 right-3 z-20 flex w-80 flex-col gap-2"
        >
          {alerts.slice(0, SHOWN).map((item) => (
            <div
              key={item.id}
              className="rounded-card border border-critical/60 bg-ground/90 px-3 py-2 text-sm text-text shadow-lg"
            >
              <div className="font-medium">{item.title}</div>
              {item.summary !== '' && (
                <div className="mt-1 line-clamp-2 text-xs text-muted">{item.summary}</div>
              )}
            </div>
          ))}
          {alerts.length > SHOWN && (
            <div className="px-1 font-mono text-[11px] text-muted">
              {alerts.length - SHOWN} more on the warning page
            </div>
          )}
        </aside>
      )}
      <div className="pointer-events-none absolute bottom-3 left-3 z-20 flex items-center gap-3">
        <BrandMark still={lite} />
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted">
          Ops room · Esc to exit
        </div>
      </div>
    </>
  );
}
