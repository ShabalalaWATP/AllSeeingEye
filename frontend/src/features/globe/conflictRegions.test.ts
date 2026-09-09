import { expect, it, vi } from 'vitest';
import { conflictCard } from '@/test/fixtures.trackers';
import { conflictRegions, filterConflictRegions, regionLabel } from './conflictRegions';
import { conflictRegionLayers } from './layers/conflictRegions';
import type { ConflictRegion } from './conflictRegions';
import type { Position } from '@/lib/map/geoJsonTypes';

it('uses catalogue area centres without relocating evidence and rejects malformed regions', () => {
  const [region] = conflictRegions([conflictCard]);
  expect(region!.centre).toEqual([31.5, 48.25]);
  expect(region!.card.latest!.point).toEqual({ lon: 36.2, lat: 49.9 });
  expect(regionLabel(region!)).toBe('War region (curated)');
  expect(conflictRegions(Array.from({ length: 110 }, () => conflictCard))).toHaveLength(100);
  for (const bbox of [
    [],
    [0, 1, 0, 2],
    [0, 3, 2, 1],
    [-181, 0, 5, 1],
    [0, -86, 1, 1],
    [0, 0, 181, 1],
    [0, 0, 1, 86],
    [0, 0, 1, NaN],
  ]) {
    expect(
      conflictRegions([{ ...conflictCard, conflict: { ...conflictCard.conflict, bbox } }]),
    ).toEqual([]);
  }
  expect(
    conflictRegions([
      { ...conflictCard, conflict: { ...conflictCard.conflict, status: 'unknown' } },
    ]),
  ).toEqual([]);
});

it('combines regional text, classification and nation filters', () => {
  const regions = conflictRegions([
    conflictCard,
    {
      ...conflictCard,
      conflict: {
        ...conflictCard.conflict,
        id: 'taiwan',
        name: 'Taiwan Strait',
        countries: ['TW', 'CN'],
        status: 'tension',
        belligerents: ['China', 'Taiwan'],
        bbox: [118, 21, 123, 27],
      },
    },
  ]);
  expect(filterConflictRegions(regions, ' ukraine Russia ', 'war', 'UA')).toEqual([regions[0]]);
  expect(filterConflictRegions(regions, 'China', 'all', 'TW')).toEqual([regions[1]]);
  expect(filterConflictRegions(regions, '', 'tension', null)).toEqual([regions[1]]);
  expect(filterConflictRegions(regions, 'missing', 'all', null)).toEqual([]);
  expect(filterConflictRegions(regions, '', 'all', 'GB')).toEqual([]);
  expect(regionLabel(regions[1]!)).toBe('Tension area (curated)');
});

it('shows a selected outline and halo, with static icons and no hit targets during drawing', () => {
  const regions = conflictRegions([conflictCard]);
  const pick = vi.fn();
  expect(conflictRegionLayers([], null, pick, false)).toEqual([]);
  const layers = conflictRegionLayers(regions, regions[0]!, pick, true);
  expect(layers[0]!.props.data).toEqual(regions);
  expect(layers[1]!.props.data).toEqual([
    [
      [22, 44],
      [41, 44],
      [41, 52.5],
      [22, 52.5],
      [22, 44],
    ],
  ]);
  const markers = layers[2]!.props as unknown as {
    pickable: boolean;
    onClick: (info: { object?: unknown }) => boolean;
  };
  markers.onClick({ object: regions[0] });
  markers.onClick({});
  expect(pick).toHaveBeenCalledExactlyOnceWith(regions[0]);
  const inactive = conflictRegionLayers(regions, null, pick, false, false);
  expect(inactive[0]!.props.data).toEqual([]);
  expect(inactive[1]!.props.data).toEqual([]);
  expect(inactive[2]!.props.pickable).toBe(false);
  const icon = layers[2]!.props as unknown as {
    getPosition: (region: ConflictRegion) => Position;
    getColor: (region: ConflictRegion) => number[];
    getIcon: () => { url: string };
  };
  expect(icon.getPosition(regions[0]!)).toEqual([31.5, 48.25]);
  expect(icon.getColor(regions[0]!)).toEqual([255, 106, 106, 245]);
  const tension = conflictRegions([
    { ...conflictCard, conflict: { ...conflictCard.conflict, status: 'tension' } },
  ])[0]!;
  expect(icon.getColor(tension)).toEqual([249, 190, 84, 245]);
  expect(icon.getIcon().url).toMatch(/^data:image\/svg\+xml,/);
  const label = layers[3]!.props as unknown as {
    getText: (region: ConflictRegion) => string;
    getPosition: (region: ConflictRegion) => Position;
  };
  expect(label.getText(regions[0]!)).toBe(conflictCard.conflict.name);
  expect(label.getPosition(regions[0]!)).toEqual(icon.getPosition(regions[0]!));
  const halo = layers[0]!.props as unknown as { getPosition: (region: ConflictRegion) => Position };
  expect(halo.getPosition(regions[0]!)).toEqual(icon.getPosition(regions[0]!));
  const path = layers[1]!.props as unknown as { getPath: (points: Position[]) => Position[] };
  expect(
    path.getPath([
      [22, 44],
      [41, 44],
    ]),
  ).toEqual([
    [22, 44],
    [41, 44],
  ]);
});
