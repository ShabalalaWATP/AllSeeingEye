import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('trackers', () => {
  it('lists conflicts and hazards with their activity', async () => {
    renderApp('/trackers', 'user');
    const conflicts = await screen.findByRole('table', { name: 'Conflicts' }, { timeout: 5000 });
    expect(
      within(conflicts).getByRole('link', { name: "Russia's war in Ukraine" }),
    ).toBeInTheDocument();
    expect(within(conflicts).getByText('4 reported deaths / 7 d')).toBeInTheDocument();
    expect(within(conflicts).getByText('falling')).toBeInTheDocument();
    const hazards = screen.getByRole('list', { name: 'Hazards' });
    expect(within(hazards).getByRole('link', { name: 'Earthquakes' })).toBeInTheDocument();
    expect(within(hazards).getByText('1 red')).toBeInTheDocument();
    expect(within(hazards).getByText('rising')).toBeInTheDocument();
  });

  it('opens a conflict with its timeline and events, and scopes the globe to it', async () => {
    const { user } = renderApp('/trackers', 'user');
    await user.click(
      await screen.findByRole('link', { name: "Russia's war in Ukraine" }, { timeout: 5000 }),
    );
    expect(
      await screen.findByRole('heading', { name: "Russia's war in Ukraine" }),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Conflict events by day/ })).toBeInTheDocument();
    const latest = screen.getByRole('region', { name: 'Latest in the area' });
    expect(within(latest).getByRole('link', { name: 'Shelling in Kharkiv' })).toHaveAttribute(
      'href',
      'https://example.com/e1',
    );
    expect(within(latest).getByText('Talks in Kyiv')).toBeInTheDocument();
    expect(within(latest).queryByRole('link', { name: 'Talks in Kyiv' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show on globe' }));
    await waitFor(() => {
      expect(useEventsStore.getState().country).toBe('UA');
    });
  });

  it('opens a hazard and reports unknown ones', async () => {
    renderApp('/trackers/disasters/earthquake', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Earthquakes' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText('1 red alerts / 7 d')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Events by day/ })).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: 'Latest events' })).getAllByRole('listitem'),
    ).toHaveLength(2);
  });

  it('shows the error for an unknown conflict', async () => {
    renderApp('/trackers/conflicts/nope', 'user');
    expect(await screen.findByText('No such conflict', {}, { timeout: 5000 })).toBeInTheDocument();
  });
});

describe('tracker products', () => {
  it('links a conflict to a prefilled assessment form that posts the conflict scope', async () => {
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post('/api/reports', async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(report, { status: 201 });
      }),
    );
    const { user } = renderApp('/trackers/conflicts/ukraine', 'user');
    const generate = await screen.findByRole(
      'link',
      { name: 'Generate assessment' },
      { timeout: 5000 },
    );
    expect(generate).toHaveAttribute(
      'href',
      '/reports?template=conflict_assessment&conflict=ukraine',
    );
    await user.click(generate);
    const form = await screen.findByRole('form', { name: 'Generate a report' }, { timeout: 5000 });
    expect(within(form).getByLabelText('Product')).toHaveValue('conflict_assessment');
    await waitFor(() => {
      expect(within(form).getByLabelText('Conflict')).toHaveValue('ukraine');
    });
    await user.click(within(form).getByRole('button', { name: 'Generate' }));
    await waitFor(() => {
      expect(body).toEqual({ template: 'conflict_assessment', conflict: 'ukraine' });
    });
  });

  it('offers a SITREP for a hazard', async () => {
    renderApp('/trackers/disasters/earthquake', 'user');
    const generate = await screen.findByRole(
      'link',
      { name: 'Generate SITREP' },
      { timeout: 5000 },
    );
    expect(generate).toHaveAttribute('href', '/reports?template=disaster_sitrep&hazard=earthquake');
  });
});
