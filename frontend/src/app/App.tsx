import { useEffect, useMemo } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';

import { useAuthStore } from '@/stores/auth';
import { preloadSiteFacts } from '@/lib/useSiteFacts';

import { routes } from './router/routes';

// Public documents need neither a refresh nor any account data, even with a saved
// session cookie. Account bootstrap begins once the visitor enters an app/auth route.
const PUBLIC_DOCUMENT_PATHS = new Set([
  '/enterprise',
  '/privacy',
  '/privacy/requests',
  '/attributions',
]);

/** Root component: mounts the router and starts auth only when a route needs it. */
export function App() {
  const router = useMemo(() => createBrowserRouter(routes), []);

  useEffect(() => {
    let started = false;
    const bootstrap = () => {
      // Use the matched definition, so decoded, mixed-case and trailing-slash
      // URLs have the same bootstrap policy as the document they render.
      const publicDocument = router.state.matches.some(({ route }) =>
        PUBLIC_DOCUMENT_PATHS.has(route.path ?? ''),
      );
      if (router.state.matches.some(({ route }) => route.path === '/enterprise'))
        preloadSiteFacts();
      if (started || publicDocument) return;
      started = true;
      void useAuthStore.getState().bootstrap();
    };
    bootstrap();
    return router.subscribe(bootstrap);
  }, [router]);

  return <RouterProvider router={router} />;
}
