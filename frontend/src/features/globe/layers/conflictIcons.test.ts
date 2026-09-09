import { expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';
import { CONFLICT_SYMBOLS } from '@/lib/conflictSymbols';
import { buildEventLayers } from './registry';

function event(id: string, subtype: string, precision: 'exact' | 'city' = 'city') {
  return liveEvent({
    id,
    category: 'conflict',
    subtype,
    point: { lat: 50, lon: 30 },
    geo_confidence: precision,
  });
}

it.each([false, true])(
  'renders distinct selectable protest, riot and battle symbols with their precision rings on globe=%s',
  (globe) => {
    const events = [event('march', 'protest'), event('riot', 'riot'), event('battle', 'fight')];
    const onPick = vi.fn();
    const layers = buildEventLayers(events, [], onPick, 'riot', {
      globe,
      zoom: 5,
      onCluster: vi.fn(),
    });
    const icons = layers.find((layer) => layer.id === 'event-icons');
    expect(icons?.props).toMatchObject({ data: events, pickable: true, billboard: !globe });
    expect(layers.find((layer) => layer.id === 'approximate-events')?.props).toMatchObject({
      data: events,
    });
    const props = icons!.props as unknown as {
      getIcon: (event: LiveEvent) => { url: string };
      getColor: (event: LiveEvent) => number[];
      getSize: (event: LiveEvent) => number;
      onClick: (info: { object: LiveEvent }) => boolean;
    };
    expect(new Set(events.map((item) => props.getIcon(item).url)).size).toBe(3);
    expect(props.getColor(events[0]!)).toEqual([...CONFLICT_SYMBOLS.protests.colour, 245]);
    expect(props.getColor(events[1]!)).toEqual([...CONFLICT_SYMBOLS.riots.colour, 245]);
    expect(props.getSize(events[1]!)).toBeGreaterThan(props.getSize(events[0]!));
    props.onClick({ object: events[1]! });
    expect(onPick).toHaveBeenCalledWith(events[1]);
    expect(layers.some((layer) => layer.id === 'selected-event-halo')).toBe(true);
    expect(
      buildEventLayers(events, [], onPick, null).some(
        (layer) => layer.id === 'selected-event-halo',
      ),
    ).toBe(false);
    expect(buildEventLayers(events, ['conflict'], onPick, null)).toHaveLength(0);
  },
);

it('renders precise and approximate reports once each with rings only on approximate reports', () => {
  const precise = event('precise', 'riot', 'exact');
  const approximate = event('approximate', 'protest');
  const layers = buildEventLayers([precise, approximate], [], vi.fn(), null, {
    zoom: 10,
    onCluster: vi.fn(),
  });
  expect(layers.find((layer) => layer.id === 'event-icons')?.props).toMatchObject({
    data: [precise, approximate],
  });
  expect(layers.find((layer) => layer.id === 'approximate-events')?.props).toMatchObject({
    data: [approximate],
  });
  expect(layers.some((layer) => layer.id === 'events-conflict')).toBe(false);
});

it('clusters exact reports at low zoom without duplicating them or the approximate report', () => {
  const precise = ['a', 'b', 'c'].map((id) => event(id, 'fight', 'exact'));
  const approximate = event('approximate', 'protest');
  const layers = buildEventLayers([...precise, approximate], [], vi.fn(), null, {
    globe: true,
    zoom: 1.5,
    onCluster: vi.fn(),
  });
  expect(layers.find((layer) => layer.id === 'clusters')?.props).toMatchObject({
    data: [{ category: 'conflict', count: 3, members: precise }],
  });
  expect(layers.find((layer) => layer.id === 'event-icons')?.props).toMatchObject({
    data: [approximate],
  });
  expect(layers.find((layer) => layer.id === 'approximate-events')?.props).toMatchObject({
    data: [approximate],
  });
});
