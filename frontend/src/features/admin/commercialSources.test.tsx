import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { Source } from '@/lib/api/eventSchemas';
import { sources } from '@/test/fixtures';
import { sourceContext } from '@/test/fixtures.researchMetadata';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { summariseSources } from './overview/overviewSummaries';

const [source] = sources as [Source];

const licence = {
  commercial_use: 'forbidden' as const,
  attribution_required: true,
  licence_ref: 'docs/SOURCE_LICENCES.md#source-test',
  available: false,
  acknowledged: false,
  reason: 'The reviewed source terms prohibit this commercial use.',
};

it('explains the immutable licence refusal and disables enable, test and reset', async () => {
  server.use(
    http.get('/api/admin/sources', () =>
      HttpResponse.json({
        items: [
          {
            ...source,
            enabled: false,
            test_available: false,
            collection_mode: 'scheduled',
            licence,
          },
        ],
      }),
    ),
  );
  renderApp('/admin/sources', 'admin');
  const table = await screen.findByRole('table', { name: 'Sources' });
  const row = within(table);
  expect(await row.findByText(licence.reason)).toBeVisible();
  expect(row.getByText(/Commercial use: forbidden/)).toBeVisible();
  expect(row.getByRole('button', { name: 'Enable USGS earthquakes' })).toBeDisabled();
  expect(row.getByRole('button', { name: 'Test USGS earthquakes' })).toBeDisabled();
  expect(row.getByRole('button', { name: 'Reset USGS earthquakes' })).toBeDisabled();
});

it.each(['scheduled', 'on_demand'] as const)('counts %s licence refusals separately', (mode) => {
  const summary = summariseSources([
    { ...source, enabled: false, test_available: false, collection_mode: mode, licence },
  ]);
  expect(summary).toMatchObject({ healthy: 0, switchedOff: 0, blockedByLicence: 1, onDemand: 0 });
});

it('shows the licence refusal in the overview without reporting failed polls', async () => {
  server.use(
    http.get('/api/admin/sources', () =>
      HttpResponse.json({
        items: [{ ...source, collection_mode: 'on_demand', test_available: false, licence }],
      }),
    ),
  );
  renderApp('/admin', 'admin');
  const card = within(await screen.findByRole('article', { name: 'Sources' }));
  expect(await card.findByText('Licence unavailable: 1')).toBeVisible();
  expect(card.getByText(licence.reason)).toBeVisible();
  expect(card.queryByText(/failed polls/)).not.toBeInTheDocument();
});

it('shows an honest installation reason to ordinary users', async () => {
  server.use(
    http.get('/api/sources', () =>
      HttpResponse.json({
        items: [
          {
            ...sourceContext,
            connection: {
              ...sourceContext.connection,
              state: 'disabled_by_licence',
              enabled: false,
              active: false,
              health: null,
              detail: 'Not available on this installation due to licence terms',
            },
          },
        ],
        assets: [],
      }),
    ),
  );
  renderApp('/sources', 'user');
  const attention = within(await screen.findByRole('region', { name: 'Needs attention' }));
  expect(
    attention.getByText('Not available on this installation due to licence terms'),
  ).toBeVisible();
  expect(screen.getByRole('button', { name: /^Licence unavailable\s*1$/ })).toBeVisible();
  expect(screen.getByRole('button', { name: /^Blocked upstream\s*0$/ })).toBeVisible();
  expect(screen.queryByText(licence.reason)).not.toBeInTheDocument();
});
