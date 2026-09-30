import { describe, expect, it } from 'vitest';
import type { JamCell } from '@/lib/api/aviation';
import { JAM_REGIONS, formatCellPosition, regionFor, summariseJamCells } from './gnssRegions';

const cell = (lon: number, lat: number, level: JamCell['level'], bad = 2, good = 8): JamCell => ({
  lon,
  lat,
  size: 1,
  good,
  bad,
  percent_bad: Math.round(Math.max(0, (100 * (bad - 1)) / (good + bad)) * 10) / 10,
  level,
});

describe('GNSS interference regions', () => {
  it('assigns cells to the first matching box and everything else to elsewhere', () => {
    expect(regionFor(cell(20.5, 55.5, 'amber')).key).toBe('baltic');
    expect(regionFor(cell(36.5, 45.5, 'red')).key).toBe('black_sea');
    expect(regionFor(cell(36.5, 49.5, 'red')).key).toBe('ukraine');
    expect(regionFor(cell(37.5, 55.5, 'red')).key).toBe('russia_west');
    expect(regionFor(cell(-0.5, 51.5, 'red')).key).toBe('north_sea');
    expect(regionFor(cell(-100, 40, 'red')).key).toBe('elsewhere');
    expect(JAM_REGIONS.at(-1)?.box).toBeNull();
  });

  it('counts amber and red cells only, ranks regions by red then size and lists the worst cells', () => {
    const summary = summariseJamCells([
      cell(20.5, 55.5, 'amber'),
      cell(21.5, 55.5, 'amber'),
      cell(36.5, 45.5, 'red', 6, 4),
      cell(0.5, 51.5, 'green', 0, 200),
    ]);
    expect(summary.total).toBe(3);
    expect(summary.red).toBe(1);
    expect(summary.amber).toBe(2);
    expect(summary.observations).toBe(30);
    expect(summary.regions.map((row) => [row.key, row.cells, row.red])).toEqual([
      ['black_sea', 1, 1],
      ['baltic', 2, 0],
    ]);
    expect(summary.worst[0]?.lon).toBe(36.5);
    expect(formatCellPosition(cell(-0.5, 51.5, 'red'))).toBe('51.5°N 0.5°W');
  });
});
