import { Suspense, lazy, useRef } from 'react';
import { Outlet, useLocation } from 'react-router';

import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { useGlobeStore } from '@/stores/globe';
import { EyeAssistant } from '@/components/assistant/EyeAssistant';
import { PersonalAppearance } from '@/components/account/PersonalAppearance';

import { useShellStore } from '@/stores/shell';

import { LeftRail } from './LeftRail';
import { OpsRoomOverlay } from './OpsRoomOverlay';
import { TopBar } from './TopBar';
import { useViewShortcuts } from './useViewShortcuts';
import { MobileHeader } from './MobileNavigation';
import { useNarrowShell } from './useNarrowShell';

// Rarely opened and it pulls in the whole destination catalogue, so keep it out of the shell chunk.
const CommandPalette = lazy(() =>
  import('./CommandPalette').then((module) => ({ default: module.CommandPalette })),
);

/** Authenticated frame: left rail, top bar and the routed main area. */
export function AppShell() {
  useViewShortcuts();
  const { pathname } = useLocation();
  const narrow = useNarrowShell();
  const opsRoom = useGlobeStore((state) => state.opsRoom) && pathname === '/';
  const paletteOpen = useShellStore((state) => state.paletteOpen);
  const mainRef = useRef<HTMLElement>(null);

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      <PersonalAppearance />
      <a
        href="#main-content"
        onClick={() => mainRef.current?.focus()}
        className="sr-only rounded bg-surface px-3 py-2 text-text focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
      >
        Skip to main content
      </a>
      {!opsRoom && !narrow && <LeftRail />}
      <div className="flex min-w-0 flex-1 flex-col">
        {!opsRoom && (narrow ? <MobileHeader /> : <TopBar />)}
        <main id="main-content" ref={mainRef} tabIndex={-1} className="relative min-h-0 flex-1">
          <Suspense fallback={<LoadingScreen />}>
            <Outlet />
          </Suspense>
          {opsRoom && <OpsRoomOverlay />}
        </main>
      </div>
      {paletteOpen && (
        <Suspense fallback={null}>
          <CommandPalette />
        </Suspense>
      )}
      <EyeAssistant />
    </div>
  );
}
