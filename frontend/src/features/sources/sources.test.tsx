import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { sourceContext } from '@/test/fixtures.researchMetadata';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('source catalogue', () => {
  it('is available to ordinary users, authenticates its request and searches declared context', async () => {
    let auth: string | null = null;
    server.use(
      http.get('/api/sources', ({ request }) => {
        auth = request.headers.get('Authorization');
        return HttpResponse.json({ items: [sourceContext] });
      }),
    );
    const { user } = renderApp('/sources', 'user');
    expect(await screen.findByRole('heading', { name: 'BBC World' })).toBeVisible();
    expect(auth).toMatch(/^Bearer /);
    expect(screen.queryByText('Admin', { exact: true })).not.toBeInTheDocument();
    await user.click(screen.getByText('Source rating basis · Editorial B'));
    expect(screen.getByText(/Current catalogue context/)).toBeVisible();
    const search = screen.getByRole('searchbox');
    await user.type(search, 'missing');
    expect(screen.getByText('No sources match your search.')).toBeVisible();
    await user.clear(search);
    await user.type(search, 'news');
    expect(screen.getByRole('heading', { name: 'BBC World' })).toBeVisible();
  });

  it('shows a request error, retries and handles an empty catalogue', async () => {
    let requests = 0;
    server.use(
      http.get('/api/sources', () =>
        ++requests === 1
          ? HttpResponse.json(
              { error: { code: 'unavailable', message: 'Catalogue unavailable.' } },
              { status: 503 },
            )
          : HttpResponse.json({ items: [] }),
      ),
    );
    const { user } = renderApp('/sources', 'user');
    expect(await screen.findByRole('alert')).toHaveTextContent('Catalogue unavailable.');
    await user.click(screen.getByRole('button', { name: 'Retry sources' }));
    expect(await screen.findByText('No sources are registered.')).toBeVisible();
  });

  it('requires a session before fetching the catalogue', async () => {
    const { router } = renderApp('/sources', 'anonymous');
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/login');
  });
});
