import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { MapNavigationTools } from './MapNavigationTools';

function engineAt(zoom = 4): GlobeEngineHandle {
  return {
    getCamera: () => ({ center: [10, 40], zoom, bearing: 60, pitch: 30 }),
    restoreCamera: vi.fn(),
    flyTo: vi.fn(),
    getZoom: () => zoom,
    setLayers: vi.fn(),
    spin: vi.fn(),
    onCursor: () => () => undefined,
    onClick: () => () => undefined,
    onView: () => () => undefined,
  };
}

describe('compact map navigation', () => {
  afterEach(() => {
    Reflect.deleteProperty(document, 'fullscreenEnabled');
    Reflect.deleteProperty(document, 'fullscreenElement');
    Reflect.deleteProperty(document, 'exitFullscreen');
    Reflect.deleteProperty(document.documentElement, 'requestFullscreen');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('zooms around the current centre and keeps zoom within renderer limits', () => {
    const engine = engineAt(22);
    render(<MapNavigationTools engine={engine} enabled />);
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(engine.flyTo).toHaveBeenLastCalledWith({ center: [10, 40], zoom: 22 });
    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }));
    expect(engine.flyTo).toHaveBeenLastCalledWith({ center: [10, 40], zoom: 21 });
  });

  it('resets orientation without losing the current place, and offers a world reset', () => {
    const engine = engineAt();
    render(<MapNavigationTools engine={engine} enabled />);
    fireEvent.click(screen.getByRole('button', { name: 'Reset north-up' }));
    expect(engine.restoreCamera).toHaveBeenLastCalledWith({
      center: [10, 40],
      zoom: 4,
      bearing: 0,
      pitch: 0,
    });
    fireEvent.click(screen.getByRole('button', { name: 'Reset world view' }));
    expect(engine.restoreCamera).toHaveBeenLastCalledWith({
      center: [0, 20],
      zoom: 1.5,
      bearing: 0,
      pitch: 0,
    });
  });

  it('does not move an unavailable or unmounted map', () => {
    const engine = engineAt();
    engine.getCamera = () => null;
    const { rerender } = render(<MapNavigationTools engine={engine} enabled />);
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(engine.flyTo).not.toHaveBeenCalled();
    rerender(<MapNavigationTools engine={engine} enabled={false} />);
    expect(screen.getByRole('button', { name: 'Zoom in' })).toBeDisabled();
  });

  it('reports fullscreen rejection without an unhandled promise', async () => {
    Object.defineProperty(document, 'fullscreenEnabled', { value: true, configurable: true });
    const request = vi.fn().mockRejectedValue(new Error('Denied'));
    Object.defineProperty(document.documentElement, 'requestFullscreen', {
      value: request,
      configurable: true,
    });
    render(<MapNavigationTools engine={engineAt()} enabled />);
    fireEvent.click(screen.getByRole('button', { name: 'Enter fullscreen' }));
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Fullscreen is unavailable'),
    );
    Reflect.deleteProperty(document.documentElement, 'requestFullscreen');
  });

  it('tracks browser fullscreen changes and exits through the visible control', async () => {
    let fullscreen: Element | null = null;
    Object.defineProperty(document, 'fullscreenEnabled', { value: true, configurable: true });
    Object.defineProperty(document, 'fullscreenElement', {
      get: () => fullscreen,
      configurable: true,
    });
    const enter = vi.fn(() => {
      fullscreen = document.documentElement;
      fireEvent(document, new Event('fullscreenchange'));
      return Promise.resolve();
    });
    const exit = vi.fn(() => {
      fullscreen = null;
      fireEvent(document, new Event('fullscreenchange'));
      return Promise.resolve();
    });
    Object.defineProperty(document.documentElement, 'requestFullscreen', {
      value: enter,
      configurable: true,
    });
    Object.defineProperty(document, 'exitFullscreen', { value: exit, configurable: true });
    render(<MapNavigationTools engine={engineAt()} enabled />);
    fireEvent.click(screen.getByRole('button', { name: 'Enter fullscreen' }));
    expect(enter).toHaveBeenCalledOnce();
    const exitButton = await screen.findByRole('button', { name: 'Exit fullscreen' });
    expect(exitButton).toHaveAttribute('aria-pressed', 'true');
    expect(exitButton).toHaveAttribute('title', 'Exit fullscreen');
    fireEvent.click(exitButton);
    expect(exit).toHaveBeenCalledOnce();
    expect(await screen.findByRole('button', { name: 'Enter fullscreen' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });
});
