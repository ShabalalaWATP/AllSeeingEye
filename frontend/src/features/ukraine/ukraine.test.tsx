import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it, vi } from 'vitest';

import { ukraineBoard, ukraineControl } from '@/test/fixtures.ukraine';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { buildControlLayers } from './controlLayers';

beforeAll(async () => {
  await import('./UkrainePage');
});

describe('Ukraine war page', () => {
  it('shows the day count, freshness and the reported control table when WebGL is absent', async () => {
    renderApp('/conflicts/ukraine', 'user');
    expect(
      await screen.findByRole('heading', { name: 'Ukraine war' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(await screen.findByText('Day 1,663 of the full-scale invasion')).toBeInTheDocument();
    const freshness = screen.getByRole('list', { name: 'Freshness' });
    expect(within(freshness).getByText(/General Staff claim:/)).toBeInTheDocument();
    expect(screen.getByText(/This browser cannot draw the map/)).toBeInTheDocument();
    const table = await screen.findByRole('table', {
      name: 'Reported control by oblast (populated places)',
    });
    expect(within(table).getByText("Donets'k")).toBeInTheDocument();
    expect(within(table).getByText('1,430')).toBeInTheDocument();
    expect(within(table).queryByText('Kyiv')).not.toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Map legend' })).toHaveTextContent(
      'Russian-held (reported)',
    );
  });

  it('groups updates by who reports them and narrows every group by lens', async () => {
    const { user } = renderApp('/conflicts/ukraine', 'user');
    const groups = await screen.findByRole('group', { name: 'Reporting group' }, { timeout: 5000 });
    const assessments = within(screen.getByRole('list', { name: 'Assessments' }));
    expect(
      assessments.getByRole('link', {
        name: 'Russian Offensive Campaign Assessment, September 12, 2026',
      }),
    ).toHaveAttribute('href', 'https://understandingwar.org/example');
    await user.click(within(groups).getByRole('button', { name: /Russian and independent/ }));
    const russian = within(screen.getByRole('list', { name: 'Russian and independent Russian' }));
    expect(russian.getByText('state media')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Workforce' }));
    expect(screen.getByText('Nothing retained for this group in the window.')).toBeInTheDocument();
    expect(within(groups).getByRole('button', { name: /Ukrainian reporting \(1\)/ })).toBeVisible();
    await user.click(within(groups).getByRole('button', { name: /Ukrainian reporting/ }));
    const ukrainian = screen.getByRole('list', { name: 'Ukrainian reporting' });
    expect(
      within(ukrainian).getByRole('link', { name: 'Mobilisation rules tightened' }),
    ).toBeInTheDocument();
  });

  it('badges claimed figures as claims and links the original post', async () => {
    renderApp('/conflicts/ukraine', 'user');
    const figures = await screen.findByRole(
      'list',
      { name: 'Headline figures' },
      { timeout: 5000 },
    );
    const cards = [...figures.querySelectorAll(':scope > li')] as HTMLElement[];
    expect(cards).toHaveLength(10);
    expect(within(cards[1]!).getByText('12,344')).toBeInTheDocument();
    expect(within(cards[1]!).getByText('+2 claimed on 2026-09-13')).toBeInTheDocument();
    expect(within(figures).getAllByText('Claimed')).toHaveLength(6);
    expect(within(cards[6]!).getByText('5,892')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Original post' })).toHaveAttribute(
      'href',
      'https://www.facebook.com/GeneralStaff.ua/posts/example',
    );
    expect(screen.getByRole('link', { name: 'VIINA 2.0 territorial control' })).toHaveAttribute(
      'href',
      'https://github.com/zhukovyuri/VIINA',
    );
  });

  it('reports a failed board without hiding the sources', async () => {
    server.use(
      http.get('/api/conflicts/ukraine', () =>
        HttpResponse.json({ error: 'server_error', message: 'Board unavailable' }, { status: 500 }),
      ),
    );
    renderApp('/conflicts/ukraine', 'user');
    expect(await screen.findByRole('alert', undefined, { timeout: 5000 })).toHaveTextContent(
      /status 500/,
    );
    expect(screen.getByRole('heading', { name: /Sources and what this page/ })).toBeInTheDocument();
  });

  it('reaches the page from the rail', async () => {
    const { user } = renderApp('/economy', 'user');
    await user.click(await screen.findByRole('link', { name: 'Ukraine war' }, { timeout: 5000 }));
    expect(await screen.findByRole('heading', { name: 'Ukraine war' })).toBeInTheDocument();
  });
});

describe('control layers', () => {
  it('draws areas, outlines and settlements with colours that follow the reported status', () => {
    const onHover = vi.fn();
    const layers = buildControlLayers(ukraineControl, onHover);
    expect(layers.map((layer) => layer.id)).toEqual([
      'ukraine-control-ru',
      'ukraine-control-contested',
      'ukraine-oblast-outlines',
      'ukraine-settlements',
    ]);
    const settlements = layers[3]!.props as unknown as {
      getFillColor: (row: (typeof ukraineControl.settlements)[number]) => number[];
      onHover: (info: { object?: unknown; x: number; y: number }) => void;
    };
    expect(settlements.getFillColor(ukraineControl.settlements[1]!)).toEqual([239, 108, 72, 230]);
    expect(settlements.getFillColor(ukraineControl.settlements[2]!)).toEqual([56, 189, 248, 170]);
    settlements.onHover({ object: ukraineControl.settlements[0], x: 4, y: 5 });
    expect(onHover).toHaveBeenCalledWith(ukraineControl.settlements[0], 4, 5);
    settlements.onHover({ x: 0, y: 0 });
    expect(onHover).toHaveBeenLastCalledWith(null, 0, 0);
    expect(ukraineBoard.control?.counts.ru).toBe(5892);
  });
});
