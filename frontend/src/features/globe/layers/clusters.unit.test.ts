import { describe, expect, it, vi } from 'vitest';

import type { Category } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';

import { buildClusterLayers, cellSizeFor, clusterEvents, clusterRadius } from './clusters';
import { buildIconLayer, headingOf, iconFor } from './icons';
import { buildEventLayers } from './registry';

const near = (id: string, lon: number, lat: number, category: Category = 'news') =>
  liveEvent({ id, category, point: { lon, lat } });

describe('clusters', () => {
  it('bins located events per category and leaves small cells loose', () => {
    const events = [
      near('a', 10.1, 50.1),
      near('b', 10.4, 50.4),
      near('c', 10.9, 50.9),
      near('d', 10.2, 50.2, 'conflict'),
      liveEvent({ id: 'e', point: null }),
      near('f', 100, -20),
    ];
    const { clusters, loose } = clusterEvents(events, 3);
    expect(clusters).toHaveLength(1);
    expect(clusters[0]).toMatchObject({ category: 'news', count: 3 });
    expect(clusters[0]!.lon).toBeCloseTo(10.47, 1);
    expect(loose.map((event) => event.id)).toEqual(['d', 'f']);
    expect(cellSizeFor(1)).toBe(12);
    expect(cellSizeFor(2)).toBe(6);
    expect(cellSizeFor(2.9)).toBe(3);
    expect(clusterRadius(4)).toBe(18);
    expect(clusterRadius(1_000_000)).toBe(36);
  });

  it('draws a circle and a label per cluster and forwards picks', () => {
    const onPick = vi.fn();
    const clusters = clusterEvents([near('a', 0, 0), near('b', 0.5, 0.5), near('c', 1, 1)], 3);
    const layers = buildClusterLayers(clusters.clusters, onPick);
    expect(layers.map((layer) => layer.id)).toEqual(['clusters', 'cluster-labels']);
    const circle = layers[0]!.props as unknown as {
      onClick: (info: { object?: unknown }) => boolean;
      getRadius: (c: { count: number }) => number;
    };
    circle.onClick({ object: clusters.clusters[0] });
    expect(onPick).toHaveBeenCalledWith(clusters.clusters[0]);
    expect(circle.getRadius({ count: 3 })).toBeCloseTo(16.34, 1);
    expect(buildClusterLayers([], onPick)).toEqual([]);
  });

  it('clusters only when the camera is far out', () => {
    const onPick = vi.fn();
    const onCluster = vi.fn();
    const events = [near('a', 0, 0), near('b', 0.5, 0.5), near('c', 1, 1), near('d', 60, 10)];
    const far = buildEventLayers(events, [], onPick, null, { zoom: 1, onCluster });
    expect(far.map((layer) => layer.id)).toEqual(['clusters', 'cluster-labels', 'events-news']);
    const close = buildEventLayers(events, [], onPick, null, { zoom: 5, onCluster });
    expect(close.map((layer) => layer.id)).toEqual(['events-news']);
  });
});

describe('icons', () => {
  it('chooses icons for aircraft, cyclones and volcanoes only', () => {
    expect(iconFor(liveEvent({ category: 'aviation', subtype: 'military_aircraft' }))).toBe(
      'aircraft',
    );
    expect(iconFor(liveEvent({ subtype: 'tropical_cyclone' }))).toBe('cyclone');
    expect(iconFor(liveEvent({ subtype: 'volcanoes' }))).toBe('volcano');
    expect(iconFor(liveEvent({ subtype: 'earthquake' }))).toBeNull();
    expect(headingOf(liveEvent({ attributes: { track_deg: 270 } }))).toBe(270);
    expect(headingOf(liveEvent({ attributes: { track_deg: 'x' } }))).toBe(0);
  });

  it('builds one icon layer for iconed events and none otherwise', () => {
    const onPick = vi.fn();
    expect(buildIconLayer([liveEvent()], onPick, null)).toBeNull();
    const plane = liveEvent({
      id: 'p',
      category: 'aviation',
      subtype: 'military_aircraft',
      attributes: { track_deg: 90 },
    });
    const layer = buildIconLayer([plane, liveEvent({ id: 'q' })], onPick, 'p');
    expect(layer?.id).toBe('event-icons');
    const props = layer!.props as unknown as {
      data: unknown[];
      getAngle: (e: unknown) => number;
      getSize: (e: unknown) => number;
      getIcon: (e: unknown) => { url: string; mask: boolean };
      onClick: (info: { object?: unknown }) => boolean;
    };
    expect(props.data).toHaveLength(1);
    expect(props.getAngle(plane)).toBe(-90);
    expect(props.getSize(plane)).toBe(30);
    expect(props.getIcon(plane).url.startsWith('data:image/svg+xml')).toBe(true);
    props.onClick({ object: plane });
    expect(onPick).toHaveBeenCalledWith(plane);
    const layers = buildEventLayers([plane, liveEvent({ id: 'q' })], [], onPick, null);
    expect(layers.map((layer) => layer.id)).toEqual(['events-disaster', 'event-icons']);
  });
});
