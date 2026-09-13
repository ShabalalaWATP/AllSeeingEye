import { renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import type { CameraState } from './cameras/useCameras';
import type { InfrastructureState } from './infrastructure/useInfrastructure';
import { useAssistantMapSelection } from './useAssistantMapSelection';

const point = { lon: -0.1, lat: 51.5 };
const emptyInfrastructure = {
  data: null,
  cablesEnabled: false,
  stationsEnabled: false,
  nuclearEnabled: false,
  dataCentresEnabled: false,
  energyEnabled: false,
  semiconductorEnabled: false,
} as unknown as InfrastructureState;

it('selects a cited event from the visible map collection and rejects absent records', () => {
  const event = liveEvent({ id: 'event-1', point });
  const choose = vi.fn();
  const { result } = renderHook(() =>
    useAssistantMapSelection(
      [event],
      { visible: [] } as unknown as CameraState,
      emptyInfrastructure,
      choose,
      vi.fn(),
      vi.fn(),
    ),
  );
  expect(result.current({ kind: 'event', id: 'event-1', point })).toBe(true);
  expect(choose).toHaveBeenCalledWith(event);
  expect(result.current({ kind: 'event', id: 'not-visible', point })).toBe(false);
  expect(result.current({ kind: 'gnss', id: 'aggregate', point })).toBe(false);
});

it('opens a camera or infrastructure inspector only while its layer contains the record', () => {
  const camera = { id: 'camera-1', title: 'Bridge camera' };
  const cable = { id: 'cable-1', name: 'Public cable route' };
  const focusCamera = vi.fn();
  const focusInfrastructure = vi.fn();
  const infrastructure = {
    ...emptyInfrastructure,
    data: {
      cables: [cable],
      ground_stations: [],
      nuclear_facilities: [],
      data_centres: [],
      energy_sites: [],
      semiconductor_sites: [],
    },
    cablesEnabled: true,
  } as unknown as InfrastructureState;
  const { result, rerender } = renderHook(
    ({ enabled }) =>
      useAssistantMapSelection(
        [],
        { visible: [camera] } as unknown as CameraState,
        { ...infrastructure, cablesEnabled: enabled },
        vi.fn(),
        focusCamera,
        focusInfrastructure,
      ),
    { initialProps: { enabled: false } },
  );
  expect(result.current({ kind: 'camera', id: camera.id, point })).toBe(true);
  expect(focusCamera).toHaveBeenCalledWith(camera);
  expect(result.current({ kind: 'infrastructure', id: cable.id, point })).toBe(false);
  rerender({ enabled: true });
  expect(result.current({ kind: 'infrastructure', id: cable.id, point })).toBe(true);
  expect(focusInfrastructure).toHaveBeenCalledWith({ kind: 'cable', item: cable });
});
