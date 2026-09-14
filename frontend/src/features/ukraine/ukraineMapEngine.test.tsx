import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ukraineControl } from '@/test/fixtures.ukraine';
import { ukraineFrontlineReady, ukraineSpottedReady } from '@/test/fixtures.ukraineFigures';
import { applySession } from '@/test/render';

const engine = {
  setProjection: vi.fn(),
  setBaseLayer: vi.fn(),
  mount: vi.fn(),
  setLite: vi.fn(),
  fitBounds: vi.fn(),
  setLayers: vi.fn(),
  destroy: vi.fn(),
  handlers: {} as Record<string, (payload: unknown) => void>,
  on: vi.fn((event: string, handler: (payload: unknown) => void) => {
    engine.handlers[event] = handler;
    return () => undefined;
  }),
};

vi.mock('@/lib/map/webgl', () => ({ hasWebGl2: () => true }));
vi.mock('@/lib/map/MapLibreEngine', () => ({ createMapLibreEngine: () => engine }));

const { UkraineMap } = await import('./UkraineMap');

interface SettlementLayer {
  id: string;
  props: { onHover: (info: { object?: unknown; x: number; y: number }) => void };
}

describe('UkraineMap with a renderer', () => {
  beforeEach(() => {
    applySession('user');
    vi.clearAllMocks();
  });

  it('mounts a mercator map, draws the snapshot, shows hover details and refits', async () => {
    const user = userEvent.setup();
    const load = () => Promise.resolve(ukraineControl);
    const { unmount } = render(
      <UkraineMap
        loaders={{
          control: load,
          frontline: () => Promise.resolve(ukraineFrontlineReady),
          spotted: () => Promise.resolve(ukraineSpottedReady),
        }}
      />,
    );
    expect(screen.getByRole('region', { name: 'Reported control map' })).toBeInTheDocument();
    expect(engine.setProjection).toHaveBeenCalledWith('mercator');
    expect(engine.setBaseLayer).toHaveBeenCalledWith('dark');
    expect(engine.mount).toHaveBeenCalledTimes(1);
    expect(engine.fitBounds).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(engine.setLayers).toHaveBeenCalled());
    const layers = engine.setLayers.mock.calls[0]![0] as SettlementLayer[];
    const settlements = layers.find((layer) => layer.id === 'ukraine-settlements')!;
    act(() => settlements.props.onHover({ object: ukraineControl.settlements[0], x: 10, y: 20 }));
    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip).toHaveTextContent('Pokrovsk');
    expect(tooltip).toHaveTextContent('since 2026-08-30');
    act(() => settlements.props.onHover({ x: 0, y: 0 }));
    expect(screen.queryByRole('tooltip')).toBeNull();
    act(() => settlements.props.onHover({ object: ukraineControl.settlements[2], x: 1, y: 1 }));
    expect(await screen.findByRole('tooltip')).not.toHaveTextContent('since');
    await user.click(screen.getByRole('button', { name: 'Fit to Ukraine' }));
    expect(engine.fitBounds).toHaveBeenCalledTimes(2);
    const layerIds = (engine.setLayers.mock.calls.at(-1)![0] as { id: string }[]).map((l) => l.id);
    expect(layerIds).toContain('ukraine-frontline-areas');
    expect(layerIds).toContain('ukraine-spotted-losses');
    const spottedLayer = (engine.setLayers.mock.calls.at(-1)![0] as SettlementLayer[]).find(
      (layer) => layer.id === 'ukraine-spotted-losses',
    )!;
    act(() => spottedLayer.props.onHover({ object: ukraineSpottedReady.losses[0], x: 5, y: 6 }));
    expect(await screen.findByRole('tooltip')).toHaveTextContent('photographed loss, WarSpotting');
    act(() => engine.handlers.error?.({}));
    expect(await screen.findByText(/renderer reported an error/)).toBeInTheDocument();
    unmount();
    expect(engine.destroy).toHaveBeenCalledTimes(1);
  });
});
