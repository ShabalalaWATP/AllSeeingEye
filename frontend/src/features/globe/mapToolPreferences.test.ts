import { expect, it, vi } from 'vitest';
import { readToolFavourites, writeToolFavourites } from './mapToolPreferences';

it('ignores malformed or obsolete saved preferences instead of breaking the tool chooser', () => {
  for (const raw of [
    '{',
    '{}',
    '["missing"]',
    '["rf","rf"]',
    '[null]',
    '["draw","area","rf","measure","style"]',
  ]) {
    localStorage.setItem('ase.map.tool-favourites', raw);
    expect(readToolFavourites()).toBeNull();
  }
  localStorage.setItem('ase.map.tool-favourites', '["RF coverage","Draw on map"]');
  expect(readToolFavourites()).toEqual(['rf', 'draw']);
  writeToolFavourites([]);
  expect(readToolFavourites()).toEqual([]);
});

it('keeps tools usable when browser preferences are blocked', () => {
  const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('Storage blocked');
  });
  const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Storage blocked');
  });
  try {
    expect(readToolFavourites()).toBeNull();
    expect(() => writeToolFavourites(['rf'])).not.toThrow();
  } finally {
    get.mockRestore();
    set.mockRestore();
  }
});
