import { render } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { routes } from '@/app/router/routes';
import { useAuthStore } from '@/stores/auth';

import { adminUser, plainUser, tokenFor } from './fixtures';

export type Session = 'unknown' | 'anonymous' | 'user' | 'admin';

export function applySession(session: Session): void {
  const store = useAuthStore.getState();
  if (session === 'admin') store.setSession(tokenFor(adminUser));
  else if (session === 'user') store.setSession(tokenFor(plainUser));
  else if (session === 'anonymous') store.clearSession();
}

/** Renders the real route table in a memory router at `path` with the given session. */
export function renderApp(path: string, session: Session = 'unknown') {
  applySession(session);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const user = userEvent.setup();
  const view = render(<RouterProvider router={router} />);
  return { ...view, router, user };
}
