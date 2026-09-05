import { describe, expect, it } from 'vitest';

import { parseBox, parseCountries, parseSirLines } from './planText';

describe('plan text parsing', () => {
  it('reads requirement lines with optional keywords and categories', () => {
    expect(
      parseSirLines(
        'Strikes | Kharkiv, shelling | conflict, bogus\n\nTalks\n | orphan\nNo cats | | ',
      ),
    ).toEqual([
      { text: 'Strikes', keywords: ['Kharkiv', 'shelling'], categories: ['conflict'] },
      { text: 'Talks' },
      { text: 'No cats' },
    ]);
    expect(parseSirLines('   ')).toEqual([]);
  });

  it('keeps only two-letter nation codes', () => {
    expect(parseCountries('ua, gb , xx1, , d')).toEqual(['UA', 'GB']);
  });

  it('reads a bounding box only when all four numbers are present', () => {
    expect(parseBox('30, 44, 41, 53')).toEqual([30, 44, 41, 53]);
    expect(parseBox('30, 44, 41')).toBeNull();
    expect(parseBox('30, 44, 41, 53, 1')).toBeNull();
    expect(parseBox('30, abc, 41, 53')).toBeNull();
    expect(parseBox('')).toBeNull();
  });
});
