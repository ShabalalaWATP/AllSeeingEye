import { Suspense } from 'react';
import { Outlet } from 'react-router';

import { LoadingScreen } from '@/components/ui/LoadingScreen';

import { LeftRail } from './LeftRail';
import { TopBar } from './TopBar';
import { useViewShortcuts } from './useViewShortcuts';

/** Authenticated frame: left rail, top bar and the routed main area. */
export function AppShell() {
  useViewShortcuts();

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="relative min-h-0 flex-1">
          <Suspense fallback={<LoadingScreen />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
