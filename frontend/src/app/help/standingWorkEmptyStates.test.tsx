/**
 * Each standing-work list says what the work is for and what to do first when it is
 * empty: areas, plans, subscriptions, annotation monitors and alert rules.
 */
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const empty = () => HttpResponse.json({ items: [] });

describe('standing-work empty states', () => {
  it('explains areas and plans and names the first step', async () => {
    server.use(http.get('/api/direction/aois', empty), http.get('/api/direction/plans', empty));
    renderApp('/direction', 'user');
    expect(await screen.findByText('No areas of interest yet')).toBeInTheDocument();
    expect(
      screen.getByText(/saved place you can reuse in research, subscriptions and collection plans/),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Draw an area on the map' })).toHaveAttribute(
      'href',
      '/?panel=area',
    );
    expect(await screen.findByText('No collection plans yet')).toBeInTheDocument();
    expect(screen.getByText(/sets out intelligence requirements/)).toBeInTheDocument();
    expect(screen.getByText('Write your first plan with the form below.')).toBeInTheDocument();
  });

  it('explains subscriptions and names the first step', async () => {
    server.use(http.get('/api/schedules', empty));
    renderApp('/subscriptions', 'user');
    expect(await screen.findByText('No subscriptions yet')).toBeInTheDocument();
    expect(
      screen.getByText(/runs the same research again on a schedule and saves each update/),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Choose a topic and create your first update below.'),
    ).toBeInTheDocument();
  });

  it('explains annotation monitors and links to the saved reports they start from', async () => {
    server.use(
      http.get('/api/annotation-monitors', () =>
        HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
      ),
    );
    renderApp('/annotation-monitors', 'user');
    expect(await screen.findByText('No annotation monitors yet')).toBeInTheDocument();
    expect(screen.getByText(/watches selected claims, identities or relationships/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Choose a saved report' })).toHaveAttribute(
      'href',
      '/research/saved',
    );
  });

  it('explains alert rules and names the first step', async () => {
    server.use(http.get('/api/warning/indicators', empty));
    renderApp('/warning', 'user');
    expect(await screen.findByText('No alert rules yet')).toBeInTheDocument();
    expect(
      screen.getByText(/raises an alert when enough matching items arrive within its time window/),
    ).toBeVisible();
    expect(
      screen.getByText(
        'Set up your first alert rule with the form below, or choose Watch this area on the map.',
      ),
    ).toBeVisible();
    expect(screen.getByRole('form', { name: 'New alert rule' })).toBeInTheDocument();
  });
});
