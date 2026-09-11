import { Link, useLocation } from 'react-router';
import type { ReactNode } from 'react';

import { BrandMark } from '@/components/brand/BrandMark';
import { Wordmark } from '@/components/brand/Wordmark';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';

const itemClass =
  'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors';
const idleClass = 'text-muted hover:bg-surface-2 hover:text-text';
const activeClass = 'bg-surface-2 text-text';

function RailLink({
  to,
  children,
  onNavigate,
}: {
  to: string;
  children: ReactNode;
  onNavigate?: (() => void) | undefined;
}) {
  const { pathname } = useLocation();
  const active =
    pathname === to ||
    pathname.startsWith(`${to}/`) ||
    (to === '/research' && pathname.startsWith('/direction'));
  return (
    <Link
      to={to}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={`${itemClass} ${active ? activeClass : idleClass}`}
    >
      {children}
    </Link>
  );
}

export function LeftRail({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const isAdmin = useAuthStore(selectIsAdmin);
  const lite = useGlobeStore((state) => state.lite);

  return (
    <aside
      className={`flex min-h-0 flex-col bg-ground ${mobile ? 'w-full flex-1 overflow-hidden' : 'w-60 shrink-0 border-r border-line'}`}
    >
      <Link to="/" onClick={onNavigate} className="flex items-center gap-3 px-4 py-4">
        <BrandMark still={lite} />
        <Wordmark className="min-w-0 leading-snug" />
      </Link>
      <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 overflow-y-auto px-2 pb-4">
        <RailLink to="/" onNavigate={onNavigate}>
          Map
        </RailLink>
        <RailLink to="/trackers" onNavigate={onNavigate}>
          Live monitor
        </RailLink>
        <RailLink to="/research" onNavigate={onNavigate}>
          Research
        </RailLink>
        <RailLink to="/reports" onNavigate={onNavigate}>
          Saved reports
        </RailLink>
        <RailLink to="/sources" onNavigate={onNavigate}>
          Source catalogue
        </RailLink>
        <RailLink to="/warning" onNavigate={onNavigate}>
          Alerts
        </RailLink>
        <RailLink to="/teams" onNavigate={onNavigate}>
          Teams
        </RailLink>
        {isAdmin && (
          <div className="mt-4 border-t border-line pt-4">
            <RailLink to="/admin" onNavigate={onNavigate}>
              Administration
            </RailLink>
          </div>
        )}
      </nav>
    </aside>
  );
}
