import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { initialCapabilitiesState, useCapabilitiesStore } from '@/stores/capabilities';
import { useGlobeStore } from '@/stores/globe';
import { server } from '@/test/server';

import { BaseLayerToolbar } from './BaseLayerToolbar';

describe('BaseLayerToolbar', () => {
  it('offers the free layers, marks the current one and reports a choice', async () => {
    const onChange = vi.fn();
    render(<BaseLayerToolbar value="hybrid" osAvailable={false} onChange={onChange} />);
    const group = screen.getByRole('group', { name: 'Base layer' });
    expect(
      within(group)
        .getAllByRole('button')
        .map((b) => b.textContent),
    ).toEqual(['Dark', 'Satellite', 'Hybrid']);
    expect(within(group).getByRole('button', { name: 'Hybrid' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(within(group).getByRole('button', { name: 'Dark' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
    await userEvent.click(within(group).getByRole('button', { name: 'Satellite' }));
    expect(onChange).toHaveBeenCalledWith('satellite');
  });

  it('adds the Ordnance Survey styles when the server can proxy them', () => {
    render(<BaseLayerToolbar value="dark" osAvailable onChange={vi.fn()} />);
    expect(screen.getAllByRole('button')).toHaveLength(6);
    expect(screen.getByRole('button', { name: 'OS Outdoor' })).toBeInTheDocument();
  });
});

describe('globe store base layer', () => {
  it('starts dark and remembers the choice', () => {
    expect(useGlobeStore.getState().baseLayer).toBe('dark');
    useGlobeStore.getState().setBaseLayer('os_light');
    expect(useGlobeStore.getState().baseLayer).toBe('os_light');
  });
});

describe('capabilities store', () => {
  beforeEach(() => {
    useCapabilitiesStore.setState({ ...initialCapabilitiesState });
  });

  it('loads once and keeps the defaults when the request fails', async () => {
    let requests = 0;
    server.use(
      http.get('/api/capabilities', () => {
        requests += 1;
        return HttpResponse.json({ os_maps: true, os_layers: ['Road_3857'] });
      }),
    );
    await useCapabilitiesStore.getState().load();
    await useCapabilitiesStore.getState().load();
    expect(requests).toBe(1);
    expect(useCapabilitiesStore.getState()).toMatchObject({ osMaps: true, loaded: true });

    useCapabilitiesStore.setState({ ...initialCapabilitiesState });
    server.use(
      http.get('/api/capabilities', () =>
        HttpResponse.json({ error: { code: 'x', message: 'down' } }, { status: 500 }),
      ),
    );
    await useCapabilitiesStore.getState().load();
    expect(useCapabilitiesStore.getState()).toMatchObject({ osMaps: false, loaded: true });
  });
});
