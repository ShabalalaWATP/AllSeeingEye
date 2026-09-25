import { Link, NavLink } from 'react-router';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { BrandMark } from '@/components/brand/BrandMark';
import { adminOverview, adminSections, type AdminDestination } from '@/lib/adminNavigation';
import { useShellStore } from '@/stores/shell';

/** Administrator-only destinations. Research controls never appear in this rail. */
export function AdminNavigation({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const railCollapsed = useShellStore((state) => state.railCollapsed);
  const toggleRail = useShellStore((state) => state.toggleRail);
  const collapsed = railCollapsed && !mobile;
  return (
    <aside
      data-collapsed={collapsed ? 'true' : undefined}
      className={`flex min-h-0 flex-col bg-ground ${
        mobile
          ? 'w-full flex-1 overflow-hidden'
          : `shrink-0 border-r border-line/70 transition-[width] duration-200 ${collapsed ? 'w-[4.25rem]' : 'w-64'}`
      }`}
    >
      <Link
        to="/admin"
        onClick={onNavigate}
        title={collapsed ? 'Administration' : undefined}
        className={`flex items-center gap-3 border-b border-line/70 py-4 ${collapsed ? 'justify-center px-2' : 'px-4'}`}
      >
        <BrandMark size={collapsed ? 34 : 38} still />
        <span className={collapsed ? 'sr-only' : 'min-w-0 leading-tight'}>
          <span className="block truncate text-xs text-muted">The All Seeing Eye</span>
          <span className="mt-0.5 flex items-center gap-2 font-semibold">
            Administration
            <span className="rounded border border-ember/40 bg-ember/10 px-1 font-mono text-2xs tracking-widest text-ember uppercase">
              Ops
            </span>
          </span>
        </span>
      </Link>
      <nav
        aria-label="Administration"
        className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3"
      >
        <AdminLink item={adminOverview} collapsed={collapsed} onNavigate={onNavigate} />
        {adminSections.map((section) => (
          <div key={section.title} className="mt-3 flex flex-col gap-0.5">
            {collapsed ? (
              <span aria-hidden="true" className="mx-3 mb-1 border-t border-line/70" />
            ) : (
              <p className="px-3 pb-1 font-mono text-2xs tracking-[0.18em] text-muted/90 uppercase">
                {section.title}
              </p>
            )}
            {section.items.map((item) => (
              <AdminLink key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
            ))}
          </div>
        ))}
      </nav>
      <div className="border-t border-line/70 p-2">
        <Link
          to="/"
          onClick={onNavigate}
          aria-label={collapsed ? 'Return to research' : undefined}
          title={collapsed ? 'Return to research' : undefined}
          className={`flex min-h-11 items-center gap-3 rounded-lg text-sm text-muted transition-colors hover:bg-surface hover:text-text ${collapsed ? 'justify-center' : 'px-3'}`}
        >
          <AdminIcon name="back" size={18} />
          {collapsed ? null : <span>Return to research</span>}
        </Link>
        {mobile ? null : (
          <button
            type="button"
            onClick={toggleRail}
            aria-pressed={collapsed}
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            className={`mt-0.5 flex min-h-10 w-full items-center gap-3 rounded-lg text-xs text-muted transition-colors hover:bg-surface hover:text-text ${collapsed ? 'justify-center' : 'px-3'}`}
          >
            <AdminIcon name={collapsed ? 'expand' : 'collapse'} size={16} />
            {collapsed ? null : <span>Collapse</span>}
          </button>
        )}
      </div>
    </aside>
  );
}

function AdminLink({
  item,
  collapsed,
  onNavigate,
}: {
  item: AdminDestination;
  collapsed: boolean;
  onNavigate?: (() => void) | undefined;
}) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/admin'}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        `group relative flex min-h-11 items-center gap-3 rounded-lg text-sm transition-colors ${collapsed ? 'justify-center px-0' : 'px-3'} ${
          isActive
            ? 'bg-surface-2 text-text before:absolute before:top-2 before:bottom-2 before:left-0 before:w-0.5 before:rounded-full before:bg-ember'
            : 'text-muted hover:bg-surface hover:text-text'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <AdminIcon
            name={item.icon}
            size={18}
            className={isActive ? 'text-ember' : 'text-muted group-hover:text-text'}
          />
          <span className={collapsed ? 'sr-only' : 'truncate'}>{item.label}</span>
        </>
      )}
    </NavLink>
  );
}
