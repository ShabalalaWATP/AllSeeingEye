import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { reportMethodology } from '@/test/fixtures.reportAssessment';
import { server } from '@/test/server';

import { ReportMethodology } from './ReportMethodology';

describe('evidence methodology guide', () => {
  it('fetches only on disclosure, authenticates, and renders the supplied 36 cells and separate axes', async () => {
    let requests = 0;
    let auth: string | null = null;
    server.use(
      http.get('/api/report-methodology', ({ request }) => {
        requests += 1;
        auth = request.headers.get('Authorization');
        return HttpResponse.json(reportMethodology);
      }),
    );
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const user = userEvent.setup();
    render(<ReportMethodology savedMethod="old-method" />);
    expect(requests).toBe(0);
    // Native summary keyboard activation is checked in Chromium; jsdom does not implement it.
    await user.click(screen.getByText('How evidence is weighed'));
    const table = await screen.findByRole('table');
    expect(auth).toMatch(/^Bearer /);
    expect(requests).toBe(1);
    expect(within(table).getAllByRole('cell')).toHaveLength(36);
    expect(within(table).getAllByRole('rowheader')).toHaveLength(6);
    expect(within(table).getAllByRole('cell', { name: 'limited' })).toHaveLength(30);
    expect(screen.getByRole('region', { name: 'Evidence contribution matrix' })).toHaveAttribute(
      'tabindex',
      '0',
    );
    for (const label of [
      'Source reliability',
      'Information credibility',
      'Likelihood',
      'Confidence',
    ])
      expect(screen.getByText(label)).toBeVisible();
    expect(screen.getByText(/This version used old-method/)).toBeVisible();
    expect(screen.getByText(/Analytical rigour · Not assessed/)).toBeVisible();
    const yardstick = screen.getByRole('region', { name: 'Probability yardstick' });
    expect(within(yardstick).getByText('Highly likely')).toBeVisible();
    expect(within(yardstick).getByText('About 80% to about 90%')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Doctrinal reference' })).toHaveAttribute(
      'rel',
      'noopener noreferrer',
    );
    await user.click(screen.getByText('How evidence is weighed'));
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows loading, handles an error and retries without losing the disclosure', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/report-methodology', async () => {
        await gate;
        return HttpResponse.json(
          { error: { code: 'server_error', message: 'Methodology unavailable.' } },
          { status: 500 },
        );
      }),
    );
    const user = userEvent.setup();
    render(<ReportMethodology />);
    await user.click(screen.getByText('How evidence is weighed'));
    expect(await screen.findByText('Loading evidence methodology')).toBeVisible();
    release();
    expect(await screen.findByRole('alert')).toHaveTextContent('Methodology unavailable.');
    server.use(
      http.get('/api/report-methodology', () =>
        HttpResponse.json({ ...reportMethodology, contribution_matrix: [] }),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Retry methodology' }));
    expect(await screen.findByText('No contribution matrix is available.')).toBeVisible();
  });
});
