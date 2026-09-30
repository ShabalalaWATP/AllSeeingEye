import { expect, it } from 'vitest';
import { aoi } from '@/test/fixtures.direction';
import { indicator } from '@/test/fixtures';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { aoiSchema } from './direction';
import { indicatorSchema } from './warning';

it('retains exact area geometry and hash in AOI and indicator responses', () => {
  const research_area = {
    geometry: rectangleArea({ west: 170, east: -170, south: -10, north: 10 }),
    sha256: 'a'.repeat(64),
  };
  expect(aoiSchema.parse({ ...aoi, research_area }).research_area).toEqual(research_area);
  expect(indicatorSchema.parse({ ...indicator, research_area }).research_area).toEqual(
    research_area,
  );
  expect(aoiSchema.parse(aoi).research_area).toBeUndefined();
});
