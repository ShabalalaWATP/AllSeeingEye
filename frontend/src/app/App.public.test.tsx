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
