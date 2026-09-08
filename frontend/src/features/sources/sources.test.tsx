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

it('combines topic, country, language and access filters and resets them', async () => {
  server.use(
    http.get('/api/sources', () =>
      HttpResponse.json({
        items: [
          sourceContext,
          {
            ...sourceContext,
            id: 'ua_news',
            name: 'Ukraine bulletin',
            coverage_scope: 'regional',
            coverage_countries: ['UA'],
            coverage_regions: ['Eastern Europe'],
            language: 'uk',
            requires_key: true,
            collection_mode: 'on_demand',
          },
          {
            ...sourceContext,
            id: 'fi_ships',
            name: 'Finnish ships',
            category: 'maritime',
            coverage_scope: 'regional',
            coverage_countries: ['FI'],
          },
        ],
      }),
    ),
  );
  const { user } = renderApp('/sources', 'user');
  await screen.findByRole('heading', { name: 'BBC World' });
  expect(screen.getByRole('region', { name: 'News sources' })).toBeVisible();
  expect(screen.getByRole('region', { name: 'Maritime sources' })).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Country or region'), 'UA');
  await user.selectOptions(screen.getByLabelText('Topic'), 'news');
  await user.selectOptions(screen.getByLabelText('Language'), 'uk');
  await user.selectOptions(screen.getByLabelText('Access'), 'key');
  await user.selectOptions(screen.getByLabelText('Collection'), 'on_demand');
  expect(screen.getByRole('heading', { name: 'Ukraine bulletin' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'BBC World' })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Country or region'), 'region:Eastern Europe');
  expect(screen.getByRole('heading', { name: 'Ukraine bulletin' })).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Access'), 'open');
  expect(screen.getByText('No sources match your search.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));
  expect(screen.getByRole('heading', { name: 'BBC World' })).toBeVisible();
  await user.type(screen.getByRole('searchbox'), 'shipping Finland');
  expect(screen.getByRole('heading', { name: 'Finnish ships' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Ukraine bulletin' })).not.toBeInTheDocument();
});

it('keeps worldwide and unspecified sources distinct from country coverage', async () => {
  server.use(
    http.get('/api/sources', () =>
      HttpResponse.json({
        items: [
          sourceContext,
          {
            ...sourceContext,
            id: 'unknown',
            name: 'Uncatalogued source',
            coverage_scope: 'unspecified',
          },
        ],
      }),
    ),
  );
  const { user } = renderApp('/sources', 'user');
  await screen.findByRole('heading', { name: 'BBC World' });
  await user.selectOptions(screen.getByLabelText('Country or region'), 'global');
  expect(screen.queryByRole('heading', { name: 'Uncatalogued source' })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Country or region'), 'unspecified');
  expect(screen.getByRole('heading', { name: 'Uncatalogued source' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'BBC World' })).not.toBeInTheDocument();
});
