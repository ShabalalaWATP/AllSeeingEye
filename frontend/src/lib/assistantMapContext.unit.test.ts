import { afterEach, expect, it, vi } from 'vitest';
import {
  clearAssistantMapFocus,
  locateAssistantPoint,
  readAssistantMapContext,
  registerAssistantMapContext,
} from './assistantMapContext';

const releases: (() => void)[] = [];
afterEach(() => {
  releases.splice(0).forEach((release) => release());
  clearAssistantMapFocus();
  vi.restoreAllMocks();
});

it('reads bounds on demand and keeps a new map registered when an old map cleans up', () => {
  let west = 170;
  const first = registerAssistantMapContext(() => ({
    bounds: [-180, -90, 180, 90],
    selected: null,
  }));
  releases.push(first);
  releases.push(
    registerAssistantMapContext(() => ({ bounds: [west, -20, -170, 20], selected: null })),
  );
  first();
  expect(readAssistantMapContext()?.bounds).toEqual([170, -20, -170, 20]);
  west = 175;
  expect(readAssistantMapContext()?.bounds).toEqual([175, -20, -170, 20]);
  west = Infinity;
  expect(readAssistantMapContext()?.bounds).toBeNull();
});

it('queues only one explicit valid focus until the map mounts and expires stale navigation', () => {
  const now = vi.spyOn(Date, 'now').mockReturnValue(1000);
  locateAssistantPoint({ lon: 20, lat: 40 });
  locateAssistantPoint({ lon: 21, lat: 41 });
  locateAssistantPoint({ lon: Infinity, lat: 41 });
  const focus = vi.fn();
  const release = registerAssistantMapContext(() => ({ bounds: null, selected: null }), focus);
  releases.push(release);
  expect(focus).toHaveBeenCalledExactlyOnceWith({ lon: 21, lat: 41 });
  release();
  locateAssistantPoint({ lon: 20, lat: 40 });
  now.mockReturnValue(6001);
  releases.push(registerAssistantMapContext(() => ({ bounds: null, selected: null }), focus));
  expect(focus).toHaveBeenCalledTimes(1);
});

it('clears pending map navigation on an authority transition', () => {
  locateAssistantPoint({ lon: 20, lat: 40 });
  clearAssistantMapFocus();
  const focus = vi.fn();
  releases.push(registerAssistantMapContext(() => ({ bounds: null, selected: null }), focus));
  expect(focus).not.toHaveBeenCalled();
});
