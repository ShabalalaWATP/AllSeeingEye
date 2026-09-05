import { screen, within } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { sources } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { summarise } from './AdminSourcesPage';

async function findRow(name: string): Promise<HTMLElement> {
  const table = await screen.findByRole('table', { name: 'Sources' });
  const cell = await within(table).findByText(name);
  const row = cell.closest('tr');
  if (row === null) throw new Error(`No row for ${name}`);
  return row;
}

describe('AdminSourcesPage', () => {
  it('lists every source with its grade, status, last poll and error', async () => {
    renderApp('/admin/sources', 'admin');
    const usgs = await findRow('USGS earthquakes');
    expect(within(usgs).getByText('healthy')).toBeInTheDocument();
    expect(within(usgs).getByText('A')).toBeInTheDocument();
    expect(within(usgs).getByText('5 min')).toBeInTheDocument();
    expect(within(usgs).getByText(/12 items/)).toBeInTheDocument();
    expect(within(usgs).getByText('210 ms')).toBeInTheDocument();
    const gdacs = await findRow('GDACS disaster alerts');
    expect(within(gdacs).getByText('degraded')).toBeInTheDocument();
    expect(
      within(gdacs).getByTitle('HTTP 503 from https://www.gdacs.org/xml/rss.xml'),
    ).toBeInTheDocument();
    const tass = await findRow('TASS English');
    expect(within(tass).getByText('idle')).toBeInTheDocument();
    expect(within(tass).getByText('never')).toBeInTheDocument();
    expect(within(tass).getByText('state controlled')).toBeInTheDocument();
    expect(screen.getByText('3 sources: 1 healthy, 1 degraded, 1 idle')).toBeInTheDocument();
    expect(summarise([])).toBe('0 sources');
  });

  it('resets a degraded source and shows the new health', async () => {
    const { user } = renderApp('/admin/sources', 'admin');
    const gdacs = await findRow('GDACS disaster alerts');
    await user.click(within(gdacs).getByRole('button', { name: 'Reset GDACS disaster alerts' }));
    expect(await within(gdacs).findByText('idle')).toBeInTheDocument();
    expect(within(gdacs).queryByTitle(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.getByText('3 sources: 1 healthy, 2 idle')).toBeInTheDocument();
  });

  it('shows reset failures beside the button', async () => {
    server.use(
      http.post('/api/admin/sources/:id/reset', () =>
        apiError(404, 'not_found', 'Unknown source.'),
      ),
    );
    const { user } = renderApp('/admin/sources', 'admin');
    const row = await findRow(sources[0]!.name);
    await user.click(within(row).getByRole('button', { name: `Reset ${sources[0]!.name}` }));
    expect(await within(row).findByRole('alert')).toHaveTextContent('Unknown source.');
  });

  it('shows load failures at the top', async () => {
    server.use(
      http.get('/api/admin/sources', () => apiError(500, 'boom', 'Registry unavailable.')),
    );
    renderApp('/admin/sources', 'admin');
    expect(await screen.findByText('Registry unavailable.')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
