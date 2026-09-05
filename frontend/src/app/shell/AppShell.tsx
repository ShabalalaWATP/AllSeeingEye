import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router';

import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { useGlobeStore } from '@/stores/globe';

import { LeftRail } from './LeftRail';
import { OpsRoomOverlay } from './OpsRoomOverlay';
import { TopBar } from './TopBar';
import { useViewShortcuts } from './useViewShortcuts';

/** Authenticated frame: left rail, top bar and the routed main area. */
export function AppShell() {
  useViewShortcuts();
  const { pathname } = useLocation();
  const opsRoom = useGlobeStore((state) => state.opsRoom) && pathname === '/';

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      {!opsRoom && <LeftRail />}
      <div className="flex min-w-0 flex-1 flex-col">
        {!opsRoom && <TopBar />}
        <main className="relative min-h-0 flex-1">
          <Suspense fallback={<LoadingScreen />}>
            <Outlet />
          </Suspense>
          {opsRoom && <OpsRoomOverlay />}
        </main>
      </div>
    </div>
  );
}
