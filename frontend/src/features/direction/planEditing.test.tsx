import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { plan } from '@/test/fixtures';
import { planEvidence } from '@/test/fixtures.direction';
import { planFromBody } from '@/test/handlers.direction';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const conflictBody = {
  error: { code: 'conflict', message: 'This plan was changed after you opened it.' },
};

async function openEditor() {
  const result = renderApp(`/direction/plans/${plan.id}`, 'user');
  await screen.findByRole('heading', { name: 'Kharkiv axis' });
  await result.user.click(screen.getByRole('button', { name: 'Edit plan' }));
  const form = await screen.findByRole('form', { name: 'Edit Kharkiv axis' });
  return { ...result, form };
}

describe('collection plan editor', () => {
  it('creates a plan with several PIRs and SIRs from repeatable groups', async () => {
    let captured: unknown = null;
    server.use(
      http.post('/api/direction/plans', async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(planFromBody(captured as never), { status: 201 });
      }),
    );
    const { user } = renderApp('/direction', 'user');
    const form = await screen.findByRole('form', { name: 'New collection plan' });
    await user.type(within(form).getByLabelText('Plan name'), 'Sumy watch');
    await user.type(within(form).getByLabelText('Nations'), 'ua');
    await user.type(
      within(form).getByLabelText('PIR-1 priority intelligence requirement'),
      'Is Sumy next?',
    );
    await user.type(within(form).getByLabelText('SIR-1.1 specific requirement'), 'Strikes');
    await user.type(within(form).getByLabelText('SIR-1.1 keywords'), 'Sumy, strike');
    await user.type(within(form).getByLabelText('SIR-1.1 categories'), 'conflict');
    await user.click(
      within(form).getByRole('button', { name: 'Add specific requirement to PIR-1' }),
    );
    await user.type(within(form).getByLabelText('SIR-1.2 specific requirement'), 'Talks');
    await user.click(
      within(form).getByRole('button', { name: 'Add priority intelligence requirement' }),
    );
    await user.type(
      within(form).getByLabelText('PIR-2 priority intelligence requirement'),
      'Who supplies the axis?',
    );
    await user.type(within(form).getByLabelText('SIR-2.1 specific requirement'), 'Rail traffic');
    await user.click(within(form).getByRole('button', { name: 'Add plan' }));
    await waitFor(() => {
      expect(captured).toEqual({
        name: 'Sumy watch',
        enabled: true,
        description: '',
        aoi_id: null,
        countries: ['UA'],
        pirs: [
          {
            text: 'Is Sumy next?',
            sirs: [
              { text: 'Strikes', keywords: ['Sumy', 'strike'], categories: ['conflict'] },
              { text: 'Talks' },
            ],
          },
          { text: 'Who supplies the axis?', sirs: [{ text: 'Rail traffic' }] },
        ],
      });
    });
    await waitFor(() => {
      expect(within(form).getByLabelText('Plan name')).toHaveValue('');
    });
  });

  it('shows field-level errors for empty or invalid groups and sends nothing', async () => {
    let posted = false;
    server.use(
      http.post('/api/direction/plans', () => {
        posted = true;
        return HttpResponse.json(plan, { status: 201 });
      }),
    );
    const { user } = renderApp('/direction', 'user');
    const form = await screen.findByRole('form', { name: 'New collection plan' });
    await user.type(within(form).getByLabelText('Nations'), 'ua, xx1');
    await user.type(within(form).getByLabelText('SIR-1.1 categories'), 'bogus');
    await user.click(within(form).getByRole('button', { name: 'Add plan' }));
    expect(within(form).getByText('Enter a plan name.')).toBeInTheDocument();
    expect(within(form).getByText('Enter the requirement question.')).toBeInTheDocument();
    expect(within(form).getByText('Enter the specific requirement.')).toBeInTheDocument();
    expect(within(form).getByText('Unknown categories: bogus.')).toBeInTheDocument();
    expect(within(form).getByText(/Check: xx1/)).toBeInTheDocument();
    expect(within(form).getByLabelText('PIR-1 priority intelligence requirement')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
    expect(within(form).getByLabelText('Nations')).toHaveValue('ua, xx1');
    expect(posted).toBe(false);
  });

  it('loads the plan, edits groups in place and sends the expected revision', async () => {
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.put(`/api/direction/plans/${plan.id}`, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...planFromBody(captured), updated_at: '2026-09-05T09:00:00Z' });
      }),
    );
    const { user, form } = await openEditor();
    expect(within(form).getByLabelText('Plan name')).toHaveValue('Kharkiv axis');
    expect(within(form).getByLabelText('SIR-1.2 keywords')).toHaveValue('talks');
    expect(within(form).getByText(/Codes follow position/)).toBeInTheDocument();
    expect(within(form).queryByLabelText('Workspace')).toBeNull();
    await user.click(within(form).getByRole('button', { name: 'Remove SIR-1.1' }));
    // The former SIR-1.2 takes the first position and its code.
    expect(within(form).getByLabelText('SIR-1.1 specific requirement')).toHaveValue(
      'Talks or ceasefire moves',
    );
    await user.click(
      within(form).getByRole('button', { name: 'Add priority intelligence requirement' }),
    );
    await user.type(
      within(form).getByLabelText('PIR-2 priority intelligence requirement'),
      'Next?',
    );
    await user.type(within(form).getByLabelText('SIR-2.1 specific requirement'), 'Signals');
    await user.click(within(form).getByRole('button', { name: 'Save plan' }));
    await waitFor(() => {
      expect(captured).not.toBeNull();
    });
    expect(captured).toMatchObject({
      expected_updated_at: plan.updated_at,
      aoi_id: plan.aoi_id,
      enabled: true,
      pirs: [
        { text: plan.pirs[0]?.text, sirs: [{ text: 'Talks or ceasefire moves' }] },
        { text: 'Next?', sirs: [{ text: 'Signals' }] },
      ],
    });
    expect(captured).not.toHaveProperty('team_id');
    await waitFor(() => {
      expect(screen.queryByRole('form', { name: 'Edit Kharkiv axis' })).toBeNull();
    });
  });

  it('keeps the draft on a stale save and reconciles only on an explicit choice', async () => {
    const bodies: Record<string, unknown>[] = [];
    const latest = { ...plan, name: 'Renamed elsewhere', updated_at: '2026-09-05T08:00:00Z' };
    server.use(
      http.put(`/api/direction/plans/${plan.id}`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        bodies.push(body);
        if (body.expected_updated_at !== latest.updated_at)
          return HttpResponse.json(conflictBody, { status: 409 });
        return HttpResponse.json({ ...planFromBody(body), updated_at: '2026-09-05T09:00:00Z' });
      }),
      http.get(`/api/direction/plans/${plan.id}/definition`, () => HttpResponse.json(latest)),
    );
    const { user, form } = await openEditor();
    const name = within(form).getByLabelText('Plan name');
    await user.clear(name);
    await user.type(name, 'My local name');
    await user.click(within(form).getByRole('button', { name: 'Save plan' }));
    const panel = await within(form).findByRole('region', { name: 'Latest saved version' });
    expect(within(panel).getByText(/Renamed elsewhere/)).toBeInTheDocument();
    expect(within(form).getByLabelText('Plan name')).toHaveValue('My local name');
    expect(within(form).getByRole('button', { name: 'Save plan' })).toBeDisabled();
    await user.click(
      within(form).getByRole('button', { name: 'Keep my edits to save over the latest version' }),
    );
    await user.click(within(form).getByRole('button', { name: 'Save plan' }));
    await waitFor(() => {
      expect(bodies).toHaveLength(2);
    });
    expect(bodies[1]).toMatchObject({
      name: 'My local name',
      expected_updated_at: latest.updated_at,
    });
  });

  it('can replace the draft with the latest version after a conflict', async () => {
    const latest = { ...plan, name: 'Renamed elsewhere', updated_at: '2026-09-05T08:00:00Z' };
    server.use(
      http.put(`/api/direction/plans/${plan.id}`, () =>
        HttpResponse.json(conflictBody, { status: 409 }),
      ),
      http.get(`/api/direction/plans/${plan.id}/definition`, () => HttpResponse.json(latest)),
    );
    const { user, form } = await openEditor();
    await user.click(within(form).getByRole('button', { name: 'Save plan' }));
    await user.click(
      await within(form).findByRole('button', {
        name: 'Load the latest version and discard my edits',
      }),
    );
    expect(within(form).getByLabelText('Plan name')).toHaveValue('Renamed elsewhere');
    expect(within(form).getByRole('button', { name: 'Save plan' })).toBeEnabled();
  });

  it('keeps the draft after a failed save and retries the same edit', async () => {
    let attempts = 0;
    server.use(
      http.put(`/api/direction/plans/${plan.id}`, async ({ request }) => {
        attempts += 1;
        if (attempts === 1)
          return HttpResponse.json(
            { error: { code: 'internal', message: 'The server could not save.' } },
            { status: 500 },
          );
        return HttpResponse.json(planFromBody((await request.json()) as never));
      }),
    );
    const { user, form } = await openEditor();
    const name = within(form).getByLabelText('Plan name');
    await user.clear(name);
    await user.type(name, 'Kept name');
    await user.click(within(form).getByRole('button', { name: 'Save plan' }));
    expect(await within(form).findByText(/Your draft is kept/)).toBeInTheDocument();
    expect(within(form).getByLabelText('Plan name')).toHaveValue('Kept name');
    await user.click(within(form).getByRole('button', { name: 'Save plan' }));
    await waitFor(() => {
      expect(screen.queryByRole('form', { name: 'Edit Kharkiv axis' })).toBeNull();
    });
    expect(attempts).toBe(2);
  });

  it('does not offer editing to a reader who cannot manage the plan', async () => {
    server.use(
      http.get(`/api/direction/plans/${plan.id}`, () =>
        HttpResponse.json({
          ...planEvidence,
          plan: { ...plan, created_by: '99999999-9999-4999-8999-999999999999' },
        }),
      ),
    );
    renderApp(`/direction/plans/${plan.id}`, 'user');
    await screen.findByRole('heading', { name: 'Kharkiv axis' });
    expect(screen.getByRole('button', { name: 'Edit plan' })).toBeDisabled();
  });
});
