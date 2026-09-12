import { Suspense, useRef } from 'react';
import { Outlet } from 'react-router';

import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { EyeAssistant } from '@/components/assistant/EyeAssistant';
import { PersonalAppearance } from '@/components/account/PersonalAppearance';

import { AdminHeader } from './AdminHeader';
import { AdminNavigation } from './AdminNavigation';
import { useNarrowShell } from './useNarrowShell';

/** Mounted only inside both authentication and active-administrator guards. */
export function AdminShell() {
  const narrow = useNarrowShell();
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
      {!narrow && <AdminNavigation />}
      <div className="flex min-w-0 flex-1 flex-col">
        <AdminHeader key={narrow ? 'mobile' : 'desktop'} narrow={narrow} />
        <main id="main-content" ref={mainRef} tabIndex={-1} className="relative min-h-0 flex-1">
          <Suspense fallback={<LoadingScreen />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
      <EyeAssistant />
    </div>
  );
}
