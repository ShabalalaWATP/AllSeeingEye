import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('sign-in product link', () => {
  it('links to the product page beside the policy links in both layouts', async () => {
    server.use(http.get('/api/site', () => HttpResponse.json({ product_page_enabled: true })));
    renderApp('/login', 'anonymous');
    const links = await screen.findAllByRole('link', { name: 'Discover The All Seeing Eye' });
    // One in the desktop brand panel and one in the narrow-screen footer slot.
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/enterprise');
      const slot = link.parentElement?.parentElement;
      expect(slot).not.toBeNull();
      expect(within(slot!).getByRole('link', { name: 'Privacy and storage' })).toBeInTheDocument();
    }
    expect(screen.queryByRole('link', { name: 'Self-hosting for organisations' })).toBeNull();
  });

  it('shows no product link by default and leaves the sign-in form unchanged', async () => {
    renderApp('/login', 'anonymous');
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Discover The All Seeing Eye' })).toBeNull();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });
});
