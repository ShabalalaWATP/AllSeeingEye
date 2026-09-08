import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useRef } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { BaseLayer } from '@/stores/globe';

import type { MapEngine, MapEngineFactory } from './engine/MapEngine';
import { useGlobeEngine } from './useGlobeEngine';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));
vi.mock('@deck.gl/maplibre', () => import('@/test/fakeDeck'));

function fakeEngine() {
  return {
    mount: vi.fn(),
    setProjection: vi.fn(),
    setBaseLayer: vi.fn(),
    setLite: vi.fn(),
    onCursor: vi.fn(() => vi.fn()),
    on: vi.fn(() => vi.fn()),
    destroy: vi.fn(),
    captureImage: vi.fn(),
    setLayers: vi.fn(),
    spin: vi.fn(),
    flyTo: vi.fn(),
    getZoom: vi.fn(() => 2),
    getCamera: vi.fn(() => null),
    restoreCamera: vi.fn(),
    getViewportBounds: vi.fn(() => null),
    fitBounds: vi.fn(),
  } satisfies MapEngine;
}

const layers = [{ id: 'selected-events' }];
function Harness({
  factory,
  baseLayer = 'hybrid',
  enabled = true,
}: {
  factory: MapEngineFactory;
  baseLayer?: BaseLayer;
  enabled?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const engine = useGlobeEngine(container, {
    enabled,
    mode: 'map',
    lite: true,
    baseLayer,
    createEngine: factory,
  });
  return (
    <>
      <div ref={container} />
      <button
        onClick={() => {
          engine.setLayers(layers);
          engine.spin(true);
        }}
      >
        Set scene
      </button>
    </>
  );
}

describe('engine replacement', () => {
  it('reapplies unchanged view preferences when the factory changes', () => {
    const first = fakeEngine();
    const second = fakeEngine();
    const firstFactory = vi.fn(() => first);
    const secondFactory = vi.fn(() => second);
    const { rerender } = render(<Harness factory={firstFactory} />);
    rerender(<Harness factory={secondFactory} />);
    expect(first.destroy).toHaveBeenCalledOnce();
    expect(second.setProjection).toHaveBeenCalledWith('mercator');
    expect(second.setBaseLayer).toHaveBeenCalledWith('hybrid');
    expect(second.setLite).toHaveBeenCalledWith(true);
    rerender(<Harness factory={secondFactory} baseLayer="light" />);
    expect(secondFactory).toHaveBeenCalledOnce();
    expect(second.setBaseLayer).toHaveBeenLastCalledWith('light');
  });

  it('restores the latest scene after replacement or temporary disablement', async () => {
    const first = fakeEngine();
    const second = fakeEngine();
    const secondFactory = () => second;
    const { rerender } = render(<Harness factory={() => first} />);
    await userEvent.click(screen.getByRole('button', { name: 'Set scene' }));
    rerender(<Harness factory={secondFactory} />);
    expect(second.setLayers).toHaveBeenLastCalledWith(layers);
    expect(second.spin).toHaveBeenLastCalledWith(true);
    rerender(<Harness factory={secondFactory} enabled={false} />);
    expect(second.destroy).toHaveBeenCalledOnce();
    second.setLayers.mockClear();
    rerender(<Harness factory={secondFactory} />);
    expect(second.setLayers).toHaveBeenLastCalledWith(layers);
  });
});
