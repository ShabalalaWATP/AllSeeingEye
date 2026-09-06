import { Link, NavLink } from 'react-router';
import type { ReactNode } from 'react';

import { BrandMark } from '@/components/brand/BrandMark';
import { Wordmark } from '@/components/brand/Wordmark';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';

import { useViewNavigation } from './useViewNavigation';

const itemClass =
  'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors';
const idleClass = 'text-muted hover:bg-surface-2 hover:text-text';
const activeClass = 'bg-surface-2 text-text';

function RailButton({
  active,
  onClick,
  shortcut,
  children,
}: {
  active: boolean;
  onClick: () => void;
  shortcut: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`${itemClass} ${active ? activeClass : idleClass}`}
    >
      <span>{children}</span>
      <kbd className="font-mono text-[10px] text-muted" aria-label={`Shortcut ${shortcut}`}>
        {shortcut}
      </kbd>
    </button>
  );
}

function RailLink({
  to,
  children,
  onNavigate,
}: {
  to: string;
  children: ReactNode;
  onNavigate?: (() => void) | undefined;
}) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) => `${itemClass} ${isActive ? activeClass : idleClass}`}
    >
      {children}
    </NavLink>
  );
}

export function LeftRail({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const { mode, onGlobePage, showGlobe, showMap } = useViewNavigation();
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
        <RailButton
          active={onGlobePage && mode === 'globe'}
          onClick={() => {
            showGlobe();
            onNavigate?.();
          }}
          shortcut="G"
        >
          Globe
        </RailButton>
        <RailButton
          active={onGlobePage && mode === 'map'}
          onClick={() => {
            showMap();
            onNavigate?.();
          }}
          shortcut="M"
        >
          Map
        </RailButton>
        <RailLink to="/trackers" onNavigate={onNavigate}>
          Trackers
        </RailLink>
        <RailLink to="/reports" onNavigate={onNavigate}>
          Reports
        </RailLink>
        <RailLink to="/direction" onNavigate={onNavigate}>
          Direction
        </RailLink>
        <RailLink to="/warning" onNavigate={onNavigate}>
          Warning
        </RailLink>
        <RailLink to="/teams" onNavigate={onNavigate}>
          Teams
        </RailLink>
        {isAdmin ? (
          <div className="mt-4 flex flex-col gap-1">
            <div className="px-3 text-[11px] font-semibold uppercase tracking-wide text-muted">
              Admin
            </div>
            <RailLink to="/admin/requests" onNavigate={onNavigate}>
              Account requests
            </RailLink>
            <RailLink to="/admin/users" onNavigate={onNavigate}>
              Users
            </RailLink>
            <RailLink to="/admin/audit" onNavigate={onNavigate}>
              Audit log
            </RailLink>
            <RailLink to="/admin/sources" onNavigate={onNavigate}>
              Sources
            </RailLink>
            <RailLink to="/admin/llm" onNavigate={onNavigate}>
              Models
            </RailLink>
            <RailLink to="/admin/security" onNavigate={onNavigate}>
              Security
            </RailLink>
          </div>
        ) : null}
      </nav>
    </aside>
  );
}
