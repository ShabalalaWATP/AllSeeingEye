import { renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { liveEvent } from '@/test/fixtures';

import type { GlobeEngineHandle } from './useGlobeEngine';
import { useGlobeAssistant } from './useGlobeAssistant';

const seen = vi.hoisted(() => ({ selection: [] as unknown[], context: [] as unknown[] }));
const selectSource = vi.hoisted(() => () => true);
vi.mock('./useAssistantMapSelection', () => ({
  useAssistantMapSelection: (...args: unknown[]) => {
    seen.selection = args;
    return selectSource;
  },
}));
vi.mock('./useEyeMapContext', () => ({
  useEyeMapContext: (...args: unknown[]) => {
    seen.context = args;
  },
}));

it('shares the inspected record and lets the assistant select only visible records', () => {
  const engine = {} as GlobeEngineHandle;
  const event = liveEvent();
  const cameras = { selected: null };
  const infrastructure = { selected: null };
  const choose = vi.fn();
  const focusCamera = vi.fn();
  const focusInfrastructure = vi.fn();
  renderHook(() =>
    useGlobeAssistant({
      engine,
      supported: true,
      inspected: event,
      sources: { cameras, infrastructure } as never,
      selection: { pickableEvents: [event], choose },
      catalogue: { focusCamera, focusInfrastructure },
    }),
  );
  expect(seen.selection).toEqual([
    [event],
    cameras,
    infrastructure,
    choose,
    focusCamera,
    focusInfrastructure,
  ]);
  expect(seen.context).toEqual([engine, true, event, cameras, infrastructure, selectSource]);
});
