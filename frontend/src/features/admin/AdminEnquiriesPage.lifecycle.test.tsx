import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';

import type { Enquiry } from '@/lib/api/enquiries';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const ITEM: Enquiry = {
  id: 'a4148c10-4056-42ad-b8c1-b11199dc9c79',
  name: 'Example Contact',
  organisation: 'Example Company',
  email: 'contact@example.test',
  role: '',
  deployment_interest: 'on_premises',
  expected_users: '1_10',
  status: 'contacted',
  message: '',
  created_at: '2026-09-01T12:00:00Z',
  updated_at: '2026-09-01T12:00:00Z',
};

beforeEach(() => {
  server.use(
    http.get('/api/site', () =>
      HttpResponse.json({
        product_page_enabled: false,
        enterprise_enquiries_enabled: true,
        enterprise_enquiry_retention_days: 90,
      }),
    ),
  );
});

it('closes a contacted enquiry and offers only applicable actions for closed records', async () => {
  let status: Enquiry['status'] = 'contacted';
  server.use(
    http.get('/api/admin/enquiries', ({ request }) =>
      HttpResponse.json({
        items:
          new URL(request.url).searchParams.get('status') === status ? [{ ...ITEM, status }] : [],
        total: new URL(request.url).searchParams.get('status') === status ? 1 : 0,
      }),
    ),
    http.patch('/api/admin/enquiries/:id', async ({ request }) => {
      expect(await request.json()).toEqual({ status: 'closed' });
      status = 'closed';
      return HttpResponse.json({ ...ITEM, status });
    }),
  );
  const { user } = renderApp('/admin/enquiries', 'admin');
  await user.selectOptions(await screen.findByLabelText('Enquiry status'), 'contacted');
  await screen.findByRole('heading', { name: ITEM.organisation });
  expect(screen.getByText('No message supplied.')).toBeVisible();
  expect(screen.getByText('On premises')).toBeVisible();
  expect(screen.getByText('1 to 10')).toBeVisible();
  expect(screen.getByText(ITEM.name)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Mark contacted' })).toBeNull();
  await user.click(screen.getByRole('button', { name: 'Close enquiry' }));
  expect(await screen.findByText('Enquiry marked as closed.')).toBeVisible();
  await screen.findByText('No enquiries in this status.');
  await user.selectOptions(screen.getByLabelText('Enquiry status'), 'closed');
  await screen.findByRole('heading', { name: ITEM.organisation });
  expect(screen.queryByRole('button', { name: 'Close enquiry' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Mark contacted' })).toBeEnabled();
  expect(screen.queryByText('Enquiry marked as closed.')).toBeNull();
});

it('reports a malformed refresh without replacing the last valid page and can recover', async () => {
  let reads = 0;
  server.use(
    http.get('/api/admin/enquiries', () => {
      reads += 1;
      return HttpResponse.json(
        reads === 2
          ? { items: [{ ...ITEM, status: 'unknown' }], total: 1 }
          : { items: [ITEM], total: 1 },
      );
    }),
  );
  const { user } = renderApp('/admin/enquiries', 'admin');
  await screen.findByRole('heading', { name: ITEM.organisation });
  await user.click(screen.getByRole('button', { name: 'Refresh enquiries' }));
  expect(await screen.findByText('The server sent an unexpected response.')).toBeVisible();
  expect(screen.getByRole('heading', { name: ITEM.organisation })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Refresh enquiries' }));
  await waitFor(() => expect(reads).toBe(3));
  await waitFor(() =>
    expect(screen.queryByText('The server sent an unexpected response.')).toBeNull(),
  );
});

it.each([false, true])(
  'aborts an old filter mutation and ignores its later result (failure=%s)',
  async (failure) => {
    let signal: AbortSignal | undefined;
    let release!: () => void;
    const response = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/admin/enquiries', ({ request }) =>
        HttpResponse.json({
          items: new URL(request.url).searchParams.get('status') === 'new' ? [ITEM] : [],
          total: new URL(request.url).searchParams.get('status') === 'new' ? 1 : 0,
        }),
      ),
      http.patch('/api/admin/enquiries/:id', async ({ request }) => {
        signal = request.signal;
        await response;
        return failure
          ? apiError(503, 'unavailable', 'Old mutation failed.')
          : HttpResponse.json({ ...ITEM, status: 'closed' });
      }),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    await user.click(await screen.findByRole('button', { name: 'Close enquiry' }));
    await waitFor(() => expect(signal).toBeDefined());
    expect(screen.getByRole('button', { name: 'Refresh enquiries' })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Enquiry status'), 'closed');
    await screen.findByText('No enquiries in this status.');
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      release();
      await response;
    });
    expect(screen.getByLabelText('Enquiry status')).toHaveValue('closed');
    expect(screen.queryByText(ITEM.organisation)).toBeNull();
    expect(screen.queryByText('Enquiry marked as closed.')).toBeNull();
    expect(screen.queryByText('Old mutation failed.')).toBeNull();
  },
);

it('moves backwards with a stable keyboard focus target', async () => {
  const offsets: number[] = [];
  server.use(
    http.get('/api/admin/enquiries', ({ request }) => {
      offsets.push(Number(new URL(request.url).searchParams.get('offset')));
      return HttpResponse.json({ items: [ITEM], total: 26 });
    }),
  );
  const { user } = renderApp('/admin/enquiries', 'admin');
  await screen.findByRole('heading', { name: ITEM.organisation });
  await user.click(screen.getByRole('button', { name: 'Next page' }));
  const previous = await screen.findByRole('button', { name: 'Previous page' });
  await waitFor(() => expect(previous).toBeEnabled());
  previous.focus();
  await user.keyboard('{Enter}');
  await waitFor(() => expect(offsets).toEqual([0, 25, 0]));
  expect(screen.getByRole('heading', { name: 'Enquiry results' })).toHaveFocus();
});
