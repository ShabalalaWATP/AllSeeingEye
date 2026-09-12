import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

import { AdminNavigation } from './AdminNavigation';
import { NavigationDialog } from './NavigationDialog';
import { PersonalLinks } from './PersonalLinks';

/** Administration deliberately has no research alerts or globe controls. */
export function AdminHeader({ narrow }: { narrow: boolean }) {
  const { key } = useLocation();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const { run, busy } = useAsyncAction(async () => {
    await logout();
    await navigate('/login', { replace: true });
  });
  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line px-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          {narrow && (
            <Button
              variant="ghost"
              className="min-h-11 px-2"
              aria-label="Open administration navigation"
              aria-haspopup="dialog"
              onClick={() => setOpenedAt(key)}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                aria-hidden="true"
              >
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </Button>
          )}
          <p className="truncate font-mono text-xs uppercase tracking-wide text-muted">
            Administration
          </p>
        </div>
        <div className="flex min-w-0 items-center gap-3 text-sm">
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
