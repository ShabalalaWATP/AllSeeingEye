import { useLocation, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import type { ViewMode } from '@/stores/globe';

export function viewTitle(pathname: string, mode: ViewMode): string {
  if (pathname === '/') return mode === 'globe' ? 'Globe' : 'Map';
  if (pathname.startsWith('/admin')) return 'Admin';
  if (pathname.startsWith('/reports')) return 'Reports';
  return 'The All Seeing Eye';
}

export function TopBar() {
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
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-line bg-ground px-4">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
        {viewTitle(pathname, mode)}
      </p>
      <div className="flex items-center gap-3 text-sm">
        <span className="text-text">{user?.display_name}</span>
        <Button variant="ghost" busy={busy} onClick={() => void run()}>
          Logout
        </Button>
      </div>
    </header>
  );
}
