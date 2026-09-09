import { expect, it, vi } from 'vitest';
import { conflictCard } from '@/test/fixtures.trackers';
import { conflictRegions, type ConflictRegion } from './conflictRegions';
import { conflictRegionLayers } from './layers/conflictRegions';

it.each([false, true])(
  'orients regional icons and selected labels for %s flat projection without disabling far-side culling',
  (flat) => {
    const regions = conflictRegions([conflictCard]);
    const layers = conflictRegionLayers(regions, regions[0]!, vi.fn(), flat);
    for (const id of ['conflict-region-markers', 'conflict-region-labels']) {
      const layer = layers.find((item) => item.id === id)!;
      expect(layer.props).toMatchObject({ billboard: flat, getAngle: flat ? 0 : 180 });
      expect(layer.props.parameters).toEqual({ 2886: 2304 });
      const position = layer.props as unknown as {
        getPosition: (item: ConflictRegion) => readonly number[];
      };
      expect(position.getPosition(regions[0]!)).toEqual(regions[0]!.centre);
    }
  },
);

it.each([false, true])(
  'removes every selection cue when the inspector closes (%s flat)',
  (flat) => {
    const regions = conflictRegions([conflictCard]);
    const layers = conflictRegionLayers(regions, null, vi.fn(), flat);
    for (const id of [
      'conflict-region-selection',
      'conflict-region-context',
      'conflict-region-labels',
    ]) {
      expect(layers.find((item) => item.id === id)!.props.data).toEqual([]);
    }
    expect(layers.find((item) => item.id === 'conflict-region-markers')!.props.data).toEqual(
      regions,
    );
  },
);
