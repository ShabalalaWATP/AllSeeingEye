import { render } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { routes } from '@/app/router/routes';

import { applySession, type Session } from './session';

export { applySession, type Session } from './session';

/** Renders the real route table in a memory router at `path` with the given session. */
export function renderApp(path: string, session: Session = 'unknown') {
  applySession(session);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const user = userEvent.setup();
  const view = render(<RouterProvider router={router} />);
  return { ...view, router, user };
}
