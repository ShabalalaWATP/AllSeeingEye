import { reportJob } from '@/test/reportJobFixture';
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { applySession } from '@/test/render';
import {
  areaPreview,
  consentLabel,
  mountAreaPanel,
  otherResearchArea,
} from '@/test/areaResearchPanel';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { defaultProfile } from '@/test/handlers.profile';

beforeEach(() => applySession('user'));
function gate() {
  let release: () => void = () => undefined;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { promise, release };
}
async function clickCheck() {
  const button = screen.getByRole('button', { name: 'Check sources' });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
}
function ordinaryPreview() {
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) =>
      HttpResponse.json(areaPreview((await request.json()) as ResearchPlanInput)),
    ),
  );
}

it('aborts obsolete previews, blocks duplicate checks and discards their late results', async () => {
  const pending = gate();
  let signal: AbortSignal | undefined;
  let calls = 0;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      calls += 1;
      signal = request.signal;
      const input = (await request.json()) as ResearchPlanInput;
      await pending.promise;
      return HttpResponse.json(areaPreview(input));
    }),
  );
  const view = mountAreaPanel();
  await clickCheck();
  await waitFor(() => expect(calls).toBe(1));
  fireEvent.click(screen.getByRole('button', { name: 'Checking sources…' }));
  view.update({ area: otherResearchArea });
  await waitFor(() => expect(signal?.aborted).toBe(true));
  await act(async () => {
    pending.release();
    await pending.promise;
  });
  expect(calls).toBe(1);
  expect(screen.queryByLabelText('Area source coverage')).not.toBeInTheDocument();
  ordinaryPreview();
  await clickCheck();
  expect(await screen.findByText('1 source supports this area search')).toBeVisible();
});

it.each(['account', 'workspace', 'logout'] as const)(
  'clears private question and source preview on %s change',
  async (change) => {
    ordinaryPreview();
    mountAreaPanel();
    fireEvent.change(screen.getByLabelText('Question (optional)'), {
      target: { value: 'Private research draft' },
    });
    await clickCheck();
    await screen.findByText('1 source supports this area search');
    fireEvent.click(screen.getByLabelText(consentLabel));
    act(() => {
      if (change === 'workspace') invalidateWorkspaceAccess();
      else applySession(change === 'logout' ? 'anonymous' : 'admin');
    });
    expect(screen.getByLabelText('Question (optional)')).toHaveValue('');
    expect(screen.getByLabelText(consentLabel)).not.toBeChecked();
    expect(screen.queryByLabelText('Area source coverage')).not.toBeInTheDocument();
  },
);

it('cancels a pending source preview when the drawer unmounts', async () => {
  const pending = gate();
  let signal: AbortSignal | undefined;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      signal = request.signal;
      const input = (await request.json()) as ResearchPlanInput;
      await pending.promise;
      return HttpResponse.json(areaPreview(input));
    }),
  );
  const view = mountAreaPanel();
  await clickCheck();
  await waitFor(() => expect(signal).toBeDefined());
  view.unmount();
  await waitFor(() => expect(signal?.aborted).toBe(true));
  await act(async () => {
    pending.release();
    await pending.promise;
  });
});

it.each(['cancel', 'boundary', 'unmount', 'workspace'] as const)(
  'stops waiting for submission on %s and ignores a late research job receipt',
  async (cause) => {
    ordinaryPreview();
    const pending = gate();
    let signal: AbortSignal | undefined;
    let calls = 0;
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        calls += 1;
        signal = request.signal;
        await pending.promise;
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const view = mountAreaPanel();
    await clickCheck();
    await screen.findByText('1 source supports this area search');
    fireEvent.click(screen.getByLabelText(consentLabel));
    fireEvent.click(screen.getByRole('button', { name: 'Generate area report' }));
    await waitFor(() => expect(signal).toBeDefined());
    expect(screen.getByLabelText('Question (optional)')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Draw boundary' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Generating report…' }));
    if (cause === 'cancel') fireEvent.click(screen.getByRole('button', { name: 'Stop waiting' }));
    if (cause === 'boundary') view.update({ area: otherResearchArea });
    if (cause === 'unmount') view.unmount();
    if (cause === 'workspace') act(() => invalidateWorkspaceAccess());
    await waitFor(() => expect(signal?.aborted).toBe(true));
    await act(async () => {
      pending.release();
      await pending.promise;
    });
    expect(calls).toBe(1);
    if (cause !== 'unmount')
      expect(screen.getByLabelText('Current location')).toHaveTextContent('/');
    if (cause === 'cancel')
      expect(
        within(screen.getByRole('region', { name: 'Research progress' })).getByRole('link', {
          name: 'Research jobs',
        }),
      ).toBeVisible();
  },
);

it('requires report preferences and lets the operator retry a failed load', async () => {
  server.use(
    http.get('/api/me/profile', () =>
      HttpResponse.json(
        { error: { code: 'unavailable', message: 'Unavailable', fields: {} } },
        { status: 503 },
      ),
    ),
  );
  mountAreaPanel();
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Report preferences could not be loaded',
  );
  expect(screen.getByRole('button', { name: 'Check sources' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Retry preferences' })).toBeEnabled();
  server.use(http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)));
  fireEvent.click(screen.getByRole('button', { name: 'Retry preferences' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Check sources' })).toBeEnabled());
});
