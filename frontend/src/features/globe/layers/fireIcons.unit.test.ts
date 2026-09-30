import { expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';
import { buildIconLayer, iconFor } from './icons';
import { buildEventLayers } from './registry';

const wildfire = liveEvent({ id: 'wildfire', category: 'disaster', subtype: 'wildfires' });
const thermal = liveEvent({ id: 'thermal', category: 'disaster', subtype: 'thermal_detection' });

it.each(['wildfire', 'wildfires'])(
  'uses a flame for %s while retaining the distinct thermal sensor symbol',
  (subtype) => {
    const report = { ...wildfire, subtype };
    expect(iconFor(report)).toBe('wildfire');
    expect(iconFor({ ...report, category: 'news' })).toBeNull();
    expect(iconFor({ ...report, subtype: 'wildfires_unconfirmed' })).toBeNull();
    const layer = buildIconLayer([report, thermal], vi.fn(), 'wildfire', true)!;
    const props = layer.props as unknown as {
      getIcon: (event: LiveEvent) => { url: string };
      getSize: (event: LiveEvent) => number;
      getColor: (event: LiveEvent) => number[];
      getAngle: (event: LiveEvent) => number;
      onClick: (info: { object: LiveEvent }) => void;
    };
    expect(props.getIcon(report).url).not.toBe(props.getIcon(thermal).url);
    expect(props.getSize(report)).toBeGreaterThan(props.getSize(thermal));
    expect(props.getColor(report)).toEqual([251, 146, 60, 245]);
    expect(props.getAngle(report)).toBe(180);
    expect(layer.props.parameters).toEqual({ 2886: 2304 });
  },
);

it.each([true, false])(
  'retains approximate wildfire rings, picking and selection clearing in globe=%s',
  (globe) => {
    const approximate = { ...wildfire, geo_confidence: 'city' as const };
    const unlocated = { ...wildfire, id: 'country', geo_confidence: 'country' as const };
    const pick = vi.fn();
    const events = [approximate, unlocated, thermal];
    const view = { globe, zoom: 4, onCluster: vi.fn() };
    const layers = buildEventLayers(events, [], pick, approximate.id, view);
    const icons = layers.find((layer) => layer.id === 'event-icons')!;
    expect(icons.props.data).toEqual([thermal, approximate]);
    expect(layers.some((layer) => layer.id === 'approximate-events')).toBe(true);
    expect(layers.some((layer) => layer.id === 'selected-event-halo')).toBe(true);
    (icons.props as unknown as { onClick: (info: { object: LiveEvent }) => void }).onClick({
      object: approximate,
    });
    expect(pick).toHaveBeenCalledWith(approximate);
    expect(
      buildEventLayers(events, [], pick, null, view).some(
        (layer) => layer.id === 'selected-event-halo',
      ),
    ).toBe(false);
    expect(buildEventLayers(events, ['disaster'], pick, null, view)).toEqual([]);
  },
);
