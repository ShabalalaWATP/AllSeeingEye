import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { platformConnections, sourceContext } from '@/test/fixtures.researchMetadata';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import type { CatalogueSource } from '@/lib/api/sourceContext';

const keyed: CatalogueSource = {
  ...sourceContext,
  id: 'aisstream',
  name: 'AISStream ship positions',
  category: 'maritime',
  kind: 'websocket',
  requires_key: true,
  connection: {
    state: 'key_missing',
    enabled: true,
    environment_disabled: false,
    active: false,
    requirement: {
      kind: 'api_key',
      satisfied: false,
      origin: 'none',
      setting: 'ASE_AISSTREAM_API_KEY',
      note: 'Set ASE_AISSTREAM_API_KEY on the server to enable global ship positions.',
      optional: false,
    },
    health: null,
    detail: 'Set ASE_AISSTREAM_API_KEY on the server to enable global ship positions.',
  },
};
const optionalKey: CatalogueSource = {
  ...sourceContext,
  id: 'research-openalex',
  name: 'OpenAlex research',
  collection_mode: 'on_demand',
  connection: {
    state: 'on_demand',
    enabled: true,
    environment_disabled: false,
    active: false,
    requirement: {
      kind: 'api_key',
      satisfied: false,
      origin: 'none',
      setting: 'ASE_OPENALEX_API_KEY',
      note: 'Optional. Set ASE_OPENALEX_API_KEY to unlock higher limits.',
      optional: true,
    },
    health: null,
    detail: 'Queried only when a research run selects it.',
  },
};
const failing: CatalogueSource = {
  ...sourceContext,
  id: 'broken_feed',
  name: 'Broken feed',
  connection: {
    ...sourceContext.connection,
    state: 'failing',
    health: {
      status: 'disabled',
      last_success: null,
      last_error_at: '2026-09-12T11:00:00Z',
      consecutive_failures: 6,
      items_last_poll: 0,
      next_poll_at: null,
      polls: 6,
      blocked_reason: null,
    },
    detail: 'Paused after repeated failures until an administrator resets it.',
  },
};

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

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

it('shows connection state, missing keys and platform services without any values', async () => {
  server.use(
    http.get('/api/sources', () =>
      HttpResponse.json({ items: [sourceContext, keyed, optionalKey, failing] }),
    ),
  );
  const { user } = renderApp('/sources', 'user');
  await screen.findByRole('heading', { name: 'BBC World' });
  const totals = within(screen.getByRole('list', { name: 'Totals by state' }));
  expect(totals.getByRole('button', { name: /Live or available\s?1/ })).toBeVisible();
  expect(totals.getByRole('button', { name: /Retrying or failing\s?1/ })).toBeVisible();
  expect(totals.getByRole('button', { name: /Needs key or setup\s?1/ })).toBeVisible();
  expect(totals.getByRole('button', { name: /On demand\s?1/ })).toBeVisible();
  expect(totals.getByRole('button', { name: /Blocked upstream\s?0/ })).toBeVisible();
  expect(totals.getByRole('button', { name: /Off by operator choice\s?0/ })).toBeVisible();
  const attention = within(screen.getByRole('region', { name: 'Needs attention' }));
  expect(attention.getByText('Broken feed')).toBeVisible();
  expect(attention.getByText('AISStream ship positions')).toBeVisible();
  expect(attention.getAllByText('ASE_AISSTREAM_API_KEY')).not.toHaveLength(0);
  expect(attention.queryByText('OpenAlex research')).not.toBeInTheDocument();
  const platform = within(screen.getByRole('region', { name: 'Platform connections' }));
  expect(platform.getByRole('heading', { name: 'AI assessment model' })).toBeVisible();
  expect(platform.getByText(/Add one under Admin, Models/)).toBeVisible();
  expect(platform.getByText('Optional, not set')).toBeVisible();
  expect(platform.getAllByText('Connected')).not.toHaveLength(0);
  await user.click(totals.getByRole('button', { name: /Needs key or setup\s?1/ }));
  expect(screen.getByLabelText('Connection')).toHaveValue('setup');
  expect(screen.getByRole('heading', { name: 'AISStream ship positions' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'BBC World' })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Connection'), 'retrying');
  expect(screen.getByRole('heading', { name: 'Broken feed' })).toBeVisible();
  expect(screen.getByText(/6 consecutive failures/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));
  await user.type(screen.getByRole('searchbox'), 'ASE_OPENALEX');
  expect(screen.getByRole('heading', { name: 'OpenAlex research' })).toBeVisible();
  await user.clear(screen.getByRole('searchbox'));
  expect(screen.getAllByText(/Last successful collection/)[0]).toBeVisible();
});

it('explains when platform connections cannot be checked and offers a retry', async () => {
  let attempts = 0;
  server.use(
    http.get('/api/sources', () => HttpResponse.json({ items: [sourceContext] })),
    http.get('/api/sources/connections', () =>
      ++attempts === 1
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'Connection check unavailable.' } },
            { status: 503 },
          )
        : HttpResponse.json({ items: platformConnections }),
    ),
  );
  const { user } = renderApp('/sources', 'user');
  expect(await screen.findByText('Connection check unavailable.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Retry connections' }));
  expect(await screen.findByRole('heading', { name: 'Ordnance Survey maps' })).toBeVisible();
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
  await user.selectOptions(screen.getByLabelText('Family'), 'research');
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
