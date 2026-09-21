import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { adminUser, plainUser } from '@/test/fixtures';
import { researchUsagePage } from '@/test/fixtures.researchUsage';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('User research tiers', () => {
  it('assigns unlimited research using the exact revision and keeps its saved display after refresh', async () => {
    let body: unknown;
    let page = researchUsagePage();
    page = { ...page, items: page.items.map((item) => ({ ...item, revision: 7 })) };
    server.use(
      http.get('/api/admin/research-usage', () => HttpResponse.json(page)),
      http.put('/api/admin/users/:id/research-tier', async ({ request, params }) => {
        body = await request.json();
        expect(params.id).toBe(plainUser.id);
        const updated = {
          ...page.items.find((item) => item.user_id === plainUser.id)!,
          tier: 5 as const,
          label: 'Level 5',
          limit: null,
          remaining: null,
          period: 'day' as const,
          used: 37,
          revision: 8,
        };
        page = {
          ...page,
          items: page.items.map((item) => (item.user_id === updated.user_id ? updated : item)),
        };
        return HttpResponse.json(updated);
      }),
    );
    const { user } = renderApp('/admin/users', 'admin');
    const label = `Research allowance for ${plainUser.email}`;
    const select = await screen.findByRole('combobox', { name: label });
    expect(within(select).getByRole('option', { name: 'Level 5: Unlimited' })).toBeInTheDocument();
    await user.selectOptions(select, '5');
    await waitFor(() => expect(select).toHaveValue('5'));
    expect(body).toEqual({ tier: 5, expected_revision: 7 });
    const row = select.closest('tr');
    expect(row).not.toBeNull();
    const cells = within(row!);
    expect(cells.getByText('No limit on research runs')).toBeInTheDocument();
    expect(cells.getByText('37 runs recorded today (UTC)')).toBeInTheDocument();
    expect(cells.queryByText(/remaining|Resets|null/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Refresh' }));
    expect(await screen.findByRole('combobox', { name: label })).toHaveValue('5');
    expect(screen.getByText('37 runs recorded today (UTC)')).toBeInTheDocument();
  });

  it('allows an administrator to change their own research tier with the current revision', async () => {
    let body: unknown;
    server.use(
      http.put('/api/admin/users/:id/research-tier', async ({ request, params }) => {
        body = await request.json();
        expect(params.id).toBe(adminUser.id);
        return HttpResponse.json({
          ...researchUsagePage().items[0],
          tier: 3,
          label: 'Level 3',
          limit: 13,
          period: 'day',
          remaining: 12,
          revision: 1,
        });
      }),
    );
    const { user } = renderApp('/admin/users', 'admin');
    const select = await screen.findByRole('combobox', {
      name: `Research allowance for ${adminUser.email}`,
    });
    expect(
      within(select).getByRole('option', { name: 'Level 1: 4 runs per week' }),
    ).toBeInTheDocument();
    expect(
      within(select).getByRole('option', { name: 'Level 4: 32 runs per day' }),
    ).toBeInTheDocument();
    await user.selectOptions(select, '3');
    await waitFor(() => expect(select).toHaveValue('3'));
    expect(body).toEqual({ tier: 3, expected_revision: 0 });
    expect(screen.getByText('12 remaining · 1 used')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: `Role for ${adminUser.email}` })).toHaveValue(
      'admin',
    );
  });

  it('refreshes a conflicting tier without silently repeating the administrator change', async () => {
    let page = researchUsagePage();
    let writes = 0;
    server.use(
      http.get('/api/admin/research-usage', () => HttpResponse.json(page)),
      http.put('/api/admin/users/:id/research-tier', () => {
        writes += 1;
        page = {
          ...page,
          items: page.items.map((item) =>
            item.user_id === plainUser.id
              ? { ...item, tier: 2, label: 'Level 2', period: 'day', revision: 2 }
              : item,
          ),
        };
        return apiError(409, 'conflict', 'This research tier changed.');
      }),
    );
    const { user } = renderApp('/admin/users', 'admin');
    const select = await screen.findByRole('combobox', {
      name: `Research allowance for ${plainUser.email}`,
    });
    await user.selectOptions(select, '4');
    expect(
      await screen.findByText(/This allowance changed in another session/),
    ).toBeInTheDocument();
    await waitFor(() => expect(select).toHaveValue('2'));
    expect(writes).toBe(1);
  });

  it('keeps role management available when research allowances fail to load', async () => {
    server.use(
      http.get('/api/admin/research-usage', () =>
        apiError(503, 'unavailable', 'Allowance service unavailable.'),
      ),
    );
    renderApp('/admin/users', 'admin');
    expect(
      await screen.findByRole('combobox', { name: `Role for ${plainUser.email}` }),
    ).toBeEnabled();
    expect(await screen.findByText('Allowance service unavailable.')).toBeInTheDocument();
    expect(
      screen.queryByRole('combobox', { name: `Research allowance for ${plainUser.email}` }),
    ).not.toBeInTheDocument();
  });
});
