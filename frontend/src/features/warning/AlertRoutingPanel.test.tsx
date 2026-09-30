import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { indicator } from '@/test/fixtures.warning';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const route = {
  indicator_id: indicator.id,
  configured_by: indicator.created_by,
  email_enabled: false,
  webhook_id: null,
  revision: 0,
  can_manage: true,
};
const destination = {
  id: 'abcdabcd-abcd-4bcd-8bcd-abcdabcdabcd',
  name: 'Operations',
  created_by: indicator.created_by,
  team_id: null,
  enabled: true,
  created_at: '2026-09-30T10:00:00Z',
};

async function openPanel(canManage = true) {
  server.use(
    http.get('/api/warning/indicators/:id/notifications', () =>
      HttpResponse.json({ ...route, can_manage: canManage }),
    ),
    http.get('/api/warning/webhook-destinations', () => HttpResponse.json({ items: [] })),
  );
  const rendered = renderApp('/warning', 'user');
  const table = await screen.findByRole('table', { name: 'Indicators' });
  await rendered.user.click(within(table).getByRole('button', { name: 'Notifications' }));
  const panel = await screen.findByRole('region', {
    name: `Notification routing for ${indicator.name}`,
  });
  return { ...rendered, panel: within(panel) };
}

describe('alert rule notification routing', () => {
  it('registers a secret destination, saves selected channels and removes the destination', async () => {
    let registration: unknown;
    let saved: unknown;
    let removed = false;
    server.use(
      http.post('/api/warning/webhook-destinations', async ({ request }) => {
        registration = await request.json();
        return HttpResponse.json(destination, { status: 201 });
      }),
      http.put('/api/warning/indicators/:id/notifications', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        saved = body;
        return HttpResponse.json({ ...route, ...body, revision: 1 });
      }),
      http.delete('/api/warning/webhook-destinations/:id', () => {
        removed = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user, panel } = await openPanel();
    expect(panel.getByLabelText('Store alerts in the application (always on)')).toBeDisabled();
    expect(panel.getByLabelText('Email me when this rule fires')).not.toBeChecked();
    await user.click(panel.getByText('Register or remove a webhook'));
    await user.type(panel.getByLabelText('Destination name'), 'Operations');
    const secret = panel.getByLabelText('HTTPS webhook URL');
    expect(secret).toHaveAttribute('type', 'password');
    await user.type(secret, 'https://example.com/secret');
    await user.click(panel.getByRole('button', { name: 'Register webhook' }));
    await waitFor(() => expect(secret).toHaveValue(''));
    expect(registration).toEqual({
      name: 'Operations',
      url: 'https://example.com/secret',
      team_id: null,
    });
    await user.selectOptions(
      panel.getByLabelText('Registered webhook destination'),
      destination.id,
    );
    await user.click(panel.getByLabelText('Email me when this rule fires'));
    await user.click(panel.getByRole('button', { name: 'Save notification routing' }));
    expect(await panel.findByText('Notification routing saved.')).toBeInTheDocument();
    expect(saved).toEqual({
      email_enabled: true,
      webhook_id: destination.id,
      expected_revision: 0,
    });
    await user.click(panel.getByRole('button', { name: 'Remove Operations' }));
    await waitFor(() => expect(removed).toBe(true));
    await waitFor(() =>
      expect(panel.getByLabelText('Registered webhook destination')).toHaveValue(''),
    );
  });

  it('keeps external choices disabled for a team reader', async () => {
    const { panel } = await openPanel(false);
    expect(panel.getByLabelText('Email me when this rule fires')).toBeDisabled();
    expect(panel.getByRole('button', { name: 'Save notification routing' })).toBeDisabled();
    expect(panel.getByText(/Only the personal rule owner/)).toBeInTheDocument();
  });

  it('discloses the separate installation copy and keeps mutation errors visible', async () => {
    server.use(
      http.get('/api/warning/notification-capabilities', () =>
        HttpResponse.json({
          installation_copy_enabled: true,
          in_app_required: true,
          installation_copy_notice:
            'Personal and team rule alerts include title, summary, countries and event IDs.',
        }),
      ),
      http.put('/api/warning/indicators/:id/notifications', () =>
        HttpResponse.json(
          { error: { code: 'conflict', message: 'Routing changed. Reload it before saving.' } },
          { status: 409 },
        ),
      ),
    );
    const { panel, user } = await openPanel();
    expect(await panel.findByText('Installation-wide copy enabled')).toBeInTheDocument();
    expect(panel.getByText(/Personal and team rule alerts/)).toBeInTheDocument();
    await user.click(panel.getByRole('button', { name: 'Save notification routing' }));
    expect(await panel.findByText('Routing changed. Reload it before saving.')).toBeInTheDocument();
  });

  it('does not claim that alerts stay in-app when installation settings are unavailable', async () => {
    server.use(
      http.get(
        '/api/warning/notification-capabilities',
        () => new HttpResponse(null, { status: 503 }),
      ),
    );
    const { panel } = await openPanel();
    expect(
      await panel.findByText(/Installation copy settings could not be checked/),
    ).toBeInTheDocument();
  });
});
