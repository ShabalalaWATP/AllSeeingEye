import { Link, useLocation, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

import { AlertBell } from './AlertBell';
import { useGlobeStore } from '@/stores/globe';
import type { ViewMode } from '@/stores/globe';

export function viewTitle(pathname: string, mode: ViewMode): string {
  if (pathname === '/') return mode === 'globe' ? 'Globe' : 'Map';
  if (pathname.startsWith('/admin')) return 'Admin';
  if (pathname.startsWith('/reports')) return 'Reports';
  if (pathname.startsWith('/trackers')) return 'Trackers';
  if (pathname.startsWith('/direction')) return 'Direction';
  if (pathname.startsWith('/warning')) return 'Warning';
  if (pathname.startsWith('/teams')) return 'Teams';
  if (pathname.startsWith('/account')) return 'Account';
  return 'The All Seeing Eye';
}

export function TopBar({ onOpenNavigation }: { onOpenNavigation?: (() => void) | undefined }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const mode = useGlobeStore((state) => state.mode);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { run, busy } = useAsyncAction(async () => {
    await logout();
    await navigate('/login', { replace: true });
  });

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line bg-ground px-2 sm:px-4">
      <div className="flex min-w-0 items-center gap-2">
        {onOpenNavigation !== undefined && (
          <Button
            variant="ghost"
            className="min-h-11 shrink-0 px-2"
            onClick={onOpenNavigation}
            aria-label="Open navigation"
            aria-haspopup="dialog"
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
        <p className="truncate font-mono text-xs uppercase tracking-[0.1em] text-muted sm:tracking-[0.2em]">
          {viewTitle(pathname, mode)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1 text-sm sm:gap-3">
        <AlertBell />
        <Link
          to="/account"
          aria-label="Account settings"
          title="Account settings"
          className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md px-2 text-text hover:bg-surface-2"
        >
          <svg
            className="md:hidden"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <circle cx="12" cy="8" r="3.5" />
            <path d="M5 21v-2a7 7 0 0 1 14 0v2" />
          </svg>
          <span className="hidden max-w-40 truncate md:inline">{user?.display_name}</span>
        </Link>
        <Button variant="ghost" className="min-h-11" busy={busy} onClick={() => void run()}>
          Logout
        </Button>
      </div>
    </header>
  );
}
