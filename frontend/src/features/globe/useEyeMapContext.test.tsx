import { renderHook } from '@testing-library/react';
import { beforeAll, expect, it, vi } from 'vitest';

import {
  locateAssistantPoint,
  locateAssistantSource,
  readAssistantMapContext,
} from '@/lib/assistantMapContext';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures';
import type { Camera } from '@/lib/api/cameras';

import { useEyeMapContext } from './useEyeMapContext';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { InfrastructureSelection } from './infrastructure/useInfrastructure';

beforeAll(() => applySession('user'));

const camera = { id: 'tfl:1', title: 'London Bridge' } as Camera;
const infrastructure = {
  item: { id: 'infra-1', name: 'Grid substation' },
} as unknown as InfrastructureSelection;

function engine(bounds?: { west: number; south: number; east: number; north: number }) {
  return {
    getViewportBounds: vi.fn(() => bounds),
    flyTo: vi.fn(),
  } as unknown as GlobeEngineHandle & { flyTo: ReturnType<typeof vi.fn> };
}

it('prefers the selected camera, then infrastructure, then the event, and trims titles', () => {
  const map = engine({ west: -1, south: 50, east: 1, north: 52 });
  const event = liveEvent({ id: 'event-1', title: 'E'.repeat(200) });
  interface Props {
    cam: Camera | null;
    infra: InfrastructureSelection | null;
    record: typeof event;
  }
  const initialProps: Props = { cam: camera, infra: infrastructure, record: event };
  const { rerender, unmount } = renderHook(
    ({ cam, infra, record }: Props) =>
      useEyeMapContext(map, true, record, { selected: cam }, { selected: infra }),
    { initialProps },
  );
  expect(readAssistantMapContext()).toEqual({
    bounds: [-1, 50, 1, 52],
    selected: { kind: 'camera', id: 'tfl:1', title: 'London Bridge' },
  });
  rerender({ cam: null, infra: infrastructure, record: event });
  expect(readAssistantMapContext()?.selected).toEqual({
    kind: 'infrastructure',
    id: 'infra-1',
    title: 'Grid substation',
  });
  rerender({ cam: null, infra: null, record: event });
  const selected = readAssistantMapContext()?.selected;
  expect(selected?.kind).toBe('event');
  expect(selected?.title).toHaveLength(160);
  unmount();
  expect(readAssistantMapContext()).toBeNull();
});

it('flies to located points and selects sources only while the workspace is unchanged', () => {
  const map = engine(undefined);
  const select = vi.fn(() => true);
  renderHook(() =>
    useEyeMapContext(map, true, null, { selected: null }, { selected: null }, select),
  );
  expect(readAssistantMapContext()).toEqual({ bounds: null, selected: null });
  locateAssistantPoint({ lon: 10, lat: 20 });
  expect(map.flyTo).toHaveBeenCalledWith({ center: [10, 20], zoom: 6 });
  locateAssistantSource({ kind: 'event', id: 'record-1', point: { lon: 11, lat: 21 } });
  expect(select).toHaveBeenCalledOnce();

  invalidateWorkspaceAccess();
  map.flyTo.mockClear();
  locateAssistantPoint({ lon: 12, lat: 22 });
  locateAssistantSource({ kind: 'event', id: 'record-2', point: { lon: 12, lat: 22 } });
  expect(map.flyTo).not.toHaveBeenCalled();
  expect(select).toHaveBeenCalledOnce();
  expect(readAssistantMapContext()).toEqual({ bounds: null, selected: null });
});

it('registers nothing while disabled', () => {
  const map = engine({ west: 0, south: 0, east: 1, north: 1 });
  renderHook(() => useEyeMapContext(map, false, null, { selected: null }, { selected: null }));
  expect(readAssistantMapContext()).toBeNull();
});
