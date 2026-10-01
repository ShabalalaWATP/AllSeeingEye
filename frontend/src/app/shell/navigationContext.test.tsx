/**
 * The current page is named the same way in the rail, the top bar and the page heading,
 * detail pages keep their parent's place, and old addresses keep working.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { lazy } from 'react';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router';
import { describe, expect, it } from 'vitest';

import { routes } from '@/app/router/routes';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';

const PLAN_ID = 'b2b2b2b2-b2b2-4b2b-8b2b-b2b2b2b2b2b2';

function primary() {
  return screen.getByRole('navigation', { name: 'Primary' });
}

function topBarTitle() {
  // The shell's top bar is the first banner; some pages have their own header too.
  const [shellHeader] = screen.getAllByRole('banner');
  return within(shellHeader!).getByText(/./, { selector: 'p' });
}

describe('current page and headings agree', () => {
  it.each([
    ['/research', 'Research'],
    ['/research/jobs', 'Research progress'],
    ['/geolocation', 'Geolocation'],
    ['/watches', 'Watches'],
    ['/subscriptions', 'Subscriptions'],
    ['/direction', 'Plans and areas'],
    ['/annotation-monitors', 'Annotation monitors'],
    ['/trackers', 'Live monitor'],
    ['/economy', 'Economy'],
  ])('names %s as %s in the rail, the top bar and the heading', async (path, name) => {
    renderApp(path, 'user');
    await screen.findByRole('heading', { name, level: 1 });
    expect(within(primary()).getByRole('link', { name })).toHaveAttribute('aria-current', 'page');
    expect(within(primary()).getAllByRole('link', { current: 'page' })).toHaveLength(1);
    expect(topBarTitle()).toHaveTextContent(name);
  });

  it('keeps a watch detail page inside Watches and its own watch type', async () => {
    renderApp(`/direction/plans/${PLAN_ID}`, 'user');
    await screen.findByRole('heading', { level: 1 });
    const plans = within(primary()).getByRole('link', { name: 'Plans and areas' });
    expect(plans).toHaveAttribute('aria-current', 'page');
    const watches = within(primary()).getByRole('link', { name: 'Watches' });
    expect(watches).not.toHaveAttribute('aria-current');
    expect(watches).toHaveAttribute('data-section-current', 'true');
    expect(topBarTitle()).toHaveTextContent('Collection plan');
  });

  it('keeps research tabs consistent, including progress and a job detail page', async () => {
    renderApp('/research/jobs', 'user');
    await screen.findByRole('heading', { name: 'Research progress', level: 1 });
    const tabs = screen.getByRole('navigation', { name: 'Research' });
    expect(
      within(tabs)
        .getAllByRole('link')
        .map((link) => link.textContent),
    ).toEqual(['New research', 'Saved research', 'Research progress']);
    expect(within(tabs).getByRole('link', { name: 'Research progress' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.queryByRole('navigation', { name: 'Research tools' })).not.toBeInTheDocument();
  });
});

describe('old addresses and history', () => {
  it('keeps bookmarked compatibility routes, their query and back and forward', async () => {
    const { user, router } = renderApp('/warning?tab=rules', 'user');
    await screen.findByRole('heading', { name: 'Alerts', level: 1 });
    expect(router.state.location.search).toBe('?tab=rules');
    expect(within(primary()).getByRole('link', { name: 'Alerts' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await user.click(within(primary()).getByRole('link', { name: 'Watches' }));
    await screen.findByRole('heading', { name: 'Watches', level: 1 });
    await router.navigate(-1);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/warning');
    });
    expect(router.state.location.search).toBe('?tab=rules');
    await router.navigate(1);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/watches');
    });
  });
});

describe('navigation survives page trouble', () => {
  it('keeps the rail while a destination is still loading', async () => {
    const Pending = lazy(() => new Promise<never>(() => undefined));
    const withPending = (list: RouteObject[]): RouteObject[] =>
      list.some((route) => route.path === 'watches')
        ? [...list, { path: 'pending', element: <Pending /> }]
        : list.map((route) =>
            route.children ? { ...route, children: withPending(route.children) } : route,
          );
    applySession('user');
    const router = createMemoryRouter(withPending(routes), { initialEntries: ['/pending'] });
    render(<RouterProvider router={router} />);
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    expect(within(primary()).getByRole('link', { name: 'Watches' })).toBeInTheDocument();
  });

  it('keeps the rail when a destination fails to load its data', async () => {
    server.use(
      http.get('/api/direction/plans', () =>
        HttpResponse.json({ detail: 'unavailable' }, { status: 503 }),
      ),
    );
    renderApp('/direction', 'user');
    await screen.findByRole('heading', { name: 'Plans and areas', level: 1 });
    expect(within(primary()).getByRole('link', { name: 'Plans and areas' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });
});
