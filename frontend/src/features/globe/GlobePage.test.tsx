import { act, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { mockWebGl2 } from '@/test/env';
import { FakeMap } from '@/test/fakeMap';
import { renderApp } from '@/test/render';

vi.mock('maplibre-gl', () => import('@/test/fakeMap'));

describe('GlobePage', () => {
  beforeEach(() => {
    FakeMap.reset();
  });

  it('mounts the engine on the globe projection by default and switches to Mercator', async () => {
    mockWebGl2(true);
    const { user } = renderApp('/', 'user');
    expect(await screen.findByRole('region', { name: '3D globe' })).toBeInTheDocument();
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    const map = FakeMap.instances[0]!;
    expect(map.options).toMatchObject({
      style: 'https://tiles.openfreemap.org/styles/dark',
      center: [10, 30],
      zoom: 1.6,
    });
    expect(map.options.container).toBe(screen.getByTestId('map-container'));
    expect(map.setProjection).not.toHaveBeenCalled();

    act(() => {
      map.fire('style.load');
    });
    expect(map.setSky).toHaveBeenCalledWith(
      expect.objectContaining({ 'atmosphere-blend': expect.any(Array) }),
    );
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'globe' });

    const toolbar = screen.getByRole('group', { name: 'View mode' });
    expect(within(toolbar).getByRole('button', { name: 'Globe' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await user.click(within(toolbar).getByRole('button', { name: 'Map' }));
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'mercator' });
    expect(useGlobeStore.getState().mode).toBe('map');
    expect(screen.getByRole('region', { name: 'Map' })).toBeInTheDocument();

    await user.click(within(toolbar).getByRole('button', { name: 'Globe' }));
    expect(map.setProjection).toHaveBeenLastCalledWith({ type: 'globe' });
  });

  it('destroys the engine when the page unmounts', async () => {
    mockWebGl2(true);
    const { unmount } = renderApp('/', 'user');
    await waitFor(() => {
      expect(FakeMap.instances).toHaveLength(1);
    });
    unmount();
    expect(FakeMap.instances[0]!.remove).toHaveBeenCalledTimes(1);
  });

  it('explains that WebGL2 is required instead of mounting the engine', async () => {
    mockWebGl2(false);
    renderApp('/', 'user');
    expect(await screen.findByText('WebGL2 is required')).toBeInTheDocument();
    expect(screen.queryByTestId('map-container')).not.toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'View mode' })).toBeInTheDocument();
    expect(FakeMap.instances).toHaveLength(0);
  });

  it('treats a throwing canvas probe as unsupported', async () => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => {
      throw new Error('no canvas');
    });
    renderApp('/', 'user');
    expect(await screen.findByText('WebGL2 is required')).toBeInTheDocument();
  });
});
