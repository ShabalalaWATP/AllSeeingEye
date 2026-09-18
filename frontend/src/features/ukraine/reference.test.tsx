import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

beforeAll(async () => {
  await import('./UkrainePage');
  // jsdom has no object URLs; the component only needs a string it can put in src.
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:preview', revokeObjectURL: () => undefined });
  }
});

describe('Ukraine reference sections', () => {
  it('renders the timeline journey with its phases, stage and reading list', async () => {
    const { user } = renderApp('/conflicts/ukraine', 'user');
    const phases = await screen.findByRole('list', { name: 'Phases' }, { timeout: 5000 });
    expect(within(phases).getAllByRole('button')).toHaveLength(2);
    const list = screen.getByRole('list', { name: 'Phases of the war' });
    expect(within(list).getByText('The full-scale invasion begins')).toBeInTheDocument();
    expect(within(list).getByText(/the drive on Kyiv failed/)).toBeInTheDocument();
    const stage = screen.getByTestId('journey-stage');
    expect(within(stage).getByText(/^Event 1 of 2\. 24 February 2022/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next event' }));
    expect(within(stage).getByText(/^Event 2 of 2\. 15 January 2026/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Diplomacy and aid' }));
    expect(within(list).queryByText('The full-scale invasion begins')).toBeNull();
    expect(within(list).getByText('Talks without a ceasefire')).toBeInTheDocument();
  });

  it('reads a force chart node, its chain of command and its subordinates', async () => {
    const { user } = renderApp('/conflicts/ukraine', 'user');
    const russia = await screen.findByRole(
      'region',
      { name: 'Russia force structure' },
      { timeout: 5000 },
    );
    // Re-query after each toggle: expanding rebuilds the list under the chart.
    const chart = () => within(russia).getByRole('list', { name: 'Russia chain of command' });
    const detail = within(russia).getByRole('complementary', { name: 'Russia formation detail' });
    expect(detail).toHaveTextContent('Choose a box in the chart');

    await user.click(within(chart()).getByRole('button', { name: /^Supreme Commander-in-Chief/ }));
    expect(detail).toHaveTextContent('Commander (reported): Vladimir Putin');
    expect(within(detail).getByRole('link', { name: 'figure record' })).toHaveAttribute(
      'href',
      '/trackers/figures',
    );

    const subordinate = 'General Staff and Joint Grouping of Forces';
    expect(within(chart()).queryByText(subordinate)).not.toBeNull();

    const ukraine = screen.getByRole('region', { name: 'Ukraine force structure' });
    await user.click(within(ukraine).getByRole('button', { name: /^Supreme Commander-in-Chief/ }));
    expect(
      within(ukraine).getByRole('complementary', { name: 'Ukraine formation detail' }),
    ).toHaveTextContent('Strength: Around one million personnel by official statements.');
  });

  it('groups equipment by speciality and sub-heading, with a compare table and licensed images', async () => {
    server.use(
      http.get('/api/conflicts/ukraine/images/:id.jpg', () =>
        HttpResponse.arrayBuffer(new Uint8Array([0xff, 0xd8, 0xff, 0xd9]).buffer, {
          headers: { 'Content-Type': 'image/jpeg' },
        }),
      ),
    );
    const { user } = renderApp('/conflicts/ukraine', 'user');
    const specialities = await screen.findByRole(
      'group',
      { name: 'Speciality' },
      { timeout: 5000 },
    );
    expect(within(specialities).getByRole('button', { name: 'Drones (2)' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    const recon = screen.getByRole('region', { name: 'Drones: Reconnaissance' });
    expect(within(recon).getByText('Orlan-10')).toBeInTheDocument();
    expect(within(recon).getByText('No entry written yet.')).toBeInTheDocument();
    await waitFor(() => {
      expect(within(recon).getByRole('img', { name: 'Orlan-10' })).toBeInTheDocument();
    });
    expect(within(recon).getByText(/CC BY-SA 4.0, via Wikimedia Commons/)).toBeInTheDocument();
    // Each sub-heading folds away so a long speciality does not run down the page.
    await user.click(screen.getByRole('button', { name: 'Collapse all' }));
    expect(within(recon).getByText('Orlan-10')).not.toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Expand all' }));
    expect(within(recon).getByText('Orlan-10')).toBeVisible();
    await user.click(within(specialities).getByRole('button', { name: 'Tanks (1)' }));
    expect(screen.getByText('T-90M Proryv')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Compare as a table' }));
    const table = screen.getByRole('table', { name: 'Tanks: systems side by side' });
    expect(
      within(table).getByText('Oryx documents over a hundred T-90M losses.'),
    ).toBeInTheDocument();
  });

  it('keeps the rest of the page when the reference notes are missing', async () => {
    server.use(
      http.get('/api/conflicts/ukraine/reference', () =>
        HttpResponse.json({ error: 'not_found', message: 'Not imported' }, { status: 404 }),
      ),
    );
    renderApp('/conflicts/ukraine', 'user');
    expect(
      await screen.findByText(/Reference notes are unavailable/, undefined, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Headline figures' })).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Phases' })).toBeNull();
  });
});
