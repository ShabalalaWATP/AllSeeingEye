import { act, render } from '@testing-library/react';
import { afterEach, beforeEach, expect, it } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';

import { useStreamedEventList } from './useStreamedEventList';

const frames: { selected: string | null; ids: string[] }[] = [];

function Probe() {
  const list = useStreamedEventList();
  const selected = useEventsStore((state) => state.selectedId);
  frames.push({ selected, ids: list.map((event) => event.id) });
  return null;
}

beforeEach(() => {
  frames.length = 0;
  useEventsStore.getState().reset();
});
afterEach(() => {
  useEventsStore.getState().reset();
});

it('renders an ordinary delta after urgent work, in its own transition', () => {
  useEventsStore.getState().applyUpsert([liveEvent({ id: 'a' })]);
  render(<Probe />);
  frames.length = 0;
  act(() => {
    useEventsStore.getState().applyUpsert([liveEvent({ id: 'b' })]);
    useEventsStore.getState().select('a');
  });
  // The selection commits first with the previous list; the delta follows.
  expect(frames[0]).toEqual({ selected: 'a', ids: ['a'] });
  expect(frames.at(-1)).toEqual({ selected: 'a', ids: ['a', 'b'] });
});

it('applies a cleared mirror and the first records after it at once', () => {
  useEventsStore.getState().applyUpsert([liveEvent({ id: 'a' })]);
  render(<Probe />);
  frames.length = 0;
  act(() => {
    useEventsStore.getState().handleStreamMessage({
      event: 'event.resync',
      data: '{"reason":"stream_gap"}',
      id: null,
    });
    useEventsStore.getState().cancelLoad();
    useEventsStore.getState().select('x');
  });
  expect(frames[0]).toEqual({ selected: 'x', ids: [] });
  frames.length = 0;
  act(() => {
    useEventsStore.getState().applyUpsert([liveEvent({ id: 'fresh' })]);
    useEventsStore.getState().select('fresh');
  });
  expect(frames).toEqual([{ selected: 'fresh', ids: ['fresh'] }]);
});

it('shows the latest list when deltas arrive faster than they render', () => {
  render(<Probe />);
  act(() => {
    useEventsStore.getState().applyUpsert([liveEvent({ id: 'a' })]);
  });
  frames.length = 0;
  act(() => {
    for (const id of ['b', 'c', 'd']) useEventsStore.getState().applyUpsert([liveEvent({ id })]);
  });
  expect(frames.at(-1)?.ids).toEqual(['a', 'b', 'c', 'd']);
  expect(frames.length).toBeLessThanOrEqual(1);
  expect(useEventsStore.getState().list).toHaveLength(4);
});

it('picks up a change made between the first render and its subscription', () => {
  function Late() {
    const list = useStreamedEventList();
    frames.push({ selected: null, ids: list.map((event) => event.id) });
    if (frames.length === 1) useEventsStore.setState({ list: [liveEvent({ id: 'late' })] });
    return null;
  }
  render(<Late />);
  expect(frames.at(-1)?.ids).toEqual(['late']);
});
