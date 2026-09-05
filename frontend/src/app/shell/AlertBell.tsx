import { useEffect, useState } from 'react';
import { Link } from 'react-router';

import { fetchAlerts } from '@/lib/api/warning';

const POLL_MS = 60_000;

/** Unacknowledged alerts from the last day, refreshed every minute; a link to the warning page. */
export function AlertBell() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const page = await fetchAlerts(24);
        if (!cancelled) setCount(page.unacknowledged);
      } catch {
        // The bell stays quiet when the count cannot be fetched; the page shows the error.
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const label = count === null ? 'Alerts' : `Alerts, ${String(count)} unacknowledged`;
  return (
    <Link
      to="/warning"
      aria-label={label}
      className="flex items-center gap-1 rounded-md px-2 py-1 text-muted hover:bg-surface-2 hover:text-text"
    >
      <span>Alerts</span>
      {count !== null && count > 0 && (
        <span className="rounded-full bg-ember px-1.5 font-mono text-[10px] text-ground">
          {count}
        </span>
      )}
    </Link>
  );
}
