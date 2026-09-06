/** Public account pages: a live brand plane beside a quiet, opaque form. */
import { Outlet } from 'react-router';

import EvilEye from '@/components/brand/EvilEye';
import { Wordmark } from '@/components/brand/Wordmark';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';

export function AuthLayout() {
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();

  return (
    <div className="grid min-h-dvh w-full bg-ground lg:grid-cols-2">
      <div className="relative h-44 overflow-hidden bg-black sm:h-56 lg:h-auto lg:min-h-dvh">
        <div className="absolute inset-0" aria-hidden="true" data-testid="auth-backdrop">
          <EvilEye
            maxFps={reducedMotion ? 1 : 24}
            flameSpeed={reducedMotion ? 0 : 1}
            pupilFollow={reducedMotion ? 0 : 1}
            paused={!visible}
          />
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-black/80 px-6 py-5 lg:bottom-auto lg:top-0 lg:bg-transparent lg:p-10">
          <Wordmark className="sm:text-sm" />
        </div>
      </div>
      <main className="flex items-center justify-center border-line px-6 py-9 sm:px-10 sm:py-12 lg:border-l">
        <div className="w-full max-w-sm">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
