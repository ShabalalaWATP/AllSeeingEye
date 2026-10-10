import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { lazy } from 'react';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { isStaleBuildError, reloadPage } from '@/lib/pageRecovery';
import { applySession, type Session } from '@/test/render';

import { routes } from './routes';

vi.mock('@/lib/pageRecovery', async (original) => ({
  ...(await original<typeof import('@/lib/pageRecovery')>()),
  reloadPage: vi.fn(),
}));

const SECRET = 'secret internal detail at build/assets/Page.js:42';

function Broken(): never {
  throw new Error(SECRET);
}

const Removed = lazy(() =>
  Promise.reject(
    new TypeError(
      'Failed to fetch dynamically imported module: https://example.test/assets/Gone-1a2b.js',
    ),
  ),
);

/** The real route table with one extra page beside an existing sibling. */
function withPageBeside(sibling: string, page: RouteObject): RouteObject[] {
  const visit = (list: RouteObject[]): RouteObject[] =>
    list.some((route) => route.path === sibling)
      ? [...list, page]
      : list.map((route) =>
          route.children ? { ...route, children: visit(route.children) } : route,
        );
  return visit(routes);
}

function open(path: string, session: Session, sibling: string, page: RouteObject) {
  applySession(session);
  const router = createMemoryRouter(withPageBeside(sibling, page), { initialEntries: [path] });
  return render(<RouterProvider router={router} />);
}

function expectNoRawError() {
  expect(document.body).not.toHaveTextContent(SECRET);
  expect(document.body).not.toHaveTextContent(/Unexpected Application Error|Gone-1a2b|\.js:\d+/);
}

/** The recovery heading, rendered inside the page's main landmark. */
async function recoveryIn(name: string) {
  const heading = await screen.findByRole('heading', { name, level: 1 });
  const main = screen.getByRole('main');
  expect(main).toContainElement(heading);
  return main;
}

describe('route recovery', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.mocked(reloadPage).mockClear();
  });

  it.each([
    [new Error(SECRET), 'This page could not load'],
    [
      new TypeError('Failed to fetch dynamically imported module: /assets/Gone-1a2b.js'),
      'A newer version is available',
    ],
  ])('contains a public route module rejection: %s', async (error, title) => {
    const replace = (list: RouteObject[]): RouteObject[] =>
      list.map((route) => {
        if (route.path === '/enterprise') return { ...route, lazy: () => Promise.reject(error) };
        return route.children ? { ...route, children: replace(route.children) } : route;
      });
    applySession('anonymous');
    const router = createMemoryRouter(replace(routes), { initialEntries: ['/enterprise'] });
    render(<RouterProvider router={router} />);
    const main = await recoveryIn(title);
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expectNoRawError();
    await userEvent.setup().click(within(main).getByRole('button', { name: 'Reload' }));
    expect(reloadPage).toHaveBeenCalledTimes(1);
  });

  it('keeps the research shell mounted when a page throws while rendering', async () => {
    open('/broken', 'user', 'trackers', { path: 'broken', element: <Broken /> });
    const main = await recoveryIn('This page could not load');
    expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(within(main).getByRole('link', { name: 'Back to map' })).toHaveAttribute('href', '/');
    await userEvent.setup().click(within(main).getByRole('button', { name: 'Reload' }));
    expect(reloadPage).toHaveBeenCalledTimes(1);
    expectNoRawError();
  });

  it('offers a one-click reload when a deploy has removed the page code', async () => {
    open('/removed', 'user', 'trackers', { path: 'removed', element: <Removed /> });
    const main = await recoveryIn('A newer version is available');
    expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    expect(within(main).queryByRole('link', { name: 'Back to map' })).not.toBeInTheDocument();
    await userEvent.setup().click(within(main).getByRole('button', { name: 'Reload' }));
    expect(reloadPage).toHaveBeenCalledTimes(1);
    expectNoRawError();
  });

  it('keeps administration navigation mounted when an admin page throws', async () => {
    open('/admin/broken', 'admin', 'users', { path: 'broken', element: <Broken /> });
    await recoveryIn('This page could not load');
    expect(screen.getByRole('navigation', { name: 'Administration' })).toBeInTheDocument();
    expectNoRawError();
  });

  it('keeps the account access layout when a sign-in page throws', async () => {
    open('/broken-auth', 'anonymous', '/login', { path: '/broken-auth', element: <Broken /> });
    await recoveryIn('This page could not load');
    expect(screen.getByRole('navigation', { name: 'Account access' })).toBeInTheDocument();
    expectNoRawError();
  });

  it('replaces the page with a plain recovery screen when no layout can render', async () => {
    open('/broken-root', 'anonymous', '/activate', { path: '/broken-root', element: <Broken /> });
    const main = await recoveryIn('This page could not load');
    expect(within(main).getByRole('link', { name: 'Back to map' })).toHaveAttribute('href', '/');
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expectNoRawError();
  });
});

describe('stale build detection', () => {
  it.each([
    'Failed to fetch dynamically imported module: https://x.test/assets/A-1.js',
    'error loading dynamically imported module: https://x.test/assets/A-1.js',
    'Importing a module script failed.',
    'Unable to preload CSS for /assets/A-1.css',
  ])('recognises %s', (message) => {
    expect(isStaleBuildError(new TypeError(message))).toBe(true);
  });

  it.each([new Error('Cannot read properties of undefined'), 'Failed to fetch', null, undefined])(
    'does not treat %s as a stale build',
    (value) => {
      expect(isStaleBuildError(value)).toBe(false);
    },
  );
});
