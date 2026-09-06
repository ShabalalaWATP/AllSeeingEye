import { Link } from 'react-router';

import { useShellAlerts } from './useShellAlerts';

/** Unacknowledged alerts from the last day, refreshed every minute; a link to the warning page. */
export function AlertBell() {
  const count = useShellAlerts()?.unacknowledged ?? null;

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
