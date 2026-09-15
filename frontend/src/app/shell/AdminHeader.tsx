import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { Button } from '@/components/ui/Button';
import { adminLocation } from '@/lib/adminNavigation';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

import { AdminNavigation } from './AdminNavigation';
import { NavigationDialog } from './NavigationDialog';
import { PersonalLinks } from './PersonalLinks';

/** Administration deliberately has no research alerts or globe controls. */
export function AdminHeader({ narrow }: { narrow: boolean }) {
  const { key, pathname } = useLocation();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const { run, busy } = useAsyncAction(async () => {
    await logout();
    await navigate('/login', { replace: true });
  });
  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line/70 bg-ground/80 px-2 backdrop-blur sm:px-5">
        <div className="flex min-w-0 items-center gap-1.5">
          {narrow && (
            <Button
              variant="ghost"
              className="min-h-11 px-2"
              aria-label="Open administration navigation"
              aria-haspopup="dialog"
              onClick={() => setOpenedAt(key)}
            >
              <AdminIcon name="menu" />
            </Button>
          )}
          <AdminBreadcrumb pathname={pathname} />
        </div>
        <div className="flex min-w-0 items-center gap-1 text-sm sm:gap-2">
          <SessionContext />
          <PersonalLinks />
          <Button variant="ghost" className="min-h-11" busy={busy} onClick={() => void run()}>
            Logout
          </Button>
        </div>
      </header>
      {narrow && openedAt === key && (
        <NavigationDialog label="Administration navigation" onClose={() => setOpenedAt(null)}>
          <AdminNavigation mobile onNavigate={() => setOpenedAt(null)} />
        </NavigationDialog>
      )}
    </>
  );
}

function AdminBreadcrumb({ pathname }: { pathname: string }) {
  const location = adminLocation(pathname);
  const page = location?.page;
  const atOverview = page === undefined || page.to === '/admin';
  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex min-w-0 items-center gap-1.5 text-sm">
        <li className="hidden shrink-0 font-mono text-[10px] tracking-[0.2em] text-muted uppercase sm:block">
          {atOverview ? (
            <span aria-current="page">Administration</span>
          ) : (
            <Link to="/admin" className="rounded hover:text-text">
              Administration
            </Link>
          )}
        </li>
        {location?.section == null ? null : (
          <li className="hidden min-w-0 items-center gap-1.5 text-muted xl:flex">
            <span aria-hidden="true">/</span>
            <span className="truncate">{location.section}</span>
          </li>
        )}
        {atOverview ? (
          <li className="truncate font-medium sm:hidden">Administration</li>
        ) : (
          <li className="flex min-w-0 items-center gap-1.5">
            <span aria-hidden="true" className="hidden text-muted sm:inline">
              /
            </span>
            <span aria-current="page" className="truncate font-medium">
              {page.label}
            </span>
          </li>
        )}
      </ol>
    </nav>
  );
}

/** The admin area mounts only after the server re-verifies this administrator session. */
function SessionContext() {
  const user = useAuthStore((state) => state.user);
  if (user === null) return null;
  return (
    <Link
      to="/admin/security"
      aria-label="Verified administrator session: security settings"
      title="The server verified this administrator session. Administrator sessions require multi-factor verification. Open security settings."
      className="hidden min-h-11 items-center gap-2 rounded-md px-2 text-muted hover:bg-surface-2 hover:text-text md:inline-flex"
    >
      <span className="flex size-7 items-center justify-center rounded-full border border-good/40 bg-good/10 text-good">
        <AdminIcon name="shield" size={14} />
      </span>
      <span className="hidden flex-col text-left leading-tight lg:flex">
        <span className="text-[11px] text-good">Verified session</span>
        <span className="text-[11px]">Administrator</span>
      </span>
    </Link>
  );
}
