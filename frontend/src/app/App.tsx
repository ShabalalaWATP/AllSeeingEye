import { useEffect, useMemo } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';

import { useAuthStore } from '@/stores/auth';

import { routes } from './router/routes';

/** Root component: starts the silent session refresh and mounts the router. */
export function App() {
  const router = useMemo(() => createBrowserRouter(routes), []);

  useEffect(() => {
    void useAuthStore.getState().bootstrap();
  }, []);

  return <RouterProvider router={router} />;
}
