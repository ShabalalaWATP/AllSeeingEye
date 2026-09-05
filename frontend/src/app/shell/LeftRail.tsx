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

const laterItems = [
  { label: 'Trackers', phase: 'Phase 3' },
  { label: 'Direction', phase: 'Phase 4' },
  { label: 'Reports', phase: 'Phase 2' },
];

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

function RailLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `${itemClass} ${isActive ? activeClass : idleClass}`}
    >
      {children}
    </NavLink>
  );
}

export function LeftRail() {
  const { mode, onGlobePage, showGlobe, showMap } = useViewNavigation();
  const isAdmin = useAuthStore(selectIsAdmin);
  const lite = useGlobeStore((state) => state.lite);

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-ground">
      <Link to="/" className="flex items-center gap-3 px-4 py-4">
        <BrandMark still={lite} />
        <Wordmark className="min-w-0 leading-snug" />
      </Link>
      <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 px-2">
        <RailButton active={onGlobePage && mode === 'globe'} onClick={showGlobe} shortcut="G">
          Globe
        </RailButton>
        <RailButton active={onGlobePage && mode === 'map'} onClick={showMap} shortcut="M">
          Map
        </RailButton>
        {laterItems.map((item) => (
          <button
            key={item.label}
            type="button"
            disabled
            className={`${itemClass} text-muted/60`}
            title={`Available in ${item.phase}`}
          >
            <span>{item.label}</span>
            <span className="font-mono text-[10px] uppercase tracking-wide">{item.phase}</span>
          </button>
        ))}
        {isAdmin ? (
          <div className="mt-4 flex flex-col gap-1">
            <div className="px-3 text-[11px] font-semibold uppercase tracking-wide text-muted">
              Admin
            </div>
            <RailLink to="/admin/requests">Account requests</RailLink>
            <RailLink to="/admin/users">Users</RailLink>
            <RailLink to="/admin/audit">Audit log</RailLink>
            <RailLink to="/admin/sources">Sources</RailLink>
          </div>
        ) : null}
      </nav>
    </aside>
  );
}
