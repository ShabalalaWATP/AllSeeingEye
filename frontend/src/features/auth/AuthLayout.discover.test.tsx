import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('sign-in product link', () => {
  it('links to the product page only when the installation enables it', async () => {
    server.use(http.get('/api/site', () => HttpResponse.json({ product_page_enabled: true })));
    renderApp('/login', 'anonymous');
    expect(await screen.findByRole('link', { name: 'Discover what it can do' })).toHaveAttribute(
      'href',
      '/enterprise',
    );
  });

  it('shows no product link by default', async () => {
    renderApp('/login', 'anonymous');
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Discover what it can do' })).toBeNull();
  });
});
