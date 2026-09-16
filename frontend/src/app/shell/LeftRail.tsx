import { Link, useLocation } from 'react-router';

import { BrandMark } from '@/components/brand/BrandMark';
import { Wordmark } from '@/components/brand/Wordmark';
import {
  isWorkspacePath,
  workspaceHome,
  workspaceSections,
  type WorkspaceDestination,
} from '@/lib/workspaceNavigation';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { useShellStore } from '@/stores/shell';

import { ChevronIcon, RailIcon } from './railIcons';

const ADMIN_ITEM: WorkspaceDestination = {
  to: '/admin',
  label: 'Administration',
  description: 'The separate administration workspace.',
  icon: 'admin',
};

function RailLink({
  item,
  collapsed,
  onNavigate,
}: {
  item: WorkspaceDestination;
  collapsed: boolean;
  onNavigate?: (() => void) | undefined;
}) {
  const { pathname } = useLocation();
  const active = isWorkspacePath(item.to, pathname);
  return (
    <Link
      to={item.to}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      title={collapsed ? item.label : undefined}
      className={`group relative flex min-h-10 items-center gap-3 rounded-lg text-sm transition-colors ${collapsed ? 'justify-center px-0' : 'px-3'} ${
        active
          ? 'bg-surface-2 text-text before:absolute before:top-2 before:bottom-2 before:left-0 before:w-0.5 before:rounded-full before:bg-ember'
          : 'text-muted hover:bg-surface hover:text-text'
      }`}
    >
      <RailIcon
        name={item.icon}
        className={active ? 'text-ember' : 'text-muted group-hover:text-text'}
      />
      <span className={collapsed ? 'sr-only' : 'truncate'}>{item.label}</span>
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
  const railCollapsed = useShellStore((state) => state.railCollapsed);
  const toggleRail = useShellStore((state) => state.toggleRail);
  const collapsed = railCollapsed && !mobile;

  return (
    <aside
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
        <BrandMark size={collapsed ? 34 : 38} still={lite} />
        <Wordmark className={collapsed ? 'sr-only' : 'min-w-0 leading-snug'} />
      </Link>
      <nav aria-label="Primary" className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 pb-3">
        <RailLink item={workspaceHome} collapsed={collapsed} onNavigate={onNavigate} />
        {workspaceSections.map((section) => (
          <div key={section.title} className="mt-3 flex flex-col gap-0.5">
            {collapsed ? (
              <span aria-hidden="true" className="mx-3 mb-1 border-t border-line/70" />
            ) : (
              <p className="px-3 pb-1 font-mono text-[10px] tracking-[0.18em] text-muted/90 uppercase">
                {section.title}
              </p>
            )}
            {section.items.map((item) => (
              <RailLink key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
            ))}
          </div>
        ))}
        {isAdmin && (
          <div className="mt-3 border-t border-line/70 pt-3">
            <RailLink item={ADMIN_ITEM} collapsed={collapsed} onNavigate={onNavigate} />
          </div>
        )}
      </nav>
      {!mobile && (
        <div className="border-t border-line/70 p-2">
          <button
            type="button"
            onClick={toggleRail}
            aria-pressed={collapsed}
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
