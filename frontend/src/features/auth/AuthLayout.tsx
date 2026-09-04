/**
 * Layout for the public auth pages: the full-bleed Evil Eye at its defaults
 * (mouse-following pupil on) behind a centred translucent card. The card wrapper
 * ignores pointer events so mouse movement outside the card still reaches the eye.
 */
import { Outlet } from 'react-router';

import EvilEye from '@/components/brand/EvilEye';
import { Wordmark } from '@/components/brand/Wordmark';

export function AuthLayout() {
  return (
    <div className="relative min-h-dvh w-full overflow-hidden bg-ground">
      <div className="absolute inset-0" aria-hidden="true" data-testid="auth-backdrop">
        <EvilEye />
      </div>
      <div className="pointer-events-none relative z-10 flex min-h-dvh items-center justify-center p-4">
        <div className="card-surface pointer-events-auto w-full max-w-md p-6 sm:p-8">
          <div className="mb-6 flex justify-center">
            <Wordmark />
          </div>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
