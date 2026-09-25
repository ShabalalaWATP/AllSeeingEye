import { useLocation, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useNow } from '@/lib/hooks/useNow';
import { useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import type { ViewMode } from '@/stores/globe';

import { PersonalLinks } from './PersonalLinks';
import { pageTitle } from './pageTitles';

/** The root route names the current projection; every other route names its page. */
export function viewTitle(pathname: string, mode: ViewMode): string {
  if (pathname === '/') return mode === 'globe' ? 'Globe' : 'Map';
  return pageTitle(pathname);
}

const UTC_CLOCK = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
  hourCycle: 'h23',
});

function UtcClock() {
  const now = useNow();
  return (
    <time
      dateTime={new Date(now).toISOString()}
      aria-label="Current time, UTC"
      className="hidden items-center gap-1.5 rounded-md border border-line/60 bg-surface/60 px-2.5 py-1 font-mono text-[11px] text-muted tabular-nums md:inline-flex"
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-good" />
      {UTC_CLOCK.format(now)} <span className="text-muted/70">UTC</span>
    </time>
  );
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
    <header className="relative flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line/70 bg-ground/85 px-2 backdrop-blur-md after:pointer-events-none after:absolute after:inset-x-0 after:bottom-0 after:h-px after:bg-linear-to-r after:from-ember/50 after:via-cyan/30 after:to-transparent sm:px-4">
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
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
        <span aria-hidden="true" className="hidden size-1.5 rounded-full bg-ember sm:block" />
        <p className="truncate font-mono text-xs tracking-normal text-muted uppercase sm:tracking-[0.2em]">
          {viewTitle(pathname, mode)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1 text-sm sm:gap-2">
        <UtcClock />
        <span aria-hidden="true" className="mx-1 hidden h-5 w-px bg-line/70 md:block" />
        <PersonalLinks />
        <Button variant="ghost" className="min-h-11" busy={busy} onClick={() => void run()}>
          Logout
        </Button>
      </div>
    </header>
  );
}
