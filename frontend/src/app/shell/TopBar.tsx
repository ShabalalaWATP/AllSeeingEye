import { useLocation, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

import { PersonalLinks } from './PersonalLinks';
import { useGlobeStore } from '@/stores/globe';
import type { ViewMode } from '@/stores/globe';

export function viewTitle(pathname: string, mode: ViewMode): string {
  if (pathname === '/') return mode === 'globe' ? 'Globe' : 'Map';
  if (pathname.startsWith('/admin')) return 'Admin';
  if (pathname.startsWith('/reports')) return 'Saved reports';
  if (pathname.startsWith('/subscriptions')) return 'Subscriptions';
  if (pathname.startsWith('/economy')) return 'Economy';
  if (pathname.startsWith('/settings')) return 'Your settings';
  if (pathname.startsWith('/research')) return 'Research';
  if (pathname.startsWith('/geolocation')) return 'Geolocation';
  if (pathname.startsWith('/sources')) return 'Sources';
  if (pathname.startsWith('/trackers')) return 'Live monitor';
  if (pathname.startsWith('/direction')) return 'Plans & areas';
  if (pathname.startsWith('/warning')) return 'Alerts';
  if (pathname.startsWith('/teams')) return 'Teams';
  if (pathname.startsWith('/account')) return 'Account';
  return 'The All Seeing Eye';
}

export function TopBar({ onOpenNavigation }: { onOpenNavigation?: (() => void) | undefined }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const mode = useGlobeStore((state) => state.mode);
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
        <p className="truncate font-mono text-xs uppercase tracking-normal text-muted sm:tracking-[0.2em]">
          {viewTitle(pathname, mode)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1 text-sm sm:gap-3">
        <PersonalLinks />
        <Button variant="ghost" className="min-h-11" busy={busy} onClick={() => void run()}>
          Logout
        </Button>
      </div>
    </header>
  );
}
