import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { LlmProfile } from '@/lib/api/llm';
import { adminUser, llmProfiles } from '@/test/fixtures';
import { navigationUnconfigured } from '@/test/handlers.capabilities';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const [draft] = llmProfiles as [LlmProfile];
const tested: LlmProfile = { ...draft, is_tested: true, tested_revision: 1, is_bound: true };

function configureAi() {
  server.use(
    http.get('/api/admin/llm/profiles', () =>
      HttpResponse.json({ items: [tested], encryption_available: true }),
    ),
    http.get('/api/admin/llm/connections', () =>
      HttpResponse.json({
        items: [
          {
            team_id: null,
            user_id: null,
            profile_id: tested.id,
            profile_revision: 1,
            tested_config_hash: 'hash',
            activated_at: '2026-09-01T00:00:00Z',
            activated_by: adminUser.id,
            revision: 1,
          },
        ],
      }),
    ),
  );
}

function row(list: HTMLElement, title: string) {
  const item = within(list).getByText(title).closest('li');
  if (item === null) throw new Error(`No checklist row for ${title}`);
  return within(item);
}

describe('SetupChecklistCard', () => {
  it('opens on a fresh installation with each step, its state and where to do it', async () => {
    renderApp('/admin', 'admin');
    const card = await screen.findByRole('article', { name: 'Setup checklist' });
    expect(within(card).getByText('AI research is not ready')).toBeVisible();
    const essentials = within(card).getByRole('region', { name: 'Essential steps' });
    expect(row(essentials, 'Connect an AI provider').getByText('Done')).toBeVisible();
    expect(row(essentials, 'Test the connection').getByText('Not done')).toBeVisible();
    expect(row(essentials, 'Assign it to research').getByText('Not done')).toBeVisible();
    for (const name of ['Connect an AI provider', 'Test the connection', 'Assign it to research'])
      expect(within(essentials).getByRole('link', { name })).toHaveAttribute('href', '/admin/llm');
    const optional = within(card).getByRole('region', { name: 'Optional steps' });
    expect(row(optional, 'Email relay (optional)').getByText('Done')).toBeVisible();
    expect(
      row(optional, 'Ordnance Survey maps key (optional)').getByText('Not done'),
    ).toBeVisible();
    expect(row(optional, 'Feeds contact (optional)').getByText('ASE_FEEDS_CONTACT')).toBeVisible();
    expect(within(optional).queryByRole('link')).not.toBeInTheDocument();
  });

  it('folds away once the essentials are done and can be reopened', async () => {
    configureAi();
    const { user } = renderApp('/admin', 'admin');
    const card = await screen.findByRole('article', { name: 'Setup checklist' });
    const summary = within(card).getByText('Essentials done · 2 optional left');
    expect(summary).toBeVisible();
    expect(within(card).getByText('Assign it to research')).not.toBeVisible();
    await user.click(summary);
    expect(within(card).getByText('Assign it to research')).toBeVisible();
  });

  it('is absent when every step is done', async () => {
    configureAi();
    let checks = 0;
    server.use(
      http.get('/api/capabilities', () => {
        checks += 1;
        return HttpResponse.json({ os_maps: true, os_layers: ['Road_3857'], ai_research: true });
      }),
      http.get('/api/navigation/capabilities', () => {
        checks += 1;
        return HttpResponse.json({
          ...navigationUnconfigured,
          operator_contact: 'operator@example.org',
          available: true,
          configuration_message: null,
        });
      }),
    );
    renderApp('/admin', 'admin');
    await screen.findByRole('article', { name: 'AI connections' });
    await waitFor(() => expect(checks).toBe(2));
    await screen.findByText('Global connection tested');
    expect(screen.queryByRole('article', { name: 'Setup checklist' })).not.toBeInTheDocument();
  });

  it('marks an optional check that fails as unknown and retries a failed AI lookup', async () => {
    server.use(
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({ error: { code: 'x', message: 'Down.' } }, { status: 500 }),
      ),
    );
    const first = renderApp('/admin', 'admin');
    const card = await first.findByRole('article', { name: 'Setup checklist' });
    const optional = within(card).getByRole('region', { name: 'Optional steps' });
    expect(row(optional, 'Email relay (optional)').getByText('Unknown')).toBeVisible();
    first.unmount();

    // Both the checklist and the AI connections card read connections once on load.
    let failures = 2;
    server.use(
      http.get('/api/admin/llm/connections', () => {
        if (failures-- > 0)
          return HttpResponse.json(
            { error: { code: 'server_error', message: 'Connections unavailable.' } },
            { status: 500 },
          );
        return HttpResponse.json({ items: [] });
      }),
    );
    const { user } = renderApp('/admin', 'admin');
    const failed = await screen.findByRole('article', { name: 'Setup checklist' });
    await user.click(await within(failed).findByRole('button', { name: 'Retry setup checklist' }));
    expect(
      await within(await screen.findByRole('article', { name: 'Setup checklist' })).findByRole(
        'region',
        { name: 'Essential steps' },
      ),
    ).toBeVisible();
  });
});
