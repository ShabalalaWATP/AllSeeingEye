import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, expect, it, vi } from 'vitest';

import * as authApi from '@/lib/api/auth';
import { server } from '@/test/server';

import { App } from './App';

afterEach(() => window.history.replaceState(null, '', '/'));

it.each(['/enterprise?campaign=example', '/enterprise/', '/Enterprise', '/%65nterprise'])(
  'defers session bootstrap on %s until the visitor chooses sign-in',
  async (path) => {
    window.history.replaceState(null, '', path);
    document.cookie = 'ase_csrf=synthetic-public-visit; path=/';
    server.use(http.get('/api/site', () => HttpResponse.json({ product_page_enabled: true })));
    const refresh = vi.spyOn(authApi, 'refreshSession');
    render(<App />);
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    expect(refresh).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getAllByRole('link', { name: 'Sign in' })[0]!);
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    await screen.findByRole('heading', { level: 1, name: 'Sign in' });
  },
);

it.each([
  ['/Privacy/', 'Privacy and storage'],
  ['/privacy/%72equests', 'Personal-data requests'],
  ['/Attributions', 'Source attributions'],
])('keeps the public policy route %s outside session bootstrap', async (path, title) => {
  window.history.replaceState(null, '', path);
  document.cookie = 'ase_csrf=synthetic-public-visit; path=/';
  server.use(
    http.get('/api/site', () =>
      HttpResponse.json({
        product_page_enabled: true,
        enterprise_enquiries_enabled: true,
        enterprise_enquiry_retention_days: 90,
      }),
    ),
  );
  const refresh = vi.spyOn(authApi, 'refreshSession');
  render(<App />);
  await screen.findByRole('heading', { level: 1, name: title });
  expect(refresh).not.toHaveBeenCalled();
  expect(document.head.querySelector('meta[name="robots"]')).toHaveAttribute(
    'content',
    'noindex, follow',
  );
  await userEvent.setup().click(screen.getByRole('link', { name: 'The All Seeing Eye' }));
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  await screen.findByRole('heading', { level: 1, name: 'Sign in' });
});
