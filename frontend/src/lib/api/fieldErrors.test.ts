import { describe, expect, it } from 'vitest';

import { ApiError } from './errors';
import { mapFieldErrors } from './fieldErrors';

const invalid = (fields: Record<string, string>) =>
  new ApiError(422, 'validation_error', 'The request is invalid.', fields);

const ids = (name: string) => `form-${name}`;

describe('mapFieldErrors', () => {
  it('matches exact keys and nested loc paths to declared fields', () => {
    const result = mapFieldErrors(
      invalid({
        name: 'Too long.',
        'countries.0': 'Unknown country.',
        'scope.country_isos': 'Bad.',
      }),
      {
        name: 'Indicator name',
        countries: 'Countries',
        nations: { label: 'Nations', paths: ['scope.country_isos'], target: 'nations-step' },
      },
      ids,
    );
    expect(result.message('name')).toBe('Too long.');
    expect(result.message('countries')).toBe('Unknown country.');
    expect(result.message('nations')).toBe('Bad.');
    expect(result.matched).toBe(true);
    expect(result.entries).toEqual([
      { key: 'name', label: 'Indicator name', message: 'Too long.', target: 'form-name' },
      {
        key: 'countries',
        label: 'Countries',
        message: 'Unknown country.',
        target: 'form-countries',
      },
      { key: 'nations', label: 'Nations', message: 'Bad.', target: 'nations-step' },
    ]);
  });

  it('keeps the first reason when several paths land on one field', () => {
    const result = mapFieldErrors(
      invalid({ 'keywords.0': 'First.', 'keywords.3': 'Second.' }),
      { keywords: 'Keywords' },
      ids,
    );
    expect(result.entries).toHaveLength(1);
    expect(result.message('keywords')).toBe('First.');
  });

  it('lists unknown paths with a readable label and no focus target', () => {
    const result = mapFieldErrors(
      invalid({ 'research_area.geometry.coordinates.0': 'Invalid ring.', body: 'Malformed.' }),
      { name: 'Name' },
      ids,
    );
    expect(result.matched).toBe(false);
    expect(result.entries).toEqual([
      {
        key: 'research_area.geometry.coordinates.0',
        label: 'Research area geometry coordinates item 1',
        message: 'Invalid ring.',
        target: null,
      },
      { key: 'body', label: 'Request', message: 'Malformed.', target: null },
    ]);
  });

  it('bounds overlong server reasons and labels', () => {
    const result = mapFieldErrors(invalid({ ['x'.repeat(500)]: 'y'.repeat(900) }), {}, ids);
    const [entry] = result.entries;
    expect(entry?.label.length).toBeLessThanOrEqual(120);
    expect(entry?.message.length).toBeLessThanOrEqual(300);
  });

  it('returns nothing for errors without field reasons', () => {
    for (const error of [null, new Error('x'), new ApiError(500, 'internal_error', 'Boom.')]) {
      const result = mapFieldErrors(error, { name: 'Name' }, ids);
      expect(result.entries).toEqual([]);
      expect(result.matched).toBe(false);
      expect(result.message('name')).toBeUndefined();
    }
  });
});

describe('mapFieldErrors with a request root', () => {
  it('leaves the wrapping path out of readable labels', () => {
    const result = mapFieldErrors(invalid({ 'report.research_terms.0': 'Too long.' }), {}, ids, {
      root: 'report',
    });
    expect(result.entries[0]?.label).toBe('Research terms item 1');
  });
});
