import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { PAGE_DESCRIPTION, PAGE_TITLE } from './content/chapters';

const meta = (key: string, attribute = 'name') =>
  document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`)?.content;

function enable(enabled = true) {
  server.use(http.get('/api/site', () => HttpResponse.json({ product_page_enabled: enabled })));
}

describe('public product metadata', () => {
  it.each(['anonymous', 'user'] as const)(
    'uses same-origin canonical and social metadata for %s visitors',
    async (session) => {
      enable();
      renderApp('/enterprise?tracking=discard#contact', session);
      await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
      await waitFor(() => expect(document.title).toBe(PAGE_TITLE));
      const canonical = `${window.location.origin}/enterprise`;
      expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute('href', canonical);
      expect(meta('description')).toBe(PAGE_DESCRIPTION);
      expect(meta('robots')).toBe('index, follow');
      expect(meta('og:url', 'property')).toBe(canonical);
      expect(meta('og:title', 'property')).toBe(PAGE_TITLE);
      expect(meta('og:image', 'property')).toBe(`${window.location.origin}/brand/eye-512.png`);
      expect(meta('og:image:type', 'property')).toBe('image/png');
      expect(meta('og:image:width', 'property')).toBe('512');
      expect(meta('og:image:height', 'property')).toBe('512');
      expect(meta('og:image:alt', 'property')).toMatch(/brand mark/);
      expect(document.querySelectorAll('link[rel="canonical"]')).toHaveLength(1);
    },
  );

  it('removes product metadata and restores app noindex when navigating away and back', async () => {
    enable();
    const { router } = renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    await act(() => router.navigate('/login'));
    await screen.findByRole('heading', { level: 1, name: 'Sign in' });
    expect(meta('robots')).toBe('noindex, follow');
    expect(meta('og:image', 'property')).toBeUndefined();
    expect(document.querySelector('link[rel="canonical"]')).toBeNull();
    await act(() => router.navigate('/enterprise'));
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    expect(meta('robots')).toBe('index, follow');
  });

  it('keeps a disabled product page noindex without canonical or social advertising', async () => {
    enable(false);
    renderApp('/enterprise', 'anonymous');
    await screen.findByRole('heading', { name: /not found/i });
    expect(meta('robots')).toBe('noindex, follow');
    expect(meta('og:title', 'property')).toBeUndefined();
    expect(document.querySelector('link[rel="canonical"]')).toBeNull();
  });

  it('lets signed-in visitors pause the public story without private API calls', async () => {
    const calls: string[] = [];
    server.use(
      http.all('/api/*', ({ request }) => {
        calls.push(new URL(request.url).pathname);
        return HttpResponse.json({ product_page_enabled: true });
      }),
    );
    const { user } = renderApp('/enterprise', 'user');
    await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
    await user.click(screen.getByRole('button', { name: 'Pause animation' }));
    expect(document.querySelector('.product-story')).toHaveAttribute('data-motion', 'still');
    expect(calls).toEqual(['/api/site']);
  });
});
