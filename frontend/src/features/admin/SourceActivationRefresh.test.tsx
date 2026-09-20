import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { sources, adminUser, tokenFor } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import AdminSourcesPage from './AdminSourcesPage';

function family(enabled: boolean) {
  return ['google_news', 'research_google_news_en', 'research_google_news_fr'].map((id, index) => ({
    ...sources[0],
    id,
    name: `News ${index}`,
    enabled: enabled && index !== 2,
    test_available: index === 0,
    environment_disabled: false,
    health: { ...sources[0]!.health, source_id: id },
  }));
}

async function row(name: string) {
  return within((await screen.findByText(name)).closest('tr')!);
}

it('reloads inherited source states after toggles and preserves a child opt-out', async () => {
  applySession('admin');
  let enabled = true;
  server.use(
    http.get('/api/admin/sources', () => HttpResponse.json({ items: family(enabled) })),
    http.patch('/api/admin/sources/:id/activation', async ({ request }) => {
      enabled = ((await request.json()) as { enabled: boolean }).enabled;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  render(<AdminSourcesPage />);
  expect((await row('News 1')).getByText('Collection enabled')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Disable News 0' }));
  await user.click(screen.getByRole('button', { name: 'Confirm disable' }));
  expect(await (await row('News 1')).findByText('Collection disabled')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Enable News 0' }));
  await user.click(screen.getByRole('button', { name: 'Confirm enable' }));
  expect(await (await row('News 1')).findByText('Collection enabled')).toBeVisible();
  expect((await row('News 2')).getByText('Collection disabled')).toBeVisible();
});

it('hides stale states while reloading, shows reload failures and supports recovery', async () => {
  applySession('admin');
  let changed = false;
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/admin/sources', async () => {
      if (!changed) return HttpResponse.json({ items: family(true) });
      await gate;
      return apiError(503, 'unavailable', 'Source statuses could not be loaded.');
    }),
    http.patch('/api/admin/sources/:id/activation', () => {
      changed = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  render(<AdminSourcesPage />);
  await row('News 0');
  await user.click(screen.getByRole('button', { name: 'Disable News 0' }));
  await user.click(screen.getByRole('button', { name: 'Confirm disable' }));
  expect(await screen.findByText('Loading sources')).toBeVisible();
  expect(screen.queryByRole('table', { name: 'Sources' })).not.toBeInTheDocument();
  await act(async () => {
    release();
    await gate;
  });
  expect(await screen.findByText('Source statuses could not be loaded.')).toBeVisible();
  server.use(http.get('/api/admin/sources', () => HttpResponse.json({ items: family(false) })));
  await user.click(screen.getByRole('button', { name: 'Refresh' }));
  expect((await row('News 1')).getByText('Collection disabled')).toBeVisible();
});

it('discards a previous administrator’s delayed post-activation list', async () => {
  applySession('admin');
  let changed = false;
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/admin/sources', async () => {
      if (!changed) return HttpResponse.json({ items: family(true) });
      await gate;
      return HttpResponse.json({ items: family(false) });
    }),
    http.patch('/api/admin/sources/:id/activation', () => {
      changed = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const user = userEvent.setup();
  render(<AdminSourcesPage />);
  await row('News 0');
  await user.click(screen.getByRole('button', { name: 'Disable News 0' }));
  await user.click(screen.getByRole('button', { name: 'Confirm disable' }));
  await screen.findByText('Loading sources');
  server.use(http.get('/api/admin/sources', () => HttpResponse.json({ items: [] })));
  act(() =>
    useAuthStore
      .getState()
      .setSession(tokenFor({ ...adminUser, id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb' })),
  );
  await screen.findByText('No sources are registered.');
  await act(async () => {
    release();
    await gate;
  });
  expect(screen.queryByText('News 1')).not.toBeInTheDocument();
});
