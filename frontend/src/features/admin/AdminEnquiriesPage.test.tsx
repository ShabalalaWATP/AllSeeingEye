import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import type { Enquiry } from '@/lib/api/enquiries';
import { apiError } from '@/test/handlers';
import { expectNoAxeViolations } from '@/test/axe';
import { installDialogStub } from '@/test/dialogStub';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

installDialogStub();

const ITEM: Enquiry = {
  id: 'a4148c10-4056-42ad-b8c1-b11199dc9c79',
  name: 'Example Contact',
  organisation: 'Example Company',
  email: 'contact@example.com',
  role: 'Analyst',
  deployment_interest: 'own_cloud',
  expected_users: '11_50',
  status: 'new',
  message: '<img src=x onerror=alert(1)>',
  created_at: '2026-09-01T12:00:00Z',
  updated_at: '2026-09-01T12:00:00Z',
};

function enabled() {
  server.use(
    http.get('/api/site', () =>
      HttpResponse.json({
        product_page_enabled: false,
        enterprise_enquiries_enabled: true,
        enterprise_enquiry_retention_days: 90,
      }),
    ),
  );
}

describe('AdminEnquiriesPage', () => {
  it('lists private enquiries, renders literal markup and copies the email', async () => {
    enabled();
    server.use(
      http.get('/api/admin/enquiries', () => HttpResponse.json({ items: [ITEM], total: 1 })),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    expect(await screen.findByRole('heading', { name: 'Example Company' })).toBeVisible();
    expect(screen.getByText(/90 days after submission/)).toBeVisible();
    await user.click(screen.getByText('Read message'));
    expect(screen.getByText(ITEM.message)).toBeVisible();
    expect(screen.getByText(ITEM.message).querySelector('img')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Copy email' }));
    expect(await navigator.clipboard.readText()).toBe(ITEM.email);
  });

  it('filters on the server and resets pagination', async () => {
    enabled();
    const calls: string[] = [];
    server.use(
      http.get('/api/admin/enquiries', ({ request }) => {
        calls.push(new URL(request.url).search);
        return HttpResponse.json({ items: [ITEM], total: 26 });
      }),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    await screen.findByRole('heading', { name: 'Example Company' });
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    await waitFor(() => expect(calls.at(-1)).toContain('offset=25'));
    await user.selectOptions(screen.getByLabelText('Enquiry status'), 'closed');
    await waitFor(() => expect(calls.at(-1)).toBe('?status=closed&offset=0&limit=25'));
  });

  it('marks contacted and refreshes the current queue', async () => {
    enabled();
    let changed = false;
    server.use(
      http.get('/api/admin/enquiries', () =>
        HttpResponse.json({ items: changed ? [] : [ITEM], total: changed ? 0 : 1 }),
      ),
      http.patch('/api/admin/enquiries/:id', async ({ request, params }) => {
        expect(params.id).toBe(ITEM.id);
        expect(await request.json()).toEqual({ status: 'contacted' });
        changed = true;
        return HttpResponse.json({ ...ITEM, status: 'contacted' });
      }),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    await user.click(await screen.findByRole('button', { name: 'Mark contacted' }));
    expect(await screen.findByText('Enquiry marked as contacted.')).toBeVisible();
    expect(await screen.findByText('No enquiries in this status.')).toBeVisible();
  });

  it('deletes only after explicit confirmation and supports cancelling', async () => {
    enabled();
    let deleted = false;
    server.use(
      http.get('/api/admin/enquiries', () =>
        HttpResponse.json({ items: deleted ? [] : [ITEM], total: deleted ? 0 : 1 }),
      ),
      http.delete('/api/admin/enquiries/:id', () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    let dialog = screen.getByRole('alertdialog');
    expect(within(dialog).getByText(/cannot be undone/)).toBeVisible();
    expect(deleted).toBe(false);
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(deleted).toBe(false);
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    dialog = screen.getByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Delete permanently' }));
    expect(await screen.findByText('Enquiry permanently deleted.')).toBeVisible();
    expect(deleted).toBe(true);
  });

  it('shows read and mutation errors without losing a retry', async () => {
    enabled();
    server.use(
      http.get('/api/admin/enquiries', () => apiError(503, 'unavailable', 'Try again later.')),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    expect(await screen.findByText('Try again later.')).toBeVisible();
    server.use(
      http.get('/api/admin/enquiries', () => HttpResponse.json({ items: [ITEM], total: 1 })),
      http.patch('/api/admin/enquiries/:id', () =>
        apiError(503, 'unavailable', 'Could not update.'),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Refresh enquiries' }));
    await user.click(await screen.findByRole('button', { name: 'Close enquiry' }));
    expect(await screen.findByText('Could not update.')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Example Company' })).toBeVisible();
  });

  it('hides the navigation and makes no private read when disabled', async () => {
    let reads = 0;
    server.use(
      http.get('/api/admin/enquiries', () => {
        reads += 1;
        return HttpResponse.json({ items: [], total: 0 });
      }),
    );
    renderApp('/admin/enquiries', 'admin');
    await screen.findByRole('heading', { name: /not found/i });
    expect(screen.queryByRole('link', { name: 'Enquiries' })).not.toBeInTheDocument();
    expect(reads).toBe(0);
  });

  it.each(['anonymous', 'user'] as const)(
    'blocks private reads for %s visitors',
    async (session) => {
      enabled();
      let reads = 0;
      server.use(
        http.get('/api/admin/enquiries', () => {
          reads += 1;
          return HttpResponse.json({ items: [ITEM], total: 1 });
        }),
      );
      renderApp('/admin/enquiries', session);
      if (session === 'anonymous') await screen.findByRole('heading', { name: 'Sign in' });
      else await screen.findByText('Admin access required');
      expect(screen.queryByText(ITEM.organisation)).not.toBeInTheDocument();
      expect(reads).toBe(0);
    },
  );

  it('keeps a late previous-filter response out of the selected queue', async () => {
    enabled();
    let release!: () => void;
    const response = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    server.use(
      http.get('/api/admin/enquiries', async ({ request }) => {
        if (new URL(request.url).searchParams.get('status') === 'new') {
          started = true;
          await response;
          return HttpResponse.json({ items: [ITEM], total: 1 });
        }
        return HttpResponse.json({ items: [], total: 0 });
      }),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    await waitFor(() => expect(started).toBe(true));
    await user.selectOptions(screen.getByLabelText('Enquiry status'), 'closed');
    await screen.findByText('No enquiries in this status.');
    await act(async () => {
      release();
      await response;
    });
    expect(screen.queryByText(ITEM.organisation)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Enquiry status')).toHaveValue('closed');
  });

  it('returns to the previous page after removing the last result on a later page', async () => {
    enabled();
    const calls: number[] = [];
    let changed = false;
    server.use(
      http.get('/api/admin/enquiries', ({ request }) => {
        calls.push(Number(new URL(request.url).searchParams.get('offset')));
        return HttpResponse.json({ items: [ITEM], total: changed ? 25 : 26 });
      }),
      http.delete('/api/admin/enquiries/:id', () => {
        changed = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    await screen.findByRole('heading', { name: ITEM.organisation });
    screen.getByRole('button', { name: 'Next page' }).focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(calls.at(-1)).toBe(25));
    expect(screen.getByRole('heading', { name: 'Enquiry results' })).toHaveFocus();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await user.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete permanently' }),
    );
    await waitFor(() => expect(calls).toEqual([0, 25, 0]));
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled();
    expect(screen.getByText('Enquiry permanently deleted.')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Enquiry results' })).toHaveFocus();
  });

  it('exposes semantic content and lets the keyboard cancel deletion with restored focus', async () => {
    enabled();
    server.use(
      http.get('/api/admin/enquiries', () => HttpResponse.json({ items: [ITEM], total: 1 })),
    );
    const { user } = renderApp('/admin/enquiries', 'admin');
    const trigger = await screen.findByRole('button', { name: 'Delete' });
    await expectNoAxeViolations();
    trigger.focus();
    await user.keyboard('{Enter}');
    const cancel = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(trigger).toHaveFocus();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('keeps enquiries in the admin mobile navigation and closes it after keyboard selection', async () => {
    enabled();
    const original = window.matchMedia.bind(window);
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
      const media = original(query);
      if (query.includes('max-width')) Object.defineProperty(media, 'matches', { value: true });
      return media;
    });
    server.use(http.get('/api/admin/enquiries', () => HttpResponse.json({ items: [], total: 0 })));
    const { user, router } = renderApp('/admin/users', 'admin');
    const trigger = await screen.findByRole('button', { name: 'Open administration navigation' });
    trigger.focus();
    await user.keyboard('{Enter}');
    const dialog = screen.getByRole('dialog', { name: 'Administration navigation' });
    const nav = within(dialog).getByRole('navigation', { name: 'Administration' });
    expect(within(dialog).queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument();
    const link = await within(nav).findByRole('link', { name: 'Enquiries' });
    link.focus();
    await user.keyboard('{Enter}');
    expect(router.state.location.pathname).toBe('/admin/enquiries');
    await screen.findByRole('heading', { name: 'Enquiries', level: 1 });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
