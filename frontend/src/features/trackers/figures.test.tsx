import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('public figures tracker', () => {
  it('lists office-holders with their placement basis and reporting', async () => {
    const { user } = renderApp('/trackers/figures', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Public figures' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(await screen.findByText('Office-holders tracked')).toBeInTheDocument();
    expect(
      screen.getByText(/absence of reporting never means an official is at home/),
    ).toBeVisible();
    const list = screen.getByRole('list', { name: 'Public figures' });
    const cards = within(list).getAllByRole('listitem');
    expect(cards).toHaveLength(3);
    expect(within(cards[0]!).getByText('Volodymyr Zelenskyy')).toBeVisible();
    expect(within(cards[0]!).getByText(/Reported location · 2 mentions/)).toBeVisible();
    await user.click(within(cards[0]!).getByRole('button', { name: /Volodymyr Zelenskyy/ }));
    const reporting = screen.getByRole('region', { name: 'Reporting naming Volodymyr Zelenskyy' });
    expect(within(reporting).getByText(/front-line troops/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Wikimedia Commons' })).toHaveAttribute(
      'href',
      'https://commons.wikimedia.org/wiki/File:Example.jpg',
    );
    await user.type(screen.getByRole('searchbox', { name: 'Find a figure' }), 'burnham');
    expect(within(list).getAllByRole('listitem')).toHaveLength(1);
    expect(within(list).getByText(/Seat of office · 0 mentions/)).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Generate report' })).not.toBeInTheDocument();
  });

  it('shows a readable error when the board cannot load', async () => {
    server.use(http.get('/api/figures', () => HttpResponse.json({}, { status: 503 })));
    renderApp('/trackers/figures', 'user');
    expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Public figures' })).not.toBeInTheDocument();
  });

  it('links to the tracker from the live monitor', async () => {
    renderApp('/trackers', 'user');
    const modules = await screen.findByRole('list', { name: 'Modules' }, { timeout: 5000 });
    expect(within(modules).getByRole('link', { name: 'Public figures' })).toHaveAttribute(
      'href',
      '/trackers/figures',
    );
  });
});
