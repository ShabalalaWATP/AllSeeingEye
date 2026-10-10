import { useEffect, useMemo, useState } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';

import { preloadSiteFacts } from '@/lib/useSiteFacts';
import { reloadPage } from '@/lib/pageRecovery';

import { routes } from './router/routes';
import { watchSessionRoute } from './sessionBootstrap';

/** Root component: mounts the router and starts auth only when a route needs it. */
export function App() {
  const router = useMemo(() => createBrowserRouter(routes), []);
  const [bootstrapFailed, setBootstrapFailed] = useState(false);

  useEffect(() => watchSessionRoute(router, setBootstrapFailed), [router]);

  useEffect(() => {
    const preload = () => {
      if (router.state.matches.some(({ route }) => route.path === '/enterprise'))
        preloadSiteFacts();
    };
    preload();
    return router.subscribe(preload);
  }, [router]);

  return (
    <>
      {bootstrapFailed && (
        <div
          role="alert"
          className="fixed inset-x-0 top-0 z-50 bg-surface p-4 text-center text-text"
        >
          Session checks could not load.{' '}
          <button className="text-ember underline" onClick={() => reloadPage()}>
            Reload to try again
          </button>
        </div>
      )}
      <RouterProvider router={router} />
    </>
  );
}
