import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { GLOBE_PREFS_KEY, useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

import { CoordinateReadout, formatCoordinate } from './CoordinateReadout';
import type { CursorHandler } from './engine/MapEngine';
import type { GlobeEngineHandle } from './useGlobeEngine';

function fakeHandle() {
  const handlers = new Set<CursorHandler>();
  const handle: GlobeEngineHandle = {
    setLayers: vi.fn(),
    flyTo: vi.fn(),
    onCursor: (handler) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
  };
  return { handle, handlers };
}

describe('CoordinateReadout', () => {
  it('formats hemispheres and four decimals', () => {
    expect(formatCoordinate({ lon: -0.1278, lat: 51.5074 })).toBe('51.5074° N, 0.1278° W');
    expect(formatCoordinate({ lon: 151.2093, lat: -33.8688 })).toBe('33.8688° S, 151.2093° E');
    expect(formatCoordinate({ lon: 0, lat: 0 })).toBe('0.0000° N, 0.0000° E');
  });

  it('shows nothing until the cursor moves, then keeps the last position and copies it', async () => {
    const { handle, handlers } = fakeHandle();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const { unmount } = render(<CoordinateReadout engine={handle} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(handlers.size).toBe(1);
    act(() => {
      for (const handler of handlers) handler({ lon: -0.1278, lat: 51.5074 });
    });
    const button = screen.getByRole('button', { name: 'Copy coordinates' });
    expect(button).toHaveTextContent('51.5074° N, 0.1278° W');
    await userEvent.click(button);
    expect(writeText).toHaveBeenCalledWith('51.5074° N, 0.1278° W');
    expect(button).toHaveTextContent('Copied');
    unmount();
    expect(handlers.size).toBe(0);
  });

  it('stays quiet when the clipboard refuses', async () => {
    const { handle, handlers } = fakeHandle();
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('no')) },
    });
    render(<CoordinateReadout engine={handle} />);
    act(() => {
      for (const handler of handlers) handler({ lon: 1, lat: 2 });
    });
    await userEvent.click(screen.getByRole('button', { name: 'Copy coordinates' }));
    expect(screen.getByRole('button')).toHaveTextContent('2.0000° N, 1.0000° E');
  });
});

describe('display preferences', () => {
  it('persists the base layer, terminator and lite mode but not the view mode', () => {
    useGlobeStore.getState().setBaseLayer('hybrid');
    useGlobeStore.getState().toggleTerminator();
    useGlobeStore.getState().toggleLite();
    useGlobeStore.getState().setMode('map');
    const stored = JSON.parse(localStorage.getItem(GLOBE_PREFS_KEY) ?? '{}') as {
      state: Record<string, unknown>;
    };
    expect(stored.state).toEqual({ baseLayer: 'hybrid', terminator: false, lite: true });
  });

  it('holds the brand mark still in lite mode', async () => {
    useGlobeStore.setState({ lite: true });
    renderApp('/admin/users', 'admin');
    const marks = await screen.findAllByTestId('evil-eye');
    expect(marks[0]).toHaveAttribute('data-flame-speed', '0');
    expect(marks[0]).toHaveAttribute('data-max-fps', '1');
  });
});
