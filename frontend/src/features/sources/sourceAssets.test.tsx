import { screen, within } from '@testing-library/react';
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { beforeEach, expect, it, vi } from 'vitest';
import { sourceContext } from '@/test/fixtures.researchMetadata';
import {
  blockedSource,
  catalogueAssets,
  dataCentreAsset,
  wsdotAsset,
} from '@/test/fixtures.sourceAssets';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

function serve(body: JsonBodyType) {
  server.use(http.get('/api/sources', () => HttpResponse.json(body)));
}

it('summarises every family and state and lists only actionable items', async () => {
  serve({ items: [sourceContext, blockedSource], assets: catalogueAssets });
  renderApp('/sources', 'user');
  await screen.findByRole('heading', { name: 'BBC World' });
  expect(screen.getByText(/sources, services and\s+datasets on this server/)).toHaveTextContent(
    '8 sources',
  );
  const states = within(screen.getByRole('list', { name: 'Totals by state' }));
  expect(states.getByRole('button', { name: /Live or available\s?3/ })).toBeVisible();
  expect(states.getByRole('button', { name: /On demand\s?1/ })).toBeVisible();
  expect(states.getByRole('button', { name: /Needs key or setup\s?1/ })).toBeVisible();
  expect(states.getByRole('button', { name: /Blocked upstream\s?1/ })).toBeVisible();
  expect(states.getByRole('button', { name: /Retrying or failing\s?1/ })).toBeVisible();
  expect(states.getByRole('button', { name: /Off by operator choice\s?1/ })).toBeVisible();
  const families = within(screen.getByRole('list', { name: 'Totals by family' }));
  expect(families.getByRole('button', { name: /Scheduled feeds\s?2/ })).toBeVisible();
  expect(families.getByRole('button', { name: /On-demand research\s?0/ })).toBeVisible();
  expect(families.getByRole('button', { name: /Camera indexes\s?3/ })).toBeVisible();
  expect(families.getByRole('button', { name: /Map layers and services\s?1/ })).toBeVisible();
  expect(families.getByRole('button', { name: /Ukraine tracker datasets\s?1/ })).toBeVisible();
  expect(families.getByRole('button', { name: /Reference datasets\s?1/ })).toBeVisible();

  const attention = within(screen.getByRole('region', { name: 'Needs attention' }));
  const rows = attention.getAllByRole('listitem');
  expect(rows).toHaveLength(2);
  expect(rows[0]).toHaveTextContent('US CISA cybersecurity and ICS advisories');
  expect(rows[0]).toHaveTextContent("refuses this application's HTTP client");
  expect(rows[0]).toHaveTextContent('Blocked upstream');
  expect(rows[1]).toHaveTextContent('WSDOT');
  expect(rows[1]).toHaveTextContent('ASE_WSDOT_ACCESS_CODE');
  expect(attention.queryByText('DeepStateMap frontline')).not.toBeInTheDocument();
  expect(attention.queryByText('Public figures')).not.toBeInTheDocument();
});

it('filters by family, state and access, and hides data assets for source-only filters', async () => {
  serve({ items: [sourceContext, blockedSource], assets: catalogueAssets });
  const { user } = renderApp('/sources', 'user');
  await screen.findByRole('heading', { name: 'BBC World' });
  const families = within(screen.getByRole('list', { name: 'Totals by family' }));
  await user.click(families.getByRole('button', { name: /Camera indexes/ }));
  expect(screen.getByLabelText('Family')).toHaveValue('camera_index');
  const cameras = within(screen.getByRole('region', { name: 'Camera indexes' }));
  expect(cameras.getAllByRole('heading', { level: 4 })).toHaveLength(3);
  expect(screen.queryByRole('heading', { name: 'BBC World' })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Access'), 'key');
  expect(screen.getByRole('heading', { name: 'WSDOT' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'UK public streams' })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Access'), 'open');
  expect(screen.getByRole('heading', { name: 'UK public streams' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));

  const states = within(screen.getByRole('list', { name: 'Totals by state' }));
  await user.click(states.getByRole('button', { name: /Off by operator choice/ }));
  expect(screen.getByRole('heading', { name: 'DeepStateMap frontline' })).toBeVisible();
  expect(screen.getByText('Optional, not set')).toBeVisible();
  await user.click(states.getByRole('button', { name: /Blocked upstream/ }));
  expect(screen.getByRole('region', { name: 'Cyber sources' })).toBeVisible();
  expect(screen.getByRole('status')).toHaveTextContent('1 of 8 entries');
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));

  await user.selectOptions(screen.getByLabelText('Topic'), 'news');
  expect(screen.getByRole('heading', { name: 'BBC World' })).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Map layers and services' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));
  await user.type(screen.getByRole('searchbox'), 'openstreetmap');
  expect(screen.getByRole('heading', { name: 'Data centres' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'BBC World' })).not.toBeInTheDocument();
});

it('shows licence, provenance and a safe publisher link as text', async () => {
  serve({ items: [], assets: [dataCentreAsset] });
  const { user } = renderApp('/sources', 'user');
  const region = within(await screen.findByRole('region', { name: 'Map layers and services' }));
  expect(region.getByText('Packaged snapshot')).toBeVisible();
  expect(region.getByText('Available')).toBeVisible();
  await user.click(region.getByText('Licence and provenance'));
  expect(region.getByText('© OpenStreetMap contributors (ODbL).')).toBeVisible();
  expect(
    region.getByText('As of 2026-09-13 · 3,622 records · Refresh with ase import-data-centres.'),
  ).toBeVisible();
  const link = region.getByRole('link', { name: 'Publisher website' });
  expect(link).toHaveAttribute('href', 'https://www.openstreetmap.org/');
  expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  expect(screen.queryByRole('region', { name: 'Needs attention' })).not.toBeInTheDocument();
});

it('rejects an asset whose homepage is not https', async () => {
  serve({ items: [], assets: [{ ...dataCentreAsset, homepage: 'javascript:alert(1)' }] });
  renderApp('/sources', 'user');
  expect(await screen.findByRole('button', { name: 'Retry sources' })).toBeVisible();
  expect(screen.queryByRole('link', { name: 'Publisher website' })).not.toBeInTheDocument();
});

it('keeps a long attention list short and points to the catalogue', async () => {
  const assets = Array.from({ length: 17 }, (_, index) => ({
    ...wsdotAsset,
    id: `camera:keyed-${index}`,
    name: `Keyed camera ${String(index).padStart(2, '0')}`,
  }));
  serve({ items: [], assets });
  renderApp('/sources', 'user');
  const attention = within(await screen.findByRole('region', { name: 'Needs attention' }));
  expect(attention.getAllByRole('listitem')).toHaveLength(15);
  expect(attention.getByText('2 more in the catalogue below.')).toBeVisible();
});
