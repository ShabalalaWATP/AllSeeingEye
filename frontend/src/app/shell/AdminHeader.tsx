import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';

import { AdminIcon } from '@/components/admin/AdminIcon';
import { Button } from '@/components/ui/Button';
import { adminLocation } from '@/lib/adminNavigation';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

import { AccountMenu } from './AccountMenu';
import { AdminNavigation } from './AdminNavigation';
import { NavigationDialog } from './NavigationDialog';
import { PersonalLinks } from './PersonalLinks';
import { WorkspaceSwitch } from './WorkspaceSwitch';

/**
 * Administration deliberately has no research alerts or globe controls. An ember accent
 * bar and the Administration badge mark this workspace apart from research, and the
 * Research switch stays outside every menu. Narrow screens gather the personal links and
 * Logout into the account menu, as the research top bar does.
 */
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
      <header
        data-workspace="admin"
        className="relative flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line/70 bg-ground/80 px-2 backdrop-blur before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-0.5 before:bg-ember sm:px-5"
      >
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
          <WorkspaceSwitch to="research" />
          {narrow ? (
            <AccountMenu />
          ) : (
            <>
              <PersonalLinks />
              <Button variant="ghost" className="min-h-11" busy={busy} onClick={() => void run()}>
                Logout
              </Button>
            </>
          )}
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

// The badge names the workspace at every width; letter spacing opens up once there is room.
const BADGE =
  'inline-flex min-h-7 items-center rounded border border-ember/40 bg-ember/10 px-1.5 font-mono text-2xs tracking-normal text-ember uppercase sm:tracking-[0.18em]';

function AdminBreadcrumb({ pathname }: { pathname: string }) {
  const location = adminLocation(pathname);
  const page = location?.page;
  const atOverview = page === undefined || page.to === '/admin';
  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex min-w-0 items-center gap-1.5 text-sm">
        <li className="shrink-0">
          {atOverview ? (
            <span aria-current="page" className={BADGE}>
              Administration
            </span>
          ) : (
            <Link to="/admin" className={`${BADGE} hover:bg-ember/20`}>
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
        {atOverview ? null : (
          <li className="flex min-w-0 items-center gap-1.5">
            <span aria-hidden="true" className="text-muted">
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
      aria-label="Verified session Administrator: security settings"
      title="The server verified this administrator session. Administrator sessions require multi-factor verification. Open security settings."
      className="hidden min-h-11 items-center gap-2 rounded-md px-2 text-muted hover:bg-surface-2 hover:text-text md:inline-flex"
    >
      <span className="flex size-7 items-center justify-center rounded-full border border-good/40 bg-good/10 text-good">
        <AdminIcon name="shield" size={14} />
      </span>
      <span className="hidden flex-col text-left leading-tight lg:flex">
        <span className="text-2xs text-good">Verified session</span>
        <span className="text-2xs">Administrator</span>
      </span>
    </Link>
  );
}
