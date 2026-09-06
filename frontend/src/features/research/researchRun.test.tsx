import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('research request progress integration', () => {
  it('passes a unique run header, cancels while saving and suppresses a late success navigation', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const runIds: (string | null)[] = [];
    server.use(
      http.post('/api/reports', async ({ request }) => {
        runIds.push(request.headers.get('X-Research-Run-ID'));
        await gate;
        return HttpResponse.json(report, { status: 201 });
      }),
      http.get('/api/research/runs/:id', ({ params }) =>
        HttpResponse.json({
          id: params.id,
          stage: 'saving',
          started_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 900_000).toISOString(),
          report_id: null,
        }),
      ),
    );
    const { user, router } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'What changed?');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(await screen.findByText('Starting research')).toBeVisible();
    expect(await screen.findByText('Saving the report')).toBeVisible();
    expect(runIds[0]).toMatch(/^[0-9a-f-]{36}$/);
    await user.click(screen.getByRole('button', { name: 'Cancel research' }));
    expect(await screen.findByText('Cancellation requested')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Check Reports' })).toHaveAttribute('href', '/reports');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await act(async () => {
      release();
      await gate;
    });
    expect(router.state.location.pathname).toBe('/research');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Your question')).toHaveValue('What changed?');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/reports/${report.report.id}`),
    );
    expect(runIds).toHaveLength(2);
    expect(runIds[1]).not.toBe(runIds[0]);
  });
});
