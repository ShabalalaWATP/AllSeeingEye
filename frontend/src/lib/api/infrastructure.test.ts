import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, it } from 'vitest';
import { infrastructureSchema } from './infrastructure';
import type { Infrastructure, Cable, GroundStation } from './infrastructure';

function resource(name: string): unknown {
  return JSON.parse(
    readFileSync(resolve(process.cwd(), '../backend/src/ase/resources', name), 'utf8'),
  ) as unknown;
}

export const packagedInfrastructure = {
  ...(resource('nuclear_facilities.json') as Omit<
    Infrastructure,
    'cables' | 'ground_stations' | 'snapshot_date' | 'cable_attribution' | 'cable_licence_url'
  >),
  cables: resource('submarine_cables.json') as Cable[],
  ground_stations: resource('ground_stations.json') as GroundStation[],
  snapshot_date: '2026-09-08',
  cable_attribution: 'OpenStreetMap contributors',
  cable_licence_url: 'https://www.openstreetmap.org/copyright',
};

it('accepts every actual packaged infrastructure record without rewriting historical URLs', () => {
  const result = infrastructureSchema.safeParse(packagedInfrastructure);
  const issues = result.success ? [] : result.error.issues.map((issue) => issue.path.join('.'));
  expect(issues).toEqual([]);
  if (!result.success) return;
  expect(result.data.nuclear_facilities).toEqual(packagedInfrastructure.nuclear_facilities);
  expect(result.data.cables).toHaveLength(packagedInfrastructure.cables.length);
  expect(result.data.ground_stations).toHaveLength(packagedInfrastructure.ground_stations.length);
  expect(result.data.nuclear_facilities.some((row) => row.source_url.startsWith('http://'))).toBe(
    true,
  );
});

it.each([
  'javascript:alert(1)',
  'file:///private',
  'https://user:secret@example.org/',
  'http://example.org:8080/',
])('rejects unsafe nuclear source references: %s', (source_url) => {
  const payload = {
    ...packagedInfrastructure,
    nuclear_facilities: [{ ...packagedInfrastructure.nuclear_facilities[0], source_url }],
  };
  expect(infrastructureSchema.safeParse(payload).success).toBe(false);
});
