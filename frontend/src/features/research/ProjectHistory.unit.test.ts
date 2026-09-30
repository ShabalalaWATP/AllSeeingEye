import { describe, expect, it } from 'vitest';
import { projectInterval } from './ProjectHistory';

describe('historical commitment years', () => {
  it('includes the whole last year and permits thirty complete years', () => {
    expect(projectInterval({ enabled: true, firstYear: '2000', lastYear: '2029' })).toEqual({
      since: '2000-01-01T00:00:00.000Z',
      until: '2030-01-01T00:00:00.000Z',
    });
  });
  it.each([
    ['2000', '2030'],
    ['2021', '2020'],
    ['', '2020'],
    ['2e03', '2020'],
    ['2000', '9999'],
    ['0999', '1000'],
  ])('rejects invalid or oversized intervals %s to %s', (firstYear, lastYear) => {
    expect(projectInterval({ enabled: true, firstYear, lastYear })).toBeNull();
  });
});
