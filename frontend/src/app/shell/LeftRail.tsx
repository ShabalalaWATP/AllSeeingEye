import { useId } from 'react';
import { Link } from 'react-router';

import { BrandMark } from '@/components/brand/BrandMark';
import { MotionToggle } from '@/components/brand/MotionToggle';
import { Wordmark } from '@/components/brand/Wordmark';
import {
  administrationDestination,
  workspaceHome,
  workspaceSections,
} from '@/lib/workspaceNavigation';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { useShellStore } from '@/stores/shell';
import { useWorkspaceReturnStore } from '@/stores/workspaceReturn';

import { RailItem } from './RailLinks';
import { ChevronIcon, RailIcon } from './railIcons';

export function LeftRail({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const isAdmin = useAuthStore(selectIsAdmin);
  const lite = useGlobeStore((state) => state.lite);
  const railCollapsed = useShellStore((state) => state.railCollapsed);
  const toggleRail = useShellStore((state) => state.toggleRail);
  const openPalette = useShellStore((state) => state.openPalette);
  const collapsed = railCollapsed && !mobile;
  const railId = useId();

  return (
    <aside
      id={railId}
      data-collapsed={collapsed ? 'true' : undefined}
      className={`flex min-h-0 flex-col bg-ground ${
        mobile
          ? 'w-full flex-1 overflow-hidden'
          : `shrink-0 border-r border-line/70 transition-[width] duration-200 ${collapsed ? 'w-[4.25rem]' : 'w-[13.5rem]'}`
      }`}
    >
      <Link
        to="/"
        onClick={onNavigate}
        title={collapsed ? 'The All Seeing Eye' : undefined}
        className={`flex items-center gap-3 py-3.5 ${collapsed ? 'justify-center px-2' : 'px-3'}`}
      >
        {/* The wordmark names the link, so the mark itself stays silent. */}
        <BrandMark size={collapsed ? 34 : 38} still={lite} decorative />
        <Wordmark className={collapsed ? 'sr-only' : 'min-w-0 leading-snug'} />
      </Link>
      <MotionToggle compact={collapsed} className="px-2 pb-2" />
      <nav aria-label="Primary" className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 pb-3">
        {/* The mobile dialog leads with the way to administration, so it never needs a scroll. */}
        {isAdmin && mobile && (
          <AdministrationGroup collapsed={false} onNavigate={onNavigate} first />
        )}
        <button
          type="button"
          onClick={() => {
            onNavigate?.();
            openPalette();
          }}
          title={collapsed ? 'Find anything (Ctrl K)' : undefined}
          className={`group mb-1 flex min-h-10 items-center gap-3 rounded-lg border border-line/70 text-sm text-muted transition-colors hover:bg-surface hover:text-text ${collapsed ? 'justify-center px-0' : 'px-3'}`}
        >
          <RailIcon name="search" className="text-muted group-hover:text-text" />
          <span className={collapsed ? 'sr-only' : 'min-w-0 flex-1 truncate text-left'}>
            Find anything
          </span>
          {!collapsed && (
            <span aria-hidden="true" className="shrink-0 font-mono text-2xs text-muted">
              Ctrl K
            </span>
          )}
        </button>
        <ul className="flex flex-col gap-0.5">
          <RailItem item={workspaceHome} collapsed={collapsed} onNavigate={onNavigate} />
        </ul>
        {workspaceSections.map((section, index) => {
          // A section of one destination is named by that destination, not a heading.
          const headingId = section.items.length > 1 ? `${railId}-section-${index}` : undefined;
          return (
            <div key={section.title} className="mt-3 flex flex-col gap-0.5">
              {collapsed || headingId === undefined ? (
                <span aria-hidden="true" className="mx-3 mb-1 border-t border-line/70" />
              ) : (
                <p
                  id={headingId}
                  className="px-3 pb-1 font-mono text-2xs tracking-[0.18em] text-muted uppercase"
                >
                  {section.title}
                </p>
              )}
              <ul
                aria-labelledby={collapsed ? undefined : headingId}
                aria-label={collapsed || headingId === undefined ? section.title : undefined}
                className="flex flex-col gap-0.5"
              >
                {section.items.map((item) => (
                  <RailItem
                    key={item.to}
                    item={item}
                    collapsed={collapsed}
                    onNavigate={onNavigate}
                  />
                ))}
              </ul>
            </div>
          );
        })}
        {isAdmin && !mobile && (
          <AdministrationGroup collapsed={collapsed} onNavigate={onNavigate} />
        )}
      </nav>
      {!mobile && (
        <div className="border-t border-line/70 p-2">
          <button
            type="button"
            onClick={toggleRail}
            aria-expanded={!collapsed}
            aria-controls={railId}
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            title={`${collapsed ? 'Expand' : 'Collapse'} navigation ([)`}
            className={`flex min-h-10 w-full items-center gap-3 rounded-lg text-xs text-muted transition-colors hover:bg-surface hover:text-text ${collapsed ? 'justify-center' : 'px-3'}`}
          >
            <ChevronIcon direction={collapsed ? 'right' : 'left'} />
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      )}
    </aside>
  );
}

/**
 * Administration is a separate workspace, so it sits in its own headed group apart from
 * every research section, and opens on the administration page visited last.
 */
function AdministrationGroup({
  collapsed,
  onNavigate,
  first = false,
}: {
  collapsed: boolean;
  onNavigate?: (() => void) | undefined;
  first?: boolean;
}) {
  const headingId = useId();
  const target = useWorkspaceReturnStore((state) => state.admin);
  return (
    <div
      className={`flex flex-col gap-0.5 border-line/70 ${first ? 'mb-2 border-b pb-3' : 'mt-3 border-t pt-3'}`}
    >
      {collapsed ? null : (
        <p
          id={headingId}
          className="px-3 pb-1 font-mono text-2xs tracking-[0.18em] text-ember uppercase"
        >
          Switch workspace
        </p>
      )}
      <ul
        aria-labelledby={collapsed ? undefined : headingId}
        aria-label={collapsed ? 'Switch workspace' : undefined}
        className="flex flex-col gap-0.5"
      >
        <RailItem
          item={{ ...administrationDestination, to: target }}
          collapsed={collapsed}
          onNavigate={onNavigate}
        />
      </ul>
    </div>
  );
}
