import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { useAuthStore } from '@/stores/auth';
import { useEventsStore } from '@/stores/events';
import { adminUser, sources, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function row() {
  const table = await screen.findByRole('table', { name: 'Sources' });
  const element = await within(table).findByText('USGS earthquakes');
  const parent = element.closest('tr');
  if (!parent) throw new Error('Source row missing');
  return within(parent);
}

describe('administrator source controls', () => {
  it('confirms activation changes and describes retained evidence', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.patch('/api/admin/sources/:id/activation', async ({ request }) => {
        bodies.push(await request.json());
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/admin/sources', 'admin');
    const source = await row();
    await user.click(source.getByRole('button', { name: 'Disable USGS earthquakes' }));
    expect(bodies).toEqual([]);
    expect(source.getByText(/Existing live records and saved reports are retained/)).toBeVisible();
    await user.click(source.getByRole('button', { name: 'Cancel' }));
    expect(bodies).toEqual([]);
    await user.click(source.getByRole('button', { name: 'Disable USGS earthquakes' }));
    await user.click(source.getByRole('button', { name: 'Confirm disable' }));
    expect(await source.findByText('Collection disabled')).toBeVisible();
    expect(bodies).toEqual([{ enabled: false }]);
    await user.click(source.getByRole('button', { name: 'Enable USGS earthquakes' }));
    await user.click(source.getByRole('button', { name: 'Confirm enable' }));
    expect(await source.findByText('Collection enabled')).toBeVisible();
    expect(bodies).toEqual([{ enabled: false }, { enabled: true }]);
  });

  it('displays bounded isolated test outcomes without adding public events', async () => {
    server.use(
      http.post('/api/admin/sources/:id/test', () =>
        HttpResponse.json({
          ok: true,
          fetched: 3,
          capped: false,
          message: 'Test records were not published or saved.',
        }),
      ),
    );
    const { user } = renderApp('/admin/sources', 'admin');
    const source = await row();
    const before = useEventsStore.getState().list;
    await user.click(source.getByRole('button', { name: 'Test USGS earthquakes' }));
    expect(await source.findByText(/Test completed:.*3 records received/)).toBeVisible();
    expect(useEventsStore.getState().list).toBe(before);
    server.use(
      http.post('/api/admin/sources/:id/test', () =>
        HttpResponse.json({
          ok: false,
          fetched: 0,
          capped: false,
          message: 'The source exceeded its deadline.',
        }),
      ),
    );
    await user.click(source.getByRole('button', { name: 'Test USGS earthquakes' }));
    expect(await source.findByText('Test failed: The source exceeded its deadline.')).toBeVisible();
  });

  it('keeps environment restrictions and on-demand test limitations explicit', async () => {
    server.use(
      http.get('/api/admin/sources', () =>
        HttpResponse.json({
          items: [
            { ...sources[0], enabled: false, environment_disabled: true, test_available: false },
          ],
        }),
      ),
    );
    renderApp('/admin/sources', 'admin');
    const source = await row();
    expect(source.getByRole('button', { name: 'Enable USGS earthquakes' })).toBeDisabled();
    expect(source.queryByRole('button', { name: 'Test USGS earthquakes' })).not.toBeInTheDocument();
    expect(source.getByText('Disabled in operator configuration.')).toBeVisible();
    expect(
      source.getByText('On-demand source. Test through a scoped research query.'),
    ).toBeVisible();
  });

  it('retains activation confirmation and session after a rejected change', async () => {
    server.use(
      http.patch('/api/admin/sources/:id/activation', () =>
        apiError(422, 'invalid_request', 'Enable the parent source first.'),
      ),
    );
    const { user } = renderApp('/admin/sources', 'admin');
    const source = await row();
    await user.click(source.getByRole('button', { name: 'Disable USGS earthquakes' }));
    await user.click(source.getByRole('button', { name: 'Confirm disable' }));
    expect(await source.findByRole('alert')).toHaveTextContent('Enable the parent source first.');
    expect(source.getByText('Collection enabled')).toBeVisible();
    expect(useAuthStore.getState().user?.id).toBe(adminUser.id);
  });

  it.each(['test', 'reset', 'activation'] as const)(
    'aborts delayed %s errors before retrying as another administrator',
    async (operation) => {
      let release: () => void = () => undefined;
      const gate = new Promise<void>((resolve) => {
        release = resolve;
      });
      let signal: AbortSignal | undefined;
      let calls = 0;
      let refreshes = 0;
      const delayed = async ({ request }: { request: Request }) => {
        signal = request.signal;
        calls += 1;
        await gate;
        return apiError(401, 'unauthenticated', 'Expired session.');
      };
      server.use(
        http.post('/api/admin/sources/:id/test', delayed),
        http.post('/api/admin/sources/:id/reset', delayed),
        http.patch('/api/admin/sources/:id/activation', delayed),
        http.post('/api/auth/refresh', () => {
          refreshes += 1;
          return HttpResponse.json(tokenFor(adminUser));
        }),
      );
      const { user } = renderApp('/admin/sources', 'admin');
      const source = await row();
      const label =
        operation === 'activation' ? 'Disable' : operation === 'test' ? 'Test' : 'Reset';
      await user.click(source.getByRole('button', { name: `${label} USGS earthquakes` }));
      if (operation === 'activation')
        await user.click(source.getByRole('button', { name: 'Confirm disable' }));
      await waitFor(() => expect(calls).toBe(1));
      const otherAdmin = { ...adminUser, id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb' };
      server.use(http.get('/api/me', () => HttpResponse.json(otherAdmin)));
      act(() => useAuthStore.getState().setSession(tokenFor(otherAdmin)));
      expect(signal?.aborted).toBe(true);
      await act(async () => {
        release();
        await gate;
      });
      await row();
      expect(calls).toBe(1);
      expect(refreshes).toBe(0);
      expect(useAuthStore.getState().user?.id).toBe(otherAdmin.id);
    },
  );
});
