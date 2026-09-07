import { describe, expect, it, vi } from 'vitest';

import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';

import { buildIconLayer, iconFor } from './icons';

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
