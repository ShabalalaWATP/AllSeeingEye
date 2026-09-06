import { Link, NavLink } from 'react-router';

import { BrandMark } from '@/components/brand/BrandMark';
import { adminSections } from '@/lib/adminNavigation';

export function AdminNavigation({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <aside
      className={`flex min-h-0 flex-col bg-ground ${mobile ? 'w-full flex-1 overflow-hidden' : 'w-60 shrink-0 border-r border-line'}`}
    >
      <Link
        to="/admin"
        onClick={onNavigate}
        className="flex items-center gap-3 border-b border-line px-4 py-5"
      >
        <BrandMark still />
        <span className="min-w-0">
          <span className="block text-xs text-muted">The All Seeing Eye</span>
          <span className="block font-semibold">Administration</span>
        </span>
      </Link>
      <nav
        aria-label="Administration"
        className="flex flex-1 flex-col gap-1 overflow-y-auto px-2 py-4"
      >
        <AdminLink to="/admin" onNavigate={onNavigate}>
          Overview
        </AdminLink>
        {adminSections.map((section) => (
          <div key={section.title} className="mt-4">
            <p className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wide text-muted">
              {section.title}
            </p>
            {section.items.map((item) => (
              <AdminLink key={item.to} to={item.to} onNavigate={onNavigate}>
                {item.label}
              </AdminLink>
            ))}
          </div>
        ))}
      </nav>
      <Link
        to="/"
        onClick={onNavigate}
        className="flex min-h-14 shrink-0 items-center gap-2 border-t border-line px-5 text-sm text-muted hover:bg-surface-2 hover:text-text"
      >
        <span aria-hidden="true">←</span> Return to research
      </Link>
    </aside>
  );
}

function AdminLink({
  to,
  onNavigate,
  children,
}: {
  to: string;
  onNavigate?: (() => void) | undefined;
  children: string;
}) {
  return (
    <NavLink
      to={to}
      end={to === '/admin'}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex min-h-11 items-center rounded-md px-3 py-2 text-sm transition-colors ${isActive ? 'bg-surface-2 text-text' : 'text-muted hover:bg-surface-2 hover:text-text'}`
      }
    >
      {children}
    </NavLink>
  );
}
