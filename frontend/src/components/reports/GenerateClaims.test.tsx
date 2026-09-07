import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { GenerateClaims } from './GenerateClaims';

it.each(['empty', 'invalid', 'unavailable', 'unsupported'] as const)(
  'explains %s without reporting saved claims',
  async (status) => {
    const saved = vi.fn();
    server.use(
      http.post('/api/claims/generate', async ({ request }) => {
        expect(await request.json()).toEqual({ report_id: 'report-1', version_number: 3 });
        return HttpResponse.json({ status, items: [] });
      }),
    );
    render(<GenerateClaims reportId="report-1" version={3} onSaved={saved} />);
    await userEvent.click(screen.getByRole('button', { name: 'Generate proposed claims' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      status === 'empty'
        ? 'does not confirm'
        : status === 'unsupported'
          ? 'manual claim review'
          : 'No proposals were saved',
    );
    expect(saved).not.toHaveBeenCalled();
  },
);

it('disables duplicate submission and ignores completion after unmount', async () => {
  let finish: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => {
    finish = resolve;
  });
  const saved = vi.fn();
  server.use(
    http.post('/api/claims/generate', async () => {
      await pending;
      return HttpResponse.json({ status: 'completed', items: [] });
    }),
  );
  const view = render(<GenerateClaims reportId="report-1" version={3} onSaved={saved} />);
  await userEvent.click(screen.getByRole('button', { name: 'Generate proposed claims' }));
  expect(screen.getByRole('button', { name: 'Generating proposed claims…' })).toBeDisabled();
  view.unmount();
  await act(async () => {
    finish?.();
    await pending;
  });
  expect(saved).not.toHaveBeenCalled();
});

it('shows request failures without a success notice', async () => {
  server.use(
    http.post('/api/claims/generate', () =>
      HttpResponse.json({ detail: 'Unavailable' }, { status: 503 }),
    ),
  );
  render(<GenerateClaims reportId="report-1" version={3} onSaved={vi.fn()} />);
  await userEvent.click(screen.getByRole('button', { name: 'Generate proposed claims' }));
  await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});
