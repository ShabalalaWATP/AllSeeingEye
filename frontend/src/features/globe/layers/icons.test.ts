import { describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';

import { buildIconLayer, iconFor } from './icons';
import { buildEventLayers } from './registry';

type Accessor<T> = (event: LiveEvent) => T;

function props(layer: ReturnType<typeof buildIconLayer>) {
  if (layer === null) throw new Error('expected a layer');
  return layer.props as unknown as {
    getIcon: Accessor<{ url: string }>;
    getSize: Accessor<number>;
    getColor: Accessor<number[]>;
    getAngle: Accessor<number>;
    onClick: (info: { object?: LiveEvent }) => boolean;
  };
}

describe('icon layer accessors', () => {
  it('draws a thermal sensor symbol for FIRMS detections without relabelling other disasters', () => {
    const thermal = liveEvent({
      source_id: 'firms_viirs_noaa20',
      category: 'disaster',
      subtype: 'thermal_detection',
      point: { lon: 0, lat: 0 },
    });
    expect(iconFor(thermal)).toBe('thermal');
    expect(props(buildIconLayer([thermal], vi.fn(), null)).getIcon(thermal).url).toContain('svg');
    expect(iconFor({ ...thermal, subtype: 'earthquake' })).toBeNull();
  });
  it('draws only vessel positions as boats, retaining heading and warning distinctions', () => {
    const vessel = liveEvent({
      category: 'maritime',
      subtype: 'vessel_position',
      point: { lon: 2, lat: 50 },
      attributes: { track_deg: 135 },
    });
    const warning = liveEvent({
      category: 'maritime',
      subtype: 'hazard',
      point: { lon: 2, lat: 50 },
    });
    expect(iconFor(vessel)).toBe('vessel');
    const unknown = { ...vessel, attributes: { track_deg: null } };
    expect(iconFor(unknown)).toBe('vessel_unknown');
    expect(props(buildIconLayer([unknown], vi.fn(), null)).getIcon(unknown).url).not.toEqual(
      props(buildIconLayer([vessel], vi.fn(), null)).getIcon(vessel).url,
    );
    expect(iconFor(warning)).toBeNull();
    expect(props(buildIconLayer([vessel], vi.fn(), null)).getAngle(vessel)).toBe(-135);
  });
  const aircraft = liveEvent({
    id: 'a1',
    category: 'aviation',
    subtype: 'military',
    point: { lon: 30, lat: 45 },
    attributes: { track_deg: 90 },
  });
  const emergency = liveEvent({
    id: 'a2',
    category: 'aviation',
    subtype: 'emergency',
    point: { lon: 31, lat: 45 },
  });
  const volcano = liveEvent({
    id: 'v1',
    category: 'disaster',
    subtype: 'volcano',
    point: { lon: 15, lat: 38 },
  });

  it('returns nothing when no event carries an icon', () => {
    const news = liveEvent({ id: 'n1', category: 'news', point: { lon: 0, lat: 0 } });
    expect(buildIconLayer([news], vi.fn(), null)).toBeNull();
  });

  it('sizes the selected icon up, colours emergencies, rotates aircraft and reports picks', () => {
    const onPick = vi.fn();
    const layer = props(buildIconLayer([aircraft, emergency, volcano], onPick, 'a1'));
    expect(layer.getSize(aircraft)).toBe(30);
    expect(layer.getSize(volcano)).toBe(22);
    expect(layer.getColor(emergency)).toEqual([255, 90, 90, 255]);
    expect(layer.getColor(volcano)).toHaveLength(4);
    expect(layer.getAngle(aircraft)).toBe(-90);
    expect(layer.getAngle(volcano)).toBe(0);
    expect(layer.getIcon(volcano).url.startsWith('data:image/svg+xml')).toBe(true);
    expect(layer.onClick({ object: volcano })).toBe(true);
    expect(onPick).toHaveBeenCalledWith(volcano);
    layer.onClick({});
    expect(onPick).toHaveBeenLastCalledWith(null);
  });
});

it('supplies intrinsic SVG dimensions so browsers can decode icon bitmaps', () => {
  const event = liveEvent({ category: 'aviation', point: { lon: 0, lat: 0 } });
  const url = props(buildIconLayer([event], vi.fn(), null)).getIcon(event).url;
  const svg = new DOMParser().parseFromString(
    decodeURIComponent(url.slice(url.indexOf(',') + 1)),
    'image/svg+xml',
  ).documentElement;
  expect(svg.getAttribute('width')).toBe('64');
  expect(svg.getAttribute('height')).toBe('64');
  expect(svg.getAttribute('viewBox')).toBe('0 0 64 64');
});

it.each([
  [true, 4, false, 90],
  [false, 4, true, -90],
  [true, 13, true, -90],
] as const)(
  'preserves heading and hemisphere treatment for globe=%s zoom=%s',
  (globe, zoom, billboard, angle) => {
    const event = liveEvent({
      category: 'aviation',
      point: { lon: 0, lat: 0 },
      attributes: { track_deg: 90 },
    });
    const layer = buildEventLayers([event], [], vi.fn(), null, {
      zoom,
      globe,
      onCluster: vi.fn(),
    }).find((item) => item.id === 'event-icons');
    expect(layer?.props).toMatchObject({ billboard });
    expect(props(layer ?? null).getAngle(event)).toBe(angle);
    if (!billboard) expect(layer?.props).toMatchObject({ parameters: { 2886: 2304 } });
  },
);
